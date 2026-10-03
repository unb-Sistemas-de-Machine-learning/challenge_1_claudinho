#!/usr/bin/env python
"""Ingestao LOCAL de PDFs de artigos para o Supabase.

ATENCAO: este script NAO faz parte da API e NAO vai para o repositorio
compartilhado (esta no .gitignore.local). Ele existe so para popular o banco a
partir da sua maquina, usando um modelo de embeddings LOCAL e open source
(sem chave de API, sem custo, sem enviar o conteudo dos PDFs para terceiros).

Fluxo:

    PDF -> extrair texto -> limpar -> `sources` -> `articles`
        -> dividir em chunks -> embeddings locais -> `chunks`

Instalacao (ambiente separado, para nao poluir o .venv da API):

    uv venv .venv-ingestao
    uv pip install --python .venv-ingestao/bin/python -r requirements-ingestao.txt

Antes da primeira execucao, rode `migracao_chunks.sql` no SQL Editor do
Supabase: ele cria a tabela `chunks` (se faltar) e alinha a dimensao do
vetor com o modelo local (768), ja que o schema original veio vector(1536).

Uso:
    .venv-ingestao/bin/python ingerir_pdf.py pdfs/ --fonte "Web of Science"
    .venv-ingestao/bin/python ingerir_pdf.py a.pdf b.pdf --fonte "SciELO" --label true
    .venv-ingestao/bin/python ingerir_pdf.py pdfs/ --fonte X --dry-run   # so inspeciona

Todas as opcoes:  ingerir_pdf.py --help
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CAMINHO_ENV = RAIZ / "APP" / ".env"

# ---------------------------------------------------------------------------
# Parametros de ingestao
# ---------------------------------------------------------------------------

# Modelo de embeddings local. multilingual-e5-base -> 768 dimensoes, treinado em
# 100 idiomas e solido para portugues tecnico. Alternativas:
#   intfloat/multilingual-e5-large  -> 1024 dims, melhor qualidade, ~2 GB
#   BAAI/bge-m3                     -> 1024 dims, otimo para textos longos
# Ao trocar, ajuste DIMENSAO aqui E o vector(...) da coluna chunks.embedding.
MODELO = "intfloat/multilingual-e5-base"
DIMENSAO = 768

# CPU por padrao: a GPU desta maquina (GeForce MX110, sm_50) e antiga demais
# para os kernels CUDA que o torch distribui, e o processo quebra com
# "no kernel image is available for execution on the device". Em CPU um artigo
# de ~20 paginas leva poucos segundos, o que basta para ingestao em lote.
# Numa maquina com GPU recente, use --device cuda.
DISPOSITIVO = "cpu"

# Janelas de ~500 tokens com ~100 de sobreposicao (Docs/Data/02). Como contamos
# palavras e nao tokens, usamos ~0.7 palavra por token para portugues.
PALAVRAS_POR_CHUNK = 350
SOBREPOSICAO = 70
MIN_PALAVRAS_CHUNK = 20  # descarta sobras minusculas no fim do documento

# O PostgREST recusa payloads muito grandes; gravamos os chunks em lotes.
TAMANHO_LOTE = 50

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+\b")
PALAVRAS_CHAVE_RE = re.compile(
    r"(?:palavras[-\s]?chave|palabras[-\s]?clave|keywords?)\s*[:.\-]\s*(.{3,300})",
    re.IGNORECASE,
)
# Secao de referencias: costuma ser ~30% do PDF e so polui a busca semantica.
# O titulo da secao inicia um paragrafo; limpar_texto() ja transformou as
# quebras internas em espaco, entao nao exigimos \n depois do titulo.
REFERENCIAS_RE = re.compile(
    r"(?:^|\n)[ \t]*(?:refer[eê]ncias(?:\s+bibliogr[aá]ficas)?|references|bibliografia)\b[ \t:.]*",
    re.IGNORECASE,
)
LIGADURAS = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "…": "..."}


# ---------------------------------------------------------------------------
# Configuracao / cliente Supabase
# ---------------------------------------------------------------------------
def obter_supabase():
    """Cria o cliente Supabase lendo APP/.env diretamente (independe da API)."""
    from dotenv import dotenv_values
    from supabase import create_client

    if not CAMINHO_ENV.exists():
        sys.exit(f"[erro] Nao encontrei {CAMINHO_ENV}. Ele guarda SUPABASE_URL/KEY.")

    cfg = dotenv_values(CAMINHO_ENV)
    url, key = cfg.get("SUPABASE_URL"), cfg.get("SUPABASE_KEY")
    if not url or not key:
        sys.exit(f"[erro] SUPABASE_URL e SUPABASE_KEY precisam estar em {CAMINHO_ENV}.")

    # O client ja acrescenta /rest/v1; se a URL do .env tambem trouxer esse
    # caminho, o PostgREST responde PGRST125 ("Invalid path"). Corrigimos aqui
    # e avisamos, porque o mesmo .env alimenta a API (APP/model/database.py).
    limpa = url.strip().rstrip("/").removesuffix("/rest/v1")
    if limpa != url.strip().rstrip("/") or url.strip() != limpa:
        print(f"[aviso] SUPABASE_URL deveria ser so o host ({limpa}). Corrija o {CAMINHO_ENV}.")

    return create_client(limpa, key)


# ---------------------------------------------------------------------------
# Extracao de texto do PDF
# ---------------------------------------------------------------------------
def _ocr_pagina(pagina) -> str:
    """OCR de uma pagina (usado so quando --ocr e o PDF e digitalizado)."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        sys.exit(
            "[erro] --ocr exige pytesseract e Pillow:\n"
            "    uv pip install --python .venv-ingestao/bin/python pytesseract pillow\n"
            "    sudo pacman -S tesseract tesseract-data-por"
        )
    import io

    import pymupdf

    # zoom 2x: ~150 dpi, suficiente para artigo cientifico e rapido o bastante.
    pixmap = pagina.get_pixmap(matrix=pymupdf.Matrix(2, 2))
    imagem = Image.open(io.BytesIO(pixmap.tobytes("png")))
    return pytesseract.image_to_string(imagem, lang="por+eng")


def extrair_paginas(caminho: Path, usar_ocr: bool) -> tuple[list[str], dict]:
    """Devolve o texto de cada pagina e os metadados embutidos do PDF."""
    import pymupdf

    documento = pymupdf.open(caminho)
    paginas: list[str] = []
    paginas_ocr = 0
    for pagina in documento:
        texto = pagina.get_text()
        # Menos de 50 caracteres = pagina de imagem (PDF digitalizado).
        if usar_ocr and len(texto.strip()) < 50:
            texto = _ocr_pagina(pagina)
            paginas_ocr += 1
        paginas.append(texto)
    metadados = dict(documento.metadata or {})
    documento.close()
    if paginas_ocr:
        print(f"[ocr] {paginas_ocr} pagina(s) lidas por OCR")
    return paginas, metadados


def remover_cabecalhos_repetidos(paginas: list[str]) -> list[str]:
    """Remove linhas que se repetem na maioria das paginas (cabecalho/rodape)."""
    if len(paginas) < 3:
        return paginas

    contagem: Counter[str] = Counter()
    for pagina in paginas:
        # so as 3 primeiras e 3 ultimas linhas de cada pagina sao candidatas
        linhas = [linha.strip() for linha in pagina.splitlines() if linha.strip()]
        for linha in linhas[:3] + linhas[-3:]:
            contagem[linha] += 1

    limite = max(3, int(len(paginas) * 0.6))
    ruido = {linha for linha, n in contagem.items() if n >= limite and len(linha) < 120}

    limpas = []
    for pagina in paginas:
        mantidas = [
            linha
            for linha in pagina.splitlines()
            # descarta o ruido recorrente e numeros de pagina soltos
            if linha.strip() not in ruido and not re.fullmatch(r"\s*\d{1,4}\s*", linha)
        ]
        limpas.append("\n".join(mantidas))
    return limpas


def limpar_texto(texto: str) -> str:
    """Normaliza o texto bruto do PDF para virar contexto util de RAG."""
    texto = unicodedata.normalize("NFKC", texto)
    for origem, destino in LIGADURAS.items():
        texto = texto.replace(origem, destino)

    # remove caracteres de controle que o PyMuPDF as vezes deixa passar
    texto = "".join(c for c in texto if c == "\n" or c == "\t" or ord(c) >= 32)

    # junta palavras hifenizadas quebradas na virada de linha ("nutri-\ncao")
    texto = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", texto)
    # quebra simples dentro do paragrafo vira espaco; quebra dupla e paragrafo
    texto = re.sub(r"\n{2,}", "\x00", texto)
    texto = re.sub(r"\s*\n\s*", " ", texto)
    texto = texto.replace("\x00", "\n\n")

    texto = re.sub(r"[ \t]{2,}", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def cortar_referencias(texto: str) -> tuple[str, bool]:
    """Corta a secao de referencias, se ela aparecer na metade final do texto."""
    for match in REFERENCIAS_RE.finditer(texto):
        if match.start() > len(texto) * 0.5:
            return texto[: match.start()].strip(), True
    return texto, False


# ---------------------------------------------------------------------------
# Metadados do artigo
# ---------------------------------------------------------------------------
def _data_do_pdf(bruta: str | None) -> str | None:
    """Converte o formato 'D:20230415120000+00'00' do PDF em ISO-8601."""
    if not bruta:
        return None
    digitos = re.sub(r"\D", "", bruta)[:8]
    if len(digitos) != 8:
        return None
    try:
        return datetime.strptime(digitos, "%Y%m%d").replace(tzinfo=UTC).isoformat()
    except ValueError:
        return None


# O campo `title` do PDF costuma vir preenchido pelo programa de diagramacao
# com o nome do arquivo de trabalho ("Microsoft Word - tese_final.docx",
# "Latino marco (2).indd"). Isso passaria por titulo e sujaria a base.
_LIXO_TITULO = re.compile(r"""(?ix)
    ^untitled | \.(pdf|indd|docx?|qxd|qxp|pmd|cdr|ai|tex)\s*$   # extensao de arquivo
    | ^microsoft\s+word | ^documento\d* | ^sem\s*t[ií]tulo
    | ^\d+[-_]texto\s+do\s+artigo                              # padrao de OJS
    | ^\d{3,}[-_]                                               # comeca com id numerico
    | ^(layout|arte|prova|miolo|revista|artigo)\s*\d*\s*$
    """)


def _titulo_lixo(titulo: str) -> bool:
    """Diz se o titulo embutido no PDF e nome de arquivo de producao, e nao titulo."""
    return bool(_LIXO_TITULO.search(titulo.strip()))


def deduzir_titulo(meta: dict, primeira_pagina: str, caminho: Path) -> str:
    """Titulo do PDF; se vazio ou generico, a primeira linha longa da 1a pagina.

    Recebe a pagina BRUTA de proposito: limpar_texto() junta as linhas de um
    paragrafo, o que grudaria o titulo na linha dos autores.
    """
    titulo = (meta.get("title") or "").strip()
    if len(titulo) > 10 and not _titulo_lixo(titulo):
        return titulo

    # o titulo costuma quebrar em duas linhas, as vezes com hifen no meio de
    # uma palavra; desfazemos isso antes de escolher a linha candidata
    pagina = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", primeira_pagina)

    for linha in pagina.split("\n")[:15]:
        linha = linha.strip()
        if 20 < len(linha) < 250 and not DOI_RE.search(linha):
            return linha
    return caminho.stem


def extrair_metadados(meta: dict, texto: str, caminho: Path, sha256: str) -> dict:
    """Monta o jsonb `metadata` de `articles` com o que der para inferir."""
    dados: dict = {"arquivo": caminho.name, "sha256": sha256}

    doi = DOI_RE.search(texto[:6000])
    if doi:
        dados["doi"] = doi.group(0).rstrip(".,;)")

    chaves = PALAVRAS_CHAVE_RE.search(texto[:6000])
    if chaves:
        termos = [t.strip(" .;") for t in re.split(r"[;,]", chaves.group(1))]
        dados["palavras_chave"] = [t for t in termos if 2 < len(t) < 60][:12]

    for origem, destino in (("subject", "assunto"), ("creator", "produtor_pdf")):
        valor = (meta.get(origem) or "").strip()
        if valor:
            dados[destino] = valor[:300]

    dados["paginas"] = meta.get("_paginas")
    dados["modelo_embedding"] = MODELO
    return {k: v for k, v in dados.items() if v}


# ---------------------------------------------------------------------------
# Divisao em fragmentos (chunks)
# ---------------------------------------------------------------------------
def segmentar_sentencas(texto: str) -> list[str]:
    """Quebra em sentencas, respeitando paragrafos e abreviacoes comuns."""
    sentencas: list[str] = []
    for paragrafo in texto.split("\n\n"):
        paragrafo = paragrafo.strip()
        if not paragrafo:
            continue
        # corta apos . ! ? seguidos de espaco e maiuscula/numero, ignorando
        # abreviacoes de uma letra (iniciais de autor) e "Fig.", "et al."
        partes = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý0-9])", paragrafo)
        for parte in partes:
            parte = parte.strip()
            if not parte:
                continue
            # sentenca gigante (tabela, lista sem pontuacao): corta na forca
            palavras = parte.split()
            if len(palavras) > PALAVRAS_POR_CHUNK:
                for i in range(0, len(palavras), PALAVRAS_POR_CHUNK):
                    sentencas.append(" ".join(palavras[i : i + PALAVRAS_POR_CHUNK]))
            else:
                sentencas.append(parte)
    return sentencas


def dividir_em_chunks(texto: str) -> list[str]:
    """Agrupa sentencas em janelas de ~PALAVRAS_POR_CHUNK com sobreposicao.

    Diferente de cortar por contagem crua de palavras, isto nunca parte uma
    sentenca ao meio — o fragmento recuperado pelo RAG continua legivel.
    """
    sentencas = segmentar_sentencas(texto)
    if not sentencas:
        return []

    chunks: list[str] = []
    atual: list[str] = []
    total = 0

    for sentenca in sentencas:
        n = len(sentenca.split())
        if atual and total + n > PALAVRAS_POR_CHUNK:
            chunks.append(" ".join(atual))
            # a cauda vira o inicio do proximo chunk (sobreposicao de contexto)
            cauda: list[str] = []
            acumulado = 0
            for anterior in reversed(atual):
                tamanho = len(anterior.split())
                if acumulado + tamanho > SOBREPOSICAO:
                    break
                cauda.insert(0, anterior)
                acumulado += tamanho
            atual, total = cauda, acumulado
        atual.append(sentenca)
        total += n

    if atual:
        chunks.append(" ".join(atual))

    # a ultima janela pode ser so a sobreposicao da anterior; se for curta, some
    return [c for c in chunks if len(c.split()) >= MIN_PALAVRAS_CHUNK]


# ---------------------------------------------------------------------------
# Embeddings (modelo local, carregado uma unica vez)
# ---------------------------------------------------------------------------
_modelo = None


def gerar_embeddings(textos: list[str]) -> list[list[float]]:
    """Gera embeddings normalizados. e5 exige o prefixo 'passage: ' nos documentos."""
    global _modelo
    if _modelo is None:
        # esconder a GPU antes de importar o torch evita os avisos de CUDA
        # incompativel e garante que nada tente rodar no device errado
        if DISPOSITIVO == "cpu":
            os.environ["CUDA_VISIBLE_DEVICES"] = ""

        from sentence_transformers import SentenceTransformer

        print(f"[modelo] carregando '{MODELO}' em {DISPOSITIVO} (a 1a vez baixa ~1 GB)...")
        _modelo = SentenceTransformer(MODELO, device=DISPOSITIVO)

        # o metodo foi renomeado no sentence-transformers 6; aceitamos os dois
        medir = getattr(_modelo, "get_embedding_dimension", None) or (
            _modelo.get_sentence_embedding_dimension
        )
        obtida = medir()
        if obtida != DIMENSAO:
            sys.exit(
                f"[erro] o modelo devolve {obtida} dimensoes, mas DIMENSAO={DIMENSAO}. "
                f"Ajuste a constante e a coluna chunks.embedding para vector({obtida})."
            )

    entradas = [f"passage: {texto}" for texto in textos]
    vetores = _modelo.encode(
        entradas,
        normalize_embeddings=True,  # normalizado -> distancia de cosseno vira produto interno
        batch_size=16,
        show_progress_bar=len(entradas) > 32,
    )
    return [vetor.tolist() for vetor in vetores]


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------
def obter_ou_criar_fonte(supabase, nome: str, tipo: str, reliability: int) -> str:
    """Devolve o id da fonte, criando-a em `sources` se ainda nao existir."""
    existente = supabase.table("sources").select("id").eq("name", nome).limit(1).execute()
    if existente.data:
        return existente.data[0]["id"]
    criada = (
        supabase.table("sources")
        .insert({"name": nome, "type": tipo, "reliability": reliability})
        .execute()
    )
    print(f"[sources] fonte '{nome}' criada")
    return criada.data[0]["id"]


def verificar_schema(supabase) -> None:
    """Confere que as tabelas existem antes de processar qualquer PDF.

    Sem isso, um `chunks` ausente so estouraria depois de extrair o texto e
    gerar os embeddings — e ja com o artigo gravado pela metade.
    """
    for tabela in ("sources", "articles", "chunks"):
        try:
            supabase.table(tabela).select("id").limit(1).execute()
        except Exception as erro:
            sys.exit(
                f"[erro] nao consegui ler a tabela `{tabela}` no Supabase.\n"
                f"       Se ela nao existe, rode migracao_chunks.sql no SQL Editor.\n"
                f"       Se e erro de credencial, confira SUPABASE_URL/KEY em {CAMINHO_ENV}.\n"
                f"       Detalhe: {erro}"
            )
    print("[schema] sources, articles e chunks acessiveis")


def ja_ingerido(supabase, sha256: str) -> str | None:
    """Procura um artigo com o mesmo hash de arquivo (evita duplicar)."""
    resposta = (
        supabase.table("articles")
        .select("id,title")
        .eq("metadata->>sha256", sha256)
        .limit(1)
        .execute()
    )
    return resposta.data[0]["id"] if resposta.data else None


def gravar_chunks(
    supabase, article_id: str, chunks: list[str], embeddings: list[list[float]]
) -> None:
    """Grava os fragmentos em lotes, para nao estourar o payload do PostgREST."""
    linhas = [
        {
            "article_id": article_id,
            "chunk_index": indice,
            "content": conteudo,
            "embedding": vetor,
        }
        for indice, (conteudo, vetor) in enumerate(zip(chunks, embeddings, strict=True))
    ]
    for inicio in range(0, len(linhas), TAMANHO_LOTE):
        lote = linhas[inicio : inicio + TAMANHO_LOTE]
        try:
            supabase.table("chunks").insert(lote).execute()
        except Exception as erro:
            mensagem = str(erro)
            if "dimension" in mensagem.lower() or "expected" in mensagem.lower():
                sys.exit(
                    f"[erro] a coluna chunks.embedding nao aceita {DIMENSAO} dimensoes.\n"
                    f"       Rode migracao_chunks.sql no SQL Editor do Supabase.\n"
                    f"       Detalhe: {mensagem}"
                )
            raise
        print(f"[chunks] {min(inicio + TAMANHO_LOTE, len(linhas))}/{len(linhas)} gravados")


# ---------------------------------------------------------------------------
# Pipeline de um PDF
# ---------------------------------------------------------------------------
def preparar(
    caminho: Path, usar_ocr: bool, manter_referencias: bool
) -> tuple[str, dict, list[str]]:
    """PDF -> (texto limpo, metadados do PDF, chunks). Nao toca no banco."""
    paginas, meta = extrair_paginas(caminho, usar_ocr)
    meta["_paginas"] = len(paginas)

    # sem cabecalho/rodape, mas ainda com as quebras de linha originais:
    # e dai que o titulo e deduzido quando o PDF nao traz metadado bom.
    paginas_limpas = remover_cabecalhos_repetidos(paginas)
    meta["_primeira_pagina"] = paginas_limpas[0] if paginas_limpas else ""

    texto = limpar_texto("\n\n".join(paginas_limpas))
    if not manter_referencias:
        texto, cortou = cortar_referencias(texto)
        if cortou:
            print("[limpeza] secao de referencias removida")

    return texto, meta, dividir_em_chunks(texto)


def remover_artigo(supabase, article_id: str) -> None:
    """Apaga o artigo; os chunks somem junto pelo ON DELETE CASCADE."""
    supabase.table("articles").delete().eq("id", article_id).execute()
    print(f"[articles] artigo anterior removido (id={article_id})")


def ingerir(supabase, caminho: Path, args) -> None:
    """Ingesta um unico PDF: sources -> articles -> chunks."""
    print(f"\n=== {caminho.name} ===")

    # O hash sai direto dos bytes do arquivo: da para decidir se ja ingerimos
    # este PDF antes de pagar o custo de extrair e limpar o texto.
    sha256 = hashlib.sha256(caminho.read_bytes()).hexdigest()
    existente = None if args.dry_run else ja_ingerido(supabase, sha256)
    if existente and not args.reingerir:
        print(f"[pular] ja existe em articles (id={existente}). Use --reingerir para substituir.")
        return

    texto, meta, chunks = preparar(caminho, args.ocr, args.manter_referencias)

    if not texto.strip():
        print(
            "[aviso] nenhum texto extraido — provavelmente e um PDF digitalizado. "
            "Repita com --ocr. Pulando."
        )
        return
    if not chunks:
        print("[aviso] texto curto demais para gerar fragmentos. Pulando.")
        return

    externo = args.metadados.get(caminho.name, {})
    titulo = externo.get("title") or deduzir_titulo(meta, meta.get("_primeira_pagina", ""), caminho)
    metadados = extrair_metadados(meta, texto, caminho, sha256)
    # o que veio da base bibliografica sobrescreve o que foi inferido do PDF
    for chave in ("doi", "revista", "openalex", "palavras_chave"):
        if externo.get(chave):
            metadados[chave] = externo[chave]
    print(f"[texto] {len(texto)} caracteres, {len(chunks)} fragmentos")
    print(f"[titulo] {titulo[:100]}")
    if metadados.get("doi"):
        print(f"[doi] {metadados['doi']}")

    if args.dry_run:
        print("[dry-run] nada foi gravado. Primeiro fragmento:")
        print("  " + chunks[0][:300].replace("\n", " ") + "...")
        return

    # Embeddings ANTES de gravar: se o modelo falhar, nao deixamos para tras um
    # artigo orfao em `articles` sem nenhum chunk correspondente.
    print(f"[embeddings] gerando {len(chunks)} vetores de {DIMENSAO} dims...")
    embeddings = gerar_embeddings(chunks)

    if existente:
        remover_artigo(supabase, existente)

    source_id = obter_ou_criar_fonte(supabase, args.fonte, args.tipo, args.reliability)

    registro = {
        "source_id": source_id,
        "title": titulo,
        "content": texto,
        "url": externo.get("url") or args.url,
        "author": externo.get("author") or (meta.get("author") or "").strip() or None,
        "published_at": externo.get("published_at") or _data_do_pdf(meta.get("creationDate")),
        "collected_at": datetime.now(UTC).isoformat(),
        "content_type": "article",
        "label": args.label,
        "labeled_by": args.rotulado_por,
        "language": args.idioma,
        "metadata": metadados,
    }
    artigo = supabase.table("articles").insert(registro).execute()
    article_id = artigo.data[0]["id"]
    print(f"[articles] inserido id={article_id}")

    try:
        gravar_chunks(supabase, article_id, chunks, embeddings)
    except Exception:
        # sem os chunks o artigo nao serve para RAG; desfazemos para o banco
        # nunca ficar num estado meio gravado.
        print("[rollback] falha ao gravar os chunks — removendo o artigo inserido")
        remover_artigo(supabase, article_id)
        raise
    print("[ok] concluido")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def carregar_metadados_externos(caminho: Path | None) -> dict[str, dict]:
    """Le um JSON opcional com metadados confiaveis por arquivo.

    Formato: {"artigo.pdf": {"title": ..., "author": ..., "doi": ...,
              "url": ..., "published_at": "2023-01-01", "revista": ...}}

    Serve para quando ja temos os metadados de uma base bibliografica
    (OpenAlex, Crossref, SciELO): eles valem mais do que qualquer heuristica
    sobre o PDF, cujo campo `title` costuma trazer o nome do arquivo de
    diagramacao em vez do titulo do artigo.
    """
    if caminho is None:
        return {}
    if not caminho.exists():
        sys.exit(f"[erro] arquivo de metadados nao encontrado: {caminho}")
    with caminho.open(encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    print(f"[metadados] {len(dados)} entradas lidas de {caminho.name}")
    return dados


def coletar_pdfs(caminhos: list[Path]) -> list[Path]:
    """Expande diretorios em arquivos .pdf, ordenados e sem repeticao."""
    encontrados: list[Path] = []
    for caminho in caminhos:
        if caminho.is_dir():
            encontrados.extend(sorted(caminho.rglob("*.pdf")))
        elif caminho.suffix.lower() == ".pdf":
            encontrados.append(caminho)
        else:
            print(f"[aviso] ignorando (nao e .pdf nem pasta): {caminho}")
    return list(dict.fromkeys(encontrados))


def main() -> None:
    global DISPOSITIVO

    parser = argparse.ArgumentParser(
        description="Ingesta PDFs de artigos no Supabase (execucao 100% local).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Uso:")[-1],
    )
    parser.add_argument("pdfs", nargs="+", type=Path, help="Arquivos .pdf e/ou pastas")
    parser.add_argument("--fonte", required=True, help="Nome da fonte (ex: 'Web of Science')")
    parser.add_argument(
        "--tipo",
        default="scientific",
        choices=["scientific", "social_media", "news"],
        help="Tipo da fonte, enum source_type (padrao: scientific)",
    )
    parser.add_argument(
        "--reliability", type=int, default=90, help="Confiabilidade da fonte, 0-100 (padrao: 90)"
    )
    parser.add_argument(
        "--label",
        default="unlabeled",
        choices=["true", "fake", "misleading", "unlabeled"],
        help="Rotulo do conteudo, enum label_type (padrao: unlabeled)",
    )
    parser.add_argument("--rotulado-por", default=None, help="Preenche articles.labeled_by")
    parser.add_argument("--url", default=None, help="URL original do artigo (mesma para todos)")
    parser.add_argument("--idioma", default="pt-BR", help="articles.language (padrao: pt-BR)")
    parser.add_argument(
        "--metadados",
        type=Path,
        default=None,
        help="JSON com metadados confiaveis por arquivo (title, doi, url, published_at)",
    )
    parser.add_argument(
        "--device",
        default=DISPOSITIVO,
        help=f"Device do torch para os embeddings "
        f"(padrao: {DISPOSITIVO}; use cuda se a GPU suportar)",
    )
    parser.add_argument(
        "--ocr", action="store_true", help="Ativa OCR nas paginas sem texto (PDF digitalizado)"
    )
    parser.add_argument(
        "--manter-referencias",
        action="store_true",
        help="Nao corta a secao de referencias bibliograficas",
    )
    parser.add_argument(
        "--reingerir", action="store_true", help="Ingere de novo mesmo se o hash ja existir"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="So extrai e mostra o resultado, sem gravar nada"
    )
    args = parser.parse_args()
    DISPOSITIVO = args.device
    args.metadados = carregar_metadados_externos(args.metadados)

    arquivos = coletar_pdfs(args.pdfs)
    if not arquivos:
        sys.exit("[erro] nenhum PDF encontrado nos caminhos informados.")
    print(f"{len(arquivos)} PDF(s) para processar.")

    supabase = None
    if not args.dry_run:
        supabase = obter_supabase()
        verificar_schema(supabase)

    falhas = 0
    for caminho in arquivos:
        try:
            ingerir(supabase, caminho, args)
        except SystemExit:
            raise
        except Exception as erro:  # noqa: BLE001 — script local: registrar e seguir
            falhas += 1
            print(f"[erro] falha em {caminho.name}: {type(erro).__name__}: {erro}")

    print(f"\nConcluido. {len(arquivos) - falhas}/{len(arquivos)} processados sem erro.")


if __name__ == "__main__":
    main()
