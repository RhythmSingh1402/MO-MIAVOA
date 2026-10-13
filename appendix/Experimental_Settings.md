# Supplementary Material: Experimental Settings

This file lists the experimental settings that were omitted from the paper for space.
Paper: *MO-MIAVOA: A Multi-Objective Multi-Strategy Improved African Vulture Optimization Algorithm*.

## 1. Common budget (all algorithms)

| Item | Value |
|---|---|
| Population size | 100 |
| Max. iterations | 200 |
| Function evaluations per run | 20,000 |
| Independent runs | 30 (fixed seeds 1-30, identical for all algorithms) |

## 2. Metric settings

**Hypervolume (HV) reference points**

| Problem | Reference point |
|---|---|
| ZDT1, ZDT2 | (1.1, 1.1) |
| ZDT3 | (1.0, 1.0) |
| DTLZ1 | (1.0, 1.0, 1.0) |
| DTLZ2 | (1.5, 1.5, 1.5) |

**IGD / GD reference fronts** (generated with `pymoo`)

| Problems | True Pareto front representation |
|---|---|
| ZDT1-ZDT3 | 100 uniformly sampled points |
| DTLZ1-DTLZ2 | 136 points from uniform reference directions |

## 3. Baseline settings

### NSGA-II and NSGA-III (`pymoo`)
- Crossover: simulated binary crossover (SBX), probability 0.9, distribution index eta_c = 15
- Mutation: polynomial mutation, distribution index eta_m = 20
- NSGA-III reference points:
  - ZDT (2 objectives): 99 partitions, giving 100 reference points
  - DTLZ (3 objectives): Das-Dennis method with 12 partitions, giving 91 reference points

### MOEA/D (`pymoo`)
- Decomposition: Tchebycheff approach
- Weight vectors: 100 (ZDT) and 91 (DTLZ)
- Neighborhood size: 20
- Probability of neighbor mating: 0.9
- Crossover: SBX with eta_c = 20; mutation: polynomial mutation with eta_m = 20

### MOPSO and MOGWO (own implementations, following the original papers)
- External archive capacity: 100
- Archive grid divisions: 10 per objective
- Leader selection: archive members chosen by crowding-distance roulette
- MOPSO: inertia weight decreasing linearly from 0.9 to 0.4; c1 = c2 = 2.0
- MOGWO: parameter a decreasing linearly from 2 to 0

## 4. MO-MIAVOA parameters (full list)

| Parameter | Symbol | Value |
|---|---|---|
| Population size | N | 100 |
| Max. iterations | T_max | 200 |
| Archive capacity | C_max | 100 |
| Leader pool size | L | 8 |
| Crossover interval | rho | 3 iterations |
| Mutation rate | mu | 0.35 |
| Exploration threshold | p1 | 0.6 |
| Exploitation sub-phase threshold | p2 | 0.4 |
| Late exploitation threshold | p3 | 0.6 |
| Adaptive control | alpha | 0.8 |
| Levy exponent | beta | 1.5 |
| Levy scale base | s0 | 2.5 |
| Detour block size | b | 1-3 variables |
| Detour offset bound | - | 10% of the variable range |
| Repair max. retries | - | 3 |

## 5. Additional results

The complete GD and Spread tables (mean +/- std over 30 runs, with Wilcoxon rank-sum markers) are in this folder:
- `GD_and_Spread_Results.md`
