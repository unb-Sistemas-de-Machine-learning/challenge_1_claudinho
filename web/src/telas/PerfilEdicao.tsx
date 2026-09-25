import { ArrowLeft, ChevronDown, CircleAlert } from 'lucide-react';
import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Aviso } from '../componentes/Aviso';
import { Botao } from '../componentes/Botao';
import { Campo } from '../componentes/Campo';
import { Chip } from '../componentes/Chip';
import { ErroDaApi, MENSAGEM_DE_ERRO, salvarPerfil } from '../lib/api/cliente';
import type { Perfil, Rotina, Sexo } from '../lib/api/tipos';
import { gravar, ler } from '../lib/armazenamento';
import { CONDICOES, RESTRICOES, ROTINAS, SEXOS, idadeDe } from '../lib/perfil';

/**
 * Formulário do perfil de saúde.
 *
 * Tudo aqui é opcional de propósito (Docs/User/02, seção 3.2). Condições clínicas acionam
 * os filtros de grupo de risco de Docs/Ethics/02, e exigem consentimento explícito pela
 * LGPD (Art. 5º, II). Menores de 18 anos são bloqueados preventivamente (LGPD Art. 14).
 */
export function PerfilEdicao() {
  const navegar = useNavigate();
  const perfilSalvo = ler('perfil');

  const [birthDate, setBirthDate] = useState<string>(perfilSalvo?.birth_date ?? '');
  const [sex, setSex] = useState<Sexo>(perfilSalvo?.sex ?? 'nao_informado');
  const [conditions, setConditions] = useState<string[]>(perfilSalvo?.conditions ?? []);
  const [dietaryRestrictions, setDietaryRestrictions] = useState<string[]>(
    perfilSalvo?.dietary_restrictions ?? [],
  );
  const [routine, setRoutine] = useState<Rotina | null>(perfilSalvo?.routine ?? null);
  const [heightCm, setHeightCm] = useState<string>(
    perfilSalvo?.height_cm != null ? String(perfilSalvo.height_cm) : '',
  );
  const [weightKg, setWeightKg] = useState<string>(
    perfilSalvo?.weight_kg != null ? String(perfilSalvo.weight_kg) : '',
  );
  const [consentHealthData, setConsentHealthData] = useState<boolean>(
    Boolean(perfilSalvo?.consent_health_data),
  );
  const [alturaPesoAberto, setAlturaPesoAberto] = useState<boolean>(
    Boolean(perfilSalvo?.height_cm || perfilSalvo?.weight_kg),
  );

  const [erroNascimento, setErroNascimento] = useState<string | null>(null);
  const [erroConsentimento, setErroConsentimento] = useState<string | null>(null);
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const nascimentoRef = useRef<HTMLInputElement>(null);
  const consentRef = useRef<HTMLInputElement>(null);

  function toggleCondicao(valor: string) {
    setConditions((anteriores) =>
      anteriores.includes(valor)
        ? anteriores.filter((item) => item !== valor)
        : [...anteriores, valor],
    );
    setErroConsentimento(null);
  }

  function toggleRestricao(valor: string) {
    setDietaryRestrictions((anteriores) =>
      anteriores.includes(valor)
        ? anteriores.filter((item) => item !== valor)
        : [...anteriores, valor],
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (salvando) return;

    setErroGeral(null);
    setErroNascimento(null);
    setErroConsentimento(null);

    // Validação de Menor de 18 anos (Docs/Ethics/02 e LGPD Art. 14)
    const idade = idadeDe(birthDate);
    if (idade !== null && idade < 18) {
      setErroNascimento(
        'Pela data informada, você tem menos de 18 anos. O Claudinho é só para maiores de idade.',
      );
      nascimentoRef.current?.focus();
      return;
    }

    // Consentimento da LGPD (Art. 5º, II): obrigatório quando houver condições de saúde
    if (conditions.length > 0 && !consentHealthData) {
      setErroConsentimento('Para salvar suas condições de saúde, marque a autorização acima.');
      consentRef.current?.focus();
      return;
    }

    const alturaNum = heightCm.trim() ? Number(heightCm) : null;
    const pesoNum = weightKg.trim() ? Number(weightKg) : null;

    const perfilAEnviar: Perfil = {
      sex: sex || 'nao_informado',
      birth_date: birthDate.trim() ? birthDate.trim() : null,
      height_cm: alturaNum != null && !Number.isNaN(alturaNum) ? alturaNum : null,
      weight_kg: pesoNum != null && !Number.isNaN(pesoNum) ? pesoNum : null,
      conditions,
      dietary_restrictions: dietaryRestrictions,
      routine: routine || null,
      consent_health_data: consentHealthData,
    };

    setSalvando(true);
    try {
      await salvarPerfil(perfilAEnviar);
      gravar('perfil', perfilAEnviar);
      navegar('/perfil', { state: { aviso: 'Perfil salvo' } });
    } catch (erro) {
      setSalvando(false);
      if (erro instanceof ErroDaApi) {
        if (erro.codigo === 'invalid_input') {
          const detalhe = erro.detalhe ?? MENSAGEM_DE_ERRO.invalid_input;
          if (detalhe.includes('consent_health_data')) {
            setErroConsentimento(detalhe);
            consentRef.current?.focus();
          } else {
            setErroGeral(detalhe);
          }
        } else {
          setErroGeral(MENSAGEM_DE_ERRO[erro.codigo] ?? MENSAGEM_DE_ERRO.desconhecido);
        }
      } else {
        setErroGeral('Não foi possível salvar o perfil. Tente novamente.');
      }
    }
  }

  return (
    <div className="tela">
      <header className="tela-topo">
        <button
          className="icon-btn"
          aria-label="Voltar para o perfil"
          onClick={() => navegar('/perfil')}
        >
          <ArrowLeft aria-hidden="true" />
        </button>
        <span className="topbar-title">Perfil de saúde</span>
      </header>

      <form
        id="perfil-form"
        onSubmit={handleSubmit}
        noValidate
        style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}
      >
        <main className="tela-conteudo">
          <div className="pilha">
            <p className="lede screen-title" tabIndex={-1}>
              Tudo aqui é opcional. Preencha só o que fizer sentido para você.
            </p>

            {erroGeral && <Aviso tipo="erro">{erroGeral}</Aviso>}

            <section className="form-section" aria-labelledby="sec-voce">
              <h2 className="h3" id="sec-voce">
                Sobre você
              </h2>
              <div className="field">
                <Campo
                  ref={nascimentoRef}
                  id="birth_date"
                  name="birth_date"
                  rotulo="Data de nascimento"
                  type="date"
                  value={birthDate}
                  onChange={(e) => {
                    setBirthDate(e.target.value);
                    setErroNascimento(null);
                  }}
                  erro={erroNascimento ?? undefined}
                />
                {erroNascimento && (
                  <div style={{ marginTop: 'calc(var(--s-2) * -1)' }}>
                    <Botao variante="discreta" pequeno onClick={() => navegar('/menor-de-idade')}>
                      Tenho menos de 18 anos
                    </Botao>
                  </div>
                )}
              </div>

              <fieldset className="field grupo-opcoes">
                <legend className="field-label" style={{ marginBottom: '8px' }}>
                  Sexo
                </legend>
                <div className="chips" role="radiogroup" aria-label="Sexo">
                  {SEXOS.map((opcao) => (
                    <Chip
                      key={opcao.valor}
                      tipo="radio"
                      name="sex"
                      value={opcao.valor}
                      checked={sex === opcao.valor}
                      onChange={() => setSex(opcao.valor)}
                    >
                      {opcao.rotulo}
                    </Chip>
                  ))}
                </div>
              </fieldset>
            </section>

            <section className="form-section" aria-labelledby="sec-saude">
              <fieldset className="field grupo-opcoes">
                <legend className="h3" id="sec-saude">
                  Condições de saúde
                </legend>
                <p className="field-help">
                  São elas que ativam os avisos de cuidado nas respostas.
                </p>
                <div className="chips">
                  {CONDICOES.map((opcao) => (
                    <Chip
                      key={opcao.valor}
                      tipo="checkbox"
                      name="conditions"
                      value={opcao.valor}
                      checked={conditions.includes(opcao.valor)}
                      onChange={() => toggleCondicao(opcao.valor)}
                    >
                      {opcao.rotulo}
                    </Chip>
                  ))}
                </div>
              </fieldset>

              <div className="field">
                <label className="check" htmlFor="consent" style={{ paddingBottom: 0 }}>
                  <input
                    ref={consentRef}
                    type="checkbox"
                    id="consent"
                    name="consent"
                    checked={consentHealthData}
                    onChange={(e) => {
                      setConsentHealthData(e.target.checked);
                      setErroConsentimento(null);
                    }}
                    aria-describedby={erroConsentimento ? 'consent-erro' : undefined}
                    aria-invalid={erroConsentimento ? true : undefined}
                  />
                  <span>
                    Autorizo o Claudinho a guardar minhas condições de saúde para adaptar as
                    respostas.{' '}
                    <span className="caption" style={{ display: 'block', marginTop: '2px' }}>
                      Dado sensível pela LGPD (Art. 5º, II). Sem essa autorização, as condições não
                      são salvas.
                    </span>
                  </span>
                </label>
                {erroConsentimento && (
                  <p className="field-error" id="consent-erro" role="alert">
                    <CircleAlert aria-hidden="true" />
                    {erroConsentimento}
                  </p>
                )}
              </div>
            </section>

            <section className="form-section" aria-labelledby="sec-alim">
              <fieldset className="field grupo-opcoes">
                <legend className="h3" id="sec-alim">
                  Alimentação
                </legend>
                <div className="chips">
                  {RESTRICOES.map((opcao) => (
                    <Chip
                      key={opcao.valor}
                      tipo="checkbox"
                      name="dietary_restrictions"
                      value={opcao.valor}
                      checked={dietaryRestrictions.includes(opcao.valor)}
                      onChange={() => toggleRestricao(opcao.valor)}
                    >
                      {opcao.rotulo}
                    </Chip>
                  ))}
                </div>
              </fieldset>
            </section>

            <section className="form-section" aria-labelledby="sec-rotina">
              <fieldset className="field grupo-opcoes">
                <legend className="h3" id="sec-rotina">
                  Rotina
                </legend>
                <div className="routine" role="radiogroup" aria-label="Rotina">
                  {ROTINAS.map((opcao) => (
                    <Chip
                      key={opcao.valor}
                      tipo="radio"
                      name="routine"
                      value={opcao.valor}
                      checked={routine === opcao.valor}
                      onChange={() => setRoutine(opcao.valor)}
                      comVisto={false}
                    >
                      <span>
                        {opcao.rotulo}
                        {opcao.descricao && <small>{opcao.descricao}</small>}
                      </span>
                    </Chip>
                  ))}
                </div>
              </fieldset>
            </section>

            <details
              className="more"
              open={alturaPesoAberto}
              onToggle={(e) => setAlturaPesoAberto(e.currentTarget.open)}
            >
              <summary>
                Altura e peso <ChevronDown className="chev" aria-hidden="true" />
              </summary>
              <div className="more-body">
                <p className="field-help">Só se quiser. As respostas nunca comentam o seu peso.</p>
                <div className="grid-2">
                  <Campo
                    id="height_cm"
                    name="height_cm"
                    rotulo="Altura (cm)"
                    type="number"
                    inputMode="numeric"
                    min={50}
                    max={250}
                    value={heightCm}
                    onChange={(e) => setHeightCm(e.target.value)}
                  />
                  <Campo
                    id="weight_kg"
                    name="weight_kg"
                    rotulo="Peso (kg)"
                    type="number"
                    inputMode="decimal"
                    min={20}
                    max={400}
                    value={weightKg}
                    onChange={(e) => setWeightKg(e.target.value)}
                  />
                </div>
              </div>
            </details>
          </div>
        </main>

        <div className="tela-rodape">
          <Botao type="submit" bloco carregando={salvando} disabled={salvando}>
            Salvar perfil
          </Botao>
        </div>
      </form>
    </div>
  );
}
