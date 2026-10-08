import { Construction } from 'lucide-react';
import type { ReactNode } from 'react';

interface Props {
  tela: string;
  /** Número da issue que implementa a tela. Sem número, só avisa que falta. */
  issue?: number;
  children?: ReactNode;
}

const REPOSITORIO = 'https://github.com/unb-Sistemas-de-Machine-learning/challenge_1_claudinho';

/**
 * Marcador das telas que ainda são issue aberta.
 *
 * Existe para o app rodar inteiro desde o primeiro dia: a navegação funciona e cada tela
 * pendente diz qual issue a implementa. Usa a mesma estrutura de tela das telas de
 * verdade, senão o rodapé e a barra de abas sobem para o meio da página.
 *
 * Quem pegar a issue troca este componente pela tela, na rota correspondente.
 */
export function Pendente({ tela, issue, children }: Props) {
  return (
    <div className="tela">
      <header className="tela-topo">
        <span className="topbar-title">{tela}</span>
      </header>
      <main className="tela-conteudo">
        <div className="pendente">
          <Construction aria-hidden="true" />
          <h1 className="h2">{tela}</h1>
          <p className="small">
            Esta tela ainda não foi implementada.{' '}
            {issue ? (
              <>
                Ela é a issue{' '}
                <a
                  href={`${REPOSITORIO}/issues/${issue}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  #{issue}
                </a>
                .
              </>
            ) : (
              'Procure a issue com a etiqueta front-end no repositório.'
            )}
          </p>
          {children}
        </div>
      </main>
    </div>
  );
}
