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

    def loadShaders(self, vsf, fsf, gsf=None):
        vertexShaderFile = os.path.join(abPath, vsf)
        fragmentShaderFile = os.path.join(abPath, fsf)
        vertexShaderSource = ''
        with open(vertexShaderFile) as vs:
            vertexShaderSource = vs.read()
        fragmentShaderSource = ''
        with open(fragmentShaderFile) as fg:
            fragmentShaderSource = fg.read()

        vertexShader = shaders.compileShader(vertexShaderSource, GL_VERTEX_SHADER)
        fragmentShader = shaders.compileShader(fragmentShaderSource, GL_FRAGMENT_SHADER)
        geometryShader = None
        if gsf:
            geometryShaderFile = os.path.join(abPath, gsf)
            geometryShaderSource = ''
            with open(geometryShaderFile) as gs:
                geometryShaderSource = gs.read()
            geometryShader = shaders.compileShader(geometryShaderSource, GL_GEOMETRY_SHADER)
        return vertexShader, fragmentShader

    def initializeGL(self):
        # setup some OpenGL options
        glEnable(GL_DEPTH_TEST)
        # glDepthFunc(GL_ALWAYS) # Set to always pass the depth test (same effect as glDisable(GL_DEPTH_TEST))

        vertexShader, fragmentShader = self.loadShaders('3.3.csm.vs', '3.3.csm.frag')
        self.__shader = shaders.compileProgram(vertexShader, fragmentShader)

        cubeVertices = np.array([
            # position         # texture coords
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
            -0.5,  0.5, -0.5,  0.0, 1.0,
        ], np.float32)
        planeVertices = np.array([
            # Positions          # Texture Coords (note we set these higher than 1 that together with GL_REPEAT as texture wrapping mode will cause the floor texture to repeat)
            5.0,  -0.5,  5.0,  2.0, 0.0,
            -5.0, -0.5,  5.0,  0.0, 0.0,
            -5.0, -0.5, -5.0,  0.0, 2.0,

            5.0,  -0.5,  5.0,  2.0, 0.0,
            -5.0, -0.5, -5.0,  0.0, 2.0,
            5.0,  -0.5, -5.0,  2.0, 2.0,
        ], np.float32)
        # setup cube vao
        self.cubeVAO = glGenVertexArrays(1)
        cubeVBO = glGenBuffers(1)
        glBindVertexArray(self.cubeVAO)
        glBindBuffer(GL_ARRAY_BUFFER, cubeVBO)
        glBufferData(GL_ARRAY_BUFFER, cubeVertices.nbytes, cubeVertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * cubeVertices.itemsize, None)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * cubeVertices.itemsize, ctypes.c_void_p(3 * cubeVertices.itemsize))
        glBindVertexArray(0)
        # setup plane vao
        self.planeVAO = glGenVertexArrays(1)
        planeVBO = glGenBuffers(1)
        glBindVertexArray(self.planeVAO)
        glBindBuffer(GL_ARRAY_BUFFER, planeVBO)
        glBufferData(GL_ARRAY_BUFFER, planeVertices.nbytes, planeVertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * planeVertices.itemsize, None)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * planeVertices.itemsize, ctypes.c_void_p(3 * planeVertices.itemsize))
        glBindVertexArray(0)

        # load texture
        self.cubeTexture = loadTexture(os.path.join(abPath, '..', '..', 'resources', 'textures', 'marble.jpg'))
        self.floorTexture = loadTexture(os.path.join(abPath, '..', '..', 'resources', 'textures', 'metal.png'))

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

    def paintGL(self):
        currentTime = self.__timer.elapsed() / 1000.0
        self.__deltaTime = currentTime - self.__lastTime
        self.__lastTime = currentTime

        # clear the colorbuffer
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # draw objects
        glUseProgram(self.__shader)
        view = self.camera.viewMatrix
        projection = glm.perspective(self.camera.zoom, float(self.width())/self.height(), 0.1, 100.0)
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'view'), 1, GL_FALSE, view)
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'projection'), 1, GL_FALSE, projection)
        # cubes
        glBindVertexArray(self.cubeVAO)
        glBindTexture(GL_TEXTURE_2D, self.cubeTexture)
        model = glm.translate(np.identity(4, np.float32), -1.0, 0.0, -1.0)
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'model'), 1, GL_FALSE, model)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        model = glm.translate(np.identity(4, np.float32), 2.0, 0.0, 0.0)
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'model'), 1, GL_FALSE, model)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        # floor
        glBindVertexArray(self.planeVAO)
        glBindTexture(GL_TEXTURE_2D, self.floorTexture)
        model = np.identity(4, np.float32)
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'model'), 1, GL_FALSE, model)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)

        glUseProgram(0)

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

def loadTexture(texPath, gammaCorrection=False):
    textureID = glGenTextures(1)
    im = Image.open(texPath)
    alpha = im.mode == 'RGBA'
    texFormat = GL_RGBA if alpha else GL_RGB
    texFormat2 = texFormat
    if gammaCorrection:
        texFormat2 = GL_SRGB_ALPHA if alpha else GL_SRGB
    glBindTexture(GL_TEXTURE_2D, textureID)
    glTexImage2D(GL_TEXTURE_2D, 0, texFormat2, im.size[0], im.size[1], 0, texFormat, GL_UNSIGNED_BYTE, im.tobytes())
    glGenerateMipmap(GL_TEXTURE_2D)

    # parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE if alpha else GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE if alpha else GL_REPEAT)
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
    QCursor.setPos(glWindow.geometry().center())
    glWindow.setWindowTitle('LearnPyOpenGL')
    glWindow.show()

    sys.exit(app.exec_())
