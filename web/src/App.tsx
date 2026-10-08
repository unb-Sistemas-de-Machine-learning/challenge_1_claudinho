import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { BarraDeAbas } from './componentes/BarraDeAbas';
import { FocoDeTela } from './componentes/FocoDeTela';
import { ler } from './lib/armazenamento';
import { Bloqueado } from './telas/Bloqueado';
import { BoasVindas } from './telas/BoasVindas';
import { Carregando } from './telas/Carregando';
import { Checar } from './telas/Checar';
import { Conta } from './telas/Conta';
import { Historico } from './telas/Historico';
import { Perfil } from './telas/Perfil';
import { PerfilEdicao } from './telas/PerfilEdicao';
import { Resultado } from './telas/Resultado';

/** Rotas que mostram a barra de abas. Checagem e resultado ficam sem, de propósito. */
const COM_ABAS = ['/', '/historico', '/perfil'];

/**
 * Manda para as boas-vindas quem ainda não aceitou os termos.
 *
 * A Docs/Ethics/03, secao 2.2, exige o termo e a confirmação de 18 anos ANTES de
 * qualquer checagem, então a trava fica na rota, não na tela.
 */
function ExigeOnboarding({ children }: { children: React.ReactNode }) {
  if (!ler('onboarded')) return <Navigate to="/boas-vindas" replace />;
  return <>{children}</>;
}

export function App() {
  const { pathname } = useLocation();

  return (
    <div className="app">
      <FocoDeTela />
      <Routes>
        <Route path="/boas-vindas" element={<BoasVindas />} />
        <Route
          path="/"
          element={
            <ExigeOnboarding>
              <Checar />
            </ExigeOnboarding>
          }
        />
        <Route
          path="/checando"
          element={
            <ExigeOnboarding>
              <Carregando />
            </ExigeOnboarding>
          }
        />
        <Route
          path="/resultado/:id"
          element={
            <ExigeOnboarding>
              <Resultado />
            </ExigeOnboarding>
          }
        />
        <Route
          path="/historico"
          element={
            <ExigeOnboarding>
              <Historico />
            </ExigeOnboarding>
          }
        />
        <Route
          path="/perfil"
          element={
            <ExigeOnboarding>
              <Perfil />
            </ExigeOnboarding>
          }
        />
        <Route
          path="/perfil/editar"
          element={
            <ExigeOnboarding>
              <PerfilEdicao />
            </ExigeOnboarding>
          }
        />
        <Route path="/conta" element={<Conta />} />
        <Route path="/menor-de-idade" element={<Bloqueado />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      {COM_ABAS.includes(pathname) && ler('onboarded') && <BarraDeAbas />}
    </div>
  );
}
