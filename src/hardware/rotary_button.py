import RPi.GPIO as GPIO
import time

class RotaryButton:
    def __init__(self, pin, mode_manager):
        self.pin = pin
        self.mode_manager = mode_manager
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.pin, GPIO.FALLING, callback=self._pressed, bouncetime=200)

    def _pressed(self, channel):
        # Only trigger back when a menu is active
        if self.mode_manager.get_mode() in self.mode_manager.menu_modes:
            self.mode_manager.back()

    def cleanup(self):
        GPIO.remove_event_detect(self.pin)
        GPIO.cleanup(self.pin)
