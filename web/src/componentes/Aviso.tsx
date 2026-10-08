import { Info, ServerOff, Stethoscope, Timer } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

type Tipo = 'cuidado' | 'atencao' | 'erro' | 'informacao';

interface Props {
  tipo?: Tipo;
  titulo?: ReactNode;
  children: ReactNode;
  Icone?: LucideIcon;
  acoes?: ReactNode;
}

const CLASSE: Record<Tipo, string> = {
  cuidado: 'notice-care',
  atencao: 'notice-warn',
  erro: 'notice-error',
  informacao: 'notice-info',
};

const ICONE_PADRAO: Record<Tipo, LucideIcon> = {
  cuidado: Stethoscope,
  atencao: Timer,
  erro: ServerOff,
  informacao: Info,
};

/**
 * Aviso no lugar do problema, nunca em pop-up.
 *
 * Erro usa `role="alert"` para o leitor de tela anunciar na hora; os outros tipos usam
 * `role="status"`, que espera a pessoa terminar o que esta fazendo.
 */
export function Aviso({ tipo = 'informacao', titulo, children, Icone, acoes }: Props) {
  const Desenho = Icone ?? ICONE_PADRAO[tipo];

  return (
    <div className={`notice ${CLASSE[tipo]}`} role={tipo === 'erro' ? 'alert' : 'status'}>
      <Desenho aria-hidden="true" />
      <div className="notice-body">
        {titulo && <strong>{titulo}</strong>}
        <span>{children}</span>
        {acoes && <div className="notice-actions">{acoes}</div>}
      </div>
    </div>
  );
}
