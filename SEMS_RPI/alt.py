import serial



import time
PORT = 'COM5'
class SerialCom():
    def __init__(self):
        self.ser = serial.Serial(PORT, 9600)
        self.ser.flushInput()
    def send(self, msg):
        #if msg is empty
        if not msg:
            return
        #check if msg have \n or not, if not add it
        if msg[-1] != '\n':
            msg += '\n'
        self.ser.write(msg.encode())
        self.ser.flush()
    def read(self):
        return self.ser.readline().decode('ascii').rstrip()
    def close(self):
        self.ser.close()
msgs = ''
ser = SerialCom()
time.sleep(1)
print("Starting..")
ser.send('_')
while True:
    msg = ser.read()
    if msg:
        msgs += msg[1:]
        if msg[1:] == 'D':
            
            msgs = msgs[:-2]
        ser.send('D'+msgs)
        ser.send('_')