/**
 * O que o app guarda no aparelho.
 *
 * Decisao de produto (Docs/Design/design-system.md, secao 8): dá para usar sem conta, e
 * enquanto nao houver conta o historico e o perfil vivem so aqui. Toda leitura tolera
 * armazenamento bloqueado (aba anonima, cookies desligados) devolvendo o padrao.
 */

import type { Perfil, RespostaDeChecagem } from './api/tipos';

const PREFIXO = 'claudinho:';

export interface ItemDoHistorico {
  /**
   * Identificador da entrada no histórico.
   *
   * Não use o `trace_id` para isso: o contrato tem `cached`, e uma resposta vinda do
   * cache semântico repete o mesmo `trace_id`. Duas checagens iguais colidiriam, e a
   * mais antiga ficaria inalcançável.
   */
  id: string;
  /** Quando a checagem foi feita, em epoch ms. */
  em: number;
  /** O que a pessoa mandou, do jeito que ela mandou. */
  entrada: string;
  /** De onde veio: link colado ou print enviado. Texto puro não tem origem. */
  origem?: { tipo: 'url'; valor: string } | { tipo: 'imagem'; src: string };
  resposta: RespostaDeChecagem;
}

export interface EstadoLocal {
  onboarded: boolean;
  /** O que a pessoa escreveu e ainda não virou checagem. Sobrevive a erro e a cancelamento. */
  rascunho: string;
  instalacaoDispensada: boolean;
  tema: 'auto' | 'light' | 'dark';
  historico: ItemDoHistorico[];
  perfil: Perfil | null;
  usarPerfil: boolean;
}

export const PADRAO: EstadoLocal = {
  onboarded: false,
  rascunho: '',
  instalacaoDispensada: false,
  tema: 'auto',
  historico: [],
  perfil: null,
  usarPerfil: true,
};

export function ler<C extends keyof EstadoLocal>(chave: C): EstadoLocal[C] {
  try {
    const bruto = localStorage.getItem(PREFIXO + chave);
    return bruto === null ? PADRAO[chave] : (JSON.parse(bruto) as EstadoLocal[C]);
  } catch {
    return PADRAO[chave];
  }
}

export function gravar<C extends keyof EstadoLocal>(chave: C, valor: EstadoLocal[C]): void {
  try {
    localStorage.setItem(PREFIXO + chave, JSON.stringify(valor));
  } catch {
    // Sem armazenamento o app continua funcionando, so nao lembra da proxima vez.
  }
}

export function limparTudo(): void {
  for (const chave of Object.keys(PADRAO)) {
    try {
      localStorage.removeItem(PREFIXO + chave);
    } catch {
      /* idem */
    }
  }
}

/** Guarda a checagem no topo do historico, com teto para nao crescer sem fim. */
export function registrarNoHistorico(
  item: Omit<ItemDoHistorico, 'id'>,
  teto = 50,
): ItemDoHistorico {
  const completo: ItemDoHistorico = { id: crypto.randomUUID(), ...item };
  gravar('historico', [completo, ...ler('historico')].slice(0, teto));
  return completo;
}
