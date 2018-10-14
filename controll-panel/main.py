from time import sleep
import logging
import logging.handlers

from interface.interface_panel import InterfacePanel
from interface.interface_mapping import InterfacePanelMapping
from mqtt.connection import MQTT
from devices.devices import DeviceManager
from devices.explore import DeviceExplorer


logger = logging.getLogger('hallway-GUI')
logger.setLevel(logging.DEBUG)

log_file = '/'.join(["", "var", "log", "hallway-gui", "logs"])
file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=1e5, backupCount=2)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(logging.StreamHandler())


class MainController:

    def __init__(self):
        interface = InterfacePanel()
        interface.add_button('light', self.toggle_light, InterfacePanelMapping.Buttons['bottom-left'])
        self.interface = interface

        mqtt = MQTT(server='192.168.0.80')
        mqtt.connect()
        self.mqtt = mqtt

        devices = DeviceManager(mqtt)
        explorer = DeviceExplorer(mqtt, devices)
        explorer.find_class('IOUnit')
        self.devices = devices
        self.explorer = explorer

    def toggle_light(self, btn_name):
        try:
            device = self.devices.get_device('hall', 'IOUnit')
        except KeyError:
            logger.error('Hall device in not available. Failed to set new value!')
            return
        s0 = device.io_state['roof']['actual']
        s = not s0
        device.set_io('roof', state=s)
        logger.debug("Set new state on hall-light {}->{}".format(s0, s))

    def run(self):
        while(True):
            sleep(1e6)


if __name__ == "__main__":
    MainController().run()
