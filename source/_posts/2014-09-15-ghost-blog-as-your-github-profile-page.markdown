---
layout: post
title: "Ghost blog as your Github User Page"
date: 2014-09-15 19:54:00 +0530
comments: true
categories: 
---

Ghost is a minimalistic blogging platform that is very easy to setup. You can use it as your github user page using a tool called [buster](https://github.com/axitkhurana/buster)

My current github pages are setup using Octopress, both ghost and octopress has its advantages and disadvantages. Every time I'm making a new post using octopress, I have to go to some online markdown editor to write my post. Where as Ghost has its inbuilt markdown editor where you can preview your changes as you type. That can be a little annoying. Even though my current setup still uses octopress, I am editing this markdown using Ghost. One disadvantage of ghost is that it stores all the my blog posts in a local sqlite db, where as in octopress, I can see my markdown files and edit and commit changes to the main repository.

## 3 Steps
* Setup Ghost Blog
* Generate Static Content using [Buster](https://github.com/axitkhurana/buster)
* Gotchas.

### Setting up Ghost
* Download ghost from [here.](https://ghost.org/download/)
* Install npm dependencies.
* npm start to run it on your local machine port 2368.
* Click [here](http://localhost:2368/ghost) to register a new user and start posting new blog posts.
* If you want, you can download additional themes into /content/themes folder and change the theme in your [ghost settings.](http://localhost:2368/ghost/settings)
```
> npm install
> npm start
```

### Generating Static Pages from your ghost blog using [Buster.](https://github.com/axitkhurana/buster)
* You need wget for buster python package to work.
* Download and install wget and its dependencies from [here.](http://gnuwin32.sourceforge.net/packages/wget.htm)
* Install *libintl-2*, *libiconv-2*, *openssl* along with *wget* as given in the end of the wget download page.
* You can install **buster** using pip, and can use *buster* directly from the command line, but you are likely to face problems if you are using Windows. Instead you can just clone the buster repo and use the **buster.py** directly.
```
> pip install buster
> buster setup --gh-repo=<repo-url>
> buster generate --domain=http://localhost:2368
```

#### or
```
> git clone http://github.com/axitkhurana/buster
> cd buster
> python buster/buster.py setup --gh-repo=<repo-url>
> python buster/buster.py generate --domain=http://localhost:2386
```
* ***setup*** argumet will ask you for the github repo of your userpage and creates a directory named **static**
* ***generate*** argument will recursively download all the static files of a given url into **static** folder.
* ***preview*** argument will start a simple python webserver and hosts the static files in your **static** folder on your localmachine port 9000, so that you can preview the static files genereated by your previous command.
* ***deploy*** will push changes to your github repository

### Gotchas
* **wget** has some problems downloading a webpage using **generate** command because of \\\ slashes so remove those according to this [commit.](https://github.com/syllogismos/buster/commit/ba2c8df24b78361699e767891f14ed63d775ec21#diff-a61cc6042865036a60870334dd92047cL39)
* When previewing the static site generated, **.css** and **.js** using pythons SimpleHttpServer, the MIME type is changed to **application/octet-stream**. In order to fix this we have an additional class named **ExtHandler** that extends *SimpleHttpRequestHandler* to change the default *get_type()* behaviour.
* This [commit](https://github.com/syllogismos/buster/commit/ba2c8df24b78361699e767891f14ed63d775ec21#diff-a61cc6042865036a60870334dd92047cL39) has both of the above changes. 
* If you are on windows, I recommend cloning [this fork](http://github.com/syllogismos/buster) of buster instead of the original, that has both of the above fixes.
* Some static files aren't downloaded using the **generate** command, my understanding is that the static files that are requested from javascript or fonts requested using css aren't generated. You are better of copying the static files and images that aren't in your static folder directly.

### Summary
```
## download ghost
> cd ghost
> npm install
> npm start
## ghost blog is in http://localhost:2368
## admin/settings in http://localhost:2368/ghost

## change to another directory where you want your generated static website to reside
> git clone https://github.com/syllogismos/buster
> cd buster

> python buster/buster.py setup
## give your github page repository, it creates a static dir

> python buster/buster.py generate --domain=http://localhost:2368
## downloads all the static files into your static dir

> python buster/buster.py preview
## to see your downloaded static files are proper
## If you see any of the static files missing, say fonts or images, just copy them from your ghost directory
## make sure your generated static files look okay

> python buster/buster.py deploy # to commit your changes to the github repo
```

Thank you.