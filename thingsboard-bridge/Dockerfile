FROM python:3.4.9-slim

RUN pip install paho-mqtt

COPY things_board_bridge.py /src/things_board_bridge.py
CMD python /src/things_board_bridge.py
