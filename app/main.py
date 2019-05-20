# Native Imports
from functools import wraps
import requests
from threading import Thread

# Dependencies Imports
from flask import Flask, Response, request, jsonify
# TODO: 1)study performance with redirect(url_for('hello_guest',guest = name)) & from flask import Flask, redirect, url_for

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Module Imports
from app.limiter.limiter_handler import is_request_forbidden, _counter_increment

_DEFAULT_LIMIT_TO_ALL_URLS = 10  # 60000 rpm (1000 req x s)
_DEFAULT_LIMIT_TO_ALL_IP = 3  # 600 rpm (10 req x s)


# PROXIED_ROUTE
# _route = 'api-dev.XXXX/hello_world'
_route = '​api.mercadolibre.com/'

# Instantiate the app
app = Flask(__name__)
# If nginx or uwsgi is having problems with https redirection: --->
# app.config.update(dict(
#   PREFERRED_URL_SCHEME = 'https'
# ))

# Get cached configuration for limiter
# limits_cached_dict = CachedLimits().limits
#
# ####################################### # Instantiate Limiter class for IP throttling. Default rpm limit for all IPs
# ####################################### ip_limiter = Limiter(
# #######################################     app,
# #######################################     key_func=get_remote_address,
# #######################################     default_limits=limits_cached_dict['ip']['default_values']
# ####################################### )
# #######################################
# ####################################### ip_limiter.init_app(app)
# #######################################
# #######################################
# ####################################### # Create key_function for throttling URL addresses obtained from cached config
# ####################################### def url_filter_key_function():
# #######################################     return request.url
# #######################################
# #######################################
# ####################################### # Instantiate Limiter class route (url) throttling to ALL ip's
# ####################################### all_path_limiter = Limiter(
# #######################################     app,
# #######################################     key_func=url_filter_key_function,
# #######################################     default_limits=limits_cached_dict['path']['default_values']
# ####################################### )
# #######################################
# ####################################### all_path_limiter.init_app(app)

#
# # Decorators for proxy method
# def ip_filter_decorator(f):
#     @wraps(f)
#     def ipfilter(*args, **kwargs):
#         print('SEBA2', get_remote_address())
#         if get_remote_address() in limits_cached_dict['ip']['blacklist']:
#             return jsonify({'message': 'Forbidden entry: IP is not allowed..'}), 429
#         else:
#             return f(*args, **kwargs)
#     return ipfilter
#
#
# def url_filter_decorator(f):
#     @wraps(f)
#     def ufilter(path, *args, **kwargs):
#         print('SEBA3', request.url, path)
#         if path in limits_cached_dict['path']['blacklist']:
#             return jsonify({'message': 'Forbidden entry: desired url is not allowed..'}), 429
#         else:
#             return f(path, *args, **kwargs)
#     return ufilter
#

# ####### MY ROUTER FUNCTION ################## #

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path, *args, **kwargs):
    # print('original url', request.url)
    # print('destiny url', request.url.replace(request.host_url, 'https://' + _route))
    # TODO: add case for token limiter ¿?¿?¿?¿?
    print('BODY??', request.get_data())
    # Check if mitigation has started for IP and URL
    token = request.headers.get('Authorization')
    if is_request_forbidden(path, request.remote_addr):
        return jsonify({'message': 'Forbidden entry. Rate limit exceeded'}), 429
    # Request allowed:
    else:

        # Send request to backend server
        resp = requests.request(
            method=request.method,
            url=request.url.replace(request.host_url, 'https://' + _route),
            headers={key: value for (key, value) in request.headers if key != 'Host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False)
        # print('request.url', request.url) request.url http://localhost:8080/categories/MLA1112
        # print('remote_addr', request.remote_addr, 'endpoint', request.endpoint) remote_addr 127.0.0.1 endpoint proxy
        # Prepare proxied response
        # excluded_headers = []
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        # Send response to client
        response = Response(resp.iter_content(chunk_size=10 * 1024), resp.status_code,
                            headers, content_type=resp.headers['Content-Type'])

        # Start a background process to send rapidly response
        thread = Thread(target=_counter_increment, args=(path, request.remote_addr))
        thread.start()

        return response
# ############################################# #
@app.route('/foo')
def proxy2(*args, **kwargs):
    # Este anduvo..asiq podria setear y reetear filtros por aca
    # Tambien mandar estadisticas!
    return jsonify({'message': 'Hola, esta ruta aclarada anda :)'}), 429


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=8080)
