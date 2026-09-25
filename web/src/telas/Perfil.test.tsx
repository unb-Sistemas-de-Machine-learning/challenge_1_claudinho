/**
 * A tela de Perfil guarda duas coisas que quebram calado: o resumo do perfil de saúde e
 * a troca de tema. O teste cobre as duas pelo que a pessoa vê e faz.
 */

import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { gravar } from '../lib/armazenamento';
import { Perfil } from './Perfil';

function montar() {
  return render(
    <MemoryRouter>
      <Perfil />
    </MemoryRouter>,
  );
}

describe('Perfil', () => {
  beforeEach(() => {
    document.documentElement.removeAttribute('data-theme');
  });

  it('convida a preencher quando o perfil está vazio', () => {
    montar();

    expect(screen.getByText('Seu perfil de saúde está vazio')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Preencher perfil' })).toBeInTheDocument();
  });

  it('mostra o resumo com os rótulos que a pessoa entende', () => {
    gravar('perfil', {
      sex: 'F',
      birth_date: '1972-04-12',
      conditions: ['diabetes_tipo_2'],
      dietary_restrictions: ['lactose'],
      routine: 'sedentaria',
      consent_health_data: true,
    });

    montar();

    expect(screen.getByText('Diabetes tipo 2')).toBeInTheDocument();
    expect(screen.getByText('Intolerância à lactose')).toBeInTheDocument();
    expect(screen.getByText('Sedentária')).toBeInTheDocument();
  });

  it('troca o tema e lembra da escolha', async () => {
    const usuario = userEvent.setup({ delay: null });
    montar();

    await usuario.click(screen.getByRole('radio', { name: /Escuro/ }));

    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    expect(JSON.parse(localStorage.getItem('claudinho:tema') ?? '""')).toBe('dark');
  });

  it('avisa que sem conta os dados ficam só no aparelho', () => {
    montar();

    expect(screen.getByText('Você está usando sem conta')).toBeInTheDocument();
  });

  it('exibe o aviso de sucesso e o remove após 3 segundos', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    render(
      <MemoryRouter initialEntries={[{ pathname: '/perfil', state: { aviso: 'Perfil salvo' } }]}>
        <Perfil />
      </MemoryRouter>,
    );

    expect(screen.getByText('Perfil salvo')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.queryByText('Perfil salvo')).not.toBeInTheDocument();
    vi.useRealTimers();
  });
});
