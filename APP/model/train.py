"""Treinamento do Classificador de Risco Nutricional utilizando dados do Supabase.

Baseado em:
- Docs/Model/01_metricas_e_avaliacao.md (F2-Score, Recall > 0.95, Platt Scaling)
- Docs/Data/02_armazenamento_e_estrutura.md (Corpus de artigos cientificos)
"""

import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, fbeta_score, recall_score
from sklearn.model_selection import StratifiedKFold

from APP.model.database import obter_supabase
from APP.model.embeddings import gerar_embedding_consulta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("treinamento_classificador")

CAMINHO_MODELO = Path(__file__).parent / "classificador_risco.joblib"


def extrair_dados_do_banco():
    """Consulta o Supabase e extrai amostras de treino a partir dos artigos e chunks."""
    logger.info("Conectando ao Supabase para carregar o corpus...")
    supabase = obter_supabase()

    artigos = supabase.table("articles").select("id, title, content_type, metadata").execute().data
    logger.info(f"Total de artigos identificados no Supabase: {len(artigos)}")

    # Mapeamento tematico das evidencias catalogadas no banco
    # Categoria 1 (Risco / Desinformacao / Pratica Nociva):
    # Artigos que analisam mitos de internet, infodemia, terrorismo nutricional e revistas
    palavras_chave_risco = [
        "desinformação",
        "infodemia",
        "terrorismo nutricional",
        "dietas da moda",
        "magazine",
        "instagram",
        "facebook",
        "influenciadores",
        "formulações emagrecedoras",
        "suplementos",
        "gordofobia",
    ]

    # Categoria 1 (Cautela / Inconclusivo):
    # Artigos sobre dietas restritivas e low carb
    palavras_chave_cautela = [
        "low carb",
        "low-carb",
        "restrição alimentar",
        "dietas restritivas",
        "alimentos funcionais",
    ]

    # Categoria 0 (Seguro / Consenso Cientifico / Fatores Protetores):
    # Artigos de reeducacao alimentar, dieta flexivel, comensalidade e protecao
    palavras_chave_seguro = [
        "dieta flexível",
        "reeducação alimentar",
        "habilidades sociais",
        "intervenção",
        "saúde mental",
        "treinamento de força",
        "modelo transteórico",
    ]

    exemplos = []

    for art in artigos:
        titulo = art.get("title", "")
        titulo_lower = titulo.lower()
        art_id = art["id"]

        # Determina a classe de risco com base no tema de estudo catalogado
        if any(p in titulo_lower for p in palavras_chave_risco):
            classe = 1  # Risco / Mito estudado
            categoria = "desinformacao"
        elif any(p in titulo_lower for p in palavras_chave_cautela):
            classe = 1  # Cautela / Risco moderado
            categoria = "cautela"
        elif any(p in titulo_lower for p in palavras_chave_seguro):
            classe = 0  # Seguro / Consenso favoravel
            categoria = "seguro"
        else:
            # Demais artigos sobre transtornos alimentares e riscos
            classe = 1
            categoria = "risco_transtorno"

        # Busca fragmentos (chunks) do artigo no Supabase
        chunks = (
            supabase.table("chunks")
            .select("chunk_index, content")
            .eq("article_id", art_id)
            .limit(5)
            .execute()
            .data
        )

        for c in chunks:
            conteudo = c.get("content", "").strip()
            # Seleciona trechos representativos com tamanho suficiente
            if len(conteudo) > 120:
                trecho = conteudo[:400].replace("\n", " ")
                exemplos.append(
                    {
                        "texto": trecho,
                        "classe": classe,
                        "categoria": categoria,
                        "titulo_artigo": titulo,
                    }
                )

    logger.info(f"Total de fragmentos científicos extraídos do Supabase: {len(exemplos)}")
    return exemplos


def treinar():
    logger.info("Iniciando processo de treinamento...")
    dados = extrair_dados_do_banco()

    textos = [d["texto"] for d in dados]
    y = np.array([d["classe"] for d in dados])

    logger.info(f"Distribuicao das classes: {np.bincount(y)} (0: Seguro, 1: Risco/Alerta)")
    logger.info("Gerando embeddings de 768 dimensoes via multilingual-e5-base...")

    X = []
    for i, t in enumerate(textos):
        if i % 50 == 0:
            logger.info(f"Vetorizando amostra {i}/{len(textos)}...")
        vetor = gerar_embedding_consulta(t)
        X.append(vetor)

    X = np.array(X)
    logger.info(f"Matriz de features gerada: shape {X.shape}")

    # Validacao Cruzada Estratificada (5 Folds)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    recalls = []
    f2_scores = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        # Regressao Logistica com regularizacao L2 e pesos sensiveis ao custo (Elkan, 2001)
        # O custo de FN e maior que FP, entao damos maior peso para a classe positiva (1)
        base_clf = LogisticRegression(
            C=1.0,
            class_weight="balanced",
            max_iter=1000,
            random_state=42,
        )
        # Calibracao de probabilidades via Platt Scaling (metodo sigmoid) com cv=3
        calibrador = CalibratedClassifierCV(estimator=base_clf, method="sigmoid", cv=3)
        calibrador.fit(X_tr, y_tr)

        probs_val = calibrador.predict_proba(X_val)[:, 1]
        # Limiar de decisao calibrado de 0.35 (Docs/Model/01, secao 4.2)
        preds_val = (probs_val >= 0.35).astype(int)

        rec = recall_score(y_val, preds_val, zero_division=0)
        f2 = fbeta_score(y_val, preds_val, beta=2, zero_division=0)
        recalls.append(rec)
        f2_scores.append(f2)
        logger.info(f"Fold {fold}: Recall={rec:.4f} | F2-Score={f2:.4f}")

    logger.info(f"Media Validacao Cruzada - Recall: {np.mean(recalls):.4f}")
    logger.info(f"Media Validacao Cruzada - F2-Score: {np.mean(f2_scores):.4f}")

    # Treinamento final sobre todo o conjunto de evidencias do banco
    modelo_final_base = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=1000,
        random_state=42,
    )
    modelo_final_base.fit(X, y)

    modelo_calibrado = CalibratedClassifierCV(estimator=modelo_final_base, method="sigmoid", cv=5)
    modelo_calibrado.fit(X, y)

    probs_treino = modelo_calibrado.predict_proba(X)[:, 1]
    preds_treino = (probs_treino >= 0.35).astype(int)
    print("\n" + "=" * 60)
    print("RELATÓRIO DE TREINAMENTO SOBRE O CORPUS DO SUPABASE")
    print("=" * 60)
    print(classification_report(y, preds_treino, target_names=["Seguro (0)", "Risco/Mito (1)"]))

    # Salva o artefato do modelo
    joblib.dump(modelo_calibrado, CAMINHO_MODELO)
    logger.info(f"Modelo treinado e calibrado salvo com sucesso em: {CAMINHO_MODELO}")


if __name__ == "__main__":
    treinar()
