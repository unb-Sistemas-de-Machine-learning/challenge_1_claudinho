/**
 * Tela de carregamento: a alegação extraída aparece antes da resposta (issue #26).
 *
 * A extração é acessória: ela existe para a pessoa ver que foi compreendida enquanto
 * espera, e falhar nela não pode atrapalhar a checagem de verdade.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import * as cliente from '../lib/api/cliente';
import { Carregando } from './Carregando';

const PEDIDO = {
  pedido: { input_type: 'text' as const, text: 'agua com limao emagrece???' },
  entrada: 'agua com limao emagrece???',
};

function montar() {
  return render(
    <MemoryRouter initialEntries={[{ pathname: '/checando', state: PEDIDO }]}>
      <Routes>
        <Route path="/checando" element={<Carregando />} />
        <Route path="/resultado/:id" element={<p>resultado</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

/** Checagem que nunca termina: mantém a tela no estado de espera, que é o que se testa. */
function checagemPendente() {
  return vi.spyOn(cliente, 'checarAlegacao').mockReturnValue(new Promise(() => {}));
}

afterEach(() => vi.restoreAllMocks());

describe('Carregando', () => {
  it('mostra a alegação como a API entendeu, enquanto a checagem roda', async () => {
    checagemPendente();
    vi.spyOn(cliente, 'extrairAlegacao').mockResolvedValue({
      canonical_claim: 'Água com limão em jejum emagrece?',
      safe_refusal: false,
    });

    montar();

<<<<<<< HEAD
    expect(
      await screen.findByText('Entendi assim: Água com limão em jejum emagrece?'),
    ).toBeInTheDocument();
=======
    // A alegacao vai em negrito e o rotulo em texto normal, entao o texto fica em dois
    // elementos: a busca e pelo trecho em negrito.
    const alegacao = await screen.findByText('Água com limão em jejum emagrece?');
    expect(alegacao.tagName).toBe('STRONG');
    expect(alegacao.parentElement?.textContent).toBe(
      'Entendi assim: Água com limão em jejum emagrece?',
    );
>>>>>>> 1f67b5f9c619536f61e68cff1499e8b563c6d8ae
  });

  it('segue funcionando quando a extração falha', async () => {
    checagemPendente();
    vi.spyOn(cliente, 'extrairAlegacao').mockRejectedValue(new Error('sem conexão'));

    montar();

    await waitFor(() => expect(screen.getByText('Procurando nos estudos')).toBeInTheDocument());
<<<<<<< HEAD
    expect(screen.queryByText(/Entendi assim/)).not.toBeInTheDocument();
=======
    // O paragrafo existe desde o inicio, com o espaco reservado, mas fica vazio: e isso
    // que evita a lista de passos pular quando a extracao chega (ou nao chega).
    expect(document.querySelector('.entendi-assim')?.textContent).toBe('');
>>>>>>> 1f67b5f9c619536f61e68cff1499e8b563c6d8ae
  });

  it('não pede extração para print, que a API ainda não lê', () => {
    checagemPendente();
    const extrair = vi.spyOn(cliente, 'extrairAlegacao');

    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: '/checando',
            state: { pedido: { input_type: 'image', image_base64: 'YQ==' }, entrada: 'print' },
          },
        ]}
      >
        <Routes>
          <Route path="/checando" element={<Carregando />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(extrair).not.toHaveBeenCalled();
  });
});
