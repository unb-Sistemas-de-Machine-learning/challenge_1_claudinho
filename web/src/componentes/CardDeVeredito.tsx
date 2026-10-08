import { VEREDITOS } from '../lib/vereditos';
import type { Veredito } from '../lib/api/tipos';

interface Props {
  veredito: Veredito;
  /** A frase grande, escrita como fala. Vem do backend ou do texto padrao da tela. */
  frase: string;
  /** A alegacao canonica, que confirma que o sistema entendeu a pergunta certa. */
  alegacao?: string;
  /** Id do titulo, para a secao ser rotulada por ele. */
  idDoTitulo?: string;
}

/**
 * O momento principal do produto.
 *
 * O veredito vem ANTES da explicacao e cabe na primeira dobra, porque e ele que decide
 * se a pessoa vai ler o resto (Docs/Design/design-system.md, principio 1).
 */
export function CardDeVeredito({ veredito, frase, alegacao, idDoTitulo }: Props) {
  const { rotulo, Icone } = VEREDITOS[veredito];

  return (
    <section className="reply" data-verdict={veredito} aria-labelledby={idDoTitulo}>
      <span className="verdict-label">
        <Icone aria-hidden="true" />
        {rotulo}
      </span>
      <h1 className="verdict-headline" id={idDoTitulo}>
        {frase}
      </h1>
      {alegacao && (
        <p className="understood">
          Entendi assim: <strong>{alegacao}</strong>
        </p>
      )}
    </section>
  );
}

/** Versao compacta, para listas como o histórico. */
export function SeloDeVeredito({ veredito }: { veredito: Veredito }) {
  const { rotulo, Icone } = VEREDITOS[veredito];

  return (
    <span data-verdict={veredito}>
      <span className="verdict-chip">
        <Icone aria-hidden="true" />
        {rotulo}
      </span>
    </span>
  );
}
