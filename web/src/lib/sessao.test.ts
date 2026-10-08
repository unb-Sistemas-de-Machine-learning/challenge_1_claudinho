/**
 * Sessão anônima (issue #23).
 *
 * O que estes testes protegem: em produção a API valida o JWT do Supabase, então um token
 * fixo embutido no build devolveria 401 em toda chamada.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const criarClient = vi.hoisted(() => vi.fn());
vi.mock('@supabase/supabase-js', () => ({ createClient: criarClient }));

// Mock do módulo, e não spy: cada teste recarrega o sessao.ts (resetModules), e o módulo
// recarregado importaria uma cópia nova do cliente, deixando o spy sem efeito.
const definirToken = vi.hoisted(() => vi.fn());
vi.mock('./api/cliente', () => ({ definirToken }));

function supabaseFalso(
  sessaoExistente: string | null,
  aoEntrar: { token?: string; erro?: boolean },
) {
  const ouvintes: ((evento: string, sessao: { access_token: string } | null) => void)[] = [];
  return {
    ouvintes,
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: sessaoExistente ? { access_token: sessaoExistente } : null },
      }),
      signInAnonymously: vi
        .fn()
        .mockResolvedValue(
          aoEntrar.erro
            ? { data: { session: null }, error: new Error('indisponível') }
            : { data: { session: { access_token: aoEntrar.token } }, error: null },
        ),
      onAuthStateChange: vi.fn((ouvinte) => {
        ouvintes.push(ouvinte);
        return { data: { subscription: { unsubscribe: vi.fn() } } };
      }),
    },
  };
}

async function carregarSessao() {
  vi.resetModules();
  return import('./sessao');
}

beforeEach(() => {
  definirToken.mockClear();
  vi.stubEnv('VITE_SUPABASE_URL', 'https://projeto.supabase.co');
  vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'chave-publica');
});

afterEach(() => {
  vi.unstubAllEnvs();
  criarClient.mockReset();
});

describe('sessão anônima', () => {
  it('entra sem conta e entrega o token à camada de rede', async () => {
    const falso = supabaseFalso(null, { token: 'jwt-novo' });
    criarClient.mockReturnValue(falso);

    const { iniciarSessao } = await carregarSessao();
    await iniciarSessao();

    expect(falso.auth.signInAnonymously).toHaveBeenCalled();
    expect(definirToken).toHaveBeenCalledWith('jwt-novo');
  });

  it('reaproveita a sessão que já existe no aparelho', async () => {
    const falso = supabaseFalso('jwt-guardado', {});
    criarClient.mockReturnValue(falso);

    const { iniciarSessao } = await carregarSessao();
    await iniciarSessao();

    expect(falso.auth.signInAnonymously).not.toHaveBeenCalled();
    expect(definirToken).toHaveBeenCalledWith('jwt-guardado');
  });

  it('atualiza o token quando o Supabase renova', async () => {
    const falso = supabaseFalso('jwt-velho', {});
    criarClient.mockReturnValue(falso);

    const { iniciarSessao } = await carregarSessao();
    await iniciarSessao();
    falso.ouvintes.forEach((ouvir) => ouvir('TOKEN_REFRESHED', { access_token: 'jwt-renovado' }));

    // Sem isso, o app funcionaria por uma hora e depois tomaria 401 sem motivo aparente.
    expect(definirToken).toHaveBeenLastCalledWith('jwt-renovado');
  });

  it('sem Supabase configurado, usa o token de desenvolvimento', async () => {
    vi.stubEnv('VITE_SUPABASE_URL', '');
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', '');
    vi.stubEnv('VITE_API_TOKEN', 'token-de-desenvolvimento');

    const { iniciarSessao } = await carregarSessao();
    await iniciarSessao();

    expect(criarClient).not.toHaveBeenCalled();
    expect(definirToken).toHaveBeenCalledWith('token-de-desenvolvimento');
  });

  it('falha no login não derruba o app', async () => {
    criarClient.mockReturnValue(supabaseFalso(null, { erro: true }));

    const { iniciarSessao } = await carregarSessao();
    await expect(iniciarSessao()).resolves.toBeUndefined();

    expect(definirToken).toHaveBeenCalledWith(null);
  });

  it('exceção do SDK também não derruba o app', async () => {
    const falso = supabaseFalso(null, {});
    falso.auth.getSession.mockRejectedValue(new Error('rede caiu'));
    criarClient.mockReturnValue(falso);

    const { iniciarSessao } = await carregarSessao();
    await expect(iniciarSessao()).resolves.toBeUndefined();

    expect(definirToken).toHaveBeenCalledWith(null);
  });

  it('sair e entrar de novo não acumula ouvintes de renovação', async () => {
    const falso = supabaseFalso('jwt', {});
    criarClient.mockReturnValue(falso);

    const { iniciarSessao } = await carregarSessao();
    await iniciarSessao();
    await iniciarSessao();

    expect(falso.auth.onAuthStateChange).toHaveBeenCalledTimes(1);
  });
});
