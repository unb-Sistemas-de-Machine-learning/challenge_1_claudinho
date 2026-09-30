import { ArrowLeft, BookOpen, ChevronDown, Info, Phone, Plus, SearchX, Share2 } from 'lucide-react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';

import { Aviso } from '../componentes/Aviso';

import { Avaliacao } from '../componentes/Avaliacao';
import { Bolha } from '../componentes/Bolha';
import { Botao } from '../componentes/Botao';
import { CardDeVeredito } from '../componentes/CardDeVeredito';
import { ItemDeFonte } from '../componentes/ItemDeFonte';
import { ler } from '../lib/armazenamento';
import { extrairParagrafosDoCorpo } from '../lib/resposta';
import { VEREDITOS } from '../lib/vereditos';

/**
 * A resposta.
 *
 * Ordem fixa, e ela é o produto: veredito, depois explicação, depois fontes, depois
 * avaliação, e o aviso da Ethics/03 em toda resposta. O veredito cabe na primeira dobra
 * porque é ele que decide se a pessoa lê o resto.
 *
 * A resposta vem do histórico no aparelho, e não de um estado de navegação, para a tela
 * sobreviver a recarregar a página e poder ser aberta de novo pelo histórico.
 */
export function Resultado() {
  const { id } = useParams();
  const navegar = useNavigate();

  const item = ler('historico').find((guardado) => guardado.id === id);
  if (!item) return <Navigate to="/" replace />;

  const { resposta, entrada } = item;
  const { mostraFontes, aberturaDaFrase } = VEREDITOS[resposta.verdict];

  /**
   * Abre a seção de fontes e leva até a fonte citada.
   *
   * A referência precisa ser clicável: a promessa do produto é a fonte à mão, e obrigar
   * a rolar até o fim para achar qual estudo sustenta a frase quebra essa promessa.
   */
  function irParaFonte(numero: number) {
    const secao = document.getElementById('fontes') as HTMLDetailsElement | null;
    if (secao) secao.open = true;
    const alvo = document.getElementById(`fonte-${numero}`);
    alvo?.scrollIntoView({ block: 'start', behavior: 'smooth' });
    alvo?.focus({ preventScroll: true });
  }

  /** Troca os marcadores [Ref: chunk_x] do texto pela pílula numerada da fonte. */
  function comReferencias(texto: string) {
    return texto.split(/(\[Ref:\s*[^\]]+\])/g).map((pedaco, indice) => {
      const achado = /^\[Ref:\s*([^\]]+)\]$/.exec(pedaco);
      if (!achado) return pedaco;

      const posicao = resposta.sources.findIndex((fonte) => fonte.chunk_id === achado[1].trim());
      if (posicao < 0) return null;

      return (
        <button
          key={`${pedaco}-${indice}`}
          className="ref"
          onClick={() => irParaFonte(posicao + 1)}
          aria-label={`Ver fonte ${posicao + 1}`}
        >
          {posicao + 1}
        </button>
      );
    });
  }
  const cuidado = resposta.verdict === 'recusa_segura';

  async function compartilhar() {
    const fonte = resposta.sources[0];
    const texto = [
      `Chequei no Claudinho: "${resposta.canonical_claim}"`,
      `${VEREDITOS[resposta.verdict].rotulo}. ${resposta.answer}`,
      fonte ? `Fonte: ${fonte.title}, ${fonte.journal}. doi.org/${fonte.doi}` : '',
    ]
      .filter(Boolean)
      .join('\n');

    try {
      if (navigator.share) await navigator.share({ title: 'Checagem do Claudinho', text: texto });
      else await navigator.clipboard.writeText(texto);
    } catch {
      // Compartilhar cancelado pela pessoa, ou bloqueado pelo navegador: nao e erro.
    }
  }

  return (
    <div className="tela">
      <header className="tela-topo">
        <button className="icon-btn" aria-label="Voltar para o início" onClick={() => navegar('/')}>
          <ArrowLeft aria-hidden="true" />
        </button>
        <span style={{ flex: 1 }} />
        {!cuidado && (
          <Botao variante="discreta" pequeno onClick={() => void compartilhar()}>
            <Share2 aria-hidden="true" />
            Compartilhar
          </Botao>
        )}
      </header>

      <main className="tela-conteudo">
        <div className="pilha">
          <div className="conversa">
            <Bolha origem={item.origem}>{entrada}</Bolha>
            <CardDeVeredito
              veredito={resposta.verdict}
              frase={aberturaDaFrase}
              alegacao={resposta.canonical_claim}
              idDoTitulo="veredito"
            />
          </div>

          <div className="answer">
            {extrairParagrafosDoCorpo(resposta.answer, aberturaDaFrase).map((paragrafo, indice) => (
              // O índice serve de chave aqui porque a ordem dos parágrafos não muda:
              // a resposta é imutável depois de gravada no histórico.
              <p key={indice}>{comReferencias(paragrafo)}</p>
            ))}
          </div>

          {resposta.verdict === 'cautela' && (
            <Aviso tipo="atencao" titulo="Aviso de evidência limitada" Icone={Info}>
              A alegação analisada aborda um tema onde a ciência atual apresenta estudos
              inconclusivos, de baixa qualidade metodológica ou com opiniões divergentes na
              comunidade acadêmica. O resultado apresentado reflete o consenso provisório da
              literatura e não deve ser tomado como verdade definitiva.
            </Aviso>
          )}

          {cuidado && (
            <section className="pilha-curta" aria-labelledby="apoio">
              <h2 className="h3" id="apoio">
                Se quiser conversar com alguém
              </h2>
              <div className="rows">
                <a className="row" href="tel:188" style={{ color: 'inherit' }}>
                  <span className="row-main">
                    <span className="row-title">CVV, apoio emocional</span>
                    <span className="small muted">Ligue 188. É de graça e funciona 24 horas.</span>
                  </span>
                  <Phone className="chev" aria-hidden="true" />
                </a>
                <div className="row">
                  <span className="row-main">
                    <span className="row-title">Unidade Básica de Saúde</span>
                    <span className="small muted">
                      Consulta com nutricionista pelo SUS, perto de você.
                    </span>
                  </span>
                </div>
                <div className="row">
                  <span className="row-main">
                    <span className="row-title">Nutricionista com registro</span>
                    <span className="small muted">
                      Confira o registro no conselho regional (CRN) antes de seguir uma orientação.
                    </span>
                  </span>
                </div>
              </div>
            </section>
          )}

          {mostraFontes && resposta.sources.length === 0 && (
            <Aviso tipo="informacao" titulo="Nenhuma fonte encontrada" Icone={SearchX}>
              Nenhum estudo da base tratou dessa pergunta. Isso não quer dizer que é mentira, nem
              que é verdade: quer dizer que ninguém mediu isso ainda.
            </Aviso>
          )}

          {mostraFontes && resposta.sources.length > 0 && (
            <details className="sources" id="fontes">
              <summary>
                <BookOpen aria-hidden="true" />
                Fontes consultadas <span className="count">({resposta.sources.length})</span>
                <ChevronDown className="chev" aria-hidden="true" />
              </summary>
              <ol className="source-list">
                {resposta.sources.map((fonte, indice) => (
                  <ItemDeFonte key={fonte.chunk_id} fonte={fonte} numero={indice + 1} />
                ))}
              </ol>
            </details>
          )}

          <Avaliacao traceId={resposta.trace_id} />

          <p className="disclaimer">
            <strong>Aviso:</strong> {resposta.disclaimer}
          </p>

          <Botao variante="secundaria" bloco onClick={() => navegar('/')}>
            <Plus aria-hidden="true" />
            Checar outra dúvida
          </Botao>
        </div>
      </main>
    </div>
  );
}
