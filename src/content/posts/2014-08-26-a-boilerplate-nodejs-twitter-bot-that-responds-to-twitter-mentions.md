---
title: "A Boilerplate Nodejs Twitter Bot That Responds to Twitter Mentions."
date: 2014-08-26T23:20:56+05:30
---

Start by forking this [GitHub repo](https://github.com/syllogismos/twitter-bot-template).

## Config:

Make a copy of config.template.json named config.json, and fill in the secret keys of your Twitter bot that you obtain from [here](https://apps.twitter.com), and make sure your Twitter app has both read and write access in the “permissions” tab.

## Installation

Install all the node dependencies.

```
> npm install
```

## Your bot code.

The bot is written in coffeescript, and the compiled javascript is also provided in case if you prefer that.

At the least you need to fill the function **solve** whose only argument is the tweet text, including all the mentions. Not the Tweet Object, it’s just the tweet text.

You are also provided with a function **isOfWrongFormat** that defaults to *false* which checks the validity of the tweet text. And its only argument is the tweet text as well. Not the tweet object.

## Running the bot.

If you wrote the bot in coffee-script do this

```
> coffee twitterBot.coffee
```

Or if you wrote it in plain javascript do this

```
> node twitterBot.js
```

If you want to compile your coffee-script to plain javascript you can run the coffee command with a *\-c* flag

```
> coffee -c twitterBot.coffee
```

## Sample Bot

You can find a sample Twitter bot that I wrote based on this, albeit slightly modified, at [countdownbot](https://github.com/syllogismos/countdownbot).

It responds with a solution of the **numbers game** from the game show **Countdown**, if someone mentions the bot along with the target number and the rest of the numbers.

After you fill the config in the countdownbot as shown above, and run it, anyone mentioning your bot along with a set of numbers, with the first one being the target number

@someRandomPerson: @countdownbot 347 2 3 10 75 23 12

it responds like this.

@countdownbot: @someRandomPerson One possible solution for 347 is: (10\*(12+23))-3
