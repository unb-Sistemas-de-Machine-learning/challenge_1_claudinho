/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig(() => {
  return {
    plugins: [
      react(),
      VitePWA({
        registerType: 'autoUpdate',
        manifest: {
          name: 'Claudinho',
          short_name: 'Claudinho',
          description: 'Checagem de desinformação nutricional com base em estudos científicos.',
          lang: 'pt-BR',
          start_url: '/',
          display: 'standalone',
          background_color: '#FCFAF6',
          theme_color: '#226FB3',
          icons: [
            {
              src: 'pwa-192x192.png',
              sizes: '192x192',
              type: 'image/png',
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
            },
            {
              src: 'pwa-512x512-maskable.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable',
            },
          ],
          // Texto e link chegam por GET, que nao precisa de handler no service worker: o
          // Android abre `/?title=&text=&url=` e a tela Checar le os parametros (issue #27).
          // Receber o print (arquivo) exige POST com handler, que ainda nao existe.
          share_target: {
            action: '/',
            method: 'GET',
            params: { title: 'title', text: 'text', url: 'url' },
          },
        },
        workbox: {
          // O worker do MSW só serve ao modo de desenvolvimento com mock. Sem esta linha
          // ele é pré-carregado no app publicado: peso inútil no primeiro acesso.
          globIgnores: ['**/mockServiceWorker.js'],
        },
        devOptions: { enabled: false },
      }),
    ],
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/teste/setup.ts'],
      // Os testes de fluxo esperam o mock responder com o atraso de rede simulado, entao
      // o limite padrao de 5s aperta demais.
      testTimeout: 15000,
      css: false,
      coverage: { reporter: ['text', 'html'], include: ['src/**/*.{ts,tsx}'] },
    },
  };
});
