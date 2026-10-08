import { useId } from 'react';
import type { ReactNode } from 'react';

interface Props {
  rotulo: ReactNode;
  descricao?: ReactNode;
  marcado: boolean;
  aoMudar: (marcado: boolean) => void;
}

/** Linha com rotulo e interruptor, usada no perfil e nas preferencias. */
export function Interruptor({ rotulo, descricao, marcado, aoMudar }: Props) {
  const id = useId();

  return (
    <div className="switch-row">
      <label htmlFor={id} className="small">
        <strong>{rotulo}</strong>
        {descricao && (
          <span className="caption" style={{ display: 'block' }}>
            {descricao}
          </span>
        )}
      </label>
      <input
        type="checkbox"
        role="switch"
        className="switch"
        id={id}
        checked={marcado}
        onChange={(evento) => aoMudar(evento.target.checked)}
      />
    </div>
  );
}
