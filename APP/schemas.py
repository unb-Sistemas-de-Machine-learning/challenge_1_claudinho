"""Modelos do contrato REST descrito em Docs/Production/01_plataforma_e_deploy.md."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

TipoEntrada = Literal["text", "url", "image"]
Veredito = Literal["seguro", "cautela", "desinformacao", "sem_evidencia", "recusa_segura"]


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


class HealthResponse(BaseModel):
    status: Literal["ok"]
    environment: str
    version: str


MotivoFeedback = Literal[
    "fonte_irrelevante",
    "resposta_confusa",
    "parece_errado",
    "tom_julgador",
    "nao_respondeu",
    "outro",
]


class FeedbackRequest(BaseModel):
    trace_id: UUID
    rating: Literal["up", "down"]
    reason: MotivoFeedback | None = None
    comment: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def exige_motivo_quando_negativo(self) -> "FeedbackRequest":
        # Sem motivo, o feedback negativo nao e triavel: nao da para saber se o
        # problema foi recuperacao, geracao ou tom. Ver Docs/Production/02, secao 4.
        if self.rating == "down" and self.reason is None:
            raise ValueError("reason e obrigatorio quando rating e 'down'")
        return self


class FeedbackResponse(BaseModel):
    status: Literal["registered"]
    feedback_id: str


Sexo = Literal["F", "M", "outro", "nao_informado"]
Rotina = Literal["sedentaria", "leve", "moderada", "intensa"]


class Profile(BaseModel):
    """Perfil de saude do usuario.

    LGPD: `conditions` e dado pessoal sensivel (Art. 5o, II). So e persistido
    quando `consent_health_data` for verdadeiro, e nunca aparece nos logs.
    """

    sex: Sexo = "nao_informado"
    birth_date: date | None = None
    height_cm: int | None = Field(default=None, ge=50, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=400)
    conditions: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)
    routine: Rotina | None = None
    consent_health_data: bool = False

    @model_validator(mode="after")
    def exige_consentimento_para_condicoes(self) -> "Profile":
        if self.conditions and not self.consent_health_data:
            raise ValueError("consent_health_data deve ser true para enviar condicoes de saude")
        return self
