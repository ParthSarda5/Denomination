# Denomination: A Placement Puzzle for Teaching Integer Programming and Graph-Based Modeling

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

This project contains the code used in the article **Denomination: A Placement Puzzle for
Teaching Integer Programming and Graph-Based Modeling** by **Parth Sarda** and **Dr. Bismark Singh**, submitted to *INFORMS Transactions
on Education*. We provide the implementation of the exact mixed-integer linear programming
(MILP) formulation discussed in the article, an interactive Pygame implementation of the
puzzle for classroom use, and verified optimal $k_{\max}$ values for small grids.

## Repository structure

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
├── enumerator                       
└── bruteforce.py              
```

## Requirements for running the code

Before running the code, make sure you have the below installed:

- python3 (>= 3.9)
- numpy
- scipy (>= 1.9, for the ILP solver)
- pygame (>= 2.0, for the interactive game only)

Install all dependencies with:

```bash
pip install numpy scipy pygame
```

Clone the repository as usual:

```bash
git clone https://github.com/ParthSarda5/Denomination.git
cd Denomination
```

## Repository content

Please refer to the manuscript (`data/rules_denomination.pdf`) for the full statement of the
puzzle rules and the MILP formulation's notation. The repository is structured as follows:

- `data`: This folder contains supporting reference material and verified results.
  - `rules_denomination.pdf`: the formal rules of the Denomination puzzle and the worked
    example referenced throughout the code.
  - `kmax_table.csv`: verified optimal (or best-known, for larger grids) values of
    $k_{\max}$ for $m \times n$ grids, produced by the solvers in `milp_and_game`.
- `milp_and_game`: This folder contains the main part of the code. We briefly describe the
  purpose of each file:
  - `denomination_ilp.py`: the exact MILP formulation of Denomination (model (2) in the
    manuscript) and a `scipy.optimize.milp`-based solver for it.
  - `denomination_game.py`: an interactive Pygame implementation of the puzzle, used for
    classroom demonstrations and manual exploration of the rules.
  - `denomination_verify.py`: independent, non-MILP verification of $k_{\max}$ — an exact
    breadth-first search over reachable board states (feasible for grids up to about 4x4)
    and a depth-first branch-and-bound search with an anytime guarantee (used for larger
    grids, e.g. 5x5, where it reports a proven optimum when the search completes in time,
    and otherwise a lower bound together with a witnessing placement sequence).
  - `utils.py`: shared subroutines — king-graph adjacency and neighbourhoods, the
    rectangle's symmetry group (used to deduplicate reachable states), and grid I/O helpers.
  - `main.py`: a concrete example of how to run the code end to end (see below).

## Example

We provide a short concrete example of how to run this code in the `main.py` file. To run
it, make sure you have navigated to the repository root in your terminal, then run:

```bash
python3 ./milp_and_game/main.py
```

By default, this solves the 3x3 grid with the exact MILP formulation, reproduces the worked
example from the manuscript ($k_{\max} = 7$), and cross-checks the result against the
independent brute-force verifier in `denomination_verify.py`. Edit the `if __name__ ==
"__main__":` block at the bottom of `main.py` to change the grid size, switch between the
MILP solver and the verifier, or launch the interactive game instead.




