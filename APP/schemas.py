"""Modelos do contrato REST descrito em Docs/Production/01_plataforma_e_deploy.md."""

from datetime import date
from typing import Literal

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
