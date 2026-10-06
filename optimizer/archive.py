"""
Pareto Archive Management
===========================
Handles Pareto dominance, crowding distance computation, and archive updates.
"""

from __future__ import annotations

import numpy as np
from typing import List, Sequence, Tuple

from environment.models import Path


def dominates(objectives_a: Sequence[float], objectives_b: Sequence[float]) -> bool:
    """Return whether objective vector ``a`` Pareto-dominates vector ``b``.

    This is the unconstrained form used by the archive unit tests and is also
    the objective comparison performed by :func:`constrained_dominates` once
    two paths have equal constraint violation.
    """
    a = np.asarray(objectives_a)
    b = np.asarray(objectives_b)
    return bool(np.all(a <= b) and np.any(a < b))


def constrained_dominates(path_a: Path, path_b: Path) -> bool:
    """
    Check if path_a dominates path_b using the Constrained Dominance Principle (CDP).
    1. Feasible dominates Infeasible.
    2. If both Infeasible, lower constraint violation dominates.
    3. If both Feasible (or equal violation), standard Pareto dominance on objectives.
    """
    cv_a = path_a.constraint_violation
    cv_b = path_b.constraint_violation

    if cv_a < cv_b:
        return True
    elif cv_a > cv_b:
        return False
    
    # Both have equal constraint violation (often both 0.0)
    # Check standard Pareto dominance
    if path_a.objectives is None or path_b.objectives is None:
        return False

    return dominates(path_a.objectives, path_b.objectives)


def compute_crowding_distances(archive: List[Path]) -> List[float]:
    """
    Compute the crowding distance for each member in the archive.
    Returns a list of distances corresponding to the order of paths in the archive.
    """
    size = len(archive)
    if size == 0:
        return []
    if size <= 2:
        return [float('inf')] * size

    distances = [0.0] * size
    
    # Evaluate objectives
    obj_array = np.array([p.objectives for p in archive])  # shape (size, 3)
    num_objectives = obj_array.shape[1]

    for m in range(num_objectives):
        # Sort indices by this objective
        sorted_indices = np.argsort(obj_array[:, m])
        
        # Boundary members get infinite distance
        distances[sorted_indices[0]] = float('inf')
        distances[sorted_indices[-1]] = float('inf')
        
        obj_min = obj_array[sorted_indices[0], m]
        obj_max = obj_array[sorted_indices[-1], m]
        
        obj_range = obj_max - obj_min
        if obj_range == 0:
            continue
            
        # Interior members
        for i in range(1, size - 1):
            if distances[sorted_indices[i]] != float('inf'):
                distances[sorted_indices[i]] += (
                    obj_array[sorted_indices[i + 1], m] - 
                    obj_array[sorted_indices[i - 1], m]
                ) / obj_range

    return distances


def prune_archive(archive: List[Path], max_size: int) -> None:
    """
    If the archive exceeds max_size, remove the member(s) with the smallest
    crowding distance until it fits within max_size.
    Modifies the list in place.
    """
    while len(archive) > max_size:
        distances = compute_crowding_distances(archive)
        # Find index with minimum crowding distance
        min_idx = np.argmin(distances)
        archive.pop(min_idx)


def try_insert(candidate: Path, archive: List[Path], max_size: int) -> bool:
    """
    Attempt to insert a candidate path into the archive.
    Follows Section 5.2 of the design document:
    1. Dominance check against current archive.
    2. Insert if not dominated.
    3. Prune if exceeds capacity.
    
    Returns True if the candidate was inserted and kept, False otherwise.
    """
    if candidate.objectives is None:
        raise ValueError("Candidate path must have evaluated objectives.")

    dominated_by_archive = False
    to_remove = []

    for i, member in enumerate(archive):
        if member.objectives is None:
            continue
            
        if constrained_dominates(member, candidate):
            dominated_by_archive = True
            break
        elif constrained_dominates(candidate, member):
            to_remove.append(i)

    if dominated_by_archive:
        return False

    # Remove members dominated by the candidate (in reverse to avoid index shifting issues)
    for i in reversed(to_remove):
        archive.pop(i)

    # Insert candidate
    archive.append(candidate)

    # Prune if over capacity
    if len(archive) > max_size:
        # Check if the candidate itself was the one pruned
        # (It shouldn't usually be unless it's very crowded)
        prune_archive(archive, max_size)
        return candidate in archive

    return True
