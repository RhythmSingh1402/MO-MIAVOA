"""
Combined Objective Evaluator
==============================
Computes the full (T, E, R) objective triple for a path.
Caches results on the Path object to avoid redundant computation.
"""

from __future__ import annotations

from typing import Tuple

from environment.models import Path, Environment
from objectives.time_obj import compute_time
from objectives.energy_obj import compute_energy
from objectives.risk_obj import compute_risk


import config
from environment.collision import minimum_clearance

def evaluate_path(path: Path, env: Environment,
                  force: bool = False) -> Tuple[float, float, float]:
    """
    Evaluate all three objectives for a path.

    Args:
        path: The candidate drone path.
        env: The simulation environment.
        force: If True, recompute even if cached.

    Returns:
        (T, E, R) tuple — all to be minimized.
    """
    if path.objectives is not None and not force:
        return path.objectives

    t = compute_time(path)
    e = compute_energy(path, env.wind_zones)
    r = compute_risk(path, env.buildings, env.wind_zones)

    # Calculate constraint violation (segments violating minimum clearance)
    clearances = minimum_clearance(path, env.buildings)
    path.constraint_violation = float(
        sum(1 for c in clearances if c < config.MIN_CLEARANCE_DIST)
    )

    path.objectives = (t, e, r)
    return path.objectives
