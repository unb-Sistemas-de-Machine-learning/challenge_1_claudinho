import {
  ChevronRight,
  ClipboardPaste,
  ImagePlus,
  Link as IconeLink,
  MessageSquareText,
  Smartphone,
  X,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { Aviso } from '../componentes/Aviso';
import { Botao } from '../componentes/Botao';
import type { PedidoDeChecagem } from '../lib/api/tipos';
import { gravar, ler } from '../lib/armazenamento';

/**
 * Envio de print desligado ate a API ler imagem. Hoje ela recusa com 422
 * `input_nao_suportado`, porque o OCR nao existe: mostrar o botao fazia a pessoa escolher a
 * imagem, esperar e so entao ler que nao da. O codigo fica para quando a leitura existir.
 */
const PRINT_DISPONIVEL = false;

/**
 * Link pelo mesmo motivo: a API ainda nao le pagina e responde 422. Com isto desligado, um
 * link colado sozinho e recusado aqui mesmo, antes da tela de espera, com o caminho que
 * funciona: colar o texto do post. Link junto de texto (o compartilhar do Android faz isso)
 * nao e "so link" e segue normal.
 */
const LINK_DISPONIVEL = false;

/** Limite do contrato para imagem (Docs/Production/01, secao 2.1). */
const MAXIMO_DA_IMAGEM = 5 * 1024 * 1024;

const EXEMPLOS = [
  { texto: 'pão francês inflama o corpo?', tipo: 'texto' as const },
  { texto: 'arroz com feijão é proteína completa mesmo?', tipo: 'texto' as const },
  { texto: 'café faz mal pro coração?', tipo: 'texto' as const },
  { texto: 'kefir de água ajuda na ansiedade?', tipo: 'texto' as const },
  {
    texto: 'quantos dias posso ficar só no suco de limão pra secar 10kg?',
    tipo: 'texto' as const,
  },
];

const ehUrl = (texto: string) => /^(https?:\/\/|www\.)\S+$/i.test(texto.trim());

interface ImagemPreparada {
  /** Só o conteúdo, sem o prefixo `data:` */
  base64: string;
  /** Data URL para mostrar a miniatura na bolha. */
  previa: string;
  /** Explicação do tamanho, ou da redução feita. */
  aviso: string;
}

/** Reduz o print no aparelho antes de enviar, como o design system pede na secao 9. */
async function prepararImagem(arquivo: File): Promise<ImagemPreparada> {
  const emBase64 = (blob: Blob) =>
    new Promise<string>((resolver, rejeitar) => {
      const leitor = new FileReader();
      leitor.onload = () => resolver(String(leitor.result).split(',')[1] ?? '');
      leitor.onerror = () => rejeitar(leitor.error);
      leitor.readAsDataURL(blob);
    });

  if (arquivo.size <= MAXIMO_DA_IMAGEM) {
    const base64 = await emBase64(arquivo);
    return {
      base64,
      previa: `data:${arquivo.type || 'image/jpeg'};base64,${base64}`,
      aviso: formatarTamanho(arquivo.size),
    };
  }

  const bitmap = await createImageBitmap(arquivo);
  const escala = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * escala);
  canvas.height = Math.round(bitmap.height * escala);
  canvas.getContext('2d')?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);

  const reduzido = await new Promise<Blob | null>((resolver) =>
    canvas.toBlob(resolver, 'image/jpeg', 0.82),
  );
  if (!reduzido || reduzido.size > MAXIMO_DA_IMAGEM) {
    throw new Error('imagem grande demais');
  }

  const base64 = await emBase64(reduzido);
  return {
    base64,
    previa: `data:image/jpeg;base64,${base64}`,
    aviso: `Reduzi de ${formatarTamanho(arquivo.size)} para ${formatarTamanho(reduzido.size)}`,
  };
}

function formatarTamanho(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

/**
 * Tela inicial: a pessoa manda a dúvida do jeito que ela chegou.
 *
 * Hoje a entrada que funciona é texto: print e link estão desligados até a API ler imagem
 * e página (PRINT_DISPONIVEL e LINK_DISPONIVEL). Colar fica sempre visível porque é o
 * caminho para trazer o texto de um post (Docs/Design/design-system.md, secao 9).
 */
/**
 * Texto recebido do compartilhar do Android (issue #27).
 *
 * O manifest declara o app como destino de compartilhamento, e o Android abre a tela com
 * `?text=...&url=...`. O link vira parte do texto, e nao um pedido do tipo `url`: a API
 * ainda nao le pagina, e mandar como link so renderia um 422. Assim a pessoa ao menos ve
 * o que compartilhou e pode escrever a duvida em volta.
 */
function textoCompartilhado(): string | null {
  const parametros = new URLSearchParams(window.location.search);
  const partes = [parametros.get('title'), parametros.get('text'), parametros.get('url')]
    .filter((parte): parte is string => Boolean(parte?.trim()))
    // O Android repete o link no "text" e no "url" em vários apps.
    .filter((parte, indice, todas) => todas.indexOf(parte) === indice);

  if (partes.length === 0) return null;
  return partes.join(' ').slice(0, 2000);
}

export function Checar() {
  // Recupera o que a pessoa escreveu e não chegou a virar checagem, depois de um erro
  // ou de um cancelamento. O design system, seção 9, pede isso explicitamente.
  const [texto, setTexto] = useState(() => textoCompartilhado() ?? ler('rascunho'));

  // Limpa a URL para um F5 nao reabrir o mesmo compartilhamento por engano. Fica num
  // efeito, e nao no inicializador do useState: o StrictMode chama o inicializador duas
  // vezes, e limpar na primeira fazia a segunda cair no rascunho.
  useEffect(() => {
    if (window.location.search) {
      window.history.replaceState(window.history.state, '', window.location.pathname);
    }
  }, []);
  const [imagem, setImagem] = useState<ImagemPreparada | null>(null);
  /** Erro do campo de texto. Fica separado do erro da imagem para não pintar a borda errada. */
  const [erro, setErro] = useState<string | null>(null);
  const [erroDaImagem, setErroDaImagem] = useState<string | null>(null);
  const [offline, setOffline] = useState(!navigator.onLine);
  const [instalacaoDispensada, setInstalacaoDispensada] = useState(ler('instalacaoDispensada'));
  const [promptInstalacao, setPromptInstalacao] = useState<any>(null);
  const [estaInstalado, setEstaInstalado] = useState(
    () => window.matchMedia('(display-mode: standalone)').matches,
  );
  const temPerfil = ler('perfil') !== null;
  const arquivoRef = useRef<HTMLInputElement>(null);
  const navegar = useNavigate();
  const { state } = useLocation();
  const [tempoEspera, setTempoEspera] = useState(
    (state as { tentarEm?: number } | null)?.tentarEm ?? 0,
  );

  useEffect(() => {
    const mudou = () => setOffline(!navigator.onLine);
    window.addEventListener('online', mudou);
    window.addEventListener('offline', mudou);

    const media = window.matchMedia('(display-mode: standalone)');
    const alterouDisplayMode = (e: MediaQueryListEvent) => setEstaInstalado(e.matches);
    media.addEventListener('change', alterouDisplayMode);

    const guardouPrompt = (e: Event) => {
      e.preventDefault();
      setPromptInstalacao(e);
    };
    window.addEventListener('beforeinstallprompt', guardouPrompt);

    return () => {
      window.removeEventListener('online', mudou);
      window.removeEventListener('offline', mudou);
      media.removeEventListener('change', alterouDisplayMode);
      window.removeEventListener('beforeinstallprompt', guardouPrompt);
    };
  }, []);

  // Contador regressivo: quando o tempo de espera é maior que 0, diminui 1 a cada segundo
  useEffect(() => {
    if (tempoEspera <= 0) return;
    const intervalo = setInterval(() => {
      setTempoEspera((tempoAtual) => Math.max(0, tempoAtual - 1));
    }, 1000);
    //limpa o intervalo quando o componente sair ou quando o tempo zerar
    return () => clearInterval(intervalo);
  }, [tempoEspera]);

  function checar(valor = texto) {
    const limpo = valor.trim();

    if (!limpo && !imagem) {
      setErro('Escreva a dúvida com suas palavras para eu checar.');
      return;
    }

    if (!LINK_DISPONIVEL && !imagem && ehUrl(limpo)) {
      setErro('Ainda não consigo abrir links. Cole o texto do post ou escreva a dúvida.');
      return;
    }

    gravar('rascunho', '');

    const pedido: PedidoDeChecagem = imagem
      ? { input_type: 'image', image_base64: imagem.base64 }
      : ehUrl(limpo)
        ? { input_type: 'url', url: limpo }
        : { input_type: 'text', text: limpo };

    navegar('/checando', {
      state: {
        pedido,
        entrada: imagem ? 'Print enviado para checagem' : limpo,
        origem: imagem
          ? ({ tipo: 'imagem', src: imagem.previa } as const)
          : ehUrl(limpo)
            ? ({ tipo: 'url', valor: limpo } as const)
            : undefined,
      },
    });
  }

  async function colar() {
    try {
      const copiado = await navigator.clipboard.readText();
      if (copiado) {
        setTexto(copiado);
        gravar('rascunho', copiado);
        setErro(null);
      }
    } catch {
      setErroDaImagem('Não consegui ler a área de transferência. Cole no campo com o teclado.');
    }
  }

  async function escolherImagem(arquivo: File | undefined) {
    if (!arquivo) return;
    try {
      setImagem(await prepararImagem(arquivo));
      setErroDaImagem(null);
      setErro(null);
    } catch {
      setImagem(null);
      setErroDaImagem(
        'Esse print passou de 5 MB mesmo depois de reduzir. Corte a parte que interessa e envie de novo.',
      );
    }
  }

  const tipoDetectado = texto.trim() ? (ehUrl(texto) ? 'Link' : 'Texto') : null;

  return (
    <div className="tela">
      <header className="tela-topo">
        <span className="wordmark">claudinho</span>
      </header>

      <main className="tela-conteudo">
        <div className="pilha">
          <div className="pilha-curta">
            <h1 className="h1">O que você viu por aí?</h1>
            <p className="lede">Escreva com suas palavras ou cole o texto do post.</p>
          </div>

          {offline && (
            <Aviso tipo="informacao" titulo="Você está sem internet">
              Pode escrever a dúvida agora. Eu checo assim que a conexão voltar.
            </Aviso>
          )}

          <div className="pilha-curta">
            <div className={`composer${erro ? ' is-invalid' : ''}`}>
              <label className="sr-only" htmlFor="duvida">
                Sua dúvida ou texto do post
              </label>
              <textarea
                id="duvida"
                value={texto}
                placeholder="Escreva a dúvida ou cole o texto do post"
                aria-invalid={erro ? true : undefined}
                aria-describedby="erro-da-duvida"
                onChange={(evento) => {
                  setTexto(evento.target.value);
                  gravar('rascunho', evento.target.value);
                  if (erro) setErro(null);
                }}
              />

              {imagem && (
                <div className="attach">
                  <span className="small" style={{ fontWeight: 700 }}>
                    Print pronto para enviar
                  </span>
                  <span className="caption">{imagem.aviso}</span>
                  <button
                    type="button"
                    className="icon-btn"
                    aria-label="Remover print"
                    onClick={() => setImagem(null)}
                  >
                    <X aria-hidden="true" />
                  </button>
                </div>
              )}

              <div className="composer-tools">
                <Botao variante="secundaria" pequeno onClick={colar} type="button">
                  <ClipboardPaste aria-hidden="true" />
                  Colar
                </Botao>
                {PRINT_DISPONIVEL && (
                  <Botao
                    variante="secundaria"
                    pequeno
                    type="button"
                    onClick={() => arquivoRef.current?.click()}
                  >
                    <ImagePlus aria-hidden="true" />
                    Enviar print
                  </Botao>
                )}
                {/* A região viva fica sempre no DOM: criada junto com o conteúdo, ela
                    normalmente não é anunciada pelo leitor de tela. */}
                <span className="detected" aria-live="polite">
                  {tipoDetectado === 'Link' && (
                    <>
                      <IconeLink aria-hidden="true" />
                      Link
                    </>
                  )}
                  {tipoDetectado === 'Texto' && (
                    <>
                      <MessageSquareText aria-hidden="true" />
                      Texto
                    </>
                  )}
                </span>
              </div>
            </div>

            {/* Dormente enquanto PRINT_DISPONIVEL for false: quem abre este campo é o botão
                "Enviar print", que hoje não aparece. Fica fora do fluxo de tabulação e
                escondido do leitor de tela de propósito, porque o botão tem rótulo e foco. */}
            <input
              ref={arquivoRef}
              type="file"
              accept="image/*"
              className="campo-de-arquivo"
              tabIndex={-1}
              aria-hidden="true"
              onChange={(evento) => void escolherImagem(evento.target.files?.[0])}
            />

            <div id="erro-da-duvida">
              {erro && (
                <p className="field-error" role="alert">
                  {erro}
                </p>
              )}
            </div>

            {erroDaImagem && (
              <p className="field-error" role="alert">
                {erroDaImagem}
              </p>
            )}
            {tempoEspera > 0 && (
              <p className="field-error" role="alert">
                Muitas checagens seguidas. Aguarde {tempoEspera} segundos para tentar de novo.
              </p>
            )}
          </div>

          <section className="pilha-curta" aria-labelledby="exemplos">
            <h2 className="h3" id="exemplos">
              Dúvidas que chegam muito por aqui
            </h2>
            <div className="examples">
              {EXEMPLOS.map((exemplo) => (
                <button
                  key={exemplo.texto}
                  type="button"
                  className="example"
                  onClick={() => checar(exemplo.texto)}
                >
                  <MessageSquareText aria-hidden="true" />
                  <span>{exemplo.texto}</span>
                </button>
              ))}
            </div>
          </section>
          {!temPerfil && (
            <button className="row" onClick={() => navegar('/perfil/editar')}>
              <span className="row-main">
                <span className="row-title">
                  <strong>Quer que eu leve sua saúde em conta?</strong>
                </span>
                <span className="small muted">
                  Se você tem alguma condição, eu aviso quando uma dica da internet não serve para
                  você.
                </span>
              </span>
              <ChevronRight className="chev" aria-hidden="true" />
            </button>
          )}

          {!instalacaoDispensada && !estaInstalado && (
            <section className="install" aria-labelledby="instalar">
              <div className="install-head">
                <Smartphone aria-hidden="true" />
                <div>
                  <h2 className="h3" id="instalar">
                    Instale na tela inicial
                  </h2>
                  <p className="small muted">
                    Fica na tela do celular como um app, pronto para checar.
                  </p>
                </div>
                <button
                  className="icon-btn"
                  aria-label="Dispensar convite de instalação"
                  onClick={() => {
                    gravar('instalacaoDispensada', true);
                    setInstalacaoDispensada(true);
                  }}
                >
                  <X aria-hidden="true" />
                </button>
              </div>
              {promptInstalacao ? (
                <div style={{ marginTop: '16px' }}>
                  <Botao
                    bloco
                    variante="secundaria"
                    onClick={async () => {
                      promptInstalacao.prompt();
                      const { outcome } = await promptInstalacao.userChoice;
                      if (outcome === 'accepted') {
                        setPromptInstalacao(null);
                      }
                    }}
                  >
                    Instalar aplicativo
                  </Botao>
                </div>
              ) : (
                <details>
                  <summary>Como instalar</summary>
                  <ol>
                    <li>
                      <strong>Android (Chrome):</strong> toque no menu de três pontos e em Instalar
                      app.
                    </li>
                    <li>
                      <strong>iPhone (Safari):</strong> toque em Compartilhar e em Adicionar à Tela
                      de Início. No iPhone, use Colar para checar.
                    </li>
                  </ol>
                </details>
              )}
            </section>
          )}
        </div>
      </main>

      <div className="tela-rodape">
        <Botao bloco disabled={offline || tempoEspera > 0} onClick={() => checar()}>
          {offline ? 'Sem conexão' : tempoEspera > 0 ? `Aguarde ${tempoEspera}s` : 'Checar'}
        </Botao>
      </div>
    </div>
  );
}
