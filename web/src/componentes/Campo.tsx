import { CircleAlert } from 'lucide-react';
import { useId } from 'react';
import type { InputHTMLAttributes } from 'react';

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  rotulo: string;
  ajuda?: string;
  /** Mensagem de erro. Diz o que houve e como corrigir, nunca so "invalido". */
  erro?: string;
  ref?: React.Ref<HTMLInputElement>;
}

/** Campo com rotulo sempre visivel e erro logo abaixo, como manda o design system. */
export function Campo({ rotulo, ajuda, erro, id, ...resto }: Props) {
  const gerado = useId();
  const campoId = id ?? gerado;
  const ajudaId = `${campoId}-ajuda`;
  const erroId = `${campoId}-erro`;

  return (
    <div className="field">
      <label className="field-label" htmlFor={campoId}>
        {rotulo}
      </label>
      <input
        className="input"
        id={campoId}
        aria-invalid={erro ? true : undefined}
        aria-describedby={[ajuda && ajudaId, erro && erroId].filter(Boolean).join(' ') || undefined}
        {...resto}
      />
      {ajuda && (
        <span className="field-help" id={ajudaId}>
          {ajuda}
        </span>
      )}
      {erro && (
        <p className="field-error" id={erroId} role="alert">
          <CircleAlert aria-hidden="true" />
          {erro}
        </p>
      )}
    </div>
  );
}
