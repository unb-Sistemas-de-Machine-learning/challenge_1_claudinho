-- RLS da base científica. Executado no SQL Editor do Supabase em 06/10/2026.
--
-- Antes disto, articles, chunks e sources estavam com RLS desligado. Com a chave pública
-- do Supabase embutida no app (sessão anônima, PR #60), qualquer visitante podia inserir
-- ou alterar trechos em chunks, e o RAG passaria a citar "estudos" falsos.
--
-- Leitura liberada para anon e authenticated: é conteúdo científico público, e assim a
-- busca funciona qualquer que seja a chave da API. Escrita só pela service_role (scraper
-- e ingestão), que ignora o RLS.

alter table public.articles enable row level security;
alter table public.chunks   enable row level security;
alter table public.sources  enable row level security;

create policy "leitura publica" on public.articles for select to anon, authenticated using (true);
create policy "leitura publica" on public.chunks   for select to anon, authenticated using (true);
create policy "leitura publica" on public.sources  for select to anon, authenticated using (true);
create policy "leitura publica" on public."TBCA"   for select to anon, authenticated using (true);
