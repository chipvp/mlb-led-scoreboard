import logging
import threading
from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_LIGHTBULB, CATEGORY_SWITCH


class BrightnessAccessory(Accessory):
    category = CATEGORY_LIGHTBULB

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        serv_light = self.add_preload_service('Lightbulb', chars=['On', 'Brightness'])

        self.char_on = serv_light.configure_char('On', setter_callback=self.set_on)
        self.char_brightness = serv_light.configure_char('Brightness', setter_callback=self.set_brightness)

        self._last_brightness = 100

    def set_on(self, value):
        import brightness_manager
        if value:
            print(f'[HomeKit] Power ON — restoring brightness to {self._last_brightness}')
            brightness_manager.power_on(self._last_brightness)
        else:
            self._last_brightness = brightness_manager.get_brightness()
            print(f'[HomeKit] Power OFF — clearing matrix')
            brightness_manager.power_off()

    def set_brightness(self, value):
        import brightness_manager
        print(f'[HomeKit] Brightness set to {value}')
        self._last_brightness = value
        brightness_manager.set_brightness(value)


class SpoilerModeAccessory(Accessory):
    category = CATEGORY_SWITCH

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        serv = self.add_preload_service('Switch')
        self.char_on = serv.configure_char('On', setter_callback=self.set_on)

    def set_on(self, value):
        import spoiler_mode_manager
        print(f'[HomeKit] Spoiler mode set to {value}')
        spoiler_mode_manager.set_spoiler_mode(value)


def _mdns_keepalive(driver, interval=20):
    """Re-announce mDNS every interval seconds to keep Unifi's reflector cache alive."""
    import time
    while True:
        time.sleep(interval)
        try:
            driver.update_advertisement()
        except Exception:
            pass


def run_homekit_service():
    logging.basicConfig(level=logging.INFO)
    try:
        driver = AccessoryDriver(port=51826, pincode=b"031-45-154")
        bridge = Bridge(driver, 'MLB Scoreboard')
        bridge.add_accessory(BrightnessAccessory(driver, 'Brightness'))
        bridge.add_accessory(SpoilerModeAccessory(driver, 'Spoiler Free'))
        driver.add_accessory(bridge)
        keepalive = threading.Thread(target=_mdns_keepalive, args=(driver,), daemon=True)
        keepalive.start()
        print('[HomeKit] Starting accessory server...')
        driver.start()
    except Exception:
        logging.exception('[HomeKit] Accessory server failed — HomeKit control unavailable')


def start_homekit_background_thread():
    thread = threading.Thread(target=run_homekit_service, name='HomeKitThread', daemon=True)
    thread.start()
    print('[HomeKit] Background thread started.')
