FROM python:3
RUN pip install flask
RUN pip install redis
RUN pip install marshmallow
RUN pip install pandas