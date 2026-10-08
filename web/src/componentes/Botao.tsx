import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variante = 'primaria' | 'secundaria' | 'discreta';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
  /** Ocupa a largura toda. Usado no botao principal do rodape. */
  bloco?: boolean;
  pequeno?: boolean;
  carregando?: boolean;
  children: ReactNode;
}

const CLASSE: Record<Variante, string> = {
  primaria: 'btn-primary',
  secundaria: 'btn-secondary',
  discreta: 'btn-ghost',
};

/**
 * Botao do design system.
 *
 * Um botao principal por tela, no rodape, ao alcance do polegar. O texto diz a acao que
 * acontece: Checar, Salvar perfil, Enviar avaliacao.
 */
export function Botao({
  variante = 'primaria',
  bloco = false,
  pequeno = false,
  carregando = false,
  disabled,
  children,
  className = '',
  // O padrao do HTML e "submit": dentro do formulário do perfil, um botão sem tipo
  // enviaria o formulário sem querer.
  type = 'button',
  ...resto
}: Props) {
  const classes = ['btn', CLASSE[variante], bloco && 'btn-block', pequeno && 'btn-sm', className]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      className={classes}
      type={type}
      disabled={disabled || carregando}
      aria-busy={carregando}
      {...resto}
    >
      {carregando && <span className="spinner" aria-hidden="true" />}
      {children}
    </button>
  );
}
