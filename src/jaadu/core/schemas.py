from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    CLIMATE = "CLIMATE"
    WATER = "WATER"
    AGRICULTURE = "AGRICULTURE"
    ENERGY = "ENERGY"
    TRANSPORT = "TRANSPORT"
    MARKET = "MARKET"
    HEALTH = "HEALTH"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    POPULATION = "POPULATION"
    POLICY = "POLICY"
    EVENT = "EVENT"
    OUTCOME = "OUTCOME"


class RelationshipType(str, Enum):
    TEMPORAL_ASSOCIATION = "temporal_association"
    SPATIAL_ASSOCIATION = "spatial_association"
    KNOWN_MECHANISM = "known_mechanism"
    OBSERVATIONAL_EVIDENCE = "observational_evidence"
    EXPERIMENTAL_EVIDENCE = "experimental_evidence"
    POLICY_RELATIONSHIP = "policy_relationship"
    HYPOTHESIZED = "hypothesized"


class CausalStatus(str, Enum):
    CORRELATION = "correlation"
    EVIDENCE_SUPPORTED_ASSOCIATION = "evidence_supported_association"
    CAUSAL_HYPOTHESIS = "causal_hypothesis"
    CONFIRMED_CAUSAL = "confirmed_causal"


class Availability(str, Enum):
    AVAILABLE = "available"
    DELAYED = "delayed"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


class ExtractionKind(str, Enum):
    DIRECT_MEASUREMENT = "direct_measurement"
    STRUCTURED_EXTRACT = "structured_extract"
    INTERPRETATION = "interpretation"
    HEURISTIC_EXTRACTION = "heuristic_extraction"


class Observation(BaseModel):
    observation_id: str
    variable: str
    node_type: NodeType
    timestamp: str
    available_at: str
    geo_id: str
    geo_resolution: str
    raw_value: float | None
    value: float | None
    unit: str
    source: str
    source_url: str | None = None
    license: str | None = None
    transformation: str = "none"
    quality_score: float = Field(ge=0, le=1, default=0.8)
    source_reliability: float = Field(ge=0, le=1, default=0.8)
    missingness: float = Field(ge=0, le=1, default=0.0)
    availability: Availability = Availability.AVAILABLE
    notes: str = ""


class EvidenceObject(BaseModel):
    evidence_id: str
    claim: str
    source: str
    source_url: str | None = None
    published_at: str
    ingested_at: str
    geographic_scope: str
    entities: list[str] = Field(default_factory=list)
    variables: list[str] = Field(default_factory=list)
    direction: str | None = None
    magnitude: str | None = None
    time_relationship: str | None = None
    confidence: float = Field(ge=0, le=1)
    supporting_passage: str
    contradictory_passage: str | None = None
    source_reliability: float = Field(ge=0, le=1)
    extraction_kind: ExtractionKind
    extractor: str
    model_name: str | None = None
    provenance_hash: str | None = None


class GraphNode(BaseModel):
    node_id: str
    variable: str
    node_type: NodeType
    geo_id: str
    current_value: float | None = None
    seasonal_z: float | None = None
    trend: float | None = None
    variance: float | None = None
    data_quality: float = 0.0
    confidence: float = 0.0
    availability: Availability = Availability.UNAVAILABLE
    baseline_mean: float | None = None
    n_obs: int = 0


class GraphEdge(BaseModel):
    edge_id: str
    source: str
    target: str
    direction: Literal["forward", "bidirectional", "unknown"] = "forward"
    lag_months: int = 0
    strength: float = 0.0
    uncertainty: float = 1.0
    p_value: float | None = None
    geographic_scope: str
    evidence_count: int = 0
    evidence_ids: list[str] = Field(default_factory=list)
    relationship_type: RelationshipType = RelationshipType.TEMPORAL_ASSOCIATION
    causal_status: CausalStatus = CausalStatus.CORRELATION
    historical_stability: float = 0.0
    method: str = "unknown"
    window_end: str | None = None


class HypothesisScore(BaseModel):
    supporting: float
    contradictory: float
    temporal_consistency: float
    spatial_consistency: float
    mechanism_support: float
    historical_precedent: float
    data_quality: float
    posterior: float
    rank: int


class Hypothesis(BaseModel):
    hypothesis_id: str
    template_id: str
    label: str
    statement: str
    causal_status: CausalStatus = CausalStatus.CAUSAL_HYPOTHESIS
    geo_id: str
    as_of: str
    assumptions: list[str] = Field(default_factory=list)
    expected_moved: list[str] = Field(default_factory=list)
    expected_not_moved: list[str] = Field(default_factory=list)
    supporting_observation_ids: list[str] = Field(default_factory=list)
    contradictory_observation_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradictory_evidence_ids: list[str] = Field(default_factory=list)
    unknown_variables: list[str] = Field(default_factory=list)
    score: HypothesisScore
    invalidation_tests: list[str] = Field(default_factory=list)


class VoICandidate(BaseModel):
    observation_id: str
    label: str
    variable: str
    method: str
    cost_usd: float
    days_required: float
    availability: str
    geographic_coverage: str
    expected_information_gain: float
    expected_uncertainty_reduction: float
    decision_impact: float
    cost_normalized_voi: float
    rank: int
    rationale: str


class AlertReport(BaseModel):
    alert_id: str
    risk: str
    geography: str
    detection_time: str
    earliest_signal: str | None
    current_signals: list[dict[str, Any]]
    discovered_pathway: list[str]
    leading_hypothesis: Hypothesis | None
    alternatives: list[Hypothesis]
    confidence: dict[str, Any]
    expected_development: str
    what_would_invalidate: list[str]
    next_best_observation: VoICandidate | None
    low_regret_action: str
    intervention_vs_investigation: Literal["investigation", "low_regret", "intervention"]
    data_sources: list[str]
    provenance_ids: list[str]


class DatasetRecord(BaseModel):
    dataset_id: str
    name: str
    source: str
    url: str
    country: str
    geographic_resolution: str
    temporal_resolution: str
    start_date: str | None = None
    end_date: str | None = None
    units: str
    license: str
    update_frequency: str
    known_limitations: str
    missingness: str
    quality_score: float
    transformation: str
    variables: list[str]
    why_it_matters: str
    status: Availability
    citation: str
