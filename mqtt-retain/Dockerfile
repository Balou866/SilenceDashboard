FROM python:3.12-alpine
RUN pip install --no-cache-dir paho-mqtt==2.1.0
COPY mqtt-retain/relay.py /relay.py
CMD ["python", "/relay.py"]
