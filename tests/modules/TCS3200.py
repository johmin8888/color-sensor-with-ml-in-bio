import time
import RPi.GPIO as GPIO
import numpy as np
from filterpy.kalman import KalmanFilter


class TCS3200:
    # Define GPIO pins
    def __init__(self, S0, S1, S2, S3, OUT, LED, scaling=0.20, led_power=True):
        # Setup numbers
        self.S0 = S0    # scaling pin
        self.S1 = S1    # scaling pin
        self.S2 = S2    # color filter pin
        self.S3 = S3    # color filter pin
        self.OUT = OUT  # output pin
        self.LED = LED  # LED pin

        # Control sensor
        self.setup_gpio()
        self.scale_frequency(scaling)
        if led_power == True:
            self.led_on()
        else:
            self.led_off()


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
    
    # Method to read raw frequencies of color through red, green, blue, and clear filters
    def read_color_freq(self, num_samples=10, impulse_counts=100):
        # Record the start time
        start_time = time.time()

        colors = ['RED', 'GREEN', 'BLUE', 'CLEAR']
        filters = [(GPIO.LOW, GPIO.LOW), (GPIO.HIGH, GPIO.HIGH), (GPIO.LOW, GPIO.HIGH), (GPIO.HIGH, GPIO.LOW)]
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
                for impulse_count in range(impulse_counts):
                    GPIO.wait_for_edge(self.OUT, GPIO.FALLING)
                duration = time.time() - start_time_sample
                frequency = 100 / duration

                freq_array.append(frequency)

            # Apply a filter to freq_array to get the final frequency
            color_freq[color] = self.apply_filter(freq_array)

        return color_freq

    # Gamma Correction
    def gamma_correction(self, channel, gamma=1):
        return 255 * (channel / 255.0) ** (1/gamma)

    # Method to read color in RGB format calibrated with the data
    def read_color(self, global_min, global_max, num_samples=10, impulse_counts=100, gamma=1):
        # Get the raw frequency values
        freq = self.read_color_freq(num_samples, impulse_counts)

        # Normalize frequency values for RGB to [0, 255]
        colors = ['RED', 'GREEN', 'BLUE']
        for i, color in enumerate(colors):
            # Normalize to [0, 255] range
            if freq[color] < global_min[i]:
                freq[color] = 0
            elif freq[color] > global_max[i]:
                freq[color] = 255
            else:
                freq[color] = (freq[color] - global_min[i]) / (global_max[i] - global_min[i]) * 255

        #Apply Gamma Correction
        rgb = {}
        for color in colors:
            rgb[color] = self.gamma_correction(freq[color], gamma)
        freq = rgb

        return freq

class convert_color:
    # Define GPIO pins
    def __init__(self):
        self.r = 0
        self.g = 0
        self.b = 0

    # Method to convert RGB to HSL
    def rgb_to_hsl(self, r, g, b):
        # Normalize RGB values
        r /= 255
        g /= 255
        b /= 255
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        l = (max_val + min_val) / 2

        if max_val == min_val:
            h = s = 0  # achromatic
        else:
            diff = max_val - min_val
            s = diff / (2 - max_val - min_val) if l > 0.5 else diff / (max_val + min_val)
            if max_val == r:
                h = (g - b) / diff + (6 if g < b else 0)
            elif max_val == g:
                h = (b - r) / diff + 2
            else:
                h = (r - g) / diff + 4
            h /= 6

        return h, s, l

    # Method to convert RGB to HSV
    def rgb_to_hsv(self, r, g, b):
        r /= 255.0
        g /= 255.0
        b /= 255.0
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        diff = max_val - min_val
        h = 0

        if diff != 0:
            if max_val == r:
                h = (60 * ((g-b)/diff) + 360) % 360
            elif max_val == g:
                h = (60 * ((b-r)/diff) + 120) % 360
            elif max_val == b:
                h = (60 * ((r-g)/diff) + 240) % 360
        s = 0 if max_val == 0 else (diff / max_val)
        v = max_val

        return h, s, v

    # Method to convert RGB to CMYK
    def rgb_to_cmyk(self, r, g, b):
        r = r / 255.0
        g = g / 255.0
        b = b / 255.0

        k = 1 - max(r, g, b)
        c = 0 if k == 1 else (1 - r - k) / (1 - k)
        m = 0 if k == 1 else (1 - g - k) / (1 - k)
        y = 0 if k == 1 else (1 - b - k) / (1 - k)

        return c, m, y, k

    # Method to convert RGB to CIELAB
    def rgb_to_lab(self, r, g, b):
        # Gamma correction
        r = r / 255.0
        g = g / 255.0
        b = b / 255.0
        for i, val in enumerate([r, g, b]):
            if val <= 0.04045:
                val /= 12.92
            else:
                val = ((val + 0.055) / 1.055) ** 2.4
            [r, g, b][i] = val

        # RGB to CIEXYZ
        X = 0.4124 * r + 0.3576 * g + 0.1805 * b
        Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
        Z = 0.0193 * r + 0.1192 * g + 0.9505 * b

        # Normalize for D65 illuminant
        X /= 0.95047
        Y /= 1.00000
        Z /= 1.08883

        XYZ = [X, Y, Z]
        for i, val in enumerate(XYZ):
            if val > 0.008856:
                val = val ** (1/3)
            else:
                val = (7.787 * val) + (16/116)
            XYZ[i] = val

        L = (116.0 * XYZ[1]) - 16.0
        a = 500.0 * (XYZ[0] - XYZ[1])
        b = 200.0 * (XYZ[1] - XYZ[2])

        return L, a, b