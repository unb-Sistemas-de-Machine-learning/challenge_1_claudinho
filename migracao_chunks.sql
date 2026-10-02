-- Migracao necessaria antes da primeira execucao do ingerir_pdf.py.
-- Rode no SQL Editor do Supabase (projeto do Challenge 1).
--
-- Por que: o schema original previa vector(1536) (dimensao dos embeddings da
-- OpenAI). Como decidimos usar embeddings LOCAIS e open source
-- (intfloat/multilingual-e5-base), a dimensao passa a ser 768.

create extension if not exists vector;

-- 1) Tabela de fragmentos para RAG (caso ainda nao exista).
create table if not exists public.chunks (
  id uuid not null default gen_random_uuid(),
  article_id uuid not null,
  chunk_index integer not null,
  content text not null,
  embedding vector(768),
  constraint chunks_pkey primary key (id),
  constraint chunks_article_id_fkey foreign key (article_id)
    references public.articles (id) on delete cascade,
  constraint chunks_article_index_unico unique (article_id, chunk_index)
);

-- 2) Se a tabela ja existia com vector(1536), realinha a dimensao.
--    ATENCAO: descarta os embeddings antigos (dimensoes incompativeis nao
--    podem ser convertidas). Rode so se ainda nao ha vetores que importem.
do $$
declare
  dimensao integer;
begin
  -- em pgvector, atttypmod guarda a dimensao declarada (-1 se nao declarada)
  select atttypmod into dimensao
  from pg_attribute
  where attrelid = 'public.chunks'::regclass
    and attname = 'embedding'
    and not attisdropped;

  if dimensao is not null and dimensao <> 768 then
    alter table public.chunks drop column embedding;
    alter table public.chunks add column embedding vector(768);
    raise notice 'chunks.embedding recriada como vector(768) (era vector(%))', dimensao;
  end if;
end $$;

-- 3) Indices.
create index if not exists chunks_article_id_idx on public.chunks (article_id);

--    Busca por similaridade de cosseno. Os vetores saem normalizados do script,
--    entao cosseno e produto interno dao a mesma ordem.
create index if not exists chunks_embedding_idx
  on public.chunks using hnsw (embedding vector_cosine_ops);

-- 4) Deduplicacao de artigos por hash do arquivo (usado por ingerir_pdf.py).
create index if not exists articles_sha256_idx
  on public.articles ((metadata ->> 'sha256'));

-- 5) Funcao de busca semantica, para a API consumir via RPC.
--
--    IMPORTANTE: por padrao a busca considera SO fontes cientificas. A tabela
--    `articles` guarda tanto o corpus de evidencia (artigos revisados por
--    pares) quanto o material a ser classificado (posts de redes sociais). Sem
--    esse filtro, o RAG poderia recuperar um post de desinformacao e apresenta-lo
--    como evidencia — o oposto do que o sistema deve fazer.
create or replace function public.buscar_chunks(
  consulta vector(768),
  limite integer default 5,
  similaridade_minima double precision default 0.0,
  apenas_cientificos boolean default true
)
returns table (
  chunk_id uuid,
  article_id uuid,
  titulo text,
  conteudo text,
  fonte text,
  confiabilidade integer,
  similaridade double precision
)
language sql stable
as $$
  select c.id, c.article_id, a.title, c.content, s.name, s.reliability,
         1 - (c.embedding <=> consulta) as similaridade
  from public.chunks c
  join public.articles a on a.id = c.article_id
  join public.sources s on s.id = a.source_id
  where 1 - (c.embedding <=> consulta) >= similaridade_minima
    and (not apenas_cientificos
         or (s.type = 'scientific' and a.content_type = 'article'))
  order by c.embedding <=> consulta
  limit limite;
$$;
