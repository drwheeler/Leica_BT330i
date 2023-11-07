# Press Bluetooth button to start connection.
# When the COM port tries to open the windows pair box will open.
# Use code 0000

# Needs keyboad, pyserial
# pyinstaller .\disto_txfr.py --onefile


import argparse
import signal
import sys

import keyboard
import serial


def hexdump(buf) -> None:
    chunks = [buf[i:i + 16] for i in range(0, len(buf), 16)]
    idx = 0

    for chunk in chunks:
        s1 = " ".join([f"{i: 02x}" for i in chunk])
        s1 = s1[0:23] + " " + s1[23:]
        width = 48

        s2 = "".join([chr(i) if 32 <= i <= 127 else "." for i in chunk])

        print(f"{idx * 16: 08x}  {s1: <{width}}  |{s2}|")  # parameterized width

        idx += 1


def command(serport: serial.Serial, cmd: bytes) -> None:
    serport.write(cmd)
    serport.write(b'\r\n')
    print(cmd, " : ", serport.readline())


def handler(_sig, _frame):
    exit(0)


signal.signal(signal.SIGINT, handler)

parser = argparse.ArgumentParser(description="Leica Disto 330i Bluetooth serial data to keyboard presses")
parser.add_argument('comport', help="COM port")

args = parser.parse_args()

ACK = b'cfm\n'

try:
    print("Opening serial port")

    with serial.Serial(args.comport, 115200, timeout=1) as port:
        print("Serial port opened")
        port.write(ACK)

        while True:
            resp = port.readline()

            if len(resp) > 0:
                # print(resp)
                port.write(ACK)
                ackack = port.readline()

                if resp == b'?\r\n':  # OK
                    continue

                if resp.startswith(b'@E'):  # Some kind of error
                    continue

                resp = resp.decode('ascii').rstrip().split(' ')

                sum_dist = 0
                cnt_dist = 0

                for val in resp:
                    if val.startswith('31..00+'):  # Distance measured in mm
                        sum_dist += int(val[7:16])
                        cnt_dist += 1
                    elif val[0:4] == '5000':  # Direction key
                        key = int(val[7:15])

                        match key:
                            case 4:
                                keyboard.press_and_release('up, left')
                            case 2:
                                keyboard.press_and_release('up')
                            case 8:
                                keyboard.press_and_release('up, right')
                            case 3:
                                keyboard.press_and_release('left')
                            case 6:
                                keyboard.press_and_release('right')
                            case 10:
                                keyboard.press_and_release('down, left')
                            case 1:
                                keyboard.press_and_release('down')
                            case 15:
                                keyboard.press_and_release('down, right')

                if cnt_dist > 0:
                    keyboard.write(str(sum_dist / cnt_dist))
                    keyboard.press_and_release('enter')
except serial.SerialException as e:
    print(e)
    sys.exit(1)
except KeyboardInterrupt as e:
    sys.exit(1)
finally:
    print("Serial port closed")
