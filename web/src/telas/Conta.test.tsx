/** Tela de conta: criar, entrar e sair (issue #24). */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import * as sessao from '../lib/sessao';
import { Conta } from './Conta';

function montar() {
  return render(
    <MemoryRouter initialEntries={['/conta']}>
      <Routes>
        <Route path="/conta" element={<Conta />} />
        <Route path="/perfil" element={<p>tela de perfil</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

async function preencher(email: string, senha: string) {
  // A tela só aparece depois de consultar se já existe conta neste aparelho.
  await userEvent.type(await screen.findByLabelText('Email'), email);
  await userEvent.type(screen.getByLabelText(/Senha/), senha);
}

beforeEach(() => vi.spyOn(sessao, 'emailDaConta').mockResolvedValue(null));
afterEach(() => vi.restoreAllMocks());

describe('Conta', () => {
  it('cria a conta promovendo a sessão anônima e volta para o perfil', async () => {
    const criar = vi.spyOn(sessao, 'criarConta').mockResolvedValue({ ok: true });

    montar();
    await preencher('eu@exemplo.com', 'senhaforte1');
    await userEvent.click(screen.getByRole('button', { name: 'Criar conta' }));

    expect(criar).toHaveBeenCalledWith('eu@exemplo.com', 'senhaforte1');
    expect(await screen.findByText('tela de perfil')).toBeInTheDocument();
  });

  it('recusa email sem arroba antes de chamar a rede', async () => {
    const criar = vi.spyOn(sessao, 'criarConta');

    montar();
    await preencher('sem-arroba', 'senhaforte1');
    await userEvent.click(screen.getByRole('button', { name: 'Criar conta' }));

    expect(screen.getByText(/email válido/)).toBeInTheDocument();
    expect(criar).not.toHaveBeenCalled();
  });

  it('recusa senha curta antes de chamar a rede', async () => {
    const criar = vi.spyOn(sessao, 'criarConta');

    montar();
    await preencher('eu@exemplo.com', '123');
    await userEvent.click(screen.getByRole('button', { name: 'Criar conta' }));

    expect(screen.getByText(/pelo menos 8 caracteres/)).toBeInTheDocument();
    expect(criar).not.toHaveBeenCalled();
  });

  it('mostra na tela o motivo recusado pelo servidor', async () => {
    vi.spyOn(sessao, 'criarConta').mockResolvedValue({
      ok: false,
      mensagem: 'Esse email já tem conta. Use "Entrar" para acessá-la.',
    });

    montar();
    await preencher('eu@exemplo.com', 'senhaforte1');
    await userEvent.click(screen.getByRole('button', { name: 'Criar conta' }));

    expect(await screen.findByText(/já tem conta/)).toBeInTheDocument();
  });

  it('avisa que entrar numa conta existente deixa para trás o que é só deste aparelho', async () => {
    montar();
    await userEvent.click(await screen.findByRole('button', { name: 'Já tenho conta' }));

    expect(screen.getByText(/fica para trás/)).toBeInTheDocument();
  });

  it('quem já está logado vê o email e pode sair', async () => {
    vi.spyOn(sessao, 'emailDaConta').mockResolvedValue('eu@exemplo.com');
    const encerrar = vi.spyOn(sessao, 'sair').mockResolvedValue();

    montar();
    await userEvent.click(await screen.findByRole('button', { name: 'Sair da conta' }));

    expect(encerrar).toHaveBeenCalled();
    expect(await screen.findByText('tela de perfil')).toBeInTheDocument();
  });
});
