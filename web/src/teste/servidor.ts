/** Mock da API nos testes, com os mesmos handlers do navegador. */

import { setupServer } from 'msw/node';

import { handlers } from '../mocks/handlers';

export const servidor = setupServer(...handlers);
