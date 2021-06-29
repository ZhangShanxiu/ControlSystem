#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/4/25 16:05
# @Author  : Zhang Shanxiu
import platform
import ctypes, sys
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QObject
from PyQt5.QtWidgets import QMessageBox, QWidget, QApplication
# from main import ControlSystem


class ZMCWrapper(QThread, QObject):
    zmotionSignal = pyqtSignal()
    zmotionConnectFlag = pyqtSignal(str)
    zmotionTextSignal = pyqtSignal(str, str)
    # 轴类型：1-脉冲轴类型
    m_type = 1
    # 脉冲模式+逻辑方向
    m_invertStep = 0
    # 脉冲当量
    m_units = 8
    # 起始速度
    m_lspeed = 0
    # 运行速度
    m_rspeed = 500
    # 爬行速度
    m_creep = 10
    # 加速度
    m_acc = 3000
    # 减速度
    m_dec = 3000
    # S曲线时间：0-梯形加减速
    m_sramp = 10
    # ip地址
    m_ip = "192.168.0.11"
    # 连接成功
    m_flagConnect = False
    # 当前模式：False-自动模式，True-手动模式
    m_currentMode = False
    # 轴选择，用于手动模式
    m_axisSelect = [True for i in range(6)]
    # 轴方向，用于手动模式：True-正向，False-反向
    m_axisDir = [1 for i in range(6)]

    # 初始化参数
    def __init__(self):
        super(ZMCWrapper, self).__init__()
        self.working = False
        self.handle = ctypes.c_void_p()
        self.sys_ip = ""
        self.sys_info = ""
        self.is_connected = False
        self.currentModeBack = True
        self.axis_num = 6
        self.axisDirBack = [1 for i in range(self.axis_num)]

        self.axis_position = (ctypes.c_float * self.axis_num)()
        self.timer = QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.time_out)

        # 各轴运行标志
        self.flagAxisRun = [False for i in range(self.axis_num)]
        self.flagAxisStop = [True for i in range(self.axis_num)]

        # 轴硬限位
        self.axis_limitations = [[8, 0], [9, 1], [10, 2], [11, 3], [12, 4], [13, 5]]
        # 限位急停
        self.ugent_stop = [False for i in range(self.axis_num)]

        # 间隔该时间后自动反向
        self.gap = [0 for i in range(self.axis_num)]
        # 各轴状态信息
        self.axis_alarm = (ctypes.c_int32 * self.axis_num)()
        # 输入口信息
        self.in_value = (ctypes.c_uint8 * 32)()
        self.in_value_back = (ctypes.c_uint8 * 32)()
        # 回零模式:3-正向回零+反找
        self.m_datummode = 3

        # 运行环境判断
        self.zauxdll = ctypes.WinDLL('./zauxdll64.dll')
        print('Windows x64')
        self.zmotionTextSignal.emit('Windows x64...', 'i')
        # systype = platform.system()
        # if systype == 'Windows':
        #     if platform.architecture()[0] == '64bit':
        #         self.zauxdll = ctypes.WinDLL('./zauxdll64.dll')
        #         print('Windows x64')
        #     else:
        #         self.zauxdll = ctypes.WinDLL('./zauxdll.dll')
        #         print('Windows x86')
        # elif systype == 'Darwin':
        #     self.zmcdll = ctypes.CDLL('./zmotion.dylib')
        #     print("macOS")
        # elif systype == 'Linux':
        #     self.zmcdll = ctypes.CDLL('./libbzmotion.so')
        #     print("Linux")
        # else:
        #     print("OS Not Supported!!")

    def __del__(self):
        # print('驱动线程', self.currentThreadId(), '退出')
        if self.working:
            self.log.close()
            for i in range(self.axis_num):
                status = self.get_axis_status(i)
                if status.value == 0:
                    print('Axis (' + str(i) + ') canceled!')
                    self.zmotionTextSignal.emit('Axis (' + str(i) + ') canceled!', 'i')
                    self.stop(i, 2)
            self.timer.stop()
        self.working = False
        # self.wait()

    def run(self):
        # 总回零标志
        self.flag_home = 0
        # 各轴均已回零
        self.axis_already_home = [False for i in range(self.axis_num)]

        # 打印日志
        self.log = open('./log/log.txt', 'w')

        if not self.is_connected:
            ret = self.connect(self.m_ip)
            self.m_flagConnect = self.is_connected
            if ret != 0:
                self.zmotionConnectFlag.emit('Failed')
                self.zmotionTextSignal.emit('连接失败，请重试！', 'e')
                print('连接失败，请重试！')
                return
        print('驱动线程' + str(self.currentThreadId()) + '启动')
        self.log.write(str(sys._getframe().f_lineno) + '：' + '驱动线程' + str(self.currentThreadId()) + '启动\n')
        self.zmotionTextSignal.emit('驱动线程' + str(self.currentThreadId()) + '启动...', 'i')
        self.zmotionConnectFlag.emit('Succeeded')

        # 轴相关参数初始化
        self.axis_parameter_initialization()
        # 轴回零
        while self.flag_home != 63:
            self.axis_home()
            QApplication.processEvents()
        self.sleep(10)
        for i in range(len(self.in_value)):
            self.in_value_back[i] = self.in_value[i]
        # ret = self.zauxdll.ZAux_Trigger(self.handle)
        # if ret == 0:
        #     self.log.write('示波器已开')
        # else:
        #     self.log.write('示波器未开')
        while self.working:
            # 切换模式时，原有的运动需要终止
            if self.m_currentMode != self.currentModeBack:
                self.currentModeBack = self.m_currentMode
                for i in range(self.axis_num):
                    self.stop_once(i, 2, '换膜停机', 'i')

            if self.m_currentMode:
                # 手动模式
                for i in range(self.axis_num):
                    if self.m_axisSelect[i]:
                        if not self.ugent_stop[i]:
                            self.vmove_once(i, self.m_axisDir[i])
                    else:
                        self.stop_once(i, 2, '消选停机', 'i')
            else:
                # 1对应0.02mm
                # self.move_once(0, 2500)
                pass

            # 软件限位
            # for i in range(2):
            #     if self.in_value_back[i] != self.in_value[i]:
            #         self.in_value_back[i] = self.in_value[i]
            #         for iaxis in range(self.axis_num):
            #             if (self.in_value[i] & (1 << iaxis)) and (not self.ugent_stop[iaxis]):
            #                     self.in_value_back[i] = self.in_value[i]
            #                     self.stop_once(iaxis, 2, 'Axis (' + str(iaxis) + ') 限位停机', 'i')
            #                     self.log.write(str(self.gap[2]) + ',' + str(self.gap[5]) + '\n')
            #                     self.ugent_stop[iaxis] = True

            QApplication.processEvents()

###############################轴参数初始化################################################
    def axis_parameter_initialization(self):
        for iaxis in range(self.axis_num):
            # 设置轴类型
            self.set_atype(iaxis, self.m_type)
            # 设置脉冲模式+逻辑方向
            self.set_InvertStep(iaxis, self.m_invertStep)
            # 设置脉冲当量
            self.set_units(iaxis, self.m_units)
            # 设置起始速度
            self.set_lspeed(iaxis, self.m_lspeed)
            # 设置运行速度
            self.set_speed(iaxis, self.m_rspeed)
            # 设置爬行速度
            self.set_creep(iaxis, self.m_creep)
            # 设置加速度
            self.set_accel(iaxis, self.m_acc)
            # 设置减速度
            self.set_decel(iaxis, self.m_dec)
            # 设置sramp时间
            self.set_sramp(iaxis, self.m_sramp)
            # 设置原点IO：各轴负限位
            self.set_axis_origin_io(iaxis, self.axis_limitations[iaxis][1])
            # 轴限位设置
            self.set_axis_forward_in(iaxis, self.axis_limitations[iaxis][0])
            self.set_axis_reverse_in(iaxis, self.axis_limitations[iaxis][1])

    # 各轴回零一次
    def axis_home(self):
        for iaxis in range(self.axis_num):
            if self.in_value[0] & (1 << self.axis_limitations[iaxis][1]):
                self.flag_home = self.flag_home | (1 << iaxis)
            if self.m_axisSelect[iaxis] and (not self.axis_already_home[iaxis]):
                self.axis_already_home[iaxis] = True
                ret = self.zauxdll.ZAux_Direct_Single_Datum(self.handle, iaxis, self.m_datummode + 1)
                if ret == 0:
                    print("Axis (", iaxis, ") going home!")
                    self.zmotionTextSignal.emit("Axis (" + str(iaxis) + ") going home!", 'i')
                else:
                    print("Axis (", iaxis, ") going home fail!")
                    self.zmotionTextSignal.emit("Axis (" + str(iaxis) + ") going home fail!", 'w')
                return ret

###############################控制器连接################################################
    def connect(self, ip, console=[]):
        if self.handle.value is not None:
            self.disconnect()
        ip_bytes = ip.encode('utf-8')
        p_ip = ctypes.c_char_p(ip_bytes)
        print("Connecting to " + str(ip) + "...")
        self.zmotionTextSignal.emit("Connecting to" + str(ip) + "...", 'i')
        ret = self.zauxdll.ZAux_OpenEth(p_ip, ctypes.pointer(self.handle))
        msg = "Connected"
        if ret == 0:
            msg = ip + " Connected"
            self.sys_ip = ip
            self.is_connected = True
        else:
            msg = "Connection Failed, Error " + str(ret)
            self.is_connected = False
        console.append(msg)
        console.append(self.sys_info)
        return ret

    # 断开连接
    def disconnect(self):
        ret = self.zauxdll.ZAux_Close(self.handle)
        self.is_connected = False
        return ret

###############################轴参数设置################################################
    # 设置轴类型
    def set_atype(self, iaxis, iValue):
        ret = self.zauxdll.ZAux_Direct_SetAtype(self.handle, iaxis, iValue)
        if ret == 0:
            print("Set Axis (", iaxis, ") Atype:", iValue)
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Atype:" + str(iValue), 'i')
        else:
            print("Set Axis (", iaxis, ") Atype fail!")
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Atype fail!", 'w')
        return ret

    # 设置脉冲模式+逻辑方向
    def set_InvertStep(self, iaxis, iValue):
        ret = self.zauxdll.ZAux_Direct_SetInvertStep(self.handle, iaxis, iValue)
        if ret == 0:
            print("Set Axis (", iaxis, ") InvertStep:", iValue)
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") InvertStep:" + str(iValue), 'i')
        else:
            print("Set Axis (", iaxis, ") InvertStep fail!")
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") InvertStep fail!", 'w')
        return ret

    # 设置脉冲当量
    def set_units(self, iaxis, iValue):
        ret = self.zauxdll.ZAux_Direct_SetUnits(self.handle, iaxis, ctypes.c_float(iValue))
        if ret == 0:
            print("Set Axis (", iaxis, ") Units:", iValue)
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Units:" + str(iValue), 'i')
        else:
            print("Set Axis (", iaxis, ") Units fail!")
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Units fail!", 'w')
        return ret

    # 设置轴加速度
    def set_accel(self, iaxis, iValue):
        ret = self.zauxdll.ZAux_Direct_SetAccel(self.handle, iaxis, ctypes.c_float(iValue))
        if ret == 0:
            print("Set Axis (", iaxis, ") Accel:", iValue)
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Accel:" + str(iValue), 'i')
        else:
            print("Set Accel (", iaxis, ") Accel fail!")
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Accel fail!", 'w')
        return ret

    # 设置轴减速度
    def set_decel(self, iaxis, iValue):
        ret = self.zauxdll.ZAux_Direct_SetDecel(self.handle, iaxis, ctypes.c_float(iValue))
        if ret == 0:
            print("Set Axis (", iaxis, ") Decel:", iValue)
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Decel:" + str(iValue), 'i')
        else:
            print("Set Axis (", iaxis, ") Decel fail!")
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Decel fail!", 'w')
        return ret

    # 设置起始速度
    def set_lspeed(self, iaxis, iValue):
        ret = self.zauxdll.ZAux_Direct_SetLspeed(self.handle, iaxis, ctypes.c_float(iValue))
        if ret == 0:
            print("Set Axis (", iaxis, ") Lspeed:", iValue)
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Lspeed:" + str(iValue), 'i')
        else:
            print("Set Axis (", iaxis, ") Lspeed fail!")
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Lspeed fail!", 'w')
        return ret

    # 设置轴运行速度
    def set_speed(self, iaxis, iValue):
        ret = self.zauxdll.ZAux_Direct_SetSpeed(self.handle, iaxis, ctypes.c_float(iValue))
        if ret == 0:
            print("Set Axis (", iaxis, ") Speed:", iValue)
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Speed:" + str(iValue), 'i')
        else:
            print("Set Axis (", iaxis, ") Speed fail!")
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Speed fail!", 'w')
        return ret

    # 设置爬行速度
    def set_creep(self, iaxis, iValue):
        ret = self.zauxdll.ZAux_Direct_SetCreep(self.handle, iaxis, ctypes.c_float(iValue))
        if ret == 0:
            print("Set Axis (", iaxis, ") creep:", iValue)
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") creep:" + str(iValue), 'i')
        else:
            print("Set Axis (", iaxis, ") creep fail!")
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") creep fail!", 'w')
        return ret

    # 设置sramp时间
    def set_sramp(self, iaxis, iValue):
        ret = self.zauxdll.ZAux_Direct_SetSramp(self.handle, iaxis, iValue)
        if ret == 0:
            print("Set Axis (", iaxis, ") Sramp:", iValue)
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Sramp:" + str(iValue), 'i')
        else:
            print("Set Axis (", iaxis, ") Sramp fail!")
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") Sramp fail!", 'w')
        return ret

    # 设置原点IO
    def set_axis_origin_io(self, iaxis, iValue):
        ret = self.zauxdll.ZAux_Direct_SetDatumIn(self.handle, iaxis, iValue)
        if ret == 0:
            print("Set Axis (", iaxis, ") origin io:", iValue)
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") origin io:" + str(iValue), 'i')
        else:
            print("Set Axis (", iaxis, ") origin io fail!")
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") origin io fail!", 'w')
        return ret

    # 设置正向限位
    def set_axis_forward_in(self, iaxis, iValue):
        ret = self.zauxdll.ZAux_Direct_SetFwdIn(self.handle, iaxis, iValue)
        if ret == 0:
            print("Set Axis (", iaxis, ") forward in:", iValue)
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") forward in:" + str(iValue), 'i')
        else:
            print("Set Axis (", iaxis, ") forward in fail!")
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") forward in fail!", 'w')
        return ret

    # 设置反向限位
    def set_axis_reverse_in(self, iaxis, iValue):
        ret = self.zauxdll.ZAux_Direct_SetRevIn(self.handle, iaxis, iValue)
        if ret == 0:
            print("Set Axis (", iaxis, ") reverse in:", iValue)
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") reverse in:" + str(iValue), 'i')
        else:
            print("Set Axis (", iaxis, ") reverse in fail!")
            self.zmotionTextSignal.emit("Set Axis (" + str(iaxis) + ") reverse in fail!", 'w')
        return ret

###############################轴参数读取################################################
    # 读取轴类型
    def get_atype(self, iaxis):
        iValue = (ctypes.c_int)()
        ret = self.zauxdll.ZAux_Direct_GetAtype(self.handle, iaxis, ctypes.byref(iValue))
        if ret == 0:
            print("Get Axis (", iaxis, ") Atype:", iValue.value)
            self.zmotionTextSignal.emit("Get Axis (" + str(iaxis) + ") Atype:" + str(iValue), 'i')
        else:
            print("Get Axis (", iaxis, ") Atype fail!")
            self.zmotionTextSignal.emit("Get Axis (" + str(iaxis) + ") Atype fail!", 'w')
        return ret

    # 读取轴脉冲当量
    def get_untis(self, iaxis):
        iValue = (ctypes.c_float)()
        ret = self.zauxdll.ZAux_Direct_GetUnits(self.handle, iaxis, ctypes.byref(iValue))
        if ret == 0:
            print("Get Axis (", iaxis, ") Units:", iValue.value)
            self.zmotionTextSignal.emit("Get Axis (" + str(iaxis) + ") Units:" + str(iValue), 'i')
        else:
            print("Get Axis (", iaxis, ") Units fail!")
            self.zmotionTextSignal.emit("Get Axis (" + str(iaxis) + ") Units fail!", 'w')
        return ret

    # 读取轴加速度
    def get_accel(self, iaxis):
        iValue = (ctypes.c_float)()
        ret = self.zauxdll.ZAux_Direct_GetAccel(self.handle, iaxis, ctypes.byref(iValue))
        if ret == 0:
            print("Get Axis (", iaxis, ") Accel:",  iValue.value)
            self.zmotionTextSignal.emit("Get Axis (" + str(iaxis) + ") Units:" + str(iValue), 'i')
        else:
            print("Get Axis (", iaxis, ") Accel fail!")
            self.zmotionTextSignal.emit("Get Axis (" + str(iaxis) + ") Accel fail!", 'w')
        return ret

    # 读取轴减速度
    def get_decel(self, iaxis):
        iValue = (ctypes.c_float)()
        ret = self.zauxdll.ZAux_Direct_GetDecel(self.handle, iaxis, ctypes.byref(iValue))
        if ret == 0:
            print("Get Axis (", iaxis, ") Decel:",  iValue.value)
            self.zmotionTextSignal.emit("Get Axis (" + str(iaxis) + ") Decel:" + str(iValue), 'i')
        else:
            print("Get Axis (", iaxis, ") Decel fail!")
            self.zmotionTextSignal.emit("Get Axis (" + str(iaxis) + ") Decel fail!", 'w')
        return ret

    # 读取轴运行速度
    def get_speed(self, iaxis):
        iValue = (ctypes.c_float)()
        ret = self.zauxdll.ZAux_Direct_GetSpeed(self.handle, iaxis, ctypes.byref(iValue))
        if ret == 0:
            print("Get Axis (", iaxis, ") Speed:",  iValue.value)
            self.zmotionTextSignal.emit("Get Axis (" + str(iaxis) + ") Speed:" + str(iValue), 'i')
        else:
            print("Get Axis (", iaxis, ") Speed fail!")
            self.zmotionTextSignal.emit("Get Axis (" + str(iaxis) + ") Speed fail!", 'w')
        return ret

    # 读取当前轴状态
    def get_axis_status(self, iaxis):
        status = (ctypes.c_int)(-1)
        ret = self.zauxdll.ZAux_Direct_GetIfIdle(self.handle, iaxis, ctypes.byref(status))
        if ret == 0:
            print("Get Axis (", iaxis, ") status:",  status.value)
            self.zmotionTextSignal.emit("Get Axis (" + str(iaxis) + ") status:" + str(status), 'i')
        else:
            print("Get Axis (", iaxis, ") status fail!")
            self.zmotionTextSignal.emit("Get Axis (" + str(iaxis) + ") status fail!", 'w')
        return status

    # 读取当前各轴的位置
    def get_axis_pos(self, ax_num = 6):
        # axis_pos = (ctypes.c_float * ax_num)()
        ret = self.zauxdll.ZAux_Modbus_Get4x(self.handle, 11000, ax_num * 2, ctypes.byref(self.axis_position))  # 读取多个轴的mpos
        if ret == 0:
            print("Get Axis position:", self.axis_position[0], self.axis_position[1], self.axis_position[2], self.axis_position[3], self.axis_position[4], self.axis_position[5])
            # self.zmotionTextSignal.emit("Get Axis position:" + str(self.axis_position), 'i')
        else:
            print("Get Axis position fail!")
            # self.zmotionTextSignal.emit("Get Axis position fail!", 'w')
        return ret

    # 读取各轴的状态
    def get_axis_alarm(self):
        for iaxis in range(self.axis_num):
            ret = self.zauxdll.ZAux_Direct_GetAxisStatus(self.handle, iaxis, ctypes.byref(ctypes.c_int32(self.axis_alarm[iaxis])))
            if ret == 0:
                print("Get Axis alarm:", self.axis_alarm[0], self.axis_alarm[1], self.axis_alarm[2], self.axis_alarm[3], self.axis_alarm[4], self.axis_alarm[5])
                # self.zmotionTextSignal.emit("Get Axis position:" + str(self.axis_position), 'i')
            else:
                print("Get Axis alarm fail!")
                # self.zmotionTextSignal.emit("Get Axis position fail!", 'w')
            return ret

    def get_in_value(self):
        ret = self.zauxdll.ZAux_GetModbusIn(self.handle, 0, len(self.in_value) - 1, ctypes.byref(self.in_value))
        if ret == 0:
            print("Get Axis in value:", self.in_value[0], self.in_value[1], self.in_value_back[0], self.in_value_back[1])
            # self.zmotionTextSignal.emit("Get Axis position:" + str(self.axis_position), 'i')
        else:
            print("Get Axis in value fail!")
            # self.zmotionTextSignal.emit("Get Axis position fail!", 'w')

###############################运动调用####################################################
    # 直线运动
    def move(self, iaxis, iValue):
        ret = self.zauxdll.ZAux_Direct_Single_Move(self.handle, iaxis, ctypes.c_float(iValue))
        if ret == 0:
            print("Axis (", iaxis, ") Move:", iValue)
            self.zmotionTextSignal.emit("Axis (" + str(iaxis) + ") Move:" + str(iValue), 'i')
        else:
            print("Axis (", iaxis, ") Move Fail")
            self.zmotionTextSignal.emit("Axis (" + str(iaxis) + ") Move fail!", 'w')
        return ret

    # 运动一次
    def move_once(self, iaxis, idir):
        if not self.flagAxisRun[iaxis]:
            self.flagAxisRun[iaxis] = True
            self.flagAxisStop[iaxis] = False
            self.move(iaxis, idir)

    # 持续运动
    def vmove(self, iaxis, idir):
        ret = self.zauxdll.ZAux_Direct_Single_Vmove(self.handle, iaxis, idir)
        if ret == 0:
            print("Axis (", iaxis, ") Vmoving!")
            self.zmotionTextSignal.emit("Axis (" + str(iaxis) + ") Vmoving!", 'i')
        else:
            print("Vmoving fail!")
            self.zmotionTextSignal.emit("Vmoving fail!", 'w')
        return ret

    # 运动一次
    def vmove_once(self, iaxis, idir):
        if not self.flagAxisRun[iaxis]:
            self.flagAxisRun[iaxis] = True
            self.flagAxisStop[iaxis] = False
            self.vmove(iaxis, idir)

    # 停止运动
    def stop(self, iaxis, imode):
        ret = self.zauxdll.ZAux_Direct_Single_Cancel(self.handle,iaxis,2)
        if ret == 0:
            print("Axis (", iaxis, ") canceled!")
            self.zmotionTextSignal.emit("Axis (" + str(iaxis) + ") canceled!", 'i')
        else:
            print("Vmoving fail!")
            self.zmotionTextSignal.emit("Canceled fail!", 'w')
        return ret

    def stop_once(self, iaxis, imode, text, flag):
        if not self.flagAxisStop[iaxis]:
            self.flagAxisStop[iaxis] = True
            self.flagAxisRun[iaxis] = False
            print(text)
            self.zmotionTextSignal.emit(text, flag)
            self.stop(iaxis, imode)

###############################其他函数####################################################
    # 定时器
    def time_out(self):
        if self.working:
            self.get_axis_pos(6)
            self.get_in_value()
            for i in range(self.axis_num):
                if self.axisDirBack[i] != self.m_axisDir[i]:
                    self.axisDirBack[i] = self.m_axisDir[i]
                    # 改变方向，解除急停
                    self.ugent_stop[i] = False

                # 煲机测试用
                if self.ugent_stop[i]:
                    self.gap[i] += 1
                    if self.gap[i] == 10:
                        self.gap[i] = 0
                        self.m_axisDir[i] = -self.m_axisDir[i]

################################功能使用######################################################
# zaux = ZMCWrapper()
# 连接控制器ip   默认192.168.0.11
# res = zaux.connect("192.168.0.11")
# print(res)
# # 设置轴0参数
# zaux.set_atype(0, 1)
# zaux.set_units(0, 100)
# zaux.set_accel(0, 1000)
# zaux.set_decel(0, 1000)
# zaux.set_speed(0, 1000)
# # 获取轴0参数
# zaux.get_atype(0)
# zaux.get_untis(0)
# zaux.get_accel(0)
# zaux.get_decel(0)
# zaux.get_speed(0)
# # 运动
# zaux.move(0, 100)  # 轴0直线运动移动100

