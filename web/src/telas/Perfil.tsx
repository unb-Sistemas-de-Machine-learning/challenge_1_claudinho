import { ChevronRight, Moon, Pencil, Smartphone, Sun } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { Aviso } from '../componentes/Aviso';
import { Botao } from '../componentes/Botao';
import { Chip } from '../componentes/Chip';
import { ler } from '../lib/armazenamento';
import { CONDICOES, RESTRICOES, ROTINAS, idadeDe, listarRotulos, rotuloDe } from '../lib/perfil';
import type { Tema } from '../lib/tema';
import { definirTema } from '../lib/tema';

const TEMAS: { valor: Tema; rotulo: string; Icone: typeof Sun }[] = [
  { valor: 'auto', rotulo: 'Automático', Icone: Smartphone },
  { valor: 'light', rotulo: 'Claro', Icone: Sun },
  { valor: 'dark', rotulo: 'Escuro', Icone: Moon },
];

/**
 * Perfil: o que o app sabe sobre você e o que você controla.
 *
 * O perfil de saúde fica no aparelho enquanto não houver conta (Docs/Design/design-system.md,
 * secao 8), e a tela diz isso com todas as letras, em vez de deixar a pessoa descobrir
 * quando trocar de celular. Quem preenche é o formulário em `/perfil/editar`.
 */
export function Perfil() {
  const navegar = useNavigate();
  const { state } = useLocation();
  const avisoInicial = (state as { aviso?: string } | null)?.aviso;
  const [aviso, setAviso] = useState<string | null>(avisoInicial ?? null);
  const perfil = ler('perfil');
  const [tema, setTema] = useState<Tema>(ler('tema'));

  useEffect(() => {
    if (!avisoInicial) return;
    const temporizador = setTimeout(() => {
      setAviso(null);
      window.history.replaceState({}, '');
    }, 3000);
    return () => clearTimeout(temporizador);
  }, [avisoInicial]);

  function trocarTema(novo: Tema) {
    definirTema(novo);
    setTema(novo);
  }

  const idade = idadeDe(perfil?.birth_date);

  return (
    <div className="tela">
      <header className="tela-topo">
        <span className="topbar-title">Perfil</span>
      </header>

      <main className="tela-conteudo">
        <div className="pilha">
          {perfil ? (
            <section className="pilha-curta" aria-labelledby="saude">
              <h1 className="h2" id="saude">
                Seu perfil de saúde
              </h1>
              <dl>
                <div className="kv">
                  <dt>Idade</dt>
                  <dd>{idade === null ? 'Não informada' : `${idade} anos`}</dd>
                </div>
                <div className="kv">
                  <dt>Condições</dt>
                  <dd>{listarRotulos(CONDICOES, perfil.conditions)}</dd>
                </div>
                <div className="kv">
                  <dt>Alimentação</dt>
                  <dd>{listarRotulos(RESTRICOES, perfil.dietary_restrictions)}</dd>
                </div>
                <div className="kv">
                  <dt>Rotina</dt>
                  <dd>{perfil.routine ? rotuloDe(ROTINAS, perfil.routine) : 'Não informada'}</dd>
                </div>
              </dl>
              <Botao variante="secundaria" bloco onClick={() => navegar('/perfil/editar')}>
                <Pencil aria-hidden="true" />
                Editar perfil
              </Botao>
            </section>
          ) : (
            <section className="pilha-curta" aria-labelledby="saude">
              <h1 className="h2" id="saude">
                Seu perfil de saúde está vazio
              </h1>
              <p className="lede">
                Preenchendo, eu aviso quando uma informação da internet não combina com a sua
                condição.
              </p>
              <Botao bloco onClick={() => navegar('/perfil/editar')}>
                Preencher perfil
              </Botao>
            </section>
          )}

          <section className="pilha-curta" aria-labelledby="aparencia">
            <h2 className="h3" id="aparencia">
              Aparência
            </h2>
            <div className="chips" role="radiogroup" aria-labelledby="aparencia">
              {TEMAS.map(({ valor, rotulo, Icone }) => (
                <Chip
                  key={valor}
                  tipo="radio"
                  comVisto={false}
                  name="tema"
                  value={valor}
                  checked={tema === valor}
                  onChange={() => trocarTema(valor)}
                >
                  <Icone aria-hidden="true" />
                  {rotulo}
                </Chip>
              ))}
            </div>
            <p className="caption">No automático, o app segue o tema do seu celular.</p>
          </section>

          <section className="pilha-curta" aria-labelledby="conta">
            <h2 className="h3" id="conta">
              Sua conta
            </h2>
            <Aviso
              tipo="informacao"
              titulo="Você está usando sem conta"
              Icone={Smartphone}
              acoes={
                <>
                  <Botao variante="secundaria" pequeno onClick={() => navegar('/conta')}>
                    Criar conta
                  </Botao>
                  <Botao variante="discreta" pequeno onClick={() => navegar('/conta')}>
                    Já tenho conta
                  </Botao>
                </>
              }
            >
              Tudo que você checou e o seu perfil ficam guardados só neste aparelho. Se desinstalar
              o app ou trocar de celular, isso se perde.
            </Aviso>
          </section>

          <section className="pilha-curta" aria-labelledby="privacidade">
            <h2 className="h3" id="privacidade">
              Privacidade
            </h2>
            <div className="rows">
              <button
                className="row"
                onClick={() => navegar('/boas-vindas', { state: { revisao: true } })}
              >
                <span className="row-main">
                  <span className="row-title">Termos de uso e limites</span>
                </span>
                <ChevronRight className="chev" aria-hidden="true" />
              </button>
              <div className="row">
                <span className="row-main">
                  <span className="row-title">Seus dados de saúde</span>
                  <span className="small muted">
                    Condição clínica é dado sensível pela LGPD. Só é guardada com a sua autorização,
                    e nunca aparece nos registros do sistema.
                  </span>
                </span>
              </div>
            </div>
          </section>
        </div>
      </main>
      {aviso && (
        <div className="toast is-on" role="status" aria-live="polite">
          <span>{aviso}</span>
        </div>
      )}
    </div>
  );
}
