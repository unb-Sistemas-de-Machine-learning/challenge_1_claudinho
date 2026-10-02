import { Clock, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Botao } from '../componentes/Botao';
import type { ItemDoHistorico } from '../lib/armazenamento';
import { gravar, ler } from '../lib/armazenamento';
import { VEREDITOS } from '../lib/vereditos';

/**
 * Checagens já feitas, guardadas no aparelho.
 *
 * Três decisões que a tela carrega:
 *
 * 1. **A entrada é o título, e não o veredito.** A pessoa procura pelo que perguntou
 *    ("água com limão"), não por "desinformação". O veredito vem ao lado, como rótulo.
 * 2. **Apagar não pede confirmação, mas dá para desfazer.** Diálogo a cada item cansa, e
 *    apagar sem volta pune quem errou o alvo no celular.
 * 3. **O estado vazio diz que fica no aparelho** (Docs/Design/design-system.md, seção 8),
 *    em vez de deixar a pessoa descobrir isso ao trocar de celular.
 */
export function Historico() {
  const navegar = useNavigate();
  const [itens, setItens] = useState<ItemDoHistorico[]>(() => ler('historico'));
  const [apagado, setApagado] = useState<{ item: ItemDoHistorico; posicao: number } | null>(null);

  function salvar(novos: ItemDoHistorico[]) {
    setItens(novos);
    gravar('historico', novos);
  }

  function apagar(item: ItemDoHistorico) {
    const posicao = itens.indexOf(item);
    salvar(itens.filter((guardado) => guardado.id !== item.id));
    setApagado({ item, posicao });
  }

  function desfazer() {
    if (!apagado) return;
    const novos = [...itens];
    novos.splice(apagado.posicao, 0, apagado.item);
    salvar(novos);
    setApagado(null);
  }

  return (
    <div className="tela">
      <header className="tela-topo">
        <span className="topbar-title">Histórico</span>
      </header>
      <main className="tela-conteudo">
        {itens.length === 0 ? (
          <div className="pendente">
            <Clock aria-hidden="true" />
            <h1 className="h2">Suas checagens aparecem aqui</h1>
            <p className="small">
              O histórico fica salvo só neste aparelho: ele não vai junto se você trocar de celular
              ou limpar os dados do navegador.
            </p>
            <Botao onClick={() => navegar('/')}>Fazer uma checagem</Botao>
          </div>
        ) : (
          <ul className="pilha historico">
            {itens.map((item) => {
              const { rotulo, Icone } = VEREDITOS[item.resposta.verdict];
              return (
                <li key={item.id} className="historico-item" data-verdict={item.resposta.verdict}>
                  <button
                    type="button"
                    className="historico-abrir"
                    onClick={() => navegar(`/resultado/${item.id}`)}
                  >
                    <span className="historico-entrada">{item.entrada}</span>
                    <span className="historico-meta small">
                      <Icone aria-hidden="true" />
                      {rotulo} · {formatarData(item.em)}
                    </span>
                  </button>
                  <button
                    type="button"
                    className="historico-apagar"
                    onClick={() => apagar(item)}
                    aria-label={`Apagar a checagem sobre ${item.entrada}`}
                  >
                    <Trash2 aria-hidden="true" />
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {apagado && (
          <div className="toast is-on" role="status" aria-live="polite">
            Checagem apagada.
            <Botao variante="discreta" pequeno onClick={desfazer}>
              Desfazer
            </Botao>
          </div>
        )}
      </main>
    </div>
  );
}

/** "hoje" e "ontem" em vez da data, que é como a pessoa lembra de quando perguntou. */
function formatarData(em: number): string {
  const dia = new Date(em);
  const hoje = new Date();
  const ontem = new Date(hoje);
  ontem.setDate(hoje.getDate() - 1);

  const mesmoDia = (a: Date, b: Date) => a.toDateString() === b.toDateString();
  if (mesmoDia(dia, hoje)) return 'hoje';
  if (mesmoDia(dia, ontem)) return 'ontem';
  return dia.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}
