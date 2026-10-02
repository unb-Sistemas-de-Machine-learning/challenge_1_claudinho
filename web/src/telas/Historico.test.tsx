/** Tela de histórico: lista, estado vazio e apagar com desfazer (issue #18). */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import type { ItemDoHistorico } from '../lib/armazenamento';
import { gravar, ler, limparTudo } from '../lib/armazenamento';
import { Historico } from './Historico';

function item(id: string, entrada: string, verdict: ItemDoHistorico['resposta']['verdict']) {
  return {
    id,
    em: Date.now(),
    entrada,
    resposta: {
      trace_id: `trace-${id}`,
      canonical_claim: entrada,
      verdict,
      risk_score: 0.8,
      risk_level: 'alto',
      answer: 'resposta',
      sources: [],
      disclaimer: 'aviso',
      cached: false,
      latency_ms: 10,
      model_version: 'teste',
      prompt_version: 'teste',
    },
  } as ItemDoHistorico;
}

function montar() {
  return render(
    <MemoryRouter initialEntries={['/historico']}>
      <Routes>
        <Route path="/historico" element={<Historico />} />
        <Route path="/resultado/:id" element={<p>tela de resultado</p>} />
        <Route path="/" element={<p>tela de checagem</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => limparTudo());
afterEach(() => limparTudo());

describe('Histórico', () => {
  it('convida a checar quando ainda não há nada, avisando que fica no aparelho', async () => {
    montar();

    expect(screen.getByText(/só neste aparelho/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Fazer uma checagem' }));
    expect(screen.getByText('tela de checagem')).toBeInTheDocument();
  });

  it('lista pela entrada da pessoa, e não pelo veredito', () => {
    gravar('historico', [item('1', 'água com limão emagrece?', 'desinformacao')]);

    montar();

    const linha = screen.getByRole('listitem');
    expect(within(linha).getByText('água com limão emagrece?')).toBeInTheDocument();
    expect(within(linha).getByText(/Mito|Desinformação/i)).toBeInTheDocument();
  });

  it('abre a checagem guardada', async () => {
    gravar('historico', [item('abc', 'ovo faz mal?', 'seguro')]);

    montar();
    await userEvent.click(screen.getByRole('button', { name: /^ovo faz mal/ }));

    expect(screen.getByText('tela de resultado')).toBeInTheDocument();
  });

  it('apaga a checagem e grava a remoção', async () => {
    gravar('historico', [item('1', 'detox funciona?', 'cautela')]);

    montar();
    await userEvent.click(screen.getByRole('button', { name: /Apagar a checagem/ }));

    expect(screen.queryByText('detox funciona?')).not.toBeInTheDocument();
    expect(ler('historico')).toHaveLength(0);
  });

  it('desfaz o apagar, devolvendo o item à mesma posição', async () => {
    gravar('historico', [
      item('1', 'primeira', 'seguro'),
      item('2', 'segunda', 'cautela'),
      item('3', 'terceira', 'desinformacao'),
    ]);

    montar();
    await userEvent.click(screen.getByRole('button', { name: /Apagar a checagem sobre segunda/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Desfazer' }));

    expect(ler('historico').map((guardado) => guardado.entrada)).toEqual([
      'primeira',
      'segunda',
      'terceira',
    ]);
  });
});
