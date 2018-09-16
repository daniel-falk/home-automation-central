#!/usr/bin/python3

import paho.mqtt.client as mqtt
import json
from queue import Queue
from threading import Thread
from time import sleep

class LocalMQTT:
    mapping = {
            "home/greenhouse/esp32-1/weather": "*******SECRET*TOKEN******",
            }

    def __init__(self, host, callback, debug=False):
        self.callback = callback
        self.debug = debug

        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message

        if self.debug:
            print("Connecting..")
        client.connect(host, 1883, 60)

        if self.debug:
            print("Ok")
        client.loop_forever()


    def on_connect(self, client, userdata, flags, rc):
        if self.debug:
            print("Local client connected with result code " + str(rc))
        client.subscribe("#")


    def on_message(self, client, userdata, msg):
        try:
            # Se if it has a token in ThingsBoard
            try:
                token = self.mapping[msg.topic]
            except KeyError:
                return

            # Test if valid json, otherwise pack it
            data = msg.payload.decode("utf-8")
            try:
                data = json.loads(data)
                if not isinstance(data, dict):
                    raise ValueError()
            except ValueError:
                data = {"value" : data}

            if self.debug:
                print("Publish as [%s]: %s" % (token, json.dumps(data)))
            self.callback(token=token, topic=msg.topic, data=json.dumps(data))

        except Exception as e:
            print(type(e))
            print(e)


class ThingsBoardPublishWorker:
    connected = False

    def __init__(self, host, queue, token, debug=False):
        self.queue = queue
        self.token = token
        self.debug = debug

        client = self.client = mqtt.Client()
        client.username_pw_set(token)
        client.on_connect = self.on_connect
        client.connect(host, 1883, 60)
        client.loop_start()

        t = self.t = Thread(target=self.work)
        t.daemon = True
        t.start()


    def work(self):
        while True:
            if self.connected:
                item = self.queue.get()
                topic = item.get("topic")
                if not topic:
                    self.queue.task_done()
                    continue
                data = item.get("data")
                print("Publish: %s : %s" % ("v1/devices/me/telemetry", data))
                ref = self.client.publish("v1/devices/me/telemetry", data)
                ref.wait_for_publish() # TODO: This should be uncyncronious!
                print("Data sent")
                self.queue.task_done()
            else:
                sleep(0.1)


    def on_connect(self, client, userdata, flags, rc):
        self.connected = True
        try:
            if self.debug:
                print("New ThingsBoard client connected with result code " + str(rc))

        except Exception as e:
            print(type(e))
            print(e)


class ThingsBoardBridge:
    workers = {}


    def __init__(self, debug=False):
        self.debug = debug
        lmqtt = LocalMQTT("192.168.0.80", self.callback, debug=debug)


    def add_or_get_worker(self, token):
        # Add to queue if token already has a worker,
        # otherwise create a worker and Queue
        try:
            worker = self.workers[token]
        except KeyError:
            q = Queue()
            pw = ThingsBoardPublishWorker("192.168.100.200", q, token, debug=self.debug)
            worker = {"Q": q, "worker": pw}
            self.workers[token] = worker
        return worker


    def callback(self, **kwargs):
        token = kwargs["token"]
        w = self.add_or_get_worker(token)
        w["Q"].put(kwargs)


def main():
    ThingsBoardBridge(debug=True)

if __name__ == "__main__":
    main()
