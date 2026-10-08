/**
 * Exemplo de teste de tela.
 *
 * Testa o que a pessoa vê e faz, não o estado interno: o botão só libera depois da
 * confirmação de 18 anos, que é exigência da Docs/Ethics/03, secao 2.2.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ler } from '../lib/armazenamento';
import { BoasVindas } from './BoasVindas';

function montar() {
  return render(
    <MemoryRouter>
      <BoasVindas />
    </MemoryRouter>,
  );
}

describe('BoasVindas', () => {
  it('mostra os cinco termos homologados', () => {
    montar();

    expect(screen.getByText('Não fazemos prescrições')).toBeInTheDocument();
    expect(screen.getByText('Uso exclusivo para maiores de 18 anos')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(5);
  });

  it('só libera o começo depois da confirmação de 18 anos', async () => {
    const usuario = userEvent.setup();
    montar();

    const botao = screen.getByRole('button', { name: 'Começar a checar' });
    expect(botao).toBeDisabled();

    await usuario.click(screen.getByRole('checkbox'));

    expect(botao).toBeEnabled();
  });

  it('marca o onboarding como concluído ao começar', async () => {
    const usuario = userEvent.setup();
    montar();

    await usuario.click(screen.getByRole('checkbox'));
    await usuario.click(screen.getByRole('button', { name: 'Começar a checar' }));

    expect(ler('onboarded')).toBe(true);
  });

  it('não oferece entrar numa conta enquanto a criação de conta está desligada', () => {
    montar();

    // Sem SMTP próprio o link de confirmação não chega a quem é de fora da equipe
    // (CONTA_DISPONIVEL, em lib/sessao.ts). A saída para menor de idade continua.
    expect(screen.queryByRole('button', { name: 'Já tenho conta' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tenho menos de 18' })).toBeInTheDocument();
  });
});
