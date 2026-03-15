
import math

def bounty(base_value, scarcity, assembly_weight):
    return base_value * math.log(1 + scarcity) * assembly_weight
