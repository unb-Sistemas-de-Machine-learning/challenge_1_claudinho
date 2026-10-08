/**
 * Como cada veredito do contrato aparece na tela.
 *
 * Rotulo, icone e abertura da frase estao documentados em Docs/Design/design-system.md,
 * secao 6. Cor nunca e o unico sinal: todo veredito leva icone e rotulo escrito.
 */

import { CircleCheck, CircleX, HeartHandshake, Scale, SearchX } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import type { Veredito } from './api/tipos';

export interface ApresentacaoDoVeredito {
  rotulo: string;
  Icone: LucideIcon;
  /** Falso quando a tela nao mostra fontes nem botao de compartilhar. */
  mostraFontes: boolean;
  /**
   * A frase grande que abre a resposta.
   *
   * O contrato devolve só `answer`, sem separar manchete de corpo, e cortar a primeira
   * frase da resposta gerava manchete de 20 palavras, que é o oposto do princípio 1 do
   * design system. Até a API devolver o campo, a abertura é fixa por veredito, na forma
   * que a seção 6 define. Ver a pendência 7 em Docs/Design/design-system.md.
   */
  aberturaDaFrase: string;
}

export const VEREDITOS: Record<Veredito, ApresentacaoDoVeredito> = {
  seguro: {
    rotulo: 'Tem base científica',
    Icone: CircleCheck,
    mostraFontes: true,
    aberturaDaFrase: 'Pode confiar: isso tem base científica.',
  },
  cautela: {
    rotulo: 'Depende',
    Icone: Scale,
    mostraFontes: true,
    aberturaDaFrase: 'Depende, e a ciência ainda não fechou essa conta.',
  },
  desinformacao: {
    rotulo: 'É mito',
    Icone: CircleX,
    mostraFontes: true,
    aberturaDaFrase: 'Pode respirar: isso é mito.',
  },
  sem_evidencia: {
    rotulo: 'Faltam estudos',
    Icone: SearchX,
    mostraFontes: true,
    aberturaDaFrase: 'Ainda não achei estudos suficientes para te responder.',
  },
  recusa_segura: {
    rotulo: 'Resposta de cuidado',
    Icone: HeartHandshake,
    mostraFontes: false,
    aberturaDaFrase: 'Essa eu não vou responder, porque pode te fazer mal.',
  },
};
