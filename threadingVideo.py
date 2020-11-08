#!/usr/bin/env python3

import threading
import cv2
import numpy as np
import queue

class VideoBuffer:
    Lock = None
    Full = None
    Empty = None
    Queue = None
    numItems = 0

    def __init__(self, initialCapacity=10):
        self.QLock = threading.Lock()
        self.Full = threading.Semaphore(0)
        self.Empty = threading.Semaphore(initialCapacity)
        self.Queue = queue.Queue()

    def addItem(self, item):
        self.Empty.acquire()
        self.QLock.acquire()
        self.Queue.put(item)
        self.numItems += 1
        self.QLock.release()
        self.Full.release()

    def getItem(self):
        self.Full.acquire()
        self.QLock.acquire()
        element = self.Queue.get()
        self.numItems -= 1
        self.QLock.release()
        self.Empty.release()
        return element

    def isEmpty(self):
        return self.numItems == 0

def extractFrames(filename, outputQueue, compLock):
    count = 0
    #open video clip
    vidcap = cv2.VideoCapture(filename)
    #reads 1 frame
    success, image = vidcap.read()

    print("Reading frame {}".format(count))
    while success:
        #to jpeg
        success, jpgImage = cv2.imencode('.jpg', image)

        #add frame to queue
        outputQueue.addItem(jpgImage)

        success,image = vidcap.read()
        print('Reading frame {}'.format(count))
        count += 1
    compLock.release()
    print("Frame extraction complete release")

def convertToGreyscale(inputQueue, outputQueue, inputLock, outputLock):
    count = 0
    complete = False
    complete = inputLock.acquire(blocking = False) and inputQueue.isEmpty()
    while not complete:
        inputFrame = inputQueue.getItem()
        greyFrame = cv2.imdecode(inputFrame, cv2.IMREAD_COLOR)

        print("Converting frame {}".format(count))

        greyImg = cv2.cvtColor(greyFrame, cv2.COLOR_BGR2GRAY)

        success, jpgGreyImg = cv2.imencode('.jpg', greyImg)

        #add frame to buffer
        outputQueue.addItem(jpgGreyImg)
        if inputQueue.isEmpty():
            if inputLock.acquire(blocking = False):
                complete = True

        count += 1
    outputLock.release()

def displayFrames(inputQueue, compLock):
    count = 0
    complete = False

    complete = compLock.acquire(blocking = False) and inputQueue.isEmpty()

    while not complete:
        #gets next frame
        frameAsText = inputQueue.getItem()
        jpgImage = np.asarray(bytearray(frameAsText), dtype=np.uint8)

        #get encoded frame
        img = cv2.imdecode(jpgImage, cv2.IMREAD_UNCHANGED)

        print("Displaying frame {}".format(count))

        #diplay img
        cv2.imshow("Video", img)
        if cv2.waitKey(42) and 0xFF == ord('q'):
            break

        count += 1

        if inputQueue.isEmpty():
            if compLock.acquire(blocking = False):
                complete = True

    cv2.destroyAllWindows()
    print("Done displaying frames")

filename = "clip.mp4"

#lock for extraction, unlock when done
extractionLock = threading.Lock()
extractionLock.acquire()

#lock for conversion, unlock when done
conversionLock = threading.Lock()
conversionLock.acquire()

#queue for extaction and greyscale
extractionQueue = VideoBuffer(10)
greyScaleQueue = VideoBuffer(10)

#extract frames
extractionThread = threading.Thread(target=extractFrames, args=(filename, extractionQueue, extractionLock))

#convert frames
conversionThread = threading.Thread(target=convertToGreyscale, args=(extractionQueue, greyScaleQueue, extractionLock, conversionLock))

#display frames
displayThread = threading.Thread(target=displayFrames, args=(greyScaleQueue, conversionLock))

extractionThread.start()
conversionThread.start()
displayThread.start()
