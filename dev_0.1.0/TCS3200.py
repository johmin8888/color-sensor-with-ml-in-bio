import time
import RPi.GPIO as GPIO
import numpy as np
from filterpy.kalman import KalmanFilter


class TCS3200:
    # Define GPIO pins
    def __init__(self, S0, S1, S2, S3, OUT, LED, scaling=0.02):
        self.S0 = S0    # scaling pin
        self.S1 = S1    # scaling pin
        self.S2 = S2    # color filter pin
        self.S3 = S3    # color filter pin
        self.OUT = OUT  # output pin
        self.LED = LED  # LED pin
        self.setup_gpio()
        self.scale_frequency(scaling)

    # GPIO setups
    def setup_gpio(self):
        # Set up GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.S0, GPIO.OUT)
        GPIO.setup(self.S1, GPIO.OUT)
        GPIO.setup(self.S2, GPIO.OUT)
        GPIO.setup(self.S3, GPIO.OUT)
        GPIO.setup(self.OUT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.LED, GPIO.OUT)  # Setup LED as output

    # Method to choose frequency scaling factor
    def scale_frequency(self, scaling):
        # Set frequency scaling (LH = 0.02, HL = 0.20, HH = 1.00)
        if scaling == 0.02: # appropriate when LED is turned on
            GPIO.output(self.S0, GPIO.LOW)
            GPIO.output(self.S1, GPIO.HIGH)
            print("TCS3200 sensor is scaled to 2%.")
        elif scaling == 0.20: # appropriate when there is ambient light
            GPIO.output(self.S0, GPIO.HIGH)
            GPIO.output(self.S1, GPIO.LOW)
            print("TCS3200 sensor is scaled to 20%.")
        elif scaling == 1.00: # appropriate when enclosed without light
            GPIO.output(self.S0, GPIO.HIGH)
            GPIO.output(self.S1, GPIO.HIGH)
            print("TCS3200 sensor is scaled to 100%.")
        else:
            raise(f"Scaling to {scaling} is not available. Please select among 0.02, 0.20, or 1.00.")
        return

    # Method to turn LED on
    def led_on(self):
        GPIO.output(self.LED, GPIO.HIGH)
        return

    # Method to turn LED off
    def led_off(self):
        GPIO.output(self.LED, GPIO.LOW)
        return

    # Method to apply statistic model to return precise value through several iterations
    def apply_filter(self, arr):
        # Initialize Kalman filter
        kf = KalmanFilter(dim_x=1, dim_z=1)
        kf.x = np.array([arr[0]]) # initial state
        kf.F = np.array([[1]])    # state transition matrix
        kf.H = np.array([[1]])    # measurement function
        kf.P *= 1000.             # covariance matrix
        kf.R = 5                  # state uncertainty
        for i in range(1, len(arr)):
            kf.predict()
            kf.update(arr[i])
        return kf.x[0]
    
    # Method to read raw frequencies of color through red, green, and blue filters
    def read_color_freq(self, num_samples=10):
        # Record the start time
        start_time = time.time()

        colors = ['RED', 'GREEN', 'BLUE']
        filters = [(GPIO.LOW, GPIO.LOW), (GPIO.HIGH, GPIO.HIGH), (GPIO.LOW, GPIO.HIGH)]
        color_freq = {}

        for color, (S2_state, S3_state) in zip(colors, filters):
            GPIO.output(self.S2, S2_state)
            GPIO.output(self.S3, S3_state)
            
            # Array to store multiple samples
            freq_array = []

            # Taking num_samples samples and averaging
            for j in range(num_samples):
                # If reading color frequencies took more than 30 seconds, raise an error
                if time.time() - start_time > 30:
                    raise Exception("Ambient light is not enough to detect the color.")

                start_time_sample = time.time()
                for impulse_count in range(100):
                    GPIO.wait_for_edge(self.OUT, GPIO.FALLING)
                duration = time.time() - start_time_sample
                frequency = 100 / duration

                freq_array.append(frequency)

            # Apply a filter to freq_array to get the final frequency
            color_freq[color] = self.apply_filter(freq_array)

        return color_freq
        
    # Method to read color in RGB format calibrated with the data
    def read_color(self, global_min, global_max):
        # Get the raw frequency values
        raw_freq = self.read_color_freq()

        # Normalize frequency values for RGB to [0, 255]
        colors = ['RED', 'GREEN', 'BLUE']
        for i, color in enumerate(colors):
            # If raw frequency is less than global_min, set to 0
            if raw_freq[color] < global_min[i]:
                raw_freq[color] = 0
            # If raw frequency is more than global_max, set to 255
            elif raw_freq[color] > global_max[i]:
                raw_freq[color] = 255
            else:
                # Convert frequency to a value in the range [0, 255]
                raw_freq[color] = (raw_freq[color] - global_min[i]) / (global_max[i] - global_min[i]) * 255

        return raw_freq

    # Method to convert RGB to HSL
    def rgb_to_hsl(self, r, g, b):
        # Normalize RGB values
        r /= 255
        g /= 255
        b /= 255
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        diff = max_val - min_val
        h = s = l = (max_val + min_val) / 2

        if max_val == min_val:
            h = s = 0  # achromatic
        else:
            # saturation calculation
            if l > 0.5:
                s = diff / (2 - max_val - min_val)
            else:
                s = diff / (max_val + min_val)
            
            # hue calculation
            if max_val == r:
                h = (g - b) / diff + (g < b) * 6
            elif max_val == g:
                h = (b - r) / diff + 2
            else:
                h = (r - g) / diff + 4

            h /= 6

        return h, s, l
    
    # Method to convert RGB to CMYK
    def rgb_to_cmyk(self, r, g, b):
        # Normalize RGB values
        r = r / 255.0
        g = g / 255.0
        b = b / 255.0

        # Convert RGB to CMYK
        # Black
        k = 1 - max(r, g, b)

        # Cyan
        c = (1 - r - k) / (1 - k) if k != 1 else 0

        # Magenta
        m = (1 - g - k) / (1 - k) if k != 1 else 0

        # Yellow
        y = (1 - b - k) / (1 - k) if k != 1 else 0

        # Return CMYK color
        return c, m, y, k