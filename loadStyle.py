#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/5/26 19:23
# @Author  : Zhang Shanxiu
class LoadStyle:
    @staticmethod
    def readQSS(sytle):
        with open(sytle, 'r') as f:
            return f.read()