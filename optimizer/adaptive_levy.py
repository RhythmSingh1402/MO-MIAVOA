"""
Adaptive Lévy Flight Module
=============================
Implements diversity-scaled and crowding-aware Lévy flight for MO-MIAVOA,
plus a stagnation-triggered reactivation mechanism.

Generic path-planning module: works on any Environment/Path pair produced
by the current optimizer package (no application-specific assumptions).

Combines three complementary mechanisms:

  1. Diversity-scaled magnitude (#2)
     Lévy step size grows automatically as decision-space diversity
     collapses relative to the start of the run. This is self-correcting:
     it does nothing while the population is healthy and spread out, and
     kicks in exactly when the population starts to cluster.

  2. Crowding-aware scaling (#4)
     Individuals sitting in dense (over-crowded) regions of the current
     population/front get larger Lévy jumps, pushing them toward
     unexplored regions. Individuals already in sparse regions get
     smaller jumps so they refine rather than scatter.

  3. Stagnation reactivation (#5)
     If the archive hasn't improved (grown or spread out) for `patience`
     iterations, the most crowded fraction of the population is
     force-restarted with a full-strength Lévy jump around a random
     archive leader — bypassing all of the normal F-gated branch logic.
     This is a cheap safety net for when 1+2 aren't enough.
"""

from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

import config
from environment.models import Path


# ---------------------------------------------------------------------------
# Core Lévy step generator (Mantegna's algorithm) — the single source of
# truth for Lévy sampling. Both mutation.py and miavoa_core.py should call
# this rather than maintaining their own copies, so tuning BETA_LEVY in one
# place changes behaviour everywhere consistently.
# ---------------------------------------------------------------------------

def mantegna_levy(dim: int, beta: Optional[float] = None,
                   rng: np.random.Generator = None) -> np.ndarray:
    """Raw Lévy-distributed step vector via Mantegna's algorithm."""
    if rng is None:
        raise ValueError("rng is required")
    beta = beta if beta is not None else config.BETA_LEVY

    num = math.gamma(1 + beta) * math.sin(math.pi * beta / 2)
    den = math.gamma((1 + beta) / 2) * beta * (2 ** ((beta - 1) / 2))
    sigma = (num / den) ** (1 / beta)

    u = rng.normal(0, sigma, size=dim)
    v = rng.normal(0, 1, size=dim)

    epsilon = 1e-8
    return u / (np.abs(v) ** (1 / beta) + epsilon)


# Backwards-compatible private alias (some callers/tests may import this name).
_mantegna_levy = mantegna_levy


# ---------------------------------------------------------------------------
# #2 — Diversity-scaled magnitude
# ---------------------------------------------------------------------------

def population_diversity(positions: List[np.ndarray], reference: np.ndarray) -> float:
    """Mean distance of all position vectors to a reference point (e.g. leader1)."""
    if not positions:
        return 0.0
    dists = [np.linalg.norm(p - reference) for p in positions]
    return float(np.mean(dists))


class DiversityTracker:
    """
    Tracks decision-space diversity across iterations and exposes a
    self-correcting scale factor: as diversity collapses relative to the
    initial (iteration-0) diversity, the factor rises toward `max_factor`,
    amplifying Lévy step size automatically. When diversity is healthy the
    factor sits near `floor_factor` (effectively "off").
    """

    def __init__(self, max_factor: float = 3.0, floor_factor: float = 1.0):
        self.initial_diversity: Optional[float] = None
        self.max_factor = max_factor
        self.floor_factor = floor_factor
        self.last_value = floor_factor

    def update(self, positions: List[np.ndarray], reference: np.ndarray) -> float:
        div = population_diversity(positions, reference)

        if self.initial_diversity is None:
            self.initial_diversity = max(div, 1e-8)
            self.last_value = self.floor_factor
            return self.last_value

        ratio = div / self.initial_diversity  # ~1.0 at start, -> 0 as it collapses
        ratio = float(np.clip(ratio, 0.0, 1.0))

        # exp(-ratio) rises from ~0.37 (healthy diversity, ratio=1) toward
        # 1.0 (fully collapsed, ratio=0). Rescale into [floor, max].
        raw = math.exp(-ratio)
        raw_norm = (raw - math.exp(-1)) / (1.0 - math.exp(-1))
        raw_norm = float(np.clip(raw_norm, 0.0, 1.0))

        self.last_value = self.floor_factor + raw_norm * (self.max_factor - self.floor_factor)
        return self.last_value


# ---------------------------------------------------------------------------
# #4 — Crowding-aware scaling
# ---------------------------------------------------------------------------

def crowding_scale_factors(crowding_distances: List[float],
                            min_scale: float = 0.3,
                            max_scale: float = 1.0) -> List[float]:
    """
    Convert raw crowding distances into per-individual Lévy scale multipliers.

    Low crowding distance (individual is in a crowded region)  -> high scale
        (jump harder, go find new territory).
    High crowding distance (individual is isolated / on a sparse
        stretch of the front) -> low scale (refine gently, don't scatter
        what's already spread out).
    Infinite distance (boundary point) -> treated like a sparse point;
        it's already well-placed, so only refine.
    """
    if not crowding_distances:
        return []

    finite = [d for d in crowding_distances if np.isfinite(d)]
    if not finite:
        return [max_scale] * len(crowding_distances)

    d_min, d_max = min(finite), max(finite)
    span = d_max - d_min

    factors = []
    for d in crowding_distances:
        if not np.isfinite(d):
            factors.append(min_scale)
            continue
        norm = 0.5 if span == 0 else (d - d_min) / span  # 0=crowded, 1=sparse
        scale = max_scale - norm * (max_scale - min_scale)
        factors.append(float(scale))
    return factors


# ---------------------------------------------------------------------------
# Combined adaptive Lévy jump — usable both from miavoa_core.update_position's
# exploitation sub-phase-2 branch (full-dimensional) and from mutation.py's
# single-waypoint perturbation (dim=2).
# ---------------------------------------------------------------------------

def adaptive_levy_step(dim: int,
                        diversity_factor: float,
                        crowding_factor: float,
                        rng: np.random.Generator,
                        beta: Optional[float] = None) -> np.ndarray:
    """
    Produce a single Lévy jump vector, scaled by both the global diversity
    factor (#2) and the individual's crowding factor (#4).
    """
    raw_step = mantegna_levy(dim, beta, rng)
    base_scale = getattr(config, "LEVY_BASE_SCALE", 0.01)
    return base_scale * diversity_factor * crowding_factor * raw_step


# ---------------------------------------------------------------------------
# #5 — Stagnation-triggered reactivation
# ---------------------------------------------------------------------------

class StagnationTracker:
    """
    Watches archive quality (size + a cheap spread proxy) across iterations.
    If nothing has improved for `patience` iterations, `update()` returns
    True, signalling that a reactivation event should fire this iteration.
    """

    def __init__(self, patience: int = 15):
        self.patience = patience
        self.best_size = -1
        self.best_spread = -1.0
        self.last_improve_iter = 0

    @staticmethod
    def _spread_proxy(archive: List[Path]) -> float:
        """Cheap hypervolume-free proxy: sum of per-objective ranges in the archive."""
        if len(archive) < 2:
            return 0.0
        obj = np.array([p.objectives for p in archive if p.objectives is not None])
        if obj.size == 0:
            return 0.0
        return float(np.sum(obj.max(axis=0) - obj.min(axis=0)))

    def update(self, archive: List[Path], iteration: int) -> bool:
        size = len(archive)
        spread = self._spread_proxy(archive)

        improved = size > self.best_size or spread > self.best_spread * 1.001
        if improved:
            self.best_size = max(self.best_size, size)
            self.best_spread = max(self.best_spread, spread)
            self.last_improve_iter = iteration

        return (iteration - self.last_improve_iter) >= self.patience


def _clip_vector(vec: np.ndarray) -> np.ndarray:
    """
    Local copy of miavoa_core.clip_position, duplicated here (rather than
    imported) to avoid a circular import between miavoa_core and
    adaptive_levy. Clamps [x, y, x, y, ...] pairs to world bounds.
    """
    pos_2d = vec.reshape(-1, 2).copy()
    pos_2d[:, 0] = np.clip(pos_2d[:, 0], 0, config.WORLD_WIDTH)
    pos_2d[:, 1] = np.clip(pos_2d[:, 1], 0, config.WORLD_HEIGHT)
    return pos_2d.flatten()


def stagnation_reactivation(population: List[Path],
                             archive: List[Path],
                             crowding_distances: List[float],
                             create_and_eval_func,
                             rng: np.random.Generator,
                             fraction: float = 0.2,
                             max_feasibility_violation: float = 0.0) -> List[int]:
    """
    Force-restart the most crowded fraction of the population with a
    bounded Lévy jump around a random archive leader, bypassing all normal
    F-gated branch selection. Modifies `population` in place.

    Two safeguards against the reactivation itself corrupting the archive:
      - The jump is capped relative to world size (not leader-coordinate
        magnitude) and always clipped back into bounds before evaluation.
      - A reactivated candidate only replaces the population slot if it's
        at least as feasible as the threshold (default: fully feasible,
        constraint_violation <= 0.0). Infeasible outliers are discarded
        rather than being allowed to become permanent "boundary" members
        of the Pareto archive.

    Returns the list of population indices that were actually reactivated
    (i.e. passed the feasibility gate), so the caller can insert only
    those into the archive.
    """
    if not archive or not population:
        return []

    n = len(population)
    k = max(1, int(n * fraction))

    # Most crowded population members = smallest crowding distance.
    order = np.argsort(crowding_distances)  # ascending: most crowded first
    target_indices = order[:k]

    dim = population[0].to_vector().shape[0]
    boost = getattr(config, "STAGNATION_LEVY_BOOST", 1.5)
    # Cap the jump to a fraction of the world diagonal, not leader magnitude.
    world_diag = float(np.hypot(config.WORLD_WIDTH, config.WORLD_HEIGHT))
    max_step_frac = getattr(config, "STAGNATION_MAX_STEP_FRACTION", 0.15)
    max_step = world_diag * max_step_frac

    reactivated = []

    for idx in target_indices:
        leader = archive[rng.integers(0, len(archive))]
        r_i = leader.to_vector()

        step = adaptive_levy_step(
            dim,
            diversity_factor=boost,
            crowding_factor=1.0,
            rng=rng,
        )
        # Cap per-jump magnitude so a heavy Lévy tail can't fling a
        # waypoint far outside the workable area.
        step = np.clip(step, -max_step, max_step)

        new_vec = _clip_vector(r_i + step)

        new_path = create_and_eval_func(new_vec)

        if new_path.constraint_violation <= max_feasibility_violation:
            population[idx] = new_path
            reactivated.append(int(idx))
        # else: discard silently, leave the original population member in place

    return reactivated