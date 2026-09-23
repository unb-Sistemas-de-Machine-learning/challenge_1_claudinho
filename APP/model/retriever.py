"""Recuperador semântico de evidências científicas no Supabase (pgvector).

Documentado em Docs/Model/02_arquitetura_nlp_rag.md e Docs/Data/02_armazenamento_e_estrutura.md.
"""

import re
import time
from datetime import date, datetime

from APP.model.database import obter_supabase
from APP.model.embeddings import gerar_embedding_consulta
from APP.observabilidade import adicionar_ao_log
from APP.schemas import Fonte

SIMILARIDADE_MINIMA_PADRAO = 0.70
LIMITE_PADRAO = 4

# Abaixo disso a consulta conta como "sem cobertura" na deteccao de drift
# (Docs/Production/02, secao 2.1). Estimativa inicial, a calibrar com uso real.
LIMIAR_BAIXA_COBERTURA = 0.75

_catalogo_de_artigos: dict[str, dict[str, object]] | None = None


class RecuperacaoIndisponivel(RuntimeError):
    """A busca vetorial nao pode ser feita (banco ou servico de embeddings indisponivel)."""


def obter_metadados_artigos() -> dict[str, dict[str, object]]:
    """Carrega metadados de artigos em memoria para enriquecer os chunks retornados.

    O cache so guarda consultas BEM-SUCEDIDAS. Com `lru_cache`, uma falha na primeira
    chamada deixava o catalogo vazio em cache ate o proximo restart, e toda fonte
    aparecia como "Autores nao informados".
    """
    global _catalogo_de_artigos
    if _catalogo_de_artigos is not None:
        return _catalogo_de_artigos

    try:
        supabase = obter_supabase()
        resposta = (
            supabase.table("articles").select("id, title, author, published_at, metadata").execute()
        )
    except Exception as erro:
        adicionar_ao_log(retrieval={"erro_metadados": type(erro).__name__})
        return {}

    _catalogo_de_artigos = {item["id"]: item for item in resposta.data or []}
    return _catalogo_de_artigos


def limpar_cache_de_artigos() -> None:
    """Descarta o catalogo em memoria (usado nos testes e apos nova ingestao)."""
    global _catalogo_de_artigos
    _catalogo_de_artigos = None


def _extrair_data_publicacao(valor_data: str | None) -> date:
    if not valor_data:
        return date(2020, 1, 1)
    try:
        return datetime.fromisoformat(valor_data).date()
    except (ValueError, TypeError):
        return date(2020, 1, 1)


def buscar_evidencias_cientificas(
    consulta: str,
    limite: int = LIMITE_PADRAO,
    similaridade_minima: float = SIMILARIDADE_MINIMA_PADRAO,
) -> tuple[list[Fonte], list[dict[str, object]]]:
    """Busca os fragmentos de artigos mais proximos semanticamente da consulta.

    Retorna uma tupla:
      (lista_de_fontes_validadas, dados_brutos_dos_chunks)
    """
    chunks = []
    inicio = time.perf_counter()
    try:
        vetor_consulta = gerar_embedding_consulta(consulta)
        supabase = obter_supabase()

        resposta_rpc = supabase.rpc(
            "buscar_chunks",
            {
                "consulta": vetor_consulta,
                "limite": limite,
                "similaridade_minima": similaridade_minima,
            },
        ).execute()
        chunks = resposta_rpc.data or []
    except Exception as erro:
        # Falha de infraestrutura (banco fora do ar, Space de embeddings dormindo) NAO e
        # "a base nao tem estudos sobre isso". Responder "sem evidencia" nesse caso seria
        # dizer ao usuario algo falso; o pipeline transforma isto em 503.
        adicionar_ao_log(
            retrieval={
                "erro": type(erro).__name__,
                # Ex.: "HTTP 402" e a cota mensal do Hugging Face esgotada; sem isso, o log
                # so diria que os embeddings falharam, sem dizer por que.
                "detalhe": str(erro)[:80],
                "vector_search_ms": _ms_desde(inicio),
            }
        )
        raise RecuperacaoIndisponivel(type(erro).__name__) from erro

    _registrar_recuperacao(chunks, limite, inicio)

    if not chunks:
        return [], []

    catalogo_artigos = obter_metadados_artigos()
    fontes: list[Fonte] = []

    for chunk in chunks:
        article_id = chunk.get("article_id")
        metadados_artigo = catalogo_artigos.get(article_id, {})
        metas_json = metadados_artigo.get("metadata") or {}

        title = chunk.get("titulo") or metadados_artigo.get("title") or "Artigo Científico"
        authors = metadados_artigo.get("author") or "Autores não informados"
        journal = metas_json.get("revista") or chunk.get("fonte") or "Periódico Científico"
        doi = metas_json.get("doi") or "DOI não informado"
        pub_at = _extrair_data_publicacao(metadados_artigo.get("published_at"))
        conteudo = chunk.get("conteudo") or ""

        # Limita o excerpt a ~300 caracteres legíveis
        excerpt = conteudo[:300].strip() + ("..." if len(conteudo) > 300 else "")

        fonte = Fonte(
            chunk_id=str(chunk.get("chunk_id", "")),
            title=title,
            authors=authors,
            journal=journal,
            published_at=pub_at,
            doi=doi,
            excerpt=excerpt,
        )
        fontes.append(fonte)

    return fontes, chunks


def _ms_desde(inicio: float) -> int:
    return int((time.perf_counter() - inicio) * 1000)


def _registrar_recuperacao(chunks: list[dict[str, object]], limite: int, inicio: float) -> None:
    """Grava no log as metricas de cobertura usadas na deteccao de drift.

    Docs/Production/02, secao 2.1: a taxa de consultas com baixa cobertura e o sinal
    primario de que surgiu um tema novo que a base ainda nao cobre.
    """
    similaridades = [
        float(c["similaridade"]) for c in chunks if isinstance(c.get("similaridade"), int | float)
    ]
    maxima = max(similaridades) if similaridades else None
    adicionar_ao_log(
        retrieval={
            "top_k": limite,
            "chunks": len(chunks),
            "chunk_ids": [str(c.get("chunk_id", "")) for c in chunks],
            "similarity_max": round(maxima, 4) if maxima is not None else None,
            "low_coverage": not chunks or (maxima is not None and maxima < LIMIAR_BAIXA_COBERTURA),
            "vector_search_ms": _ms_desde(inicio),
        }
    )


def formatar_contexto_cientifico(chunks: list[dict[str, object]]) -> str:
    """Formata os chunks recuperados para insercao no bloco de estudos do prompt."""
    if not chunks:
        return "Nenhum artigo cientifico encontrado na base com similaridade suficiente."

    blocos = []
    for i, c in enumerate(chunks, 1):
        cid = c.get("chunk_id", f"chunk_{i}")
        titulo = c.get("titulo", "")
        conteudo = (c.get("conteudo") or "").strip()
        bloco = f"[ID_CHUNK: {cid}]\n" f"Artigo: {titulo}\n" f"Conteudo: {conteudo}\n"
        blocos.append(bloco)

    return "\n---\n".join(blocos)


def limpar_nome_alimento(nome: str) -> str:
    """Remove marcadores de tag html e notas de media do nome do alimento."""
    limpo = re.sub(r"<[^>]+>", "", nome)
    limpo = re.sub(r"\(média[^)]*\)", "", limpo)
    limpo = " ".join(limpo.split()).strip().rstrip(",")
    return limpo


def _converter_numero_tbca(val: str | int | float | None) -> float:
    """Converte valores decimais da TBCA (que usam virgula) para float."""
    if val is None:
        return 0.0
    s = str(val).replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def buscar_alimento_tbca(termo: str) -> dict[str, object] | None:
    """Busca o alimento mais representativo na tabela TBCA do Supabase."""
    try:
        supabase = obter_supabase()
        res = (
            supabase.table("TBCA")
            .select("ID, alimento, kcal, carboidrato_tot, proteina, lipidios, fibra, umidade")
            .ilike("alimento", f"%{termo}%")
            .execute()
            .data
        )
    except Exception:
        return None

    if not res:
        return None

    def score(item):
        nome = item["alimento"].lower()
        s = 0
        if nome.startswith(termo):
            s += 50
        if "in natura" in nome:
            s += 40
        if "polido" in nome or "inglesa" in nome or "carioca" in nome:
            s += 30
        if "cozido" in nome or "cozida" in nome:
            s += 25
        if "s/ sal" in nome or "s/ óleo" in nome:
            s += 15
        if "c/ " in nome:
            s -= 30
        for p in [
            "caramelada",
            "flambada",
            "milanesa",
            "doce",
            "açúcar",
            "leite",
            "coco",
            "bacon",
            "camarão",
            "frito",
            "chips",
            "suíça",
            "rechead",
            "ovo",
            "bacalhau",
        ]:
            if p == "doce" and ("doce" in termo):
                continue
            if p in nome:
                s -= 40
        return s

    escolhido = max(res, key=score)
    return {
        "id": escolhido["ID"],
        "nome": limpar_nome_alimento(escolhido["alimento"]),
        "kcal": int(_converter_numero_tbca(escolhido["kcal"])),
        "carboidratos": _converter_numero_tbca(escolhido["carboidrato_tot"]),
        "proteina": _converter_numero_tbca(escolhido["proteina"]),
        "lipidios": _converter_numero_tbca(escolhido["lipidios"]),
        "fibra": _converter_numero_tbca(escolhido["fibra"]),
        "umidade": _converter_numero_tbca(escolhido["umidade"]),
    }


def detectar_e_comparar_tbca(
    consulta: str,
) -> tuple[dict[str, object] | None, list[Fonte]]:
    """Detecta se a consulta é uma comparação ou consulta nutricional na TBCA do Supabase."""
    c = consulta.lower()
    candidatos = [
        "abacate",
        "abacaxi",
        "abobrinha",
        "abóbora",
        "abobora",
        "açaí",
        "acai",
        "acerola",
        "achocolatado",
        "agrião",
        "agriao",
        "alface",
        "alho",
        "almeirão",
        "almôndega",
        "amendoim",
        "amora",
        "arroz",
        "aveia",
        "azeite",
        "azeitona",
        "açúcar",
        "acucar",
        "banana",
        "batata",
        "feijão",
        "feijao",
        "frango",
        "leite",
        "macarrão",
        "macarrao",
        "mandioca",
        "óleo",
        "oleo",
        "ovo",
        "pão",
        "pao",
        "tapioca",
    ]

    # Deduplicar preservando termos encontrados
    achados: list[str] = []
    for cand in candidatos:
        # Limite de palavra: por substring, "alho" casava em "trabalho", "ovo" em "novo" e
        # "pao" no fim de uma URL, e a pergunta era desviada para a TBCA sem nunca passar
        # pelos estudos.
        if re.search(rf"\b{re.escape(cand)}\b", c):
            base = (
                cand.replace("á", "a")
                .replace("ã", "a")
                .replace("ó", "o")
                .replace("é", "e")
                .replace("ç", "c")
            )
            if not any(
                base
                in a.replace("á", "a")
                .replace("ã", "a")
                .replace("ó", "o")
                .replace("é", "e")
                .replace("ç", "c")
                for a in achados
            ):
                achados.append(cand)

    termos_nutricao = [
        "caloria",
        "calorias",
        "kcal",
        "carboidrato",
        "carboidratos",
        "proteina",
        "proteínas",
        "proteinas",
        "gordura",
        "gorduras",
        "lipidio",
        "lipidios",
        "lipídios",
        "fibra",
        "fibras",
        "tabela",
        "nutriente",
        "nutrientes",
        "nutricional",
        "engorda",
        "emagrece",
        "100g",
        "porção",
        "porcao",
    ]
    tem_termo_nutricao = any(tn in c for tn in termos_nutricao)

    # Caso 1: Comparacao entre 2 ou mais alimentos. Exige termo nutricional como o caso
    # individual: citar dois alimentos nao quer dizer que a pergunta e sobre composicao
    # ("posso comer arroz e feijao todo dia?" e duvida para os estudos, nao para a TBCA).
    if len(achados) >= 2 and tem_termo_nutricao:
        item1 = buscar_alimento_tbca(achados[0])
        item2 = buscar_alimento_tbca(achados[1])
        if not item1 or not item2:
            return None, []

        fontes = [
            Fonte(
                chunk_id=f"TBCA/{item1['id']}",
                title=item1["nome"],
                authors="USP / FoRC - Centro de Pesquisa em Alimentos",
                journal="Tabela Brasileira de Composição de Alimentos - TBCA (Versão 7.2)",
                published_at=date(2022, 3, 31),
                doi="http://www.tbca.net.br/",
                excerpt=(
                    f"Composição por 100g de alimento pronto para consumo: "
                    f"{item1['kcal']} kcal, {item1['carboidratos']}g carboidratos, "
                    f"{item1['proteina']}g proteínas, {item1['lipidios']}g lipídios, "
                    f"{item1['fibra']}g fibras, {item1['umidade']}% umidade."
                ),
            ),
            Fonte(
                chunk_id=f"TBCA/{item2['id']}",
                title=item2["nome"],
                authors="USP / FoRC - Centro de Pesquisa em Alimentos",
                journal="Tabela Brasileira de Composição de Alimentos - TBCA (Versão 7.2)",
                published_at=date(2022, 3, 31),
                doi="http://www.tbca.net.br/",
                excerpt=(
                    f"Composição por 100g de alimento pronto para consumo: "
                    f"{item2['kcal']} kcal, {item2['carboidratos']}g carboidratos, "
                    f"{item2['proteina']}g proteínas, {item2['lipidios']}g lipídios, "
                    f"{item2['fibra']}g fibras, {item2['umidade']}% umidade."
                ),
            ),
        ]
        dados_comp = {
            "alimento_1": item1,
            "alimento_2": item2,
            "termo_1": achados[0],
            "termo_2": achados[1],
        }
        return dados_comp, fontes

    # Caso 2: Dúvida nutricional sobre 1 alimento específico da TBCA
    if len(achados) == 1 and tem_termo_nutricao:
        item1 = buscar_alimento_tbca(achados[0])
        if not item1:
            return None, []

        fontes = [
            Fonte(
                chunk_id=f"TBCA/{item1['id']}",
                title=item1["nome"],
                authors="USP / FoRC - Centro de Pesquisa em Alimentos",
                journal="Tabela Brasileira de Composição de Alimentos - TBCA (Versão 7.2)",
                published_at=date(2022, 3, 31),
                doi="http://www.tbca.net.br/",
                excerpt=(
                    f"Composição por 100g de alimento pronto para consumo: "
                    f"{item1['kcal']} kcal, {item1['carboidratos']}g carboidratos, "
                    f"{item1['proteina']}g proteínas, {item1['lipidios']}g lipídios, "
                    f"{item1['fibra']}g fibras, {item1['umidade']}% umidade."
                ),
            )
        ]
        dados_comp = {
            "alimento_1": item1,
            "termo_1": achados[0],
        }
        return dados_comp, fontes

    return None, []
