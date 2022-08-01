FROM python:3.9-slim
COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY ./app.py ./
COPY ./front ./front
COPY ./scheduler ./scheduler
COPY ./others ./others
CMD gunicorn --workers 4 --worker-class gevent --timeout 30 --bind 0.0.0.0:80 app:server 