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

        print("Initialization done.")
        lcd.text("Done.", line=1)
        lcd.text("Device is ready.", line=2)
        time.sleep(1)
        lcd.clear()

        calibration_colors = {
            "BLACK": (0, 0, 0, 0),
            #"RED": (255, 0, 0, 255),
            #"GREEN": (0, 255, 0, 255),
            #"BLUE": (0, 0, 255, 255),
            "WHITE": (255, 255, 255, 255),
        }

        global_min = [float('inf'), float('inf'), float('inf'), float('inf')]
        global_max = [float('-inf'), float('-inf'), float('-inf'), float('-inf')]

        for color, rgb in calibration_colors.items():
            lcd.text(f"Insert {color}.", line=1)
            lcd.text("Press Enter.", line=2)
            input(f"Insert {color} strip and press Enter to continue.")

            # ...

            # Take 5 measurements and find min and max values
            for i in range(5):
                color_freq = sensor.read_color_freq(num_samples=30)
                print(f"Measurement: {i+1}, RGB({color_freq})")
                lcd.text(f"({int(color_freq['RED']):4d},{int(color_freq['GREEN']):4d},{int(color_freq['BLUE']):4d})", line=1)
                lcd.text(f"Measurement: {i+1}/5", line=2)
                
                # Update global min and max values
                global_min = [min(global_min[i], color_freq[color]) for i, color in enumerate(["RED", "GREEN", "BLUE", "CLEAR"])]
                global_max = [max(global_max[i], color_freq[color]) for i, color in enumerate(["RED", "GREEN", "BLUE", "CLEAR"])]
            
            time.sleep(1)
        
        lcd.text("Calibration done", line=1)
        lcd.text("Saving File...", line=2)
        time.sleep(1)

        # Get script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Create /data directory if doesn't exist
        data_dir = os.path.join(script_dir, DATA_DIRECTORY)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # Save the global min and max values to a file
        with open(os.path.join(data_dir, CALIBRATION_FILE), "w") as f:
            f.write(f"global_min:{global_min}\n")
            f.write(f"global_max:{global_max}\n")
            f.write(f"white_balance:{global_max[3]}\n")  # Saving the CLEAR channel reading as the white balance
        print(f"Calibration done. \nCalibration file saved at: {os.path.join(data_dir, CALIBRATION_FILE)}\n")
        
        lcd.text("File saved.", line=2)
        time.sleep(1)

    except KeyboardInterrupt:
        # Handle the Ctrl-C exception to gracefully exit the script
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
        lcd.backlight(True)
        lcd.clear()  # Clear the display before stopping
        sensor.led_off()
        GPIO.cleanup()
        time.sleep(1)
        exit(0)