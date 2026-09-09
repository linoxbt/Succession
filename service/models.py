"""Validate seller-controlled public data before storing or rendering it."""
from typing import Annotated, Literal, Any
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, field_validator

Count = Annotated[int, Field(strict=True, ge=0, le=9_007_199_254_740_991)]
Text = Annotated[str, Field(max_length=10_000)]
Hash = Annotated[str, Field(pattern=r'^0x[0-9a-fA-F]{64}$')]


class PublicModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')


class Split(PublicModel):
    sellable: Count = 0
    withheld: Count = 0


class Inventory(PublicModel):
    category: Text
    sellable: Count = 0
    withheld_by_seller: Count = 0
    withheld_without_consent: Count = 0
    total: Count = 0
    depth: Literal['empty','thin','moderate','deep'] = 'empty'
    offerable: bool = False
    newest: Text = ''
    oldest: Text = ''


class Factor(PublicModel):
    name: Text
    value: Text
    explanation: Text = ''
    inputs: dict[str, Any] = Field(default_factory=dict)
    weight: Text = '0'
    contribution: Text = '0'


class Valuation(PublicModel):
    currency: Text = 'USD'
    base_price: Text = '0'
    amount: Text = '0'
    formula: Text = ''
    factors: list[Factor] = Field(default_factory=list, max_length=32)


class Reputation(PublicModel):
    score: Text = '0'
    grade: Text = 'unverified'
    links: Count = 0
    basis: Text = ''
    computed_at: Text = ''
    factors: list[Factor] = Field(default_factory=list, max_length=32)


class ACP(PublicModel):
    agent_address: Text = ''
    agent_id: Count | None = None
    agent_name: Text = ''
    registered: bool = False
    source: Text = 'seller-supplied'
    fetched_at: Text = ''
    completed_jobs: Count = 0
    failed_jobs: Count = 0
    gross_volume: Text = '0'
    distinct_counterparties: Count = 0
    success_rate: Text | None = None
    verifiable_job_ids: list[Count] = Field(default_factory=list, max_length=10_000)
    verification: Text = ''


class Figures(PublicModel):
    self_reported: list[Text] = Field(default_factory=list, max_length=32)
    independently_verifiable: list[Text] = Field(default_factory=list, max_length=32)


class Preview(PublicModel):
    agent_identity: Text = ''
    tenure_days: Count = 0
    counts: dict[str, Count] = Field(default_factory=dict)
    memory_size_bytes: Count = 0
    category_breakdown: dict[str, Count] = Field(default_factory=dict)
    public_counterparties: list[Text] = Field(default_factory=list, max_length=100)
    withheld_non_transferable: Count = 0
    category_transferability: dict[str, Split] = Field(default_factory=dict)
    inventory: dict[str, Inventory] = Field(default_factory=dict)
    disclosure: Text = ''
    committed_root: Hash | None = None
    valuation: Valuation | None = None
    reputation: Reputation | None = None
    acp: ACP | None = None
    provenance_of_figures: Figures = Field(default_factory=Figures)


class CategoryProof(PublicModel):
    category: Text
    subroot: Hash
    leaf_count: Count


class Manifest(PublicModel):
    algorithm: Literal['keccak256']
    construction: Literal['rfc6962-domain-separated']
    root: Hash
    leaf_count: Count
    categories: list[CategoryProof] = Field(max_length=6)


class Lineage(PublicModel):
    owner: Text
    acquired_at: Text
    verified_hash: Hash
    memory_version: Count | None = None


class Header(PublicModel):
    smp_version: Literal['1.0']
    agent_identity: Text
    created_at: Text
    memory_version: Count
    categories: list[Text] = Field(max_length=6)
    provenance_chain: list[Lineage] = Field(max_length=1000)
    integrity_root: Hash
    permissions_hash: Hash
    signature: Text
    engine_schema_version: Count | None = None


class Envelope(PublicModel):
    listing_id: Annotated[str, Field(pattern=r'^[A-Za-z0-9_.-]{1,32}$')]
    hash_commitment: Hash
    nonce: Annotated[str, Field(pattern=r'^[0-9a-fA-F]{24}$')]
    tag: Annotated[str, Field(pattern=r'^[0-9a-fA-F]{32}$')]
    ciphertext: Annotated[str, Field(pattern=r'^(?:[0-9a-fA-F]{2})+$', max_length=32_000_000)]


UNVERIFIED_BASIS = 'Heuristic over seller-supplied history. Historical transfers and ACP outcomes have not been independently verified by this marketplace.'


def public_preview(value: dict) -> dict:
    if not value:
        return {}
    result = Preview.model_validate(value).model_dump(exclude_none=True)
    if result.get('reputation'):
        result['reputation'].update(grade='unverified', basis=UNVERIFIED_BASIS)
    if result.get('acp'):
        result['acp']['verification'] = 'Seller-supplied ACP history; job references require independent verification.'
    result['provenance_of_figures']['independently_verifiable'] = []
    return result
