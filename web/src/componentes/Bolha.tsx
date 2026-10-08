import { Link as IconeLink, ScanText } from 'lucide-react';
import type { ReactNode } from 'react';

interface Props {
  children: ReactNode;
  /** Mostra a origem acima do texto: o link colado ou o print enviado. */
  origem?: { tipo: 'url'; valor: string } | { tipo: 'imagem'; src: string };
}

/**
 * A dúvida da pessoa, citada de volta.
 *
 * O canto inferior direito quase reto marca quem fala: a pergunta vem da direita, a
 * resposta do Claudinho vem da esquerda (ver CardDeVeredito).
 */
export function Bolha({ children, origem }: Props) {
  return (
    <div className="bubble">
      {origem?.tipo === 'imagem' && (
        <img className="bubble-img" src={origem.src} alt="Print enviado" />
      )}
      {origem?.tipo === 'url' && (
        <div className="bubble-meta">
          <IconeLink aria-hidden="true" />
          {origem.valor.replace(/^https?:\/\/(www\.)?/, '')}
        </div>
      )}
      {origem?.tipo === 'imagem' && (
        <div className="bubble-meta">
          <ScanText aria-hidden="true" />
          Texto encontrado no print
        </div>
      )}
      {children}
    </div>
  );
}
