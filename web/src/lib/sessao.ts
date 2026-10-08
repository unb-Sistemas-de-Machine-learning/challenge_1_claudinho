import { createClient, type SupabaseClient } from '@supabase/supabase-js';

import { definirToken } from './api/cliente';

/**
 * Sessão do usuário (issue #23).
 *
 * A API valida o JWT do Supabase: fora do ambiente local, nenhum token inventado passa.
 * Antes daqui o app mandava um `VITE_API_TOKEN` fixo, embutido no build — que funcionava
 * só contra a API em modo local e, em produção, devolveria 401 em toda chamada.
 *
 * O login é **anônimo**: a pessoa checa uma informação sem criar conta, que é a promessa
 * do produto. A sessão fica no navegador e sobrevive a recarregar a página, então o
 * histórico e o perfil continuam sendo dela no mesmo aparelho.
 *
 * `VITE_SUPABASE_ANON_KEY` é pública de propósito: ela identifica o projeto e só autoriza
 * o que as políticas do banco (RLS) permitirem. Não confundir com a `service_role`, essa
 * sim secreta e que nunca entra no front.
 */

let cliente: SupabaseClient | null = null;
let ouvindo = false;

export function clienteDoSupabase(): SupabaseClient | null {
  const url = import.meta.env.VITE_SUPABASE_URL;
  const chave = import.meta.env.VITE_SUPABASE_ANON_KEY;
  if (!url || !chave) return null;

  cliente ??= createClient(url, chave, {
    auth: { persistSession: true, autoRefreshToken: true },
  });
  return cliente;
}

/**
 * Garante uma sessão e entrega o token à camada de rede.
 *
 * Sem Supabase configurado (desenvolvimento com mock), cai no token de desenvolvimento,
 * que só a API em modo local aceita. É o que mantém o app funcionando offline.
 */
export async function iniciarSessao(): Promise<void> {
  const supabase = clienteDoSupabase();
  if (!supabase) {
    definirToken(import.meta.env.VITE_API_TOKEN ?? 'token-de-desenvolvimento');
    return;
  }

  // O token expira em cerca de uma hora e o SDK o renova sozinho. Ouvir o evento é o que
  // mantém a camada de rede com o token novo: sem isto, o app funcionaria por uma hora e
  // depois começaria a receber 401 sem motivo aparente. Registrado uma vez só: o `sair()`
  // chama esta função de novo, e cada chamada acumularia mais um ouvinte.
  if (!ouvindo) {
    ouvindo = true;
    supabase.auth.onAuthStateChange((_evento, sessao) => {
      definirToken(sessao?.access_token ?? null);
    });
  }

  try {
    const { data } = await supabase.auth.getSession();
    if (data.session) {
      definirToken(data.session.access_token);
      return;
    }

    const { data: nova, error } = await supabase.auth.signInAnonymously();
    // Sem sessão, a API responde 401 e a tela mostra a mensagem de sessão. Deixar o app
    // seguir mesmo assim é melhor do que uma tela branca: o histórico local continua lá.
    definirToken(error ? null : (nova.session?.access_token ?? null));
  } catch {
    // Rede caída ou SDK lançando em vez de devolver `error`: mesmo tratamento, a falha de
    // sessão nunca pode travar o app (issue #23).
    definirToken(null);
  }
}

/**
 * Entradas da tela de conta (Perfil e boas-vindas). Desligadas por dois motivos:
 *
 * 1. Para usuário anônimo, o Supabase só aceita senha depois de o e-mail ser confirmado:
 *    primeiro `updateUser({ email })`, a pessoa abre o link, e só então
 *    `updateUser({ password })`. O `criarConta` daqui ainda manda os dois de uma vez.
 * 2. Sem SMTP próprio, o Supabase só entrega e-mail para quem é da equipe do projeto, até
 *    2 por hora. Qualquer outra pessoa nunca receberia o link de confirmação.
 *
 * Religar exige os dois: SMTP configurado no painel e o fluxo em duas etapas.
 */
export const CONTA_DISPONIVEL = false;

/** Resultado das operações de conta: a tela só precisa saber se deu certo e o que dizer. */
export type ResultadoDaConta = { ok: true } | { ok: false; mensagem: string };

const MENSAGENS: Record<string, string> = {
  user_already_exists: 'Esse email já tem conta. Use "Entrar" para acessá-la.',
  email_exists: 'Esse email já tem conta. Use "Entrar" para acessá-la.',
  invalid_credentials: 'Email ou senha não conferem.',
  weak_password: 'A senha precisa ter pelo menos 8 caracteres.',
  over_email_send_rate_limit: 'Muitas tentativas seguidas. Espere um minuto e tente de novo.',
};

function traduzir(codigo: string | undefined, padrao: string): string {
  return (codigo && MENSAGENS[codigo]) || padrao;
}

/**
 * Transforma a sessão anônima em conta com email e senha (issue #24).
 *
 * `updateUser` promove o usuário anônimo em vez de criar outro: o id continua o mesmo,
 * então perfil de saúde e feedback já gravados continuam sendo dele. Criar uma conta nova
 * e depois "migrar" perderia esse vínculo.
 */
export async function criarConta(email: string, senha: string): Promise<ResultadoDaConta> {
  const supabase = clienteDoSupabase();
  if (!supabase) return { ok: false, mensagem: 'Conta indisponível neste ambiente.' };

  const { error } = await supabase.auth.updateUser({ email, password: senha });
  if (error) {
    return { ok: false, mensagem: traduzir(error.code, 'Não consegui criar a conta agora.') };
  }
  return { ok: true };
}

/**
 * Entra numa conta que já existe.
 *
 * Troca a sessão anônima pela da conta, então o que estava só no anônimo (perfil ainda
 * não vinculado) fica para trás — por isso a tela avisa antes.
 */
export async function entrar(email: string, senha: string): Promise<ResultadoDaConta> {
  const supabase = clienteDoSupabase();
  if (!supabase) return { ok: false, mensagem: 'Conta indisponível neste ambiente.' };

  const { error } = await supabase.auth.signInWithPassword({ email, password: senha });
  if (error) {
    return { ok: false, mensagem: traduzir(error.code, 'Não consegui entrar agora.') };
  }
  return { ok: true };
}

/** Volta para uma sessão anônima nova, para o aparelho não ficar logado. */
export async function sair(): Promise<void> {
  const supabase = clienteDoSupabase();
  if (!supabase) return;
  await supabase.auth.signOut();
  await iniciarSessao();
}

/** Email da conta, ou null quando a sessão é anônima. */
export async function emailDaConta(): Promise<string | null> {
  const supabase = clienteDoSupabase();
  if (!supabase) return null;
  const { data } = await supabase.auth.getUser();
  return data.user?.email ?? null;
}
