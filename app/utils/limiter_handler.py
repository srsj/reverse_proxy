import time

from flask import request, g, jsonify
from flask_restful import abort, Resource
from marshmallow import Schema, fields
from redis import Redis

from app.config import default_configuration

redis = Redis()
DEBUG = True

CACHED_MITIGATIONS_IN_SERVER = default_configuration


# validates the input with marshmallow
def validate_input(schema, json_data):
    try:
        data, errors = schema.load(json_data)
    except Exception as e:
        abort(400, message=str('Validation error: {}'.format(e)))

    if errors:
        abort(400, message=str(errors))

    return data


def security_wrapper(f):
    """
    This method should check that the requester ID (user) is an Admin
    or some kind of important role or user. So as to avoid that anyone
    can apply filters to this reverse_proxy. However, this was left
    unimplemented cause it was not the main part of the challenge
    :param f: function or method to wrap with security check
    :return: wrapped function
    """
    return f


class FilterSchema(Schema):
    filter_ip_tupple = fields.Dict()
    filter_url_tupple = fields.Dict()
    filter_url = fields.String()
    filter_ip = fields.String()


class Filter(Resource):

    @security_wrapper
    def get(self):
        """
        Get all applied filters in redis.
        :return:
        """
        # curl -X GET  http://localhost:8080/filter
        p = redis.pipeline()
        p.keys(pattern='mitigate*')
        b = p.execute()
        keys = list()
        for key in b[0]:
            ip = key.decode("utf-8").split(sep='mitigate/')[1]
            keys.append(ip)
        return {'message': 'OK', 'data': keys}, 200


    @security_wrapper
    def post(self):
        """
        :param filter_ip_tupple: <dict> of the remote address to apply mitigation. Sent in the request body data.
        Not required. Eg: {"127.0.0.1": 0}. Key is the IP to ban, and value is the amount of time in
        seconds to apply the filter. If 0 is given it will be applied forever.
        :param filter_url_tupple: <dict> of the URL (after prefix URL "​api.mercadolibre.com/") to apply mitigation.
        Sent in the request body data. Not required. Eg: {"categories/MLA1113": 0}
        Key is the URL path to ban, and value is the amount of time in seconds to apply the filter. if 0 is given
        it will be applied forever.
        :return:
        """
        # curl -X POST  http://localhost:8080/filter -H "Content-Type: application/json" -d '{"filter_ip_tupple": {"fake_ip3": "100"}}'
        # get json data from request
        json_data = request.get_json()
        if json_data is None:
            return {"message": 'Missing required JSON arguments: filter_ip nor filter_url tupple was given'}, 400

        filters_schema = FilterSchema()
        filters_schema.fields['filter_ip_tupple'].required = False
        filters_schema.fields['filter_url_tupple'].required = False

        # validates the input coming from the request as json
        data = validate_input(filters_schema, json_data)

        ip_key, url_key = None, None

        # extract variables
        if data.get('filter_ip_tupple'):
            ip_tuple = data['filter_ip_tupple'].popitem()
            ip, ip_time = ip_tuple
            ip_key = 'mitigate/ip/' + ip + '/'
        if data.get('filter_url_tupple'):
            url_tuple = data['filter_url_tupple'].popitem()
            url, url_time = url_tuple
            url_key = 'mitigate/url/' + url + '/'

        if ip_key or url_key:

            p = redis.pipeline()

            if ip_key:
                # Increments the value of key by 1
                p.incr(ip_key)
                # Set an expire flag on key name for time seconds
                if int(ip_time) != 0:
                    p.expire(ip_key, ip_time)
                    CACHED_MITIGATIONS_IN_SERVER[ip_key] = (ip_time)
                else:
                    # Set expiration time almost to infinity in local cache
                    CACHED_MITIGATIONS_IN_SERVER[ip_key] = (time.time() + 10e10)

            if url_key:
                p.incr(url_key)
                if int(url_time) != 0:
                    p.expire(url_time, url_time)
                    CACHED_MITIGATIONS_IN_SERVER[url_key] = (url_time)
                else:
                    # Set expiration time almost to infinity in local cache
                    CACHED_MITIGATIONS_IN_SERVER[url_key] = (time.time() + 10e10)


            b = p.execute()
            # Get the actual window counter b[0] is counter from last minute

        return {'message': 'OK'}, 200

    @security_wrapper
    def delete(self):
        """
        :param filter_ip_tupple: <dict> of the remote address to apply mitigation. Sent in the request body data.
        Not required. Eg: {"127.0.0.1": "0"}. Key is the IP to ban, and value is the amount of time in
        seconds to apply the filter. If 0 is given it will be applied forever.
        :param filter_url_tupple: <dict> of the URL (after prefix URL "​api.mercadolibre.com/") to apply mitigation.
        Sent in the request body data. Not required. Eg: {"categories/MLA1113": "0"}
        Key is the URL path to ban, and value is the amount of time in seconds to apply the filter. if 0 is given
        it will be applied forever.
        :return:
        """
        # curl -X DELETE  http://localhost:8080/filter -H "Content-Type: application/json" -d '{"filter_ip": "fake_ip2"}'
        # get json data from request
        json_data = request.get_json()
        if json_data is None:
            return {"message": 'Missing required JSON arguments: filter_ip nor filter_url was given'}, 400

        filters_schema = FilterSchema()
        filters_schema.fields['filter_ip'].required = False
        filters_schema.fields['filter_url'].required = False

        # validates the input coming from the request as json
        data = validate_input(filters_schema, json_data)

        ip_key, url_key = None, None

        # extract variables
        if data.get('filter_ip'):
            ip = data['filter_ip']
            ip_key = 'mitigate/ip/' + ip + '/'
        if data.get('filter_url'):
            url = data['filter_url_tupple']
            url_key = 'mitigate/url/' + url + '/'

        if ip_key or url_key:

            p = redis.pipeline()

            if ip_key:
                # Delete value of key of Redis Cluster
                p.delete(ip_key)
                if CACHED_MITIGATIONS_IN_SERVER.get(ip_key):
                    # Delete value of key of Local cache
                    CACHED_MITIGATIONS_IN_SERVER.pop(ip_key)

            if url_key:
                # Delete value of key of Redis Cluster
                p.delete(url_key)
                if CACHED_MITIGATIONS_IN_SERVER.get(url_key):
                    # Delete value of key of Local cache
                    CACHED_MITIGATIONS_IN_SERVER.pop(url_key)
            b = p.execute()
            # Get the actual window counter b[0] is counter from last minute
        return {'message': 'OK'}, 200


def _is_request_forbidden(resource, resource_name, key_prefix='mitigate/'):
    resource_key = key_prefix + resource_name + '/' + resource + '/'
    cached_url_mitigation = CACHED_MITIGATIONS_IN_SERVER.get(resource_key)
    # if cached_url_mitigation is None:
    #     cached_url_mitigation = CACHED_MITIGATIONS_IN_SERVER.get('default_' + resource_name)

    now = time.time()
    if cached_url_mitigation:
        if now > cached_url_mitigation:
            CACHED_MITIGATIONS_IN_SERVER.pop(resource_key)
            return False, resource_key
        else:
            return True, resource_key
    else:
        return False, resource_key


def is_request_forbidden(asked_url, remote_address):
    url_ip_asked = asked_url + '_' + remote_address

    # Check local CACHE in server before going to Redis
    url_forbidden,  url_key = _is_request_forbidden(asked_url, 'url')
    ip_forbidden,  ip_key = _is_request_forbidden(remote_address, 'ip')
    urlip_forbidden,  urlip_key = _is_request_forbidden(url_ip_asked, 'urlip')
    # If any is forbidden
    if url_forbidden or ip_forbidden or urlip_forbidden:
        return True

    p = redis.pipeline()
    p.get(url_key)
    p.get(ip_key)
    p.get(urlip_key)
    b = p.execute()
    if DEBUG:
        print('request to redis: is mitigated?? ', b, url_key, ip_key, urlip_key)
    return any(b)


def get_actual_count_and_increment(current_url_key, past_url_key,
                                   current_ip_key, past_ip_key,
                                   current_urlip_key, past_urlip_key,
                                   current_time, per):

    current_second = current_time % per

    p = redis.pipeline()
    p.get(past_url_key)
    p.get(past_ip_key)
    p.get(past_urlip_key)
    # Increments the value of key by amount. If no key exists, the value will be initialized as  amount
    p.incr(current_url_key)
    p.incr(current_ip_key)
    p.incr(current_urlip_key)
    # Set an expire flag on key name for time seconds
    p.expire(current_url_key, 2 * per - current_second)  # 2 minutes 1 for each window
    p.expire(current_ip_key, 2 * per - current_second)  # 2 minutes 1 for each window
    p.expire(current_urlip_key, 2 * per - current_second)  # 2 minutes 1 for each window
    b = p.execute()
    # Get the actual window counter b[0] is counter from last minute

    # current atempts during this minute
    url_current = b[3] - 1
    ip_current = b[4] - 1
    urlip_current = b[5] - 1

    past_url_counter = int(b[0]) if b[0] else 0
    past_ip_counter = int(b[1]) if b[1] else 0
    past_urlip_counter = int(b[2]) if b[1] else 0

    if DEBUG:
        print('response from redis: ', b)
        print('URL', current_url_key, past_url_key, url_current, past_url_counter)
        print('IP', current_ip_key, past_ip_key, ip_current, past_ip_counter)
        print('URLIP', current_urlip_key, past_urlip_key, urlip_current, past_urlip_counter)

    return url_current, past_url_counter, ip_current, past_ip_counter, urlip_current, past_urlip_counter


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


def time_of_expiration(limit, present_hits, previous_hits, period, actual_time):
    """
    Calculate how much time (seconds) must pass before letting another request in
    to comply with the limit imposed. Equation was calculated from original:
    rate <= limit = previous hits * (% of the previous window being evaluated) + actual hits
    (period - actual hits) / actual hits  <=  (limit - actual hits) / previous hits
    :param limit: <int> Number of requests permitted
    :param present_hits: <int> Number of request in the present window period
    :param previous_hits: <int> Number of request in the past window period
    :param period: <int> Period in seconds on which to look at
    :return:
    """
    if previous_hits != 0:
        print('Expiration time', period * (1 - (limit - present_hits) / previous_hits) - actual_time)
        return period * (1 - (limit - present_hits) / previous_hits) - actual_time
    else:
        return period - actual_time


def _counter_increment(url, ip, per=60):
    # url_limit = CACHED_MITIGATIONS_IN_SERVER.get(url) if CACHED_MITIGATIONS_IN_SERVER.get(url) else \
    #     CACHED_MITIGATIONS_IN_SERVER['default_url']
    #
    # ip_limit = CACHED_MITIGATIONS_IN_SERVER.get(ip) if CACHED_MITIGATIONS_IN_SERVER.get(ip) else \
    #     CACHED_MITIGATIONS_IN_SERVER['default_ip']

    # minute, second = time.strftime("%M,%s").split(',')
    # current_time = int(second)
    # current_second = current_time % per

    current_url_key, past_url_key, url_limit, current_second, current_time = aux_counter_increment(url, 'url', per)
    current_ip_key, past_ip_key, ip_limit, _, _ = aux_counter_increment(url, 'url', per)
    current_urlip_key, past_urlip_key, urlip_limit, _, _ = aux_counter_increment(url, 'urlip', per)

    url_current, past_url_counter,\
    ip_current, past_ip_counter, \
    urlip_current, past_urlip_counter = get_actual_count_and_increment(
        current_url_key,past_url_key,
        current_ip_key,past_ip_key,
        current_urlip_key, past_urlip_key,
        current_time, per)

    # current mean rate (number of request in 1 minute window)
    current_url_rate = int(past_url_counter * ((60 - (current_time % 60)) / 60) + url_current)
    current_ip_rate = int(past_ip_counter * ((60 - (current_time % 60)) / 60) + ip_current)
    current_urlip_rate = int(past_urlip_counter * ((60 - (current_time % 60)) / 60) + urlip_current)

    if current_url_rate >= url_limit:
        set_mitigation('mitigate/url/' + url + '/',
                       time_of_expiration(url_limit, url_current, past_url_counter, per, current_second)
                       )
        print('Rate limit setted by URL. Current rate:', current_url_rate, 'Limit:', url_limit)
    if current_ip_rate >= ip_limit:
        set_mitigation('mitigate/ip/' + ip + '/',
                       time_of_expiration(ip_limit, ip_current, past_ip_counter, per, current_second)
                       )
        print('Rate limit setted by IP. Current rate:', current_ip_rate, 'Limit:',  ip_limit)

    if current_urlip_rate >= urlip_limit:
        set_mitigation('mitigate/urlip/' + url + '_' + ip + '/',
                       time_of_expiration(urlip_limit, urlip_current, past_urlip_counter, per, current_second)
                       )
        print('Rate limit setted by URL+IP. Current rate:', current_urlip_rate, 'Limit:',  urlip_limit)


def aux_counter_increment(resource, resource_name, per):
    resource_limit = CACHED_MITIGATIONS_IN_SERVER.get(resource) if CACHED_MITIGATIONS_IN_SERVER.get(resource) else \
        CACHED_MITIGATIONS_IN_SERVER['default_' + resource_name]

    current_minute, unix_second = time.strftime("%M,%s").split(',')
    current_time = int(unix_second)
    # With another period given this can be WINDOW instead of minute
    current_second = current_time % per
    past_minute = int(current_minute) - 1 if int(current_minute)!=0 else 59

    current_resource_key = resource_name + "_count/" + resource + '/' + str(current_minute)
    past_resource_key = resource_name + "_count/" + resource + '/' + str(past_minute)

    return current_resource_key, past_resource_key, resource_limit, current_second, current_time