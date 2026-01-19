from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .services.core_service import create_core
from .services.run_inspector import create_run_inspector
from .services.run_service import create_run_service
from .services.tours_service import load_tours
from .services.validation_service import load_validation_data


@dataclass
class FlowStudioState:
    repo_root: Path
    core: Optional[Any]
    run_inspector: Optional[Any]
    run_service: Optional[Any]
    validation_data: Optional[Dict[str, Any]]
    flows_cache: Dict[str, Any] = field(default_factory=dict)
    agents_cache: Dict[str, Any] = field(default_factory=dict)
    agent_flow_index: Dict[str, List[str]] = field(default_factory=dict)
    tours_cache: Dict[str, Any] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)

    def reload_from_disk(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if self.core:
            self.agents_cache, self.flows_cache = self.core.reload()

            # Build agent_flow_index
            self.agent_flow_index.clear()
            for flow_key, flow in self.flows_cache.items():
                for step in flow.get("steps", []):
                    for agent_key in step.get("agents", []):
                        if agent_key not in self.agent_flow_index:
                            self.agent_flow_index[agent_key] = []
                        if flow_key not in self.agent_flow_index[agent_key]:
                            self.agent_flow_index[agent_key].append(flow_key)

        self.tours_cache = load_tours(self.repo_root)
        return self.agents_cache, self.flows_cache


def create_state(repo_root: Path) -> FlowStudioState:
    core = create_core()
    run_inspector = create_run_inspector(repo_root)
    run_service = create_run_service(repo_root)
    validation_data = load_validation_data()

    state = FlowStudioState(
        repo_root=repo_root,
        core=core,
        run_inspector=run_inspector,
        run_service=run_service,
        validation_data=validation_data,
    )
    state.reload_from_disk()
    return state
