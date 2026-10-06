"""
MO-MIAVOA Configuration
========================
Central configuration for all tunable parameters.
All values are derived from the MIAVOA base paper (Li et al. 2024)
and the MO-MIAVOA Design Document.
"""

import math

# =============================================================================
# Population & Iterations
# =============================================================================
POPULATION_SIZE = 35          # N — number of vultures (candidate paths)
MAX_ITERATIONS = 300          # T — maximum optimization iterations
NUM_WAYPOINTS = 10            # n — intermediate waypoints per path

# =============================================================================
# World
# =============================================================================
WORLD_WIDTH = 1000.0          # meters
WORLD_HEIGHT = 1000.0         # meters

# =============================================================================
# MIAVOA Parameters (from base paper Table 6)
# =============================================================================
P1 = 0.6                     # Exploration strategy selection threshold
P2 = 0.4                     # Exploitation sub-phase threshold
P3 = 0.6                     # Late exploitation strategy threshold
ALPHA_CONTROL = 0.8           # Adaptive control parameter (α)
BETA_LEVY = 1.5               # Lévy flight exponent (β)

# =============================================================================
# Pareto Archive
# =============================================================================
ARCHIVE_CAPACITY = 75         # C_max — maximum archive size
LEADER_POOL_SIZE = 8          # Number of leaders selected per iteration

# =============================================================================
# Drone Parameters
# =============================================================================
DRONE_CRUISE_SPEED = 15.0     # v (m/s) — constant cruise speed

# =============================================================================
# Objective 2 — Energy Coefficients
# =============================================================================
K1_ENERGY_DISTANCE = 1.0     # k1 — weight for distance-driven energy cost
K2_ENERGY_WIND = 0.5          # k2 — weight for wind-driven energy cost

# =============================================================================
# Wind Zone Intensities
# =============================================================================
WIND_INTENSITY = {
    "green": 0.5,             # Low wind — minor effect
    "yellow": 1.5,            # Medium wind — moderate effect
    "red": 3.0,               # High wind — significant but not dominating
}

# =============================================================================
# Objective 3 — Risk Sub-Component Weights
# =============================================================================
W_CLEARANCE = 0.4             # w_c — obstacle clearance risk weight
W_TURNING = 0.3               # w_t — turning severity risk weight
W_WIND_RISK = 0.3             # w_w — wind exposure risk weight
CLEARANCE_DECAY_ALPHA = 1.50   # α in f(c) = exp(-α·c) for clearance penalty
SAFETY_BUFFER = 15.0          # meters — buffer zone around buildings
MIN_CLEARANCE_DIST = 10.0     # meters — hard minimum clearance from any building edge/corner

# =============================================================================
# GA Component — Crossover
# =============================================================================
CROSSOVER_INTERVAL = 6        # Iterations between crossover events
REPAIR_MAX_RETRIES = 3        # Max crossover repair attempts per offspring
REPAIR_CLEARANCE = 10.0       # meters — clearance offset for corner routing (≥ MIN_CLEARANCE_DIST)

# =============================================================================
# GA Component — Mutation (Adaptive Lévy)
# =============================================================================
MUTATION_RATE = 0.25          # Fraction of population mutated per iteration
LEVY_SCALE_BASE = 2.5         # Base scale factor for Adaptive Lévy mutation
DETOUR_MAX_WAYPOINTS = 3      # Max consecutive waypoints for bounded detour
DETOUR_OFFSET_RANGE = 100.0   # Max perpendicular offset for detour (meters)

# =============================================================================
# Environment Generation Defaults
# =============================================================================
NUM_BUILDINGS = 15            # Default number of buildings
BUILDING_WIDTH_RANGE = (30, 100)    # (min, max) meters
BUILDING_HEIGHT_RANGE = (30, 150)   # (min, max) meters
NUM_WIND_ZONES = 4            # Default number of wind zones
WIND_ZONE_SIZE_RANGE = (100, 300)   # (min, max) meters per dimension
SOURCE_DEST_MIN_SEPARATION = 500.0  # Minimum distance between source & dest

# =============================================================================
# Final Solution Selection
# =============================================================================
DEFAULT_WEIGHTS = {
    "time": 0.4,
    "energy": 0.3,
    "risk": 0.3,
}

# =============================================================================
# Reproducibility
# =============================================================================
RANDOM_SEED = None            # Default seed for reproducible runs (None = random every time)

"""
Config additions required by optimizer/adaptive_levy.py
==========================================================
Append these to your existing config.py. Every one of them is read via
getattr(config, "NAME", default) in adaptive_levy.py / mo_miavoa.py, so
nothing breaks if you skip this file entirely — but adding them explicitly
here makes the knobs visible and tunable in one place instead of hiding
behind silent defaults.
"""

# Base multiplier applied to every adaptive Lévy step before diversity/
# crowding scaling (mirrors the role LEVY_SCALE_BASE plays for the
# mutation-only Lévy perturbation in mutation.py).
LEVY_BASE_SCALE = 0.01

# --- Diversity-scaled magnitude (#2) ---
# Ceiling on how much the diversity factor can amplify Lévy step size
# once population diversity has fully collapsed relative to iteration 0.
DIVERSITY_MAX_FACTOR = 3.0

# --- Stagnation reactivation (#5) ---
# Iterations without archive improvement (size or spread) before the
# most-crowded fraction of the population gets force-restarted.
STAGNATION_PATIENCE = 15

# Fraction of the population reactivated on a stagnation trigger.
STAGNATION_FRACTION = 0.2

# Extra diversity-factor boost applied specifically during a stagnation
# reactivation jump (independent of the tracked DiversityTracker value).
STAGNATION_LEVY_BOOST = 1.5

# Cap on a single stagnation-reactivation jump, expressed as a fraction of
# the world diagonal (prevents a heavy Lévy tail from placing a waypoint
# absurdly far from anything useful).
STAGNATION_MAX_STEP_FRACTION = 0.15