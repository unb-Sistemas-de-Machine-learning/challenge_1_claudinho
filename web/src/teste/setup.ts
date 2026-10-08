import '@testing-library/jest-dom/vitest';

import { configure } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';

// O padrao do findBy e 1s, e o mock simula o atraso de rede da checagem. Sem isto, todo
// teste de fluxo precisaria repetir um timeout proprio.
configure({ asyncUtilTimeout: 5000 });

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

import { servidor } from './servidor';

// O mesmo mock do navegador roda nos testes, entao teste e desenvolvimento nao divergem.
beforeAll(() => servidor.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  servidor.resetHandlers();
  localStorage.clear();
});
afterAll(() => servidor.close());
