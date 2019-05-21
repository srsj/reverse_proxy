#!/bin/bash

log_file_extension=$1

# Compress log (since delaycompress was set on logrotate config for nginx)
gzip -c /var/log/nginx/*.$log_file_extension > /tmp/log.gz

# Get ip of the instance to append it to log name
my_ip=$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1')

# Send compressed log to s3
aws s3 cp /tmp/log.gz s3://MY_S3_BUCKET/logs/reverse_proxy/$my_ip'_'`date +%Y-%m-%dT%H:%M:%S`.log.gz


