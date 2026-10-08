import { Check } from 'lucide-react';
import type { InputHTMLAttributes, ReactNode } from 'react';

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  children: ReactNode;
  tipo?: 'checkbox' | 'radio';
  /** Falso quando o chip ja tem icone proprio, para nao aparecerem dois. */
  comVisto?: boolean;
}

/**
 * Chip selecionavel.
 *
 * O visto aparece junto com a cor quando marcado: quem nao distingue a cor precisa de
 * outro sinal. A caixa fica invisivel mas focavel, entao o teclado continua funcionando.
 */
export function Chip({ children, tipo = 'checkbox', comVisto = true, ...resto }: Props) {
  return (
    <label className="chip">
      <input type={tipo} {...resto} />
      {comVisto && <Check aria-hidden="true" />}
      {children}
    </label>
  );
}
