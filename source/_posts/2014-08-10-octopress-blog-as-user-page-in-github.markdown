---
layout: post
title: "Octopress blog as User Page in Github, using Windows"
date: 2014-08-10 16:15:42 +0530
comments: true
categories: 
---
Step by step instructions to install Octopress blog on Windows to setup your github use page.

- Download RubyInstaller and ruby dev kit from [here](http://dl.bintray.com/oneclick/rubyinstaller/rubyinstaller-1.9.3-p545.exe?direct) and [here](https://github.com/downloads/oneclick/rubyinstaller/DevKit-tdm-32-4.5.2-20111229-1559-sfx.exe)
- The above installer installs Ruby 1.9.3, eventhough the most recent stable version > 2.0.0
- Go to the directory where the dev-kit is installed and do the following
```
> cd ruby-dev-kit
> ruby dk.rb init
> ruby dk.rb install
```
- Setup Octopress, change to the directory where you want your blog to reside
```
> git clone git://github.com/imathis/octopress.git octopress
> cd octopress
```
- Install dependencies
```
> gem install bundler
> bundle install
```
- Install default Octopress theme.
```
> rake install
```
- Configure your blog by updating _config.yml, name of your blog, your name and things like that.
- Create a new repo of the form YOUR-GITHUB-USER-NAME.github.io in github
```
> rake setup_github_pages
# this command will ask your for your github pages url, so type 
https://github.com/YOUR-GITHUB-USER-NAME/YOUR-GITHUB-USER-NAME.github.io
```
- and run the following commands to deploy your local blog to github
```
> rake generate
> rake deploy
# what this does is basically makes the master branch of your github repo contain all the generated
# files namely _deploy folder in your directory.
```
- If everything worked fine, you will be able to see your blog with the defalt octopress template on YOUR-GITHUB-USER-NAME.github.io
- Every time you update your blog you need ro do *rake generate* and *rake deploy* these commands will push your changes to your master branch on the remote
- You can make a new post using *rake new_post* command
```
> rake new_post["My first Blog Post"]
```
- The above command creates a new markdown file in source/_posts folder, write your blog in markdown
- Commit the changes you made locally in your local branch *source*
```
> git status
# this will show that there are changes in the folder source/_posts
> git add .
> git commit -m "my first blog post"
```
- If you want can create a new branch called *source* in your remote repository for the source files
```
> git push origin source
```
     

## This is what you do everytime you create a new post
```
> rake new_post["new blog post"]
> rake generate
> rake deploy # to deploy static files in the remote master branch.
> git add . # or you can specify the markdown file
> git commit -m "new blog post"
> git push origin source # to push the source files to the source branch
```

     
I only did this because my newly minted blog doesn't contain many entries :D