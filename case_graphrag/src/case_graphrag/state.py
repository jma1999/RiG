from typing import Optional, Dict, Any, List
from typing_extensions import TypedDict
from .models import RouterOutput, RetrievalPlan, QueryArtifact, ExecutionResult


class GraphState(TypedDict, total=False):
    question: str
    router: RouterOutput
    plan: RetrievalPlan

    sparql_query: QueryArtifact
    sparql_validation: Dict[str, Any]
    sparql_result: ExecutionResult

    sql_query: QueryArtifact
    sql_validation: Dict[str, Any]
    sql_result: ExecutionResult

    sql_repair_count: int
    sparql_repair_count: int

    final_answer: str
    evidence: Dict[str, Any]
    errors: List[str]