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


    def loadShaders(self, vsf, fsf, gsf):
        vertexShaderFile = os.path.join(abPath, vsf)
        fragmentShaderFile = os.path.join(abPath, fsf)
        geometyShaderFile = os.path.join(abPath, gsf)
        vertexShaderSource = ''
        with open(vertexShaderFile) as vs:
            vertexShaderSource = vs.read()
        fragmentShaderSource = ''
        with open(fragmentShaderFile) as fg:
            fragmentShaderSource = fg.read()
        geometyShaderSource = ''
        with open(geometyShaderFile) as gs:
            geometyShaderSource = gs.read()

        vertexShader = shaders.compileShader(vertexShaderSource, GL_VERTEX_SHADER)
        fragmentShader = shaders.compileShader(fragmentShaderSource, GL_FRAGMENT_SHADER)
        geometryShader = shaders.compileShader(geometyShaderSource, GL_GEOMETRY_SHADER)
        return vertexShader, fragmentShader, geometryShader

    def initializeGL(self):
        vertexShader, fragmentShader, geometryShader = self.loadShaders('9.geometry_shader.vs', '9.geometry_shader.frag', '9.geometry_shader.gs')
        self.__shader = shaders.compileProgram(vertexShader, fragmentShader, geometryShader)

        vertices = np.array([
            -0.5,  0.5, 1.0, 0.0, 0.0,
             0.5,  0.5, 0.0, 1.0, 0.0,
             0.5, -0.5, 0.0, 0.0, 1.0,
            -0.5, -0.5, 1.0, 1.0, 0.0,
            ], np.float32)

        # setup VAO
        self.VAO = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        glBindVertexArray(self.VAO)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 5 * vertices.itemsize, None)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 5 * vertices.itemsize, ctypes.c_void_p(2 * vertices.itemsize))
        glBindVertexArray(0)

        #glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

    def paintGL(self):

        # Render
        # Clear the colorbuffer
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

        # Draw points
        glUseProgram(self.__shader)
        glBindVertexArray(self.VAO)
        glDrawArrays(GL_POINTS, 0, 4)
        glBindVertexArray(0)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            qApp.quit()
        self.updateGL()
        return super(GLWindow, self).keyPressEvent(event)


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)

    glWindow = GLWindow()
    glWindow.setFixedSize(800, 600)
    QCursor.setPos(glWindow.geometry().center())
    glWindow.setWindowTitle('LearnPyOpenGL')
    glWindow.show()

    sys.exit(app.exec_())
