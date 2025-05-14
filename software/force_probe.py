#******************************************************************************
#
#   @file       mms101_evaboard_usb_sample_code.py
#   @brief      MMS101 Evaboard USB Sample Source File (Python)
#
#               copyright: MITSUMI Electric Co.,LTD
#   @attention  none
#   @warning    MITSUMI CONFIDENTIAL
#
#******************************************************************************
#******************************************************************************
# History : DD.MM.YYYY Version  Description
#         : 22.12.2022 1.0.0.0  First Release
#******************************************************************************

import serial
import time
import sys

DEV_SERIAL_PATH = 'COM5'        # for Controller
#DEV_SERIAL_PATH = '/dev/ttyACM0'       # for MultiFingerEvaBoardVer.3.0
SERIAL_BAUDRATE = 1000000               # for Contoller
#SERIAL_BAUDRATE = 921600               # for MultiFingerEvaBoardVer.3.0
INTERVAL_MEASURE_TIME = 10000
INTERVAL_RESTART_TIME = 10000

#******************************************************************************
# MMS101 Class
#******************************************************************************
class mms101:
    debugMode = 0   # =1: debug print

    #**************************************************************************
    # Constractor
    #**************************************************************************
    def __init__(self):
        # Device Name
        self.deviceName = DEV_SERIAL_PATH
        # Baudrate
        self.baudrate = SERIAL_BAUDRATE
        # Interval Measure Time [us]
        self.intervalMeasureTime = INTERVAL_MEASURE_TIME
        # Interval Restart Time [us]
        self.intervalRestartTime = INTERVAL_RESTART_TIME
        # Coefficient
        self.coefficient = [
            [0, 0, 0, 0, 0, 0],     #Fx
            [0, 0, 0, 0, 0, 0],     #Fy
            [0, 0, 0, 0, 0, 0],     #Fz
            [0, 0, 0, 0, 0, 0],     #Mx
            [0, 0, 0, 0, 0, 0],     #My
            [0, 0, 0, 0, 0, 0]      #Mz
        ]

        # serial port open flag
        self.serialOpenFlag = 0

        # Serial port Open
        self.serialPortOpen()

    #**************************************************************************
    # Destractor
    #**************************************************************************
    def __del__(self):
        self.serialPortClose()

    #**************************************************************************
    # Method
    #**************************************************************************
    #====================
    # Open serial port
    #====================
    def serialPortOpen(self):
        self.serialPort = serial.Serial(self.deviceName, self.baudrate)
        self.serialOpenFlag = 1

    #====================
    # Close serial port
    #====================
    def serialPortClose(self):
        if self.serialOpenFlag == 1:
            self.stopMeasure()      # for forced termination
            self.serialPort.close()
            self.serialOpenFlag = 0

    #====================
    # Define device Name and baudrate
    #====================
    def read_all(self):
        j = self.serialPort.read(2)
        if self.debugMode == 1:
            print(j.hex())

        if j[0] == 0 and j[1] > 0:
            data = self.serialPort.read(j[1])
            j = j + data
            if self.debugMode == 1:
                print(data.hex())
        return j

    #====================
    # Firmware Version
    #====================
    def priintFirmwareVersion(self):
        self.serialPort.write([0x54, 0x01, 0x15])
        self.serialPort.flush()
        firmversion = self.read_all()
        if firmversion[0] == 0 and firmversion[1] == 4:
            print("Firmware Version", firmversion[2:])
        else:
            print("Error: Firmware Version")
            exit()

    #====================
    # Board Select
    #====================
    def boardSelect(self):
        if self.debugMode == 1:
            print("Board Select")
        self.serialPort.write(bytes([0x54, 0x02, 0x10, 0x00]))
        self.serialPort.flush()
        bds = self.read_all()
        if bds[0] != 0:
            print("Error: Board Select")
            exit()

    #====================
    # Power Switch
    # (This command can be omitted when using MultiFingerEvaBoardVer.3.0.)
    #====================
    def powerSwitch(self):
        if self.debugMode == 1:
            print("Power Switch12")
        self.serialPort.write([0x54, 0x03, 0x36, 0x00, 0xFF])
        self.serialPort.flush()
        psw0 = self.read_all()
        if psw0[0] != 0 and psw0[0] != 0x10:
            print("Error: Power Switch12")
            exit()

        if self.debugMode == 1:
            print("Power Switch45")
        self.serialPort.write([0x54, 0x03, 0x36, 0x05, 0xFF])
        self.serialPort.flush()
        psw1 = self.read_all()
        if psw1[0] != 0 and psw1[0] != 0x10:
            print("Error: Power Switch45")
            exit()

    #====================
    # Axis Select And Idle
    # (This command can be omitted when using MultiFingerEvaBoardVer.3.0.)
    #====================
    def axisSelectAndIdle(self):
        for axis in range(6):
            if self.debugMode == 1:
                print("Axis Select", axis)
            self.serialPort.write([0x54, 0x02, 0x1C, axis])
            self.serialPort.flush()
            axSel = self.read_all()
            if axSel[0] != 0 and axSel[0] != 0x10:
                print("Error: Axis Select", axis)
                exit()

            #Idle
            self.serialPort.write([0x53, 0x02, 0x57, 0x94])
            self.serialPort.flush()
            idl = self.read_all()
            if idl[0] != 0 and idl[0] != 0x10:
                print("Error: IDLE", axis)
                exit()

        time.sleep(0.01)

    #====================
    # Bootload
    #====================
    def bootload(self):
        if self.debugMode == 1:
            print("Bootload")
        self.serialPort.write([0x54, 0x01, 0xB0])
        self.serialPort.flush()
        bl = self.read_all()
        if bl[0] != 0:
            print("Error: Bootload")
            exit()

    #====================
    # Read Coefficient
    # (Read and use when performing matrix conversion)
    #====================
    def readCoefficient(self):
        for axis in range(6):
            for coeff in range(6):
                if self.debugMode == 1:
                    print("Coefficient", axis, coeff)
                self.serialPort.write([0x54, 0x03, 0x27, axis, coeff])
                self.serialPort.flush()
                coeffData = self.read_all()
                if coeffData[0] == 0 and coeffData[1] == 4:
                    self.coefficient[axis][coeff] = (coeffData[2] << 24) + (coeffData[3] << 16) + (coeffData[4] << 8) + coeffData[5]
                    if self.debugMode == 1:
                        print(hex(self.coefficient[axis][coeff]))
                else:
                    print("Error: Coefficient", axis, coeff)
                    exit()

    #====================
    # Interval Measure(us)
    #====================
    def setIntervalMeasure(self, intervalTime):
        if self.debugMode == 1:
            print("Interval Measure")
        self.intervalMeasureTime = intervalTime
        bData1 = (self.intervalMeasureTime >> 16) & 0xFF
        bData2 = (self.intervalMeasureTime >> 8) & 0xFF
        bData3 = self.intervalMeasureTime & 0xFF
        self.serialPort.write([0x54, 0x04, 0x43, bData1, bData2, bData3])
        self.serialPort.flush()
        simt = self.read_all()
        if simt[0] != 0:
            print("Error: Interval Measure")
            exit()

    #====================
    # Interval Restart
    #====================
    def setIntervalRestart(self, intervalTime):
        if self.debugMode == 1:
            print("Interval Restart")
        self.intervalRestartTime = intervalTime
        bData1 = (self.intervalRestartTime >> 16) & 0xFF
        bData2 = (self.intervalRestartTime >> 8) & 0xFF
        bData3 = self.intervalRestartTime & 0xFF
        self.serialPort.write([0x54, 0x04, 0x44, bData1, bData2, bData3])
        self.serialPort.flush()
        sirt = self.read_all()
        if sirt[0] != 0:
            print("Error: Interval Restart")
            exit()

    #====================
    # Start measurement
    #====================
    def startMeasure(self):
        self.serialPort.write([0x54, 0x02, 0x23, 0x00])
        j = self.serialPort.read(2)
        if self.debugMode == 1:
            print("Start")
            print(j)

        #====================
        # Check whether the data is ready
        #====================
        if len(j) != 2 or j[0] != 0 or j[1] != 0:
            print("Error: Start")
            exit()

        time.sleep(0.01)

    #====================
    # Stop mearesument
    #====================
    def stopMeasure(self):
        if self.debugMode == 1:
            print("Stop")
        self.serialPort.write([0x54, 0x01, 0x33])
        j = self.read_all()

        #====================
        # Check whether the data is ready
        #====================
        #if len(j) != 2 or j[0] != 0 or j[1] != 0:
        #    print("Error: Stop")
        #    exit()

        #time.sleep(0.01)

    #====================
    # Read data
    #====================
    def readData(self):
        prev = bin(0xff)
        while True:
            curr = self.serialPort.read()
            if prev == b'\x00' and curr == b'\x17':
                break
            prev = curr

        data = self.serialPort.read(23)

        #time.sleep(0.01)

        return data


#******************************************************************************
# Main Routine
#******************************************************************************
args = sys.argv
if len(args) >= 2:
    measureMax = int(args[1])
else:
    measureMax = 100000

mms101ctrl = mms101()
dataCounter = 0
mms101data = [0, 0, 0, 0, 0, 0]
elapsTime = 0.0

# Initialize MMS101
mms101ctrl.boardSelect()
mms101ctrl.powerSwitch()
mms101ctrl.axisSelectAndIdle()
mms101ctrl.bootload()
#mms101ctrl.readCoefficient()
mms101ctrl.setIntervalMeasure(INTERVAL_MEASURE_TIME)
mms101ctrl.setIntervalRestart(INTERVAL_RESTART_TIME)
mms101ctrl.startMeasure()

print("time[s],Fx,Fy,Fz,Mx,My,Mz")
while True:
    if dataCounter < measureMax:
        rData = mms101ctrl.readData()
        if len(rData) == 23 and rData[0] == 0x80 and rData[1] == 0x00:
            elapsTime += ((rData[20] << 16) + (rData[21] << 8) + rData[22]) / 1000000
            for axis in range(6):
                mms101data[axis] = (rData[axis*3+2] << 16) + (rData[axis*3+3] << 8) + rData[axis*3+4]
                if mms101data[axis] >= 0x00800000:
                    mms101data[axis] -= 0x1000000       #negative number handling

            mms101data[0] = mms101data[0] / 1000
            mms101data[1] = mms101data[1] / 1000
            mms101data[2] = mms101data[2] / 1000
            mms101data[3] = mms101data[3] / 100000
            mms101data[4] = mms101data[4] / 100000
            mms101data[5] = mms101data[5] / 100000

            print(f'{elapsTime:.6f},{mms101data[0]:.3f},{mms101data[1]:.3f},{float(mms101data[2])+14.4:.3f},{mms101data[3]:.5f},{mms101data[4]:.5f},{mms101data[5]:.5f}')
        else:
            print('Error: Result data length', len(rData))

        dataCounter += 1
    else:
        mms101ctrl.stopMeasure()
        exit()