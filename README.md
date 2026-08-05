# Denomination: A Placement Puzzle for Teaching Integer Programming and Graph-Based Modeling

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

This project contains the code used in the article **Denomination: A Placement Puzzle for
Teaching Integer Programming and Graph-Based Modeling** by **Parth Sarda** and **Dr. Bismark Singh**, submitted to *INFORMS Transactions
on Education*. We provide the implementation of the exact mixed-integer linear programming
(MILP) formulation discussed in the article, an interactive Pygame implementation of the
puzzle for classroom use, and verified optimal $k_{\max}$ values for small grids.

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

## Repository structure

```
Denomination/
├── README.md                     # full description, formulation, citation
├── LICENSE                       
├── AUTHORS                       
├── model/
│   └── denomination_ilp.py       # formulation of MILP 
├── game/
│   └── denomination_game.py      # interactive pygame version of denomination
├── results/
│   └── kmax_table.csv            # updated with verified optimal values
├── enumerator                       
└── bruteforce.py                 # an independent enumerator that plays the puzzle by the rules of the puzzle
```




