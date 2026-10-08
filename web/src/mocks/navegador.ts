/** Liga o mock no navegador. Chamado so em desenvolvimento, por main.tsx. */

import { setupWorker } from 'msw/browser';

import { handlers } from './handlers';

export const worker = setupWorker(...handlers);
