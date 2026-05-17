"""
denomination_ilp.py

Solve the Denomination puzzle on an m x n king graph using a correct MILP.
Uses scipy.optimize.milp (HiGHS solver) – no commercial license required.

Usage:
    python denomination_ilp.py --m 3 --n 3 --time-limit 120
"""

import argparse
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import csr_matrix, lil_matrix
from itertools import product
import time
import sys

def solve_denomination(m: int, n: int, time_limit: float = 120.0):
    """
    Solve Denomination puzzle on an m x n king graph.
    
    Returns:
        k_max (int or None): optimal highest denomination (or best found)
        assignment (dict): mapping (i,j) -> denomination (0 if empty)
        solve_time (float): seconds taken
        status (str): 'Optimal', 'Time limit', or 'Infeasible'
    """
    cells = [(i, j) for i in range(m) for j in range(n)]
    V = len(cells)
    K = m * n                     # safe upper bound, can be reduced for speed

    # Build neighbour list (king graph)
    neighbours = {}
    for i, j in cells:
        neigh = []
        for di, dj in product((-1, 0, 1), repeat=2):
            if di == 0 and dj == 0:
                continue
            ni, nj = i + di, j + dj
            if 0 <= ni < m and 0 <= nj < n:
                neigh.append((ni, nj))
        neighbours[(i, j)] = neigh

    max_deg = max(len(neighbours[c]) for c in cells)
    M = max_deg * K + 1           # big-M constant

    # Variable indexing
    # x[v, k] for v in 0..V-1, k in 1..K
    # y[k] for k in 1..K
    n_x = V * K
    n_y = K
    n_vars = n_x + n_y

    def idx_x(v, k):
        return v * K + (k - 1)

    def idx_y(k):
        return n_x + (k - 1)

    # Objective: maximise sum y_k  -> minimise -sum y_k
    c = np.zeros(n_vars)
    for k in range(1, K + 1):
        c[idx_y(k)] = -1.0

    # Build constraints as a list of rows (dense, then convert to sparse)
    A_rows = []
    lb_rows = []
    ub_rows = []

    # 1) One denomination per cell
    for v in range(V):
        row = np.zeros(n_vars)
        for k in range(1, K + 1):
            row[idx_x(v, k)] = 1.0
        A_rows.append(row)
        lb_rows.append(-np.inf)
        ub_rows.append(1.0)

    # 2) Null stone independence (no two adjacent nulls)
    for u in cells:
        for v in neighbours[u]:
            if (u[0], u[1]) < (v[0], v[1]):   # each edge once
                row = np.zeros(n_vars)
                row[idx_x(cells.index(u), 1)] = 1.0
                row[idx_x(cells.index(v), 1)] = 1.0
                A_rows.append(row)
                lb_rows.append(-np.inf)
                ub_rows.append(1.0)

    # 3) Neighbourhood sum rule (for each cell and each k >= 2)
    for v_idx, v in enumerate(cells):
        for k in range(2, K + 1):
            # contrib = sum_{u in N(v)} sum_{ell=1}^{k-1} ell * x_{u,ell}
            # Lower: contrib >= k - M*(1 - x_{v,k})
            # Upper: contrib <= k + M*(1 - x_{v,k})
            row_lower = np.zeros(n_vars)
            row_upper = np.zeros(n_vars)
            for u in neighbours[v]:
                u_idx = cells.index(u)
                for ell in range(1, k):
                    row_lower[idx_x(u_idx, ell)] = ell
                    row_upper[idx_x(u_idx, ell)] = ell
            # Lower bound: contrib - M*x_{v,k} >= k - M
            row_lower[idx_x(v_idx, k)] = -M
            # Upper bound: contrib + M*x_{v,k} <= k + M
            row_upper[idx_x(v_idx, k)] = M

            A_rows.append(row_lower)
            lb_rows.append(k - M)
            ub_rows.append(np.inf)

            A_rows.append(row_upper)
            lb_rows.append(-np.inf)
            ub_rows.append(k + M)

    # 4) Appearance: y_k <= sum_v x_{v,k}  and  sum_v x_{v,k} <= V * y_k
    for k in range(1, K + 1):
        # y_k - sum_v x_{v,k} <= 0
        row1 = np.zeros(n_vars)
        row1[idx_y(k)] = 1.0
        for v in range(V):
            row1[idx_x(v, k)] = -1.0
        A_rows.append(row1)
        lb_rows.append(-np.inf)
        ub_rows.append(0.0)

        # sum_v x_{v,k} - V*y_k <= 0
        row2 = np.zeros(n_vars)
        for v in range(V):
            row2[idx_x(v, k)] = 1.0
        row2[idx_y(k)] = -V
        A_rows.append(row2)
        lb_rows.append(-np.inf)
        ub_rows.append(0.0)

    # 5) Contiguity: y_k >= y_{k+1}  -> y_{k+1} - y_k <= 0
    for k in range(1, K):
        row = np.zeros(n_vars)
        row[idx_y(k + 1)] = 1.0
        row[idx_y(k)] = -1.0
        A_rows.append(row)
        lb_rows.append(-np.inf)
        ub_rows.append(0.0)

    # 6) Link: x_{v,k} <= y_k  -> x_{v,k} - y_k <= 0
    for v in range(V):
        for k in range(1, K + 1):
            row = np.zeros(n_vars)
            row[idx_x(v, k)] = 1.0
            row[idx_y(k)] = -1.0
            A_rows.append(row)
            lb_rows.append(-np.inf)
            ub_rows.append(0.0)

    # 7) At least one null stone: y_1 = 1
    row = np.zeros(n_vars)
    row[idx_y(1)] = 1.0
    A_rows.append(row)
    lb_rows.append(1.0)
    ub_rows.append(1.0)

    # Build sparse matrix
    A = csr_matrix(np.vstack(A_rows))

    # Variable bounds: all binary
    x_low = np.zeros(n_vars)
    x_high = np.ones(n_vars)
    integrality = np.ones(n_vars, dtype=int)

    # Solve
    start = time.time()
    res = milp(
        c,
        constraints=LinearConstraint(A, lb_rows, ub_rows),
        integrality=integrality,
        bounds=Bounds(x_low, x_high),
        options={"time_limit": time_limit, "mip_rel_gap": 0.0},
    )
    elapsed = time.time() - start

    if res.status == 0:          # Optimal
        status = "Optimal"
    elif res.status == 1:        # Time limit
        status = "Time limit"
    else:
        status = f"Infeasible/unbounded (status {res.status})"
        return None, None, elapsed, status

    # Extract assignment
    assignment = {}
    for v_idx, cell in enumerate(cells):
        for k in range(1, K + 1):
            if np.abs(res.x[idx_x(v_idx, k)] - 1.0) < 0.5:
                assignment[cell] = k
                break
        else:
            assignment[cell] = 0

    # Determine k_max from y_k (largest k with y_k == 1)
    k_max = 0
    for k in range(1, K + 1):
        if np.abs(res.x[idx_y(k)] - 1.0) < 0.5:
            k_max = k
        else:
            break
    return k_max, assignment, elapsed, status


def print_grid(assignment, m, n, title=""):
    """Pretty print the grid assignment."""
    print(f"\n{title}")
    for i in range(m):
        row = []
        for j in range(n):
            val = assignment.get((i, j), 0)
            row.append(f"{val:3d}" if val > 0 else "  .")
        print(" ".join(row))


def main():
    parser = argparse.ArgumentParser(description="Solve Denomination puzzle.")
    parser.add_argument("--m", type=int, required=True, help="Number of rows")
    parser.add_argument("--n", type=int, required=True, help="Number of columns")
    parser.add_argument("--time-limit", type=float, default=120.0, help="Time limit in seconds")
    args = parser.parse_args()

    print(f"Solving {args.m}x{args.n} grid (time limit {args.time_limit}s)...")
    k_max, assign, t, status = solve_denomination(args.m, args.n, args.time_limit)

    if k_max is None:
        print(f"Solver failed: {status}")
        sys.exit(1)

    print(f"\nStatus: {status}, solve time: {t:.2f}s")
    print(f"Optimal maximum denomination k_max = {k_max}")
    print_grid(assign, args.m, args.n, "Optimal grid configuration:")


if __name__ == "__main__":
    main()
