import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';

import { gravar } from '../lib/armazenamento';
import { Historico } from './Historico';

function montar() {
  return render(
    <MemoryRouter initialEntries={['/historico']}>
      <Routes>
        <Route path="/historico" element={<Historico />} />
        <Route path="/resultado/:traceId" element={<p>Tela de Resultado</p>} />
        <Route path="/" element={<p>Tela Inicial</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

const itemBase = {
  id: '1',
  em: Date.now(),
  entrada: 'Ovo faz mal?',
  resposta: {
    trace_id: 'trace-1',
    verdict: 'seguro' as const,
    canonical_claim: 'Ovo faz mal para a saúde?',
    risk_score: 0.1,
    risk_level: 'baixo' as const,
    answer: 'Pode comer.',
    sources: [],
    disclaimer: '',
    cached: false,
    latency_ms: 100,
    model_version: 'v1',
    prompt_version: 'v1',
  },
};

describe('Historico', () => {
  beforeEach(() => {
    gravar('historico', []);
  });

  it('Sem itens, mostra o estado vazio e o botão que leva para a checagem', () => {
    montar();
    expect(screen.getByText('Nenhuma checagem ainda')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Checar uma dúvida' })).toBeInTheDocument();
  });

  it('Com dois itens no armazenamento, a tela mostra os dois, com o rótulo do veredito de cada um', () => {
    gravar('historico', [
      {
        ...itemBase,
        id: '1',
        entrada: 'Ovo faz mal?',
        resposta: { ...itemBase.resposta, verdict: 'seguro', trace_id: 't1' },
      },
      {
        ...itemBase,
        id: '2',
        entrada: 'Limão emagrece?',
        resposta: { ...itemBase.resposta, verdict: 'desinformacao', trace_id: 't2' },
      },
    ]);
    montar();
    expect(screen.getByText('Ovo faz mal?')).toBeInTheDocument();
    expect(screen.getByText('Limão emagrece?')).toBeInTheDocument();
    expect(screen.getByText('Tem base científica')).toBeInTheDocument();
    expect(screen.getByText('É mito')).toBeInTheDocument();
  });

  it('mostra os itens como no protótipo: lista de verdade, cada linha um botão com a data', () => {
    gravar('historico', [itemBase, { ...itemBase, id: '2', entrada: 'Limão emagrece?' }]);
    montar();

    const linhas = screen.getAllByRole('listitem');
    expect(linhas).toHaveLength(2);
    // O texto de cada linha é o nome acessível do botão: selo, pergunta e quando foi.
    expect(screen.getByRole('button', { name: /Ovo faz mal\?.*Hoje/ })).toHaveClass('row');
    expect(screen.getByText('Suas checagens ficam salvas só neste aparelho.')).toBeInTheDocument();
  });

  it('Clicar em um item navega para /resultado/<trace_id>', async () => {
    const usuario = userEvent.setup();
    gravar('historico', [itemBase]);
    montar();

    await act(async () => {
      await usuario.click(screen.getByText('Ovo faz mal?'));
    });
    expect(screen.getByText('Tela de Resultado')).toBeInTheDocument();
  });

  it('Apagar limpa a lista e leva ao estado vazio', async () => {
    const usuario = userEvent.setup();
    gravar('historico', [itemBase]);
    montar();

    expect(screen.getByText('Ovo faz mal?')).toBeInTheDocument();

    await act(async () => {
      await usuario.click(screen.getByRole('button', { name: 'Apagar histórico' }));
    });

    await act(async () => {
      await usuario.click(screen.getByRole('button', { name: 'Sim, apagar' }));
    });

    expect(screen.getByText('Nenhuma checagem ainda')).toBeInTheDocument();
    expect(screen.queryByText('Ovo faz mal?')).not.toBeInTheDocument();
  });
});
