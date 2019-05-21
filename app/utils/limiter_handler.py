import time
from functools import update_wrapper

from flask import request, g, jsonify
from flask_restful import abort, Resource
from marshmallow import Schema, fields
from redis import Redis

redis = Redis()
DEBUG = True
# TODO: implement this first as a config.json then as a cached PUB-SUB event.
CACHED_MITIGATIONS_IN_SERVER = dict()
_DYNAMIC_FILTERS_BY_IP_AND_URL = True  # TODO: leave me in False!


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
        print('\n' '\n' '\n' '\n' , b, '\n' '\n' '\n' '\n')
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

            if url_key:
                p.incr(url_key)
                if int(url_time) != 0:
                    p.expire(url_time, url_time)

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
                # Delete value of key
                p.delete(ip_key)
            if url_key:
                p.delete(url_key)
            b = p.execute()
            # Get the actual window counter b[0] is counter from last minute
        return {'message': 'OK'}, 200


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
    if DEBUG:
        print('response from redis: ¿is mitigated?', a, b)
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

    if current_url_rate >= url_limit:
        set_mitigation('mitigate/url/' + url + '/', time_of_expiration(url_limit, url_current, past_url_counter, per))
        print('Rate limit setted by URL', 'mitigate/url/' + url + '/')
    if current_ip_rate >= ip_limit:
        set_mitigation('mitigate/ip/' + ip + '/', time_of_expiration(ip_limit, ip_current, past_ip_counter, per))
        print('Rate limit setted by IP')

