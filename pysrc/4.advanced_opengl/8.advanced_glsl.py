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

        self.identityMat4 = np.identity(4, np.float32)

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

        vertexShader, fragmentShader = self.loadShaders('8.uniform_buffers.vs', '8.red.frag')
        self.__shaderRed = shaders.compileProgram(vertexShader, fragmentShader)
        vertexShader, fragmentShader = self.loadShaders('8.uniform_buffers.vs', '8.green.frag')
        self.__shaderGreen = shaders.compileProgram(vertexShader, fragmentShader)
        vertexShader, fragmentShader = self.loadShaders('8.uniform_buffers.vs', '8.blue.frag')
        self.__shaderBlue = shaders.compileProgram(vertexShader, fragmentShader)
        vertexShader, fragmentShader = self.loadShaders('8.uniform_buffers.vs', '8.yellow.frag')
        self.__shaderYellow = shaders.compileProgram(vertexShader, fragmentShader)

        vertices = np.array([
            -0.5, -0.5, -0.5,
             0.5,  0.5, -0.5,
             0.5, -0.5, -0.5,
             0.5,  0.5, -0.5,
            -0.5, -0.5, -0.5,
            -0.5,  0.5, -0.5,

            -0.5, -0.5,  0.5,
             0.5, -0.5,  0.5,
             0.5,  0.5,  0.5,
             0.5,  0.5,  0.5,
            -0.5,  0.5,  0.5,
            -0.5, -0.5,  0.5,

            -0.5,  0.5,  0.5,
            -0.5,  0.5, -0.5,
            -0.5, -0.5, -0.5,
            -0.5, -0.5, -0.5,
            -0.5, -0.5,  0.5,
            -0.5,  0.5,  0.5,

             0.5,  0.5,  0.5,
             0.5, -0.5, -0.5,
             0.5,  0.5, -0.5,
             0.5, -0.5, -0.5,
             0.5,  0.5,  0.5,
             0.5, -0.5,  0.5,

            -0.5, -0.5, -0.5,
             0.5, -0.5, -0.5,
             0.5, -0.5,  0.5,
             0.5, -0.5,  0.5,
            -0.5, -0.5,  0.5,
            -0.5, -0.5, -0.5,

            -0.5,  0.5, -0.5,
             0.5,  0.5,  0.5,
             0.5,  0.5, -0.5,
             0.5,  0.5,  0.5,
            -0.5,  0.5, -0.5,
            -0.5,  0.5,  0.5,
            ], np.float32)

        # setup cube VAO
        self.cubeVAO = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        glBindVertexArray(self.cubeVAO)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * vertices.itemsize, None)
        glBindVertexArray(0)

        # Create a uniform buffer object
        # First. We get the relevant block indices
        uniformBlockIndexRed = glGetUniformBlockIndex(self.__shaderRed, 'Matrices')
        uniformBlockIndexGreen= glGetUniformBlockIndex(self.__shaderGreen, 'Matrices')
        uniformBlockIndexBlue = glGetUniformBlockIndex(self.__shaderBlue, 'Matrices')
        uniformBlockIndexYellow = glGetUniformBlockIndex(self.__shaderYellow, 'Matrices')
        # Then we link each shader's uniform block to this uniform binding point
        glUniformBlockBinding(self.__shaderRed, uniformBlockIndexRed, 0)
        glUniformBlockBinding(self.__shaderGreen, uniformBlockIndexGreen, 0)
        glUniformBlockBinding(self.__shaderBlue, uniformBlockIndexBlue, 0)
        glUniformBlockBinding(self.__shaderYellow, uniformBlockIndexYellow, 0)
        # Now actually create the buffer
        self.uboMatrices = glGenBuffers(1)
        glBindBuffer(GL_UNIFORM_BUFFER, self.uboMatrices)
        glBufferData(GL_UNIFORM_BUFFER, 2 * self.identityMat4.nbytes, None, GL_STATIC_DRAW)
        glBindBuffer(GL_UNIFORM_BUFFER, 0)
        # Define the range of the buffer that links to a uniform binding point
        glBindBufferRange(GL_UNIFORM_BUFFER, 0, self.uboMatrices, 0, 2 * self.identityMat4.nbytes)

        # Store the projection matrix (we only have to do this once) (note: we're not using zoom anymore by changing the FoV. We only create the projection matrix once now)
        projection = glm.perspective(45.0, float(self.width())/self.height(), 0.1, 100.0)
        glBindBuffer(GL_UNIFORM_BUFFER, self.uboMatrices)
        glBufferSubData(GL_UNIFORM_BUFFER, 0, self.identityMat4.nbytes, projection)
        glBindBuffer(GL_UNIFORM_BUFFER, 0)

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

        view = self.camera.viewMatrix
        glBindBuffer(GL_UNIFORM_BUFFER, self.uboMatrices)
        glBufferSubData(GL_UNIFORM_BUFFER, self.identityMat4.nbytes, self.identityMat4.nbytes, view)
        glBindBuffer(GL_UNIFORM_BUFFER, 0)

        # Draw 4 cubes
        # Red
        glBindVertexArray(self.cubeVAO)
        glUseProgram(self.__shaderRed)
        model = glm.translate(np.identity(4, np.float32), -0.75, 0.75, 0.0)
        glUniformMatrix4fv(glGetUniformLocation(self.__shaderRed, 'model'), 1, GL_FALSE, model)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        # Green
        glUseProgram(self.__shaderGreen)
        model = glm.translate(np.identity(4, np.float32), 0.75, 0.75, 0.0)
        glUniformMatrix4fv(glGetUniformLocation(self.__shaderGreen, 'model'), 1, GL_FALSE, model)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        # Blue
        glUseProgram(self.__shaderBlue)
        model = glm.translate(np.identity(4, np.float32), -0.75, -0.75, 0.0)
        glUniformMatrix4fv(glGetUniformLocation(self.__shaderBlue, 'model'), 1, GL_FALSE, model)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        # Yellow
        glUseProgram(self.__shaderYellow)
        model = glm.translate(np.identity(4, np.float32), 0.75, -0.75, 0.0)
        glUniformMatrix4fv(glGetUniformLocation(self.__shaderYellow, 'model'), 1, GL_FALSE, model)
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

def loadTexture(texPath):
    textureID = glGenTextures(1)
    im = Image.open(texPath)
    alpha = im.mode == 'RGBA'
    texFormat = GL_RGBA if alpha else GL_RGB
    glBindTexture(GL_TEXTURE_2D, textureID)
    glTexImage2D(GL_TEXTURE_2D, 0, texFormat, im.size[0], im.size[1], 0, texFormat, GL_UNSIGNED_BYTE, im.tobytes())
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
