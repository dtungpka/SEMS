#import serial lib, open com8
import serial
import face_recognition
import cv2
import numpy as np
import logging
from datetime import datetime
from time import sleep
from collections import Counter
import os
import json
import pickle
import threading
import sys
import serial.tools.list_ports
import time
FACE_DIR = "FaceData/"
#create dir if not exist
try: 
    
    os.mkdir(FACE_DIR)
except :
    pass

try:
    os.mkdir("LogFiles/")
except :
    pass
format = "%(asctime)s: %(message)s"
logname =  "./LogFiles/Log_"+str(datetime.now().month) +"_"+ str(datetime.now().day)+"_"+ str(datetime.now().hour)+"_"+ str(datetime.now().minute)+".log"
logging.basicConfig(filename=logname,format=format, level=logging.INFO,datefmt="%H:%M:%S")
class Console():
    def Log(*arg):
        msg = ""
        for inf in arg:
            msg += str(inf) + " "
        logging.info("INFO "+msg)
        print("INFO "+msg)
    def Warning(*arg):
        msg = ""
        for inf in arg:
            msg += str(inf) + " "
        logging.warning("WARNING "+msg)
        print("WARNING "+msg)
    def Error(*arg):
        msg = ""
        for inf in arg:
            msg += str(inf) + " "
        logging.error("ERROR "+msg)
        print("ERROR "+msg)
def evaluate(method):
    start = datetime.now()
    method()
    end = datetime.now()
    Console.Log(f"Method {method.__name__} took {round((end-start).total_seconds(),5)} seconds to execute")
    return (end-start).total_seconds()



ports = list(serial.tools.list_ports.comports())
if not ports:
    sys.exit("No serial ports available")
elif len(ports) == 1:
    PORT = ports[0].device
    print(f"Selected port: {PORT}")
else:
    print("Available ports:")
    for i, port in enumerate(ports):
        print(f"{i + 1}: {port.device}")
    selection = int(input("Select a port: ")) - 1
    PORT = ports[selection].device
    print(f"Selected port: {PORT}")
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

def parse_command(command,value=''):
    to_send = ""
    to_send += COMMANDS[command]
    #loop through the value string, if encouter \n then pad by space it to 16 character
    if len(value) > 0:
        if '\n' in value:
            for i in range(len(value)):
                if value[i] == '\n':
                    value = value[:i] + ' '*(16-i) + value[i:]
                    to_send += value
                    break
        #replace the \n
            to_send = to_send.replace('\n','')
        else:
            to_send += value
    return to_send

        
        
   

COMMANDS = {
    'SEND_KEY':'K',
    'DISPLAY_MESSAGE':'D',
    'GRANT_ACCESS':'G',
    'CLOSE_DOOR':'L',
    'FACE_DETECTED':'F',
    'END':'_',
    'READY':'R',
    'SET_ACCESS_TIME':'A',
    'SET_SPEED':'E',
    'SET_OPENTIME':'T',
    'CALIBRATING':'C',
    'SET_CALIBRATING_VALUE':'V',
    'GET_CALIBRATING_VALUE':'S'
    }
data = {
    'CALIBRATING_VALUE':1000,
    'ACCESS_TIME':60000,
    'SPEED':57722,
    'OPENTIME':60000,
    'PASSWORD':[ '1234'],
    'ADMIN_PASSWORD':'0301011',
    'FACE_DATA':['ID1'], #id, encoding
    'SHOW_PASSWORD':False
    }


last_cursor = [-1,-1,-1]
cursor = [-1,-1,-1]
ADMIN_PANEL = {
    'Password':['Add','Change','Delete','Back'],
    'Face Data':['Add','Delete','Back'],
    'Access Time':['Change','Back'],
    'Speed':['Change','Back'],
    'Open Time':['Change','Back'],
    'Calibrating Value':['Run'],
    'Show password':['On/Off'],
    'Exit':['Exit']
    }
ser = SerialCom()
lock = threading.Lock()
def check_face_ids(detected:list):
    face_ids = []
    for face in data['FACE_DATA']:
        face_ids.append(face)
    for face in detected:
        if face in face_ids:
            return True
    return False

class Password():
    def __init__(self):
        self.password = data['PASSWORD']
        self.admin_password = data['ADMIN_PASSWORD']
        self.show_password = data['SHOW_PASSWORD']
        self.current_password = ''
        self.password_length = max([len(p) for p in self.password])
        self.display_password()
        
    def enter_password(self, key):
        self.current_password += key
        self.display_password()
    def entering_password(self):
        if self.current_password:
            return True
        
        return False
    def check_password(self):
        if self.current_password in self.password:
            return True
        if len(self.current_password) >= self.password_length and self.current_password not in data['ADMIN_PASSWORD']:
            ser.send(parse_command('DISPLAY_MESSAGE','Wrong password'))
            self.current_password = ''
            time.sleep(2)
            self.display_password()
        return False
    def delete_password(self):
        self.current_password = self.current_password[:-1]
        self.display_password()
    def check_admin_password(self):
        if self.current_password == self.admin_password:
            return True
        return False
    def clear_password(self):
        self.current_password = ''
    def display_password (self):
        if self.show_password: #show the password, unentered is _
            ser.send(parse_command('DISPLAY_MESSAGE','Enter password:\n'+self.current_password + '_'*(self.password_length-len(self.current_password))))
        else:
            ser.send(parse_command('DISPLAY_MESSAGE','Enter password:\n'+'*' * len(self.current_password) + '_'*(self.password_length-len(self.current_password))))
        ser.send(parse_command('END'))
    def check_admin_password(self):
        if self.current_password == self.admin_password:
            return True
        return False
class AdminPanel:
    authorized = False
    def __init__(self) -> None:
        pass
    def handle_key(self,key):
        pass
    def render_panel(self):
        if cursor[0] == -1:
            ser.send(parse_command('DISPLAY_MESSAGE','Welcome to\nSEMS Admin Panel'))
            return
        if cursor[1] == -1 and cursor[2] == -1:
            n = list(ADMIN_PANEL.keys())
            #if cursor is out of range
            if cursor[0] >= len(n):
                cursor[0] = len(n)-1
            #display > on the cursor position and ' ' on the rest (display 2 line max)
            for i in range(len(n)):
                n[i] = '>' + n[i] if i == cursor[0] else ' ' + n[i]
            if cursor[0] % 2 == 0:
                ser.send(parse_command('DISPLAY_MESSAGE',n[cursor[0]]+'\n'+n[cursor[0]+1]))
            else:
                ser.send(parse_command('DISPLAY_MESSAGE',n[cursor[0]-1]+'\n'+n[cursor[0]]))
            return
        if cursor[2] == -1:
            n = ADMIN_PANEL[list(ADMIN_PANEL.keys())[cursor[0]]]
            #if cursor is out of range
            if cursor[1] >= len(n):
                cursor[1] = len(n)-1
            #display > on the cursor position and ' ' on the rest (display 2 line max)
            for i in range(len(n)):
                n[i] = '>' + n[i] if i == cursor[1] else ' ' + n[i]
            if cursor[1] % 2 == 0:
                ser.send(parse_command('DISPLAY_MESSAGE',n[cursor[1]]+'\n'+n[cursor[1]+1]))
            else:
                ser.send(parse_command('DISPLAY_MESSAGE',n[cursor[1]-1]+'\n'+n[cursor[1]]))
            return
           
        

        
  
def serial_handler():
    password = Password()
    admin_panel = AdminPanel()
    update_face = 0
    while True:
        msg = ser.read()
        
        command = msg[0]
        value = msg[1:]
        if command != COMMANDS['END']:
            Console.Log("Received: ", msg)
        if command == COMMANDS['SEND_KEY']:
            if not AdminPanel.authorized:
                if value in ['A','B','C','*','#']:
                    ser.send(parse_command('END'))
                    continue
                if value == 'D':
                    password.delete_password()
                    ser.send(parse_command('END'))
                    continue
                password.enter_password(value)
                if password.check_password():
                    password.clear_password()
                    ser.send(parse_command('GRANT_ACCESS'))
                    ser.send(parse_command('DISPLAY_MESSAGE','Access granted'))
                    ser.send(parse_command('END'))
                if password.check_admin_password():
                    AdminPanel.authorized = True
                    cursor[0] = -1
                    cursor[1] = -1
                    cursor[2] = -1
                    admin_panel.render_panel()
            else:
                if value == 'B':
                    ser.send(parse_command('DISPLAY_MESSAGE','Capturing image'))
                    ser.send(parse_command('END'))
                    Recognition.take = True
                admin_panel.handle_key(value)
        if command == COMMANDS['END']:
            if (Recognition.detected > 0 and update_face != Recognition.detected) or len(Recognition.authorized) > 0:
                update_face = Recognition.detected
                ser.send(parse_command('FACE_DETECTED','D'))
                if check_face_ids(Recognition.authorized):
                    ser.send(parse_command('GRANT_ACCESS'))
                    
                    if len(Recognition.authorized) > 1:
                        ser.send(parse_command('DISPLAY_MESSAGE','Access granted:\n '+Recognition.authorized[0]+' and '+Recognition.authorized[1]))
                    elif len(Recognition.authorized) == 1 :
                        ser.send(parse_command('DISPLAY_MESSAGE','Access granted:\n'+Recognition.authorized[0]))
                    
            elif update_face != 0 and Recognition.detected == 0:
                ser.send(parse_command('FACE_DETECTED','U'))
                update_face = 0

            ser.send(parse_command('END'))
        

class Recognition:
    detected = 0
    authorized = []
    take = False
    def __init__(self,known_face_encodings,known_face_names):
        self.known_face_encodings = known_face_encodings
        self.known_face_names = known_face_names
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.process_frame = 2
        self.video_capture = cv2.VideoCapture(0)
    def run(self):
       current_frame = 0
       while True:
            # Grab a single frame of video
            self.ret, frame = self.video_capture.read()

            #Resize frame of video to 1/4 size for faster face recognition processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

            # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Find all the faces and face enqcodings in the frame of video
            face_locations = face_recognition.face_locations(rgb_frame)
            if current_frame > 0:
                current_frame -= 1
                continue
            current_frame = self.process_frame = 10


            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            faces = []
            # Loop through each face in this frame of video
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # See if the face is a match for the known face(s)
                

                name = "Unknown"

                # If a match was found in known_face_encodings, just use the first one.
                # if True in matches:
                #     first_match_index = matches.index(True)
                #     name = known_face_names[first_match_index]
                if len(self.known_face_encodings) > 0:
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding,0.21)
                    # Or instead, use the known face with the smallest distance to the new face
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                faces.append(name)
                # Draw a box around the face
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

                # Draw a label with a name below the face
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
            Recognition.detected = len(face_locations)
            Recognition.authorized = [face for face in faces if face != 'Unknown']
            #Console.Log("Faces: {}".format(Recognition.authorized))
            if Recognition.take:
                self.save_new_face(frame)
                Recognition.take = False
            # Display the resulting image
            

    def save_new_face(self,frame):
        #save new face
        global lock,data
        if self.ret:
            #resize frame
            #convert to rgb
            rgb_small_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            #get face location
            face_locations = face_recognition.face_locations(rgb_small_frame)
            #get face encoding
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            if len(face_encodings) > 0:
                self.known_face_encodings.append(face_encodings[0])
                self.known_face_names.append(f"Face_{len(self.known_face_names)}")
                data['FACE_DATA'].append(f"Face_{len(self.known_face_names)}")
                with open("config.json", 'w') as f:
                    json.dump(data,f)
                with open(FACE_DIR+"face_data.pickle", 'wb') as f:
                    pickle.dump(self.known_face_encodings, f)
                #save the frame 
                cv2.imwrite(FACE_DIR+f"Face_{len(self.known_face_names)}.jpg",frame)
                Console.Log("New face added:" + f"Face_{len(self.known_face_names)}" )
            else:
                Console.Log("No face detected")
    def remove_face_data(self,name):
        global data
        #remove face data
        if name in self.known_face_names:
            index = self.known_face_names.index(name)
            self.known_face_names.pop(index)
            self.known_face_encodings.pop(index)
            data['FACE_DATA'].pop(index)
            with open("config.json", 'w') as f:
                json.dump(data,f)
            with open(FACE_DIR+"face_data.pickle", 'wb') as f:
                pickle.dump(self.known_face_encodings, f)
            Console.Log("Face data removed:" + name )
        else:
            Console.Log("Face data not found:" + name )

def main():
    global data
    
    #open camera 0 and start
    video_capture = cv2.VideoCapture(0)
    process_this_frame = True
    #load face data
    Console.Log("Loading face data")
    #check if file exist
    if not os.path.isfile(FACE_DIR+"face_data.pickle"):
        known_face_encodings = []
        known_face_names = []
    else:
        with open(FACE_DIR+"face_data.pickle", 'rb') as f:
            loaded_data = pickle.load(f)
            known_face_encodings = loaded_data
    Console.Log("Face data loaded")
    #load config
    Console.Log("Loading config")
    if not os.path.isfile("config.json"):
        with open("config.json", 'w') as f:
            json.dump(data,f)
    else: 
        with open("config.json", 'r') as f:
            data = json.load(f)
    Console.Log("Config loaded")
    #send config to arduino
    Console.Log("Sending config to arduino")
    ser.send(parse_command('SET_ACCESS_TIME',str(data['ACCESS_TIME'])))
    ser.send(parse_command('SET_SPEED',str(data['SPEED'])))
    ser.send(parse_command('SET_OPENTIME',str(data['OPENTIME'])))
    ser.send(parse_command('SET_CALIBRATING_VALUE',str(data['CALIBRATING_VALUE'])))
    ser.send(parse_command('END'))
    Console.Log("Config sent")
    #start serial handler
    serial_handler_thread = threading.Thread(target=serial_handler)
    serial_handler_thread.start()
    face_rec = Recognition(known_face_encodings,data['FACE_DATA'])
    face_rec.run()
    
        
if __name__ == "__main__":
    main()
    
    