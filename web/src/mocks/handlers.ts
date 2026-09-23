/**
 * Mock da API (MSW).
 *
 * Com VITE_API_MOCK=true o app roda sem backend, sem Supabase e sem LLM. E o que permite
 * o time inteiro trabalhar nas telas ao mesmo tempo, inclusive nos estados de erro, que
 * sao dificeis de provocar no servidor de verdade.
 *
 * Para exercitar um erro, mande o codigo no texto da checagem. Ex.: "erro:429".
 */

import { HttpResponse, delay, http } from 'msw';

import type { PedidoDeChecagem, PedidoDeFeedback, Perfil } from '../lib/api/tipos';
import { respostaPara } from './respostas';

const BASE = `${import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'}/api/v1`;

/** Perfil em memoria, para o PUT e o GET conversarem durante a sessao. */
let perfilSalvo: Perfil | null = null;

function erroPedido(texto: string) {
  const achado = /erro:(\d{3})/.exec(texto);
  return achado ? Number(achado[1]) : null;
}

export const handlers = [
  http.post(`${BASE}/check-claim`, async ({ request }) => {
    const pedido = (await request.json()) as PedidoDeChecagem;
    const texto = pedido.text ?? pedido.url ?? '';

    // Espelha a recusa que a API passou a fazer no PR #15: sem OCR e sem leitura de
    // página, print e link não têm como virar checagem correta.
    if (!pedido.text && (pedido.url || pedido.image_base64)) {
      return HttpResponse.json(
        {
          error: 'input_nao_suportado',
          detail:
            'Ainda não conseguimos ler prints nem links. Escreva a dúvida em texto que a gente verifica para você.',
        },
        { status: 422 },
      );
    }

    if (!pedido.text && !pedido.url && !pedido.image_base64) {
      return HttpResponse.json(
        { error: 'invalid_input', detail: 'preencha ao menos um entre text, url e image_base64' },
        { status: 400 },
      );
    }

    switch (erroPedido(texto)) {
      case 401:
        return HttpResponse.json({ error: 'unauthorized' }, { status: 401 });
      case 413:
        return HttpResponse.json({ error: 'payload_too_large' }, { status: 413 });
      case 429:
        return HttpResponse.json(
          { error: 'rate_limited', retry_after: 42 },
          { status: 429, headers: { 'Retry-After': '42' } },
        );
      case 503:
        return HttpResponse.json({ error: 'upstream_unavailable' }, { status: 503 });
    }

    // O pipeline real leva alguns segundos. Sem esse atraso, a tela de carregamento
    // nunca aparece em desenvolvimento e ninguem percebe quando ela quebra.
    await delay(1200);
    return HttpResponse.json(respostaPara(texto));
  }),

  http.post(`${BASE}/feedback`, async ({ request }) => {
    const pedido = (await request.json()) as PedidoDeFeedback;

    // O backend de verdade aceita sem motivo. O mock recusa para o app exercitar a regra
    // de produto (design system, seção 5) em desenvolvimento.
    if (pedido.rating === 'down' && !pedido.reason) {
      return HttpResponse.json(
        { error: 'invalid_input', detail: "reason e obrigatorio quando rating e 'down'" },
        { status: 400 },
      );
    }

    await delay(300);
    return HttpResponse.json(
      { status: 'registered', feedback_id: crypto.randomUUID() },
      { status: 201 },
    );
  }),

  http.get(`${BASE}/profile`, () => {
    if (!perfilSalvo) return HttpResponse.json({ error: 'profile_not_found' }, { status: 404 });
    return HttpResponse.json(perfilSalvo);
  }),

  http.put(`${BASE}/profile`, async ({ request }) => {
    const perfil = (await request.json()) as Perfil;

    if (perfil.conditions?.length && !perfil.consent_health_data) {
      return HttpResponse.json(
        {
          error: 'invalid_input',
          detail: 'consent_health_data deve ser true para enviar condicoes de saude',
        },
        { status: 400 },
      );
    }

    perfilSalvo = perfil;
    return HttpResponse.json(perfil);
  }),
];
