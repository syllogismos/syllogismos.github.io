---
layout: post
title: "Facebook Link Prediction"
date: 2014-08-10 08:11:37 +0530
comments: true
categories: 
---
note: I did this just as an exercise, you get much more from [this post](http://blog.echen.me/2012/07/31/edge-prediction-in-a-social-graph-my-solution-to-facebooks-user-recommendation-contest-on-kaggle/).

## Link Prediction:
We are given snapshot of a network and would like to infer which which interactions among existing
members are likely to occur in the near future or which existing interactions are we missing. The challenge is to effectively combine the information from the network structure with rich node and edge
attribute data.

## Supervised Random Walks:
This repository is the implementation of Link prediction based on the paper Supervised Random Walks by  Lars Backstrom et al. The essence of which is that we combine the information from the network structure with the node and edge level attributes using Supervised Random Walks. We achieve this by using these attributes to guide a random walk on the graph. We formulate a supervised learning task where the goal is to learn a function that assigns strengths to edges in the network such that a random walker is more likely to visit the nodes to which new links will be created in the future. We develop an efficient training algorithm to directly learn the edge strength estimation function.

## Problem Description:
We are given a directed graph _G(V,E)_, a node _s_ and a set of candidates to which _s_ could create an edge. We label nodes to which _s_ creates edges in the future as _destination nodes D = {d<sub>1</sub>,..,d<sub>k</sub>}_, while we call the other nodes to which s does not create edges no-link nodes _L = {l<sub>1</sub>,..,l<sub>n</sub>}_. We label candidate nodes with a set _C = D union L_. _D_ are positive training examples and _L_ are negative training examples. We can generalize this to multiple instances of _s, D, L_. Each node and each edge in G is further described with a set of features. We assume that each edge _(u,v)_ has a corresponding feature vector psi<sub>uv</sub> that describes u and v and the interaction attributes.

For each edge (u,v) in G we compute the strength _a<sub>uv</sub> = f<sub>w</sub>(psi<sub>uv</sub>)_. Function _f<sub>w</sub>_ parameterized by _w_ takes the edge feature vector _psi<sub>uv</sub>_ as input and computes the corresponding edge strength _a<sub>uv</sub>_ that models the random walk transition probability. It is exactly the function _f<sub>w</sub>(psi)_ we learn in the training phase of the algorithm.

To predict new edges to _s_, first edge strengths of all edges are calculated using _f<sub>w</sub>_. Then random walk with restarts is run from _s_. The stationary distribution _p_ of random walk assigns each node _u_ a probability _p<sub>u</sub>_. Nodes are ordered by _p<sub>u</sub>_ and top ranked nodes are predicted as future destination nodes to _s_. The task is to learn the parameters _w_ of function _f<sub>w</sub>(psi<sub>uv</sub>)_ that assigns each edge a transition probability. One can think of the weights _a<sub>uv</sub>_ as edge strengths and the random walk is more likely to traverse edges of high strength and thus nodes connected to node _s_ via paths of strong edges will likely to be visited by the random walk and will thus rank higher.

### The optimization problem:
The training data contains information that source node _s_ will create edges to node _d subset D_ and not _l subset L_. So we set parameters _w_ of the function _f<sub>w</sub>(psi<sub>uv</sub>)_ so that it will assign edge weights _a<sub>uv</sub>_ in such a way that the random walk will be more likely to visit nodes in _D_ than _L_, _i.e.,_ _p<sub>l</sub> < p<sub>d</sub>_ for each _d subset D_ and _l subset L_. And thus we define the optimization problem as follows.  
![optimization problem hard version](http://i.imgur.com/zMjJ1Nb.png)  

where _p_ is the vector of pagerank scores. Pagerank scores _p<sub>i</sub>_ depend on edge strength on _a<sub>uv</sub>_ and thus actually depend on _f<sub>w</sub>(psi<sub>uv</sub>)_ which is parameterized by _w_. The above equation (1) simply states that we want to find _w_ such that the pagerank score of nodes in _D_ will be greater than the scores of nodes in _L_. We prefer the shortest _w_ parameters simply for the sake of regularization. But the above equation is the "hard" version of the optimization problem. However it is unlikely that a solution satisfying all the constraints exist. We make the optimization problem "soft" by introducing a loss function that penalizes the violated constraints. Now the optimization problem becomes,  
![optimization problem soft version.](http://i.imgur.com/oZ2pYN1.png)  
where lambda is the regularization parameter that trades off between the complexity(norm of _w_) for the fit of the model(how much the constraints can be violated). And _h(.)_ is a loss function that assigns a non-negative penalty according to the difference of the scores _p<sub>l</sub>-p<sub>d</sub>_. _h(.) = 0_ if _p<sub>l</sub> < p<sub>d</sub>_ as the constraint is not violated and _h(.) > 0_ if _p<sub>l</sub> > p<sub>d</sub>_

### Solving the optimization problem:
First we need to establish connection between the parameters _w_ and the random walk scores _p_. Then we show how to obtain partial derivatives of the loss function and _p_ with respect to _w_ and then perform gradient descent to obtain optimal values of _w_ and minimize loss.
We build a random walk stochastic transition matrix _Q<sup>'</sup>_ from the edge strengths _a<sub>uv</sub>_ calculated from _f<sub>w</sub>(psi<sub>uv</sub>)_.  
![Q dash](http://i.imgur.com/JiSHf7t.png)  

To obtain the final random walk transition probability matrix _Q_, we also incorporate the restart probability _alpha_, _i.e.,_ the probability with which the random walk jumps back to seed node _s_, and thus "restarts".  
![Q](http://i.imgur.com/vE2P7LJ.png)  

each entry _Q<sub>uv</sub>_ deﬁnes the conditional probability that a walk will traverse edge (u, v) given that it is currently at node u.
The vector _p_ is the stationary distribution of the Random Walk with restarts(also known as Personalized Page Rank), and is the solution to the following eigen vector equation.  
![eigen vector equation](http://i.imgur.com/UFwnobA.png)  

The above equation establishes the connection between page rank scores _p_ and the parameters _w_ via the random walk transition probability matrix _Q_. Our goal now is to minimize the soft version of the loss function(eq. 2) with respect to parameter vector _w_. We do this by obtaining the gradient of _F(w)_ with respect to _w_, and then performing gradient based optimization method to find _w_ that minimize _F(w)_. This gets complicated due to the fact that equation 4 is recursive. For this we introduce _delta<sub>ld</sub> = p<sub>l</sub>-p<sub>d</sub>_ and then we can write the derivative  
![delta ld](http://i.imgur.com/FhZVZEB.png)  
and then we can write the derivative of _F(w)_ as follows  
![lossfunction gradient with delta](http://i.imgur.com/oisE40X.png)  
For commonly used loss functions _h(.)_ it is easy to calculate derivative, but it is not clear how to obtain partial derivatives of _p_ wrt _w_. _p_ is the principle eigen vector of matrix _Q_. The above eigen vector equation can also be written as follows.  
![eigen vector reduced form.](http://i.imgur.com/z00CXm4.png)  
and taking the derivatives now gives  
![derivative of p recursive form](http://i.imgur.com/FhZVZEB.png)  
above _p<sub>u</sub>_ and its partial derivative are entangled in the equation, however we compute the above values iteratively as follows  
![power method to compute p and its partial derivative iteratively.](http://i.imgur.com/WneoOOn.png)  
we initialize the vector _p_ as _1/|V|_ and all its derivatives as zeroes before the iteration starts and terminates the recursion till the _p_ and its derivatives converge for an epsilon say _10e-12_.
To solve equation 4, we need partial derivative of _Q<sub>ju</sub>_, this calculation is straight forward. When _(j,u) subset E_ derivative of _Q<sub>ju</sub>_ is  
![partial derivative of Qju](http://i.imgur.com/aLDlWP4.png)  
and derivative of _Q<sub>ju</sub>_ is zero if edge _(j,u)_ is not a subset of _E_.

## My Implementation:
We are given a huge network with existing connections. When predicting future link of a particular node, we consider that _s_, and the graph _G(E,V)_ is 
Here we explain how each helper function and main functions implements the above algorithm..
### FeaturesFromAdjacentMatrix.m:
This is a temporary function specific to the facebook data that generates Features of each edge from a given adjacency matrix. For other problems this function must be replaced with something that generates feature vector for each edge based on graph _G(E,V)_ and node, edge attributes. For an network with _n_ nodes this function returns _n x n x m_ matrix, where _m_ is the size of parameter vector _w_(sometimes _m+1_)

-   arguments:
     - Adjacency matrix, node attributes, edge attributes

-   returns:
     - _psi size(nxnxm)_

### FeaturesToEdgeStrength.m:
This function takes the feature matrix (_psi_) and the parameter vector (_w_) as arguments to return edge strength (_A_) and partial derivative of edge strength wrt to each parameter(_dA_). We also compute partial derivative of edge strength to make further calculations easier. We can vary edge strength function in future implementations, in this we used _sigmod(w x psi<sub>uv</sub>)_ as edge strength function.

-   arguments:
    - _psi size(nxnxm)_
    - _w size(1xm)_

-   returns:
    - _A size(nxn)_
    - _dA size(nxnxm)_

### EdgeStrengthToTransitionProbability.m
This function takes the edge strength matrix _A_ and _alpha_ to compute transition probability matrix _Q_.

-   arguments:
    - _A size(nxn)_
    - _alpha size(1x1)_

-   returns:
    - _Q size(nxn)_

### EdgeStrengthToPartialdiffTransition.m
This function computes partial derivative of transition probability matrix from _A_, _dA_ and _alpha_

-   arguments:
    - _A size(nxn)_
    - _dA size(nxnxm)_
    - _alpha size(1x1)_

-   returns:
    - _dQ size(nxnxm)_

### LossFunction.m
This function takes as input parameters, adjacency matrix of the network, lambda and alpha.
* We get edge strength matrix and its partial derivatives from features and parameters
* We get transition probability and partial derivatives of it from _A_ and _dA_
* We get stationary probabilities from _Q_ and _dQ_
* Compute cost and gradient from the above variables, we can use various functions as loss function _h(.)_. Here we used wilcoxon loss function.

-   arguments:
    - param: parameters of the edge strength function, size(1,m)
    - features: features of all the edges in the network, size(n,n,m)
    - d: binary vector representing destination nodes, size(1,n)
    - lambda: regularization parameter, size(1,1)
    - alpha: random restart parameter, size(1,1)

-   returns:
    - J: loss, size(1,1)
    - grad: gradient of cost wrt parameters, size(1,m)

### fmincg.m
We use this function to do the minimization of the loss function, given a starting point for the parameters, and the function that computes loss and gradients for a given parameter vector. This is similar to fminunc function available in octave.

### GetNodesFromParam.m
This function calculates the closest nodes to the root node given the parameters obtained after training.

-   arguments:
    - param: parameters, size(m,1) 
    - features: feature matrix, size(n,n,m)
    - d: binary vector representing the destination nodes, size(1,n)
    - alpha: alpha value used in calculation of Q, size(1,1)
    - y: number of nodes to output

-   returns:
    - nodes: output nodes, size(1,y)
    - P: probabilities of the nodes, size(1,n)

## How to Train:
Here I will show how to train the supervised random walk for a given root node _s_ and edge features matrix _psi_.
I'm not showing how to obtain the edge features. Given the network structure, node and edge attributes etc, you can experiment with different feature extraction techniques.
Here we have _psi_

```
octave:1> clear, close all, clc;
octave:2> rand("seed", 3410);
octave:3> m = size(psi)(3);
octave:4> n = size(psi)(1);
octave:5> initial_w = zeroes(1,m);   % initialize the parameters to zeros or rand
octave:6> initial_w = rand(1,n);

% to calculate the loss for a given parameter vector.

octave:7> [loss, grad] = LossFunction(initial_w, psi, d, lambda=1, alpha=0.2, b=0.4);

% d above is a binary vector that represents the destination nodes to begin with, 
% you can initialize this randomly or obtain it from the graph

% training
octave:8> options = optimset('GradObj', 'on', 'MaxIter', 20);
octave:9> [w,loss] = ...
	fmincg(@(t)(LossFunction(t, psi, d, lambda=1,alpha=0.2,b=0.4)),
	initial_w, options);

% w obtained above is the parameters we obtained after gradient descent

octave:10> y = 10;
octave:11> [nodes, P] = GetNodesFromParam(w, psi,d,alpha = 0.2,y);
```