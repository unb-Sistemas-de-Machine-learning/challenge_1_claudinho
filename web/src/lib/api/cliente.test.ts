/**
 * Exemplo de teste de integração com a API.
 *
 * Usa o mesmo mock do navegador (src/mocks/handlers.ts), então o teste exercita o
 * caminho real do cliente: monta a requisição, lê o corpo e traduz o erro do contrato.
 */

import { describe, expect, it } from 'vitest';

import { ErroDaApi, checarAlegacao, enviarFeedback, obterPerfil, salvarPerfil } from './cliente';

describe('checarAlegacao', () => {
  it('devolve o veredito da resposta', async () => {
    const resposta = await checarAlegacao({ input_type: 'text', text: 'pão francês inflama?' });

    expect(resposta.verdict).toBe('desinformacao');
    expect(resposta.sources.length).toBeGreaterThan(0);
    expect(resposta.disclaimer).toContain('Não substitui');
  });

  it('traduz 429 em erro com o tempo de espera', async () => {
    const erro = await checarAlegacao({ input_type: 'text', text: 'erro:429' }).catch((e) => e);

    expect(erro).toBeInstanceOf(ErroDaApi);
    expect((erro as ErroDaApi).codigo).toBe('rate_limited');
    expect((erro as ErroDaApi).tentarEm).toBe(42);
  });

  it('traduz pedido vazio em invalid_input', async () => {
    const erro = await checarAlegacao({ input_type: 'text' }).catch((e) => e);

    expect((erro as ErroDaApi).codigo).toBe('invalid_input');
    expect((erro as ErroDaApi).status).toBe(400);
  });
});

describe('enviarFeedback', () => {
  it('recusa avaliação negativa sem motivo, como o design system pede', async () => {
    const erro = await enviarFeedback({ trace_id: 'abc', rating: 'down' }).catch((e) => e);

    expect((erro as ErroDaApi).codigo).toBe('invalid_input');
  });
});

describe('perfil', () => {
  it('devolve null quando ainda não existe, em vez de estourar', async () => {
    await expect(obterPerfil()).resolves.toBeNull();
  });

  it('guarda e devolve o perfil salvo', async () => {
    await salvarPerfil({
      sex: 'F',
      conditions: ['diabetes_tipo_2'],
      dietary_restrictions: [],
      consent_health_data: true,
    });

    const perfil = await obterPerfil();

    expect(perfil?.conditions).toEqual(['diabetes_tipo_2']);
  });
});
