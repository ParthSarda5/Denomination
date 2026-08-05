import time
from collections import deque


def neighbors_map(m, n):
    V = [(c, r) for c in range(1, m + 1) for r in range(1, n + 1)]
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
    """Return list of coordinate-transform functions forming the symmetry
    group of the m x n rectangle under king-graph adjacency (dihedral group
    of order 4, or order 8 when m == n)."""

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

    extra = []
    for f in base:
        extra.append(lambda v, f=f: transpose(f(v)))
    return base + extra


def canonical_key(state, syms):
    """Smallest (over the symmetry group) sorted-tuple representation of a
    board state; used purely as a dedup key."""
    best = None
    for s in syms:
        transformed = tuple(sorted((s(cell), val) for cell, val in state))
        if best is None or transformed < best:
            best = transformed
    return best


def solve_exact(m, n, verbose=True, time_limit=None):
    """Exact BFS over reachable board states. Returns (kmax, sequence, stats).
    sequence is a list of (cell, denomination) placements, in order, that is
    a legal Denomination sequence attaining kmax on the m x n grid.
    """
    t_start = time.time()
    V, Nbr = neighbors_map(m, n)
    syms = symmetry_maps(m, n)

    start = frozenset()
    seen_canonical = {canonical_key(start, syms)}
    parent = {start: None}
    move_that_led = {start: None}

    best_kmax = 1
    best_state = start

    frontier = [start]
    level = 0
    total_states_expanded = 0

    while frontier:
        level += 1
        next_frontier = []
        for state in frontier:
            board = dict(state)
            M = max(board.values()) if board else 0
            occupied = board.keys()
            for v in V:
                if v in occupied:
                    continue
                placed_nbrs = [u for u in Nbr[v] if u in occupied]
                if not placed_nbrs:
                    k = 1  # Rule 1: null stone
                else:
                    s = sum(board[u] for u in placed_nbrs)
                    if s < 2 or s > M + 1:
                        continue  # cannot be legal: violates Rule 2/3 bound
                    k = s
                new_state = state | frozenset({(v, k)})
                ckey = canonical_key(new_state, syms)
                if ckey in seen_canonical:
                    continue
                seen_canonical.add(ckey)
                parent[new_state] = state
                move_that_led[new_state] = (v, k)
                next_frontier.append(new_state)
                total_states_expanded += 1
                new_M = max(M, k)
                if new_M > best_kmax:
                    best_kmax = new_M
                    best_state = new_state
        if verbose:
            elapsed = time.time() - t_start
            print(f"  level {level}: {len(next_frontier)} new states "
                  f"(cumulative {total_states_expanded}), best k_max so far "
                  f"= {best_kmax}  [{elapsed:.1f}s]")
        if time_limit is not None and (time.time() - t_start) > time_limit:
            print(f"  ** time limit reached ({time_limit}s); result below is "
                  f"a lower bound, not yet proven optimal **")
            frontier = []
            break
        frontier = next_frontier

    # reconstruct the sequence for best_state
    seq = []
    s = best_state
    while s is not None and move_that_led[s] is not None:
        seq.append(move_that_led[s])
        s = parent[s]
    seq.reverse()

    stats = {
        "states_expanded": total_states_expanded,
        "time": time.time() - t_start,
        "proven_optimal": not (time_limit is not None and (time.time() - t_start) > time_limit),
    }
    return best_kmax, seq, stats


def render_sequence(m, n, seq):
    board = {}
    lines = []
    for i, (v, k) in enumerate(seq, 1):
        board[v] = k
        lines.append(f"Step {i:2d}: place {'null 1*' if k == 1 else k} at {v}")
    lines.append("")
    lines.append("Final board:")
    for r in range(n, 0, -1):
        row = []
        for c in range(1, m + 1):
            v = (c, r)
            row.append(f"{board[v]:>3}" if v in board else "  .")
        lines.append(" ".join(row))
    return "\n".join(lines)


def solve_branch_and_bound(m, n, time_limit=240, tt_max_size=4_000_000, verbose=True):
    """Depth-first branch-and-bound search for k_max, for grids too large for
    the exact BFS in solve_exact (memory blows up there well before 5x5).

    This explores the *same* legal-move space as solve_exact (Rule 1/2/3,
    with the s <= M+1 bound derived in the docstring above)

    Returns (kmax, sequence, stats). stats['proven_optimal'] is True only if
    the search provably exhausted the space within time_limit; otherwise the
    reported kmax is a lower bound (with a witnessing instance), not a proof.
    """
    t_start = time.time()
    V, Nbr = neighbors_map(m, n)
    N = len(V)
    idx = {v: i for i, v in enumerate(V)}
    Nbr_idx = [[idx[u] for u in Nbr[v]] for v in V]  # neighbor indices per cell

    best = {"kmax": 1, "seq": []}
    seen = set()
    timed_out = [False]
    node_count = [0]

    arr = [0] * N  # 0 = empty; compact fixed-order board representation

    def dfs(seq, M, empty_idx):
        if timed_out[0]:
            return
        node_count[0] += 1
        if node_count[0] % 200000 == 0:
            if time.time() - t_start > time_limit:
                timed_out[0] = True
                return
        if M > best["kmax"]:
            best["kmax"] = M
            best["seq"] = list(seq)
            if verbose:
                print(f"    new incumbent: k_max >= {M}  "
                      f"(nodes: {node_count[0]}, tt size: {len(seen)}, "
                      f"time: {time.time()-t_start:.1f}s)", flush=True)
        if M + len(empty_idx) <= best["kmax"]:
            return  # cannot possibly beat the incumbent from here

        if len(seen) < tt_max_size:
            key = tuple(arr)
            if key in seen:
                return
            seen.add(key)

        candidates = []
        for vi in empty_idx:
            placed_nbrs = [ui for ui in Nbr_idx[vi] if arr[ui] != 0]
            if not placed_nbrs:
                candidates.append((vi, 1))
            else:
                s = sum(arr[ui] for ui in placed_nbrs)
                if 2 <= s <= M + 1:
                    candidates.append((vi, s))
        candidates.sort(key=lambda vk: -vk[1])  # try record-extending moves first

        for vi, k in candidates:
            arr[vi] = k
            seq.append((V[vi], k))
            empty_idx.discard(vi)
            dfs(seq, max(M, k), empty_idx)
            empty_idx.add(vi)
            seq.pop()
            arr[vi] = 0
            if timed_out[0]:
                return

    dfs([], 0, set(range(N)))

    stats = {
        "states_seen": len(seen),
        "time": time.time() - t_start,
        "proven_optimal": not timed_out[0],
    }
    if verbose:
        tag = "PROVEN OPTIMAL" if stats["proven_optimal"] else "TIME LIMIT HIT (lower bound only)"
        print(f"  [{tag}] k_max >= {best['kmax']}, "
              f"states seen: {stats['states_seen']}, time: {stats['time']:.1f}s")
    return best["kmax"], best["seq"], stats


if __name__ == "__main__":
    for (m, n) in [(2, 2), (2, 3), (3, 3), (3, 4), (4, 4)]:
        print(f"\n=== {m} x {n} grid ===")
        kmax, seq, stats = solve_exact(m, n, verbose=True)
        print(f"k_max = {kmax}  "
              f"(states expanded: {stats['states_expanded']}, "
              f"time: {stats['time']:.2f}s, proven optimal: {stats['proven_optimal']})")
        print(render_sequence(m, n, seq))
