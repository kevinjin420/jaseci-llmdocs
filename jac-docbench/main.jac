"""Main entry point for jac-docbench server."""

include:jac models.source;
include:jac models.stage;
include:jac models.pipeline;
include:jac config;
include:jac walkers.sources;
include:jac walkers.config;
include:jac walkers.pipeline;
include:jac walkers.websocket;

import:py from time import time;

node Root {
    has initialized: bool = False;
    has created_at: float | None = None;
}

glob root_node: Root | None = None;
glob pipeline_state: PipelineState | None = None;
glob stage_metrics: dict[str, StageMetrics] = {};

can initialize_graph() -> Root {
    """Initialize the root graph structure with pipeline state and stages."""
    global root_node, pipeline_state, stage_metrics;

    if root_node is not None and root_node.initialized {
        return root_node;
    }

    root_node = Root(initialized=True, created_at=time());

    pipeline_state = PipelineState();
    root_node ++> HasPipeline() ++> pipeline_state;

    stage_names = ["fetch", "extract", "assemble"];
    for name in stage_names {
        stage = StageMetrics(name=name);
        pipeline_state ++> HasStage() ++> stage;
        stage_metrics[name] = stage;
    }

    return root_node;
}

can get_root() -> Root {
    """Get or create the root node."""
    global root_node;
    if root_node is None {
        return initialize_graph();
    }
    return root_node;
}

can get_pipeline_state() -> PipelineState {
    """Get the pipeline state node."""
    global pipeline_state;
    if pipeline_state is None {
        initialize_graph();
    }
    return pipeline_state;
}

can get_stage(name: str) -> StageMetrics | None {
    """Get a stage metrics node by name."""
    global stage_metrics;
    if not stage_metrics {
        initialize_graph();
    }
    return stage_metrics.get(name);
}

can get_all_stages() -> list[StageMetrics] {
    """Get all stage metrics nodes."""
    global stage_metrics;
    if not stage_metrics {
        initialize_graph();
    }
    return list(stage_metrics.values());
}

can get_sources() -> list[Source] {
    """Get all source nodes connected to root."""
    root = get_root();
    sources: list[Source] = [];
    for edge in root._jac_.edges {
        if isinstance(edge, HasSource) {
            target = edge._jac_.target;
            if isinstance(target, Source) {
                sources.append(target);
            }
        }
    }
    return sources;
}

can add_source(source: Source) {
    """Add a source to the root graph."""
    root = get_root();
    root ++> HasSource() ++> source;
}

can remove_source(source_id: str) -> bool {
    """Remove a source from the root graph."""
    root = get_root();
    for edge in root._jac_.edges {
        if isinstance(edge, HasSource) {
            target = edge._jac_.target;
            if isinstance(target, Source) and target.id == source_id {
                del edge;
                return True;
            }
        }
    }
    return False;
}

can find_source(source_id: str) -> Source | None {
    """Find a source by ID."""
    for source in get_sources() {
        if source.id == source_id {
            return source;
        }
    }
    return None;
}

with entry {
    initialize_graph();
    print("jac-docbench server initialized");
}
