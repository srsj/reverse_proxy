import datetime
import calendar
import time
import os
import logging
import logging.handlers

import redis
# aws communication
import boto3
import botocore
import paramiko
from botocore.exceptions import ClientError


# framework:
from flask_restful import request, abort, Resource
from flask import jsonify
from marshmallow import Schema, fields

from app.utils.limiter_handler import redis



# --------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------
# class ExtraLogDataFromRequest(logging.Filter):
#     def filter(self, log_record):
#         ''' Provide some extra variables to give our logs some better info '''
#         # log_record.utcnow = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S,%f %Z')
#         log_record.endpoint = request.path
#         log_record.http_method = request.method
#
#         # Try to get the IP address of the user through reverse proxy
#         log_record.clientip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
#         log_record.server_protocol = request.environ['SERVER_PROTOCOL']
#         try:
#             log_record.user_agent = request.environ['HTTP_USER_AGENT']
#         except KeyError:
#             log_record.user_agent = 'HTTP_USER_AGENT:NotFound'
#         # if current_user.is_anonymous():
#         #     log_record.user_id = 'guest'
#         # else:
#         #     log_record.user_id = current_user.get_id()
#         return True
#
# def create_exception_logger():
#     """
#     Create a logger object to print Exceptions' stacktraces to a file and returns this object.
#     :return:
#     """
#
#     logger = logging.getLogger('exception_logger')
#     logger.setLevel(logging.INFO)
#
#     # Declare log path
#     # excpetions_log_path = os.path.join(os.path.expanduser("~"), 'api_exceptions.log')
#     excpetions_log_path = '/home/ssanchez/Documents/temp/api_exceptions.log'
#
#     # create a file handler
#     # file_handler = logging.FileHandler(excpetions_log_path)
#     file_handler = logging.handlers.WatchedFileHandler(excpetions_log_path)
#
#
#     # pre format the log messages
#     # 141.105.71.143 - - [29/Aug/2018:13:53:01 +0000] "GET /000000000000.cfg HTTP/1.1" 404 178 "-" "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0"
#     formatter = logging.Formatter('%(clientip)s - - [%(asctime)s] "%(http_method)s %(endpoint)s %(server_protocol)s" "%(user_agent)s" by %(name)s. %(levelname)s: %(message)s')
#     file_handler.setFormatter(formatter)
#
#     # asign the file handler to the logger object
#     logger.addHandler(file_handler)
#
#     logger.addFilter(ExtraLogDataFromRequest())
#
#     # return the logger object
#     return logger
#
# exception_logger = create_exception_logger()



