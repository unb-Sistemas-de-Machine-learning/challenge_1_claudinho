/**
 * Teste do caminho principal, ponta a ponta: escrever a dúvida, ver o carregamento e
 * chegar na resposta com fontes e avaliação.
 *
 * Roda contra o mock da API, os mesmos handlers do navegador. É o teste que quebra se
 * alguém mudar o contrato sem mexer no cliente, então vale mantê-lo passando.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, delay, http } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';

import { App } from '../App';
import { gravar } from '../lib/armazenamento';
import { respostaPara } from '../mocks/respostas';
import { servidor } from './servidor';

function abrirApp() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <App />
    </MemoryRouter>,
  );
}

describe('fluxo de checagem', () => {
  beforeEach(() => {
    // Quem já aceitou os termos cai direto na checagem. O onboarding tem teste próprio.
    gravar('onboarded', true);
  });

  it('leva da dúvida até a resposta com fonte e avaliação', async () => {
    const usuario = userEvent.setup({ delay: null });
    abrirApp();

    await usuario.type(screen.getByLabelText(/sua dúvida/i), 'pão francês inflama o corpo?');
    await usuario.click(screen.getByRole('button', { name: 'Checar' }));

    expect(await screen.findByText('Procurando nos estudos')).toBeInTheDocument();

    expect(await screen.findByText('É mito')).toBeInTheDocument();
    expect(screen.getByText(/Entendi assim:/)).toBeInTheDocument();
    expect(screen.getByText(/Fontes consultadas/)).toBeInTheDocument();
    expect(screen.getByText(/Não substitui o diagnóstico/)).toBeInTheDocument();
  });

  it('guarda a checagem no histórico do aparelho', async () => {
    const usuario = userEvent.setup({ delay: null });
    abrirApp();

    await usuario.click(screen.getByRole('button', { name: /café faz mal pro coração/i }));

    await screen.findByText('Depende');

    await waitFor(() => {
      const historico = JSON.parse(localStorage.getItem('claudinho:historico') ?? '[]');
      expect(historico).toHaveLength(1);
      expect(historico[0].resposta.verdict).toBe('cautela');
    });
  });

  it('avisa quando o serviço está fora do ar e devolve a dúvida escrita', async () => {
    const usuario = userEvent.setup({ delay: null });
    abrirApp();

    await usuario.type(screen.getByLabelText(/sua dúvida/i), 'erro:503');
    await usuario.click(screen.getByRole('button', { name: 'Checar' }));

    expect(await screen.findByText('Não consegui terminar a checagem')).toBeInTheDocument();

    await usuario.click(screen.getByRole('button', { name: 'Voltar' }));

    // Regressão: a dúvida vivia no estado da tela de checagem, que desmonta na navegação,
    // e voltava vazia. O design system, seção 9, exige que ela sobreviva ao erro.
    expect(await screen.findByLabelText(/sua dúvida/i)).toHaveValue('erro:503');
  });

  it('tentar de novo refaz a checagem', async () => {
    const usuario = userEvent.setup({ delay: null });
    abrirApp();

    await usuario.type(screen.getByLabelText(/sua dúvida/i), 'erro:503');
    await usuario.click(screen.getByRole('button', { name: 'Checar' }));
    await screen.findByText('Não consegui terminar a checagem');

    // A partir daqui a API volta a funcionar, para o botão ter o que refazer.
    servidor.use(
      http.post('*/api/v1/check-claim', async () => {
        await delay(200);
        return HttpResponse.json(respostaPara('pão francês inflama o corpo?'));
      }),
    );

    await usuario.click(screen.getByRole('button', { name: 'Tentar de novo' }));

    // Regressão: a trava contra disparo duplo ficava travada para sempre, e o botão não
    // fazia nada. O aviso de erro precisa sumir e a checagem recomeçar.
    expect(await screen.findByText('É mito')).toBeInTheDocument();
  });

  it('cancelar não deixa a resposta chegar depois nem entrar no histórico', async () => {
    const usuario = userEvent.setup({ delay: null });
    abrirApp();

    await usuario.type(screen.getByLabelText(/sua dúvida/i), 'arroz com feijão');
    await usuario.click(screen.getByRole('button', { name: 'Checar' }));
    await screen.findByText('Procurando nos estudos');

    await usuario.click(screen.getByRole('button', { name: 'Cancelar checagem' }));

    // Regressão: a requisição seguia viva, gravava no histórico e empurrava a pessoa para
    // o resultado que ela desistiu de ver. Na recusa segura isso é grave.
    await new Promise((resolver) => setTimeout(resolver, 2000));

    expect(screen.getByLabelText(/sua dúvida/i)).toBeInTheDocument();
    expect(screen.queryByText('Tem base científica')).not.toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem('claudinho:historico') ?? '[]')).toHaveLength(0);
  });

  it('recusa checagem vazia dizendo o que fazer', async () => {
    const usuario = userEvent.setup({ delay: null });
    abrirApp();

    await usuario.click(screen.getByRole('button', { name: 'Checar' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Escreva a dúvida, cole um link ou envie um print',
    );
  });
});

describe('entradas que a API ainda não lê', () => {
  beforeEach(() => {
    gravar('onboarded', true);
  });

  it('explica que print e link ainda não dão para checar, em vez de erro genérico', async () => {
    const usuario = userEvent.setup({ delay: null });
    abrirApp();

    await usuario.type(screen.getByLabelText(/sua dúvida/i), 'https://www.instagram.com/reel/abc');
    await usuario.click(screen.getByRole('button', { name: 'Checar' }));

    // O PR #15 passou a recusar com 422 `input_nao_suportado`, em vez de responder errado.
    expect(await screen.findByText(/Ainda não consigo ler print nem link/)).toBeInTheDocument();
  });
});
