/**
 * Cliente da API.
 *
 * Todo acesso a rede passa por aqui, por dois motivos: o token vai em um lugar so, e
 * todo erro chega na tela como `ErroDaApi` com um codigo do contrato, nunca como um
 * `fetch` cru que cada tela trata de um jeito diferente.
 *
 * As telas NAO devem chamar `fetch` direto. Se precisar de um endpoint novo, adicione
 * a funcao aqui e o tipo em `tipos.ts`.
 */

import type {
  CodigoDeErro,
  CorpoDeErro,
  PedidoDeChecagem,
  PedidoDeFeedback,
  Perfil,
  RespostaDeChecagem,
  RespostaDeFeedback,
} from './tipos';

const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';
const PREFIXO = '/api/v1';

/** Erro com codigo do contrato. Toda tela pode confiar nesse formato. */
export class ErroDaApi extends Error {
  readonly codigo: CodigoDeErro;
  readonly status: number;
  readonly detalhe?: string;
  /** Segundos ate poder tentar de novo. So vem em `rate_limited`. */
  readonly tentarEm?: number;

  constructor(codigo: CodigoDeErro, status: number, detalhe?: string, tentarEm?: number) {
    super(detalhe ?? codigo);
    this.name = 'ErroDaApi';
    this.codigo = codigo;
    this.status = status;
    this.detalhe = detalhe;
    this.tentarEm = tentarEm;
  }
}

/**
 * Texto pronto para a tela, por codigo de erro.
 *
 * Fica aqui de proposito: a mensagem precisa ser a mesma em qualquer tela, e a regra de
 * escrita esta no design system (Docs/Design/design-system.md, secao 7). Diz o que houve
 * e o que fazer, sem pedir desculpa e sem "Ops".
 */
export const MENSAGEM_DE_ERRO: Record<CodigoDeErro, string> = {
  invalid_input: 'Escreva a dúvida, cole um link ou envie um print para eu checar.',
  // A API recusa print e link desde o PR #15, de propósito: responder sem conseguir ler
  // o conteúdo daria veredito confiante sobre o assunto errado. Enquanto OCR e leitura
  // de página não existem, a tela diz o que dá para fazer agora.
  input_nao_suportado:
    'Ainda não consigo ler print nem link. Escreva a dúvida com suas palavras que eu checo.',
  // Enquanto a conta nao existe, nao da para pedir "entre de novo": nao ha onde entrar.
  // Troque este texto junto com a issue da sessao anonima.
  unauthorized: 'Não consegui confirmar sua sessão. Feche e abra o app para tentar de novo.',
  payload_too_large:
    'Esse print passou de 5 MB mesmo depois de reduzir. Corte a parte que interessa e envie de novo.',
  rate_limited: 'Muitas checagens seguidas. Aguarde um instante para checar de novo.',
  upstream_unavailable:
    'Não consegui terminar a checagem agora. Sua dúvida continua aqui, tente de novo em alguns minutos.',
  profile_not_found: 'Você ainda não preencheu o perfil de saúde.',
  sem_conexao: 'Você está sem internet. Eu checo assim que a conexão voltar.',
  desconhecido: 'Algo saiu diferente do esperado aqui do meu lado. Tente de novo.',
};

/** Token da sessao. Enquanto o login anonimo nao existe, o app usa um valor de teste. */
let token: string | null = null;

export function definirToken(novo: string | null): void {
  token = novo;
}

async function requisitar<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  let resposta: Response;

  try {
    resposta = await fetch(`${BASE}${PREFIXO}${caminho}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  } catch (falha) {
    // Cancelamento nao e erro de rede: quem cancelou foi a própria tela, e ela sabe o
    // que fazer. Repassamos para o chamador distinguir.
    if (falha instanceof DOMException && falha.name === 'AbortError') throw falha;
    // Falha de rede nao tem status nem corpo: e o caso de estar sem internet.
    throw new ErroDaApi('sem_conexao', 0);
  }

  if (resposta.status === 204) return undefined as T;

  const corpo = await resposta.json().catch(() => null);

  if (!resposta.ok) {
    const erro = (corpo ?? {}) as CorpoDeErro;
    const codigo: CodigoDeErro = erro.error ?? 'desconhecido';
    const cabecalho = resposta.headers.get('Retry-After');
    const tentarEm = erro.retry_after ?? (cabecalho ? Number(cabecalho) : undefined);
    throw new ErroDaApi(codigo, resposta.status, erro.detail, tentarEm);
  }

  return corpo as T;
}

/**
 * Checa a alegação. Passe `sinal` de um AbortController para poder cancelar: sem isso, a
 * resposta chega depois de a pessoa desistir, entra no histórico e a leva para uma tela
 * que ela não pediu.
 */
export function checarAlegacao(
  pedido: PedidoDeChecagem,
  sinal?: AbortSignal,
): Promise<RespostaDeChecagem> {
  return requisitar<RespostaDeChecagem>('/check-claim', {
    method: 'POST',
    body: JSON.stringify({ use_profile: true, ...pedido }),
    signal: sinal,
  });
}

export function enviarFeedback(pedido: PedidoDeFeedback): Promise<RespostaDeFeedback> {
  return requisitar<RespostaDeFeedback>('/feedback', {
    method: 'POST',
    body: JSON.stringify(pedido),
  });
}

/** Devolve `null` quando a pessoa ainda nao preencheu o perfil, em vez de estourar. */
export async function obterPerfil(): Promise<Perfil | null> {
  try {
    return await requisitar<Perfil>('/profile');
  } catch (erro) {
    if (erro instanceof ErroDaApi && erro.codigo === 'profile_not_found') return null;
    throw erro;
  }
}

export function salvarPerfil(perfil: Perfil): Promise<Perfil> {
  return requisitar<Perfil>('/profile', {
    method: 'PUT',
    body: JSON.stringify(perfil),
  });
}
