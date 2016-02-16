#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math
import ctypes
import inspect

from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtOpenGL import *
from OpenGL.GL import *
from OpenGL.GL import shaders
from PIL import Image
import numpy as np

import glm
import camera

currentFile = inspect.getframeinfo(inspect.currentframe()).filename
abPath = os.path.dirname(os.path.abspath(currentFile))

class GLWindow(QGLWidget):

    def __init__(self, gl_format=None):
        if gl_format is None:
            # using opengl 3.3 core profile
            gformat = QGLFormat()
            gformat.setVersion(3, 3)
            gformat.setProfile(QGLFormat.CoreProfile)
        super(GLWindow, self).__init__(gformat)

        self.__timer = QElapsedTimer()
        self.__timer.start()

        self.camera = camera.Camera(0.0, 0.0, 3.0)
        self.__lastX = 400
        self.__lastY = 300
        self.__firstMouse = True

        self.__deltaTime = 0.0
        self.__lastTime = 0.0

        # if you want press mouse button to active camera rotation set it to false 
        self.setMouseTracking(True)

    def loadShaders(self):
        vertexShaderFile = os.path.join(abPath, '6.coordinate_systems.vs')
        fragmentShaderFile = os.path.join(abPath, '6.coordinate_systems.frag')
        vertexShaderSource = ''
        with open(vertexShaderFile) as vs:
            vertexShaderSource = vs.read()
        fragmentShaderSource = ''
        with open(fragmentShaderFile) as fg:
            fragmentShaderSource = fg.read()

        vertexShader = shaders.compileShader(vertexShaderSource, GL_VERTEX_SHADER)
        fragmentShader = shaders.compileShader(fragmentShaderSource, GL_FRAGMENT_SHADER)
        return vertexShader, fragmentShader
    
    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)

        vertexShader, fragmentShader = self.loadShaders()
        self.__shaderProgram = shaders.compileProgram(vertexShader, fragmentShader)

        vertices = np.array([
            -0.5, -0.5, -0.5,  0.0, 0.0,
             0.5, -0.5, -0.5,  1.0, 0.0,
             0.5,  0.5, -0.5,  1.0, 1.0,
             0.5,  0.5, -0.5,  1.0, 1.0,
            -0.5,  0.5, -0.5,  0.0, 1.0,
            -0.5, -0.5, -0.5,  0.0, 0.0,

            -0.5, -0.5,  0.5,  0.0, 0.0,
             0.5, -0.5,  0.5,  1.0, 0.0,
             0.5,  0.5,  0.5,  1.0, 1.0,
             0.5,  0.5,  0.5,  1.0, 1.0,
            -0.5,  0.5,  0.5,  0.0, 1.0,
            -0.5, -0.5,  0.5,  0.0, 0.0,

            -0.5,  0.5,  0.5,  1.0, 0.0,
            -0.5,  0.5, -0.5,  1.0, 1.0,
            -0.5, -0.5, -0.5,  0.0, 1.0,
            -0.5, -0.5, -0.5,  0.0, 1.0,
            -0.5, -0.5,  0.5,  0.0, 0.0,
            -0.5,  0.5,  0.5,  1.0, 0.0,

             0.5,  0.5,  0.5,  1.0, 0.0,
             0.5,  0.5, -0.5,  1.0, 1.0,
             0.5, -0.5, -0.5,  0.0, 1.0,
             0.5, -0.5, -0.5,  0.0, 1.0,
             0.5, -0.5,  0.5,  0.0, 0.0,
             0.5,  0.5,  0.5,  1.0, 0.0,

            -0.5, -0.5, -0.5,  0.0, 1.0,
             0.5, -0.5, -0.5,  1.0, 1.0,
             0.5, -0.5,  0.5,  1.0, 0.0,
             0.5, -0.5,  0.5,  1.0, 0.0,
            -0.5, -0.5,  0.5,  0.0, 0.0,
            -0.5, -0.5, -0.5,  0.0, 1.0,

            -0.5,  0.5, -0.5,  0.0, 1.0,
             0.5,  0.5, -0.5,  1.0, 1.0,
             0.5,  0.5,  0.5,  1.0, 0.0,
             0.5,  0.5,  0.5,  1.0, 0.0,
            -0.5,  0.5,  0.5,  0.0, 0.0,
            -0.5,  0.5, -0.5,  0.0, 1.0
            ], np.float32)

        # world space positions of our cubes
        self.__cubePositions = ((0.0, 0.0, 0.0),
                                (2.0, 5.0, -15.0),
                                (-1.5, -2.2, -2.5),
                                (-3.8, -2.0, -12.3),
                                (2.4, -0.4, -3.5),
                                (-1.7, 3.0, -7.5),
                                (1.3, -2.0, -2.5),
                                (1.5, 2.0, -2.5),
                                (1.5, 0.2, -1.5),
                                (-1.3, 1.0, -1.5))

        self.__vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)

        glBindVertexArray(self.__vao)

        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * vertices.itemsize, None)
        glEnableVertexAttribArray(0)

        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 5 * vertices.itemsize, ctypes.c_void_p(3 * vertices.itemsize))
        glEnableVertexAttribArray(2)

        glBindBuffer(GL_ARRAY_BUFFER, 0)

        glBindVertexArray(0)

        # load and create a texture
        self.texture1 = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture1)
        # set our texture parameters
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        # set texture filtering
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        texturePath = os.path.join(abPath, '..', '..', 'resources', 'textures', 'container.jpg')
        im = Image.open(texturePath)
        #im = im.transpose(Image.FLIP_TOP_BOTTOM)

        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, im.size[0], im.size[1], 0, GL_RGB, GL_UNSIGNED_BYTE, im.tobytes())
        glGenerateMipmap(GL_TEXTURE_2D)
        im.close()
        glBindTexture(GL_TEXTURE_2D, 0)

        self.texture2 = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture2)
        # set our texture parameters
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        # set texture filtering
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        texture2Path = os.path.join(abPath, '..', '..', 'resources', 'textures', 'awesomeface.png')
        im2 = Image.open(texture2Path)
        #im2 = im2.transpose(Image.FLIP_TOP_BOTTOM)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, im2.size[0], im2.size[1], 0, GL_RGBA, GL_UNSIGNED_BYTE, im2.tobytes())
        glGenerateMipmap(GL_TEXTURE_2D)
        im2.close()
        glBindTexture(GL_TEXTURE_2D, 0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

    def paintGL(self):
        currentTime = self.__timer.elapsed() / 1000.0
        self.__deltaTime = currentTime - self.__lastTime
        self.__lastTime = currentTime

        # Render
        # Clear the colorbuffer
        glClearColor(0.2, 0.3, 0.3, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(self.__shaderProgram)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture1)
        glUniform1i(glGetUniformLocation(self.__shaderProgram, 'ourTexture1'), 0)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.texture2)
        glUniform1i(glGetUniformLocation(self.__shaderProgram, 'ourTexture2'), 1)

        view = self.camera.viewMatrix
        view = glm.translate(view, 0.0, 0.0, -3.0)
        projection = glm.perspective(self.camera.zoom, float(self.width()) / self.height(), 0.1, 1000.0)
        # get their uniform location
        modelLoc = glGetUniformLocation(self.__shaderProgram, 'model')
        viewLoc = glGetUniformLocation(self.__shaderProgram, 'view')
        projLoc = glGetUniformLocation(self.__shaderProgram, 'projection')
        glUniformMatrix4fv(viewLoc, 1, GL_FALSE, view)
        glUniformMatrix4fv(projLoc, 1, GL_FALSE, projection)

        glBindVertexArray(self.__vao)
        for i in self.__cubePositions:
            # calculate the model matrix for each object and pass it to shader before drawing
            angle = math.degrees(20.0 * self.__cubePositions.index(i))
            model = glm.rotate(np.identity(4, np.float32), angle, 1.0, 0.3, 0.5)
            model = glm.translate(model, i[0], i[1], i[2])
            glUniformMatrix4fv(modelLoc, 1, GL_FALSE, model)

            glDrawArrays(GL_TRIANGLES, 0, 36)

        glBindVertexArray(0)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            qApp.quit()
        if event.key() == Qt.Key_W:
            self.camera.processKeyboard(camera.Camera_Movement.FORWARD, self.__deltaTime)
        if event.key() == Qt.Key_S:
            self.camera.processKeyboard(camera.Camera_Movement.BACKWARED, self.__deltaTime)
        if event.key() == Qt.Key_A:
            self.camera.processKeyboard(camera.Camera_Movement.LEFT, self.__deltaTime)
        if event.key() == Qt.Key_D:
            self.camera.processKeyboard(camera.Camera_Movement.RIGHT, self.__deltaTime)

        self.updateGL()
        return super(GLWindow, self).keyPressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        if self.__firstMouse:
            self.__lastX = pos.x()
            self.__lastY = pos.y()
            self.__firstMouse = False

        xoffset = pos.x() - self.__lastX
        yoffset = self.__lastY - pos.y()

        self.__lastX = pos.x()
        self.__lastY = pos.y()

        self.camera.processMouseMovement(xoffset, yoffset)

        self.updateGL()
        return super(GLWindow, self).mouseMoveEvent(event)

    def wheelEvent(self, event):
        self.camera.processMouseScroll(event.delta())
        self.updateGL()



if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)

    glWindow = GLWindow()
    glWindow.setFixedSize(800, 600)
    glWindow.setWindowTitle('LearnPyOpenGL')
    glWindow.show()

    sys.exit(app.exec_())
