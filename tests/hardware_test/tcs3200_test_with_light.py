import sys
import time
import RPi.GPIO as GPIO

class TCS3200:
    # Define GPIO pins
    def __init__(self, S0, S1, S2, S3, OUT, LED):
        self.S0 = S0
        self.S1 = S1
        self.S2 = S2
        self.S3 = S3
        self.OUT = OUT
        self.LED = LED  # Added LED pin
        self.setup_gpio()

    def setup_gpio(self):
        # Set up GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.S0, GPIO.OUT)
        GPIO.setup(self.S1, GPIO.OUT)
        GPIO.setup(self.S2, GPIO.OUT)
        GPIO.setup(self.S3, GPIO.OUT)
        GPIO.setup(self.OUT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.LED, GPIO.OUT)  # Setup LED as output

        # Set frequency scaling to 20%
        GPIO.output(self.S0, GPIO.LOW)
        GPIO.output(self.S1, GPIO.HIGH)
        return

    def led_on(self):  # Method to turn LED on
        GPIO.output(self.LED, GPIO.HIGH)
        return

    def led_off(self):  # Method to turn LED off
        GPIO.output(self.LED, GPIO.LOW)
        return

    def read_color(self):
        colors = ['RED', 'GREEN', 'BLUE']
        filters = [(GPIO.LOW, GPIO.LOW), (GPIO.HIGH, GPIO.HIGH), (GPIO.LOW, GPIO.HIGH)]
        color_freq = {}

        for color, (S2_state, S3_state) in zip(colors, filters):
            GPIO.output(self.S2, S2_state)
            GPIO.output(self.S3, S3_state)
            start_time = time.time()
            for impulse_count in range(100):
                GPIO.wait_for_edge(self.OUT, GPIO.FALLING)
            duration = time.time() - start_time
            frequency = 100 / duration
            color_freq[color] = frequency

        # Normalize frequency values for RGB to [0, 255]
        max_freq = max(color_freq.values())
        for color in colors:
            color_freq[color] = int((color_freq[color] / max_freq) * 255)

        time.sleep(1)   # Wait for a second before repeating the loop
        return color_freq

if __name__ == '__main__':
    print(f"{sys.argv[0]} is running.")
    try:
        sensor = TCS3200(S0=5, S1=6, S2=23, S3=24, OUT=25, LED=18)  # Added LED pin number here
        print("GPIO pins are setup.")
        sensor.led_on()  # Turn on LED before reading colors
        while True:
            color_freq = sensor.read_color()
            print(f"RGB({color_freq['RED']}, {color_freq['GREEN']}, {color_freq['BLUE']})")
    except KeyboardInterrupt:
        print("Keyboard interrupted")
        sensor.led_off()  # Turn off LED before cleaning up GPIO and exiting
        GPIO.cleanup()
        time.sleep(1)
        quit()