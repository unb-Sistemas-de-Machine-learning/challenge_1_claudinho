import { Baby, ClipboardX, HeartPulse, ShieldCheck, Stethoscope, Zap } from 'lucide-react';
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { Botao } from '../componentes/Botao';
import { gravar } from '../lib/armazenamento';
import { CONTA_DISPONIVEL } from '../lib/sessao';

/**
 * Primeiro acesso.
 *
 * Os cinco termos vem da Docs/Ethics/03, secao 2.2, homologados pela frente de Ética:
 * mude o texto la primeiro, aqui depois. A confirmação de 18 anos e obrigatória antes de
 * qualquer checagem (LGPD Art. 14), por isso o botao só libera com a caixa marcada.
 *
 * Esta tela e a REFERENCIA de implementação para as outras: estrutura de tela com topo,
 * conteúdo e rodapé, componentes do design system, e estado do aparelho via
 * lib/armazenamento. Copie o formato daqui.
 */

const TERMOS = [
  {
    Icone: ClipboardX,
    titulo: 'Não fazemos prescrições',
    texto:
      'O aplicativo não elabora dietas, planos alimentares ou recomendações de suplementação individualizadas.',
  },
  {
    Icone: Stethoscope,
    titulo: 'Não substitui profissionais de saúde',
    texto: 'Nenhuma resposta substitui consultas com nutricionistas ou médicos.',
  },
  {
    Icone: HeartPulse,
    titulo: 'Públicos com necessidades especiais',
    texto:
      'Se você possui condições clínicas (como diabetes, hipertensão ou doença celíaca), gestação ou histórico de transtornos alimentares, consulte sempre seu profissional de referência.',
  },
  {
    Icone: Baby,
    titulo: 'Gestantes e lactantes',
    texto:
      'Se você está grávida ou amamentando, não siga recomendações genéricas de internet. A nutrição gestacional exige acompanhamento pré-natal individualizado para evitar riscos ao desenvolvimento fetal.',
  },
  {
    Icone: ShieldCheck,
    titulo: 'Uso exclusivo para maiores de 18 anos',
    texto:
      'O aplicativo é de uso estritamente proibido para menores de idade, em conformidade com o Art. 14 da LGPD sobre tratamento de dados de saúde de crianças e adolescentes.',
  },
];

export function BoasVindas() {
  const [aceitou, setAceitou] = useState(false);
  const navegar = useNavigate();
  const { state } = useLocation();
  // Quem chega pelo Perfil está relendo os termos, e não aceitando de novo: sem isto, a
  // pessoa fica presa numa tela sem saída, com a caixa desmarcada.
  const revisao = Boolean((state as { revisao?: boolean } | null)?.revisao);

  function comecar() {
    gravar('onboarded', true);
    navegar('/', { replace: true });
  }

  return (
    <div className="tela">
      <main className="tela-conteudo">
        <div className="pilha">
          <section className="hero">
            <span className="wordmark">claudinho</span>
            <h1 className="hero-title">Viu algo sobre comida na internet e bateu a dúvida?</h1>
            <p>
              Me manda o post ou a pergunta. Eu checo nos estudos científicos brasileiros e te
              explico sem complicar.
            </p>
            <p className="hero-nota">
              <Zap aria-hidden="true" />
              Sem cadastro para começar
            </p>
          </section>

          <section className="pilha-curta" aria-labelledby="termos">
            <h2 className="h2" id="termos">
              Importante saber antes de usar
            </h2>
            <ul className="terms">
              {TERMOS.map(({ Icone, titulo, texto }) => (
                <li className="term" key={titulo}>
                  <Icone aria-hidden="true" />
                  <div>
                    <strong>{titulo}</strong>
                    {texto}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </main>

      <div className="tela-rodape">
        {revisao ? (
          <Botao bloco variante="secundaria" onClick={() => navegar('/perfil')}>
            Voltar para o perfil
          </Botao>
        ) : (
          <>
            <label className="check" htmlFor="aceite" style={{ paddingBlock: '0 4px' }}>
              <input
                type="checkbox"
                id="aceite"
                checked={aceitou}
                onChange={(evento) => setAceitou(evento.target.checked)}
              />
              <span>Tenho 18 anos ou mais e concordo com esses termos.</span>
            </label>
            <Botao bloco disabled={!aceitou} onClick={comecar}>
              Começar a checar
            </Botao>
            <div className="rodape-links">
              {CONTA_DISPONIVEL && (
                <Botao variante="discreta" pequeno onClick={() => navegar('/conta')}>
                  Já tenho conta
                </Botao>
              )}
              <Botao variante="discreta" pequeno onClick={() => navegar('/menor-de-idade')}>
                Tenho menos de 18
              </Botao>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
