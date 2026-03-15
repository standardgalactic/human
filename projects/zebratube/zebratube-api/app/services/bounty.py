"""
bounty.py — bounty calculation service

B(task) = base_value × log(1 + scarcity) × assembly_weight

where:
    scarcity        = 1 / (1 + submission_count)
    assembly_weight = normalized betweenness centrality, range [0.5, 2.0]

Scarcity falls as submissions accumulate, rewarding early contributors
and bottleneck tasks over already-saturated ones.
"""

import math
from dataclasses import dataclass


@dataclass
class BountyComponents:
    base_value:      int
    submission_count: int
    assembly_weight: float
    scarcity:        float
    bounty:          float
    breakdown:       dict


def compute_bounty(
    base_value:       int   = 100,
    submission_count: int   = 0,
    assembly_weight:  float = 1.0,
    is_first:         bool  = False,
) -> BountyComponents:
    """Return bounty components for a task."""
    scarcity = 1.0 / (1.0 + submission_count)
    raw      = base_value * math.log1p(scarcity) * assembly_weight
    bounty   = round(raw, 1)

    breakdown = {
        "base_value":       base_value,
        "scarcity":         round(scarcity, 4),
        "log_scarcity":     round(math.log1p(scarcity), 4),
        "assembly_weight":  round(assembly_weight, 3),
        "raw":              round(raw, 2),
        "first_bonus":      round(bounty * 0.2, 1) if is_first else 0,
    }
    if is_first:
        bounty += breakdown["first_bonus"]

    return BountyComponents(
        base_value=base_value,
        submission_count=submission_count,
        assembly_weight=assembly_weight,
        scarcity=round(scarcity, 4),
        bounty=bounty,
        breakdown=breakdown,
    )


def award_submission_accepted(bounty: float) -> int:
    return round(bounty)


def award_submission_reviewed(bounty: float) -> int:
    return round(bounty * 0.1)


def award_selector_comparison(task_bounty: float) -> int:
    return max(1, round(task_bounty * 0.05))


def award_assembly(segment_bounties: list[float]) -> int:
    return round(sum(segment_bounties) * 0.3)


def tier_from_points(points: int) -> str:
    if points >= 2000: return "assembler"
    if points >= 500:  return "producer"
    if points >= 50:   return "contributor"
    return "observer"
