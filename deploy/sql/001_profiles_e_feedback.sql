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

<<<<<<< HEAD
=======
-- Expurgo automatico (docs/Ethics/02, secao 4): dado de saude de quem nao acessa ha 6
-- meses e apagado. `updated_at` e tocado a cada gravacao do perfil, entao ele marca o
-- ultimo acesso que mexeu no dado.
--
-- Apaga a LINHA inteira, e nao so as condicoes: sexo, altura, peso e data de nascimento,
-- juntos, tambem identificam uma pessoa. Anonimizar pela metade nao cumpriria a politica.
create or replace function public.expurgar_perfis_inativos()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  apagados integer;
begin
  delete from public.profiles where updated_at < now() - interval '6 months';
  get diagnostics apagados = row_count;
  return apagados;
end;
$$;

-- Agendamento diario. Requer a extensao pg_cron (Supabase: Database > Extensions).
-- Se ela nao estiver disponivel no plano, rode a funcao pela interface uma vez por mes:
--   select public.expurgar_perfis_inativos();
-- create extension if not exists pg_cron;
-- select cron.schedule('expurgo-perfis', '0 5 * * *', 'select public.expurgar_perfis_inativos()');

>>>>>>> e6fca9eb28e76e5a91ee68fe4e916c33c9b1d9d8
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
<<<<<<< HEAD
=======
-- Esta policy e o que sustenta o DELETE /api/v1/profile: a exclusao a pedido da pessoa,
-- prevista na mesma secao 4 do docs/Ethics/02.
>>>>>>> e6fca9eb28e76e5a91ee68fe4e916c33c9b1d9d8

-- Feedback: qualquer usuario logado registra o seu; a leitura fica para o time, pelo
-- painel do Supabase (service_role ignora RLS).
create policy "usuario logado registra feedback"
  on public.feedback for insert with check (auth.uid() = user_id);
