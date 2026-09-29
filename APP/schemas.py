"""Modelos do contrato REST descrito em Docs/Production/01_plataforma_e_deploy.md."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

TipoEntrada = Literal["text", "url", "image"]
Avaliacao = Literal["up", "down"]
MotivoDeFeedback = Literal[
    "fonte_irrelevante",
    "resposta_confusa",
    "parece_errado",
    "tom_julgador",
    "nao_respondeu",
    "outro",
]
Veredito = Literal["seguro", "cautela", "desinformacao", "sem_evidencia", "recusa_segura"]
Sexo = Literal["F", "M", "outro", "nao_informado"]
Rotina = Literal["sedentaria", "leve", "moderada", "intensa"]

# Idade minima de uso do produto (LGPD Art. 14, ver Docs/Ethics/02).
IDADE_MINIMA = 18
ANO_MINIMO_DE_NASCIMENTO = 1900

# Termo clinico nao passa de algumas palavras. O teto existe porque o perfil vai para
# uma tabela e para o contexto do prompt: sem ele, uma condicao de 10 MB e aceita.
TermoDoPerfil = Annotated[
    str, StringConstraints(min_length=1, max_length=64, strip_whitespace=True)
]


class CheckClaimRequest(BaseModel):
    input_type: TipoEntrada = "text"
    text: str | None = None
    url: str | None = None
    image_base64: str | None = None
    use_profile: bool = True

    @model_validator(mode="after")
    def exige_ao_menos_uma_entrada(self) -> "CheckClaimRequest":
        if not any([self.text, self.url, self.image_base64]):
            raise ValueError("preencha ao menos um entre text, url e image_base64")
        return self


class ExtractClaimRequest(BaseModel):
    """Entrada da extracao rapida (issue #26). So texto: print e link ainda nao sao lidos."""

    text: str = Field(min_length=1, max_length=2000)


class ExtractClaimResponse(BaseModel):
    canonical_claim: str
    safe_refusal: bool


class Fonte(BaseModel):
    chunk_id: str
    title: str
    authors: str
    journal: str
    published_at: date
    doi: str
    excerpt: str


class CheckClaimResponse(BaseModel):
    trace_id: str
    canonical_claim: str
    verdict: Veredito
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["baixo", "medio", "alto"]
    answer: str
    sources: list[Fonte]
    disclaimer: str
    cached: bool
    latency_ms: int
    model_version: str
    prompt_version: str


class FeedbackRequest(BaseModel):
    """Avaliacao de uma resposta — Docs/Production/01, secao 2.2."""

    # UUID e nao str: um trace_id malformado nao amarra em execucao nenhuma,
    # entao e melhor recusar na entrada do que guardar lixo na base de triagem.
    trace_id: UUID
    rating: Avaliacao
    # Opcional de proposito: exigir motivo em todo "down" derrubaria o volume de
    # feedback. Em compensacao, "down" sem motivo e quase inutil para a triagem
    # semanal (Production/02, secao 4) — vale o time decidir se torna obrigatorio
    # depois de ver quanto feedback chega sem motivo.
    reason: MotivoDeFeedback | None = None
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    status: Literal["registered"]
    feedback_id: str


class Profile(BaseModel):
    """Perfil de saude do usuario - Docs/Production/01, secao 2.3.

    LGPD: `conditions` e dado pessoal sensivel (Art. 5o, II). So e aceito quando
    `consent_health_data` for verdadeiro, e nunca aparece no log (Docs/Production/02,
    secao 3.1): o registro guarda apenas se existe condicao, nunca qual.
    """

    sex: Sexo = "nao_informado"
    birth_date: date | None = None
    height_cm: int | None = Field(default=None, ge=50, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=400)
    conditions: list[TermoDoPerfil] = Field(default_factory=list, max_length=20)
    dietary_restrictions: list[TermoDoPerfil] = Field(default_factory=list, max_length=20)
    routine: Rotina | None = None
    consent_health_data: bool = False

    @field_validator("birth_date")
    @classmethod
    def valida_data_de_nascimento(cls, valor: date | None) -> date | None:
        """Recusa data impossivel.

        O campo alimenta os filtros por idade (Docs/Ethics/02), entao uma data no futuro
        viraria idade negativa e o filtro de menor de idade passaria batido.
        """
        if valor is None:
            return valor
        if valor > date.today():
            raise ValueError("birth_date nao pode estar no futuro")
        if valor.year < ANO_MINIMO_DE_NASCIMENTO:
            raise ValueError(f"birth_date anterior a {ANO_MINIMO_DE_NASCIMENTO} nao e valida")
        return valor

    @model_validator(mode="after")
    def exige_consentimento_para_condicoes(self) -> "Profile":
        if self.conditions and not self.consent_health_data:
            raise ValueError("consent_health_data deve ser true para enviar condicoes de saude")
        return self


class HealthResponse(BaseModel):
    status: Literal["ok"]
    environment: str
    version: str
