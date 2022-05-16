import os
import os.path as osp
import sys
BUILD_DIR = osp.join(osp.dirname(osp.abspath(__file__)), "build/service/")
sys.path.insert(0, BUILD_DIR)
import argparse

import grpc
from concurrent import futures
import fib_pb2
import fib_pb2_grpc

##################################################3
import cv2
import argparse
from multiprocessing import Process, Queue
import numpy as np
import mediapipe as mp
mp_hands = mp.solutions.hands
mp_drawing_styles = mp.solutions.drawing_styles
mp_drawing = mp.solutions.drawing_utils

mp_object_detection = mp.solutions.object_detection

mp_pose = mp.solutions.pose

DSR = 10

# mode = 0    # 0 for hand / 1 for object / 2 for pose

class FibCalculatorServicer(fib_pb2_grpc.FibCalculatorServicer):

    def __init__(self, q):
        self.q = q 
        pass

    def Compute(self, request, context):
        n = request.order
        self.q.put(n)
        #print(self.q.size())
        response = fib_pb2.FibResponse()
        response.value = n

        return response


def GRPC(ip, port, q):
    servicer = FibCalculatorServicer(q)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    fib_pb2_grpc.add_FibCalculatorServicer_to_server(servicer, server)

    try:
        server.add_insecure_port(f"{ip}:{port}")
        server.start()
        print(f"Run gRPC Server at {ip}:{port}")
        server.wait_for_termination()
    except KeyboardInterrupt:
        pass

def gstreamer_camera(queue):
    # Use the provided pipeline to construct the video capture in opencv
    pipeline = (
        "nvarguscamerasrc ! "
            "video/x-raw(memory:NVMM), "
            "width=(int)800, height=(int)600, "
            "format=(string)NV12, framerate=(fraction)30/1 ! "
        "queue ! "
        "nvvidconv flip-method=2 ! "
            "video/x-raw, "
            "width=(int)800, height=(int)600, "
            "format=(string)BGRx, framerate=(fraction)30/1 ! "
        "videoconvert ! "
            "video/x-raw, format=(string)BGR ! "
        "appsink"
    )
    # Complete the function body
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    try:
        while True :
            ret, frame = cap.read()
            if not ret:
                break
            queue.put(frame)
    except KeyboardInterrupt as e:
        cap.release()
    pass


def gstreamer_rtmpstream(queue, q):
    # Use the provided pipeline to construct the video writer in opencv
    pipeline = (
        "appsrc ! "
            "video/x-raw, format=(string)BGR ! "
        "queue ! "
        "videoconvert ! "
            "video/x-raw, format=RGBA ! "
        "nvvidconv ! "
        "nvv4l2h264enc bitrate=8000000 ! "
        "h264parse ! "
        "flvmux ! "
        'rtmpsink location="rtmp://localhost/rtmp/live live=1"'
    )
    # Complete the function body
    # You can apply some simple computer vision algorithm here
    fps = 30
    width = 800
    height = 600
    out = cv2.VideoWriter(pipeline, cv2.CAP_GSTREAMER, 0, float(fps), (width, height))
    try:
        count = 0
        last_hand_landmarks = []
        last_objects = []
        last_pose_landmarks = []

        hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        object_detection =  mp_object_detection.ObjectDetection(min_detection_confidence=0.1)
        pose = mp_pose.Pose(static_image_mode=True, model_complexity=0, enable_segmentation=True, min_detection_confidence=0.5)
        mode = 0
        while True:
            if not q.empty():
                mode = q.get()
                print(mode)
            if queue.empty():
                continue
            frame = queue.get()
            count += 1
            count %= DSR
            if count % DSR == 0:
                #frame.flags.writeable = False
                if mode == 1:
                    results = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    if results.multi_hand_landmarks:
                        last_hand_landmarks = results.multi_hand_landmarks 
                    else:
                        last_hand_landmarks = []
                elif mode == 2:
                    results = object_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    if results.detections:
                        last_objects = results.detections
                    else:
                        last_objects = []
                elif mode == 3:
                    results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    if results.pose_landmarks:
                        last_pose_landmarks = results.pose_landmarks
                    else:
                        last_pose_landmarks = []
                #frame.flags.writeable = True
            if mode == 1:
                for mark in last_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame,
                        mark,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style()
                    )
            elif mode == 2:
                for detection in last_objects:
                    mp_drawing.draw_detection(frame, detection)
            elif mode == 3:
                mp_drawing.draw_landmarks(frame, last_pose_landmarks, mp_pose.POSE_CONNECTIONS, landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style())

            out.write(frame)
    except KeyboardInterrupt as e:
        out.release()

def grpc_func(ip, port, q):
    GRPC(ip, port, q)
    

# Complelte the code
if __name__ == "__main__":
    ip = "0.0.0.0"
    port = 5487
    qq = Queue(maxsize=10)  # writer() writes to qq from _this_ process
    q = Queue(maxsize=10)  # writer() writes to qq from _this_ process
    producer = Process(target=gstreamer_camera, args=((qq),))
    producer.start()  # Launch another proc

    consumer = Process(target=gstreamer_rtmpstream, args=((qq), q))
    consumer.start()  # Launch another proc

    grpcer = Process(target=grpc_func, args=(ip, port, q))
    grpcer.start()
    

