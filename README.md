# Denomination — A Placement Puzzle for Teaching Integer Programming

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![scipy](https://img.shields.io/badge/solver-scipy%20HiGHS-orange.svg)](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html)
[![pygame](https://img.shields.io/badge/game-pygame-green.svg)](https://www.pygame.org/)

This repository accompanies the paper

> Parth Sarda and Bismark Singh (submitted).  
> **Denomination: A Placement Puzzle for Teaching Integer Programming and Graph-Based Modeling.**  
> *INFORMS Transactions on Education.*

It provides two things: an **interactive puzzle game** you can play in class, and a **MILP solver** that finds the optimal solution and demonstrates how to code integer programmes in Python.

---

## The Puzzle

Denomination is played on an *m* × *n* grid. Each cell is either empty or holds a stone with a positive integer **denomination**. Two cells are **neighbours** if their Chebyshev distance equals 1 — exactly the movement of a king in chess.

### Rules

| Stone type | Placement condition |
|---|---|
| **Null stone** (denomination 1) | Place on cell *v* only when **every** king-graph neighbour of *v* is currently empty. Denomination 1 arises **only** as a null stone. |
| **Non-null stone** (denomination *k* > 1) | Place on empty cell *v* when (a) the sum of denominations of *v*'s already-placed neighbours equals *k*, and (b) denominations 1, 2, …, *k*−1 all exist on the grid. |

**Objective.** Maximise *k*_max, the highest denomination placed.

### Worked example — 3 × 3 grid, *k*_max = 7

```
Step 1   null 1★ at (1,2)   all 5 neighbours empty
Step 2   null 1★ at (3,1)   all 3 neighbours empty  ·  not adjacent to (1,2)
Step 3        2  at (2,2)   (1,2) + (3,1) = 2
Step 4        3  at (2,3)   (1,2) + (2,2) = 3
Step 5        4  at (2,1)   (1,2) + (2,2) + (3,1) = 4
Step 6        5  at (3,3)   (2,2) + (2,3) = 5
Step 7        6  at (1,3)   (1,2) + (2,2) + (2,3) = 6
Step 8        7  at (1,1)   (1,2) + (2,1) + (2,2) = 7
```

Final board (row ↑, col →):

```
 6    3    5
1★    2    _
 7    4   1★
```

Brute-force search confirms *k*_max = 7 is optimal for the 3 × 3 grid.

---

## Repository structure

```
Denomination/
├── src/
│   ├── denomination_game.py   Interactive pygame puzzle (click to play)
│   └── denomination_ilp.py    MILP solver — finds optimal k_max
├── results/
│   └── kmax_table.csv         Optimal k_max values by grid size
├── AUTHORS
├── LICENSE
└── README.md
```

---

## Playing the game

```bash
pip install pygame scipy numpy
python src/denomination_game.py
```

A **start screen** appears. Type or click to select a grid size, then press **Play**.

### How to place stones

- **Green highlighted cell** — click to place a null stone (denomination 1★).  
  All king-graph neighbours must be empty.
- **Blue highlighted cell** — click to place a non-null stone.  
  The denomination shown inside the cell equals the neighbourhood sum.

The game enforces all rules automatically and explains any invalid placement.

### Controls

| Key | Action |
|-----|--------|
| Click highlighted cell | Place stone |
| **H** | Toggle hint highlights |
| **U** | Undo last move |
| **R** | Restart the board |
| **M** | Return to grid-size menu |
| **Q / Escape** | Quit |

The window is fully resizable; the grid scales automatically.

---

## MILP solver

`src/denomination_ilp.py` finds the provably optimal *k*_max using `scipy.optimize.milp` — no commercial solver licence required.

```bash
python src/denomination_ilp.py           # interactive prompts
python src/denomination_ilp.py 3 3       # solve 3×3 directly
python src/denomination_ilp.py 3 3 120   # with 120-second time limit
```

### The formulation at a glance

The MILP uses two families of variables:

| Variable | Meaning |
|---|---|
| *x*_(*v*,*k*) ∈ {0,1} | Cell *v* receives denomination *k* |
| *y*_*k* ∈ {0,1} | Denomination *k* appears on the grid |

**Objective:** maximise Σ *y*_*k*  
(equals *k*_max because the contiguity constraint forces denominations to appear without gaps)

**Key constraints:**

| Constraint | Purpose |
|---|---|
| Σ_*k* *x*(*v*,*k*) ≤ 1 | Each cell holds at most one denomination |
| *x*(*u*,1) + *x*(*v*,1) ≤ 1 for each edge (*u*,*v*) | Null stones form an independent set |
| Neighbourhood-sum (big-*M* pair) | Enforces denomination = sum of placed neighbours |
| *y*_*k* ≥ *y*_(*k*+1) | Denominations appear contiguously from 1 to *k*_max |
| *y*_1 = 1 | At least one null stone is required |

This formulation avoids ordering variables and bilinear terms entirely, giving a clean LP relaxation that is fast in practice.

### Coding a MILP in Python with `scipy.optimize.milp`

```python
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix

# 1. Objective  (scipy minimises — negate to maximise Σ y_k)
c_obj = np.zeros(n_vars)
c_obj[y_indices] = -1.0

# 2. Constraint matrix  lb ≤ A x ≤ ub
A  = lil_matrix((n_constraints, n_vars))
lb = np.full(n_constraints, -np.inf)
ub = np.zeros(n_constraints)
# ... fill in A, lb, ub ...

# 3. Variable bounds and integrality
bounds      = Bounds(np.zeros(n_vars), np.ones(n_vars))
integrality = np.ones(n_vars, dtype=int)   # 1 = integer

# 4. Solve
result = milp(c_obj,
              constraints=LinearConstraint(A.tocsr(), lb, ub),
              integrality=integrality,
              bounds=bounds,
              options={"time_limit": 180.0, "mip_rel_gap": 0.0})

k_max = int(round(-result.fun))
```

The full annotated implementation is in `src/denomination_ilp.py`.

---

## Results

Optimal *k*_max values (brute-force verified for 2×2, 2×3, 3×3; MILP incumbent for larger grids):

| Grid | Cells | *k*_max | Cells used | Solve time | Status |
|------|-------|---------|-----------|------------|--------|
| 2×2  |  4 | **1** | 1 |  < 1 s | Optimal |
| 2×3  |  6 | **3** | 4 |    3 s | Optimal |
| 3×3  |  9 | **7** | 8 |   28 s | Optimal |
| 3×4  | 12 | ≥ 8   | — |  120 s | Time limit |
| 4×4  | 16 | ≥ 8   | — |  120 s | Time limit |

Raw data: [`results/kmax_table.csv`](results/kmax_table.csv).

### Key observations

- **2×2** — all four cells are mutually adjacent on the king graph, so only one null stone fits and no non-null stone can follow (*k*_max = 1).
- **3×3** — the optimal 8-step sequence uses two null stones forming an independent set, chains denominations 2–7 through the remaining cells, and leaves exactly one cell empty.
- Solve time grows rapidly with grid size because the neighbourhood-sum big-*M* constraints weaken the LP relaxation. Adding a symmetry-breaking constraint (Exercise 4 in the paper) cuts solve time substantially for the 4×4 grid.

---

## Classroom use

### Single lecture (60–90 min)

1. Project the game; invite a volunteer to play for 5–10 minutes.  
2. Pose the question: *"Can you exceed denomination 7 on the 3×3 board — and how would you prove 7 is the maximum?"*  
3. Introduce the rules formally; prove that null stones form an independent set.  
4. Walk through the MILP formulation interactively.  
5. Assign Exercises 1 and 3(a)–(b) from the paper as take-home tasks.

### Multi-week project (2–3 weeks)

| Week | Focus | Exercises |
|------|-------|-----------|
| 1 | Graph structure, hand exploration | 1, 2 |
| 2 | MILP implementation and benchmarking | 3 |
| 3 | Extensions, symmetry breaking, alternative graphs | 4 |

Teams of 2–3 students work well. A group presentation reporting the best *k*_max found for the 5×5 grid and the modelling decisions behind it provides a competitive closing element.

### Course fit

| Course | Relevant content |
|--------|-----------------|
| Integer programming / combinatorial optimisation | Full formulation, symmetry breaking, solve-time analysis |
| Network analysis / graph theory | King graph, independent sets, placement DAG |
| Introductory OR survey | Interactive game, informal rules discussion, light MIP overview |

---

## Requirements

```
Python  ≥ 3.9
pygame  ≥ 2.0     (game only)
scipy   ≥ 1.9     (MILP solver — HiGHS backend)
numpy   ≥ 1.21    (MILP solver)
```

Install all dependencies:

```bash
pip install pygame scipy numpy
```

---

## Cite

If you use this code or puzzle in teaching or research, please cite:

```bibtex
@article{sarda2025denomination,
  author  = {Parth Sarda and Bismark Singh},
  title   = {Denomination: A Placement Puzzle for Teaching Integer
             Programming and Graph-Based Modeling},
  journal = {INFORMS Transactions on Education},
  year    = {2025},
  note    = {Submitted}
}
```

---

## Support and development

This repository is actively maintained.  
Bug reports and suggestions are welcome via [GitHub Issues](https://github.com/ParthSarda5/Denomination/issues).

For questions about the puzzle, formulation, or classroom use, contact the authors — see [AUTHORS](AUTHORS).

---

## License

Released under the [MIT License](LICENSE).  
Copyright © 2025 Parth Sarda and Bismark Singh.
