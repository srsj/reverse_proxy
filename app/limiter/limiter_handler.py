import time
from functools import update_wrapper
from flask import request, g
import math

from redis import Redis
redis = Redis()

# TODO: implement this first as a config.json then as a cached PUB-SUB event.
CACHED_MITIGATIONS_IN_SERVER = dict()
_DYNAMIC_FILTERS_BY_IP_AND_URL = True  # TODO: leave me in False!
#
# _limits = {'ip':
#                {'blacklist': {'127.0.0.0': 0,
#                               },
#                 'default_values': []
#                 },
#            'path':
#                {'blacklist': ['categories/MLA1112',
#                              # 'categories/MLA1111',
#                              ],
#                 'default_values': []
#                }
#           }
#
#
# class CachedLimits():
#     def __init__(self):
#         self.limits = _limits

#
#
# class RateLimit(object):
#
#     # def __init__(self, key_prefix, limit, per, send_x_headers):
#     #
#     #     self.reset = (int(time.time()) // per) * per + per
#     #     print('AAAAAA', self.reset)  # 1557848520  or 1558205310
#     #     self.key = key_prefix + str(self.reset)
#     #     self.limit = limit
#     #     self.per = per
#     #     self.send_x_headers = send_x_headers
#     #     # print('CCCCC', self.send_x_headers)  # True
#     #
#     #     p = redis.pipeline()
#     #     print('key', self.key)  # rate-limit/proxy/127.0.0.1/1557848520
#     #
#     #     # Increments the value of key by amount. If no key exists, the value will be initialized as  amount
#     #     p.incr(self.key)
#     #     # Set an expire flag on key name for time seconds. time can be represented by an integer or a Python
#     #       # timedelta object.
#     #     p.expireat(self.key, self.reset + self.expiration_window)
#     #     b = p.execute()
#     #     a = b[0]
#     #     print('p.execute, b()[0]', a, b)  # p.execute, b()[0] 1 [1, True]
#     #     # current atempts during this minute
#     #     self.current = min(a, limit)
#     #     print('current atempts', self.current)  # 2 cdo ya me bloquea
#     #
#     # remaining = property(lambda x: x.limit - x.current)
#     # over_limit = property(lambda x: x.current >= x.limit)
#     # # print('EEEEE', remaining, over_limit)  # <property object at 0x7f2704b419f8> <property object at 0x7f2704b41d18>
#
#     def __init__(self, url_key, ip_key, url_limit, ip_limit, per, send_x_headers):
#         # I think key prefix could be the URL
#         self.current_time = int(time.time())
#         self.current_second = self.current_time % 60
#         self.current_minute = math.floor(self.current_time / 60) % 60
#         self.past_minute = self.current_minute - 1  # (self.current_minute + 59) % 60
#         self.current_url_key = "url_count/" + url_key + '/' + str(self.current_minute)
#         self.current_ip_key = "ip_count/" + ip_key + '/' + str(self.current_minute)
#         self.past_url_key = "url_count/" + url_key + '/' + str(self.past_minute)
#         self.past_ip_key = "ip_count/" + ip_key + '/' + str(self.past_minute)
#
#         self.send_x_headers = send_x_headers  # True
#
#         p = redis.pipeline()
#         p.get(self.past_url_key)
#         p.get(self.past_ip_key)
#         # Increments the value of key by amount. If no key exists, the value will be initialized as  amount
#         p.incr(self.past_url_key)
#         p.incr(self.past_ip_key)
#         # Set an expire flag on key name for time seconds
#         p.expire(self.current_url_key,   120 - self.current_second)  # 2 minutes 1 for each window
#         p.expire(self.current_ip_key,   120 - self.current_second)  # 2 minutes 1 for each window
#         b = p.execute()
#         # Get the actual window counter b[0] is counter from last minute
#         a = b[1]
#         print('AAAAAA', a, b)
#         print('URL', self.current_url_key, self.past_url_key, self.current_second)
#         print('IP', self.current_ip_key, self.past_ip_key, self.current_second)
#         # current atempts during this minute
#         self.url_current = b[2] - 1  # min(a, limit)
#         self.ip_current = b[3] - 1  # min(a, limit)
#         self.url_limit = url_limit  # min(a, limit)
#         self.ip_limit = ip_limit  # min(a, limit)
#
#         self.past_url_counter = int(b[0]) if b[0] else 0
#         self.past_ip_counter = int(b[1]) if b[1] else 0
#         # current mean rate (number of request in 1 minute window)
#         self.current_url_rate = int(self.past_url_counter * ((60 - (self.current_time % 60)) / 60) + self.url_current)
#         self.current_ip_rate = int(self.past_ip_counter * ((60 - (self.current_time % 60)) / 60) + self.ip_current)
#         print('CCCCCC', self.current_url_rate, self.past_url_counter, self.url_current, self.url_limit)
#         print('DDDDDD', self.current_ip_rate, self.past_ip_counter, self.ip_current, self.ip_limit)
#         # print('DDDDDD', self.limit, self.current_rate, self.current)
#
#     url_remaining = property(lambda x: x.url_limit - x.current_url_rate)
#     ip_remaining = property(lambda x: x.ip_limit - x.current_ip_rate)
#     url_over_limit = property(lambda x: x.current_url_rate >= x.url_limit)
#     ip_over_limit = property(lambda x: x.current_ip_rate >= x.ip_limit)
#     # print('EEEEE', remaining, over_limit)  # <property object at 0x7f2704b419f8> <property object at 0x7f2704b41d18>
#
#
# def get_view_rate_limit():
#     return getattr(g, '_view_rate_limit', None)
#
#
# def url_on_over_limit(limit):
#     return 'You hit the URL rate limit: {}'.format((limit.url_remaining, limit.url_over_limit)), 429
#
# # TODO: put responses more tidier and the same as filters!
# def ip_on_over_limit(limit):
#     return 'You hit the IP rate limit: {}'.format((limit.ip_remaining, limit.ip_over_limit)), 429
#
#
# def ratelimit(url_limit, ip_limit, per=60, send_x_headers=True,
#               url_over_limit=url_on_over_limit,
#               ip_over_limit=ip_on_over_limit,
#               scope_func=lambda: request.remote_addr,
#               key_func=lambda: request.endpoint):
#     def decorator(f):
#         def rate_limited(path, *args, **kwargs):
#             # key = 'rate-limit/%s/%s/' % (path, scope_func()) # (key_func(), scope_func())
#             rlimit = RateLimit(path, scope_func(), url_limit, ip_limit, per, send_x_headers)
#             g._view_rate_limit = rlimit
#             if url_over_limit is not None and rlimit.url_over_limit:
#                 return url_over_limit(rlimit)
#             if ip_over_limit is not None and rlimit.ip_over_limit:
#                 return ip_over_limit(rlimit)
#             return f(path, *args, **kwargs)
#         return update_wrapper(rate_limited, f)
#     return decorator

###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################


def is_request_forbidden(asked_url, remote_address, key_prefix='mitigate/'):
    url_key = key_prefix + 'url/' + asked_url + '/'
    ip_key = key_prefix + 'ip/' + remote_address + '/'

    cached_url_mitigation = CACHED_MITIGATIONS_IN_SERVER.get(url_key)
    cached_ip_mitigation = CACHED_MITIGATIONS_IN_SERVER.get(ip_key)
    now = time.time()
    # If limitation is in memory avoid doing the trip to Redis (to mitigate possible attacks)
    if cached_url_mitigation:
        if now > cached_url_mitigation:
            CACHED_MITIGATIONS_IN_SERVER.pop(url_key)
        else:
            print('Redis trip saved!!! ')
            return True
    if cached_ip_mitigation:
        if now > cached_ip_mitigation:
            CACHED_MITIGATIONS_IN_SERVER.pop(ip_key)
        else:
            print('Redis trip saved!!! ')
            return True

    p = redis.pipeline()
    p.get(url_key)
    p.get(ip_key)
    b = p.execute()
    print('request to redis: is mitigated?? ', b)
    return any(b)


def get_actual_count_and_increment(url, ip, per, current_time):

    current_second = current_time % per
    current_minute = int(current_time / per) % per
    past_minute = current_minute - 1

    current_url_key = "url_count/" + url + '/' + str(current_minute)
    current_ip_key = "ip_count/" + ip + '/' + str(current_minute)
    past_url_key = "url_count/" + url + '/' + str(past_minute)
    past_ip_key = "ip_count/" + ip + '/' + str(past_minute)

    p = redis.pipeline()
    p.get(past_url_key)
    p.get(past_ip_key)
    # Increments the value of key by amount. If no key exists, the value will be initialized as  amount
    p.incr(past_url_key)
    p.incr(past_ip_key)
    # Set an expire flag on key name for time seconds
    p.expire(current_url_key, 2 * per - current_second)  # 2 minutes 1 for each window
    p.expire(current_ip_key, 2 * per - current_second)  # 2 minutes 1 for each window
    b = p.execute()
    # Get the actual window counter b[0] is counter from last minute
    a = b[1]
    print('AAAAAA', a, b)
    print('URL', current_url_key, past_url_key, current_second)
    print('IP', current_ip_key, past_ip_key, current_second)
    # current atempts during this minute
    url_current = b[2] - 1  # min(a, limit)
    ip_current = b[3] - 1  # min(a, limit)

    past_url_counter = int(b[0]) if b[0] else 0
    past_ip_counter = int(b[1]) if b[1] else 0

    return url_current, past_url_counter, ip_current , past_ip_counter


def set_mitigation(key_to_mitigate, expiration_duration):
    """
    :param key_to_mitigate: <str>
    :param expiration_duration: <str> or <int>. Duration in SECONDS
    """
    p = redis.pipeline()
    p.incr(key_to_mitigate)
    p.expire(key_to_mitigate, int(expiration_duration))
    p.execute()
    CACHED_MITIGATIONS_IN_SERVER[key_to_mitigate] = (time.time() + expiration_duration)


def time_of_expiration(limit, present_hits, previous_hits, period):
    return period * (1 - (limit - present_hits) / previous_hits)


def _counter_increment(url, ip, url_limit=3, ip_limit=10, per=60):
    # TODO get limits from local memory ???
    minute, second = time.strftime("%M,%s").split(',')
    current_time = int(second)

    url_current, past_url_counter, ip_current, past_ip_counter = get_actual_count_and_increment(url,
                                                                                                ip,
                                                                                                per,
                                                                                                current_time
                                                                                                )

    # current mean rate (number of request in 1 minute window)
    current_url_rate = int(past_url_counter * ((60 - (current_time % 60)) / 60) + url_current)
    current_ip_rate = int(past_ip_counter * ((60 - (current_time % 60)) / 60) + ip_current)
    print('CCCCCC', current_url_rate, past_url_counter, url_current, url_limit)
    print('DDDDDD', current_ip_rate, past_ip_counter, ip_current, ip_limit)
    # print('DDDDDD', self.limit, self.current_rate, self.current)

    if current_url_rate >= url_limit:
        set_mitigation('mitigate/url/' + url + '/', time_of_expiration(url_limit, url_current, past_url_counter, per))
        print('Rate limit setted by URL', 'mitigate/url/' + url + '/')
    if current_ip_rate >= ip_limit:
        set_mitigation('mitigate/ip/' + ip + '/', time_of_expiration(ip_limit, ip_current, past_ip_counter, per))
        print('Rate limit setted by IP')


url_remaining = property(lambda x: x.url_limit - x.current_url_rate)
ip_remaining = property(lambda x: x.ip_limit - x.current_ip_rate)
url_over_limit = property(lambda x: x.current_url_rate >= x.url_limit)
ip_over_limit = property(lambda x: x.current_ip_rate >= x.ip_limit)