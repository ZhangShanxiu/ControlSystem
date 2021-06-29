#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/5/29 15:17
# @Author  : Zhang Shanxiu
import pyrealsense2 as rs
import numpy as np
import cv2
from PyQt5.QtCore import QThread, pyqtSignal
# from main import ControlSystem


class Camera(QThread):
    cameraSignal = pyqtSignal()
    cameraTextSignal = pyqtSignal(str, str)
    colorImage, depthImage = None, None
    colorSource, depthSource = None, None

    def __init__(self):
        super(Camera, self).__init__()
        self.working = False

        # Configure depth and color streams
        self.pipeline = rs.pipeline()
        config = rs.config()

        # Get device product line for setting a supporting resolution
        pipeline_wrapper = rs.pipeline_wrapper(self.pipeline)
        pipeline_profile = config.resolve(pipeline_wrapper)
        device = pipeline_profile.get_device()
        device_product_line = str(device.get_info(rs.camera_info.product_line))

        found_rgb = False
        for s in device.sensors:
            if s.get_info(rs.camera_info.name) == 'RGB Camera':
                found_rgb = True
                break
        if not found_rgb:
            print("The demo requires Depth camera with Color sensor")
            exit(0)

        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 60)

        if device_product_line == 'L500':
            config.enable_stream(rs.stream.color, 960, 540, rs.format.bgr8, 30)
        else:
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 60)

        # Start streaming
        self.pipeline.start(config)

    def __del__(self):
        # print('相机线程', self.currentThreadId(), '退出')
        self.pipeline.stop()
        self.working = False
        # self.wait()

    def run(self):
        print('相机线程' + str(self.currentThreadId()) + '启动')
        self.cameraTextSignal.emit('相机线程' + str(self.currentThreadId()) + '启动...', 'i')
        while self.working:
            # print('*********************************************')
            # Wait for a coherent pair of frames: depth and color
            frames = self.pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()
            if not depth_frame or not color_frame:
                continue

            # Convert images to numpy arrays
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

            depth_colormap_dim = depth_colormap.shape
            color_colormap_dim = color_image.shape

            # If depth and color resolutions are different, resize color image to match depth image for display
            if depth_colormap_dim != color_colormap_dim:
                resized_color_image = cv2.resize(color_image, dsize=(depth_colormap_dim[1], depth_colormap_dim[0]),
                                                 interpolation=cv2.INTER_AREA)
                # images = np.hstack((resized_color_image, depth_colormap))
                Camera.colorSource = resized_color_image
                Camera.colorImage = cv2.cvtColor(resized_color_image, cv2.COLOR_BGR2RGB)
            else:
                # images = np.hstack((color_image, depth_colormap))
                Camera.colorSource = color_image
                Camera.colorImage = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
            Camera.depthSource = depth_colormap
            Camera.depthImage = cv2.cvtColor(depth_colormap, cv2.COLOR_BGR2RGB)
            # self.sleep(1)
            self.cameraSignal.emit()