/**
 * O app monta sem esperar a sessão anônima (issue #23), então quem segura a primeira
 * requisição até o token chegar é a camada de rede.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import { aguardarSessao, checarAlegacao, definirToken } from './cliente';

afterEach(() => {
  vi.unstubAllGlobals();
  aguardarSessao(Promise.resolve());
  definirToken(null);
});

describe('cliente: espera da sessão', () => {
  it('a primeira requisição sai com o token que chegou depois de o app montar', async () => {
    const buscar = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', buscar);

    let liberar!: () => void;
    aguardarSessao(
      new Promise<void>((resolver) => {
        liberar = () => {
          definirToken('jwt-anonimo');
          resolver();
        };
      }),
    );

    const pedido = checarAlegacao({ input_type: 'text', text: 'detox funciona?' });
    expect(buscar).not.toHaveBeenCalled();

    liberar();
    await pedido.catch(() => undefined);

    const cabecalhos = buscar.mock.calls[0][1].headers as Record<string, string>;
    expect(cabecalhos.Authorization).toBe('Bearer jwt-anonimo');
  });
});
