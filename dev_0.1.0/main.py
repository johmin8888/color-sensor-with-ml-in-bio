import os
import sys
import time
import RPi.GPIO as GPIO
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib
from I2CLCD import I2CLCD
from TCS3200 import TCS3200


# Hyperparameters
DATA_DIRECTORY = "data"
MODEL_FILE = "random_forest_hsl.joblib"
CALIBRATION_FILE = "calibration.txt"


# Define a function to load pre-trained model
def load_model(model_name, data_dir):
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Join it with the relative path of your data
    data_path = os.path.join(current_dir, data_dir)

    # Define the model path
    model_path = os.path.join(data_path, model_name)
    
    # Check if the model exists
    if not os.path.exists(model_path):
        print(f"No model found at: {os.path.abspath(model_path)}")
        return None

    # Load the model
    try:
        model = joblib.load(model_path)
        print(f"Model loaded from: {os.path.abspath(model_path)}")
    except Exception as e:
        print("Model load error occurred: {e}")

    return model

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

    # Load the data
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

        sensor = TCS3200(S0=5, S1=6, S2=23, S3=24, OUT=25, LED=18, scaling=0.20)
        sensor.led_on()
        sensor.read_color_freq() # Booting sensor with a read
        print("Sensor is ready.")
        time.sleep(1)

        model = load_model(MODEL_FILE, DATA_DIRECTORY)
        print("Model is ready.")
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
            rgb = sensor.read_color(global_min, global_max)
            print(f"RGB({rgb['RED']:3.3f}, {rgb['GREEN']:3.3f}, {rgb['BLUE']:3.3f})")

            # Convert RGB to HSL
            hsl = sensor.rgb_to_hsl(rgb['RED'], rgb['GREEN'], rgb['BLUE'])
            print(f"HSL({hsl[0]*360:3.3f}, {hsl[1]*100:3.3f}, {hsl[2]*100:3.3f})")

            # Predict the value
            predicted_value = model.predict(np.array(hsl).reshape(1, -1))
            print(f"Value: {predicted_value}")
            print("\n")

            # Display
            lcd.text(f"RGB({int(rgb['RED']):3d},{int(rgb['GREEN']):3d},{int(rgb['BLUE']):3d})", line=1)
            lcd.text(f"Value: {predicted_value[0]:.3f}", line=2)
            time.sleep(3) # refresh rate

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