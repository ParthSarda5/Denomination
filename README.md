# Denomination — A Placement Puzzle for Teaching Integer Programming

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![scipy](https://img.shields.io/badge/solver-scipy%20HiGHS-orange.svg)](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html)
[![pygame](https://img.shields.io/badge/game-pygame-green.svg)](https://www.pygame.org/)

The project introduces **Denomination**, a grid-based placement puzzle designed to teach core concepts in:

- Integer Programming (IP / MILP)
- Graph Theory
- Independent Sets
- Directed Acyclic Graphs (DAGs)
- Network Modeling
- Combinatorial Optimization

This repository contains:

1. An interactive puzzle implementation built using `pygame`
2. A MILP solver for computing optimal denomination values
3. Educational material suitable for classroom demonstrations and OR coursework

---

## The Puzzle

Denomination is played on an *m* × *n* grid. Each cell is either empty or holds a stone with a positive integer **denomination**. Two cells are **neighbours** if their Chebyshev distance equals 1 — exactly the movement of a king in chess.

### Rules

| Stone type | Placement condition |
|---|---|
| **Null stone** (denomination 1) | Place on cell *v* only when **every** king-graph neighbour of *v* is currently empty. Denomination 1 arises **only** as a null stone. |
| **Non-null stone** (denomination *k* > 1) | Place on empty cell *v* when (a) the sum of denominations of *v*'s already-placed neighbours equals *k*, and (b) denominations 1, 2, …, *k*−1 all exist on the grid. |

**Objective.** Maximise *k*_max, the highest denomination placed.


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
├── rules/                       
└── rules_denomination.pdf                 
```
---

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
