/**
 * Contrato REST da API, espelhando APP/schemas.py.
 *
 * Mudou o schema no backend? Mude aqui junto, no mesmo PR. O TypeScript so protege a
 * gente enquanto os dois lados contam a mesma historia.
 *
 * Referencia: Docs/Production/01_plataforma_e_deploy.md, secao 2.
 */

export type TipoDeEntrada = 'text' | 'url' | 'image';

export type Veredito = 'seguro' | 'cautela' | 'desinformacao' | 'sem_evidencia' | 'recusa_segura';

export type NivelDeRisco = 'baixo' | 'medio' | 'alto';

export interface PedidoDeChecagem {
  input_type: TipoDeEntrada;
  text?: string | null;
  url?: string | null;
  image_base64?: string | null;
  /** Quando falso, a resposta ignora o perfil de saude nesta consulta. */
  use_profile?: boolean;
}

export interface Fonte {
  chunk_id: string;
  title: string;
  authors: string;
  journal: string;
  /** Data ISO (YYYY-MM-DD). */
  published_at: string;
  doi: string;
  excerpt: string;
}

export interface RespostaDeChecagem {
  trace_id: string;
  canonical_claim: string;
  verdict: Veredito;
  risk_score: number;
  risk_level: NivelDeRisco;
  answer: string;
  sources: Fonte[];
  disclaimer: string;
  cached: boolean;
  latency_ms: number;
  model_version: string;
  prompt_version: string;
}

export type MotivoDeFeedback =
  | 'fonte_irrelevante'
  | 'resposta_confusa'
  | 'parece_errado'
  | 'tom_julgador'
  | 'nao_respondeu'
  | 'outro';

export interface PedidoDeFeedback {
  trace_id: string;
  rating: 'up' | 'down';
  /**
   * Obrigatorio quando rating e "down" por regra de produto (design system, seção 5).
   * O backend aceita sem, de propósito: ver APP/schemas.py.
   */
  reason?: MotivoDeFeedback | null;
  comment?: string | null;
}

export interface RespostaDeFeedback {
  status: 'registered';
  feedback_id: string;
}

export type Sexo = 'F' | 'M' | 'outro' | 'nao_informado';
export type Rotina = 'sedentaria' | 'leve' | 'moderada' | 'intensa';

export interface Perfil {
  sex: Sexo;
  birth_date?: string | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  /** Dado sensivel (LGPD Art. 5o, II): so pode ir preenchido com consent_health_data. */
  conditions: string[];
  dietary_restrictions: string[];
  routine?: Rotina | null;
  consent_health_data: boolean;
}

/** Codigos de erro do contrato (Docs/Production/01, secao 2.1). */
export type CodigoDeErro =
  | 'invalid_input'
  /** 422: print e link chegam na API, mas OCR e leitura de página ainda não existem. */
  | 'input_nao_suportado'
  | 'unauthorized'
  | 'payload_too_large'
  | 'rate_limited'
  | 'upstream_unavailable'
  | 'profile_not_found'
  | 'sem_conexao'
  | 'desconhecido';

export interface CorpoDeErro {
  error: CodigoDeErro;
  detail?: string;
  retry_after?: number;
}
