import itertools
import networkx as nx
import pulp
 
 
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
 
 
def build_milp(rows, cols, K=None):
    cells = [(r, c) for r in range(rows) for c in range(cols)]
    N = len(cells)
    if K is None:
        K = N
 
    G = king_graph(rows, cols)
    NB = {v: list(G.neighbors(v)) for v in cells}
    deg = {v: len(NB[v]) for v in cells}
    real_edges = set(tuple(sorted(e)) for e in G.edges())
 
    # chordal completion: adds the minimal extra "bookkeeping" pairs
    # needed so that triangle-only consistency constraints are globally
    # sufficient (king graphs are not chordal from 3x3 upward).
    H, _ = nx.complete_to_chordal_graph(G)
    all_edges = set(tuple(sorted(e)) for e in H.edges())
    fillin_edges = all_edges - real_edges
    triangles = [c for c in nx.enumerate_all_cliques(H) if len(c) == 3]
 
    prob = pulp.LpProblem("Denomination", pulp.LpMaximize)
 
    # ---- placement variables -------------------------------------------
    x = {(v, k): pulp.LpVariable(f"x_{v}_{k}", cat="Binary")
         for v in cells for k in range(1, K + 1)}
    for v in cells:
        prob += pulp.lpSum(x[v, k] for k in range(1, K + 1)) <= 1
 
    d = {v: pulp.lpSum(k * x[v, k] for k in range(1, K + 1)) for v in cells}
    z = {v: pulp.lpSum(x[v, k] for k in range(1, K + 1)) for v in cells}
 
    y = {k: pulp.LpVariable(f"y_{k}", cat="Binary") for k in range(1, K + 1)}
    for k in range(1, K + 1):
        prob += y[k] <= pulp.lpSum(x[v, k] for v in cells)
    for k in range(2, K + 1):
        prob += y[k] <= y[k - 1]                      # contiguity (Rule 3, see theorem above)
    prob += pulp.lpSum(y[k] for k in range(1, K + 1))  # objective
 
    # ---- 'before' indicators: one per edge of the chordal completion ----
    b = {}
    for (u, v) in all_edges:
        bv = pulp.LpVariable(f"b_{u}_{v}", cat="Binary")
        b[(u, v)] = bv
        if (u, v) in real_edges:
            # value-based linking (Consequence 1): forced when both cells
            # are occupied and values differ; relaxed (vacuous) whenever
            # either cell is empty, since d=0 for an empty cell is just a
            # bookkeeping placeholder, not a real "value" the ordering
            # theorem applies to.
            slack = K * (1 - z[u]) + K * (1 - z[v])
            prob += d[u] - d[v] <= K * (1 - bv) + slack
            prob += d[v] - d[u] <= K * bv + slack
        # fill-in edges: b left free, used only for global consistency bookkeeping
 
    def before(u, v):
        key = tuple(sorted((u, v)))
        bv = b[key]
        return bv if key == (u, v) else (1 - bv)
 
    # acyclicity on every triangle of the chordal completion
    for (u, v, w) in triangles:
        buv, bvw, bwu = before(u, v), before(v, w), before(w, u)
        prob += buv + bvw + bwu <= 2
        prob += buv + bvw + bwu >= 1
 
    # ---- contribution indicators (real neighbor edges only) -------------
    a, wcontrib = {}, {}
    for v in cells:
        for u in NB[v]:
            au = pulp.LpVariable(f"a_{u}_{v}", cat="Binary")
            bef = before(u, v)
            prob += au <= z[u]
            prob += au <= z[v]
            prob += au <= bef
            prob += au >= z[u] + z[v] + bef - 2
            a[(u, v)] = au
 
            wc = pulp.LpVariable(f"w_{u}_{v}", lowBound=0, upBound=K, cat="Continuous")
            prob += wc <= K * au
            prob += wc <= d[u]
            prob += wc >= d[u] - K * (1 - au)
            wcontrib[(u, v)] = wc
 
    # ---- Rule 2 (neighbor sum) ------------------------------------------
    for v in cells:
        Mv = deg[v] * K
        for k in range(2, K + 1):
            s = pulp.lpSum(wcontrib[(u, v)] for u in NB[v])
            prob += s >= k - Mv * (1 - x[v, k])
            prob += s <= k + Mv * (1 - x[v, k])
 
    # ---- Rule 1 (null stone) ---------------------------------------------
    for v in cells:
        for u in NB[v]:
            prob += a[(u, v)] <= 1 - x[v, 1]
 
    meta = dict(cells=cells, N=N, K=K, x=x, y=y, d=d, z=z, b=b, before=before,
                a=a, w=wcontrib, NB=NB, real_edges=real_edges,
                fillin_edges=fillin_edges, triangles=triangles)
    return prob, meta
 
 
def solve_and_extract(rows, cols, K=None, msg=False, time_limit=None, min_kmax=None):
    prob, meta = build_milp(rows, cols, K=K)
    if min_kmax is not None:
        prob += pulp.lpSum(meta["y"][k] for k in range(1, meta["K"] + 1)) >= min_kmax
    solver = pulp.PULP_CBC_CMD(msg=msg, timeLimit=time_limit)
    prob.solve(solver)
    status = pulp.LpStatus[prob.status]
 
    cells, K = meta["cells"], meta["K"]
    x = meta["x"]
    board = {}
    for v in cells:
        for k in range(1, K + 1):
            if pulp.value(x[v, k]) > 0.5:
                board[v] = k
                break
    kmax = max(board.values(), default=0)
    order = reconstruct_order(meta, board)
 
    return dict(status=status, objective=pulp.value(prob.objective),
                kmax=kmax, board=board, order=order)
 
 
def reconstruct_order(meta, board):
    """Sort occupied cells by value; break ties using the model's own
    'before' relation (topological sort within each value tier)."""
    cells = meta["cells"]
    occupied = [v for v in cells if v in board]
    by_value = {}
    for v in occupied:
        by_value.setdefault(board[v], []).append(v)
 
    order = []
    for k in sorted(by_value.keys()):
        tier = by_value[k]
        if len(tier) == 1:
            order.extend(tier)
            continue
        Gt = nx.DiGraph()
        Gt.add_nodes_from(tier)
        for u, v in itertools.combinations(tier, 2):
            key = tuple(sorted((u, v)))
            if key in meta["b"]:
                bef = meta["before"](u, v)
                val = pulp.value(bef) if hasattr(bef, "varValue") or not isinstance(bef, (int, float)) else bef
                if val is None:
                    val = 0
                if val > 0.5:
                    Gt.add_edge(u, v)
                else:
                    Gt.add_edge(v, u)
        order.extend(nx.topological_sort(Gt))
    return order
 
 
if __name__ == "__main__":
    for (rows, cols) in [(1, 1), (1, 2), (2, 2), (2, 3), (3,3)]:
        res = solve_and_extract(rows, cols, msg=False)
        print(rows, cols, res["status"], "kmax=", res["kmax"], res["board"], res["order"])
