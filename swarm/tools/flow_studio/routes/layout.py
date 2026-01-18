from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter

router = APIRouter()


LAYOUT_SCREENS: List[dict[str, Any]] = [
    {
        "id": "flows.default",
        "route": "/",
        "title": "Flows - Default",
        "description": "Main Flow Studio screen with run selector, flow list, graph canvas, and inspector.",
        "regions": [
            {
                "id": "header",
                "purpose": "Global navigation, search, governance indicators, mode toggle.",
                "uiids": [
                    "flow_studio.header",
                    "flow_studio.header.search",
                    "flow_studio.header.search.input",
                    "flow_studio.header.search.results",
                    "flow_studio.header.controls",
                    "flow_studio.header.tour",
                    "flow_studio.header.governance",
                    "flow_studio.header.reload",
                    "flow_studio.header.help",
                ],
            },
            {
                "id": "sdlc_bar",
                "purpose": "SDLC progress bar showing flow completion status.",
                "uiids": ["flow_studio.sdlc_bar"],
            },
            {
                "id": "sidebar",
                "purpose": "Run selector, flow list, and view toggles.",
                "uiids": [
                    "flow_studio.sidebar",
                    "flow_studio.sidebar.run_selector",
                    "flow_studio.sidebar.flow_list",
                    "flow_studio.sidebar.view_toggle",
                ],
            },
            {
                "id": "canvas",
                "purpose": "Graph visualization of the current flow and SDLC legend.",
                "uiids": [
                    "flow_studio.canvas",
                    "flow_studio.canvas.graph",
                    "flow_studio.canvas.legend",
                    "flow_studio.canvas.outline",
                ],
            },
            {
                "id": "inspector",
                "purpose": "Details panel for selected step/agent/artifact.",
                "uiids": [
                    "flow_studio.inspector",
                    "flow_studio.inspector.details",
                ],
            },
        ],
    },
    {
        "id": "flows.selftest",
        "route": "/?modal=selftest",
        "title": "Flows - Selftest Modal",
        "description": "Selftest plan / results modal and controls.",
        "regions": [
            {
                "id": "modal",
                "purpose": "Selftest plan, run controls, copy helpers.",
                "uiids": ["flow_studio.modal.selftest"],
            }
        ],
    },
    {
        "id": "flows.shortcuts",
        "route": "/?modal=shortcuts",
        "title": "Flows - Shortcuts Modal",
        "description": "Keyboard shortcuts reference modal.",
        "regions": [
            {
                "id": "modal",
                "purpose": "Keyboard shortcuts grid.",
                "uiids": ["flow_studio.modal.shortcuts"],
            }
        ],
    },
    {
        "id": "flows.validation",
        "route": "/?tab=validation",
        "title": "Flows - Validation View",
        "description": "Governance validation results and FR status badges.",
        "regions": [
            {
                "id": "header",
                "purpose": "Governance badge and overlay toggle.",
                "uiids": ["flow_studio.header.governance"],
            },
            {
                "id": "inspector",
                "purpose": "Validation details for selected agent or flow.",
                "uiids": ["flow_studio.inspector", "flow_studio.inspector.details"],
            },
        ],
    },
    {
        "id": "flows.tour",
        "route": "/?tour=<tour_id>",
        "title": "Flows - Tour Mode",
        "description": "Guided tour overlay with step-by-step navigation.",
        "regions": [
            {
                "id": "header",
                "purpose": "Tour menu and controls.",
                "uiids": ["flow_studio.header.tour"],
            },
            {
                "id": "canvas",
                "purpose": "Tour card overlay on graph nodes.",
                "uiids": ["flow_studio.canvas", "flow_studio.canvas.graph"],
            },
        ],
    },
]


@router.get("/api/layout_screens")
async def api_layout_screens():
    return {
        "version": "0.5.0-flowstudio",
        "screens": LAYOUT_SCREENS,
    }
