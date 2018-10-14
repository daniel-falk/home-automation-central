import paho.mqtt.client as mqtt
import socket
from time import time, sleep
from threading import Lock
import logging

from topic_matcher import topic_matches_sub
from utils import get_mac, rand_str


logger = logging.getLogger('hallway-GUI')


class MQTT:
    def __init__(self, server='127.0.0.1', min_retry_time=2, max_retry_time=60, node_name=None):
        self.id = "{}-{}".format(get_mac(), rand_str(10))
        self.connected = False
        self.min_retry_time = min_retry_time
        self.max_retry_time = max_retry_time
        self.retry_time = self.min_retry_time
        self.server = server

        if not node_name:
            node_name = rand_str(10)
        banned = "/#+"
        self.node_name = "".join(["-" if ch in banned else ch for ch in node_name])

        self.path = "home/{name}/{mac}".format(name=self.node_name, mac=get_mac())

        self.mqttc = mqtt.Client(client_id=self.id, clean_session=True, userdata=self)
        self.mqttc.will_set(
                topic=self.path + "/info/status",
                payload="lost",
                qos=1,
                retain=True)

        self.mqttc.on_message = self._dispatch
        self.mqttc.on_connect = self._on_connect
        self.mqttc.on_disconnect = self._on_disconnect

        self.dispatch_table = dict()
        self.dtlock = Lock()

    def connect_and_block(self):
        '''Connect to MQTT and block until keyboard interrupt
        '''
        self.connect()

        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.disconnect()

    def connect(self):
        '''Connect to MQTT
        '''
        self.try_connect()
        self.mqttc.loop_start()

    def disconnect(self):
        '''Disconnect from MQTT
        '''
        self.publish({self.path + "/info/status": "disconnected"})
        sleep(0.5)
        self.mqttc.disconnect()
        self.mqttc.loop_stop()

    def subscribe(self, topic, callback, qos=1):
        '''Add a topic and a callback for subscription
        '''
        self.dtlock.acquire()
        try:
            if topic not in self.dispatch_table:
                self.mqttc.subscribe(topic, qos)
            self.dispatch_table[topic] = callback
        finally:
            self.dtlock.release()

    def topic_matches_sub(self, topic, sub):
        '''True if the topic matches the subscription
        '''
        return topic_matches_sub(sub, topic)

    def publish(self, data, retain=False, qos=1):
        '''Publish a dict with topic, message pairs
        '''
        data[self.path + "/info/last_update"] = str(time())
        for key, value in data.iteritems():
            self.mqttc.publish(
                    topic=key,
                    payload=value,
                    qos=qos,
                    retain=retain)

    def get_id(self):
        '''Get mqtt id
        '''
        return self.id

    def try_connect(self):
        '''Try to connect to mqtt server
        '''
        while not self.connected:
            try:
                self.mqttc.connect(self.server, keepalive=25)
                self.connected = True
            except socket.error:
                logger.warning("Failed to connect... Retrying in {} seconds".format(self.retry_time))
                sleep(self.retry_time)

    def _dispatch(self, client, data, msg):
        '''Callback for paho on mqtt message
        '''
        cb_lst = []
        data.dtlock.acquire()
        try:
            for sub, callback in data.dispatch_table.iteritems():
                if topic_matches_sub(sub, msg.topic):
                    cb_lst.append(callback)
        finally:
            data.dtlock.release()

        if not len(cb_lst):
            raise RuntimeError("Dispatch table failed to match topic", msg.topic)
        else:
            [callback(msg.topic, str(msg.payload.decode("utf-8"))) for callback in cb_lst]

    def _on_connect(self, client, data, flags, rc):
        '''Callback for paho on mqtt connected
        '''
        if rc == 0:
            data.publish({data.path + "/info/status": "online"})
            logger.info("Connected")
            return

        logger.warning("Connection failed with status " + str(rc))
        data.connected = False
        sleep(data.retry_time)
        data.retry_time = min(data.max_retry_time, data.retry_time*2)
        data.try_connect()

    def _on_disconnect(self, client, data, rc):
        '''Callback for paho on mqtt disconnect
        '''
        logger.warning("Disconnected with reason {}...".format(rc))
        data.connected = False
        if rc != 0:
            data.try_connect()
