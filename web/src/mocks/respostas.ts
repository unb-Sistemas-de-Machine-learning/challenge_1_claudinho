/**
 * Respostas de exemplo do mock.
 *
 * Os estudos e DOIs sao INVENTADOS, existem so para o app ter o que desenhar enquanto o
 * pipeline nao responde. Nunca use este conteudo em apresentacao como se fosse real.
 *
 * Cobre os cinco vereditos do contrato, que e o conjunto de estados que as telas
 * precisam tratar.
 */

import type { RespostaDeChecagem, Veredito } from '../lib/api/tipos';

const DISCLAIMER =
  'Esta análise tem caráter exclusivamente informativo e é gerada por inteligência artificial com base em literatura científica disponível. Não substitui o diagnóstico, aconselhamento ou tratamento de um nutricionista ou médico.';

function base(parcial: Partial<RespostaDeChecagem>): RespostaDeChecagem {
  return {
    trace_id: crypto.randomUUID(),
    canonical_claim: '',
    verdict: 'seguro',
    risk_score: 0.1,
    risk_level: 'baixo',
    answer: '',
    sources: [],
    disclaimer: DISCLAIMER,
    cached: false,
    latency_ms: 2870,
    model_version: 'mock@0.1.0',
    prompt_version: 'mock-v0',
    ...parcial,
  };
}

export const RESPOSTAS: Record<Veredito, RespostaDeChecagem> = {
  desinformacao: base({
    canonical_claim:
      'O consumo diário de pão francês causa inflamação no organismo de adultos saudáveis?',
    verdict: 'desinformacao',
    risk_score: 0.82,
    risk_level: 'alto',
    answer:
      'Os estudos da base não mostram que o pão francês, dentro de uma alimentação variada, cause inflamação em adultos saudáveis. O que aparece ligado a marcadores de inflamação é o padrão alimentar como um todo, com muito ultraprocessado e pouca fibra, e não um alimento sozinho [Ref: chunk_ex01]. O pão pode continuar no seu café da manhã.',
    sources: [
      {
        chunk_id: 'chunk_ex01',
        title: 'Consumo de pães e marcadores inflamatórios em adultos: revisão sistemática',
        authors: 'Oliveira, M. S.; Costa, L. R.',
        journal: 'Revista de Nutrição',
        published_at: '2022-03-01',
        doi: '10.1590/exemplo.2022.0141',
        excerpt:
          'Não foi observada associação consistente entre o consumo habitual de pão branco e a elevação de proteína C-reativa em adultos sem doenças crônicas.',
      },
    ],
  }),
  seguro: base({
    canonical_claim: 'A combinação de arroz e feijão fornece proteína de qualidade adequada?',
    verdict: 'seguro',
    risk_score: 0.12,
    answer:
      'Arroz e feijão se completam: os aminoácidos que faltam em um aparecem no outro, e juntos eles cobrem o que o corpo precisa. A dupla está associada a uma alimentação de melhor qualidade no Brasil e continua sendo uma escolha acessível [Ref: chunk_ex02].',
    sources: [
      {
        chunk_id: 'chunk_ex02',
        title: 'Complementaridade proteica da combinação arroz e feijão na dieta brasileira',
        authors: 'Pereira, F. A.; Rocha, D. M.',
        journal: 'Revista de Nutrição',
        published_at: '2019-05-01',
        doi: '10.1590/exemplo.2019.0213',
        excerpt:
          'A combinação na proporção habitual fornece todos os aminoácidos essenciais em quantidade adequada para adultos.',
      },
    ],
  }),
  cautela: base({
    canonical_claim: 'O consumo de café aumenta o risco de doenças do coração?',
    verdict: 'cautela',
    risk_score: 0.48,
    risk_level: 'medio',
    answer:
      'Para a maioria dos adultos, três a quatro xícaras por dia não aparecem ligadas a problemas no coração. Pessoas com arritmia ou pressão alta sem controle podem reagir de outro jeito à cafeína, e os estudos com esse grupo ainda são poucos [Ref: chunk_ex03].',
    sources: [
      {
        chunk_id: 'chunk_ex03',
        title: 'Consumo de café e risco cardiovascular: metanálise de estudos de coorte',
        authors: 'Martins, H. G.; Souza, P. R.',
        journal: 'Arquivos Brasileiros de Cardiologia',
        published_at: '2021-08-01',
        doi: '10.1590/exemplo.2021.0776',
        excerpt:
          'O consumo moderado, de três a quatro xícaras diárias, não se associou a aumento do risco cardiovascular.',
      },
    ],
  }),
  sem_evidencia: base({
    canonical_claim: 'O consumo de kefir de água reduz sintomas de ansiedade?',
    verdict: 'sem_evidencia',
    risk_score: 0.5,
    risk_level: 'medio',
    answer:
      'Procurei na base de artigos científicos brasileiros e não encontrei pesquisas que testem kefir de água e ansiedade em pessoas. Isso não quer dizer que é mentira, nem que é verdade. Quer dizer que ninguém mediu isso ainda, ou que o estudo ainda não está na base.',
  }),
  recusa_segura: base({
    canonical_claim: 'Por quantos dias é seguro consumir apenas suco de limão para perder 10 kg?',
    verdict: 'recusa_segura',
    risk_score: 0.95,
    risk_level: 'alto',
    answer:
      'Compreendo a vontade de ter resultados rápidos, mas práticas como restrições extremas ou uso de substâncias sem indicação trazem riscos sérios à saúde (como fraqueza, deficiências nutricionais e alterações metabólicas). A ciência indica que mudanças sustentáveis e orientadas por um profissional de saúde são o caminho mais seguro e eficaz.',
  }),
};

/**
 * Escolhe a resposta pelo texto, para o mock parecer que entendeu a pergunta.
 * Quem estiver desenvolvendo consegue exercitar cada veredito sem mexer no codigo.
 */
export function respostaPara(texto: string): RespostaDeChecagem {
  const t = texto.toLowerCase();

  // `trace_id` novo a cada chamada, como a API faz: um valor fixo por veredito
  // esconderia colisão de identificador no histórico.
  const comTraceNovo = (r: RespostaDeChecagem): RespostaDeChecagem => ({
    ...r,
    trace_id: crypto.randomUUID(),
  });

  // Limite de palavra em Unicode, e nao \b: em JavaScript o \b usa a tabela ASCII, entao
  // "café" nao casaria com /\bcaf[eé]\b/ por causa do acento. O mesmo cuidado vale no
  // backend, onde casar por substring ja trocou "cream cracker" por "crack".
  const contem = (termo: string) => new RegExp(`(?<!\\p{L})${termo}(?!\\p{L})`, 'u').test(t);

  if (/secar|laxante|purga/.test(t) || (contem('dias') && /(s[óo]|apenas)/.test(t)))
    return comTraceNovo(RESPOSTAS.recusa_segura);
  if (contem('p[ãa]o') || contem('lim[ãa]o')) return comTraceNovo(RESPOSTAS.desinformacao);
  if (contem('caf[ée]')) return comTraceNovo(RESPOSTAS.cautela);
  if (contem('arroz') || contem('feij[ãa]o')) return comTraceNovo(RESPOSTAS.seguro);
  return comTraceNovo(RESPOSTAS.sem_evidencia);
}
