import { History, ScanSearch, UserRound } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const ABAS = [
  { para: '/', rotulo: 'Checar', Icone: ScanSearch },
  { para: '/historico', rotulo: 'Histórico', Icone: History },
  { para: '/perfil', rotulo: 'Perfil', Icone: UserRound },
];

/**
 * Tres destinos, nao mais.
 *
 * Some nas telas de checagem e de resultado, para a atenção ficar na resposta. O NavLink
 * ja marca `aria-current="page"` na aba ativa, que e o gancho do estilo e do leitor de tela.
 */
export function BarraDeAbas() {
  return (
    <nav className="tabbar" aria-label="Principal">
      {ABAS.map(({ para, rotulo, Icone }) => (
        <NavLink key={para} to={para} end={para === '/'} className="tab">
          <span className="tab-icon">
            <Icone aria-hidden="true" />
          </span>
          {rotulo}
        </NavLink>
      ))}
    </nav>
  );
}
