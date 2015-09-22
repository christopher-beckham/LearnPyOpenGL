#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math

import numpy as np
import glm


class Camera_Movement:
    FORWARD = 0
    BACKWARED = 1
    LEFT = 2
    RIGHT = 3

# default camera values
YAW = -90.0
PITCH = 0.0
SPEED = 3.0
SENSITIVTY = 0.25
ZOOM = 45.0


class Camera(object):

    def __init__(self, posx, posy, posz, upx=0.0, upy=1.0, upz=0.0, yaw=YAW, pitch=PITCH):
        self.front = np.array([0.0, 0.0, -1.0], np.float32)
        self.movementSpeed = SPEED
        self.mouseSensitivity = SENSITIVTY
        self.zoom = ZOOM

        #self.up = np.array([0, 1, 0], np.float32)

        self.position = np.array([posx, posy, posz], np.float32)
        self.worldUp = np.array([upx, upy, upz], np.float32)
        self.yaw = yaw
        self.pitch = pitch

        self.__updateCameraVectors()

    @property
    def viewMatrix(self):
        return glm.lookAt(self.position, self.position + self.front, self.up)

    def processKeyboard(self, direction, deltaTime):
        velocity = self.movementSpeed * deltaTime
        if direction == Camera_Movement.FORWARD:
            self.position += self.front * velocity
        if direction == Camera_Movement.BACKWARED:
            self.position -= self.front * velocity
        if direction == Camera_Movement.LEFT:
            self.position -= self.right * velocity
        if direction == Camera_Movement.RIGHT:
            self.position += self.right * velocity

    def processMouseMovement(self, xoffset, yoffset, constrainPitch=True):
        xoffset *= self.mouseSensitivity
        yoffset *= self.mouseSensitivity

        self.yaw += xoffset
        self.pitch += yoffset

        if constrainPitch:
            if self.pitch > 89.0:
                self.pitch = 89.0
            if self.pitch < -89.0:
                self.pitch = -89.0

        self.__updateCameraVectors()

    def processMouseScroll(self, zoom):
        if self.zoom >= 1.0 and self.zoom <= 45.0:
            self.zoom -= zoom
        if self.zoom <= 1.0:
            self.zoom = 1.0
        if self.zoom >= 45.0:
            self.zoom = 45.0

    def __updateCameraVectors(self):
        front = np.array([0, 0, 0], np.float32)
        front[0] = math.cos(math.radians(self.yaw)) * math.cos(math.radians(self.pitch))
        front[1] = math.sin(math.radians(self.pitch))
        front[2] = math.sin(math.radians(self.yaw)) * math.cos(math.radians(self.pitch))
        self.front = glm.normalize(front)
        self.right = glm.normalize(np.cross(self.front, self.worldUp))
        self.up = glm.normalize(np.cross(self.right, self.front))