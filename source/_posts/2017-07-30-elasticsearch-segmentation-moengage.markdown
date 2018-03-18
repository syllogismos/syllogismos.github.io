---
layout: post
title: "Elasticsearch, Segmentation, MoEngage"
date: 2017-07-30 12:11:45 +0530
comments: true
categories: 
---

For almost two years I worked at a company called [MoEngage](https://moengage.com/), which is a marketing automation b2b company for app developers. We handle push messages, inapp messages for both mobile phone apps and web apps, email campaigns etc,. I was one of the early employees and I worked on **Segmentation** and built it from ground up. The early days were probably my favourite days, everyone worked with so much intensity at a very fast pace with no scope for any distractions. Very productive and rewarding work. My work touched almost all aspects of the product and the entire tech stack we were using. I mainly want this to be a tech blog post about the implementation of **segmentation** using **elasticsearch** but also share some learning experiences being part of a rapidly growing budding young startup., and I regret so much not writing this earlier, now that it's been a while me quitting that job, I definitely wont be able to be as comprehensive as I would like it to be. I was very comfortable with the elasticsearch, celery workers, redis, s3, sqs, aws, python, release process, testing at scale etc., I faced and solved very interesting and unique challenges specific to our use case. Please forgive me for any grammatical or spelling mistakes. I postponed this post for the single reason of wanting to do it perfectly, but the exact opposite is happening. Now I just can't wait anymore to get this out.

# Problem statement and context.
As I said, briefly Moengage is a marketing automation solution for apps, using moengage, apps can send push messages to users of an app and target a very specific  segment of users and reduce churn. At that point of time the mvp of moengage is that we can target users very specifically based on their behaviour inside the app or their own characteristics like their age/sex/location and other attributes. But none of that is built yet. And the few clients that were using us were just bulk messaging(*spamming*) all the users with the same push message. Just get a cursor on the user database, iterate through them all and send each user to the push worker and finally send the push messages. Turns out even this is hard for apps to do, they would rather use some 3rd party to do handle the push infrastructure and they just have a nice dashboard where their marking folk can put in what push message to send, like offers, deals and other stuff.

We provide sdk to the app developers where we give them two main end points. The sdk does a lot more than this, but for this blog post the only endpoints that we are concernen with are the below two

* One is to track **Users**. This endpoint can send stuff like name, location, city, sex, age, email. Everything that can be considered as a feature of the user. We call these features ***User attributes***

* And another is to track what the user is doing inside the app we call these **Events**. And all the features these events might have are called ***Event attributes***. Say for example an app developer might want to track every time a user adds something in the cart. So the event will be something like **Product added to Cart** with event attributes such as *name*, *price*, *discount*, *product_category* and etc.

So now we have all the the available data that we track we can use to target users.

And I was tasked to create a service that basically returns a list of users based on a **segment** that is defined by a marketer or anyone else that has access to the moenagege dashboard. This particular service can be used by lot of other services to do other things, like push message workers will consume the users returned by this **segmentation** service to send push messages, or an email worker to send emails, or this same service can be used to create analytic dashboards to show how a given segment is varying with time, Or a smart trigger worker(smart triggers are basically some sort of interactive push message, as in there will be some trigger defined and if a user triggers it he will get a push message. Say a user adding some product to cart but not purchasing in the next 10 mins might trigger a push message, that guy probably deserved a push message XD). All these different services uses the segmentation service one way or the other. Some sample *segments* might look like as follows. A *segment* can just be all the users of the app, or all the users except the users from another segment.

![Segment 1](http://i.imgur.com/K6NyFX4.png)
![Segment 2](http://i.imgur.com/KqoKfgZ.png)
![Segmentation Dashboard](http://i.imgur.com/NNf0upN.png)

# Segmentation
## Definitions

Just remember this blindly, the output of any **segmentation** is always a set of unique userids/users.

As shown in the above picture. A **segment** consists one or more **filters**. And there are three kinds of filters.
* User segmentation filter(get all users whose *city* attribute is *London*)
* Event/datapoint segmentation filter(get all users who did *product purchased*)
* All Users(just all the users)

Sometimes a filter can be of type **has not executed** where you get a compute a filter and then subtract from **all users**
And the segment can be **OR** of all these filters or an **AND** of all these filters.

In one of the hackathons I built a nested **AND** or **OR** combinations of filters. To enable much more complex segments.

Its so surprising what sorts of use cases the customer success team used to bring to my attention, and ask me how to do this that. Every time they   have some edge case I had to fit that request with the existing dashboard and some basic set theory. Given all that, the dashboard shown above used to cover most cases. There are some cases where a single segment contained more than 30 filters. The main challenge comes because of the disconnect where the guy who tracks the types of events(mobile app developer using sdk from app) and the person who ends up creating push campaigns (marketer who uses moengage dashboard) are from completely two different departments. And the sdk guy tracks all sorts of trivial nonsense and try to be comprehensive and the marketer has to somehow make use of the data that was being tracked and create meaningful push campaigns. I had to simultaneously handle both of their use cases and this created some unique challenges.

## Initial state when I joined
When I first joined the most of the working segmentation part is just the **All Users** segment and a little bit of **User segmentation**. The first part is basically get a cursor on the User db and iterate till we get all the user ids and return it. In the initial days, the biggest user db is less than 10million. And it takes some 3-4 mins to return all the users. And second part is a little bit of user segmentation. Where its a straight forward query, but the main problem here is all user attributes need to be indexed, which is not reasonable to expect a mongo database to do. Not just that, the user attributes are not fixed, our clients are free to introduce what ever they want. Then again you can put all the attributes in a single dict object and index that one particular field. This is actually possible in mongo. But the performance is not really that great. And datapoints/event segmentation is basically going to be an aggregation query on the 'userid' field with the given parameters. This is also implemented on mongo, but it wont work for any big aggregation queries on mongo. The schema of a user object and a data point object will give you some clarity of the ideas I just described and what I'm going to do in the rest of the article.

Sample User Object:
```
{ 
    id: userId,
    name: John Wick,
    city: London,
    phone: 911,
    last_seen: "2017-08-02 11:48:38.509285",
    location: "40.748059, -33.312945",
    age: 31,
    sex: male,
    sessions: 32,
    status: active,
    pushToken: "asdfasAs98787Dfasd",
    os: ANDROID
}
```
Sample Datapoint Object:
```
{
    id: ObjectId,
    userId: userId,
    event: "Added To Cart",
    product_name: "iPhone 64GB",
    price: 500,
    color: "Red",
    platform: "ANDROID"
}
```
The output of a **segmentation** query is always a list of userIds, so from the above sample objects its clear that, if its a user filter, the query on database is straight forward query, and if its a datapoint filter, the query on the database is an aggregation query.

So the initial implementation of datapoint filters is also on mongo, where the event attributes are also not fixed. So the query on mongo is a normal filter and then a aggregation on userIds. Just the normal filter query will kill mongo servers if the datapoints are too many. And that will be the case normally.

All these filters will be queried separately and the resultant of user ids are unioned or intersected using python set operations. This is basically limited by the memory of the segmentation worker.

Clearly all these are major scaling problems and the initial clients we had are very few in the early days of the company, and even then datapoint filters are not working.


## Initial Research
I cant find all the references right now, but my initial research(which was some 2 years back) was pointing towards some sort of search engine database. I knew by then we need to look into Elasticsearch and Apache Solr. And I came across an open source project called [Snowplow](https://github.com/snowplow/snowplow) which is basically "Enterprise-strength web, mobile and event analytics, powered by Hadoop, Kafka, Kinesis, Redshift and Elasticsearch". Sounded almost like what we wanted. Although we are not an analytics company. This played a major role in going ahead with Elasticsearch. I also had to decide between Apache Solr and Elasticsearch, but went ahead with ES given its slightly new, active and most of the comparison articles had lots of nice things to say about how its easier to manage the distributed aspects of ES than it is with Apache Solr.

## [Elasticsearch](https://www.elastic.co/products/elasticsearch)
From the elasticsearch website, "Elasticsearch is a distributed, JSON-based search and analytics engine designed for horizontal scalability, maximum reliability, and easy management."

Elasticsearch is built upon apache Lucene, just like Apache Solr, and added a nice layer that takes care of the distributed aspect of the horizontal scalability. Also provides a nice REST api to handle all sorts of operations like cluster management, node/cluster monitoring, CRUD operations etc.

In elasticsearch, by default every field(column) in the json object is indexed and can be searched, unlike usual databases like mongo, mysql and etc, you explicitly specify what fields to not be indexed. In traditional databases you specify what fields to be indexed. And it is horizontally scalable, you can add machines dynamically to the cluster as your data gets larger and when the master node discovers the newly added node, the master node will distribute all the data shards taking into consideration the newly added node.

It can be started on your local machine as a single node cluster or can be on hundreds of nodes.

## Basics of Elasticsearch.

Lets start with a basic search object and go all the way up to the elasticsearch cluster and make ourself comfortable with all the ES specific terms that come up on our way.

An elasticseach cluster can be visualised in the image below.
![Imgur](http://i.imgur.com/VAAVpeH.png)

Say for example in our case, take the event/datapoint json object that has to be searched for **segmentation** is
```
{
    id: ObjectId,
    userId: userId,
    event: "Added To Cart",
    product_name: "iPhone 64GB",
    price: 500,
    color: "Red",
    platform: "ANDROID"
}
```

The above datapoint belongs to a given **type** of an **index**. For all practical purposes you can ignore **type**, I never really made use of it, I did define that a datapoint object is of **type** datapoint and that's it. And a datapoint resides in one of the **shards**. It can be either a primary shard or a replication/secondary shard. All these primary and secondary **shards** combine to make up one **index**. All these shards are distributed over the **cluster**. A **cluster** can be a single machine or a bunch of **nodes**. 

For example in the picture below, **books** is the name of the **index**. And while creating this **index** we defined it to have to have 3 shards and replicated twice. So there are a total of 6 shards, 3 primary(whiter green) shards and 3(dark green) secondary shards. Our datapoint object can be in any of those shards. All these shards are distributed over three elasticsearch **nodes**. And all these three nodes make up the **cluster**. The node with bolded star is the master node. It coordinates all the nodes to be in sync, When you do a search query, it decides based on the metadata it has which shards in what nodes to be queried.

I'm writing this blogpost to explain how I made use of elasticsearch and fit it to our needs of segmentation. In further parts of the blog, I will be going in detail about es specific things as we go come across them.

![Imgur](http://i.imgur.com/cYJqT4j.png)


## Installation:
Elasticsearch needs java to be installed. In the below gist you can see how to install elasticsearch. And start it as service so that it starts as soon as the machine starts. It also shows you how to install various elasticsearch plugins like **kopf**, **bigdesk**, **ec2 discover** plugin.

* **kopf** that gives us a glimpse of the elasticsearch cluster, above screenshots
* **bigdesk** similar cluster state plugin
* **ec2** plugin that helps the discovery of the nodes in a cluster in a ec2, you can set discovery based on tags, security groups and other ec2 parameters. In the config file you can see the node discovery settings.

After installation of elasticsearch as a linux service, you can find the config file at `/etc/elasticsearch/elasticsearch.yml` where you define the name of the node, cluster, ec2 discovery settings. And restart the service as shown. Ideally for a elasticsearch node that is in production you should reserve half of the available memory for jvm heap. You can find the settings for this `/etc/default/elasticsearch`. And you can find the log files in `/var/log/elasticsearch/`. You will find slowlogs, cluster/node startup logs and etc here.

<script src="https://gist.github.com/syllogismos/6ca5c5ac3e89bfd314f0.js"></script>

Okay this is a brief explanation of what ES is, and how to install. Lets dive into more details about how ES fits into the problem we were trying to solve in the first place. I haven't given more details of Elasticsearch, I will explain new concepts related to ES as we come across by implementing **segmentation**.

## Segmentation Challenges.
The immediate major challenge we had was, the data point segmentation. In the initial days the biggest datapoint db has around 60 million objects. On mongo the datapoint queries/aggregations are just not working. And our first clients were just using basic user segmentation and **All users** segmentation.

Even with just 60 million objects the data point segmentation looked like a very hard problem then. After switching to elasticsearch and after a year I was able to support segmentation on 10 billion datapoint objects. We ended up having two elasticsearch clusters with ~20 nodes(32GB memory) in each just for datapoints. Things that weren't working started working, and at a scale of 166x after one year. The ride wasn't smooth, many sleepless nights, stress, hence many lessons learned along the way.

After **datapoint segmentation** was live for few days we moved the **user segmentation** also to elasticsearch. As having indexes on all the fields a user object on mongo is starting to stress our mongo db servers.

And as we got more clients, we were tracking almost 1/5th of Indian mobile users. And getting **All users** directly from cursor and iterating all the users every time there is an all users request is not feasible anymore. As a db with 30 Million user objects is taking some 10 mins just to get the user ids present in the database. I also had to come up with reliable fast solution for this.

In further segments, we will discuss, each of the above three segmentation/filters use cases.

* Datapoint segmentation filter
* User segmentation filter
* All Users.

## Datapoint/Event Segmentation Filter:
Once again, the schema of the datapoint looks like this.
```
{
    id: ObjectId,
    userId: userId,
    event: "Added To Cart",
    product_name: "iPhone 64GB",
    product_category: "Electronics",
    price: 500,
    color: "Red",
    platform: "ANDROID"
}
```
Above datapoint the event being tracked is `Added To Cart` of user `userId` and with rest of them as event attributes like `price`, `colour`, `platform`, `product_name`.
A single app can track any number of such events, and each event will have any number of attributes, of all major datatypes, `location`, `int`, `string`. We call these event attributes.

Once again reiterating, the output of a segmentation query is a list of users.

Sample Event filters might look like this.

* Get all the users who did 
    1. the event `Added to Cart`,
    2. exactly `3 times`, 
    3. with event attribute `Product Category` is `Electronics`
    4. in the last `7 days`.
* Get all the users who did
    1. the event `Song Played`,
    2. at least `3 times`,
    3. with event attribute `Song Genre` contains `Pop`
    4. with event attribute `Song Year` is equal to `2017`
    5. in the last `1 day`

As you can see a event filter will always be an exact match on the `event`, the event attribute can be of type, `int`, or `string` or `datetime` or `location`. We also provide a condition of how many times a user did this particular event with the above event filters in the last `n days`.

Any event filter have these 4 parts.
1. What event you are interested in. eg `Added to Cart`
2. Event attribute conditions, 
    * if event attribute is string, conditions like `is`, `contains`, `starts with`, and etc
    * event attribute is int, conditions like `equal to`, `greater than`, `less than`
3. Date condition `in the last n days` that specifies, how long in the past are you interested in. As a business decision we only support segmentation on the last 90 days of the data. Any data older than that will be deleted. Every day. As it doesn't make any sense to send push messages based on the user behaviour based on 90 days/3 months old data.
4. And we also support an extra condition based on how many times a given user did the above event with above event attribute conditions. Like say for the event `Logged In` you get get all the users who logged in `exactly 3 times` or `at least 3 times` or `at most 3 times`

The earlier mongo implementation, all the events are stored in a single mongo `db` called `datapoints`. From the few amount of clients we had in the beginning, it is clear that the `events` people tracked are vastly different just based on the volume. Some events like `opened main page` will be in 10s of millions every day. And `product purchased` event would just be in thousands. And `product purchased` event might be of more interest when it came to segmentation queries. As users who did that event are much more important. So the volume of a given event and the significance of that event are both completely unrelated. An event of low volume might be of very high importance. And not just that, the developers might track every little interaction of the users. But the marketing folk might only be interested in 3-10 events.

Two major challenges.
1. Same app might track two different events that vary in volume, some events can be in 10's of millions while other events are just in 1000s
2. Even though an app might track 100s of events, there are only 3-10 events that the marketers are interested in.

So the first major diversion from the mongo implementation is having a separate db(index in elasticsearch terms) for each event, as search performance on one event shouldn't be dependent on all the rest of the events.

So all the `Added to Cart` events of app `Amazon` would be in the elasticsearch index `amazon-addedtocart`. This is the first major decision that we struck with for a long time, even though the two major challenges are not completely solved. It made things a lot easier. In the initial version of Elasticsearch implementation, we decided on having 2 shards per index, no matter the volume of the index. There is a concept of `index aliasing` in elasticsearch that helps in dealing with very high volume events. In elasticsearch the name of the index cant be changed once it is created, so are the number of shards. Index aliasing helps us with having more than one name/alias to query an index. A single elasticsearch index can have more than one alias. And more than one index can all have the same alias. So that when we query using an alias, all the indexes with that alias will be queried. But when you are inserting a object into an index, using an alias, that alias must point to only one index. So a `read alias` that you can use to query filters can point to more than one index. And a `write alias` must point to only one index for write operations to be successful. This concept of index aliasing helps us in dealing with really large indexes. As the number of shards per index is fixed after an index is created using aliasing you can direct new documents of a really big index to another document using `write alias` while searches point to both the old index and the new index.

In elasticsearch by default the all the fields are indexed, there is an extra field called `_all` that considers the entire document as a single field. Indexing happens according to the type of `analyser` you select. Our segmentation queries don't really require the default analyser that is provided. The analyser defines how the fields are tokenised and etc. So I had to disable analysis, so that the fields are considered as they are provided.

All the settings of number of shards, index aliases, and analysis settings for string fields are set using `index templates`. An index template can be used to set all types of settings based on the name of the index while it is being created. A sample index template might look like this.

<script src="https://gist.github.com/syllogismos/824b069b4df415c3f2c3.js"></script>
Using the above template we are doing
1. making default no of shards as 1 per index
2. creating an alias to all indexes, just by appending `-alias` to the end. So the index `amazon-addedtocart` can also be queried using `amazon-addedtocart-alias`. In the earlier implementation I didn't use aliases to the full potential, but I knew aliases will save by bum so I put an alias to every index that is created as above and it did help me to deal with very big indexes.
3. disable indexing `_all` filed, which we don't really use in segmentation.
4. change the default analyser to no analysis on all the string fields.


With the above template settings, I started a cluster with 4 nodes, each of 16GB memory, and out of the 4, 3 master eligible nodes. And started porting event data from mongo to elasticsearch using a open source tool called elaster. If I remember correctly, when we first moved to elasticsearch I was porting 60Million documents. On the other hand we were writing live tracking data from webworkers into elasticsearch.

### Query Language:

### Stats and miscellaneous notes:
* Using this architecture, I scaled the segmentation service from initial 60 million objects to almost 10-20Billion datapoints.
* From mongo to initial 4 nodes of 16Gb cluster to a total of ~40-45 nodes of 32 Gb memory.
* Total number of shards around ~20k
* There is a concept of snapshots in elasticsearch, Along with this we also had a script that takes nightly backups of data and dumps it in S3. We also collect backups of the raw http api requests in s3, that goes in from kafka. But more backups never hurt anybody.
* And we only supported 90 days of tracking data, so we had to delete data older than 90 days everyday. With data deletion also, there is a concept of `segments` on elasticsearch. Where objects reside on these segments. And when you delete an object it is just marked as delete and only when all the documents on a segment are deleted will they go away permanently. Luckily for us we delete data date wise, and the sharding also happens based on date of creation. Although all the documents deleted might not have gone as soon as they were deleted, they eventually permanently deleted.
### Issues:

* Type issues: One major problem we faced is, in elasticsearch once the type of a field is set to `int`, and if you are trying to insert any new document with that field containing a `string` it wont be inserted. This is a really huge gotcha, and if I was not careful I would be losing lots of event data. We always have to be so nice to the `users` no matter how dumb they seem to be, we just have to think of all the ways the services we are providing can be abused or misused. Say for example `cost` event attribute initially they are sending integers. And later on decided they send the same thing by prepending a string `$`. All the new datapoints will be rejected. And there are some event attributes that exist in all datapoints. If by mistake they get mistyped when the index created, every datapoint that comes next will get rejected. To deal with this, using index templates, I set the type of the known fields beforehand. To deal with this,I put the datapoints that failed to be inserted into es because of type issues, in a mongo, and the entire json object as one string in `error-amazon`(in this example) index in the same cluster. Usually these type errors luckily for us are caused in test apps, while people are testing the integrating. So I used to deal with these errors case by case basis. I had scripts ready that clean up the data and fix type errors and reindex in the proper event index. But in later versions of the segmentation we came up with a really nice solution that permanently solves this.

* So from the above architecture, it is clear that there will be a separate index, for every new event the client starts to track. We are providing a single endpoint through the sdk, and the user might accidentally pass a variable in the event name field, like say the `user id`. With us not providing any limit on the number of the events they can track. This will end up creating tens of thousands of indexes, which will just bottle neck the entire cluster And it will become a disaster. And there are cases where some of our clients passed `user id` as the name of the event. I had to go modify the workers code and do a release at some ungodly hour to fix this.

* When an index gets too big, bigger than the heap size of the node that particular shard is residing on. I had make use of the index aliasing operation to write to a newer index while searching on both the old and new indexes. This is also one of the major problems, I faced, and directly affected the stability of the cluster. In later versions of the segmentation, using the aliases, we automated whatever I was doing manually. And I will talk about these changes in later section.


## User Segmentation filter:
Eventually as we were getting more clients, doing the user segmentation filter queries on mongo db was also proving to be challenging. As we are querying on user db, the queries that hit the db are just normal filter queries. Apply all the filters and get a cursor, iterate through the cursor and return the list of users of a given segment. As with data point segmentation, we support all types to filter on the user db, `int`, `string`, `date`, `location`.

For mongo queries to work for user segmentation on all the user attributes that the app is tracking, we have a nested object that holds all the user attributes, and a single index on the the nested field. And as the user attributes are not fixed, and our clients can introduce anything they want to track. Having index such that queries work efficiently on all these fields is becoming challenging as the user dbs are getting bigger.

So eventually we wanted to move user segmentation also to elasticsearch. But the tricky part here is, that user objects receive updates on it, unlike datapoints. Such as, last seen of the user keeps updating every time the user uses it. Location of the user updates. This is fundamentally different from datapoints db. And the challenge now is if we should completely move away from mongo and switch to elasticsearch. But mongo infrastructure was heavily used by the push team to send push notifications once they are given the user ids. And we had to have mongo as the primary data source. And have elasticsearch that mirrors the data on mongo. We can't just write once and keep quite about it, we have to constantly update the elasticsearch data with new updates on user objects.

### River Hell:
Above challenge brings us to a concept called `Rivers`, which exists to solve exactly this problem. The basic concept of rivers is that you have a primary db, some where like a mongodb/couchdb and etc. And you keep tailing all the CRUD operations that happen on the db and replay all those operations on elasticsearch. The river backend was provided by the elasticsearch backend in those days. And there exist several third party drivers that latch on to the CRUD operations that happen on the primary sources, like mongo/couchdb and etc.

Conceptually `Rivers` are what we needed. And I started the user elasticsearch cluster with some 6 nodes that serve user segmentation queries and started the rivers on all the bigger production clients. Things seemed to work well. Except RIVERS ARE UTTER CRAP AND VERY UNRELIABLE, and no wonder they were deprecated by elasticsearch guys as well.

They used to run fine, but after few days, the nodes used to max out on the jvm or memory and the entire user segmentation elasticsearch cluster used to not respond. I have to restart the questionable nodes, and after restarting the nodes, because of the replication shards, the user db indexes were back, but the individual river stopped and CRUD updates on the primary db stopped reflecting on the elasticsearch. So basically the user data on elasticsearch was stale. So I have to delete the index, restart the river from the beginning, and while this restarting is happening, I had to redirect the segmentation queries on to mongo db for backup. It was a mess. Rivers turned out to be such a pain to work with, it almost became a running joke in the entire office. I built a crude river dashboard that shows the status of the rivers and the difference in the number of users in elasticsearch index and the mongo db, this difference usually was a good indicator of the rivers status. And alerts that alert me when a river stops updating new users. Rivers are the most unreliable thing I had to use, and there is a good reason why it got deprecated.

### River Alternative:
I was already looking at alternatives for rivers, and I know that things like [mongo connector](https://github.com/mongodb-labs/mongo-connector) exist. But the question is how reliable that thing will be. But we got to know it was working well for similar use case from a asking around. Mongo already has a way of latching onto and tailing all the crud operations(oplog) and replaying all that. That is how the secondary dbs also replicate their data from the primary mongo nodes. And it is fairly robust. And the mongo connector provides us a way to make use of this replication and index into elasticsearch. Basically we are indexing stuff to elasticsearch(which it is supposed to be good at) and that stuff is basically obtained from oplog of the mongodb which is also fairly robustly implemented. So using mongo connector we are making use of things in which both mongo and elasticsearch are good at in their respective tasks.

By now I had a proper team mate and I made him fork mongo connector and replicate all the river functionality that we were using earlier and made the switch from rivers to mongo-connector.

### Stats:
I think by then we were supporting user segmentation on around 80-100Million users. And after moving away from rivers and started using mongo connector, we were very comfortable with user segmentation. 100Million objects in user cluster seemed like nothing when compared to the datapoint cluster with almost 100x volume and aggregation queries. The only tricky part is not letting the data become too stale, and keep it up to date with mongo.

## All Users:
All users filter is basically returning userids of a given app. The naive implementation is that getting a cursor with empty filter and then iterating it through each and every userid and returning them. But as the user db's got bigger and bigger this process took more and more time. `All users` query is fired not just when sending push campaign to all users. We also need it when we want a datapoint segment that goes like `All users who did not do this action in the last n days`. We do the normal datapoint segmentation and set difference it from `all users`.

Instead of querying all the user ids from the database all the time, you can store all the userids that were created till a particular time in  cache and query the rest from database, or update the cache to add newly added users hourly. But then for this to work we need an index on the `created_time` field of the user object. But we can make use of objectid property of mongo objects. It also contains the information related to when the object is created. Instead of creating an index on `created_time` field of the object we can filter directly on the object id to query on creation time of the object.
```
from bson.objectid import ObjectId
object_id_from_time_stamp = ObjectId.from_datetime(time_stamp)
cursor = db.Users.find({'_id': {'$gt': object_id_from_time_stamp}})
```
So I have a worker that updates the all users cache hourly to include the newly created users from that app. The cache key mechanism I used is such that I store 50k user ids in a single redis key and store the next 50k users in the next redis key. Also for smaller dbs I used to get all the users directly from db as often they are test apps, and it will be confusing for them to miss some users when they test using all users campaign.
I also store the last cache update time in redis, so that I can query all the new users created after that timestamp directly from db. I update the whole user cache weekly, just in case I miss some users some how.

This part of the code has to be implemented very carefully with lots of fall back mechanism. In further iterations I started getting user ids from the elasticsearch cluster. If Es fails for some reason, I get it from mongodb. And not all clients have ES river. And we a back up of querying es/mongo directly if the cache fails. The major reason I didn't store all the users in a single key is that If a single get request fails, the entire query returns zero users. Instead if I store only 50k users per key, even if single key might fail, the output wont be that unreasonable.

The sheer amount of edge cases that can screw up this result are so many I had to be very careful with this part.

But this improved the `All Users` query time from 10 minutes to in some cases less than 10 secs.

## Combining above filters.
Now that we discussed all the three types of major filters,
* datapoint segmentation filter(D)
* user segmentation filter(U)
* all users query(A)

Each of them get the userids from three different sources. And a single segment is a combination of one or more of any of the above three filters. And the combination can either be `intersection` or `union`.

We compute all the filters separately and combine them using basic python operations.

`Has not executed` is basically `All Users` - `has executed`

There are lot of iterative improvements that can be made on this naive implementation. Each filter is computed synchronously.  This can be done asynchronously. Asynchronously computing more than one datapoint filter might not be a great idea, as it might stress the datapoint cluster even more. And if you observe carefully, if there are more than one user filter, they can all be made into a single query on the user db. All sorts of combinations can be tried.

And if you study more carefully you can actually make use of set theory to reduce the computation complexity and speed up segmentation even more.

Below `A`, `B`, `C`, `D` are some combination of filters, and `S` is all users. So `S-C` is basically `has not executed` version of `C`.

Below is just one example of how to reduce the computation complexity of segmentation queries.

![Imgur](http://i.imgur.com/DA6xihK.png)



## Cluster config

## backup
We had backups in several stages, as soon as we get a http request, we back up that raw http request in s3, and then let web workers handle the request to be processed further.
At elasticsearch stage, we had two mechanisms, where we make use of snapshots, but this seemed to be unreliable. Every time a snapshot request is filed, it might or might not have worked. Given the sheer volume of the data we were dealing with, and our current index design, cluster operations like `index creation`, `index deleting`, `snapshot` these used to take some time. But major operations like search and indexing used to be very fast once an index got created. Anyway, snapshot is not really trustworthy in our case. So we just queried based on time stamp and had a worker back up the data from es to s3 in json format. I also had scripts ready so that I can recreate indexes from s3. But I always prayed we never had to use it.

## challenges while testing, smaller apps are different than bigger apps
Testing used to be a little challenging, cause, in more than one case, smaller apps are treated slightly different than bigger apps that are at more than order or two orders of volume.

Say for example, `All Users` is implemented differently for smaller and bigger apps.

## Custom segments
Instead of creating segments all the time, we also provide a way to store segmentation queries. So that they can create once and use them later.

Or a use case of where you are sending two push campaigns, and you don't want the users who were targeted in the first push campaign to get another push message, custom segments were very useful to exclude.

There are some custom segments that has more than 30 filters, its crazy.
## Overall diagrams/schemas
* Overall schema of datapoints and user cluster write operations.
![Imgur](http://i.imgur.com/QWBjdt7.jpg)
    1. raw http requests are handled by api/machines and backed up in s3 and sent to reports workers
    2. report workers insert event data using bulk indexing into datapoint cluster
    3. report workers also does some updates on mongo user objects
    4. the datapoint indexing operations might fail, the failed docs will be going to a separate index on es and if that fails as well it goes to mongo.
    5. datapoint cluster also gets event data from push workers, that captures campaign related information.
    6. the mongo connector infra takes care of replicating user data from mongo to user elasticsearch.

* Overall schema of datapoints and user cluster search/read/segmentation operations.
![Imgur](http://i.imgur.com/kkLwq5b.jpg)
    1. datapoint segmentation happens on datapoint cluster
    2. user segmentation happens on user cluster, if river exists
    3. if river doesn't exist it happens on mongo
    4. there are some events like app_opened and other important events whose histograms based on time, might reveal important usage statistics and key metrics, like MAU, DAU and other such data. These histograms are obtained form datapoint cluster
    5. campaign histograms, neat graphs based on campaign related events that shows how a campaign was delivered with time. you can get this data from datapoint cluster
    6. acquisition stats from user cluster
    7. key metrics such as uninstalled and etc can be obtained from user cluster
    8. auto trigger campaigns need a simple search based on user id and event, and this is done on datapoint cluster.

## Challenges, elasticsearch quirks
Once we replaced rivers with mongo-connector, user segmentation is smooth sailing when compared to datapoint segmentation. So most of the challenges I will be discussing in this section are datapoint cluster related and its design.

The single biggest challenge with datapoint cluster is how diverse the types of actions people are tracking, when it comes to volume. As I described earlier, we had one shard per index, as we are technically sharding on the name of the action. But we can't know what volume a given action will be before its created. The `read alias` and `write alias` of the created index sure does gives us some relief, but we are not exploiting it to the max. And some things are done manually which should have been automated. Like sometimes the size of an index gets so big, that I used to manually change the write alias to a new index, while searching on both the indexes.

Another challenge is that once a filed's type is induced by elasticsearch. And when you are trying to insert a doc with a different type, especially a filed that was induced to be `int` is getting documents with `string` it will throw up an error. 90% of the time, the mistyped data and the fields are not really of that much importance to marketers. But the rest of the 10% used to cause so many problems. I had a temporary fix to this, but we need to come up with a permanent solution to this.

The other request is to make the search queries case insensitive. Often the marketing people who are creating the segments don't know what exactly should be the search term. So they would prefer a case insensitive thing going. This request seems so innocent, but for me to implement this I have to rebuild all the indexes again with a different analyser. Given the sheer size of the data we are indexing daily, this  just seems like too much work for too little reward. I kept postponing this forever.

One more important thing is elasticsearch recommends a max heap size of only 32GB, and not more than that.

Given our index design, we are creating a new index every time they track a new event. There are no limitations on how many events an app might track. This resulted in having close to 10k shards per cluster. Which caused us so many problems. I don't even know if its normal, but somehow we made it work. Because of the sheer number of indexes/shards in the datapoint cluster, the meta data that the master nodes stores is so much, and most of the cluster operations used to take so much to succeed. And most of them fail. During really stressful periods of times, when big segmentation queries are running, and some new app is trying to start tracking new events. Most of them timed out cuz the index is not present. And the timed out documents are stored in a different mongo db, temporarily. When this happened, I got all the events they are tracking and keep on hitting the cluster with index creation requests till they succeed. I'm slightly embarrassed we had to do this. It always caused us problems. And this is the main reason for us to rearchitect. And we are well prepared to do this as I was much more comfortable with es after this adventure, which lasted for almost 1.5 years. Now I had a proper team and I headed the re-architecture project before moving on from Moengage.

There are lot more stuff I'm not able to recall right now, I might add more stuff later. probably not.

## Re-architecture

### Index aliasing
As described in earlier sections, the biggest challenge with the design is the sheer number of shards that exist in the cluster, no matter if a given index and its respective event gets queried a lot. A given app might be tracking a really high volume action, and at the same time several number of low volume actions that need their own events based on the above design. Somehow if we make use of index aliasing to be clever with how we direct what event data is written in what indexes, and what indexes will be searched given a segmentation query on the action. More or less the goal of the re-architecture is to reduce the number of shards in the cluster and more or less have all the shards of similar size.


For this we will have have one master index that contains all the smaller event data, basically when a new event gets tracked it is directed into the master index, by adding a new alias. As the days go along and that event starts getting more and more data, based on the volume of the event, we start writing the data into separate index. Based on the volume of the data, we decide if that new index gets rotated daily/weekly/monthly.

We will be having a external worker that constantly monitors what the volume of each event is and decides its `read alias` and `write alias`. And all the search queries will be on the event's `read alias` and all the insert operations will be on the event's `write alias`.

This will bring down the number of indexes that exist on the cluster a lot. and put us more in control.

This might reduce the number of indices by lot, but the master index we were talking about will have thousands of aliases.

### Case Insensitivity.
This request I'm dodging for a long time is now feasible as we were building the cluster again from the ground up and moving from the old cluster.

Basically we just have to change the analyser we were using to analyse our string fields.

The case insensitive analyser basically while indexes with lower case of all the string fields. If we index with lower case no matter what, and search with lower case, its just equivalent to case insensitivity.

We introduce this case insensitivity analyser using the index templates. For backward compatibility we store the unanalysed field as well as case insensitive analyser filed by having the template like below.

We access the old field while searching by querying on `field` name, and new case insensitive field with `field.case_insensitive`

<script src="https://gist.github.com/syllogismos/d7e63fd683484ab2d635b4c735bb7bfb.js"></script>

### Type errors/mismatch
Another major problem is that once you create an index, elasticsearch will induce the type of the fields as they come along. But once a document with a wrong datatype that can't be type casted is being inserted it will throw up an error. One elegant solution is that have your own type inference engine, and insert a field of type `int` and keyword `age` into `age_int` field, and when `age` of type `string` comes along, you can insert into `age_string`. If you infer the type of the field before you can handle this elegantly. But then inference of type is in your hands now.. And you have to modify the queries on the application side to take this into consideration. This way we wont face this problem anymore.

### Suggestions:
When people are creating segments on the dashboard, often people wont know what goes into it unless they go into another dashboard with all types of values a given key will be taking, So having a top 5 or top 10 values a particular string field takes will help a lot from user interface pov. Elasticsearch does have suggestions api, but I cant remember correctly, how we making use of it is non trivial or downright impossible with current index template settings and analyser. But in one of the hackathons I implemented this with some caching mechanism, from a simple aggregation query I can get the top 10 values a given field takes. And I maintain a cache that gets updated weekly or daily that gives the top 10 values.

### event management dashboard
As we discussed earlier, there is a huge disconnect between the developers who decide what to track, and the marketers who end up creating push campaigns and knows what events are relevant. As the size and the user base of the client integrating increases, the disconnect increases. As both are from two different departments.

Usually what developers do is track comprehensively and let marketers create campaigns on what ever they are interested in. Funnily because of this some clients happen to track more than 1000 events, with a dropdown of more than 1000 items in the dashboard. Which is almost nonsensical, especially when they are interested in at max 15 events.

If there are only 15 events marketers are interested in and we are indexing 1000s of useless indices, there is no point indexing everything in elasticsearch which is not cheap to have.

So to solve this if we proved a dashboard where they can decide what action they are segmentable. And we will only be indexing what ever they are interested in and chuck the rest in S3, and if they decide they want it back, start indexing it again and load the last 90days data from s3.

# Miscellaneous notes and scripts.
Be comfortable with the rest apis, I found it much more helpful than any elasticsearch plugin. Cat apis and the rest apis using `curl` and `jq` made my life so simple.

Learn the query language, once you are comfortable with it, it wont be as scary as it looks the first time you go see the documentation. `must`, `must_not`, `bool`, nested aggregations, histograms and etc.

```
1. Routing settings

curl -XPUT 172.31.46.49:9200/_cluster/settings -d '{
"persistent" : {
"cluster.routing.allocation.node_initial_primaries_recoveries": 4,
"cluster.routing.allocation.node_concurrent_recoveries": 15,
"indices.recovery.max_bytes_per_sec": "120mb",
"indices.recovery.concurrent_streams": 6
}
}'


'{
"persistent": {
"cluster.routing.allocation.node_concurrent_rebalance": 2}}'


"cluster.routing.allocation.node_initial_primaries_recoveries": 4
"cluster.routing.allocation.node_concurrent_recoveries": 15
"indices.recovery.max_bytes_per_sec": 100mb
"indices.recovery.concurrent_streams": 5

curl -XPOST 172.31.46.49:9200/_cluster/reroute -d '{"commands":[{"move":{"index":"wynkmusic-click", "shard":0, "from_node":"30GB_1TB_ComputeNode9", "to_node":"30GB_1TB_ComputeNode8"}}]}'

###################################################################

curl -XPOST 172.31.46.49:9200/_cluster/reroute -d '{
  "commands": [
    {
      "move": {
        "index": "wynkmusic-songplayedlong-feb0105",
        "shard": 0,
        "from_node": "30GB_1TB_ComputeNode7",
        "to_node": "30GB_1TB_ComputeNode9"
      }
    },
    {
      "move": {
        "index": "wynkmusic-songplayedlong-jan2531",
        "shard": 0,
        "from_node": "30GB_1TB_ComputeNode7",
        "to_node": "30GB_1TB_ComputeNode8"
      }
    }
  ]
}'
##################################################################

2. Rerouting a shard manually

curl -XPOST 172.31.46.49:9200/_cluster/reroute -d '{
        "commands" : [ {
              "allocate" : {
                  "index" : "shopotest-acceptonlinedisclaimer",
                  "shard" : 0, 
                  "node" : "30GB_1TB_ComputeNode5"
              }
            }
        ]
    }' | jq '.' > reroute_gos.json

###################################################################

3. Emptying a node completely, you can do this before decommissioning a node.

curl -XPUT 172.31.33.23:9200/_cluster/settings -d '{
"transient": {
"cluster.routing.allocation.exclude._ip": "172.31.33.23"
}}' | jq '.'


curl -XPUT 172.31.46.49:9200/_cluster/settings -d '{
"transient": {
"cluster.routing.allocation.exclude._ip": "172.31.41.73"
}}' | jq '.'

```

# Conclusion
Here is a brief explanation of how I made segmentation work for moengage using elasticsearch. I had a lot of fun with this challenge with no experience in distributed computing, I had to ramp up very fast and learned a lot. Being part of a startup forced me to do lot of learning in a very short period of time not just tech related, learned about building an engineering team, release process, workers, distributed computing, and what not to do. When I first joined I didn't think I get to play a major role on the moengage tech stack. For a long time till I left I took care of the elasticsearch infrastructure, application side logic, architecture design and etc all by myself with a engineering bandwidth. I'm very grateful for having this opportunity. I already postponed this blog post for a long time. I would have liked it to be much more comprehensive with code examples and so on. After a long of break from elasticsearch, I had to write this from memory. And lastly I'm forever grateful for moengage for pushing me so much and making me deliver.

Fun email we got on new years eve from arguably the biggest client we had in the initial stages.
```
Hi Guys
 
I have been trying for a very long time and no matter what combination of filters
are tried the server response is error. We are unable to make very basic segment
of customers. Frankly on New Years Eve we are not able to reach the right customer,
this is disappointing . Attaching screen shot here.
```
This is when we moved the segmentation architecture from mongo to elasticsearch. Everything was ready, only the data porting from mongo to es was left and releasing the new segmentation code. So in 24 hours we released the new segmentation logic and ported the data. The only reason I didn't release was because of me being relatively new in the company and me having to check everything twice or thrice. This email is the push we needed to jump head first. And it worked for a long time. Fun times.