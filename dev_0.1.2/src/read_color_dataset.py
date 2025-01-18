import os
import sys
import time
import traceback
import RPi.GPIO as GPIO
import numpy as np
import pandas as pd
from modules.I2CLCD import I2CLCD
from modules.TCS3200 import TCS3200


# Hyperparameters
DATA_DIRECTORY = os.path.join("..", "data")
CALIBRATION_FILE = "calibration.txt"
REFERENCE_FILE = ""

def get_latest_file(directory, default_name="*.csv"):
    """Return the most recently modified file in the given directory."""
    # Get list of all files in the directory
    list_of_files = [os.path.join(directory, file) for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file)) and file.endswith('.csv')]

    # If there are no files, return the default_name
    if not list_of_files:
        return default_name

    # Otherwise, return the file with the most recent modification time
    return max(list_of_files, key=os.path.getmtime)

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

# Define a function to save the reference data
def save_data(dataframe, data_dir):
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Join it with the relative path of your data
    data_path = os.path.join(current_dir, data_dir)
    filename = get_latest_file(data_path)

    # Define the reference data path
    reference_data_path = os.path.join(data_path, filename)

    if filename == "*.csv":
        # Prompt for a new filename
        filename = input("Enter the new filename: ")
        reference_data_path = os.path.join(data_path, filename)
        
        # Check if the new filename already exists
        while os.path.exists(reference_data_path):
            print(f"File named {filename} already exists.")
            filename = input("Enter another filename: ")
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
            while os.path.exists(new_data_path):
                print(f"File named {new_filename} already exists.")
                new_filename = input("Enter another filename: ")
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
            return save_data(dataframe, DATA_DIRECTORY)
        
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


def label_prompt(avg_rgb, avg_rgb_freq, avg_clear_freq):
    global reference_data

    # Ask for label
    lcd.text("Enter label.", line=1)
    lcd.text(f"Measurement: {index:3d}", line=2)
    print("\nType (n/no/none/s/save) to finish the measurement and to go save options.")
    print("Type (r/re/redo) to measure again.")
    user_input = input(f"\tMeasurement {index}: Type name of label: ")
    print("\n")

    if user_input.lower() in ['r', 're', 'redo']:
        avg_rgb, avg_rgb_freq, avg_clear_freq = measure_color()
        return label_prompt(avg_rgb, avg_rgb_freq, avg_clear_freq)

    elif user_input.lower() in ['n', 'no', 'none', 's', 'save']:
        save_data(reference_data, DATA_DIRECTORY)
        print("\n")
        return False

    elif user_input:  # If user presses enter
        # Add the label to DataFrame
        new_data = pd.DataFrame({
            "Label_Name": str(user_input),
            "Red_Frequency": [avg_rgb_freq['RED']],
            "Green_Frequency": [avg_rgb_freq['GREEN']],
            "Blue_Frequency": [avg_rgb_freq['BLUE']],
            "Clear_Frequency": [avg_clear_freq],  # Add clear frequency data
            "Red": [avg_rgb['RED']],
            "Green": [avg_rgb['GREEN']],
            "Blue": [avg_rgb['BLUE']],
        })
        reference_data = pd.concat([reference_data, new_data])
        return True
    else:
        print("\nInvalid input.")
        return label_prompt(avg_rgb, avg_rgb_freq, avg_clear_freq)
            


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

        # Initialize parameters
        reference_data = pd.DataFrame(columns=["Label_Name", "Red_Frequency", "Green_Frequency", "Blue_Frequency", "Clear_Frequency", "Red", "Green", "Blue"])
        previous_label = None
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
            loop = label_prompt(avg_rgb, avg_rgb_freq, avg_clear_freq)

    except KeyboardInterrupt:
        # Handle the Ctrl-C exception to gracefully exit the script
        save_data(reference_data, DATA_DIRECTORY) # checkpointing
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