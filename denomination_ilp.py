"""
denomination_ilp.py
===================
Solves the Denomination puzzle using Integer Linear Programming (ILP).
Implemented with scipy.optimize.milp, which wraps the open-source HiGHS
solver — no commercial licence is required.

This script is designed to accompany the paper:
    Sarda, P. and Singh, B. (submitted).
    "Denomination: A Grid Placement Puzzle for Teaching Discrete Optimization."
    INFORMS Transactions on Education.

How to run
----------
    python denomination_ilp.py               # interactive prompts
    python denomination_ilp.py 3 3           # solve 3×3 directly
    python denomination_ilp.py 3 3 120       # with 120-second time limit

Puzzle rules
------------
A null stone (denomination 1) may be placed on cell v only when every
king-graph neighbour of v is empty.  Denomination 1 arises ONLY as a null
stone — the sum rule below cannot produce it.

A non-null stone (denomination k > 1) may be placed on empty cell v when:
  (a) the sum of the denominations of v's already-placed neighbours equals k,
  (b) every denomination 1, 2, …, k-1 already appears on the grid.

The objective is to maximise k_max, the highest denomination placed.

ILP formulation
---------------
Decision variables
  d[c]        ∈ {0, …, K}  denomination at cell c  (0 = empty)
  null[c]     ∈ {0, 1}     1 if c holds a null stone
  occ[c]      ∈ {0, 1}     1 if c is occupied
  tau[c]      ∈ {0, …, N}  placement time of c (0 = unoccupied)
  b[c, nb]    ∈ {0, 1}     1 if neighbour nb is placed before c
  w[c, nb]    ∈ {0, …, K}  McCormick linearisation of  d[nb] · b[c, nb]
  yn[c]       ∈ {0, …, K}  McCormick linearisation of  d[c]  · null[c]
  p[c, k]     ∈ {0, 1}     indicator that  d[c] = k
  present[k]  ∈ {0, 1}     1 if denomination k appears on the grid
  ismax[c]    ∈ {0, 1}     1 if c achieves k_max
  kmax        ∈ {0, …, K}  objective variable

Key constraint groups
  Occupation        occ[c] ≤ d[c] ≤ K · occ[c]
  Null denom = 1    null[c] ≤ d[c] ≤ 1 + K(1 − null[c])
  Null indep. set   null[c] + null[nb] ≤ 1        for each king edge
  Sum rule          Σ_nb w[c,nb] + yn[c] = d[c]
  McCormick w       w = b · d[nb]                 (four inequalities)
  McCormick yn      yn = null · d                 (three inequalities)
  Null no-pred.     b[c,nb] + null[c] ≤ 1
  Ordering (big-M)  tau variables enforce b[c,nb] = 1 ⟺ tau[nb] < tau[c]
  Indicators        Σ_k k · p[c,k] = d[c];  null[c] ≥ p[c,1]
  Sequencing        present[k] ≤ present[k−1]     for k = 2, …, K

Reference for McCormick envelopes
    McCormick, G.P. (1976). Computability of global solutions to factorable
    nonconvex programs: Part I. Mathematical Programming 10(1): 147–175.
"""

import sys
import time
import warnings

import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix


# ---------------------------------------------------------------------------
# King-graph neighbour helper
# ---------------------------------------------------------------------------

def king_nbrs(i, j, m, n):
    """Return all king-graph neighbours of cell (i, j) on an m×n grid."""
    return [
        (i + di, j + dj)
        for di in (-1, 0, 1)
        for dj in (-1, 0, 1)
        if (di, dj) != (0, 0)
        and 0 <= i + di < m
        and 0 <= j + dj < n
    ]


# ---------------------------------------------------------------------------
# Build the ILP
# ---------------------------------------------------------------------------

def build_ilp(m, n, K):
    """
    Construct all ILP data for an m×n king-graph Denomination puzzle.

    Parameters
    ----------
    m, n : int   grid dimensions (0-indexed rows, columns internally)
    K    : int   denomination upper bound  (use m*n as a safe default)

    Returns
    -------
    c_obj  : 1-D array   objective vector (minimise − k_max)
    A      : csr_matrix  constraint matrix
    lb, ub : 1-D arrays  row bounds  lb ≤ A·x ≤ ub
    x_lo, x_hi : 1-D arrays  variable bounds
    integrality : 1-D array  1 = integer, 0 = continuous
    idx    : dict  variable name → column index
    """
    cells = [(i, j) for i in range(m) for j in range(n)]
    NB    = {c: king_nbrs(*c, m, n) for c in cells}
    N     = m * n                # placement-time big-M
    BK    = float(K)
    BN    = float(N)
    BN1   = float(N + 1)
    INF   = np.inf

    # ------------------------------------------------------------------
    # 1.  Assign a column index to every variable
    # ------------------------------------------------------------------
    idx = {}
    col = 0

    for c in cells:
        for tag in ("d", "null", "occ", "tau", "yn", "ismax"):
            idx[(tag, c)] = col;  col += 1
        for nb in NB[c]:
            idx[("b", c, nb)] = col;  col += 1    # ordering binary
            idx[("w", c, nb)] = col;  col += 1    # McCormick product

    for k in range(1, K + 1):
        idx[("pr", k)] = col;  col += 1            # present[k]
        for c in cells:
            idx[("p", c, k)] = col;  col += 1      # p[c, k]

    idx["kmax"] = col;  col += 1
    nv = col

    # ------------------------------------------------------------------
    # 2.  Variable bounds and integrality
    # ------------------------------------------------------------------
    x_lo = np.zeros(nv)
    x_hi = np.full(nv, BK)
    intg = np.ones(nv, dtype=int)

    for c in cells:
        for tag in ("null", "occ", "ismax"):
            x_hi[idx[(tag, c)]] = 1.0
        x_hi[idx[("tau", c)]] = BN
        for nb in NB[c]:
            x_hi[idx[("b", c, nb)]] = 1.0

    for k in range(1, K + 1):
        x_hi[idx[("pr", k)]] = 1.0
        for c in cells:
            x_hi[idx[("p", c, k)]] = 1.0

    x_hi[idx["kmax"]] = BK

    # ------------------------------------------------------------------
    # 3.  Objective: minimise −k_max
    # ------------------------------------------------------------------
    c_obj = np.zeros(nv)
    c_obj[idx["kmax"]] = -1.0

    # ------------------------------------------------------------------
    # 4.  Constraints
    #     Each row is a triple (coefficient_value_list, lb, ub).
    # ------------------------------------------------------------------
    rows = []

    def row(cv, lo, hi):
        rows.append((cv, lo, hi))

    def eq(cv, val):
        rows.append((cv, val, val))

    for c in cells:
        dc = idx[("d",     c)]
        nc = idx[("null",  c)]
        oc = idx[("occ",   c)]
        tc = idx[("tau",   c)]
        yn = idx[("yn",    c)]
        im = idx[("ismax", c)]
        km = idx["kmax"]

        # Occupation: occ ≤ d ≤ K·occ
        row([(dc, 1), (oc, -BK)], -INF, 0)
        row([(oc, 1), (dc, -1)],  -INF, 0)

        # Null stone forces d = 1
        row([(nc, 1), (dc, -1)],      -INF, 0)
        row([(dc, 1), (nc,  BK)],     -INF, 1 + BK)

        # Sum rule: Σ_nb w[c,nb] + yn[c] = d[c]
        eq([(dc, -1), (yn, 1)] + [(idx[("w", c, nb)], 1) for nb in NB[c]], 0)

        # McCormick  yn = null · d[c]
        row([(yn, 1), (nc, -BK)],            -INF, 0)    # yn ≤ K·null
        row([(yn, 1), (dc, -1)],             -INF, 0)    # yn ≤ d
        row([(yn, 1), (dc, -1), (nc, -BK)],  -BK, INF)  # yn ≥ d − K(1−null)

        # Placement-time occupancy: occ ≤ tau ≤ N·occ
        row([(tc, 1), (oc, -1)],  0, INF)
        row([(tc, 1), (oc, -BN)], -INF, 0)

        # Null stone has no predecessors: b[c,nb] ≤ 1 − null[c]
        for nb in NB[c]:
            row([(idx[("b", c, nb)], 1), (nc, 1)], -INF, 1)

        for nb in NB[c]:
            d2 = idx[("d",   nb)]
            o2 = idx[("occ", nb)]
            t2 = idx[("tau", nb)]
            bc = idx[("b",   c, nb)]
            ww = idx[("w",   c, nb)]

            # McCormick  w[c,nb] = b[c,nb] · d[nb]
            row([(ww, 1), (bc, -BK)],           -INF, 0)   # w ≤ K·b
            row([(ww, 1), (d2, -1)],            -INF, 0)   # w ≤ d[nb]
            row([(ww, 1), (d2, -1), (bc, -BK)], -BK, INF)  # w ≥ d[nb]−K(1−b)

            # b = 0 if nb is unoccupied
            row([(bc, 1), (o2, -1)], -INF, 0)

            # Big-M ordering: b=1 ⟹ tau[c] > tau[nb]
            row([(tc, 1), (t2, -1), (bc, -BN)],              1 - BN, INF)
            # Big-M ordering: b=0 ⟹ tau[nb] > tau[c]  (relaxed for empty cells)
            row([(t2, 1), (tc, -1), (bc, BN1),
                 (oc, -BN1), (o2, -BN1)],         1 - 2*BN1, INF)

        # Denomination indicators
        eq([(dc, -1)] + [(idx[("p", c, k)], float(k)) for k in range(1, K+1)], 0)
        eq([(oc, -1)] + [(idx[("p", c, k)], 1.0)      for k in range(1, K+1)], 0)

        # Denomination 1 may ONLY appear as a null stone
        row([(nc, 1), (idx[("p", c, 1)], -1)], 0, INF)

        # k_max ≥ d[c]
        row([(km, 1), (dc, -1)],          0, INF)
        # k_max ≤ d[c] + K·(1 − ismax[c])
        row([(km, 1), (dc, -1), (im, BK)], -INF, BK)

    # Null stones must form an independent set
    seen = set()
    for c in cells:
        for nb in NB[c]:
            e = (min(c, nb), max(c, nb))
            if e not in seen:
                seen.add(e)
                row([(idx[("null", c)], 1), (idx[("null", nb)], 1)], -INF, 1)

    # At least one null stone; at least one cell achieves k_max
    row([(idx[("null",  c)], 1) for c in cells], 1, INF)
    row([(idx[("ismax", c)], 1) for c in cells], 1, INF)

    # Present indicators: present[k] ↔ some cell has denomination k
    for k in range(1, K + 1):
        pr = idx[("pr", k)]
        row([(pr, 1)] + [(idx[("p", c, k)], -1) for c in cells], -INF, 0)
        for c in cells:
            row([(pr, 1), (idx[("p", c, k)], -1)], 0, INF)

    # Sequencing: denomination k cannot appear before k−1
    for k in range(2, K + 1):
        row([(idx[("pr", k)], 1), (idx[("pr", k-1)], -1)], -INF, 0)

    # ------------------------------------------------------------------
    # 5.  Assemble sparse constraint matrix
    # ------------------------------------------------------------------
    nr = len(rows)
    A  = lil_matrix((nr, nv))
    lb = np.empty(nr)
    ub = np.empty(nr)
    for r, (cv, lo, hi) in enumerate(rows):
        for ci, val in cv:
            A[r, ci] += val
        lb[r] = lo
        ub[r] = hi

    return c_obj, A.tocsr(), lb, ub, x_lo, x_hi, intg, idx


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

def solve(m, n, K=None, time_limit=180, verbose=False):
    """
    Solve the Denomination puzzle on an m×n king graph.

    Parameters
    ----------
    m, n       : int    grid dimensions
    K          : int    denomination upper bound  (default: m * n)
    time_limit : float  HiGHS time limit in seconds
    verbose    : bool   print HiGHS log

    Returns
    -------
    dict with keys
        kmax       : int or None   optimal maximum denomination found
        board      : dict          {(row, col): denomination}
        solve_time : float         wall-clock seconds
        status     : str           solver status message
    """
    if K is None:
        K = m * n

    print(f"  Building ILP for {m}×{n} grid  (K = {K})…")
    t0 = time.perf_counter()

    c_obj, A, lb, ub, x_lo, x_hi, intg, idx = build_ilp(m, n, K)

    print(f"  Variables: {len(c_obj)}   Constraints: {A.shape[0]}")
    print(f"  Calling HiGHS (time limit = {time_limit:.0f}s)…")

    options = {
        "disp":        verbose,
        "time_limit":  float(time_limit),
        "mip_rel_gap": 0.0,
    }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = milp(
            c_obj,
            constraints=LinearConstraint(A, lb, ub),
            integrality=intg,
            bounds=Bounds(x_lo, x_hi),
            options=options,
        )

    elapsed = time.perf_counter() - t0

    cells = [(i, j) for i in range(m) for j in range(n)]
    board = {}
    kmax  = None

    if result.x is not None:
        kmax = int(round(-result.fun))
        for c in cells:
            v = int(round(result.x[idx[("d", c)]]))
            if v > 0:
                board[c] = v

    return {
        "kmax":       kmax,
        "board":      board,
        "solve_time": elapsed,
        "status":     result.message,
    }


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_solution(m, n, result):
    board = result["board"]
    km    = result["kmax"]
    t     = result["solve_time"]
    status = result["status"].split("(")[0].strip()

    print()
    print(f"  Grid   : {m} × {n}   ({m*n} cells)")
    print(f"  k_max  : {km if km is not None else '—  (no solution found)'}")
    print(f"  Used   : {len(board)} / {m*n} cells")
    print(f"  Time   : {t:.1f}s")
    print(f"  Status : {status}")

    if not board:
        return

    print()
    sep = "  +" + ("--------+" * n)
    print(sep)
    for i in range(m):
        row = "  |"
        for j in range(n):
            v = board.get((i, j), 0)
            cell = " 1*  " if v == 1 else (f"  {v:<2} " if v else "  _  ")
            row += cell + "|"
        print(row)
        print(sep)
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    if len(args) >= 2:
        # Command-line mode:  python denomination_ilp.py m n [time_limit]
        try:
            m    = int(args[0])
            n    = int(args[1])
            tlim = float(args[2]) if len(args) >= 3 else 180.0
        except ValueError:
            print("Usage: python denomination_ilp.py [m n [time_limit_seconds]]")
            sys.exit(1)
    else:
        # Interactive mode
        print()
        print("  ╔══════════════════════════════════════╗")
        print("  ║  Denomination ILP Solver             ║")
        print("  ║  Finds optimal k_max on an m×n grid  ║")
        print("  ╚══════════════════════════════════════╝")
        print()
        try:
            m    = int(input("  Rows  m  (1–9): ").strip())
            n    = int(input("  Cols  n  (1–9): ").strip())
            raw  = input("  Time limit in seconds  [180]: ").strip()
            tlim = float(raw) if raw else 180.0
        except (ValueError, KeyboardInterrupt, EOFError):
            print("\n  Invalid input. Exiting.")
            sys.exit(1)

    if not (1 <= m <= 9 and 1 <= n <= 9):
        print("  Error: m and n must be between 1 and 9.")
        sys.exit(1)

    print()
    result = solve(m, n, time_limit=tlim)
    print_solution(m, n, result)


if __name__ == "__main__":
    main()
