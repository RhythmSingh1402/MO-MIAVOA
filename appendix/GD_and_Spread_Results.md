# Appendix: Full Generational Distance (GD) and Spread ($\Delta$) Results

This appendix provides the full experimental results for the Generational Distance (GD) and Spread ($\Delta$) metrics across all five benchmark problems (ZDT1-3, DTLZ1-2), complementing the Hypervolume and IGD results presented in the main paper.

*Results are shown as Mean $\pm$ Standard Deviation over 30 independent runs.*
*(+) indicates the algorithm is significantly better than MO-MIAVOA, (-) indicates significantly worse, and (≈) indicates no statistical difference according to the Wilcoxon rank-sum test ($\alpha=0.05$).*

## 1. ZDT1 (2-Objective)
| Algorithm | Generational Distance (GD) | Spread ($\Delta$) |
|-----------|-----------------------------|--------------------|
| NSGA-II | 0.0058 ± 0.0002 (-) | 0.3411 ± 0.0401 (-) |
| NSGA-III | **0.0047 ± 0.0002 (+)** | 0.3049 ± 0.0166 (-) |
| MOEA/D | 0.0064 ± 0.0040 (≈) | 0.5920 ± 0.2236 (-) |
| MOPSO | 0.0050 ± 0.0003 (≈) | 0.1778 ± 0.0131 (-) |
| MOGWO | 0.0113 ± 0.0007 (-) | 0.1811 ± 0.0102 (-) |
| MO-MIAVOA | 0.0051 ± 0.0003 | **0.0893 ± 0.0124** |

## 2. ZDT2 (2-Objective)
| Algorithm | Generational Distance (GD) | Spread ($\Delta$) |
|-----------|-----------------------------|--------------------|
| NSGA-II | 0.0048 ± 0.0002 (-) | 0.3365 ± 0.0237 (-) |
| NSGA-III | 0.0052 ± 0.0004 (-) | 0.2092 ± 0.0989 (-) |
| MOEA/D | 0.0057 ± 0.0035 (-) | 0.8201 ± 0.3059 (-) |
| MOPSO | 0.1336 ± 0.2038 (≈) | 0.1324 ± 0.1498 (≈) |
| MOGWO | 0.0049 ± 0.0038 (≈) | 0.1184 ± 0.0906 (≈) |
| MO-MIAVOA | **0.0039 ± 0.0002** | **0.0877 ± 0.0101** |

## 3. ZDT3 (2-Objective)
| Algorithm | Generational Distance (GD) | Spread ($\Delta$) |
|-----------|-----------------------------|--------------------|
| NSGA-II | 0.0057 ± 0.0003 (-) | 0.5416 ± 0.0258 (-) |
| NSGA-III | 0.0055 ± 0.0002 (≈) | 0.4926 ± 0.0062 (-) |
| MOEA/D | 0.0085 ± 0.0065 (≈) | 0.9549 ± 0.0873 (-) |
| MOPSO | **0.0053 ± 0.0003 (≈)** | 0.4287 ± 0.0061 (-) |
| MOGWO | 0.0095 ± 0.0008 (-) | 0.4515 ± 0.0086 (-) |
| MO-MIAVOA | 0.0054 ± 0.0003 | **0.4229 ± 0.0063** |

## 4. DTLZ1 (3-Objective)
| Algorithm | Generational Distance (GD) | Spread ($\Delta$) |
|-----------|-----------------------------|--------------------|
| NSGA-II | 0.8165 ± 1.0019 (+) | 0.9524 ± 0.2021 (+) |
| NSGA-III | 0.1360 ± 0.1635 (+) | 0.7403 ± 0.1630 (+) |
| MOEA/D | **0.0299 ± 0.0569 (+)** | **0.6206 ± 0.1212 (+)** |
| MOPSO | 19.5541 ± 2.1457 (-) | 0.6212 ± 0.0779 (+) |
| MOGWO | 31.2890 ± 2.1073 (-) | 0.6342 ± 0.0691 (+) |
| MO-MIAVOA | 4.6434 ± 4.2561 | 1.2048 ± 0.1303 |

## 5. DTLZ2 (3-Objective)
| Algorithm | Generational Distance (GD) | Spread ($\Delta$) |
|-----------|-----------------------------|--------------------|
| NSGA-II | 0.0465 ± 0.0014 (+) | 0.7213 ± 0.0506 (≈) |
| NSGA-III | **0.0400 ± 0.0002 (+)** | 0.5954 ± 0.0280 (+) |
| MOEA/D | 0.0401 ± 0.0001 (+) | 0.6039 ± 0.0271 (+) |
| MOPSO | 0.1306 ± 0.0077 (-) | **0.5663 ± 0.0395 (+)** |
| MOGWO | 0.0608 ± 0.0058 (+) | 0.6606 ± 0.0394 (+) |
| MO-MIAVOA | 0.0938 ± 0.0128 | 0.7301 ± 0.0431 |
