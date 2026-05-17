[![INFORMS Transactions on Education](https://pubsonline.informs.org/cms/asset/1a8e1d52-72ac-482d-bcd0-f5f8cb8f2e38/ited.header.png)](https://pubsonline.informs.org/journal/ited)

# Denomination: A Grid Placement Puzzle for Teaching Discrete Optimization

This repository is distributed in association with the
[INFORMS Transactions on Education](https://pubsonline.informs.org/journal/ited)
under the [MIT License](LICENSE).

The software in this repository accompanies the paper

> Parth Sarda and Bismark Singh (submitted).
> **Denomination: A Grid Placement Puzzle for Teaching Discrete Optimization.**
> *INFORMS Transactions on Education.*

## Cite

To cite this repository, please cite both the paper and this repository.

```bibtex
@article{sarda2025denomination,
  author    = {Parth Sarda and Bismark Singh},
  title     = {Denomination: A Grid Placement Puzzle for
               Teaching Discrete Optimization},
  journal   = {INFORMS Transactions on Education},
  year      = {2025},
  note      = {Submitted},
  url       = {https://github.com/ParthSarda5/Denomination}
}
```

## The Puzzle

Denomination is a single-player combinatorial puzzle played on an *m* × *n* grid.
Two cells are **neighbours** if their Chebyshev distance is 1 (king-graph adjacency).

| Stone type | Rule |
|---|---|
| **Null stone** (denomination 1) | Place on empty cell *v* only when **every** neighbour of *v* is also empty. Denomination 1 appears **only** as a null stone. |
| **Non-null stone** (denomination *k* > 1) | Place on empty cell *v* when (a) the sum of the denominations of *v*'s already-placed neighbours equals *k*, and (b) every denomination 1, 2, …, *k*−1 already exists on the grid. |

**Objective:** maximise *k*_max, the highest denomination placed.

### Worked example — 3 × 3 grid, *k*_max = 7

The sequence below is optimal (verified by brute force and the ILP):

```
Step 1  null 1★ at (1,2)   all 5 neighbours empty
Step 2  null 1★ at (3,1)   all 3 neighbours empty; not adjacent to (1,2)
Step 3       2  at (2,2)   (1,2) + (3,1) = 2
Step 4       3  at (2,3)   (1,2) + (2,2) = 3
Step 5       4  at (2,1)   (1,2) + (2,2) + (3,1) = 4
Step 6       5  at (3,3)   (2,2) + (2,3) = 5
Step 7       6  at (1,3)   (1,2) + (2,2) + (2,3) = 6
Step 8       7  at (1,1)   (1,2) + (2,1) + (2,2) = 7
```

Final board (row ↑, col →):

```
 6   3   5
1★   2   _
 7   4  1★
```

## Description

```
Denomination/
├── README.md                     # full description, formulation, citation
├── LICENSE                       
├── AUTHORS                       
├── model/
│   └── denomination_ilp.py       # formulation of MILP 
├── game/
│   └── denomination_game.py      #interactive pygame version of denomination
├── results/
│   └── kmax_table.csv            # updated with verified optimal values
├── rules/                       
└── rules_denomination.pdf                 
```

### `game/denomination_game.py`

An interactive implementation of Denomination using
[pygame](https://www.pygame.org/).
The game opens with a **start screen** where you type the desired grid
dimensions (any *m* × *n* with *m*, *n* ≤ 10) 

### `model/denomination_ilp.py`

An Integer Linear Programme that finds the optimal *k*_max on an *m* × *n* grid.
The solver uses `scipy.optimize.milp`, which wraps the open-source
[HiGHS](https://highs.dev/) solver — no commercial licence is required.

#### Coding an ILP in Python with `scipy.optimize.milp`

`scipy.optimize.milp` expects the problem in the form

```
minimise    c · x
subject to  lb ≤ A · x ≤ ub
            x_lo ≤ x ≤ x_hi
            x_i ∈ ℤ  for all i marked as integer
```

A minimal template:

```python
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix

# 1. Objective  (scipy minimises, so negate k_max)
c_obj = np.zeros(n_vars)
c_obj[idx_kmax] = -1.0

# 2. Constraints  (build as a sparse matrix)
A  = lil_matrix((n_constraints, n_vars))
lb = np.full(n_constraints, -np.inf)
ub = np.zeros(n_constraints)
# ... fill in A, lb, ub row by row ...

# 3. Variable bounds and integrality
x_lo = np.zeros(n_vars)
x_hi = np.ones(n_vars)                  # tighten per variable
intg = np.ones(n_vars, dtype=int)       # 1 = integer, 0 = continuous

# 4. Solve
result = milp(
    c_obj,
    constraints=LinearConstraint(A.tocsr(), lb, ub),
    integrality=intg,
    bounds=Bounds(x_lo, x_hi),
    options={"time_limit": 180.0, "mip_rel_gap": 0.0},
)

k_max = int(round(-result.fun))
```

The full annotated implementation is in `src/denomination_ilp.py`.  It includes:

- **Occupation / null-denomination constraints** linking `d[c]`, `null[c]`,
  and `occ[c]`.
- **Ordering variables** `tau[c]` and binary `b[c, nb]` to enforce the
  acyclic placement sequence (the placement DAG from the paper).
- **McCormick linearisation** of the bilinear products
  `d[nb] · b[c, nb]` and `d[c] · null[c]`.
- **Sequencing constraint** preventing denomination *k* from appearing
  before denomination *k*−1.
- A rule enforcing that denomination 1 arises **only** as a null stone.

#### Comparison with other INFORMS Trans. Ed. puzzle ILPs

The table below places this formulation in context with related puzzles
from the journal's Puzzle section.

| Puzzle | Reference | Key OR concept illustrated |
|--------|-----------|---------------------------|
| *n*-Queens | Letavec & Ruggiero (2002) | Binary IP, symmetry breaking |
| Chessboard placements | Chlond & Toase (2002) | IP framework across piece types |
| Fillomino | Pearce & Forbes (2017) | Lazy constraints, column generation |
| Knights exchange | Iranpoor (2021) | Network flow vs. binary IP efficiency |
| Snake Eggs | Harris & Forbes (2023) | Benders decomposition |
| Wordle | Lakhani et al. (2023) | Combinatorial search as IP |
| **Denomination** | **Sarda & Singh (submitted)** | **Independent sets, placement DAG, McCormick linearisation** |

## Requirements

```
Python >= 3.9
pygame >= 2.0        # game only
scipy  >= 1.9        # ILP solver
numpy  >= 1.21       # ILP solver
```

Install all dependencies:

```bash
pip install pygame scipy numpy
```

## Results

Optimal *k*_max values (brute-force verified for 2×2, 2×3, and 3×3;
ILP incumbent for larger grids with a 120 s time limit):

| Grid | Total cells | *k*_max | Cells used | Solve time | Status |
|------|------------|---------|-----------|------------|--------|
| 2×2  | 4  | **1** | 1  | 0.4 s  | Optimal |
| 2×3  | 6  | **3** | 4  | 3.0 s  | Optimal |
| 3×3  | 9  | **7** | 8  | 70 s   | Optimal |
| 3×4  | 12 | ≥ 8   | 10 | 120 s  | Time limit |
| 4×4  | 16 | ≥ 8   | 11 | 120 s  | Time limit |

Raw data: [`results/kmax_table.csv`](results/kmax_table.csv).

**Key observations**

- On the **2×2** grid all four cells are mutually adjacent; only one null
  stone fits and no non-null stone can follow, so *k*_max = 1.
- On the **3×3** grid the optimal 8-step sequence uses two null stones that
  form an independent set, then builds a denomination chain through the
  remaining cells, leaving exactly one cell empty.
- Solve time grows sharply with grid size due to the ordering constraints.

## Ongoing Development

This code is being developed on an ongoing basis at the authors' GitHub site:
<https://github.com/ParthSarda5/Denomination>.

Please go there for the most recent version or to request support.

## Support

For questions about the puzzle, the ILP formulation, or classroom use,
contact the authors (see [AUTHORS](AUTHORS)).

Bismark Singh is supported by the University of Southampton's Global
Partnership Award.
