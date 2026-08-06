## Denomination GAMS model

Files
-----
denomination.gms
    Exact MILP implementation of the revised formulation using x, y, p,
    tau, and w, with explicit definitions of z and d.

Running the model
-----------------
Default 3 x 3 instance:
    gams denomination.gms

Different grid dimensions:
    gams denomination.gms --M=4 --N=4

Choose a MIP solver explicitly, for example CPLEX:
    gams denomination.gms --M=4 --N=4 --SOLVER=cplex

Outputs
-------
The listing file reports the objective, board, ordering potentials,
reconstructed placement steps, predecessor sums, and residual checks.

The run also creates:
    denomination_board.csv
    denomination_sequence.csv
    denomination_arcs.csv

For the 3 x 3 instance, the article reports k_max = 7.  The scalar
article3x3Match equals 1 when the optimized objective matches that claim.

Implementation note
-------------------
The mathematical formulation uses z_v and d_v but does not list them as
independent binary decision variables.  The code implements them as
continuous variables defined exactly by
    z_v = sum_k x_{v,k},
    d_v = sum_k k x_{v,k}.
Because x is binary and each cell receives at most one denomination,
these definitions give the intended values without additional integrality.
