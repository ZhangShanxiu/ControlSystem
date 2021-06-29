#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/5/30 16:06
# @Author  : Zhang Shanxiu
from PyQt5.QtCore import QThread, pyqtSignal
import psutil
import traceback
# from main import ControlSystem


class Graph(QThread):
    graphSignal = pyqtSignal()
    graphTextSignal = pyqtSignal(str, str)
    dataList = list()

    def __init__(self):
        super(Graph, self).__init__()
        self.working = False

    def __del__(self):
        # print('绘图线程', self.currentThreadId(), '退出')
        self.working = False
        # self.wait()

    def run(self):
        print('绘图线程' + str(self.currentThreadId()) + '启动')
        self.graphTextSignal.emit('绘图线程' + str(self.currentThreadId()) + '启动...', 'i')

        while self.working:
            self.sleep(1)
            try:
                cpu = "%0.2f" % psutil.cpu_percent(interval=1)
                self.dataList.append(float(cpu))
                self.graphSignal.emit()
            except Exception as e:
                print(traceback.print_exc())