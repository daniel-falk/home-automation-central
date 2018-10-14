from threading import Lock


class DeviceManager:

    def __init__(self, mqtt):
        self.mqtt = mqtt

        self.device_table = dict()
        self.table_lock = Lock()

    # TODO: Split into domains so we can allow same name on different kind of devices
    def add_device(self, device):
        name = device.get_name()
        self.table_lock.acquire()
        try:
            if name not in self.device_table.keys():
                print("Added device '{}' of type '{}'".format(name, device.get_type()))
                self.device_table[name] = device
                device.start_update()
        finally:
            self.table_lock.release()

    def get_device(self, name, device_type):
        self.table_lock.acquire()
        try:
            for _name, _type in [
                    (_name, _props.get_type()) for _name, _props
                    in self.device_table.iteritems()
                    if _name == name]:
                if _type == device_type:
                    return self.device_table[_name]
        finally:
            self.table_lock.release()

        return None
