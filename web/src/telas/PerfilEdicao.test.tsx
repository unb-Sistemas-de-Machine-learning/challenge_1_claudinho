import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { App } from '../App';
import { gravar, ler } from '../lib/armazenamento';
import { servidor } from '../teste/servidor';

function montar(rota = '/perfil/editar') {
  return render(
    <MemoryRouter initialEntries={[rota]}>
      <App />
    </MemoryRouter>,
  );
}

describe('PerfilEdicao', () => {
  beforeEach(() => {
    gravar('onboarded', true);
  });

  it('salvar vazio funciona e volta para o perfil', async () => {
    const usuario = userEvent.setup({ delay: null });
    montar();

    await usuario.click(screen.getByRole('button', { name: 'Salvar perfil' }));

    // Volta para o perfil e exibe aviso de sucesso
    expect(await screen.findByText('Perfil salvo')).toBeInTheDocument();
    expect(screen.getByText('Seu perfil de saúde')).toBeInTheDocument();
    expect(ler('perfil')).toEqual({
      sex: 'nao_informado',
      birth_date: null,
      height_cm: null,
      weight_kg: null,
      conditions: [],
      dietary_restrictions: [],
      routine: null,
      consent_health_data: false,
    });
  });

  it('marcar uma condição sem marcar o consentimento mostra o erro e não chama a API', async () => {
    const usuario = userEvent.setup({ delay: null });
    const chamadaApi = vi.fn();

    servidor.use(
      http.put('*/api/v1/profile', () => {
        chamadaApi();
        return HttpResponse.json({});
      }),
    );

    montar();

    // Marca a condição Diabetes tipo 2
    await usuario.click(screen.getByRole('checkbox', { name: 'Diabetes tipo 2' }));

    // Tenta salvar sem marcar a autorização
    await usuario.click(screen.getByRole('button', { name: 'Salvar perfil' }));

    // Mostra o erro de consentimento
    expect(
      await screen.findByText('Para salvar suas condições de saúde, marque a autorização acima.'),
    ).toBeInTheDocument();

    // Não chama a API nem grava no armazenamento local
    expect(chamadaApi).not.toHaveBeenCalled();
    expect(ler('perfil')).toBeNull();
  });

  it('marcar condição com consentimento salva e o valor aparece no armazenamento local', async () => {
    const usuario = userEvent.setup({ delay: null });
    montar();

    // Marca a condição
    await usuario.click(screen.getByRole('checkbox', { name: 'Diabetes tipo 2' }));

    // Marca o consentimento da LGPD
    await usuario.click(
      screen.getByRole('checkbox', {
        name: /Autorizo o Claudinho a guardar minhas condições de saúde/i,
      }),
    );

    await usuario.click(screen.getByRole('button', { name: 'Salvar perfil' }));

    // Confirmação de sucesso e retorno para /perfil
    expect(await screen.findByText('Perfil salvo')).toBeInTheDocument();
    expect(screen.getByText('Diabetes tipo 2')).toBeInTheDocument();

    // Valor no armazenamento local
    const salvo = ler('perfil');
    expect(salvo?.conditions).toContain('diabetes_tipo_2');
    expect(salvo?.consent_health_data).toBe(true);
  });

  it('data de nascimento de menor de 18 mostra o erro e não salva', async () => {
    const usuario = userEvent.setup({ delay: null });
    const chamadaApi = vi.fn();

    servidor.use(
      http.put('*/api/v1/profile', () => {
        chamadaApi();
        return HttpResponse.json({});
      }),
    );

    montar();

    // Calcula uma data de 16 anos atrás
    const hoje = new Date();
    const anoMenor = hoje.getFullYear() - 16;
    const mes = String(hoje.getMonth() + 1).padStart(2, '0');
    const dia = String(hoje.getDate()).padStart(2, '0');
    const dataMenor = `${anoMenor}-${mes}-${dia}`;

    await usuario.type(screen.getByLabelText(/Data de nascimento/i), dataMenor);
    await usuario.click(screen.getByRole('button', { name: 'Salvar perfil' }));

    expect(
      await screen.findByText(
        'Pela data informada, você tem menos de 18 anos. O Claudinho é só para maiores de idade.',
      ),
    ).toBeInTheDocument();

    // Oferece caminho para /menor-de-idade
    expect(screen.getByRole('button', { name: 'Tenho menos de 18 anos' })).toBeInTheDocument();

    // Não chama a API nem grava no storage
    expect(chamadaApi).not.toHaveBeenCalled();
    expect(ler('perfil')).toBeNull();
  });

  it('quando a API responde 400 invalid_input, a mensagem do erro aparece na tela e o perfil local não é alterado', async () => {
    const usuario = userEvent.setup({ delay: null });

    servidor.use(
      http.put('*/api/v1/profile', () => {
        return HttpResponse.json(
          {
            error: 'invalid_input',
            detail: 'consent_health_data deve ser true para enviar condicoes de saude',
          },
          { status: 400 },
        );
      }),
    );

    montar();

    // Preenche com consentimento para passar na validação local do form
    await usuario.click(screen.getByRole('checkbox', { name: 'Diabetes tipo 2' }));
    await usuario.click(
      screen.getByRole('checkbox', {
        name: /Autorizo o Claudinho a guardar minhas condições de saúde/i,
      }),
    );

    await usuario.click(screen.getByRole('button', { name: 'Salvar perfil' }));

    // A mensagem da API aparece na tela
    expect(
      await screen.findByText('consent_health_data deve ser true para enviar condicoes de saude'),
    ).toBeInTheDocument();

    // Perfil local NÃO é alterado
    expect(ler('perfil')).toBeNull();
  });

  it('carrega o perfil salvo para edição', () => {
    gravar('perfil', {
      sex: 'F',
      birth_date: '1990-05-15',
      height_cm: 165,
      weight_kg: 60,
      conditions: ['hipertensao'],
      dietary_restrictions: ['vegetariana'],
      routine: 'moderada',
      consent_health_data: true,
    });

    montar();

    expect(screen.getByLabelText(/Data de nascimento/i)).toHaveValue('1990-05-15');
    expect(screen.getByRole('radio', { name: 'Feminino' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Hipertensão' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Vegetariana' })).toBeChecked();
    expect(screen.getByRole('radio', { name: /Moderada/ })).toBeChecked();
    expect(
      screen.getByRole('checkbox', {
        name: /Autorizo o Claudinho a guardar minhas condições de saúde/i,
      }),
    ).toBeChecked();
  });

  it('sobrevive a erro de rede sem perder os dados digitados', async () => {
    const usuario = userEvent.setup({ delay: null });

    servidor.use(
      http.put('*/api/v1/profile', () => {
        return HttpResponse.error();
      }),
    );

    montar();

    await usuario.type(screen.getByLabelText(/Data de nascimento/i), '1995-10-20');
    await usuario.click(screen.getByRole('radio', { name: 'Feminino' }));
    await usuario.click(screen.getByRole('button', { name: 'Salvar perfil' }));

    expect(await screen.findByText(/Você está sem internet/i)).toBeInTheDocument();

    // Os dados digitados sobrevivem
    expect(screen.getByLabelText(/Data de nascimento/i)).toHaveValue('1995-10-20');
    expect(screen.getByRole('radio', { name: 'Feminino' })).toBeChecked();
    expect(ler('perfil')).toBeNull();
  });
});
