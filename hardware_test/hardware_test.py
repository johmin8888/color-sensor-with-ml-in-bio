import sys
import time
from smbus2 import SMBus, i2c_msg
import RPi.GPIO as GPIO
import numpy as np
from filterpy.kalman import KalmanFilter


class I2CLCD:
    """1602LCD Screen"""
    def __init__(self, i2c_address=0x27, bus=1, display_size=(16, 2)):
        self.display_size = display_size
        self.address = i2c_address
        self.bus = SMBus(bus)
        self.display_function = 0x20  # 4-bit mode, 2-line, 5x7 format
        self.displaycontrol = 0x0C  # display on, cursor off, blink off
        self.displaymode = 0x06  # Entries increment automatically
        self.backlightval = 0x08  # Backlight ON
        self.line_offsets = [0x00, 0x40, 0x14, 0x54]
        self.displayed_text = ['' for _ in range(self.display_size[1])]
        self.enable_bit = 0x04  # Enable bit

        # Initialize display
        self.write_cmd(0x33)  # initialization
        self.write_cmd(0x32)  # set to 4-bit mode
        self.write_cmd(0x06)  # cursor direction
        self.write_cmd(0x0C)  # turn the display on
        self.write_cmd(0x28)  # 2 lines
        self.write_cmd(0x01)  # clear display
        time.sleep(0.0005)

    def strobe(self, data):
        self.bus.write_byte(self.address, data | self.enable_bit | self.backlightval)
        time.sleep(0.0001)
        self.bus.write_byte(self.address, ((data & ~self.enable_bit) | self.backlightval))
        time.sleep(0.0001)

    def write_four_bits(self, data):
        self.bus.write_byte(self.address, data | self.backlightval)
        self.strobe(data)

    # write a command to lcd
    def write_cmd(self, cmd, mode=0):
        self.write_four_bits(mode | (cmd & 0xF0))
        self.write_four_bits(mode | ((cmd << 4) & 0xF0))

    # write a character to lcd (or character rom) 0x09: backlight | RS=DR<
    def write_chr(self, charvalue, mode=1):
        self.write_four_bits(mode | (charvalue & 0xF0))
        self.write_four_bits(mode | ((charvalue << 4) & 0xF0))

    def _write_line(self, text, line):
        self.write_cmd(0x80 | self.line_offsets[line])  # set line offset
        for char in text:
            self.write_chr(ord(char))  # write char to display

    # put string function
    def text(self, text, line=1):
        if line < 1 or line > self.display_size[1]:
            raise ValueError("Line number out of bounds. Line numbers start from 1.")
        # Adjust the line index to 0-based
        line -= 1
        if text != self.displayed_text[line]:
            self.displayed_text[line] = text
            self._write_line(text.ljust(self.display_size[0]), line)

    # clear lcd and set to home
    def clear(self):
        self.write_cmd(0x01)
        time.sleep(0.005)
        self.write_cmd(0x02)
        time.sleep(0.005)

    def backlight(self, state=True):
        if state:
            self.backlightval = 0x08
        else:
            self.backlightval = 0x00
        self.write_cmd(0x00)  # Writing a command to update the backlight state


class TCS3200:
    """DFRobot Color Sensor (TCS3200)"""
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

        # Set frequency scaling (LH = 2%, HL = 20%, HH = 100%)
        GPIO.output(self.S0, GPIO.LOW)
        GPIO.output(self.S1, GPIO.HIGH)
        return

    def led_on(self):  # Method to turn LED on
        GPIO.output(self.LED, GPIO.HIGH)
        return

    def led_off(self):  # Method to turn LED off
        GPIO.output(self.LED, GPIO.LOW)
        return

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
    
    def read_color_freq(self, num_samples=10):
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
                start_time = time.time()
                for impulse_count in range(100):
                    GPIO.wait_for_edge(self.OUT, GPIO.FALLING)
                duration = time.time() - start_time
                frequency = 100 / duration

                freq_array.append(frequency)

            # Apply a filter to freq_array to get the final frequency
            color_freq[color] = self.apply_filter(freq_array)

        return color_freq
    

if __name__ == "__main__":
    # Main loop prompt
    print(f"{sys.argv[0]} is running.")
    print("="*30)
    print("This is a program to test hardwares attached to the Raspberry Pi 4B.")
    print("Hardware: \n\tDFRobot Color Sensor (TCS3200) \n\t1602LCD Screen")
    print("="*30)

    try:
        # Initialize
        lcd = I2CLCD(i2c_address=0x27, display_size=(16, 2))
        lcd.backlight(True)
        lcd.clear()
        lcd.text("Hello World", line=1)
        print("LCD screen is ready.")
        time.sleep(1)
        
        sensor = TCS3200(S0=5, S1=6, S2=23, S3=24, OUT=25, LED=18)
        sensor.led_on()
        sensor.read_color_freq()
        print("Sensor is ready.")
        time.sleep(1)

        print("Initialization done.")

        while True:
            color_freq = sensor.read_color_freq()
            print(f"Raw Freqeuncies: {color_freq}")
            lcd.text(f"({int(color_freq['RED']):4d},{int(color_freq['GREEN']):4d},{int(color_freq['BLUE']):4d})")

    except KeyboardInterrupt:
        # Handle the Ctrl-C exception to gracefully exit the script
        print("\nKeyboard interrupted.")

    except Exception as e:
        # Print out any other exceptions that might occur
        print(f"An error occurred: {e}")

    finally:
        print("\nProgram terminated by user.")
        lcd.clear()
        lcd.backlight(True)
        lcd.clear()  # Clear the display before stopping
        sensor.led_off()
        GPIO.cleanup()
        time.sleep(1)
        exit(0)