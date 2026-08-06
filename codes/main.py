"""
Concrete example of how to run the code in this repository end to end.

By default: solves the 3x3 grid with the MILP formulation in
denomination_ilp.py, reproduces the worked example from the manuscript
(k_max = 7), and cross-checks the result against the independent enumerator
in bruteforce.py.

Note: denomination_ilp.py indexes cells 0-indexed as (row, col), while
bruteforce.py indexes cells 1-indexed as (col, row) (matching the
manuscript's convention) -- both give the same board up to relabeling, so
only kmax (not the raw board dict) is compared directly below.
"""

from denomination_ilp import solve_and_extract
from bruteforce import solve_exact, render_sequence


def cross_check(rows, cols, milp_time_limit=None):
    print(f"\n=== Cross-checking {rows}x{cols} grid ===")

    milp_res = solve_and_extract(rows, cols, msg=False, time_limit=milp_time_limit)
    print(f"MILP (denomination_ilp.py):   status={milp_res['status']}  "
          f"k_max = {milp_res['kmax']}")

    verify_kmax, seq, stats = solve_exact(cols, rows, verbose=False)
    print(f"Enumerator (bruteforce.py):   k_max = {verify_kmax}  "
          f"(proven optimal: {stats['proven_optimal']})")

    status = "MATCH" if milp_res["kmax"] == verify_kmax else "MISMATCH"
    print(f"--> {status}")

    print(render_sequence(cols, rows, seq))
    return milp_res, verify_kmax


if __name__ == "__main__":
    # Reproduce the manuscript's worked example: the 3x3 king graph attains
    # k_max = 7. (CBC can take a while to prove optimality on 3x3 -- see the
    # computational notes in the manuscript -- so a generous time limit is
    # set here; the enumerator's result is exact and fast regardless.)
    cross_check(3, 3, milp_time_limit=120)

    # Uncomment to explore other grid sizes. The exact enumerator
    # (solve_exact) is only feasible up to roughly 4x4; for larger grids,
    # use bruteforce.solve_branch_and_bound(m, n, time_limit=...) instead.
    # cross_check(2, 3)
    # cross_check(3, 4)

    # To launch the interactive Pygame version instead, run:
    #     python3 ./milp_and_enumerator/denomination_game.py
