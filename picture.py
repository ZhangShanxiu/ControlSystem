#!/usr/bin/env python
# -*- coding: utf-8 -*-
from PyQt5.QtCore import QThread, pyqtSignal
from camera import Camera
import cv2
# import pixellib
# from pixellib.semantic import semantic_segmentation
# import time


class Picture(QThread):
    pictureSignal = pyqtSignal()
    pictureTextSignal = pyqtSignal(str, str)
    processdImage = None
    threshold = 23
    filter_kernel = 8
    dilate_iterations = 5

    def __init__(self):
        super().__init__()
        self.working = False
        self.minArea = 50

        self.firstFrame = None
        self.text = "Unoccupied"

        # 用于计算三维坐标的首次进入标志位
        self.first = True
        self.FlagCreateBar = True

    def __del__(self):
        # print('图片线程', self.currentThreadId(), '退出')
        self.working = False
        # self.wait()

    def run(self):
        print('图片线程' + str(self.currentThreadId()) + '启动')
        self.pictureTextSignal.emit('图片线程' + str(self.currentThreadId()) + '启动...', 'i')
        while self.working:
            if Camera.colorImage is None:
                continue
            Picture.processdImage = Camera.colorSource.copy()
            # Picture.processdImage = cv2.cvtColor(Picture.processdImage, cv2.COLOR_RGB2BGR)
            # 创建灰度图像
            gray = cv2.cvtColor(Picture.processdImage, cv2.COLOR_BGR2GRAY)
            kernel = 2 * self.filter_kernel +1
            gray = cv2.GaussianBlur(gray, (kernel, kernel), 0)

            # 使用两帧图像做比较，检测移动物体的区域
            if self.firstFrame is None:
                self.firstFrame = gray
                continue
            frameDelta = cv2.absdiff(self.firstFrame, gray)

            thresh = cv2.threshold(frameDelta, self.threshold, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=self.dilate_iterations)
            cnts, hierarchy = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # cv2.namedWindow("thresh", cv2.WINDOW_AUTOSIZE)
            # cv2.imshow("thresh", thresh)
            # cv2.waitKey(1)
            for c in cnts:
                # 如果检测到的区域小于设置值，则忽略
                # if cv2.contourArea(c) < self.minArea:
                #    continue

                # if cv2.contourArea(c) > 200 or cv2.contourArea(c) < 10:
                #     continue

                # 在输出画面上框出识别到的物体
                (x, y, w, h) = cv2.boundingRect(c)

                # if x >= 540 or y <= 90:
                #     continue

                # if h / w > 1.2 or w / h > 1.2:
                #    continue

                # if w < 10:
                #     continue

                cv2.rectangle(Picture.processdImage, (x, y), (x + w, y + h), (50, 255, 50), 2)
                self.text = "Occupied"

                # print (x, y, w, h, self.pixel.x, self.pixel.y)

                # 在输出画面上打印面积
                cv2.putText(Picture.processdImage, "{}".format(cv2.contourArea(c)), (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

                # self.coordinate_map(x, y)
            # 在输出画面上打当前状态和时间戳信息
            # cv2.putText(Picture.processdImage, "Status: {}".format(self.text), (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            Picture.processdImage = cv2.cvtColor(Picture.processdImage, cv2.COLOR_BGR2RGB)
            self.pictureSignal.emit()
        # while self.working:
        #     if Camera.colorImage is None:
        #         continue
        #     Picture.processdImage = Camera.colorSource.copy()
        #     segment_image = semantic_segmentation()
        #     segment_image.load_pascalvoc_model('mask_rcnn_coco.h5')
        #     start = time.time()
        #     segment_image.segmentImage("sample2.jpg", output_image_name = "image_new.jpg", show_bboxes = True)
        #     end = time.time()
        #     print(f'Inference Time: {end - start: .2f}seconds')
        #     Picture.processdImage = cv2.cvtColor(Picture.processdImage, cv2.COLOR_BGR2RGB)
        #     self.pictureSignal.emit()
