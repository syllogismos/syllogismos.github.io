---
layout: post
title: "Stochastic Gradient Descent in AD."
date: 2014-09-13 19:17:43 +0530
comments: true
categories: 
---

In **stochastic gradient descent**, the true gradient is approximated by gradient at each single example.

![update rule](http://upload.wikimedia.org/math/7/d/9/7d9f6671a202d94d26730ef898d8d4f2.png)

As the algorithm sweeps through the training set, it performs the above update for each training example. Several passes can be made over the training set until the algorithm converges, if this is done, the data can be shuffled for each pass to prevent cycles.

Obviously it is faster than normal gradient descent, cause we don't have to compute  cost function over the entire data set in each iteration in case of stochastic gradinet descent.

## stochasticGradientDescent in AD:
This is my implementation of Stochastic Gradient Descent in AD library, you can get it from [my fork](http://github.com/syllogismos/ad) of AD.

Its type signature is 
```
stochasticGradientDescent :: (Traversable f, Fractional a, Ord a) 
  => (forall s. Reifies s Tape => f (Scalar a) -> f (Reverse s a) -> Reverse s a) 
  -> [f (Scalar a)]
  -> f a 
  -> [f a]
```  

####Its arguments are:  
* ```errorSingle :: (forall s. Reifies s Tape => f (Scalar a) -> f (Reverse s a) -> Reverse s a)``` function, that computes error in a single training sample given ```theta```
* Entire training data, you should be able to map the above ```errorSingle``` function over the training data.
* and initial Theta

## Example:
[Here](https://raw.githubusercontent.com/syllogismos/machine-learning-haskell/master/exampledata.txt) is the sample data I'm running ```stochasticGradientDescent``` on.

Its just 97 rows of samples with two columns, first column is ```y``` and the other is ```x```

Below is our error function, a simple squared loss error function. You can introduce regularization here if you want.
```
errorSingle :: 
  forall a. (Floating a, Mode a) 
  => [Scalar a] 
  -> [a] 
  -> a
errorSingle d0 theta = sqhalf $ costSingle (tail d0) theta - auto ( head d0)
  where
    sqhalf t = (t**2)/2
    
costSingle x' theta' = constant + sum (zipWith (*) coeff autox')
      where
        constant = head theta'
        autox' = map auto x'
        coeff = tail theta'
```
Running Stochastic Gradient Descent:
```
lambda: a <- readFile "exampledata.txt"
lambda: let d = lines a
lambda: let train = map ((read :: String -> [Float]) . (\tmp -> "[" ++ tmp ++ "]")) d
lambda: let sgdRegressor = stochasticGradientDescent errorSingle train

lambda: sgdRegressor [0, 0] !! 96
[0.2981517,1.2027082]
(0.03 secs, 4228764 bytes)

lambda: sgdRegressor [0, 0] !! (97*2 -1)
[0.49144596,1.1814859]
(0.03 secs, 2097796 bytes)

lambda: sgdRegressor [0, 0] !! (97*3 -1)
[0.67614514,1.1605322]
(0.03 secs, 2647504 bytes)

lambda: sgdRegressor [0, 0] !! (97*4 -1)
[0.8526818,1.1405041]
(0.03 secs, 3158452 bytes)

lambda: sgdRegressor [0, 0] !! (97*5 -1)
[1.0214167,1.1213613]
(0.05 secs, 3707068 bytes)
```

## Cross checking with [SGDRegressor](http://scikit-learn.org/stable/modules/generated/sklearn.linear_model.SGDRegressor.html) from scikit-learn
```
> import csv
> import numpy as np
> from sklearn import linear_model

> f = open('exampledata.txt', 'r')
> fcsv = csv.reader(f)

> d = []
> try:
>    while True:
>        d.append(fcsv.next())
> except:
>     pass
> f.close()

> for i in range(len(d)):
>     for j in range(2):
>         d[i][j] = float(d[i][j])

> x = []
> y = []
> for i in range(len(d)):
>     x.append(d[i][1:])
>     y.append(d[i][0])

# initial learning rate eta0 = 0.001
# learning rate is constant
# regularization parameter alpha = 0.0, as we ignored reqularization
# loss function = squared_loss
# n_iter or epoch, how many times does the algorithm pass our training data.
> reg = linear_model.SGDRegressor(alpha=0.0, eta0=0.001, loss='squared_loss',n_iter=1, learning_rate='constant' )
# start training with initial theta of 0, 0
> sgd = reg.fit(x,y, coef_init=[0], intercept_init=[0])
> print [sgd.intercept_, sgd.coef_]
[array([ 0.29815173]), array([ 1.20270826])]
```

The only restriction we have in our implementation of stochasticGradientDescent is that we set the learning rate a default value of 0.001 and is a constant through out the algorithm.

The rest of the things like the sort of regulariztion, regularization parameter, loss function we are using, we can specify in ```errorSingle```.

## Results:
So when ```n_iter = 1```, went through the entire data set once, so we must check ```97th``` theta from our regression result from **AD**.
Similarly ```n_iter = 2``` implies ```97*2``` iteration in our implementation, and etc.,

```
n-iter = 1, i = 96
scikit-learn: [array([ 0.29815173]), array([ 1.20270826])]
AD: [0.2981517,1.2027082]

n-iter = 2, i = 97x2 - 1
scikit-learn: [array([ 0.49144583]), array([ 1.18148583])]  
AD: [0.49144596,1.1814859]

n-iter = 3, i = 97x3 - 1  
scikit-learn: [array([ 0.67614512]), array([ 1.16053217])]  
AD: [0.67614514,1.1605322]

n-iter = 4, i = 97x4 - 1  
scikit-learn: [array([ 0.85268182]), array([ 1.14050415])]  
AD: [0.8526818,1.1405041]

n-iter = 5, i = 97X5 -1  
scikit-learn: [array([ 1.02141669]), array([ 1.12136124])]  
AD: [1.0214167,1.1213613]
```

[Here](http://www.github.com/syllogismos/machine-learning-haskell) in this repository, you can find the ipython notebook and haskell code so that you can test these yourself.

## References:
1. [Stochastic Gradient Descent on wikipedia](http://en.wikipedia.org/wiki/Stochastic_gradient_descent)
2. [SGDRegressor from scikit-learn](http://scikit-learn.org/stable/modules/generated/sklearn.linear_model.SGDRegressor.html)
3. [Gradient Descent vs Stochastic Gradient Descent](http://www.quora.com/Whats-the-difference-between-gradient-descent-and-stochastic-gradient-descent)
4. [Batch Gradient Descent vs Stochastic Gradient Descent](http://metaoptimize.com/qa/questions/10046/batch-gradient-descent-vs-stochastic-gradient-descent)
4. [Batch Gradient Descent vs Stochastic Gradient Descent](http://stats.stackexchange.com/questions/49528/batch-gradient-descent-versus-stochastic-gradient-descent) 