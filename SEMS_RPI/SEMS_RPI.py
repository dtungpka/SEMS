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


PORT = 'COM8'
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
    'CALIBRATING_VALUE':100,
    'ACCESS_TIME':10000,
    'SPEED':57722,
    'OPENTIME':10000,
    'PASSWORD':[ '1234'],
    'ADMIN_PASSWORD':'0000',
    'FACE_DATA':[]
    
    }


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

ser = SerialCom()
lock = threading.Lock()
def serial_handler():
    while True:
        msg = ser.read()
        

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
            known_face_encodings = loaded_data['known_face_encodings']
            known_face_names = loaded_data['known_face_names']
    Console.Log("Face data loaded")
    face_locations = []
    face_encodings = []
    face_names = []
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
    while True:
        ret, frame = video_capture.read()

        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_small_frame = small_frame[:, :, ::-1]

        # Only process every other frame of video to save time
        if process_this_frame:
            # Find all the faces and face encodings in the current frame of video
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            face_names = []
            for face_encoding in face_encodings:
                # See if the face is a match for the known face(s)
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = "Unknown"

                # # If a match was found in known_face_encodings, just use the first one.
                # if True in matches:
                #     first_match_index = matches.index(True)
                #     name = known_face_names[first_match_index]

                # Or instead, use the known face with the smallest distance to the new face
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]

                face_names.append(name)

        process_this_frame = not process_this_frame


        # Display the results
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Draw a box around the face
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

            # Draw a label with a name below the face
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

        # Display the resulting image
        cv2.imshow('Video', frame)

        # Hit 'q' on the keyboard to quit!
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
        
if __name__ == "__main__":
    main()
    
    