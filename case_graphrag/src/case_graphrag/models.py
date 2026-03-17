from __future__ import annotations
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field

Intent = Literal[
    "graph_only",
    "timeseries_only",
    "graph_plus_timeseries",
    "unsupported",
]

AnswerType = Literal[
    "identity_lookup",
    "set_membership",
    "latest_reading",
    "aggregation",
    "coverage",
    "comfort_assessment",
    "count",
    "unknown",
]

class RouterOutput(BaseModel):
    intent: Intent
    answer_type: AnswerType
    confidence: float = Field(ge=0.0, le=1.0)
    rationale_short: str

class EntityHints(BaseModel):
    space_label: Optional[str] = None
    sensor_label: Optional[str] = None
    device_id: Optional[str] = None
    metric_names: List[str] = Field(default_factory=list)
    needs_latest: bool = False
    needs_aggregation: bool = False
    aggregation_fn: Optional[str] = None

class PlanStep(BaseModel):
    step_id: str
    tool: Literal["sql", "sparql", "synthesis"]
    purpose: str

class RetrievalPlan(BaseModel):
    intent: Intent
    entities: EntityHints
    steps: List[PlanStep]
    output_style: Literal["concise", "table", "hybrid"] = "hybrid"

class QueryArtifact(BaseModel):
    query_text: str
    dialect: Literal["sql", "sparql"]
    warnings: List[str] = Field(default_factory=list)

class ExecutionResult(BaseModel):
    ok: bool
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GeneratedSQL(BaseModel):
    sql: str

class GeneratedSPARQL(BaseModel):
    sparql: str

class SynthesizedAnswer(BaseModel):
    answer_markdown: str
    evidence_summary: str

class QueryRepair(BaseModel):
    reasoning: str
    revised_query: str

class ResolvedEntity(BaseModel):
    entity_type: Literal["space", "sensor", "metric", "unknown"]
    original_text: str
    resolved_value: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None

class EntityResolutionOutput(BaseModel):
    resolutions: List[ResolvedEntity]

class DerivedReasoningOutput(BaseModel):
    judgment: str
    rationale: str
    applied_rule: str