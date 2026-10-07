---
title: "Facebook Link Prediction"
date: 2014-08-10T08:11:37+05:30
---

Note: I did this just as an exercise, you get much more from [this post](http://blog.echen.me/2012/07/31/edge-prediction-in-a-social-graph-my-solution-to-facebooks-user-recommendation-contest-on-kaggle/).

## Link Prediction:

We are given a snapshot of a network and would like to infer which interactions among existing members are likely to occur in the near future or which existing interactions we are missing. The challenge is to effectively combine the information from the network structure with rich node and edge attribute data.

## Supervised Random Walks:

This repository is the implementation of Link prediction based on the paper Supervised Random Walks by Lars Backstrom et al. The essence of which is that we combine the information from the network structure with the node and edge level attributes using Supervised Random Walks. We achieve this by using these attributes to guide a random walk on the graph. We formulate a supervised learning task where the goal is to learn a function that assigns strengths to edges in the network such that a random walker is more likely to visit the nodes to which new links will be created in the future. We develop an efficient training algorithm to directly learn the edge strength estimation function.

## Problem Description:

We are given a directed graph *G(V,E)*, a node *s* and a set of candidates to which *s* could create an edge. We label nodes to which *s* creates edges in the future as *destination nodes D = {d1,..,dk}*, while we call the other nodes to which s does not create edges no-link nodes *L = {l1,..,ln}*. We label candidate nodes with a set *C = D union L*. *D* are positive training examples and *L* are negative training examples. We can generalize this to multiple instances of *s, D, L*. Each node and each edge in G is further described with a set of features. We assume that each edge *(u,v)* has a corresponding feature vector psiuv that describes u and v and the interaction attributes.

For each edge (u,v) in G we compute the strength *auv = fw(psiuv)*. Function *fw* parameterized by *w* takes the edge feature vector *psiuv* as input and computes the corresponding edge strength *auv* that models the random walk transition probability. It is exactly the function *fw(psi)* we learn in the training phase of the algorithm.

To predict new edges to *s*, first edge strengths of all edges are calculated using *fw*. Then a random walk with restarts is run from *s*. The stationary distribution *p* of the random walk assigns each node *u* a probability *pu*. Nodes are ordered by *pu* and top ranked nodes are predicted as future destination nodes to *s*. The task is to learn the parameters *w* of function *fw(psiuv)* that assigns each edge a transition probability. One can think of the weights *auv* as edge strengths, and the random walk is more likely to traverse edges of high strength, and thus nodes connected to node *s* via paths of strong edges will likely be visited by the random walk and will thus rank higher.

### The optimization problem:

The training data contains information that source node *s* will create edges to node *d subset D* and not *l subset L*. So we set parameters *w* of the function *fw(psiuv)* so that it will assign edge weights *auv* in such a way that the random walk will be more likely to visit nodes in *D* than *L*, *i.e.,* *pl < pd* for each *d subset D* and *l subset L*. And thus we define the optimization problem as follows.  
![optimization problem hard version](http://i.imgur.com/zMjJ1Nb.png)

where *p* is the vector of pagerank scores. Pagerank scores *pi* depend on edge strength *auv* and thus actually depend on *fw(psiuv)* which is parameterized by *w*. The above equation (1) simply states that we want to find *w* such that the pagerank score of nodes in *D* will be greater than the scores of nodes in *L*. We prefer the shortest *w* parameters simply for the sake of regularization. But the above equation is the “hard” version of the optimization problem. However, it is unlikely that a solution satisfying all the constraints exists. We make the optimization problem “soft” by introducing a loss function that penalizes the violated constraints. Now the optimization problem becomes,  
![optimization problem soft version.](http://i.imgur.com/oZ2pYN1.png)  
where lambda is the regularization parameter that trades off between the complexity (norm of *w*) and the fit of the model (how much the constraints can be violated). And *h(.)* is a loss function that assigns a non-negative penalty according to the difference of the scores *pl\-pd*. *h(.) = 0* if *pl < pd* as the constraint is not violated and *h(.) > 0* if *pl > pd*.

### Solving the optimization problem:

First we need to establish a connection between the parameters *w* and the random walk scores *p*. Then we show how to obtain partial derivatives of the loss function and *p* with respect to *w* and then perform gradient descent to obtain optimal values of *w* and minimize loss. We build a random walk stochastic transition matrix *Q<sup>‘</sup>* from the edge strengths *auv* calculated from *fw(psiuv)*.  
![Q dash](http://i.imgur.com/JiSHf7t.png)

To obtain the final random walk transition probability matrix *Q*, we also incorporate the restart probability *alpha*, *i.e.,* the probability with which the random walk jumps back to seed node *s*, and thus “restarts”.  
![Q](http://i.imgur.com/vE2P7LJ.png)

Each entry *Quv* deﬁnes the conditional probability that a walk will traverse edge (u, v) given that it is currently at node u. The vector *p* is the stationary distribution of the Random Walk with restarts (also known as Personalized Page Rank), and is the solution to the following eigen vector equation.  
![eigen vector equation](http://i.imgur.com/UFwnobA.png)

The above equation establishes the connection between page rank scores *p* and the parameters *w* via the random walk transition probability matrix *Q*. Our goal now is to minimize the soft version of the loss function (eq. 2) with respect to parameter vector *w*. We do this by obtaining the gradient of *F(w)* with respect to *w*, and then performing a gradient based optimization method to find *w* that minimizes *F(w)*. This gets complicated due to the fact that equation 4 is recursive. For this we introduce *deltald = pl\-pd* and then we can write the derivative  
![delta ld](http://i.imgur.com/FhZVZEB.png)  
and then we can write the derivative of *F(w)* as follows  
![lossfunction gradient with delta](http://i.imgur.com/oisE40X.png)  
For commonly used loss functions *h(.)* it is easy to calculate the derivative, but it is not clear how to obtain partial derivatives of *p* wrt *w*. *p* is the principal eigen vector of matrix *Q*. The above eigen vector equation can also be written as follows.  
![eigen vector reduced form.](http://i.imgur.com/z00CXm4.png)  
and taking the derivatives now gives  
![derivative of p recursive form](http://i.imgur.com/FhZVZEB.png)  
Above, *pu* and its partial derivative are entangled in the equation, however we compute the above values iteratively as follows  
![power method to compute p and its partial derivative iteratively.](http://i.imgur.com/WneoOOn.png)  
We initialize the vector *p* as *1/|V|* and all its derivatives as zeroes before the iteration starts, and terminate the recursion when *p* and its derivatives converge for an epsilon, say *10e-12*. To solve equation 4, we need the partial derivative of *Qju*, this calculation is straightforward. When *(j,u) subset E*, the derivative of *Qju* is  
![partial derivative of Qju](http://i.imgur.com/aLDlWP4.png)  
and derivative of *Qju* is zero if edge *(j,u)* is not a subset of *E*.

## My Implementation:

We are given a huge network with existing connections. When predicting a future link of a particular node, we consider that *s*, and the graph *G(E,V)* is Here we explain how each helper function and main function implements the above algorithm.

### FeaturesFromAdjacentMatrix.m:

This is a temporary function specific to the Facebook data that generates Features of each edge from a given adjacency matrix. For other problems this function must be replaced with something that generates a feature vector for each edge based on graph *G(E,V)* and node, edge attributes. For a network with *n* nodes this function returns an *n x n x m* matrix, where *m* is the size of parameter vector *w* (sometimes *m+1*).

-   arguments:
    
    -   Adjacency matrix, node attributes, edge attributes
-   returns:
    
    -   *psi size(nxnxm)*

### FeaturesToEdgeStrength.m:

This function takes the feature matrix (*psi*) and the parameter vector (*w*) as arguments to return edge strength (*A*) and partial derivative of edge strength wrt each parameter (*dA*). We also compute the partial derivative of edge strength to make further calculations easier. We can vary the edge strength function in future implementations, in this we used *sigmod(w x psiuv)* as the edge strength function.

-   arguments:
    
    -   *psi size(nxnxm)*
    -   *w size(1xm)*
-   returns:
    
    -   *A size(nxn)*
    -   *dA size(nxnxm)*

### EdgeStrengthToTransitionProbability.m

This function takes the edge strength matrix *A* and *alpha* to compute the transition probability matrix *Q*.

-   arguments:
    
    -   *A size(nxn)*
    -   *alpha size(1x1)*
-   returns:
    
    -   *Q size(nxn)*

### EdgeStrengthToPartialdiffTransition.m

This function computes the partial derivative of the transition probability matrix from *A*, *dA* and *alpha*.

-   arguments:
    
    -   *A size(nxn)*
    -   *dA size(nxnxm)*
    -   *alpha size(1x1)*
-   returns:
    
    -   *dQ size(nxnxm)*

### LossFunction.m

This function takes as input parameters, adjacency matrix of the network, lambda and alpha. \* We get edge strength matrix and its partial derivatives from features and parameters \* We get transition probability and partial derivatives of it from *A* and *dA* \* We get stationary probabilities from *Q* and *dQ* \* Compute cost and gradient from the above variables, we can use various functions as loss function *h(.)*. Here we used the Wilcoxon loss function.

-   arguments:
    
    -   param: parameters of the edge strength function, size(1,m)
    -   features: features of all the edges in the network, size(n,n,m)
    -   d: binary vector representing destination nodes, size(1,n)
    -   lambda: regularization parameter, size(1,1)
    -   alpha: random restart parameter, size(1,1)
-   returns:
    
    -   J: loss, size(1,1)
    -   grad: gradient of cost wrt parameters, size(1,m)

### fmincg.m

We use this function to do the minimization of the loss function, given a starting point for the parameters, and the function that computes loss and gradients for a given parameter vector. This is similar to the fminunc function available in Octave.

### GetNodesFromParam.m

This function calculates the closest nodes to the root node given the parameters obtained after training.

-   arguments:
    
    -   param: parameters, size(m,1)
    -   features: feature matrix, size(n,n,m)
    -   d: binary vector representing the destination nodes, size(1,n)
    -   alpha: alpha value used in calculation of Q, size(1,1)
    -   y: number of nodes to output
-   returns:
    
    -   nodes: output nodes, size(1,y)
    -   P: probabilities of the nodes, size(1,n)

## How to Train:

Here I will show how to train the supervised random walk for a given root node *s* and edge features matrix *psi*. I’m not showing how to obtain the edge features. Given the network structure, node and edge attributes etc., you can experiment with different feature extraction techniques. Here we have *psi*.

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
