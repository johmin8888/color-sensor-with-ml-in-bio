import os
import sys
import time
import traceback
import RPi.GPIO as GPIO
from modules.I2CLCD import I2CLCD
from modules.TCS3200 import TCS3200


# Hyperparameters
DATA_DIRECTORY = os.path.join("..", "data")
CALIBRATION_FILE = "calibration.txt"


# Define a function to load sensor calibration data
def load_calibration_data(calibration_data, data_dir):
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Join it with the relative path of your data
    data_path = os.path.join(current_dir, data_dir)

    # Define the calibration data path
    calibration_data_path = os.path.join(data_path, calibration_data)
    
    # Check if the data file exists
    if not os.path.exists(calibration_data_path):
        print(f"No calibration data found at: {os.path.abspath(calibration_data_path)}")
        return None, None

    # Load the global_min and global_max data
    try:
        with open(calibration_data_path, 'r') as file:
            lines = file.readlines()
            global_min = [float(val) for val in lines[0].split(":")[1].strip()[1:-1].split(", ")]
            global_max = [float(val) for val in lines[1].split(":")[1].strip()[1:-1].split(", ")]

        print(f"Calibration data loaded from: {os.path.abspath(calibration_data_path)}")
    except Exception as e:
        print(f"Calibration data load error occurred: {e}")
        return None, None

    return global_min, global_max


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

        global_min, global_max = load_calibration_data(CALIBRATION_FILE, DATA_DIRECTORY)
        print("Calibration data is ready.")
        time.sleep(1)

        print("Initialization done.")
        print("\n")
        lcd.text("Done.", line=1)
        lcd.text("Device is ready.", line=2)
        time.sleep(1)
        lcd.clear()

        while True:
            # Read color
            print("Reading color...")
            lcd.text("Reading color...", line=1)
            lcd.text("", line=2)
            rgb = sensor.read_color(global_min, global_max)
            print(f"RGB({rgb['RED']:3.3f}, {rgb['GREEN']:3.3f}, {rgb['BLUE']:3.3f})")

            # Convert RGB to HSL
            hsl = sensor.rgb_to_hsl(rgb['RED'], rgb['GREEN'], rgb['BLUE'])
            print(f"HSL({hsl[0]*360:3.3f}, {hsl[1]*100:3.3f}, {hsl[2]*100:3.3f})")
            print("\n")

            # Display
            lcd.text(f"RGB({int(rgb['RED']):3d},{int(rgb['GREEN']):3d},{int(rgb['BLUE']):3d})", line=1)
            lcd.text(f"HSL({int(hsl[0]*360):3d},{int(hsl[1]*100):3d},{int(hsl[2]*100):3d})", line=2)
            time.sleep(1) # refresh rate

    except KeyboardInterrupt:
        # Handle the Ctrl-C exception to gracefully exit the script
        print("\nKeyboard interrupted.")
        print("Program terminated by user.\n")

    except Exception as e:
        # Print out any other exceptions that might occur
        print(f"An error occurred: {e}\n")
        traceback.print_exc()

    finally:
        lcd.clear()
        lcd.backlight(True)
        lcd.clear()  # Clear the display before stopping
        sensor.led_off()
        GPIO.cleanup()
        time.sleep(1)
        exit(0)