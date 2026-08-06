$title Denomination puzzle: exact MILP formulation

$onText
This program implements the formulation with variables
    x(v,k), y(k), p(u,v), tau(v), and w(u,v)
for an m-by-n king grid.

The two implementation identities
    z(v) = sum(k, x(v,k))
    d(v) = sum(k, ord(k)*x(v,k))
are included explicitly because z and d are used throughout the model.

Default instance: 3 by 3.
Examples:
    gams denomination.gms
    gams denomination.gms --M=4 --N=4
    gams denomination.gms --M=4 --N=4 --SOLVER=cplex

The program writes:
    denomination_board.csv
    denomination_sequence.csv
    denomination_arcs.csv
$offText


options
mip = gurobi,
OptCA = 0,
optcr = 0
;



$if not set M $set M 4
$if not set N $set N 5
$eval KMAX %M%*%N%


Sets
    c       columns                    / c1*c%M% /
    r       rows                       / r1*r%N% /
    k       possible denominations     / k1*k%KMAX% /
    s       possible placement steps   / s1*s%KMAX% /;

Alias (c,cc), (r,rr);

Sets
    arc(c,r,cc,rr)   both orientations of every king-graph edge
    edge(c,r,cc,rr)  one stored orientation of each undirected edge;

Parameters
    cellId(c,r)      lexicographic cell identifier
    denomVal(k)      numerical denomination represented by k
    delta(c,r)       number of king-graph neighbors
    bigM(c,r)        neighborhood big-M value;

Scalars
    numCells         number of cells
    Kbar              denomination upper bound;

numCells   = card(c)*card(r);
Kbar       = card(k);
cellId(c,r)= (ord(c)-1)*card(r) + ord(r);
denomVal(k)= ord(k);

* Chebyshev distance one gives king adjacency.
arc(c,r,cc,rr) = yes$(
    max(abs(ord(c)-ord(cc)),abs(ord(r)-ord(rr))) = 1
);

* Keep one orientation of each undirected edge for constraints that
* involve p(u,v)+p(v,u).
edge(c,r,cc,rr) = yes$(
    arc(c,r,cc,rr) and cellId(c,r) < cellId(cc,rr)
);

delta(c,r) = sum((cc,rr)$arc(cc,rr,c,r),1);
bigM(c,r)  = Kbar*max(1,delta(c,r));

Binary Variables
    x(c,r,k)         1 if cell CR receives denomination k
    y(k)             1 if denomination k appears
    p(c,r,cc,rr)     1 if CR and CCRR are occupied and first precedes second;

Positive Variables
    z(c,r)           occupied-cell indicator, defined from x
    d(c,r)           denomination at a cell, defined from x
    tau(c,r)         ordering potential
    w(c,r,cc,rr)     denomination contributed by first cell to second cell;

Free Variable
    objective;

* Tight bounds and removal of non-edge variables.
z.up(c,r) = 1;
d.up(c,r) = Kbar;
tau.up(c,r) = numCells-1;
w.up(c,r,cc,rr)$arc(c,r,cc,rr) = Kbar;
p.fx(c,r,cc,rr)$(not arc(c,r,cc,rr)) = 0;
w.fx(c,r,cc,rr)$(not arc(c,r,cc,rr)) = 0;

Equations
    objectiveDef
    zDefinition(c,r)
    dDefinition(c,r)
    assignment(c,r)
    linkAppear1(c,r,k)
    linkAppear2(k)
    contiguity(k)
    orientation1(c,r,cc,rr)
    orientation2(c,r,cc,rr)
    orientation3(c,r,cc,rr)
    orderBounds(c,r)
    acyclicity(c,r,cc,rr)
    valueOrder(c,r,cc,rr)
    contribution1(c,r,cc,rr)
    contribution2(c,r,cc,rr)
    contribution3(c,r,cc,rr)
    neighborhoodLB(c,r,k)
    neighborhoodUB(c,r,k)
    nullRule(c,r,cc,rr)
    firstDenomination;

objectiveDef..
    objective =e= sum(k,y(k));

* Definitions used in the article's constraints.
zDefinition(c,r)..
    z(c,r) =e= sum(k,x(c,r,k));

dDefinition(c,r)..
    d(c,r) =e= sum(k,denomVal(k)*x(c,r,k));

* At most one denomination per cell.
assignment(c,r)..
    sum(k,x(c,r,k)) =l= 1;

* y(k)=1 exactly when denomination k appears.
linkAppear1(c,r,k)..
    x(c,r,k) =l= y(k);

linkAppear2(k)..
    y(k) =l= sum((c,r),x(c,r,k));

* Appearing denominations form the prefix 1,...,k_max.
contiguity(k)$(ord(k)>1)..
    y(k) =l= y(k-1);

* Every occupied undirected edge is oriented exactly once;
* an edge incident to an empty cell is not oriented.
orientation1(c,r,cc,rr)$edge(c,r,cc,rr)..
    z(c,r) + z(cc,rr) - 1
    =l= p(c,r,cc,rr) + p(cc,rr,c,r);

orientation2(c,r,cc,rr)$edge(c,r,cc,rr)..
    p(c,r,cc,rr) + p(cc,rr,c,r) =l= z(c,r);

orientation3(c,r,cc,rr)$edge(c,r,cc,rr)..
    p(c,r,cc,rr) + p(cc,rr,c,r) =l= z(cc,rr);

* Empty cells have tau=0; occupied cells have tau in [0,N-1].
orderBounds(c,r)..
    tau(c,r) =l= (numCells-1)*z(c,r);

* A selected precedence arc strictly increases the potential.
acyclicity(c,r,cc,rr)$arc(c,r,cc,rr)..
    tau(c,r) + 1
    =l= tau(cc,rr) + numCells*(1-p(c,r,cc,rr));

* Along a precedence arc, denomination cannot decrease.
valueOrder(c,r,cc,rr)$arc(c,r,cc,rr)..
    d(c,r)
    =l= d(cc,rr) + Kbar*(1-p(c,r,cc,rr));

* Linearization of w(u,v)=d(u)*p(u,v).
contribution1(c,r,cc,rr)$arc(c,r,cc,rr)..
    w(c,r,cc,rr) =l= Kbar*p(c,r,cc,rr);

contribution2(c,r,cc,rr)$arc(c,r,cc,rr)..
    w(c,r,cc,rr) =l= d(c,r);

contribution3(c,r,cc,rr)$arc(c,r,cc,rr)..
    w(c,r,cc,rr)
    =g= d(c,r) - Kbar*(1-p(c,r,cc,rr));

* A non-null cell receives exactly the sum of earlier neighbors.
neighborhoodLB(c,r,k)$(ord(k)>1)..
    sum((cc,rr)$arc(cc,rr,c,r),w(cc,rr,c,r))
    =g= denomVal(k) - bigM(c,r)*(1-x(c,r,k));

neighborhoodUB(c,r,k)$(ord(k)>1)..
    sum((cc,rr)$arc(cc,rr,c,r),w(cc,rr,c,r))
    =l= denomVal(k) + bigM(c,r)*(1-x(c,r,k));

* No occupied neighbor may precede a null stone at the destination cell.
nullRule(c,r,cc,rr)$arc(c,r,cc,rr)..
    p(c,r,cc,rr) =l= 1-x(cc,rr,'k1');

firstDenomination..
    y('k1') =e= 1;

Model denomination / all /;

option optcr  = 0;
option reslim = 3600;
option limrow = 0;
option limcol = 0;

Solve denomination using mip maximizing objective;

* ----------------------------------------------------------------------
* Reconstruct one legal placement sequence.
*
* Cells are ordered first by final denomination, then by tau, and finally
* by cellId.  The value-order and acyclicity constraints ensure that this
* respects every selected precedence arc.  Ordering by denomination also
* enforces the global prerequisite that 1,...,k-1 appear before k.
* ----------------------------------------------------------------------
Sets
    occupied(c,r)
    remaining(c,r)
    candidateD(c,r)
    candidateTau(c,r)
    chosen(c,r)
    placement(s,c,r);

Parameters
    board(c,r)       final denomination
    stepOf(c,r)      reconstructed placement step
    predecessorSum(c,r)
    cellResidual(c,r);

Scalars
    minD
    minTau
    minId
    article3x3Claim
    article3x3Match;

board(c,r)    = round(d.l(c,r));
occupied(c,r) = yes$(z.l(c,r)>0.5);
remaining(c,r)= occupied(c,r);
stepOf(c,r)   = 0;

loop(s$(card(remaining)>0),
    minD = smin((c,r)$remaining(c,r),board(c,r));

    candidateD(c,r) = no;
    candidateD(c,r) = yes$(remaining(c,r) and board(c,r)=minD);

    minTau = smin((c,r)$candidateD(c,r),tau.l(c,r));

    candidateTau(c,r) = no;
    candidateTau(c,r) = yes$(
        candidateD(c,r) and abs(tau.l(c,r)-minTau)<1e-7
    );

    minId = smin((c,r)$candidateTau(c,r),cellId(c,r));

    chosen(c,r) = no;
    chosen(c,r) = yes$(candidateTau(c,r) and cellId(c,r)=minId);

    placement(s,c,r) = chosen(c,r);
    stepOf(c,r)$chosen(c,r) = ord(s);
    remaining(c,r)$chosen(c,r) = no;
);

predecessorSum(c,r) = sum((cc,rr)$(
       arc(cc,rr,c,r)
   and stepOf(cc,rr)>0
   and stepOf(cc,rr)<stepOf(c,r)
),board(cc,rr));

cellResidual(c,r)$occupied(c,r) =
    predecessorSum(c,r) - board(c,r);
cellResidual(c,r)$(occupied(c,r) and board(c,r)=1) =
    predecessorSum(c,r);

* The article's worked 3-by-3 instance reports k_max=7.
article3x3Claim = 0;
article3x3Claim$((card(c)=3) and (card(r)=3)) = 7;
article3x3Match = 1;
article3x3Match$(article3x3Claim>0) =
    abs(objective.l-article3x3Claim)<0.5;

Display
    denomination.modelstat,
    denomination.solvestat,
    objective.l,
    article3x3Claim,
    article3x3Match,
    delta,
    bigM,
    board,
    stepOf,
    tau.l,
    predecessorSum,
    cellResidual;

* ----------------------------------------------------------------------
* Machine-readable output files.
* Coordinates follow the article: column increases left-to-right and row
* increases bottom-to-top.
* ----------------------------------------------------------------------
File boardOut / denomination_board.csv /;
put boardOut;
put 'column,row,denomination,tau,placement_step' /;
loop((c,r),
    put ord(c):0:0, ',', ord(r):0:0, ',', board(c,r):0:0, ',',
        tau.l(c,r):0:6, ',', stepOf(c,r):0:0 /;
);
putclose boardOut;

File sequenceOut / denomination_sequence.csv /;
put sequenceOut;
put 'step,column,row,denomination,tau,predecessor_sum' /;
loop((s,c,r)$placement(s,c,r),
    put ord(s):0:0, ',', ord(c):0:0, ',', ord(r):0:0, ',',
        board(c,r):0:0, ',', tau.l(c,r):0:6, ',',
        predecessorSum(c,r):0:0 /;
);
putclose sequenceOut;

File arcOut / denomination_arcs.csv /;
put arcOut;
put 'from_column,from_row,to_column,to_row,from_denomination,contribution' /;
loop((c,r,cc,rr)$(arc(c,r,cc,rr) and p.l(c,r,cc,rr)>0.5),
    put ord(c):0:0, ',', ord(r):0:0, ',',
        ord(cc):0:0, ',', ord(rr):0:0, ',',
        board(c,r):0:0, ',', w.l(c,r,cc,rr):0:0 /;
);
putclose arcOut;
