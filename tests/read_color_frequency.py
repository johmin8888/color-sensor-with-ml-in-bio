import os
import sys
import time
import RPi.GPIO as GPIO
from modules.I2CLCD import I2CLCD
from modules.TCS3200 import TCS3200


if __name__ == "__main__":
    print("\n"+"="*50)
    print(f"{sys.argv[0]} is running.")
    print("="*50+"\n")

    try:
        # Initialize
        lcd = I2CLCD(i2c_address=0x27, display_size=(16, 2))
        lcd.backlight(True)
        lcd.clear()
        lcd.text("Initializing...", line=1)
        print("LCD screen is ready.")
        time.sleep(1)

        SCALING = input("Select scaling option (0.02, 0.20, 1.00):\t")
        LED_POWER = input("LED power option (True/False):\t")
        sensor = TCS3200(S0=5, S1=6, S2=23, S3=24, OUT=25, LED=18, scaling=float(SCALING), led_power=LED_POWER)
        sensor.read_color_freq() # Booting sensor with a read
        print("Sensor is ready.")
        time.sleep(1)

        print("Initialization done.")
        print("\n")
        lcd.text("Done.", line=1)
        lcd.text("Device is ready.", line=2)
        time.sleep(1)
        lcd.clear()

        while True:
            color_freq = sensor.read_color_freq(num_samples=10, impulse_counts=100)
            print(f"RGBC-Frequency: (R: {color_freq['RED']:3.3f}, G: {color_freq['GREEN']:3.3f}, B: {color_freq['BLUE']:3.3f}, C: {color_freq['CLEAR']:3.3f})")
            rgb_ratios = [color_freq['RED']/color_freq['CLEAR'],
                        color_freq['GREEN']/color_freq['CLEAR'],
                        color_freq['BLUE']/color_freq['CLEAR'],
                        (color_freq['RED'] + color_freq['GREEN'] + color_freq['BLUE']) / color_freq['CLEAR']]
            print(f"RGB/Clear: (R/C: {rgb_ratios[0]:3.3f}, G/C: {rgb_ratios[1]:3.3f}, B/C: {rgb_ratios[2]:3.3f}, RGB/C: {rgb_ratios[3]:3.3f})")
            lcd.text("Raw Frequencies:", line=1)
            lcd.text(f"({int(color_freq['RED']):4d},{int(color_freq['GREEN']):4d},{int(color_freq['BLUE']):4d})", line=2)

    except KeyboardInterrupt:
        # Handle the Ctrl-C exception to gracefully exit the script
        print("\nKeyboard interrupted.")
        print("Program terminated by user.\n")

    except Exception as e:
        # Print out any other exceptions that might occur
        print(f"An error occurred: {e}\n")

    finally:
        lcd.clear()
        lcd.backlight(True)
        lcd.clear()  # Clear the display before stopping
        sensor.led_off()
        GPIO.cleanup()
        time.sleep(1)
        exit(0)