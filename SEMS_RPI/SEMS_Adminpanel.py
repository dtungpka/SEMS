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
FACE_DIR = ""
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
data = {
    'CALIBRATING_VALUE':'1000',
    'ACCESS_TIME':'60000',
    'SPEED':'50',
    'OPENTIME':'60000',
    'PASSWORD':[ '1234'],
    'ADMIN_PASSWORD':'0301011',
    'FACE_DATA':['Face_0','Face_1'], #id, encoding
    'SHOW_PASSWORD':False
    }

lock = threading.Lock()
        

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


if not os.path.isfile(FACE_DIR+"face_data.pickle"):
        known_face_encodings = []
        known_face_names = []
else:
    with open(FACE_DIR+"face_data.pickle", 'rb') as f:
        loaded_data = pickle.load(f)
        known_face_encodings = loaded_data
rec = Recognition(known_face_encodings,['Face_0','Face_1'])
rec.remove_face_data('Face_0')
rec.run()