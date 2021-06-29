#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/5/29 11:58
# @Author  : Zhang Shanxiu
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import uic
from camera import Camera
from graph import Graph
from picture import Picture
import numpy as np
from loadStyle import LoadStyle
import pyqtgraph as pg
from zmotion import ZMCWrapper


class ControlSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.threadGraph = Graph()
        self.threadCamera = Camera()
        self.threadPicture = Picture()
        self.threadZmotion = ZMCWrapper()
        self.gif3 = QMovie('./gif/default3.gif')
        self.gif2 = QMovie('./gif/default2.gif')
        self.gif1 = QMovie('./gif/default1.gif')
        self.stopGif = False
        self.initUI()

    def initUI(self):
        uic.loadUi('./ui.ui', self)
        styleFile = './style.qss'
        style = LoadStyle.readQSS(styleFile)
        self.setStyleSheet(style)
        self.showMaximized()
        self.printf('主线程' + str(QThread.currentThreadId()) + "启动...", 'i')

        # 设置图片
        self.Btn_OpenCamera.setIcon(QIcon('./res/openCamera.png'))
        self.Btn_OpenCamera.setIconSize(QSize(51, 51))

        self.Btn_Run.setIcon(QIcon('./res/close.png'))
        self.Btn_Run.setIconSize(QSize(51, 51))

        self.Btn_Debug.setIcon(QIcon('./res/debugIn.png'))
        self.Btn_Debug.setIconSize(QSize(51, 51))

        self.Btn_Set.setIcon(QIcon('./res/repair.png'))
        self.Btn_Set.setIconSize(QSize(51, 51))

        self.Btn_Back.setIcon(QIcon('./res/back2.png'))
        self.Btn_Back.setIconSize(QSize(51, 51))

        self.gif1.setScaledSize(QSize(self.label_RGB.width(), self.label_RGB.height()))
        self.label_RGB.setMovie(self.gif1)
        self.gif1.start()

        self.gif2.setScaledSize(QSize(self.label_Depth.width(), self.label_Depth.height()))
        self.label_Depth.setMovie(self.gif2)
        self.gif2.start()

        self.gif3.setScaledSize(QSize(self.label_Picture.width(), self.label_Picture.height()))
        self.label_Picture.setMovie(self.gif3)
        self.gif3.start()

        # 摄像头按钮
        self.Btn_OpenCamera.clicked.connect(self.dealOpenCamera)
        self.Btn_OpenCamera.setToolTip('Camera On')
        # 链接按钮
        self.Btn_Debug.clicked.connect(self.dealDebug)
        self.Btn_Debug.setToolTip('Debug In')
        # 运行按钮
        self.Btn_Run.clicked.connect(self.dealRun)
        self.Btn_Run.setToolTip('Run')
        # 设置按钮
        self.Btn_Set.clicked.connect(self.dealSet)
        # 备用按钮
        self.Btn_Back.clicked.connect(self.dealBack)
        self.Btn_Back.setToolTip('Graph Start')

        self.threadCamera.cameraSignal.connect(self.dealCameraSignal)
        self.threadCamera.cameraTextSignal.connect(self.printf)
        self.threadGraph.graphSignal.connect(self.dealGraphSignal)
        self.threadGraph.graphTextSignal.connect(self.printf)
        self.threadPicture.pictureSignal.connect(self.dealPictureSignal)
        self.threadPicture.pictureTextSignal.connect(self.printf)
        self.threadZmotion.zmotionSignal.connect(self.dealZmotionSignal)
        self.threadZmotion.zmotionConnectFlag.connect(self.dealZmotionConnectFlag)
        self.threadZmotion.zmotionTextSignal.connect(self.printf)

        # SpinBox
        self.spinBoxUnits.valueChanged.connect(self.spinBoxUnitsValueChanged)
        self.spinBoxLspeed.valueChanged.connect(self.spinBoxLspeedValueChanged)
        self.spinBoxRspeed.valueChanged.connect(self.spinBoxRspeedValueChanged)
        self.spinBoxCreep.valueChanged.connect(self.spinBoxCreepValueChanged)
        self.spinBoxAcc.valueChanged.connect(self.spinBoxAccValueChanged)
        self.spinBoxDec.valueChanged.connect(self.spinBoxDecValueChanged)
        self.spinBoxSramp.valueChanged.connect(self.spinBoxSrampValueChanged)
        self.spinBoxThreshold.valueChanged.connect(self.spinBoxThresholdValueChanged)
        self.spinBoxFilterKernel.valueChanged.connect(self.spinBoxFilterKernelValueChanged)
        self.spinBoxDilate.valueChanged.connect(self.spinBoxDilateValueChanged)

        # Slider
        self.horizontalSliderUnits.valueChanged.connect(self.sliderUnitsValueChanged)
        self.horizontalSliderLspeed.valueChanged.connect(self.sliderLspeedValueChanged)
        self.horizontalSliderRspeed.valueChanged.connect(self.sliderRspeedValueChanged)
        self.horizontalSliderCreep.valueChanged.connect(self.sliderCreepValueChanged)
        self.horizontalSliderAcc.valueChanged.connect(self.sliderAccValueChanged)
        self.horizontalSliderDec.valueChanged.connect(self.sliderDecValueChanged)
        self.horizontalSliderSramp.valueChanged.connect(self.sliderSrampValueChanged)
        self.horizontalSliderThreshold.valueChanged.connect(self.sliderThresholdValueChanged)
        self.horizontalSliderFilterKernel.valueChanged.connect(self.sliderFilterKernelValueChanged)
        self.horizontalSliderDilate.valueChanged.connect(self.sliderDilateValueChanged)

        # CheckBox
        self.checkBox1.stateChanged.connect(self.checkBox1StateChanged)
        self.checkBox2.stateChanged.connect(self.checkBox2StateChanged)
        self.checkBox3.stateChanged.connect(self.checkBox3StateChanged)
        self.checkBox4.stateChanged.connect(self.checkBox4StateChanged)
        self.checkBox5.stateChanged.connect(self.checkBox5StateChanged)
        self.checkBox6.stateChanged.connect(self.checkBox6StateChanged)

        # QRadioButton
        self.radioButton1Forward.toggled.connect(self.radioButton1Toggled)
        self.radioButton2Forward.toggled.connect(self.radioButton2Toggled)
        self.radioButton3Forward.toggled.connect(self.radioButton3Toggled)
        self.radioButton4Forward.toggled.connect(self.radioButton4Toggled)
        self.radioButton5Forward.toggled.connect(self.radioButton5Toggled)
        self.radioButton6Forward.toggled.connect(self.radioButton6Toggled)

        # self.dealGraphDisplay()
        font = QFont()
        font.setFamily("宋体")
        font.setPixelSize(18)
        self.textBrowser.setFont(font)
        self.textBrowser.setObjectName("textBrowser")

    # SpinBox
    def spinBoxUnitsValueChanged(self):
        self.horizontalSliderUnits.setValue(self.spinBoxUnits.value())
        ZMCWrapper.m_units = self.spinBoxUnits.value()

    def spinBoxLspeedValueChanged(self):
        self.horizontalSliderLspeed.setValue(self.spinBoxLspeed.value())
        ZMCWrapper.m_lspeed = self.spinBoxLspeed.value()

    def spinBoxRspeedValueChanged(self):
        self.horizontalSliderRspeed.setValue(self.spinBoxRspeed.value())
        ZMCWrapper.m_rspeed = self.spinBoxRspeed.value()

    def spinBoxCreepValueChanged(self):
        self.horizontalSliderCreep.setValue(self.spinBoxCreep.value())
        ZMCWrapper.m_creep = self.spinBoxCreep.value()

    def spinBoxAccValueChanged(self):
        self.horizontalSliderAcc.setValue(self.spinBoxAcc.value())
        ZMCWrapper.m_acc = self.spinBoxAcc.value()

    def spinBoxDecValueChanged(self):
        self.horizontalSliderDec.setValue(self.spinBoxDec.value())
        ZMCWrapper.m_dec = self.spinBoxDec.value()

    def spinBoxSrampValueChanged(self):
        self.horizontalSliderSramp.setValue(self.spinBoxSramp.value())
        ZMCWrapper.m_sramp = self.spinBoxSramp.value()

    def spinBoxThresholdValueChanged(self):
        self.horizontalSliderThreshold.setValue(self.spinBoxThreshold.value())
        Picture.threshold = self.spinBoxThreshold.value()

    def spinBoxFilterKernelValueChanged(self):
        self.horizontalSliderFilterKernel.setValue(self.spinBoxFilterKernel.value())
        Picture.filter_kernel = self.spinBoxFilterKernel.value()

    def spinBoxDilateValueChanged(self):
        self.horizontalSliderDilate.setValue(self.spinBoxDilate.value())
        Picture.dilate_iterations = self.spinBoxDilate.value()

    # Slider
    def sliderUnitsValueChanged(self):
        self.spinBoxUnits.setValue(self.horizontalSliderUnits.value())
        ZMCWrapper.m_units = self.horizontalSliderUnits.value()

    def sliderLspeedValueChanged(self):
        self.spinBoxLspeed.setValue(self.horizontalSliderLspeed.value())
        ZMCWrapper.m_lspeed = self.horizontalSliderLspeed.value()

    def sliderRspeedValueChanged(self):
        self.spinBoxRspeed.setValue(self.horizontalSliderRspeed.value())
        ZMCWrapper.m_rspeed = self.horizontalSliderRspeed.value()

    def sliderCreepValueChanged(self):
        self.spinBoxCreep.setValue(self.horizontalSliderCreep.value())
        ZMCWrapper.m_creep = self.horizontalSliderCreep.value()

    def sliderAccValueChanged(self):
        self.spinBoxAcc.setValue(self.horizontalSliderAcc.value())
        ZMCWrapper.m_acc = self.horizontalSliderAcc.value()

    def sliderDecValueChanged(self):
        self.spinBoxDec.setValue(self.horizontalSliderDec.value())
        ZMCWrapper.m_dec = self.horizontalSliderDec.value()

    def sliderSrampValueChanged(self):
        self.spinBoxSramp.setValue(self.horizontalSliderSramp.value())
        ZMCWrapper.m_sramp = self.horizontalSliderSramp.value()

    def sliderThresholdValueChanged(self):
        self.spinBoxThreshold.setValue(self.horizontalSliderThreshold.value())
        Picture.threshold = self.horizontalSliderThreshold.value()

    def sliderFilterKernelValueChanged(self):
        self.spinBoxFilterKernel.setValue(self.horizontalSliderFilterKernel.value())
        Picture.filter_kernel = self.horizontalSliderFilterKernel.value()

    def sliderDilateValueChanged(self):
        self.spinBoxDilate.setValue(self.horizontalSliderDilate.value())
        Picture.dilate_iterations = self.horizontalSliderDilate.value()

    def checkBox1StateChanged(self):
        if self.checkBox1.isChecked():
            ZMCWrapper.m_axisSelect[0] = True
        else:
            ZMCWrapper.m_axisSelect[0] = False
        ZMCWrapper.m_axisDir[0] = 1 if self.radioButton1Forward.isChecked() else -1

    def checkBox2StateChanged(self):
        if self.checkBox2.isChecked():
            ZMCWrapper.m_axisSelect[1] = True
        else:
            ZMCWrapper.m_axisSelect[1] = False
        ZMCWrapper.m_axisDir[1] = 1 if self.radioButton2Forward.isChecked() else -1

    def checkBox3StateChanged(self):
        if self.checkBox3.isChecked():
            ZMCWrapper.m_axisSelect[2] = True
        else:
            ZMCWrapper.m_axisSelect[2] = False
        ZMCWrapper.m_axisDir[2] = 1 if self.radioButton3Forward.isChecked() else -1

    def checkBox4StateChanged(self):
        if self.checkBox4.isChecked():
            ZMCWrapper.m_axisSelect[3] = True
        else:
            ZMCWrapper.m_axisSelect[3] = False
        ZMCWrapper.m_axisDir[3] = 1 if self.radioButton4Forward.isChecked() else -1

    def checkBox5StateChanged(self):
        if self.checkBox5.isChecked():
            ZMCWrapper.m_axisSelect[4] = True
        else:
            ZMCWrapper.m_axisSelect[4] = False
        ZMCWrapper.m_axisDir[4] = 1 if self.radioButton5Forward.isChecked() else -1

    def checkBox6StateChanged(self):
        if self.checkBox6.isChecked():
            ZMCWrapper.m_axisSelect[5] = True
        else:
            ZMCWrapper.m_axisSelect[5] = False
        ZMCWrapper.m_axisDir[5] = 1 if self.radioButton6Forward.isChecked() else -1

    def radioButton1Toggled(self):
        ZMCWrapper.m_axisDir[0] = 1 if self.radioButton1Forward.isChecked() else -1

    def radioButton2Toggled(self):
        ZMCWrapper.m_axisDir[1] = 1 if self.radioButton2Forward.isChecked() else -1

    def radioButton3Toggled(self):
        ZMCWrapper.m_axisDir[2] = 1 if self.radioButton3Forward.isChecked() else -1

    def radioButton4Toggled(self):
        ZMCWrapper.m_axisDir[3] = 1 if self.radioButton4Forward.isChecked() else -1

    def radioButton5Toggled(self):
        ZMCWrapper.m_axisDir[4] = 1 if self.radioButton5Forward.isChecked() else -1

    def radioButton6Toggled(self):
        ZMCWrapper.m_axisDir[5] = 1 if self.radioButton6Forward.isChecked() else -1

    def dealOpenCamera(self):
        if not self.stopGif:
            self.stopGif = True
            self.gif1.stop()
            self.gif2.stop()
            self.gif3.stop()

        if self.threadCamera.working:
            self.threadCamera.working = False
            self.threadPicture.working = False
        else:
            self.threadCamera.working = True
            self.threadPicture.working = True

        if self.threadCamera.working:
            self.threadCamera.start()
            # self.Btn_OpenCamera.setText('Camera Off')
            self.Btn_OpenCamera.setIcon(QIcon('./res/closeCamera.png'))
            self.Btn_OpenCamera.setToolTip('Camera Off')
        else:
            # self.Btn_OpenCamera.setText('Camera On')
            self.Btn_OpenCamera.setIcon(QIcon('./res/openCamera.png'))
            self.Btn_OpenCamera.setToolTip('Camera On')
        if self.threadPicture.working:
            self.threadPicture.start()
        self.Btn_OpenCamera.setIconSize(QSize(51, 51))

    def dealDebug(self):
        if not ZMCWrapper.m_currentMode:
            ZMCWrapper.m_currentMode = True
        else:
            ZMCWrapper.m_currentMode = False

        if ZMCWrapper.m_currentMode:
            self.Btn_Debug.setIcon(QIcon('./res/debugOut.png'))
            self.Btn_Debug.setToolTip('Debug Out')
        else:
            self.Btn_Debug.setIcon(QIcon('./res/debugIn.png'))
            self.Btn_Debug.setToolTip('Debug In')
        self.Btn_Debug.setIconSize(QSize(51, 51))

    def dealRun(self):
        if self.threadZmotion.working:
            self.threadZmotion.working = False
        else:
            self.threadZmotion.working = True

        if self.threadZmotion.working:
            self.threadZmotion.start()
        else:
            self.Btn_Run.setIcon(QIcon('./res/close.png'))
            self.Btn_Run.setToolTip('Run')

    def dealSet(self):
        pass

    def dealBack(self):
        if self.threadGraph.working:
            self.threadGraph.working = False
        else:
            self.threadGraph.working = True

        if self.threadGraph.working:
            self.threadGraph.start()
            # self.Btn_OpenCamera.setText('Camera Off')
            self.Btn_Back.setIcon(QIcon('./res/back1.png'))
            self.Btn_Back.setToolTip('Graph Stop')
        else:
            # self.Btn_OpenCamera.setText('Camera On')
            self.Btn_Back.setIcon(QIcon('./res/back2.png'))
            self.Btn_Back.setToolTip('Graph Start')
        self.Btn_Back.setIconSize(QSize(51, 51))

    def dealCameraSignal(self):
        self.label_RGB.setPixmap(QPixmap.fromImage(QImage(Camera.colorImage.data,
                                                          Camera.colorImage.shape[1],
                                                          Camera.colorImage.shape[0],
                                                          Camera.colorImage.shape[1] * 3,
                                                          QImage.Format_RGB888)))
        self.label_Depth.setPixmap(QPixmap.fromImage(QImage(Camera.depthImage.data,
                                                            Camera.depthImage.shape[1],
                                                            Camera.depthImage.shape[0],
                                                            Camera.depthImage.shape[1] * 3,
                                                            QImage.Format_RGB888)))

    # 显示曲线
    def dealGraphSignal(self):
        self.pyqtgraph_Trend.clear()
        plt = self.pyqtgraph_Trend.addPlot(title='条状图')
        x = np.arange(10)

        y1 = np.sin(x)
        y2 = 1.1 * np.sin(x + 1)
        y3 = 1.2 * np.sin(x + 2)

        bg1 = pg.BarGraphItem(x=x, height=y1, width=0.3, brush='r')
        bg2 = pg.BarGraphItem(x=x + 0.33, height=y2, width=0.3, brush='g')
        bg3 = pg.BarGraphItem(x=x + 0.66, height=y3, width=0.3, brush='b')

        plt.addItem(bg1)
        plt.addItem(bg2)
        plt.addItem(bg3)

        self.pyqtgraph_Trend.nextRow()
        p4 = self.pyqtgraph_Trend.addPlot(title='显示网格')
        x = np.cos(np.linspace(0, 2 * np.pi, 1000))
        y = np.sin(np.linspace(0, 4 * np.pi, 1000))
        p4.plot(x, y, pen=pg.mkPen(color='d', width=2))
        p4.showGrid(x=True, y=True)
        # plt = self.pyqtgraph_Trend.addPlot(title='CPU利用率')
        # x = np.arange(len(Graph.dataList))
        # bg = pg.BarGraphItem(x = x, height=Graph.dataList, width=0.3, brush='g')
        # # plt.plot(x, Graph.dataList, pen=pg.mkPen(color='d', width=2))
        # plt.addItem(bg)
        # # plt.showGrid(x=True, y=True)

    def dealPictureSignal(self):
        # print("*_*")
        self.label_Picture.setPixmap(QPixmap.fromImage(QImage(Picture.processdImage.data,
                                                          Picture.processdImage.shape[1],
                                                          Picture.processdImage.shape[0],
                                                          Picture.processdImage.shape[1] * 3,
                                                          QImage.Format_RGB888)))

    def dealZmotionSignal(self):
        print("*_*")

    def dealZmotionConnectFlag(self, s):
        if s == 'Failed':
            QMessageBox.information(self, 'Information', 'Connect Failed, Please try again later!', QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            self.Btn_Run.setIcon(QIcon('./res/close.png'))
            self.Btn_Run.setToolTip('Run')
        else:
            self.Btn_Run.setIcon(QIcon('./res/stop.png'))
            self.Btn_Run.setToolTip('Stop')

    def printf(self, s1, s2):
        if s2 == 'i':
            self.textBrowser.append(s1)                      # 在指定的区域显示提示信息
        elif s2 == 'w':
            self.textBrowser.append("<font color='yellow'>" + s1 + "<font>")  # 在指定的区域显示提示信息
        elif s2 == 'e':
            self.textBrowser.append("<font color='red'>" + s1 + "<font>")  # 在指定的区域显示提示信息
        self.cursor = self.textBrowser.textCursor()
        self.textBrowser.moveCursor(self.cursor.End)    # 光标移到最后，这样就会自动显示出来
        QApplication.processEvents()                    # 一定加上这个功能，不然有卡顿

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()


if __name__ == '__main__':
    # 创建一个应用
    app = QApplication(sys.argv)

    # 创建一个窗口
    w = ControlSystem()

    # 显示窗口
    w.show()

    # 执行窗口
    sys.exit(app.exec())
