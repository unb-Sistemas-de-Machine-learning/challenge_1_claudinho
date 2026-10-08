/**
 * Vocabulário do perfil de saúde.
 *
 * Fica em um lugar só porque duas telas dependem dele: o resumo em `telas/Perfil` e o
 * formulário em `telas/PerfilEdicao`. Se a lista viver dentro de uma das telas, a outra
 * acaba com uma cópia desatualizada, e o usuário vê rótulos diferentes para a mesma coisa.
 *
 * Os valores são os que vão para a API (`conditions`, `dietary_restrictions`, `routine`),
 * então mudar um valor aqui muda o dado gravado: combine com a frente de Dados antes.
 */

import type { Rotina, Sexo } from './api/tipos';

export interface Opcao<T extends string = string> {
  valor: T;
  rotulo: string;
  descricao?: string;
}

export const SEXOS: Opcao<Sexo>[] = [
  { valor: 'F', rotulo: 'Feminino' },
  { valor: 'M', rotulo: 'Masculino' },
  { valor: 'outro', rotulo: 'Outro' },
  { valor: 'nao_informado', rotulo: 'Prefiro não informar' },
];

/** Condições que acionam os filtros de grupo de risco (Docs/Ethics/02). */
export const CONDICOES: Opcao[] = [
  { valor: 'diabetes_tipo_1', rotulo: 'Diabetes tipo 1' },
  { valor: 'diabetes_tipo_2', rotulo: 'Diabetes tipo 2' },
  { valor: 'hipertensao', rotulo: 'Hipertensão' },
  { valor: 'doenca_renal_cronica', rotulo: 'Doença renal crônica' },
  { valor: 'doenca_celiaca', rotulo: 'Doença celíaca' },
  { valor: 'gestante', rotulo: 'Gestação' },
  { valor: 'lactante', rotulo: 'Amamentação' },
  { valor: 'transtorno_alimentar', rotulo: 'Transtorno alimentar, atual ou passado' },
];

export const RESTRICOES: Opcao[] = [
  { valor: 'lactose', rotulo: 'Intolerância à lactose' },
  { valor: 'gluten', rotulo: 'Sem glúten' },
  { valor: 'vegetariana', rotulo: 'Vegetariana' },
  { valor: 'vegana', rotulo: 'Vegana' },
  { valor: 'alergia_alimentar', rotulo: 'Alergia alimentar' },
];

export const ROTINAS: Opcao<Rotina>[] = [
  { valor: 'sedentaria', rotulo: 'Sedentária', descricao: 'Pouco movimento no dia a dia' },
  { valor: 'leve', rotulo: 'Leve', descricao: 'Caminhadas curtas e tarefas de casa' },
  { valor: 'moderada', rotulo: 'Moderada', descricao: 'Exercício algumas vezes por semana' },
  { valor: 'intensa', rotulo: 'Intensa', descricao: 'Treino quase todo dia ou trabalho físico' },
];

/** Traduz o valor guardado para o rótulo que a pessoa lê. */
export function rotuloDe(lista: Opcao[], valor: string): string {
  return lista.find((opcao) => opcao.valor === valor)?.rotulo ?? valor;
}

export function listarRotulos(lista: Opcao[], valores: string[]): string {
  return valores.length ? valores.map((valor) => rotuloDe(lista, valor)).join(', ') : 'Nenhuma';
}

/** Idade em anos a partir da data de nascimento, ou null quando não informada. */
export function idadeDe(nascimento?: string | null): number | null {
  if (!nascimento) return null;
  const data = new Date(`${nascimento}T12:00:00`);
  if (Number.isNaN(data.getTime())) return null;

  const hoje = new Date();
  let idade = hoje.getFullYear() - data.getFullYear();
  if (hoje < new Date(hoje.getFullYear(), data.getMonth(), data.getDate())) idade--;
  return idade;
}
