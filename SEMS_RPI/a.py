
from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import cv2

# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 32
rawCapture = PiRGBArray(camera, size=(640, 480))

# allow the camera to warmup
time.sleep(0.1)

# capture frames from the camera
for i in range(10):
    camera.capture(rawCapture, format="bgr")
    image = rawCapture.array
    cv2.imwrite(f"image_{i}.jpg", image)
    rawCapture.truncate(0)
