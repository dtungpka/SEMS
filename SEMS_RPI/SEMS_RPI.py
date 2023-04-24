#import serial lib, open com8
from statistics import variance
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
def save_setting():
    with open('config.json', 'w') as f:
        json.dump(data, f)
def get_preloader(value):
    value = max(min(95,100 - int(value) ),2)
    DELAY_TIME = max((int(value) / 100 * 32.76) / 1000, 0.001);
    preloader = 65535 - (16000000 * DELAY_TIME / 8)
    return str(preloader)

ports = list(serial.tools.list_ports.comports())
if not ports:
    Console.Error("No serial ports available")
    sys.exit()
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
        self.watch_dog_timer = 0
    def send(self, msg):
        #if msg is empty
        if not msg:
            return
        #check if msg have \n or not, if not add it
        if msg[-1] != '\n':
            msg += '\n'
        while True:
            
            self.watch_dog_timer = time.time()
            self.ser.write(msg.encode())
            self.ser.flush()
            if msg[0] == '_':
                break
            Console.Log("send: |",msg+'|')
            r = self.read()
            
            if r[1:3] == msg[1:3].replace('\n',''):
                break

    def read(self):
        try:
            l = self.ser.readline().decode('ascii').rstrip()
            #Console.Log('Received: ',l)
        except:
            l = "_"

        return l
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
    'GET_CALIBRATING_VALUE':'S',
    'CHECK_PASSWORD':'X'
    }
data = {
    'CALIBRATING_VALUE':'1000',
    'ACCESS_TIME':'60000',
    'SPEED':'50',
    'OPENTIME':'60000',
    'PASSWORD':[ '1234'],
    'ADMIN_PASSWORD':'0301011',
    'FACE_DATA':[], #id, encoding
    'SHOW_PASSWORD':False
    }


ADMIN_PANEL = {
    'SEMS Admin panel':'',
    'Password':['Add','Change','Delete','Back'],
    'Face Data':['Add','Delete','Back'],
    'Access Time':['Change','Back'],
    'Speed':['Change','Back'],
    'Open Time':['Change','Back'],
    'Calibrate':['Start','Back'],
    'Show password':['On/Off','Back'],
    'Exit':['Exit']
    }
PANEL_COMMANDS = {
    'Password':'PASSWORD',
    'Face Data':'FACE_DATA',
    'Access Time':'ACCESS_TIME',
    'Speed':'SPEED',
    'Open Time':'OPENTIME',
    'Calibrate':'CALIBRATING_VALUE',
    'Show password':'SHOW_PASSWORD'
    }
ser = SerialCom()
lock = threading.Lock()
face_rec = None
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
    def __init__(self,panel,parent:str,serial,optional_action=None) -> None:
        self.cursor = 0
        self.panel = panel #if not select: Add, Change, Delete,...
        self.parent = parent #Password,..
        self.keys = list(panel)
        self.ser = serial
        self.value = ''
        self.optional_action = optional_action
        self.OoF = False # Out of focus
        self.return_focus = False
        self.subPanel = None
        self.is_selects_panel = type(panel) != str
            
    def handle_key(self,key):
        if self.OoF and self.subPanel != None:
            self.subPanel.handle_key(key)
            self.OoF = self.subPanel.check_focus_scope()
            if self.OoF == False and self.is_selects_panel:
                self.render()
            return
        if key != '*' and key != '#' and not self.is_selects_panel:
            self.modify(key)
        elif key == 'A':
            self.move_up()
        elif key == 'C':
            self.move_down()
        elif key == 'B':
            self.select()
        elif key == 'D':
            self.back()
        
    def select(self):
        if self.is_selects_panel:
            if self.keys[self.cursor] == 'Back':
                self.back()
            if self.keys[self.cursor] == 'Exit':
                self.exit()
            else:
                #Need review
                panel = self.panel[self.keys[self.cursor]] if type(self.panel) == dict else self.panel[self.cursor]
                parent = self.keys[self.cursor] if type(self.panel) == dict else self.parent
                if self.parent in PANEL_COMMANDS and (panel == 'Change' or panel == 'Delete'):
                    global data
                    index  = PANEL_COMMANDS[self.parent]
                    if type(data[index]) == list:
                        self.subPanel = AdminPanel(data[index],self.parent,self.ser,panel)
                        self.subPanel.render()
                        self.OoF = True
                    else:
                        v = data[index]
                        self.subPanel = AdminPanel(v,self.parent,self.ser,self.panel[self.cursor])
                        self.subPanel.render()
                        self.OoF = True
                else:
                    self.subPanel = AdminPanel(panel,parent,self.ser,self.optional_action)
                    self.subPanel.render()
                    self.OoF = True
        else:
            
            pass

    def back(self):
        self.return_focus = True
    def move_up(self):
        if self.cursor == 0 or not self.is_selects_panel:
            return
        self.cursor -= 1
        self.render()
    def move_down(self):
        if not self.is_selects_panel:
            return
        if self.cursor == len(self.panel) -1:
            self.cursor = 0
        else:
            self.cursor += 1
        self.render()
    def render(self):
        if not self.is_selects_panel:
            self.modify()
            return
        start_position = self.cursor if self.cursor % 2 == 0 else self.cursor - 1
        render_text = ''
        for i in range(start_position,start_position+2):
            if i >= len(self.panel):
                break
            if self.panel[self.get_key_from_cursor(i)] != '':
                if i == self.cursor:
                    render_text += '>'
                else:
                    render_text += ' '
            if  type(self.panel) == list:
                render_text += self.panel[i] + ('\n' if len(self.panel[i]) < 16 else '')
            else:
                render_text += self.get_key_from_cursor(i) + ('\n' if len(self.get_key_from_cursor(i)) < 16 else '')
            self.ser.send(parse_command('DISPLAY_MESSAGE',render_text))
            self.ser.send(parse_command('END'))
    def get_key_from_cursor(self,cursor):
        if type(self.panel) == list:
            return cursor
        return self.keys[cursor]
    def exit(self):
        AdminPanel.authorized = False
        self.return_focus = True
    def modify(self,key=None):
        global PANEL_COMMANDS,data,face_rec
        custom_display = False
        if key != None or self.optional_action or self.panel in  ['Start','On/Off']:
            if key == 'D':
                if len(self.value) > 0:
                    self.value = self.value[:-1]
                else:
                    self.back()
            if self.optional_action == 'Delete':
                self.value = 'Yes[B]/No[D]?'
                if key == 'B':
                    index  = PANEL_COMMANDS[self.parent]
                    if index == 'FACE_DATA':
                        face_rec.remove_face_data(self.panel)
                    else:
                        data[index].remove(self.panel)
                    self.back()
                    save_setting()
                elif key == 'D':
                    self.back()
            elif self.optional_action == 'Change' and self.value == '' and key == None:
                self.value = self.panel
            elif self.optional_action == 'Add' or self.panel == 'Add':
                index  = PANEL_COMMANDS[self.parent]
                if index == 'FACE_DATA':
                    Recognition.take = True
                    render_text = 'Taking picture..'
                    self.ser.send(parse_command('DISPLAY_MESSAGE',render_text))
                    while Recognition.take:
                        pass
                    custom_display = True
                    render_text = 'New user saved.'
                    save_setting()
                    self.back()
                elif key == 'B':
                    data[index].append(self.value)
                    Console.Log(self.parent,'Saved')
                    self.back()
                    save_setting()
            elif self.panel == 'Start' and key == None:
                self.ser.send(parse_command('CALIBRATING'))
                self.ser.send(parse_command('GET_CALIBRATING_VALUE'))
                self.back()
                save_setting()
            elif self.panel == 'On/Off' and key == None:
                index  = PANEL_COMMANDS[self.parent]
                data[index] = not data[index]
                render_text = f'{self.parent} \nset to {"On" if data[index] else "Off"}'
                custom_display = True
                save_setting()
                self.back()
            elif self.optional_action == 'Change' and key == 'B':
                index  = PANEL_COMMANDS[self.parent]
                if type(data[index]) == list:
                    data[index][data[index].index(self.panel)] = self.value
                else:
                    data[index] = self.value
                self.back()
                Console.Log("Sending config to arduino")
                self.ser.send(parse_command('SET_ACCESS_TIME',str(data['ACCESS_TIME'])))
                self.ser.send(parse_command('SET_SPEED',str(get_preloader(data['SPEED']))))
                self.ser.send(parse_command('SET_OPENTIME',str(data['OPENTIME'])))
                self.ser.send(parse_command('SET_CALIBRATING_VALUE',str(data['CALIBRATING_VALUE'])))
                Console.Log("Config sent")
                save_setting()
            
            if not key in ['A','B','C','D','*'] and key != None:
                self.value += key

        if not custom_display:
            if self.optional_action == None:
                render_text = f'{self.panel} {self.parent}:\n{self.value}'
            else:
                render_text = f'{self.optional_action} {self.parent}:\n{self.value}'
        self.ser.send(parse_command('DISPLAY_MESSAGE',render_text))
        self.ser.send(parse_command('END'))
    def check_focus_scope(self):
        return not self.return_focus
           
        

        
  
def serial_handler():
    global data
    password = Password()
    admin_panel = None
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
                    admin_panel = AdminPanel(ADMIN_PANEL,"",ser)
                    AdminPanel.authorized = True
                    admin_panel.render()
                    #admin_panel.render_panel()
            else:
                #if value == 'B':
                #    ser.send(parse_command('DISPLAY_MESSAGE','Capturing image'))
                #    ser.send(parse_command('END'))
                #    Recognition.take = True
                admin_panel.handle_key(value)
                if AdminPanel.authorized == False:
                    ser.send(parse_command('DISPLAY_MESSAGE','Setting saved'))
                    password.show_password = data['SHOW_PASSWORD']
                    password.clear_password()
                    time.sleep(2)
                    password.display_password()
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
        if command == COMMANDS['SET_CALIBRATING_VALUE']:
            data['SET_CALIBRATING_VALUE'] = value
        

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
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding,0.54)
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
                if Recognition.take:
                    self.save_new_face(frame,face_encoding)
            Recognition.detected = len(face_locations)
            Recognition.authorized = [face for face in faces if face != 'Unknown']
            #Console.Log("Faces: {}".format(Recognition.authorized))
            
                
            # Display the resulting image
            

    def save_new_face(self,frame,face_encoding):
        #save new face
        global lock,data
        if self.ret:
                name = f"Face_{len(self.known_face_names)}"
                self.known_face_encodings.append(face_encoding)
                self.known_face_names.append(name)
                data['FACE_DATA'] = self.known_face_names
                with open("config.json", 'w') as f:
                    json.dump(data,f)
                with open(FACE_DIR+"face_data.pickle", 'wb') as f:
                    pickle.dump(self.known_face_encodings, f)
                #save the frame 
                cv2.imwrite(FACE_DIR+f"{name}.jpg",frame)
                Console.Log("New face added:" + f"{name}" )
                Recognition.take = False
    def remove_face_data(self,name):
        global data
        #remove face data
        if name in self.known_face_names:
            index = self.known_face_names.index(name)
            if len(self.known_face_encodings) -1 < index:
                index = len(self.known_face_encodings) -1
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
    global data,face_rec
    
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
    ser.send(parse_command('SET_SPEED',str(get_preloader(data['SPEED']))))
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
    
    