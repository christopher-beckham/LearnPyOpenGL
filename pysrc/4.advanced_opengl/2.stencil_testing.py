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
        vertexShaderFile = os.path.join(abPath, '2.stencil_testing.vs')
        fragmentShaderFile = os.path.join(abPath, '2.stencil_testing.frag')
        coloerShaderFile = os.path.join(abPath, '2.stencil_single_color.frag')
        vertexShaderSource = ''
        with open(vertexShaderFile) as vs:
            vertexShaderSource = vs.read()
        fragmentShaderSource = ''
        with open(fragmentShaderFile) as fg:
            fragmentShaderSource = fg.read()
        colorShaderSource = ''
        with open(coloerShaderFile) as cs:
            colorShaderSource = cs.read()

        vertexShader = shaders.compileShader(vertexShaderSource, GL_VERTEX_SHADER)
        fragmentShader = shaders.compileShader(fragmentShaderSource, GL_FRAGMENT_SHADER)
        colorShader = shaders.compileShader(colorShaderSource, GL_FRAGMENT_SHADER)
        return vertexShader, fragmentShader, colorShader
    
    def initializeGL(self):
        # setup some OpenGL options
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        glEnable(GL_STENCIL_TEST)
        glStencilFunc(GL_NOTEQUAL, 1, 0xFF)
        glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)

        vertexShader, fragmentShader, colorShader = self.loadShaders()
        self.__shaderProgram = shaders.compileProgram(vertexShader, fragmentShader)
        self.__singleColorProgram = shaders.compileProgram(vertexShader, colorShader)

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

        self.planeVertices = np.array([
            # Positions     Texture Coords (note we set these higher than 1 that together with GL_REPEAT as texture wrapping mode will cause the floor texture to repeat)
            5.0, -0.5, 5.0, 2.0, 0.0,
            -5.0, -0.5, 5.0, 0.0, 0.0,
            -5.0, -0.5, -5.0, 0.0, 2.0,

            5.0, -0.5, 5.0, 2.0, 0.0,
            -5.0, -0.5, -5.0, 0.0, 2.0,
            5.0, -0.5, -5.0, 2.0, 2.0
        ], np.float32)

        # setup cube VAO
        self.cubeVAO = glGenVertexArrays(1)
        vbo = glGenBuffers(1)

        glBindVertexArray(self.cubeVAO)

        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * vertices.itemsize, None)
        glEnableVertexAttribArray(0)

        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * vertices.itemsize, ctypes.c_void_p(3 * vertices.itemsize))
        glEnableVertexAttribArray(1)

        # setup plane VAO
        self.planeVAO = glGenVertexArrays(1)
        planeVBO = glGenBuffers(1)

        glBindVertexArray(self.planeVAO)
        glBindBuffer(GL_ARRAY_BUFFER, planeVBO)
        glBufferData(GL_ARRAY_BUFFER, self.planeVertices.nbytes, self.planeVertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * self.planeVertices.itemsize, None)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * self.planeVertices.itemsize, ctypes.c_void_p(3 * self.planeVertices.itemsize))
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        glBindVertexArray(0)

        # load and create a texture
        texturePath = os.path.join(abPath, '..', '..', 'resources', 'textures', 'marble.jpg')
        self.cubeTexture = loadTexture(texturePath)
        texture2Path = os.path.join(abPath, '..', '..', 'resources', 'textures', 'metal.png')
        self.floorTexture = loadTexture(texture2Path)

    def resizeGL(self, w, h):
        QCursor.setPos(self.geometry().center())
        glViewport(0, 0, w, h)

    def paintGL(self):
        currentTime = self.__timer.elapsed() / 1000.0
        self.__deltaTime = currentTime - self.__lastTime
        self.__lastTime = currentTime

        # Render
        # Clear the colorbuffer
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

        glUseProgram(self.__singleColorProgram)

        view = self.camera.viewMatrix
        projection = glm.perspective(self.camera.zoom, float(self.width()) / self.height(), 0.1, 100.0)
        # get their uniform location
        modelLoc = glGetUniformLocation(self.__shaderProgram, 'model')
        glUniformMatrix4fv(glGetUniformLocation(self.__singleColorProgram, 'view'), 1, GL_FALSE, view)
        glUniformMatrix4fv(glGetUniformLocation(self.__singleColorProgram, 'projection'), 1, GL_FALSE, projection)
        glUseProgram(self.__shaderProgram)
        glUniformMatrix4fv(glGetUniformLocation(self.__shaderProgram, 'view'), 1, GL_FALSE, view)
        glUniformMatrix4fv(glGetUniformLocation(self.__shaderProgram, 'projection'), 1, GL_FALSE, projection)

        # Draw floor as normal, we only care about the containers. The floor should NOT fill the stencil buffer so we set its mask to 0x00
        glStencilMask(0x00)
        # Floor
        glBindVertexArray(self.planeVAO)
        glBindTexture(GL_TEXTURE_2D, self.floorTexture)
        glUniformMatrix4fv(glGetUniformLocation(self.__shaderProgram, 'model'), 1, GL_FALSE, np.identity(4))
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)

        # 1st. Render pass, draw objects as normal, filling the stencil buffer
        glStencilFunc(GL_ALWAYS, 1, 0xFF)
        glStencilMask(0xFF)
        # Cubes
        glBindVertexArray(self.cubeVAO)
        glBindTexture(GL_TEXTURE_2D, self.cubeTexture)
        model = glm.translate(np.identity(4), -1, 0, -1)
        glUniformMatrix4fv(glGetUniformLocation(self.__shaderProgram, 'model'), 1, GL_FALSE, model)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        model = glm.translate(np.identity(4), 2, 0, 0)
        glUniformMatrix4fv(glGetUniformLocation(self.__shaderProgram, 'model'), 1, GL_FALSE, model)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        glBindVertexArray(0)

        # 2nd. Render pass, now draw slightly scaled versions of the objects, this time disabling stencil writing.
        # Because stencil buffer is now filled with several 1s. The parts of the buffer that are 1 are now not drawn, thus only drawing
        # the objects' size differences, making it look like borders.
        glStencilFunc(GL_NOTEQUAL, 1, 0xFF)
        glStencilMask(0x00)
        glDisable(GL_DEPTH_TEST)
        glUseProgram(self.__singleColorProgram)
        scale = 1.1
        # Cubes
        glBindVertexArray(self.cubeVAO)
        glBindTexture(GL_TEXTURE_2D, self.cubeTexture)
        model = glm.scale(np.identity(4), scale, scale, scale)
        model = glm.translate(model, -1, 0, -1)
        glUniformMatrix4fv(glGetUniformLocation(self.__singleColorProgram, 'model'), 1, GL_FALSE, model)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        model = glm.scale(np.identity(4), scale, scale, scale)
        model = glm.translate(model, 2, 0, 0)
        glUniformMatrix4fv(glGetUniformLocation(self.__singleColorProgram, 'model'), 1, GL_FALSE, model)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        glBindVertexArray(0)
        glStencilMask(0xFF)
        glEnable(GL_DEPTH_TEST)

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

def loadTexture(texPath):
    textureID = glGenTextures(1)
    im = Image.open(texPath)
    glBindTexture(GL_TEXTURE_2D, textureID)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, im.size[0], im.size[1], 0, GL_RGB, GL_UNSIGNED_BYTE, im.tobytes())
    glGenerateMipmap(GL_TEXTURE_2D)

    # parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    im.close()
    glBindTexture(GL_TEXTURE_2D, 0)
    return textureID

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)

    glWindow = GLWindow()
    glWindow.setFixedSize(800, 600)
    glWindow.setWindowTitle('LearnPyOpenGL')
    glWindow.show()

    sys.exit(app.exec_())
