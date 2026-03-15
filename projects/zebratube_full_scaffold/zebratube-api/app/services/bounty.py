import math

def compute_bounty(base_value: float, submission_count: int, assembly_weight: float) -> float:
    scarcity = 1.0 / (1.0 + submission_count)
    return round(base_value * math.log(1 + scarcity) * assembly_weight, 2)
