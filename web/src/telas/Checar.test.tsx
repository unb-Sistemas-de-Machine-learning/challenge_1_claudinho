/**
 * Tela de checagem: o que chega pelo compartilhar do Android (issue #27) e a base de
 * acessibilidade da tela (issue #28).
 */

import { render, screen } from '@testing-library/react';
import { StrictMode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { limparTudo } from '../lib/armazenamento';
import { Checar } from './Checar';

function abrirCom(busca: string) {
  window.history.replaceState({}, '', `/${busca}`);
  return render(
    <MemoryRouter>
      <Checar />
    </MemoryRouter>,
  );
}

beforeEach(() => limparTudo());
afterEach(() => window.history.replaceState({}, '', '/'));

describe('Checar: compartilhamento do Android', () => {
  it('traz o texto compartilhado já no campo', () => {
    abrirCom('?text=agua%20com%20limao%20emagrece');

    expect(screen.getByRole('textbox')).toHaveValue('agua com limao emagrece');
  });

  it('junta título, texto e link do post', () => {
    abrirCom('?title=Dica&text=jejum%20de%2024h&url=https://exemplo.com/post');

    expect(screen.getByRole('textbox')).toHaveValue('Dica jejum de 24h https://exemplo.com/post');
  });

  it('não repete o link quando vem no texto e na url', () => {
    const link = 'https://exemplo.com/post';
    abrirCom(`?text=${encodeURIComponent(link)}&url=${encodeURIComponent(link)}`);

    expect(screen.getByRole('textbox')).toHaveValue(link);
  });

  it('limpa a URL, para recarregar não reabrir o mesmo compartilhamento', () => {
    abrirCom('?text=detox%20funciona');

    expect(window.location.search).toBe('');
  });

  it('no StrictMode, o texto compartilhado não se perde na segunda chamada', () => {
    window.history.replaceState({}, '', '/?text=jejum%20seco');
    render(
      <StrictMode>
        <MemoryRouter>
          <Checar />
        </MemoryRouter>
      </StrictMode>,
    );

    expect(screen.getByRole('textbox')).toHaveValue('jejum seco');
  });

  it('sem compartilhamento, mantém o rascunho de antes', () => {
    abrirCom('');

    expect(screen.getByRole('textbox')).toHaveValue('');
  });
});

describe('Checar: acessibilidade', () => {
  it('todo botão tem nome acessível', () => {
    abrirCom('');

    for (const botao of screen.getAllByRole('button')) {
      expect(botao).toHaveAccessibleName();
    }
  });

  it('o campo de texto tem rótulo associado', () => {
    abrirCom('');

    expect(screen.getByRole('textbox')).toHaveAccessibleName();
  });
});
