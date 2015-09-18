#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math

import numpy as np
import glm


# default camera values
YAW = -90.0
PITCH = 0.0
SPEED = 3.0
SENSITIVTY = 0.25
ZOOM = 45.0


class Camera(object):

    FORWARD = 0
    BACKWARED = 1
    LEFT = 2
    RIGHT = 3

    def __init__(self, posx, posy, posz, upx, upy, upz, yaw, pitch):
        self.front = np.array(0.0, 0.0, -1.0, np.float32)
        self.movementSpeed = SPEED
        self.mouseSensitivity = SENSITIVTY
        self.zoom = ZOOM
