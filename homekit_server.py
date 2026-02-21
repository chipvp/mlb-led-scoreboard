import logging
import threading
from pyhap.accessory import Accessory
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_LIGHTBULB


class BrightnessAccessory(Accessory):
    category = CATEGORY_LIGHTBULB

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        serv_light = self.add_preload_service("Lightbulb", chars=["On", "Brightness"])

        self.char_on = serv_light.configure_char("On", setter_callback=self.set_on)
        self.char_brightness = serv_light.configure_char("Brightness", setter_callback=self.set_brightness)

    def set_on(self, value):
        print(f"[HomeKit] Power {'ON' if value else 'OFF'}")  # Optional

    def set_brightness(self, value):
        import brightness_manager
        print(f"[HomeKit] Brightness set to {value}")
        brightness_manager.set_brightness(value)


def run_homekit_service():
    logging.basicConfig(level=logging.INFO)
    driver = AccessoryDriver(port=51826)

    accessory = BrightnessAccessory(driver, "MLB Scoreboard Brightness")
    driver.add_accessory(accessory)

    print("[HomeKit] Starting accessory server...")
    driver.start()


def start_homekit_background_thread():
    thread = threading.Thread(target=run_homekit_service, name="HomeKitThread", daemon=True)
    thread.start()
    print("[HomeKit] Background thread started.")

