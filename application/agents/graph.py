# LangChain / LangGraph compatibility patch
# 部分 langchain-core 版本会读取 langchain.debug / langchain.verbose，
# 但某些 langchain 版本中这些属性不存在，因此这里做兼容兜底。
try:
    import langchain

    if not hasattr(langchain, "debug"):
        langchain.debug = False  # type: ignore[attr-defined]

    if not hasattr(langchain, "verbose"):
        langchain.verbose = False  # type: ignore[attr-defined]

except Exception:
    pass


from typing import Any, Callable, Dict, Iterable, cast
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from application.agents.state import ContentPilotState
from application.agents.nodes.intake_node import intake_node
from application.agents.nodes.intent_node import intent_node
from application.agents.nodes.rewrite_node import rewrite_node
from application.agents.nodes.route_node import route_node
from application.agents.nodes.retrieve_node import retrieve_node
from application.agents.nodes.compress_node import compress_node
from application.agents.nodes.risk_node import risk_node
from application.agents.nodes.optimize_node import optimize_node
from application.agents.nodes.review_node import review_node
from application.agents.nodes.memory_node import memory_node


NODE_ORDER = [
    "intake_node",
    "intent_node",
    "rewrite_node",
    "route_node",
    "retrieve_node",
    "compress_node",
    "risk_node",
    "optimize_node",
    "review_node",
    "memory_node",
]


RawNode = Callable[[Dict[str, Any]], Dict[str, Any]]


def adapt_node(fn: RawNode) -> Callable[..., Dict[str, Any]]:
    """
    将普通 Dict 节点函数适配为 LangGraph 可调用节点。
    """

    def wrapped(state: Any, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        state_dict: Dict[str, Any] = dict(state)
        result = fn(state_dict)
        return dict(result)

    return wrapped


def add_graph_node(graph: Any, name: str, fn: RawNode) -> None:
    """
    避免 Pylance 对 LangGraph 泛型签名误判。
    """
    graph.add_node(name, cast(Any, adapt_node(fn)))


def route_after_risk(state: ContentPilotState) -> str:
    """
    根据任务类型决定风险检测后的执行路径。

    review_only:
        只做风险质检，跳过内容改写。

    title_generation:
        进入 optimize_node，但 optimize_node 只生成标题建议，不生成正文改写。

    review_and_rewrite:
        执行完整改写流程。
    """
    task_type = state.get("task_type") or "review_and_rewrite"

    if task_type == "review_only":
        return "review_only"

    return "optimize"


def build_state_graph():
    """
    构建 LangGraph StateGraph。

    现在已经不是纯线性流程，而是在 risk_node 后加入条件路由。
    """

    graph = StateGraph(ContentPilotState)

    add_graph_node(graph, "intake_node", intake_node)
    add_graph_node(graph, "intent_node", intent_node)
    add_graph_node(graph, "rewrite_node", rewrite_node)
    add_graph_node(graph, "route_node", route_node)
    add_graph_node(graph, "retrieve_node", retrieve_node)
    add_graph_node(graph, "compress_node", compress_node)
    add_graph_node(graph, "risk_node", risk_node)
    add_graph_node(graph, "optimize_node", optimize_node)
    add_graph_node(graph, "review_node", review_node)
    add_graph_node(graph, "memory_node", memory_node)

    graph.add_edge(START, "intake_node")
    graph.add_edge("intake_node", "intent_node")
    graph.add_edge("intent_node", "rewrite_node")
    graph.add_edge("rewrite_node", "route_node")
    graph.add_edge("route_node", "retrieve_node")
    graph.add_edge("retrieve_node", "compress_node")
    graph.add_edge("compress_node", "risk_node")

    # 关键修改：risk_node 后不再固定进入 optimize_node，而是根据 task_type 条件路由
    cast(Any, graph).add_conditional_edges(
        "risk_node",
        route_after_risk,
        {
            "review_only": "review_node",
            "optimize": "optimize_node",
        },
    )

    graph.add_edge("optimize_node", "review_node")
    graph.add_edge("review_node", "memory_node")
    graph.add_edge("memory_node", END)

    return graph.compile()


class ContentPilotWorkflow:
    """
    LangGraph 工作流封装。

    对外提供：
    - run(): 一次性执行完整流程
    - stream(): 按节点逐步输出事件
    """

    def __init__(self):
        self.graph = build_state_graph()

    def _prepare_state(self, input_state: Dict[str, Any]) -> ContentPilotState:
        state = dict(input_state)

        state.setdefault("task_id", f"T-{uuid4().hex[:12]}")
        state.setdefault("user_id", "default_user")
        state.setdefault("trace", [])
        state.setdefault("errors", [])
        state.setdefault("title_suggestions", [])
        state.setdefault("rewritten_versions", [])

        return cast(ContentPilotState, state)

    def run(self, input_state: Dict[str, Any]) -> Dict[str, Any]:
        state = self._prepare_state(input_state)
        result = self.graph.invoke(state)
        return dict(result)

    def stream(self, input_state: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        state = self._prepare_state(input_state)
        latest_state: Dict[str, Any] = dict(state)

        for chunk in self.graph.stream(state, stream_mode="updates"):
            if not isinstance(chunk, dict):
                continue

            for node_name, node_state in chunk.items():
                if node_name == "__end__":
                    continue

                if isinstance(node_state, dict):
                    latest_state.update(node_state)

                yield {
                    "event": "node_finished",
                    "node": node_name,
                    "trace": latest_state.get("trace", [])[-1:] if latest_state.get("trace") else [],
                }

        yield {
            "event": "finished",
            "result": latest_state,
        }


def build_workflow() -> ContentPilotWorkflow:
    return ContentPilotWorkflow()