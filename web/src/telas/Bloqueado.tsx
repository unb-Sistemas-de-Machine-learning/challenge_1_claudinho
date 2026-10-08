import { ArrowLeft, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

/**
 * Recusa de serviço para menores de 18 anos.
 *
 * O texto é o da Docs/Ethics/02, tabela de filtros: tratar dado de saúde de menor exige
 * consentimento do responsável (LGPD Art. 14), o que está fora do escopo do MVP. A
 * recusa é acolhedora e aponta um caminho, em vez de só fechar a porta.
 */
export function Bloqueado() {
  const navegar = useNavigate();

  return (
    <div className="tela">
      <header className="tela-topo">
        <button
          className="icon-btn"
          aria-label="Voltar para as boas-vindas"
          onClick={() => navegar('/boas-vindas')}
        >
          <ArrowLeft aria-hidden="true" />
        </button>
      </header>

      <main className="tela-conteudo">
        <div className="centro">
          <span className="icone-grande">
            <ShieldCheck aria-hidden="true" />
          </span>
          <h1 className="h1">O Claudinho é só para maiores de 18 anos</h1>
          <p className="lede">
            O uso deste aplicativo é restrito a maiores de 18 anos (LGPD Art. 14). Recomendamos
            consultar um nutricionista com seu responsável legal.
          </p>
          <p className="small muted">
            Na UBS mais perto de você dá para marcar consulta com nutricionista pelo SUS.
          </p>
        </div>
      </main>
    </div>
  );
}
