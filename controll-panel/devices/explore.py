import imp
from os.path import dirname


class DeviceExplorer:

    def __init__(self, mqtt, devices):
        self.mqtt = mqtt
        self.devices = devices

        self.status_topic_map = dict()

    def find_class(self, class_name):
        device_class = self._get_class(class_name)

        if class_name in [v["class_name"] for v in self.status_topic_map.values()]:
            raise ValueError("Device ({}) already added...".format(class_name))

        device_topic = device_class.find()

        # Todo, check so that two subscriptions can't match on the same topic
        if device_topic in self.status_topic_map.keys():
            raise RuntimeError("Device class '{}' uses the same status topic as '{}'".format(
                class_name,
                self.status_topic_map[device_topic]["class_name"]))

        self.status_topic_map[device_topic] = device_class

        self.mqtt.subscribe(device_topic, self._mqtt_status_callback)

    def _mqtt_status_callback(self, topic, payload):
        device_class = None
        for sub, value in self.status_topic_map.iteritems():
            if self.mqtt.topic_matches_sub(topic, sub):
                if device_class is None:
                    device_class = value
                else:
                    raise RuntimeError("Panic, status topic matches two subscriptions, {} and one of {}".format(
                        sub, self.status_topic_map.keys()))

        if device_class is None:
            raise RuntimeError("Unmatched status topic: " + topic)

        device_name = device_class.get_name_from_topic(topic)

        self.devices.add_device(device_class(device_name, self.mqtt))

    def _get_class(self, class_name):
        try:
            fpath = dirname(__file__) + "/device/{}.py".format(class_name)
            return getattr(imp.load_source(class_name, fpath), class_name)
        except IOError:
            raise ValueError("Trying to find device but no device file found.. ({}.py)".format(class_name))
        except AttributeError:
            msg = "Trying to find device but class '{class_name}' wasn't found in file ({class_name}.py)"
            raise ValueError(msg.format(class_name=class_name))
