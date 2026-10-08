import { ThumbsDown, ThumbsUp } from 'lucide-react';
import { useState } from 'react';

import { ErroDaApi, MENSAGEM_DE_ERRO, enviarFeedback } from '../lib/api/cliente';
import type { MotivoDeFeedback } from '../lib/api/tipos';
import { Aviso } from './Aviso';
import { Botao } from './Botao';
import { Chip } from './Chip';

const MOTIVOS: { valor: MotivoDeFeedback; rotulo: string }[] = [
  { valor: 'fonte_irrelevante', rotulo: 'A fonte não tem a ver' },
  { valor: 'resposta_confusa', rotulo: 'Ficou confuso' },
  { valor: 'parece_errado', rotulo: 'Parece errado' },
  { valor: 'tom_julgador', rotulo: 'Me senti julgado' },
  { valor: 'nao_respondeu', rotulo: 'Não respondeu minha dúvida' },
  { valor: 'outro', rotulo: 'Outro motivo' },
];

/**
 * Avaliacao da resposta.
 *
 * O motivo e obrigatorio no "não ajudou" por REGRA DE PRODUTO, do design system, seção 5:
 * sem motivo, a triagem semanal nao sabe se o problema foi recuperacao, geracao ou tom
 * (Docs/Production/02, secao 4). Atenção: o backend ACEITA sem motivo (ver o comentário
 * em APP/schemas.py, que deixou `reason` opcional de propósito para não derrubar o volume
 * de feedback). Se alguém descobrir isso e remover a exigência daqui, vai quebrar a
 * triagem: mude o design system primeiro, e os dois lados juntos.
 */
export function Avaliacao({ traceId }: { traceId: string }) {
  const [nota, setNota] = useState<'up' | 'down' | null>(null);
  const [motivo, setMotivo] = useState<MotivoDeFeedback | null>(null);
  const [comentario, setComentario] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(valor: 'up' | 'down', razao?: MotivoDeFeedback) {
    // Toque duplo em celular lento geraria duas avaliações para a mesma resposta, e a
    // base de re-anotação ganharia duplicata.
    if (enviando) return;
    setEnviando(true);
    setErro(null);
    try {
      await enviarFeedback({
        trace_id: traceId,
        rating: valor,
        reason: razao ?? null,
        comment: comentario.trim() || null,
      });
      setEnviado(true);
    } catch (falha) {
      setErro(
        falha instanceof ErroDaApi ? MENSAGEM_DE_ERRO[falha.codigo] : MENSAGEM_DE_ERRO.desconhecido,
      );
    } finally {
      setEnviando(false);
    }
  }

  if (enviado) {
    return (
      <section className="feedback" aria-labelledby="avaliacao">
        <h2 className="h3" id="avaliacao" tabIndex={-1}>
          Obrigado por avaliar
        </h2>
        <p className="small muted" role="status">
          {nota === 'up'
            ? 'Que bom que ajudou. Isso me mostra o que está funcionando.'
            : 'Avaliação enviada. A equipe usa esses avisos para corrigir as respostas.'}
        </p>
      </section>
    );
  }

  return (
    <section className="feedback" aria-labelledby="avaliacao">
      <h2 className="h3" id="avaliacao">
        Essa resposta ajudou?
      </h2>

      <div className="feedback-row">
        <Botao
          variante="secundaria"
          pequeno
          disabled={enviando}
          aria-pressed={nota === 'up'}
          onClick={() => {
            setNota('up');
            void enviar('up');
          }}
        >
          <ThumbsUp aria-hidden="true" />
          Ajudou
        </Botao>
        <Botao
          variante="secundaria"
          pequeno
          disabled={enviando}
          aria-pressed={nota === 'down'}
          onClick={() => setNota('down')}
        >
          <ThumbsDown aria-hidden="true" />
          Não ajudou
        </Botao>
      </div>

      {nota === 'down' && (
        <>
          <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
            <legend className="small" style={{ fontWeight: 700, marginBottom: 8 }}>
              O que não funcionou?
            </legend>
            <div className="chips">
              {MOTIVOS.map(({ valor, rotulo }) => (
                <Chip
                  key={valor}
                  tipo="radio"
                  name="motivo"
                  value={valor}
                  checked={motivo === valor}
                  onChange={() => setMotivo(valor)}
                >
                  {rotulo}
                </Chip>
              ))}
            </div>
          </fieldset>

          <div className="field">
            <label className="field-label" htmlFor="comentario">
              Quer contar mais? <span className="muted">(opcional)</span>
            </label>
            <textarea
              className="input"
              id="comentario"
              rows={3}
              maxLength={2000}
              style={{ resize: 'vertical' }}
              value={comentario}
              onChange={(evento) => setComentario(evento.target.value)}
            />
          </div>

          <Botao
            bloco
            disabled={!motivo}
            carregando={enviando}
            onClick={() => motivo && void enviar('down', motivo)}
          >
            Enviar avaliação
          </Botao>
          {!motivo && <p className="caption">Escolha um motivo para enviar.</p>}
        </>
      )}

      {erro && (
        <Aviso tipo="erro" titulo="Não consegui enviar sua avaliação">
          {erro}
        </Aviso>
      )}
    </section>
  );
}
