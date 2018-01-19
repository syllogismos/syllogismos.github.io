---
layout: post
title: "Miscellanious Notes"
date: 2017-08-02 13:55:59 +0530
comments: true
categories: 
---
Just a collection of some notes and tips that helps me in my development workflow.


## SSH
* Quit an ssh session using `CR~.` and get to your local terminal. `~` is the escape character for ssh and dot to quit ssh. But note that tilda has to follow new line. When ever your ssh connection gets disconnected for one reason or the other, say you lost internet connection or some other reason, sometimes the screen wont repsond to any keystroke and it seems like its struck in the ssh session. Its very annoying. Instead of closing the terminal, you can do this instead `CR~.`
* Add `ServerAliveInterval 60` to your ssh config file, most probably in `~/.ssh/config`. Usually by default your ssh connection closes if it is idle for a long time, by doing this you are pinging every 60 seconds to keep the connection alive. Very helpful as you don't have to connect to your remote machine again and again.


## Useful command line tools
* s3cmd, interact with your s3 buckets
    1. `pip install s3cmd`
    1. `s3cmd --configure` # configure your keys
    1. `s3cmd ls` # list buckets, contents of a dir
    2. `s3cmd mb s3://new_bucket/` # make new bucket
    3. `s3cmd put --recursive localfiles s3://uri/` # copy local files to s3
    4. `s3cmd get --recursive s3://uri/` # get s3 files to local machine
* jq, parse json files and pretty print on terminal
    1. `brew install jq`
* grep, unix search tool
    1. `grep -A2 query file.txt` # prints 2 lines `After` the queried term
    2. `grep -B2 query file.txt` # prints 2 lines `Before` the queried term
    3. `grep -C2 query file.txt` # prints 2 lines of `Context` on both sides
    4. `grep -e regex file.txt` # searches for the regexp
* sort, sorting text
    1. `sort -nr` # sorts numbers in descending order
* awk, command line programming language?
    1. `cat file.txt | awk '{print $2}'` # prints the second column
    2. it does a lot more things, but this is what i end up using the most for
* watch, executes the given command with the time interval mentioned
    1. `watch -d -n600 "cat train.log | grep EpRewMean | awk '{print \$2,\$1}' | sort -nr | head"`
    2. `n` flag gives the time interval, so in above example every 10 minutes it executes the command to give the best mean reward.
    3. `d` flag highlights the difference between two consecutive runs.
* head tail, head and tail of the files
    1. `tail -1000f file.txt` # last 1000 lines and waits for more lines that are being added to the file
    2. `head -n 25 file.txt` # first 25 lines
* gist, command line gist utility
    1. `brew install gist`
    2. `gist --login` # loging to your github
    3. `gist -p file.txt` # upload private gist
* screen, window manager that multiplexs multiple terminal sessions
    1. `screen -rd` reattach to an existing secreen session even if its open somewhere else
    2. `Ctrl-a d` detach from an existing screen session
    3. `Ctrl-a ?` help menu in screen
    4. `Ctrl-a n` next terminal
    5. `Ctrl-a p` previous terminal
    6. `Ctrl-a k` kill the curernt temrinal in screen


## python
* `python -u python_script.py > python_logs.txt` Usually I want to capture all the print statement logs in some text file, so that I can save them for further reference, instead of throwing them off in stdout. So above all my print logs will be in `python_logs.txt`, and I follow along the logs using `tail -100f python_logs.txt`. And the `-u` flag forces the print statements to be not bufferred while writing them to `python_logs.txt`. Other wise even if your program is running you wont find the logs in the log file as soon as they get executed.

* Start a simple http server to serve static files temporarily. Change directory to the relevant directory and `python -m SimpleHTTPServer 8001`, `8001` is the port number, You can now navigate to `localhost:8001` to browse files.

* Use `%autoreload` while developing your jupyter notebooks and inside ipython, so that it will automatically reload changes of the imported modules and files. You don't have to restart ipython and reimport everything again to see the changes reflected. You have to be careful though, use it only while developing. Type the below two lines in the ipython terminal.

```
In [1]: %load_ext autoreload

In [2]: %autoreload 2

```
* Use `?` to get function signature and function doc string, and `??` to get function source inside ipython terminal and jupyter notebook.

```
In [3]: json.dump?
Signature: json.dump(obj, fp, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, cls=None, indent=None, separators=None, encoding='utf-8', default=None, sort_keys=False, **kw)
Docstring:
Serialize ``obj`` as a JSON formatted stream to ``fp`` (a
``.write()``-supporting file-like object).

If ``skipkeys`` is true then ``dict`` keys that are not basic types
(``str``, ``unicode``, ``int``, ``long``, ``float``, ``bool``, ``None``)
will be skipped instead of raising a ``TypeError``.

In [4]: json.dump??
Signature: json.dump(obj, fp, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, cls=None, indent=None, separators=None, encoding='utf-8', default=None, sort_keys=False, **kw)
Source:
def dump(obj, fp, skipkeys=False, ensure_ascii=True, check_circular=True,
        allow_nan=True, cls=None, indent=None, separators=None,
        encoding='utf-8', default=None, sort_keys=False, **kw):
    """Serialize ``obj`` as a JSON formatted stream to ``fp`` (a
    ``.write()``-supporting file-like object).
```

* Started using `conda` which made python dev much more saner. No more issues with `six` package in OSX while installing a new package, and other common dependency related issues while installing packages.

```
wget https://repo.continuum.io/archive/Anaconda3-5.0.1-MacOSX-x86_64.sh
bash Anaconda3-5.0.1-MacOSX-x86_64.sh
```


## [Bitbar](https://github.com/matryer/bitbar)
A utility that helps you write osx menu bar applications, and also use lots of community built plugins/menu bar applications.

`brew install bitbar`


### Community Plugins:
* [Timezone plugin](https://github.com/matryer/bitbar-plugins/blob/master/Time/worldclock.1s.sh), shows time in 4-5 major timezones.
![Timezone plugin](http://i.imgur.com/OoCfxTn.png)

* [Clipboard plugin](), clipboard of the last 10 items copied, click on an item to copy it back to clipboard.


### My Plugins:
#### EC2 Plugin
My own ec2 bitbar plugin, that makes all my common EC2 tasks one click, and so much easier to do.
![Imgur](http://i.imgur.com/xG7rtCt.png)
![Imgur](http://i.imgur.com/S3YOsfG.png)


1. I can start, stop, restart, teminate my running machines from the menu bar
2. Create a low cpu alarm, that sends me an alert email when the cpu is lower than 20%. This is what I use mostly cause I want to get an alert when my machine learning scripts are die/finish.
3. Delete the above created alarm.
4. Copy ssh command to the clipboard with the right private key file just by a single click. It so annoying everytime I start a machine in ec2, I have to copy the public ip/dns and type where the private key is and type `ubuntu@`. All of this is just single click away now.
5. Displays various machine types, their cores, memory, normal prices, current spot prices in all the regions I'm interested in.
6. Lists all the available AMIs, and launch a spot instance from that AMI

#### KEYS plugin
![Imgur](http://i.imgur.com/zuuGgq4.png)

By clicking on the above words, the respective thing will be copied to clipboard.

Server setup is to setup my vim/github settings to any new server that I start. which basically copies `wget https://github.com/syllogismos/dotfiles/raw/master/server_setup.sh` into clipboard. and `sh server_setup.sh` will update my server vimrc and gitconfig files.

## git
* add this alias in your `~/.gitconfig` under `[alias]`, so that you can do `git hist` that shows pretty tree version of git commit history. This is very useful for my sanity, while rebasing, merging pull requests and etc. This forces me to keep my commit tree sane.
    ```
    hist = log --pretty=format:'%h %ad | %s%d [%an]' --graph --date=short
    ```
![](http://i.imgur.com/iktQDA1.png)
![](http://i.imgur.com/JBTqcyN.png)

## vim
You can find my vimrc [here](https://github.com/syllogismos/dotfiles/blob/master/vim/vimrc.symlink)

My favourite things in default vim are and find myself using them again and again.


* visual block, this is the feature I miss the most when I use any other editor like say vscode or any other. `Ctrl+Shift+v`
* recording, macro recording. `qa` to start recording your operations in the `a` register, and end the recording by typing `q` again. And repeat those operations by doing `@a`. I did `qa` for clarity of whats happening, but for speediness, I do `qq` to record in `q` register. And then end recording with `q`. And repeat with `@q`. You can also use `@@` to just repeat the previous macro operation.
* `.` a simple dot. it just repeats previous insert operation. Its so valuable and it surprises several times. Especially while programming, where things often repeat.


Most used `vimrc` settings.


* `set number` line number
* `set relativenumber` shows lines numbers relative to the current line
* `set scrolloff=3` while scrolling all the way down or all the way up it gives you 3 lines of context instead of the default. It starts scrolling when you reach the last 3 lines instead of the bottom.
* `inoremap jk <esc>` and `inoremap kj <esc> ` escape key is soo far away.. and I just type `jk` or `kj` quickly to get to normal mode from insert mode.
* `inoremap ,,  <C-p>` intellisense of sorts by doing `,,` quick completions but only works for the words that already came earlier.
* `noremap <Space> :w<Esc>` space bar to save the file in normal mode
* `noremap  <buffer> <silent> k gk` and `noremap  <buffer> <silent> j gj` when lines are wrapped around the width and a single line takes up more than one line, normally you have to type `gk` to go down but its annoying so binding `k` to `gk` makes things easier.

Sample video with various vim commands that I use often. like macros, visual block and etc.
<iframe width="560" height="315" src="https://www.youtube.com/embed/ZZEcg4pNF-I" frameborder="0" allowfullscreen></iframe>