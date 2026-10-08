import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Move o foco para o título quando a tela muda.
 *
 * Sem isso, quem toca em um botão fica com o foco no elemento que acabou de desmontar: o
 * foco volta para o começo da página, o leitor de tela não anuncia a tela nova e a
 * tabulação recomeça do topo. O protótipo faz o mesmo a cada navegação.
 *
 * Fica em um lugar só, e não em cada tela, para não virar cinco implementações diferentes.
 */
export function FocoDeTela() {
  const { pathname } = useLocation();

  useEffect(() => {
    const titulo = document.querySelector<HTMLElement>(
      'main h1, main .h1, main .h2, .tela-topo .topbar-title',
    );
    if (!titulo) return;

    // tabindex negativo: focável por código, fora da ordem de tabulação.
    titulo.setAttribute('tabindex', '-1');
    titulo.focus({ preventScroll: true });
  }, [pathname]);

  return null;
}
