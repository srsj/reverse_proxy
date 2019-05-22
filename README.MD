# Welcome to my Reverse Proxy Repository

This repository aims to build a docker compose that deploys a reverse proxy service with some features:
- limit throttling by IP, URL or both
- filtering request by IP, URL or both permanently
- Filters can be applied (POST) and removed (DELETE) through HTTP request to any instance of the service using "/filter"
- If a PUB SUB service is implemented default limits can be modified on the fly rapidly
- Logs are automatically sent to S3 once a rotation has ended. If the instance shutdowns it will also sync access logs
- Stats in real time from each server can be obtained through GET request to "/get_stats"

#### Configuring the service:

* aws-cli command line should be available in the docker image for this to work!
* logrotate.d configuration should be updated with the one provided in this repo
* nginx configuration should be updated with the one provided in this repo
* upstart job config file (/etc/init/shutdown-hook.conf) should be updated with the one provided in this repo

#### Brief explanation of the flow
For every request that reaches the service, Nginx server will be the master process in charge of the workers process execution. It will derive the request
to Flask app using (WSGI interface, in this case uWSGI). Once in Flask, a single GET trip to the Redis Cluster will be made to see if the resource (URL, IP, combination, or others)
is prohibited. In case not, the request will be read and a new request will be made to the desired URL. Then, after receiving the response, it will re format some headers.
Before sending the response it will create a new thread (to be executed asynchronous) and then the response is send back to the original requester.

The new thread iniciated will be en charge of getting the limits from the cache, getting the counter from the resources (of the last time window and the actual
window) and compute a mean rate at this window length. If mean rate is equal or greater than the limit, a mitigation will be imposed in the Redis Cluster for a period of time so
as to ensure that the rate limit is accomplished. More over, it will save this information locally in the server so that subsequent request from this resource will be forbidden
without even doing the GET request to the Redis Cluster. This tweak will mitigate possible attacks without penalizing "real" requests (If a lot of GETs are done at the same time,
the response from Redis can get lower). As sticky sessions will be used in the deployment of the instances cluster (rerouting) so the requests from the same client are always
forwarded to the same web server instance, then this feature of saving locally the mitigated resources is very usefull.

Filters to ban ALL request to a URL, from an IP or mixes can be applied (or removed) by HTTP request to any server instances. This server will then propagate this mitigation to
the Redis Cluster and save it locally. The rate limits to all IP's, URL's and mixes are setted by a configuration file. However, it is proposed to use a PUB SUB service, and subscribe
all servers so that rate limits can be modified on the fly in all the servers. At the moment, this repo only supports default limits to resources.


#### Logging proposed improvements
The visualisation of data is a necessary step in situations where a huge amount of data is generated every single moment.
Nginx web server and Flask (through the uWSGI component) both log activity in the server. A special configuration is proposed for Nginx for additional valuable information as
response time and response size. Automatically it is copied to a specific bucket in a storage service (S3 in this case) when a log file is rotated. The config of shutdown-hook
also is to be modified so logs are copied to s3 in case of a failure and shutdown.
However, this is far from the ideal implementation of logging activity in a proxy service running in multiple instances.
A better implementation would be the so called ELK stack:
Elasticsearch + Logstash + Kibana (all of them open source)
LogStash will listen to the application logs (in each server instance) and transform those logs to a JSON format. Then it will send the JSON formatted logs to Elasticsearch.
User will view the logs from KIBANA, which is the interface of elastic search cluster.
Elasticsearch is a distributed search and analytics engine. It stores centrally all the data collected so that many type of searchs can be implemented.
Logstach is a server-side data processing pipeline that gets information from multiple sources, transforms it and send it to a centrilized "stash"
Kibana is an open source analytics and visualization platform designed to work with Elasticsearch indices.

We can use Logstash and Python programs (Flask) to parse the raw log data and pipeline it to Elasticsearch from which Kibana consumes data.



Example from access.log of Nginx:

190.191.147.123-+-200-+-[2019-05-22T14:43:52+00:00]-+-"GET /test:endpoint HTTP/1.1"-+-875-+-0.052-+-"https://web-test.testing.com/"-+-"172.31.0.170"

