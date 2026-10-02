import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import requests
from supabase import create_client

sys.path.append(str(Path(__file__).resolve().parent.parent))
from ingerir_pdf import dividir_em_chunks, gerar_embeddings, gravar_chunks


def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print(
            "Erro: SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY "
            "(ou SUPABASE_KEY) devem estar definidos."
        )
        exit(1)
    url = url.strip().rstrip("/").removesuffix("/rest/v1")
    return create_client(url, key)


def get_or_create_source(supabase, name="PubMed", type_="scientific", reliability=100):
    try:
        res = supabase.table("sources").select("id").eq("name", name).limit(1).execute()
        if res.data:
            return res.data[0]["id"]
        res = (
            supabase.table("sources")
            .insert({"name": name, "type": type_, "reliability": reliability})
            .execute()
        )
        return res.data[0]["id"]
    except Exception as e:
        print(f"Erro ao obter/criar fonte no Supabase: {e}")
        exit(1)


def parse_pubmed_date(article):
    year_elem = article.find(".//PubDate/Year")
    month_elem = article.find(".//PubDate/Month")
    day_elem = article.find(".//PubDate/Day")

    year = year_elem.text if year_elem is not None else "2023"
    month_str = month_elem.text if month_elem is not None else "01"
    day = day_elem.text if day_elem is not None else "01"

    if not month_str.isdigit():
        month_map = {
            "Jan": "01",
            "Feb": "02",
            "Mar": "03",
            "Apr": "04",
            "May": "05",
            "Jun": "06",
            "Jul": "07",
            "Aug": "08",
            "Sep": "09",
            "Oct": "10",
            "Nov": "11",
            "Dec": "12",
        }
        month = month_map.get(month_str[:3].capitalize(), "01")
    else:
        month = month_str.zfill(2)

    day = day.zfill(2)
    return f"{year}-{month}-{day}T00:00:00Z"


def main():
    print("Iniciando scraper do PubMed...")
    supabase = get_supabase_client()
    source_id = get_or_create_source(supabase)

    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": '("nutrition"[MeSH Terms] OR "physical fitness"[MeSH Terms]) AND (y_5[Filter])',
        "retmode": "json",
        "retmax": 5000,
    }

    try:
        response = requests.get(search_url, params=search_params, timeout=10)
        response.raise_for_status()
        id_list = response.json().get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"Erro ao buscar IDs no PubMed: {e}")
        exit(1)

    if not id_list:
        print("Nenhum artigo encontrado.")
        exit(0)

    print(f"Encontrados {len(id_list)} artigos recentes. Buscando detalhes...")

    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    batch_size = 50
    inserted_count = 0

    print(f"Processando em lotes de {batch_size} artigos com sistema de retries...")

    for i in range(0, len(id_list), batch_size):
        batch_ids = id_list[i : i + batch_size]
        fetch_params = {"db": "pubmed", "id": ",".join(batch_ids), "retmode": "xml"}

        root = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                fetch_response = requests.post(fetch_url, data=fetch_params, timeout=30)
                fetch_response.raise_for_status()
                root = ET.fromstring(fetch_response.text)
                break  # Sucesso, sai do loop de tentativas
            except requests.exceptions.RequestException as e:
                print(
                    f"Aviso: Falha no lote {i // batch_size + 1} "
                    f"(tentativa {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff (1s, 2s)
                else:
                    print(
                        f"Erro ao buscar detalhes do lote {i // batch_size + 1} "
                        "após várias tentativas. Pulando."
                    )
            except Exception as e:
                print(f"Erro inesperado no lote {i // batch_size + 1}: {e}")
                break

        if root is None:
            continue

        for article in root.findall(".//PubmedArticle"):
            try:
                # Título
                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else "Sem título"

                # Resumo (Abstract)
                abstract_parts = []
                for abstract_text in article.findall(".//AbstractText"):
                    if abstract_text.text:
                        abstract_parts.append(abstract_text.text)
                abstract = "\n".join(abstract_parts).strip()

                if not abstract:
                    continue  # Ignorar artigos sem abstract

                # Identificadores (DOI, PMID)
                doi = None
                for el in article.findall(".//ArticleId"):
                    if el.get("IdType") == "doi":
                        doi = el.text
                        break

                pmid_elem = article.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else None

                url = (
                    f"https://doi.org/{doi}"
                    if doi
                    else (f"https://pubmed.ncbi.nlm.nih.gov/{pmid}" if pmid else "")
                )
                if not url:
                    continue

                # Checar se já existe no banco
                if doi:
                    exists = (
                        supabase.table("articles")
                        .select("id")
                        .eq("metadata->>doi", doi)
                        .limit(1)
                        .execute()
                    )
                    if exists.data:
                        continue
                else:
                    exists = (
                        supabase.table("articles").select("id").eq("url", url).limit(1).execute()
                    )
                    if exists.data:
                        continue

                published_at = parse_pubmed_date(article)

                author_list = []
                for author in article.findall(".//Author"):
                    last = author.find("LastName")
                    first = author.find("ForeName")
                    if last is not None and first is not None:
                        author_list.append(f"{first.text} {last.text}")
                author_str = ", ".join(author_list) if author_list else None

                data = {
                    "source_id": source_id,
                    "title": title[:300],
                    "content": abstract,
                    "url": url,
                    "author": author_str,
                    "published_at": published_at,
                    "collected_at": datetime.now(UTC).isoformat(),
                    "content_type": "article",
                    "label": "unlabeled",
                    "language": "en",
                    "metadata": {"doi": doi, "pmid": pmid},
                }

                artigo = supabase.table("articles").insert(data).execute()
                article_id = artigo.data[0]["id"]

                chunks = dividir_em_chunks(abstract)
                if chunks:
                    embeddings = gerar_embeddings(chunks)
                    gravar_chunks(supabase, article_id, chunks, embeddings)

                inserted_count += 1

            except Exception as e:
                print(f"Erro ao processar artigo {pmid}: {e}")

        # Respeitar rate limit da API entre cada lote
        time.sleep(1)

    print(f"Sucesso: Inseridos {inserted_count} artigos")


if __name__ == "__main__":
    main()
