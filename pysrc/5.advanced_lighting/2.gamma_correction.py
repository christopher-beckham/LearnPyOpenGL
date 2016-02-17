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

        self.gammaEnabled = False

        # if you want press mouse button to active camera rotation set it to false 
        self.setMouseTracking(True)

    def loadShaders(self, vsf, fsf):
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
        return vertexShader, fragmentShader

    def initializeGL(self):
        # setup some OpenGL options
        glEnable(GL_DEPTH_TEST)

        vertexShader, fragmentShader = self.loadShaders('2.gamma_correction.vs', '2.gamma_correction.frag')
        self.__shader = shaders.compileProgram(vertexShader, fragmentShader)

        vertices = np.array([
            # positions        # normals       # texture coords
             8.0, -0.5,  8.0,  0.0, 1.0, 0.0,  5.0, 0.0,
            -8.0, -0.5,  8.0,  0.0, 1.0, 0.0,  0.0, 0.0,
            -8.0, -0.5, -8.0,  0.0, 1.0, 0.0,  0.0, 5.0,

             8.0, -0.5,  8.0,  0.0, 1.0, 0.0,  5.0, 0.0,
            -8.0, -0.5, -8.0,  0.0, 1.0, 0.0,  0.0, 5.0,
             8.0, -0.5, -8.0,  0.0, 1.0, 0.0,  5.0, 5.0,
            ], np.float32)

        # setup cube VAO
        self.planeVAO = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        glBindVertexArray(self.planeVAO)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 8 * vertices.itemsize, None)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 8 * vertices.itemsize, ctypes.c_void_p(3 * vertices.itemsize))
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 8 * vertices.itemsize, ctypes.c_void_p(6 * vertices.itemsize))
        glBindVertexArray(0)

        # light source
        self.lightPos = np.array([(-3.0, 0.0, 0.0),
                                  (-1.0, 0.0, 0.0),
                                  (1.0, 0.0, 0.0),
                                  (3.0, 0.0, 0.0)], np.float32)
        self.lightColors = np.array([(0.25, 0.25, 0.25),
                                     (0.5, 0.5, 0.5),
                                     (0.75, 0.75, 0.75),
                                     (1.0, 1.0, 1.0)], np.float32)

        # load texture
        self.floorTexture = loadTexture(os.path.join(abPath, '..', '..', 'resources', 'textures', 'wood.png'), False)
        self.floorTextureGammaCorrected = loadTexture(os.path.join(abPath, '..', '..', 'resources', 'textures', 'wood.png'), True)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

    def paintGL(self):
        currentTime = self.__timer.elapsed() / 1000.0
        self.__deltaTime = currentTime - self.__lastTime
        self.__lastTime = currentTime

        # Render
        # Clear the colorbuffer
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Draw objects
        glUseProgram(self.__shader)
        view = self.camera.viewMatrix
        projection = glm.perspective(self.camera.zoom, float(self.width())/self.height(), 0.1, 100.0)
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'view'), 1, GL_FALSE, view)
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'projection'), 1, GL_FALSE, projection)
        # Set light uniforms
        glUniform3fv(glGetUniformLocation(self.__shader, 'lightPos'), 4, self.lightPos)
        glUniform3fv(glGetUniformLocation(self.__shader, 'lightColors'), 4, self.lightColors)
        glUniform3fv(glGetUniformLocation(self.__shader, 'viewPos'), 1, self.camera.position)
        glUniform1i(glGetUniformLocation(self.__shader, 'gamma'), self.gammaEnabled)
        # floor
        glBindVertexArray(self.planeVAO)
        glBindTexture(GL_TEXTURE_2D,
                      self.floorTextureGammaCorrected if self.gammaEnabled else self.floorTexture)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)

        print "Gamma enabled" if self.gammaEnabled else "Gamma disabled"

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
        if event.key() == Qt.Key_Space:
            self.gammaEnabled = not self.gammaEnabled

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
