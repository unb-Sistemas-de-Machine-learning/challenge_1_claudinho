import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Aviso } from '../componentes/Aviso';
import { Botao } from '../componentes/Botao';
import { SeloDeVeredito } from '../componentes/CardDeVeredito';
import { gravar, ler } from '../lib/armazenamento';
import type { ItemDoHistorico } from '../lib/armazenamento';

export function Historico() {
  const navegar = useNavigate();
  const [itens, setItens] = useState<ItemDoHistorico[]>(() => ler('historico'));
  const [confirmando, setConfirmando] = useState(false);

  function apagar() {
    gravar('historico', []);
    setItens([]);
    setConfirmando(false);
  }

  function formatarData(epoch: number) {
    const data = new Date(epoch);
    const hoje = new Date();
    const ontem = new Date();
    ontem.setDate(hoje.getDate() - 1);

    const horaFormatada = data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

    if (data.toDateString() === hoje.toDateString()) {
      return `Hoje, ${horaFormatada}`;
    }
    if (data.toDateString() === ontem.toDateString()) {
      return `Ontem, ${horaFormatada}`;
    }

    return data.toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' }).replace('.', '');
  }

  if (itens.length === 0) {
    return (
      <div className="tela">
        <header className="tela-topo">
          <span className="topbar-title">Histórico</span>
        </header>
        <main className="tela-conteudo">
          <div className="pilha">
            <h1 className="h1">Nenhuma checagem ainda</h1>
            <p className="answer">
              Quando você checar uma dúvida, ela aparece aqui para você rever ou mandar para alguém.
            </p>
            <Botao onClick={() => navegar('/')}>Checar uma dúvida</Botao>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="tela">
      <header className="tela-topo">
        <span className="topbar-title">Histórico</span>
      </header>
      <main className="tela-conteudo">
        <div className="pilha">
          <Aviso tipo="informacao">As checagens ficam salvas só neste aparelho.</Aviso>

          <ul className="historico">
            {itens.map((item) => (
              <li key={item.id} className="historico-item">
                <button
                  className="historico-abrir"
                  onClick={() => navegar(`/resultado/${item.id}`)}
                >
                  <SeloDeVeredito veredito={item.resposta.verdict} />
                  <span className="historico-entrada">{item.entrada}</span>
                  <span className="historico-meta">{formatarData(item.em)}</span>
                </button>
              </li>
            ))}
          </ul>

          <div style={{ marginTop: '24px', textAlign: 'center' }}>
            {confirmando ? (
              <div className="pilha-curta">
                <p>Tem certeza? Isso vai apagar tudo.</p>
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                  <Botao variante="secundaria" onClick={() => setConfirmando(false)}>
                    Cancelar
                  </Botao>
                  <Botao variante="secundaria" onClick={apagar}>
                    Sim, apagar
                  </Botao>
                </div>
              </div>
            ) : (
              <Botao variante="discreta" onClick={() => setConfirmando(true)}>
                Apagar histórico
              </Botao>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
