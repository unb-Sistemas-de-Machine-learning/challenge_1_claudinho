/**
 * Tema claro e escuro.
 *
 * Tres estados, nao dois: claro explicito, escuro explicito e automatico. No automatico
 * o atributo sai do HTML e o `prefers-color-scheme` do sistema volta a mandar. A troca
 * dos tokens esta em estilos/claudinho.css.
 */

import { gravar, ler } from './armazenamento';

export type Tema = 'auto' | 'light' | 'dark';

export function aplicarTema(tema: Tema): void {
  if (tema === 'auto') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.setAttribute('data-theme', tema);
}

export function definirTema(tema: Tema): void {
  gravar('tema', tema);
  aplicarTema(tema);
}

export function iniciarTema(): Tema {
  const tema = ler('tema');
  aplicarTema(tema);
  return tema;
}
