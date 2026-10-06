"""
MO-MIAVOA Main Orchestrator
=============================
Executes the MO-MIAVOA algorithm, combining the base MIAVOA equations
with multi-objective Pareto archive and GA components.

Wired with adaptive Lévy flight:
  - diversity-scaled magnitude (global, per-iteration)
  - crowding-aware scaling (per-individual)
  - stagnation-triggered reactivation (safety net)
  - a lightweight elitism guard that protects the current best-compromise
    solution from being pruned out by aggressive exploration

This orchestrator is application-agnostic: it only depends on
environment.models.Path / Environment and the optimizer package, so it
works for any waypoint-based path-planning test scenario built on top of
those.
"""

from __future__ import annotations

import numpy as np
from typing import List, Tuple, Optional

import config
from environment.models import Path, Environment
from environment.collision import segment_is_feasible
from objectives.evaluator import evaluate_path
from optimizer.archive import try_insert, constrained_dominates, compute_crowding_distances
from optimizer.leader_selection import select_leader_pool, select_leader_roulette
from optimizer.miavoa_core import gqrbl_initialization, update_position, compute_hunger
from optimizer.crossover import splice_crossover, repair_to_feasible
from optimizer.mutation import adaptive_levy_mutation, bounded_detour_mutation
from optimizer.adaptive_levy import (
    DiversityTracker,
    StagnationTracker,
    crowding_scale_factors,
    stagnation_reactivation,
)


def select_best_compromise(archive: List[Path]) -> Path:
    """
    Pick a single "best compromise" solution from the Pareto archive using
    a simple min-max-normalized distance-to-ideal-point (knee-point) rule:
    for each objective, 0 = best value seen in the archive, 1 = worst;
    the archive member with the smallest Euclidean distance to (0, 0, ...)
    wins. Feasible members are always preferred over infeasible ones.

    This is a self-contained replacement for an external final-selection
    module — no outside dependency required.
    """
    if not archive:
        raise ValueError("Cannot select a compromise from an empty archive.")

    feasible = [p for p in archive if p.constraint_violation <= 0.0 and p.objectives is not None]
    pool = feasible if feasible else [p for p in archive if p.objectives is not None]

    if not pool:
        # No evaluated members at all — just return the first entry.
        return archive[0]

    if len(pool) == 1:
        return pool[0]

    obj = np.array([p.objectives for p in pool])
    obj_min = obj.min(axis=0)
    obj_max = obj.max(axis=0)
    span = obj_max - obj_min
    span[span == 0] = 1.0  # avoid divide-by-zero for objectives with no spread

    normalized = (obj - obj_min) / span
    dist_to_ideal = np.linalg.norm(normalized, axis=1)

    best_idx = int(np.argmin(dist_to_ideal))
    return pool[best_idx]


class MOMIAVOA:
    def __init__(self, env: Environment, seed: int = None):
        self.env = env
        self.rng = np.random.default_rng(seed if seed is not None else config.RANDOM_SEED)

        self.population: List[Path] = []
        self.archive: List[Path] = []
        self.dim = config.NUM_WAYPOINTS * 2

        # Adaptive Lévy machinery
        self.diversity_tracker = DiversityTracker(
            max_factor=getattr(config, "DIVERSITY_MAX_FACTOR", 3.0)
        )
        self.stagnation_tracker = StagnationTracker(
            patience=getattr(config, "STAGNATION_PATIENCE", 15)
        )

        # Elitism guard: the best-known compromise solution found so far.
        # Re-inserted every iteration so aggressive Lévy/reactivation
        # exploration can never silently prune it out of the archive.
        self.elite_best: Optional[Path] = None

    def _create_and_eval_func(self, vector: np.ndarray) -> Path:
        """Wrapper to evaluate a flattened vector as a path."""
        p = Path.from_vector(vector, self.env.source, self.env.destination)
        evaluate_path(p, self.env)
        return p

    def initialize_population(self):
        """Generate initial population using GQRBL."""
        raw_vectors = gqrbl_initialization(
            0.0, max(config.WORLD_WIDTH, config.WORLD_HEIGHT),
            self.dim,
            config.POPULATION_SIZE,
            self.rng
        )

        valid_paths = []
        for vec in raw_vectors:
            p = Path.from_vector(vec, self.env.source, self.env.destination)
            evaluate_path(p, self.env)
            valid_paths.append(p)

        valid_paths.sort(key=lambda p: p.constraint_violation)

        for p in valid_paths:
            try_insert(p, self.archive, config.ARCHIVE_CAPACITY)

        self.population = []
        for p in self.archive:
            if len(self.population) < config.POPULATION_SIZE:
                self.population.append(p.copy())

        idx = 0
        while len(self.population) < config.POPULATION_SIZE:
            self.population.append(valid_paths[idx % len(valid_paths)].copy())
            idx += 1

    def run(self) -> List[Path]:
        """Execute the optimization loop."""
        print("Initializing MO-MIAVOA population...")
        self.initialize_population()

        print(f"Starting optimization for {config.MAX_ITERATIONS} iterations...")

        for iteration in range(1, config.MAX_ITERATIONS + 1):
            leader_pool, pool_distances = select_leader_pool(self.archive, self.rng)

            if not leader_pool:
                leader_pool = [self.population[0]]
                pool_distances = [1.0]

            leader1 = leader_pool[0].to_vector()
            leader2 = leader_pool[min(1, len(leader_pool) - 1)].to_vector()

            # --- Adaptive Lévy pre-computation for this iteration ---
            # (1) Global diversity factor, from decision-space spread vs leader1.
            population_positions = [v.to_vector() for v in self.population]
            diversity_factor = self.diversity_tracker.update(population_positions, leader1)

            # (2) Per-individual crowding factor, from crowding distance
            #     computed over the *current population* in objective space.
            population_crowding = compute_crowding_distances(self.population)
            crowding_factors = crowding_scale_factors(population_crowding)

            # Position Updates
            new_population = []
            for i, vulture in enumerate(self.population):
                r_i = select_leader_roulette(leader_pool, pool_distances, self.rng).to_vector()
                p_i = vulture.to_vector()
                F = compute_hunger(iteration, config.MAX_ITERATIONS, self.rng)

                new_vec = update_position(
                    p_i, r_i, leader1, leader2, F,
                    iteration, config.MAX_ITERATIONS,
                    self._create_and_eval_func,
                    constrained_dominates,
                    self.rng,
                    diversity_factor=diversity_factor,
                    crowding_factor=crowding_factors[i],
                )

                new_path = Path.from_vector(new_vec, self.env.source, self.env.destination)
                evaluate_path(new_path, self.env)

                if new_path.constraint_violation > 0:
                    for w_idx in range(len(new_path.waypoints)):
                        wp = new_path.waypoints[w_idx]
                        prev_wp = np.array(self.env.source) if w_idx == 0 else new_path.waypoints[w_idx - 1]
                        next_wp = np.array(self.env.destination) if w_idx == len(new_path.waypoints) - 1 else new_path.waypoints[w_idx + 1]

                        if not (segment_is_feasible(prev_wp, wp, self.env.buildings) and
                                segment_is_feasible(wp, next_wp, self.env.buildings)):
                            r_wp = repair_to_feasible(wp, prev_wp, next_wp, self.env.buildings)
                            if r_wp is not None:
                                new_path.waypoints[w_idx] = r_wp

                    new_path.objectives = None
                    evaluate_path(new_path, self.env)

                    if new_path.constraint_violation > 0:
                        new_path = vulture.copy()

                new_population.append(new_path)
                try_insert(new_path, self.archive, config.ARCHIVE_CAPACITY)

            self.population = new_population

            # Crossover
            if iteration % config.CROSSOVER_INTERVAL == 0 and len(self.archive) >= 2:
                p1, p2 = self.rng.choice(self.archive, size=2, replace=False)
                offspring = splice_crossover(p1, p2, self.env, self.rng)

                if offspring:
                    evaluate_path(offspring, self.env)
                    try_insert(offspring, self.archive, config.ARCHIVE_CAPACITY)

                    replace_idx = self.rng.integers(0, config.POPULATION_SIZE)
                    self.population[replace_idx] = offspring.copy()

            # --- Recompute crowding on the post-update population before ---
            # --- mutation, so mutation-phase Lévy scaling reflects the   ---
            # --- population as it actually is right now.                ---
            mutation_crowding = compute_crowding_distances(self.population)
            mutation_crowding_factors = crowding_scale_factors(mutation_crowding)

            # Mutation
            num_mutations = int(config.POPULATION_SIZE * config.MUTATION_RATE)
            for _ in range(num_mutations):
                idx = self.rng.integers(0, config.POPULATION_SIZE)
                cand = self.population[idx]

                if self.rng.random() < 0.5:
                    mutated = adaptive_levy_mutation(
                        cand, iteration, config.MAX_ITERATIONS, self.env, self.rng,
                        diversity_factor=diversity_factor,
                        crowding_factor=mutation_crowding_factors[idx],
                    )
                else:
                    mutated = bounded_detour_mutation(cand, self.env, self.rng)

                if mutated:
                    evaluate_path(mutated, self.env)
                    try_insert(mutated, self.archive, config.ARCHIVE_CAPACITY)
                    self.population[idx] = mutated

            # --- #5: Stagnation reactivation (safety net) ---
            if self.stagnation_tracker.update(self.archive, iteration):
                # Recompute crowding on the *current* population before reactivating,
                # since mutation/crossover may have changed it.
                current_crowding = compute_crowding_distances(self.population)
                reactivated_indices = stagnation_reactivation(
                    self.population,
                    self.archive,
                    current_crowding,
                    self._create_and_eval_func,
                    self.rng,
                    fraction=getattr(config, "STAGNATION_FRACTION", 0.2),
                )
                for idx in reactivated_indices:
                    try_insert(self.population[idx], self.archive, config.ARCHIVE_CAPACITY)

                if reactivated_indices:
                    print(f"  [stagnation] reactivated {len(reactivated_indices)} individuals at iter {iteration}")

            # --- Elitism guard ---
            # Track the best-known compromise solution and force it back
            # into the archive if crowding-based pruning ever evicted it.
            # This is a cheap safety net against aggressive exploration
            # (Lévy / reactivation) silently discarding your best result.
            if self.archive:
                current_best = select_best_compromise(self.archive)
                if self.elite_best is None or constrained_dominates(current_best, self.elite_best):
                    # Keep a reference (not a copy) so membership checks
                    # below work by identity against the live archive.
                    self.elite_best = current_best
                elif self.elite_best not in self.archive:
                    # Elite was pruned out — force it back in, even if it
                    # means the archive briefly exceeds capacity by one.
                    self.archive.append(self.elite_best)

            if iteration % 1 == 0:
                print(f"Iteration {iteration}/{config.MAX_ITERATIONS} | Archive Size: {len(self.archive)} "
                      f"| DivFactor: {diversity_factor:.2f}")

        print("Optimization complete.")
        return self.archive