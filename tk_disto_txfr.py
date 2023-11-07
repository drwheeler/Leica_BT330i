# Press Bluetooth button to start connection.
# When the COM port tries to open the windows pair box will open.
# Use code 0000

# Needs keyboard, pyserial
# pyinstaller .\disto_txfr.py --onefile


import sys
import time
import tkinter as tk
import tkinter.scrolledtext as scrolledtext
import tkinter.ttk as ttk
from tkinter import messagebox

import keyboard
import serial
import serial.tools.list_ports

ACK = b"cfm\n"
# ↖↑↗→←↙↓↘
KEY_CODES = {4: 'up, left',
             2: 'up',
             8: 'up, right',
             3: 'left',
             6: 'right',
             10: 'down, left',
             1: 'down',
             15: 'down, right'
             }


def hexdump(buf) -> str:
    chunks = [buf[i:i + 16] for i in range(0, len(buf), 16)]
    idx = 0
    lines = []

    for chunk in chunks:
        s1 = " ".join([f"{i: 02x}" for i in chunk])
        s1 = s1[0:23] + " " + s1[23:]
        width = 48

        s2 = "".join([chr(i) if 32 <= i <= 127 else "." for i in chunk])

        lines.append("".join(f"{idx * 16: 08x}  {s1: <{width}}  |{s2}|"))  # parameterized width

        idx += 1

    s3 = "\n".join(lines)

    return s3 + "\n"


def command(serport: serial.Serial, cmd: bytes) -> None:
    serport.write(cmd)
    serport.write(b'\r\n')
    print(cmd, " : ", serport.readline())


class Application(tk.Tk):
    def open_port(self) -> None:
        idx = self.ports_combo.current()

        if idx < 0:
            messagebox.showerror(title='Port Error', message="Select a serial port")
            return

        portname = self.serports[idx].device

        if self.serial_port is not None:
            self.serial_port.close()

        try:
            self.open_button.config(cursor="wait")
            self.serial_port = serial.Serial(portname, 115200, timeout=1)
            self.open_button['state'] = tk.DISABLED
            self.close_button['state'] = tk.NORMAL

            self.text_box.insert(tk.END, f"{self.serports[idx]} opened.\n", 'info')
            self.text_box.insert(tk.END, f"Keypresses will be sent to the currently active application\n", 'error')
            self.text_box.see(tk.END)

            self.reciever()

        except serial.SerialException as e:
            self.text_box.insert(tk.END, f"Could not open {self.serports[idx]} : {e}\n", 'error')
            self.text_box.see(tk.END)

            messagebox.showerror(title='Port Error', message=f"Could not open {self.serports[idx]}")

        finally:
            self.open_button.config(cursor="")

    def port_close(self) -> None:
        if self.serial_port is not None:
            self.open_button['state'] = tk.NORMAL
            self.close_button['state'] = tk.DISABLED
            self.text_box.insert(tk.END, f"{self.serial_port.name} closed.\n", 'info')
            self.text_box.see(tk.END)

            self.serial_port.close()

            self.serial_port = None

    def app_close(self) -> None:
        self.port_close()
        self.destroy()

    def reciever(self) -> None:
        if self.serial_port is None:
            return

        while self.serial_port.inWaiting() > 0:
            ser_line = self.serial_port.readline()
            self.serial_port.write(ACK)

            if ser_line == b'?\r\n':  # OK? get this continuously
                continue

            if self.debug.get() == 1:
                self.text_box.insert(tk.END, hexdump(ser_line), 'rawline')
                self.text_box.see(tk.END)

            if ser_line.startswith(b'@E'):  # Some kind of error
                if self.debug.get() == 1:
                    self.text_box.insert(tk.END, ser_line.decode('ascii'), 'error')
                    self.text_box.see(tk.END)

                continue

            readings = ser_line.decode('ascii').rstrip().split(' ')

            sum_dist = 0
            cnt_dist = 0

            for val in readings:
                if val.startswith('31..00+'):  # Distance measured in mm
                    sum_dist += int(val[7:16])
                    cnt_dist += 1

                elif val[0:4] == '5000':  # Direction key
                    key = int(val[7:15])

                    if key in KEY_CODES:
                        keyboard.press_and_release(KEY_CODES[key])

                        if self.debug.get() == 1:
                            self.text_box.insert(tk.END, KEY_CODES[key])
                            self.text_box.see(tk.END)

                    else:
                        if self.debug.get() == 1:
                            self.text_box.insert(tk.END, f"Unknown key code {key}", 'error')
                            self.text_box.see(tk.END)

            if cnt_dist > 0:
                type_str = 'val='

                if cnt_dist > 1:
                    type_str = f'avg({cnt_dist})='

                self.text_box.insert(tk.END, type_str + str(sum_dist / cnt_dist) + "\n")
                self.text_box.see(tk.END)

                keyboard.write(str(sum_dist / cnt_dist))
                keyboard.press_and_release('enter')

            time.sleep(0.001)

        self.after(1, self.reciever)

    def __init__(self) -> None:
        self.serial_port = None
        self.serports = serial.tools.list_ports.comports()

        tk.Tk.__init__(self)

        self.title('BT330i Keyboard')
        self.geometry('640x480')
        self.protocol('WM_DELETE_WINDOW', self.app_close)

        self.port_frame = ttk.Frame(self, borderwidth=5, relief='ridge')

        self.port_label = ttk.Label(self.port_frame, text='Serial Port')
        self.ports_combo = ttk.Combobox(self.port_frame, width=50, values=self.serports)
        self.ports_combo.state(['readonly'])
        self.open_button = tk.Button(self.port_frame, text='Open', command=self.open_port)
        self.close_button = tk.Button(self.port_frame, text='Close', command=self.port_close, state=tk.DISABLED)
        self.debug = tk.IntVar()
        self.debug_bx = tk.Checkbutton(self.port_frame, text='Debug', variable=self.debug, onvalue=1, offvalue=0)

        self.text_box = scrolledtext.ScrolledText()
        self.text_box['font'] = ('consolas', '10')
        self.text_box.tag_config('info', foreground='blue')
        self.text_box.tag_config('error', foreground='red')
        self.text_box.tag_config('rawline', foreground='gray')
        self.text_box.bind("<Button->", lambda e: "break")
        self.text_box.bind("<Key>", lambda e: "break")
        self.text_box.config(cursor="arrow")

        self.port_frame.pack(anchor=tk.W)

        self.port_label.grid(column=0, row=0, padx=5)
        self.ports_combo.grid(column=1, row=0, padx=5)
        self.open_button.grid(column=2, row=0, padx=5)
        self.close_button.grid(column=3, row=0, padx=5)
        self.debug_bx.grid(column=4, row=0, padx=5)

        self.text_box.pack(fill=tk.BOTH, expand=True)


def main():
    root = Application()
    root.mainloop()
    sys.exit()


if __name__ == '__main__':
    main()
