import os
import sys
import time
import RPi.GPIO as GPIO
from I2CLCD import I2CLCD
from TCS3200 import TCS3200


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

        sensor = TCS3200(S0=5, S1=6, S2=23, S3=24, OUT=25, LED=18, scaling=0.20)
        #sensor.led_on()
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
            color_freq = sensor.read_color_freq()
            print(f"Raw Freqeuncies: {color_freq}")
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