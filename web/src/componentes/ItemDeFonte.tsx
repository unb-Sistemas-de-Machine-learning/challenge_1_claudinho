import { ExternalLink } from 'lucide-react';

import type { Fonte } from '../lib/api/tipos';

interface Props {
  fonte: Fonte;
  numero: number;
}

/**
 * Uma fonte consultada.
 *
 * A Docs/Ethics/03, secao 3, exige titulo, periodico, autores, DOI e o trecho exato que
 * sustentou a resposta. Fonte visivel e condicao de confianca, nao enfeite.
 */
export function ItemDeFonte({ fonte, numero }: Props) {
  const ano = fonte.published_at?.slice(0, 4);

  return (
    <li className="source" id={`fonte-${numero}`} tabIndex={-1}>
      <span className="source-n" aria-hidden="true">
        {numero}
      </span>
      <div className="source-body">
        <p className="source-title">{fonte.title}</p>
        <p className="source-meta">
          {fonte.journal}
          {ano ? `, ${ano}` : ''}
          <br />
          {fonte.authors}
        </p>
        <blockquote className="source-quote">
          <span className="caption">Trecho usado na resposta</span>“{fonte.excerpt}”
        </blockquote>
        <a
          className="doi"
          href={`https://doi.org/${fonte.doi}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <ExternalLink aria-hidden="true" />
          doi.org/{fonte.doi}
        </a>
      </div>
    </li>
  );
}
