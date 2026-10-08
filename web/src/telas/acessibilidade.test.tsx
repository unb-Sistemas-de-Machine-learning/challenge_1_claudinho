/**
 * Passada de acessibilidade em todas as telas (issue #28).
 *
 * Três regras valem para qualquer tela e quebram o uso com leitor de tela quando falham:
 * todo controle precisa de nome acessível, todo campo precisa de rótulo associado, e cada
 * tela precisa de um título. Ícone decorativo tem que ficar escondido do leitor, senão ele
 * lê "imagem" no meio da frase.
 */

import { render, screen, within } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { limparTudo } from '../lib/armazenamento';
import * as sessao from '../lib/sessao';
import { BoasVindas } from './BoasVindas';
import { Checar } from './Checar';
import { Conta } from './Conta';
import { Historico } from './Historico';
import { Perfil } from './Perfil';
import { PerfilEdicao } from './PerfilEdicao';

const TELAS: [string, () => ReactElement][] = [
  ['Boas-vindas', () => <BoasVindas />],
  ['Checar', () => <Checar />],
  ['Histórico', () => <Historico />],
  ['Perfil', () => <Perfil />],
  ['Perfil: edição', () => <PerfilEdicao />],
  ['Conta', () => <Conta />],
];

function montar(tela: () => ReactElement) {
  return render(<MemoryRouter>{tela()}</MemoryRouter>);
}

beforeEach(() => {
  limparTudo();
  vi.spyOn(sessao, 'emailDaConta').mockResolvedValue(null);
});

afterEach(() => vi.restoreAllMocks());

describe('acessibilidade', () => {
  it.each(TELAS)('%s: todo botão e link tem nome acessível', async (_nome, tela) => {
    montar(tela);
    await screen.findAllByRole('button').catch(() => []);

    for (const controle of [...screen.queryAllByRole('button'), ...screen.queryAllByRole('link')]) {
      expect(controle).toHaveAccessibleName();
    }
  });

  it.each(TELAS)('%s: todo campo tem rótulo associado', async (_nome, tela) => {
    const { container } = montar(tela);
    await Promise.resolve();

    const campos = container.querySelectorAll('input, textarea, select');
    for (const campo of campos) {
      // `hidden` é o input de arquivo que o botão aciona: ele não é alcançado pelo leitor.
      if (campo.getAttribute('type') === 'file') continue;
      expect(campo).toHaveAccessibleName();
    }
  });

  it.each(TELAS)('%s: tem um título na tela', async (_nome, tela) => {
    const { container } = montar(tela);
    await Promise.resolve();

    const titulos = container.querySelectorAll('h1, h2, .topbar-title, .screen-title');
    expect(titulos.length).toBeGreaterThan(0);
  });

  it.each(TELAS)('%s: ícone decorativo fica escondido do leitor de tela', async (_nome, tela) => {
    const { container } = montar(tela);
    await Promise.resolve();

    for (const svg of container.querySelectorAll('svg')) {
      const dentroDeBotaoSemTexto = svg.closest('button, a');
      const rotulado =
        svg.getAttribute('aria-hidden') === 'true' ||
        svg.getAttribute('aria-label') ||
        (dentroDeBotaoSemTexto && within(dentroDeBotaoSemTexto as HTMLElement).queryByText(/\S/));
      expect(rotulado).toBeTruthy();
    }
  });
});
