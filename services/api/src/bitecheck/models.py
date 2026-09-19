"""Pydantic mirror of contract/analyze.schema.json.

Handlers return these, not dicts, so a malformed response fails a local test instead of
silently breaking the frontend. Keep this in lockstep with the schema: a schema change,
a fixture update and a models.py update land in the same commit (see contract/README.md).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

VerdictStatus = Literal["CRITICAL", "WARNING", "CAUTION", "CLEAR", "NO_DATA"]
Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "INFO"]
FindingType = Literal[
    "CONTAMINANT", "RECALL", "LABEL_CLAIM", "ADDITIVE", "LICENSE", "COLD_CHAIN", "ADJUDICATION"
]
Scope = Literal["BRAND", "PRODUCT", "BATCH", "CATEGORY"]
Category = Literal[
    "spices_blends", "supplements_protein", "dairy_perishable", "packaged_snacks",
    "beverages", "infant_food", "oils_fats", "staples_grains", "confectionery",
    "ready_to_eat", "other_food", "non_food",
]
MacroKey = Literal[
    "protein", "carbohydrate", "sugar", "fat", "saturated_fat", "fiber", "sodium", "other"
]
MacroClass = Literal["GOOD", "NEUTRAL", "WATCH", "UNKNOWN"]
AdditiveRisk = Literal["OK", "WATCH", "AVOID"]
NutritionSource = Literal["amazon_label", "openfoodfacts", "catalog", "none"]
FlagCode = Literal[
    "CLAIM_MISMATCH", "ADDED_SUGAR_HIGH", "SODIUM_HIGH", "SATFAT_HIGH",
    "ULTRA_PROCESSED", "INCOMPLETE_LABEL",
]


class Citation(BaseModel):
    label: str
    issuer: str
    date: str | None = None
    sourceUrl: str | None = None
    s3Uri: str | None = None
    excerpt: str | None = None


class Finding(BaseModel):
    id: str
    severity: Severity
    type: FindingType
    scope: Scope
    title: str = Field(max_length=140)
    detail: str
    batches: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(min_length=1)


class Product(BaseModel):
    brand: str | None
    name: str
    category: Category
    netQuantity: str | None = None
    fssaiLicense: str | None = None
    isFoodProduct: bool
    imageUrl: str | None = None


class Verdict(BaseModel):
    status: VerdictStatus
    score: int = Field(ge=0, le=100)
    headline: str = Field(max_length=120)
    summary: str


class MacroEntry(BaseModel):
    key: MacroKey
    label: str
    grams: float = Field(ge=0)
    pct: float = Field(ge=0, le=100)
    class_: MacroClass = Field(alias="class")

    model_config = {"populate_by_name": True}


class NutritionFlag(BaseModel):
    code: FlagCode
    label: str


class Additive(BaseModel):
    ins: str | None = None
    name: str
    risk: AdditiveRisk


class Nutrition(BaseModel):
    basis: Literal["per_100g", "per_100ml"]
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    source: NutritionSource
    macros: list[MacroEntry]
    flags: list[NutritionFlag] = Field(default_factory=list)
    additives: list[Additive] = Field(default_factory=list)
    novaGroup: int | None = Field(default=None, ge=1, le=4)


class Alternative(BaseModel):
    brand: str
    name: str
    why: str
    asin: str | None = None


class Grievance(BaseModel):
    eligible: bool
    reason: str | None = None


class Meta(BaseModel):
    latencyMs: int | None = None
    chunksRetrieved: int | None = None
    findingsDropped: int | None = None
    modelId: str | None = None
    nutritionSource: str | None = None


class AnalyzeResponse(BaseModel):
    """The response body for POST /v1/analyze. Keep in sync with contract/analyze.schema.json."""

    requestId: str
    asin: str = Field(pattern=r"^[A-Z0-9]{10}$")
    cached: bool
    generatedAt: datetime
    product: Product
    verdict: Verdict
    findings: list[Finding]
    nutrition: Nutrition | None = None
    alternatives: list[Alternative] = Field(default_factory=list)
    grievance: Grievance = Field(default_factory=lambda: Grievance(eligible=False))
    meta: Meta | None = None
    disclaimer: str


class AnalyzeRequestExtracted(BaseModel):
    """Extension-only DOM read. Never populated server-side (see resolver.py)."""

    title: str | None = None
    brand: str | None = None
    bullets: list[str] = Field(default_factory=list)
    technicalDetails: dict[str, str] = Field(default_factory=dict)
    ingredientsText: str | None = None
    nutritionTable: list[dict[str, str | None]] = Field(default_factory=list)
    imageUrl: str | None = None


class AnalyzeRequest(BaseModel):
    source: Literal["extension", "web"]
    url: str
    extracted: AnalyzeRequestExtracted | None = None
    forceRefresh: bool = False
