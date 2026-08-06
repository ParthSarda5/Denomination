"""
Shared subroutines used across denomination_ilp.py, bruteforce.py, and
denomination_game.py: king-graph construction/adjacency, cell
neighbourhoods, the symmetry group of the m x n rectangle (used to
deduplicate reachable board states in bruteforce.py), and small I/O/render
helpers.
"""

import csv
import os

import networkx as nx


# ---------------------------------------------------------------------------
# Plain (non-networkx) adjacency, used by bruteforce.py's state search.
# Cells are 1-indexed (c, r) here to match the manuscript's convention.
# ---------------------------------------------------------------------------

def grid_cells(m, n):
    """All cells (c, r) of the m x n grid, 1-indexed."""
    return [(c, r) for c in range(1, m + 1) for r in range(1, n + 1)]


def neighbors_map(m, n):
    """Return (V, Nbr) where V is the list of cells and Nbr[v] is the list
    of v's king-graph neighbours (1-indexed cells)."""
    V = grid_cells(m, n)
    Nbr = {}
    for v in V:
        c, r = v
        out = []
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == 0 and dr == 0:
                    continue
                nc, nr = c + dc, r + dr
                if 1 <= nc <= m and 1 <= nr <= n:
                    out.append((nc, nr))
        Nbr[v] = out
    return V, Nbr


def symmetry_maps(m, n):
    """The symmetry group of the m x n rectangle under king-graph adjacency:
    identity, horizontal/vertical flip, 180 rotation (order 4), plus the
    diagonal reflections and 90/270 rotations when m == n (order 8)."""

    def identity(v):
        return v

    def flip_h(v):
        c, r = v
        return (m + 1 - c, r)

    def flip_v(v):
        c, r = v
        return (c, n + 1 - r)

    def flip_hv(v):
        c, r = v
        return (m + 1 - c, n + 1 - r)

    base = [identity, flip_h, flip_v, flip_hv]

    if m != n:
        return base

    def transpose(v):
        c, r = v
        return (r, c)

    return base + [lambda v, f=f: transpose(f(v)) for f in base]


def canonical_key(state, syms):
    """Smallest (over the symmetry group) sorted-tuple representation of a
    board state (an iterable of (cell, denomination) pairs); used purely as
    a dedup key when enumerating reachable states."""
    best = None
    for s in syms:
        transformed = tuple(sorted((s(cell), val) for cell, val in state))
        if best is None or transformed < best:
            best = transformed
    return best


def render_board(m, n, board):
    """board: dict cell -> denomination (1-indexed cells). Returns a
    printable grid string."""
    lines = []
    for r in range(n, 0, -1):
        row = []
        for c in range(1, m + 1):
            v = (c, r)
            row.append(f"{board[v]:>3}" if v in board else "  .")
        lines.append(" ".join(row))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# networkx-based king graph, used by denomination_ilp.py. Cells are
# 0-indexed (r, c) here to match the MILP file's original convention.
# ---------------------------------------------------------------------------

def king_graph(rows, cols):
    G = nx.Graph()
    cells = [(r, c) for r in range(rows) for c in range(cols)]
    G.add_nodes_from(cells)
    for (r, c) in cells:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    G.add_edge((r, c), (nr, nc))
    return G


# ---------------------------------------------------------------------------
# Results table I/O
# ---------------------------------------------------------------------------

def load_kmax_table(path=None):
    """Load data/kmax_table.csv into a dict {(m, n): kmax}."""
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "..", "data", "kmax_table.csv")
    table = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            table[(int(row["m"]), int(row["n"]))] = int(row["kmax"])
    return table
