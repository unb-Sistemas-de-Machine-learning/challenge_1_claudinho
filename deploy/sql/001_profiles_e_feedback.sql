-- Tabelas `profiles` e `feedback` (issues #19, #22 do front e o loop de feedback do
-- Docs/Production/02, secao 4). Rode no Supabase em SQL Editor > New query.
--
-- Schema derivado dos contratos das secoes 2.2 e 2.3 do Docs/Production/01 e do plano
-- que ja estava nos docstrings de APP/repositorios/. Precisa do aval da frente de Dados
-- (schema) e da frente de Etica (prazo de expurgo do dado de saude).

create table if not exists public.profiles (
  user_id              uuid primary key references auth.users(id) on delete cascade,
  sex                  text check (sex in ('F','M','outro','nao_informado')),
  birth_date           date,
  height_cm            int  check (height_cm between 50 and 250),
  weight_kg            numeric check (weight_kg between 20 and 400),
  conditions           text[] not null default '{}',
  dietary_restrictions text[] not null default '{}',
  routine              text check (routine in ('sedentaria','leve','moderada','intensa')),
  consent_health_data  boolean not null default false,
  updated_at           timestamptz not null default now()
);

create table if not exists public.feedback (
  id           uuid primary key default gen_random_uuid(),
  -- Sem FK de proposito: nao existe tabela de execucoes; o trace vive no log estruturado.
  trace_id     uuid not null,
  user_id      uuid references auth.users(id) on delete set null,
  rating       text not null check (rating in ('up','down')),
  reason       text check (reason in ('fonte_irrelevante','resposta_confusa','parece_errado',
                                      'tom_julgador','nao_respondeu','outro')),
  comment      text,
  created_at   timestamptz not null default now(),
  triaged_at   timestamptz,
  triage_notes text
);
create index if not exists feedback_recentes on public.feedback (created_at desc);
create index if not exists feedback_por_motivo on public.feedback (rating, reason);

-- RLS: sem isto, qualquer usuario autenticado le a condicao clinica dos outros.
alter table public.profiles enable row level security;
alter table public.feedback enable row level security;

create policy "cada um le o proprio perfil"
  on public.profiles for select using (auth.uid() = user_id);
create policy "cada um escreve o proprio perfil"
  on public.profiles for insert with check (auth.uid() = user_id);
create policy "cada um atualiza o proprio perfil"
  on public.profiles for update using (auth.uid() = user_id);
create policy "cada um apaga o proprio perfil"
  on public.profiles for delete using (auth.uid() = user_id);

-- Feedback: qualquer usuario logado registra o seu; a leitura fica para o time, pelo
-- painel do Supabase (service_role ignora RLS).
create policy "usuario logado registra feedback"
  on public.feedback for insert with check (auth.uid() = user_id);
