# Native Imports
import requests
from threading import Thread

# Dependencies Imports
from flask_restful import Api
from flask import Flask, Response, request, jsonify
import pandas as pd

# online resource access permission
from flask_cors import CORS

# Module Imports
from app.utils.limiter_handler import is_request_forbidden, _counter_increment, Filter, security_wrapper


# excpetions_log_path = '/home/ubuntu/log_api.log'

# PROXIED_ROUTE
_route = '​api.mercadolibre.com/'

# Instantiate the app
app = Flask(__name__)
# default CORS config, which allows requests from all origins (doesn't filter anything)
CORS(app)
api = Api(app)


# ####### MY PROXY FUNCTION ################## #

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path, *args, **kwargs):
    # TODO: add case for token limiter ¿?¿?¿?¿?
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
        # Prepare proxied response
        # excluded_headers = []
        # The Content-Length header field MUST NOT be sent if these two lengths are different
        # (i.e., if a Transfer-Encoding header field is present). If a message is received with
        # both a Transfer-Encoding header field and a Content-Length header field, the latter MUST be ignored.
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
# ########### ROUTUING ######################## #
api.add_resource(Filter,  '/filter')


@app.route('/get_stats')
@security_wrapper
def get_stats(*args, **kwargs):
    # Example log line:
    # 190.191.147.145-+-200-+-[2019-05-21T19:59:28+00:00]-+-"GET /crops HTTP/1.1"-+-917-+-0.871-+-"https://...."-+-"172.31.0.170"
    access_log = '/var/log/nginx/access.log;'
    # TODO: erase local exmaple!!!
    access_log = '/home/ssanchez/Documents/temp/api_exceptions.log'

    df = pd.DataFrame(columns=['remote_addr', 'status', 'stat_digit', 'time', 'req',
                               'req_size', 'req_time', 'referer', 'server_addr'])
    with open(access_log, mode='r') as log:
        for line in log:
            try:
                adr, stat, time, req, rq_sz, rq_t, ref, srv_adr = line.split(sep='-+-')
                df.loc[len(df)] = [adr, int(stat), int(stat[0]),
                                   time, req, float(rq_sz), float(rq_t), ref, srv_adr[:-1]]
            # For last line empty --> results in a ValueError
            except ValueError:
                pass

    successes = df.stat_digit[df.stat_digit.apply(lambda x: x is 2)]
    client_errors = df.stat_digit[df.stat_digit.apply(lambda x: x is 4)]
    server_errors = df.stat_digit[df.stat_digit.apply(lambda x: x is 5)]

    total_req = len(df)

    success_rate = (len(successes) / total_req) * 100
    client_err_rate = (len(client_errors) / total_req) * 100
    server_err_rate = (len(server_errors) / total_req) * 100

    mean_request_time = df.req_time.mean()
    number_of_req_slower_than_mean = len(df.req_time[df.req_time.apply(lambda x: x > mean_request_time)])
    number_of_req_slower_than_500ms = len(df.req_time[df.req_time.apply(lambda x: x > 0.5)])

    mean_req_size = df.req_size.mean()

    return jsonify({'message': 'OK', 'data': {'n req slower than mean': number_of_req_slower_than_mean,
                                              'n req slower than 500ms': number_of_req_slower_than_500ms,
                                              'mean_proxy_time': mean_request_time,
                                              'success rate (%)': success_rate,
                                              'client errors rate (%)': client_err_rate,
                                              'server errors rate (%)': server_err_rate,
                                              'request analyzed': total_req,
                                              'mean req size': mean_req_size,
                                              }}), 429


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=8080)
