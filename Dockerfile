FROM tiangolo/uwsgi-nginx-flask:flask
COPY requirements.txt /tmp/
# upgrade pip and install required python packages
RUN pip install -U pip
RUN pip install -r /tmp/requirements.txt
# copy over our app code
COPY ./app /app



# FROM python:3
# RUN pip install flask
# RUN pip install redis
# RUN pip install marshmallow
# RUN pip install pandas