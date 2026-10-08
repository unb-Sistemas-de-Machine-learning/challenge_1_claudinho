import { ArrowLeft } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Aviso } from '../componentes/Aviso';
import { Botao } from '../componentes/Botao';
import { Campo } from '../componentes/Campo';
import { criarConta, emailDaConta, entrar, sair } from '../lib/sessao';

const SENHA_MINIMA = 8;
/** Um @, algo antes, e um domínio com ponto depois. A confirmação de verdade é o e-mail. */
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Criar conta ou entrar, sempre opcional (issue #24).
 *
 * A conta não é exigida para checar: o app já funciona com sessão anônima. Ela serve para
 * entrar de novo na mesma identidade. Perfil e histórico ainda ficam no aparelho
 * (o perfil passa a vir da API com a issue #22).
 *
 * **Criar conta promove a sessão anônima**, em vez de abrir outra: o id do usuário continua
 * o mesmo, então o perfil de saúde já preenchido continua sendo dele. É por isso que a tela
 * fala em "guardar o que já existe" em vez de "cadastre-se".
 *
 * **Entrar numa conta que já existe é diferente**: troca de identidade, e o que estava só na
 * sessão anônima fica para trás. A tela avisa antes, e não depois.
 */
export function Conta() {
  const navegar = useNavigate();
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [modo, setModo] = useState<'criar' | 'entrar'>('criar');
  const [erro, setErro] = useState<string | null>(null);
  const [erroDoEmail, setErroDoEmail] = useState<string | undefined>();
  const [erroDaSenha, setErroDaSenha] = useState<string | undefined>();
  const [enviando, setEnviando] = useState(false);
  const [emailAtual, setEmailAtual] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    let ativo = true;
    void emailDaConta().then((valor) => {
      if (!ativo) return;
      setEmailAtual(valor);
      setCarregando(false);
    });
    return () => {
      ativo = false;
    };
  }, []);

  async function enviar() {
    setErro(null);

    // Erro de preenchimento fica no próprio campo (issue #24); o Aviso geral é para o que
    // volta do Supabase.
    const emailInvalido = !EMAIL.test(email.trim());
    const senhaCurta = senha.length < SENHA_MINIMA;
    setErroDoEmail(emailInvalido ? 'Escreva um email válido, como nome@exemplo.com.' : undefined);
    setErroDaSenha(
      senhaCurta ? `A senha precisa ter pelo menos ${SENHA_MINIMA} caracteres.` : undefined,
    );
    if (emailInvalido || senhaCurta) return;

    setEnviando(true);
    const resultado =
      modo === 'criar' ? await criarConta(email, senha) : await entrar(email, senha);
    setEnviando(false);

    if (!resultado.ok) {
      setErro(resultado.mensagem);
      return;
    }
    navegar('/perfil', {
      replace: true,
      state: { aviso: modo === 'criar' ? 'Conta criada.' : 'Você entrou na sua conta.' },
    });
  }

  async function encerrar() {
    setEnviando(true);
    await sair();
    setEnviando(false);
    navegar('/perfil', { replace: true, state: { aviso: 'Você saiu da conta.' } });
  }

  return (
    <div className="tela">
      <header className="tela-topo">
        <button
          type="button"
          className="icone-botao"
          onClick={() => navegar('/perfil')}
          aria-label="Voltar para o perfil"
        >
          <ArrowLeft aria-hidden="true" />
        </button>
        <span className="topbar-title">Conta</span>
      </header>

      <main className="tela-conteudo pilha">
        {carregando ? null : emailAtual ? (
          <>
            <h1 className="h2">Você está na conta {emailAtual}</h1>
            <p className="small">O histórico e o perfil ainda ficam guardados só neste aparelho.</p>
            <Botao variante="secundaria" onClick={() => void encerrar()} disabled={enviando}>
              Sair da conta
            </Botao>
          </>
        ) : (
          <>
            <h1 className="h2">{modo === 'criar' ? 'Criar conta' : 'Entrar'}</h1>
            <p className="small">
              {modo === 'criar'
                ? 'Opcional. A conta guarda a identidade que você já usa aqui.'
                : 'Ao entrar numa conta que já existe, o que está guardado só neste aparelho fica para trás.'}
            </p>

            {erro && <Aviso tipo="erro">{erro}</Aviso>}

            <Campo
              rotulo="Email"
              type="email"
              autoComplete="email"
              inputMode="email"
              value={email}
              erro={erroDoEmail}
              onChange={(evento) => setEmail(evento.target.value)}
            />
            <Campo
              rotulo="Senha"
              type="password"
              autoComplete={modo === 'criar' ? 'new-password' : 'current-password'}
              ajuda={modo === 'criar' ? `Pelo menos ${SENHA_MINIMA} caracteres.` : undefined}
              value={senha}
              erro={erroDaSenha}
              onChange={(evento) => setSenha(evento.target.value)}
            />

            <Botao onClick={() => void enviar()} disabled={enviando}>
              {modo === 'criar' ? 'Criar conta' : 'Entrar'}
            </Botao>

            <Botao
              variante="discreta"
              onClick={() => {
                setModo(modo === 'criar' ? 'entrar' : 'criar');
                setErro(null);
                setErroDoEmail(undefined);
                setErroDaSenha(undefined);
              }}
            >
              {modo === 'criar' ? 'Já tenho conta' : 'Quero criar uma conta'}
            </Botao>
          </>
        )}
      </main>
    </div>
  );
}
