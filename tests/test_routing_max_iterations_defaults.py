"""Characterization tests for routing max-iteration defaults."""

from swarm.runtime.routing import (
    DecisionType,
    Edge,
    FlowGraph,
    NodeConfig,
    RouteContext,
    RunContext,
    SmartRouter,
    StepOutput,
    StepRouter,
)


def _build_flow_graph(max_loop_iterations: int) -> FlowGraph:
    nodes = {
        "node_a": NodeConfig(node_id="node_a", template_id="node-a"),
        "node_b": NodeConfig(node_id="node_b", template_id="node-b"),
    }
    edges = [
        Edge(
            edge_id="node_a->node_a:loop",
            from_node="node_a",
            to_node="node_a",
            edge_type="loop",
            priority=40,
        ),
        Edge(
            edge_id="node_a->node_b",
            from_node="node_a",
            to_node="node_b",
            edge_type="sequence",
            priority=50,
        ),
    ]
    return FlowGraph(
        graph_id="test-graph",
        nodes=nodes,
        edges=edges,
        policy={"max_loop_iterations": max_loop_iterations},
    )


def test_step_router_policy_max_iterations_over_runtime_fuse() -> None:
    graph = _build_flow_graph(max_loop_iterations=3)
    router = StepRouter()
    context = RunContext(
        run_id="run-1",
        flow_key="flow-a",
        step_output={"status": "UNVERIFIED"},
        iteration_counts={"node_a": 3},
        max_iterations=50,
    )

    result = router.route("node_a", graph, context)

    assert result.edge is not None
    assert result.edge.to_node == "node_b"


def test_smart_router_policy_max_iterations_over_runtime_fuse() -> None:
    graph = _build_flow_graph(max_loop_iterations=3)
    router = SmartRouter()
    step_output = StepOutput(status="UNVERIFIED", can_further_iteration_help=True)
    context = RouteContext(
        run_id="run-1",
        flow_key="flow-a",
        iteration_counts={"node_a": 3},
        max_iterations_default=50,
    )

    decision = router.route("node_a", graph, step_output, context)

    assert decision.next_node_id == "node_b"
    assert decision.decision_type == DecisionType.EXIT_CONDITION
