# Article Scraper (PubMed)

Este serviço é um extrator automático (scraper) que busca artigos científicos recentes no PubMed sobre nutrição e saúde física ("nutrition" ou "physical fitness"), extrai os metadados e o abstract, e os insere na tabela `articles` do Supabase.

Ele foi desenhado para rodar via cron no GitHub Actions, garantindo que o banco de dados seja alimentado de forma contínua com novos conteúdos relevantes.

## Como utilizar localmente

1. Crie um ambiente virtual e instale as dependências a partir do `requirements.txt`:
   ```bash
   python -m venv .venv-scraper
   source .venv-scraper/bin/activate
   pip install -r requirements.txt
   ```

2. Configure as variáveis de ambiente. O script necessita da Service Role Key para ignorar as regras de RLS (Row Level Security) na inserção de dados.
   ```bash
   export SUPABASE_URL="https://<seu-projeto>.supabase.co"
   export SUPABASE_SERVICE_ROLE_KEY="<sua-service-role-key>"
   ```
   *Nota: Caso as variáveis estejam configuradas no `.env` do diretório `APP/`, você pode usar bibliotecas como `dotenv` para carregá-las, ou apenas exportar no terminal.*

3. Execute o script:
   ```bash
   python fetch_pubmed.py
   ```

## Automação via GitHub Actions

O projeto já contém um arquivo de workflow em `.github/workflows/article_scraper.yml`.
Ele está configurado para rodar no dia 1º de cada mês (ex: às 04:00 AM UTC).

Para que o workflow funcione corretamente, adicione os seguintes **Secrets** nas configurações do seu repositório no GitHub (Settings > Secrets and variables > Actions):
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

## Tratamento de Duplicações

O script verifica automaticamente o DOI (ou URL do PubMed) de cada artigo retornado. Caso o artigo já esteja na base, ele será ignorado, evitando erros de duplicidade ou registros repetidos no banco.
