from __future__ import annotations

from typing import Any, Dict, List


def preview_model_policy(category: str, model: str) -> Dict[str, Any]:
    from swarm.config.model_registry import (
        VALID_TIERS,
        load_model_policy,
        resolve_model_tier,
        resolve_station_model,
    )

    policy = load_model_policy()
    resolution_chain: List[str] = []
    model_lower = model.lower()

    if model_lower == "inherit":
        resolution_chain.append(f"inherit -> category '{category}'")
        tier_name = policy.group_assignments.get(category.lower())
        if tier_name:
            resolution_chain.append(f"category -> tier group '{tier_name}'")
            tier_def = policy.tiers.get(tier_name, tier_name)
            if tier_def == "inherit_user_primary":
                resolution_chain.append(
                    f"group '{tier_name}' -> user primary '{policy.user_primary}'"
                )
            elif tier_def in VALID_TIERS:
                resolution_chain.append(f"group '{tier_name}' -> tier '{tier_def}'")
            else:
                resolution_chain.append(f"group '{tier_name}' -> fallback 'sonnet'")
        else:
            resolution_chain.append(f"category '{category}' -> fallback 'sonnet'")
    elif model_lower in VALID_TIERS:
        resolution_chain.append(f"explicit tier '{model_lower}'")
    else:
        resolution_chain.append(f"explicit model ID '{model}'")

    effective_tier = resolve_station_model(model, category, return_tier_alias=True)
    effective_model_id = resolve_model_tier(effective_tier)

    return {
        "requested": {
            "category": category,
            "model": model,
        },
        "effective": {
            "tier": effective_tier,
            "model_id": effective_model_id,
        },
        "resolution_chain": resolution_chain,
    }


def get_model_policy_matrix() -> Dict[str, Any]:
    from swarm.config.model_registry import (
        load_model_policy,
        resolve_model_tier,
        resolve_tier_alias,
    )

    policy = load_model_policy()

    resolved_tiers: Dict[str, str] = {}
    for tier_name, tier_def in policy.tiers.items():
        if tier_def == "inherit_user_primary":
            resolved_tiers[tier_name] = policy.user_primary
        else:
            resolved_tiers[tier_name] = tier_def

    assignments: Dict[str, Dict[str, str]] = {}
    for category, tier_name in policy.group_assignments.items():
        tier_alias = resolve_tier_alias(tier_name, policy)
        model_id = resolve_model_tier(tier_alias)
        assignments[category] = {
            "tier": tier_alias,
            "model_id": model_id,
        }

    return {
        "user_primary": policy.user_primary,
        "tiers": resolved_tiers,
        "assignments": assignments,
    }
