import os
import sys
import time
import traceback
import RPi.GPIO as GPIO
import numpy as np
import pandas as pd
import joblib
from modules.I2CLCD import I2CLCD
from modules.TCS3200 import TCS3200, convert_color


# Hyperparameters
DATA_DIRECTORY = os.path.join("..", "data")
CALIBRATION_FILE = "calibration.txt"
PREDICTION_FILE = "prediction_albumin_Bradford-200uL-2.csv"


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

# Define a function to load pre-trained model
def load_model(model_name, data_dir):
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Join it with the relative path of your data
    data_path = os.path.join(current_dir, data_dir)

    # Define the model path
    model_path = os.path.join(data_path, "models", model_name)
    
    # Check if the model exists
    if not os.path.exists(model_path):
        raise(f"No model found at: {os.path.abspath(model_path)}")

    # Load the model
    try:
        model = joblib.load(model_path)
        print(f"Model loaded from: {os.path.abspath(model_path)}")
    except Exception as e:
        print("Model load error occurred: {e}")

    return model

# Define a function to select color conversion
def convert_color_space(rgb, color_space_name='rgb'):
    r, g, b = [rgb['RED'], rgb['GREEN'], rgb['BLUE']]
    converter = convert_color()  # Instantiate the convert_color class.

    try:
        # Convert color space
        if color_space_name == 'rgb':
            return r, g, b
        elif color_space_name == 'cmyk':
            return converter.rgb_to_cmyk(r, g, b)
        elif color_space_name == 'hsl':
            return converter.rgb_to_hsl(r, g, b)
        elif color_space_name == 'hsv':
            return converter.rgb_to_hsv(r, g, b)
        elif color_space_name == 'lab':
            return converter.rgb_to_lab(r, g, b)
    
    except Exception as e:
        print(f"Conversion of color error occurred: {e}")
        return

# Define a function to measure color
def measure_color(measurement_count=5, deviation=3):
    global index

    print("\nReading color...")
    lcd.text("Reading color...", line=1)

    # Collect 5 measurements
    rgb_freq_list = []
    clear_freq_list = []  # List to store clear frequency
    rgb_list = []

    while len(rgb_list) < measurement_count:
        lcd.text(f"{index:3d}: |{'#' * len(rgb_list)}{' ' * (measurement_count - len(rgb_list))}|", line=2)

        rgb_freq = sensor.read_color_freq()
        clear_freq = rgb_freq['CLEAR']  # Extracting clear frequency from the RGB-frequency data
        rgbc = sensor.read_color(global_min, global_max)
        rgb = {k: rgbc[k] for k in ['RED', 'GREEN', 'BLUE']}
        print(f"RGB-frequency({rgb_freq['RED']:3.3f}, {rgb_freq['GREEN']:3.3f}, {rgb_freq['BLUE']:3.3f}, CLEAR: {clear_freq:3.3f})")
        print(f"RGB({rgb['RED']:3.3f}, {rgb['GREEN']:3.3f}, {rgb['BLUE']:3.3f})")
        lcd.text(f"RGB({int(rgb['RED']):3d},{int(rgb['GREEN']):3d},{int(rgb['BLUE']):3d})", line=1)

        # Add to list
        rgb_list.append(rgb)
        rgb_freq_list.append(rgb_freq)
        clear_freq_list.append(clear_freq)  # Append clear frequency
        time.sleep(0.3)

        if len(rgb_list) > 1 and max(abs(rgb_list[-1][key] - rgb_list[-2][key]) for key in rgb_list[-1]) > deviation:
            # If deviation is more than 3, clear the list and start over
            rgb_list = []
            rgb_freq_list = []
            clear_freq_list = []  # Clear the clear_freq_list

    # Calculate the average RGB, RGB-frequency, and Clear-frequency values
    avg_rgb = {key: sum(item[key] for item in rgb_list) / len(rgb_list) for key in rgb_list[0].keys()}
    avg_rgb_freq = {key: sum(item[key] for item in rgb_freq_list) / len(rgb_freq_list) for key in rgb_freq_list[0].keys()}
    avg_clear_freq = sum(clear_freq_list) / len(clear_freq_list)  # Calculate average clear frequency

    return avg_rgb, avg_rgb_freq, avg_clear_freq  # Return avg_clear_freq as well

# Define a function to prompt for selection of model
def select_model():
    model_names = ['Random Forest', 'Gradient Boosting', 'SVM', 'MLP']
    color_space_names = ['RGB', 'CMYK', 'HSL', 'HSV', 'LAB']

    print(f"\nSelect model:\t{model_names}")
    lcd.text("Select model.", line=1)
    user_input = input("Type name of the model:\t")
    model_name = user_input.replace(" ", "_").lower()
    
    print(f"Select color space: \t{color_space_names}")
    lcd.text("Select color", line=1)
    user_input = input("Type name of the color space: \t")
    color_space_name = user_input.lower()

    model_name = f'{model_name}_{color_space_name}.joblib'
    return model_name, color_space_name

# Define a function to save the prediction data
def save_data(dataframe, filename, data_dir):
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Join it with the relative path of your data
    data_path = os.path.join(current_dir, data_dir)

    # Define the prediction data path
    prediction_data_path = os.path.join(data_path, filename)

    if os.path.exists(prediction_data_path):
        print(f"\nA file named {filename} already exists in the data directory.\n")
        print("Select an option:")
        print("\t1. Append data to the existing file. Type (a/append).")
        print("\t2. Save data in a new file. Type (n/new/new_file).")
        print("\t3. Overwrite the existing file. Type (o/overwrite).")
        print("\t4. Delete current data frame. Type(d/delete).")
        print("\n")
        option = input("\nEnter your option: ")
        print("\n")

        if option.lower() in ['a', 'append']:
            try:
                dataframe.to_csv(prediction_data_path, mode='a', header=False, index=False)
                print(f"Data appended at: {os.path.abspath(prediction_data_path)}")
            except Exception as e:
                print(f"Data append error occurred: {e}")
                return
        elif option.lower() in ['n', 'new', 'new_file']:
            new_filename = input("Enter the new filename: ")
            new_data_path = os.path.join(data_path, new_filename)
            try:
                dataframe.to_csv(new_data_path, index=False)
                print(f"Data saved at: {os.path.abspath(new_data_path)}")
            except Exception as e:
                print(f"Data save error occurred: {e}")
                return
        elif option.lower() in ['o', 'overwrite']:
            try:
                dataframe.to_csv(prediction_data_path, index=False)
                print(f"Data overwritten at: {os.path.abspath(prediction_data_path)}")
            except Exception as e:
                print(f"Data overwrite error occurred: {e}")
                return
        elif option.lower() in ['d', 'delete']:
            print("Data not saved.")
            return
        else:
            print("Invalid option. Data not saved.")
            return save_data(dataframe, filename, data_dir)
    else:
        # Save the data in a new file if the file does not exist
        try:
            dataframe.to_csv(prediction_data_path, index=False)
            print(f"Data saved at: {os.path.abspath(prediction_data_path)}")
        except Exception as e:
            print(f"Data save error occurred: {e}")
            return
    return

def measurement_prompt(avg_rgb, avg_rgb_freq, avg_clear_freq, predicted_label):
    global prediction_data

    # Ask for label
    lcd.text(f"Pred: {predicted_label[0]:3.3f}", line=1)
    lcd.text(f"Measurement: {index:3d}", line=2)
    print("\nType (n/no/none/s/save) to finish the measurement and to go save options.")
    print("Type (r/re/redo) to measure again.")
    print(f"Type name of the predicted label ({predicted_label[0]}) and continue to the next measurement.\n")
    user_input = input(f"\tMeasurement {index}: Type name of label: ")
    print("\n")

    if user_input.lower() in ['r', 're', 'redo']:
        avg_rgb, avg_rgb_freq, avg_clear_freq = measure_color()
        color = convert_color_space(avg_rgb, color_space_name)
        prediction = model.predict(np.array(color).reshape(1, -1))
        return measurement_prompt(avg_rgb, avg_rgb_freq, avg_clear_freq, prediction)

    elif user_input.lower() in ['n', 'no', 'none', 's', 'save']:
        save_data(prediction_data, PREDICTION_FILE, DATA_DIRECTORY)
        print("\n")
        return False

    elif user_input:  # If user presses enter
        # Add the predicted_label to DataFrame
        new_data = pd.DataFrame({
            "Label_Name": str(user_input),
            "Red_Frequency": [avg_rgb_freq['RED']],
            "Green_Frequency": [avg_rgb_freq['GREEN']],
            "Blue_Frequency": [avg_rgb_freq['BLUE']],
            "Clear_Frequency": [avg_clear_freq],  # Add clear frequency data
            "Red": [avg_rgb['RED']],
            "Green": [avg_rgb['GREEN']],
            "Blue": [avg_rgb['BLUE']],
            "Predicted_Label": [predicted_label[0]]
        })
        prediction_data = pd.concat([prediction_data, new_data])
        return True
    else:

        print("\nInvalid input.")
        return measurement_prompt(avg_rgb, avg_rgb_freq, avg_clear_freq, predicted_label)


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

        sensor = TCS3200(S0=5, S1=6, S2=23, S3=24, OUT=25, LED=18, scaling=0.20, led_power=False)
        sensor.read_color_freq() # Booting sensor with a read
        print("Sensor is ready.")
        time.sleep(1)

        global_min, global_max = load_calibration_data(CALIBRATION_FILE, DATA_DIRECTORY)
        print("Calibration data is ready.")
        time.sleep(1)

        model_name, color_space_name = select_model()
        model = load_model(model_name, DATA_DIRECTORY)

        # Initialize parameters
        prediction_data = pd.DataFrame(columns=["Label_Name", "Red_Frequency", "Green_Frequency", "Blue_Frequency", "Clear_Frequency", "Red", "Green", "Blue", "Predicted_Label"])
        index = 0
        loop = True # main loop

        print("Initialization done.")
        print("\n")
        lcd.text("Done.", line=1)
        lcd.text("Device is ready.", line=2)
        time.sleep(1)
        lcd.clear()

        while loop == True:
            index += 1

            avg_rgb, avg_rgb_freq, avg_clear_freq = measure_color()  # Adjusted the unpacking here
            color = convert_color_space(avg_rgb, color_space_name)
            prediction = model.predict(np.array(color).reshape(1, -1))
            loop = measurement_prompt(avg_rgb, avg_rgb_freq, avg_clear_freq, prediction)

    except KeyboardInterrupt:
        # Handle the Ctrl-C exception to gracefully exit the script
        save_data(prediction_data, PREDICTION_FILE, DATA_DIRECTORY) # checkpointing
        print("\nKeyboard interrupted.")
        print("Program terminated by user.\n")

    except Exception as e:
        # Print out any other exceptions that might occur
        print(f"An error occurred: {e}\n")
        # Print the full stack trace using traceback
        traceback.print_exc()
        print("\n")

    finally:
        lcd.clear()
        lcd.backlight(False)
        sensor.led_off()
        GPIO.cleanup()
        time.sleep(1)
        exit(0)