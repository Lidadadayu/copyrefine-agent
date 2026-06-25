from typing import Any, Dict
from application.harness.trace_logger import TraceLogger
from infrastructure.retrieval.hybrid_retriever import HybridRetriever


_retriever = None


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever(data_dir="data")
    return _retriever


def reset_retriever_cache() -> None:
    global _retriever
    _retriever = None


def retrieve_node(state: Dict[str, Any]) -> Dict[str, Any]:
    result = get_retriever().retrieve(
        queries=state.get("rewritten_queries", []),
        routes=state.get("retrieval_routes", []),
        platform=state.get("detected_platform") or state.get("platform"),
        content_type=state.get("detected_content_type") or state.get("content_type"),
    )
    state["retrieved_rules"] = result.get("rules", [])
    state["retrieved_risks"] = result.get("risks", [])
    state["retrieved_cases"] = result.get("cases", [])
    state["retrieved_history"] = result.get("history", [])
    TraceLogger.add_trace(
        state,
        "retrieve_node",
        "多路召回完成",
        rules=len(state["retrieved_rules"]),
        risks=len(state["retrieved_risks"]),
        cases=len(state["retrieved_cases"]),
        history=len(state["retrieved_history"]),
    )
    return state
