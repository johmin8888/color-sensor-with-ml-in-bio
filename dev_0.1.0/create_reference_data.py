import os
import sys
import time
import RPi.GPIO as GPIO
import numpy as np
import pandas as pd
from I2CLCD import I2CLCD
from TCS3200 import TCS3200


# Hyperparameters
DATA_DIRECTORY = "data"
CALIBRATION_FILE = "calibration.txt"
REFERENCE_FILE = "reference_2.csv"


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

# Define a function to save the reference data
def save_data(dataframe, filename, data_dir):
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Join it with the relative path of your data
    data_path = os.path.join(current_dir, data_dir)

    # Define the reference data path
    reference_data_path = os.path.join(data_path, filename)

    if os.path.exists(reference_data_path):
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
                dataframe.to_csv(reference_data_path, mode='a', header=False, index=False)
                print(f"Data appended at: {os.path.abspath(reference_data_path)}")
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
                dataframe.to_csv(reference_data_path, index=False)
                print(f"Data overwritten at: {os.path.abspath(reference_data_path)}")
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
            dataframe.to_csv(reference_data_path, index=False)
            print(f"Data saved at: {os.path.abspath(reference_data_path)}")
        except Exception as e:
            print(f"Data save error occurred: {e}")
            return
    return


def measure_color(measurement_count=5, deviation=3):
    global index

    print("\nReading color...")
    lcd.text("Reading color...", line=1)

    # Collect 5 measurements
    rgb_freq_list = []
    rgb_list = []

    while len(rgb_list) < measurement_count:
        lcd.text(f"{index:3d}: |{'#' * len(rgb_list)}{' ' * (measurement_count - len(rgb_list))}|", line=2)

        rgb_freq = sensor.read_color_freq()
        rgb = sensor.read_color(global_min, global_max)
        print(f"RGB-frequency({rgb_freq['RED']:3.3f}, {rgb_freq['GREEN']:3.3f}, {rgb_freq['BLUE']:3.3f})")
        print(f"RGB({rgb['RED']:3.3f}, {rgb['GREEN']:3.3f}, {rgb['BLUE']:3.3f})")
        lcd.text(f"RGB({int(rgb['RED']):3d},{int(rgb['GREEN']):3d},{int(rgb['BLUE']):3d})", line=1)

        # Add to list
        rgb_list.append(rgb)
        rgb_freq_list.append(rgb_freq)
        time.sleep(0.3)

        if len(rgb_list) > 1 and max(abs(rgb_list[-1][key] - rgb_list[-2][key]) for key in rgb_list[-1]) > deviation:
            # If deviation is more than 3, clear the list and start over
            rgb_list = []
            rgb_freq_list = []

    # Calculate the average RGB and RGB-frequency values
    avg_rgb = {key: sum(item[key] for item in rgb_list) / len(rgb_list) for key in rgb_list[0].keys()}
    avg_rgb_freq = {key: sum(item[key] for item in rgb_freq_list) / len(rgb_freq_list) for key in rgb_freq_list[0].keys()}

    return avg_rgb, avg_rgb_freq


def label_prompt(avg_rgb, avg_rgb_freq):
    global reference_data
    global previous_label

    # Ask for label
    lcd.text("Enter label.", line=1)
    lcd.text(f"Measurement: {index:3d}", line=2)
    print("\nType (n/no/none/s/save) to finish the measurement and to go save options.")
    print("Type (r/re/redo) to measure again.")
    print(f"Press enter to use the previous label:\t{previous_label}.\n")
    label = input(f"\tMeasurement {index}: Enter label for this data: ")
    print("\n")

    # If the user pressed enter without input, use the previous label
    if label == "":
        label = previous_label

    try:
        label = float(label)  # convert the input to a float

        # Add to DataFrame
        new_data = pd.DataFrame({
            "Red_Frequency": [avg_rgb_freq['RED']],
            "Green_Frequency": [avg_rgb_freq['GREEN']],
            "Blue_Frequency": [avg_rgb_freq['BLUE']],
            "Red": [avg_rgb['RED']],
            "Green": [avg_rgb['GREEN']],
            "Blue": [avg_rgb['BLUE']],
            "Label": [label]
        })

        reference_data = pd.concat([reference_data, new_data])

        # Update the previous label with the current one
        previous_label = label
        return True

    except ValueError:  # if the conversion fails, the input was not a number
        if label.lower() in ['n', 'no', 'none', 's', 'save']:
            save_data(reference_data, REFERENCE_FILE, DATA_DIRECTORY)
            print("\n")
            return False
        elif label.lower() in ['r', 're', 'redo']:
            avg_rgb, avg_rgb_freq = measure_color()
            return label_prompt(avg_rgb, avg_rgb_freq)
        else:
            print("\nInput is not a number.")
            return label_prompt(avg_rgb, avg_rgb_freq)


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
        sensor.read_color_freq() # Booting sensor with a read
        print("Sensor is ready.")
        time.sleep(1)

        global_min, global_max = load_calibration_data(CALIBRATION_FILE, DATA_DIRECTORY)
        print("Calibration data is ready.")
        time.sleep(1)

        # DataFrame to hold the results
        reference_data = pd.DataFrame(columns=["Red_Frequency", "Green_Frequency", "Blue_Frequency", "Red", "Green", "Blue", "Label"])
        previous_label = None
        index = 0
        print("Dataframe has been created.")

        loop = True # main loop

        print("Initialization done.")
        print("\n")
        lcd.text("Done.", line=1)
        lcd.text("Device is ready.", line=2)
        time.sleep(1)
        lcd.clear()

        while loop == True:
            index += 1

            avg_rgb, avg_rgb_freq = measure_color()
            loop = label_prompt(avg_rgb, avg_rgb_freq)

    except KeyboardInterrupt:
        # Handle the Ctrl-C exception to gracefully exit the script
        save_data(reference_data, REFERENCE_FILE, DATA_DIRECTORY) # checkpointing
        print("\nKeyboard interrupted.")
        print("Program terminated by user.\n")

    except Exception as e:
        # Print out any other exceptions that might occur
        print(f"An error occurred: {e}\n")

    finally:
        lcd.clear()
        lcd.backlight(False)
        sensor.led_off()
        GPIO.cleanup()
        time.sleep(1)
        exit(0)