from smbus2 import SMBus, i2c_msg
from time import sleep


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
        self.enable_bit = 0x04  # Enable bit (for PCF8574T chip)

        # Initialize display
        self.write_cmd(0x33)  # initialization
        self.write_cmd(0x32)  # set to 4-bit mode
        self.write_cmd(0x06)  # cursor direction
        self.write_cmd(0x0C)  # turn the display on
        self.write_cmd(0x28)  # 2 lines
        self.write_cmd(0x01)  # clear display
        sleep(0.0005)

    def strobe(self, data):
        self.bus.write_byte(self.address, data | self.enable_bit | self.backlightval)
        sleep(0.0001)
        self.bus.write_byte(self.address, ((data & ~self.enable_bit) | self.backlightval))
        sleep(0.0001)

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
        sleep(0.005)
        self.write_cmd(0x02)
        sleep(0.005)

    def backlight(self, state=True):
        if state:
            self.backlightval = 0x08
        else:
            self.backlightval = 0x00
        self.write_cmd(0x00)  # Writing a command to update the backlight state
