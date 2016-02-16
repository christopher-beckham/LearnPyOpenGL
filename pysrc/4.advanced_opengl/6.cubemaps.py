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

    def loadCubmap(self, faces):
        textureId = glGenTextures(1)
        glActiveTexture(GL_TEXTURE0)

        glBindTexture(GL_TEXTURE_CUBE_MAP, textureId)
        for index, f in enumerate(faces):
            im = Image.open(f)
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X + index, 0, GL_RGB, im.size[0],
                         im.size[1], 0, GL_RGB, GL_UNSIGNED_BYTE, im.tobytes())
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
        glBindTexture(GL_TEXTURE_CUBE_MAP, 0)
        return textureId


    def initializeGL(self):
        # setup some OpenGL options
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

        vertexShader, fragmentShader = self.loadShaders('6.cubemaps.vs', '6.cubemaps.frag')
        self.__shaderProgram = shaders.compileProgram(vertexShader, fragmentShader)
        vertexShader, fragmentShader = self.loadShaders('6.skybox.vs', '6.skybox.frag')
        self.__skyboxShaderProgram = shaders.compileProgram(vertexShader, fragmentShader)

        vertices = np.array([
            -0.5, -0.5, -0.5,  0.0, 0.0, -1.0,
             0.5, -0.5, -0.5,  0.0, 0.0, -1.0,
             0.5,  0.5, -0.5,  0.0, 0.0, -1.0,
             0.5,  0.5, -0.5,  0.0, 0.0, -1.0,
            -0.5,  0.5, -0.5,  0.0, 0.0, -1.0,
            -0.5, -0.5, -0.5,  0.0, 0.0, -1.0,

            -0.5, -0.5,  0.5,  0.0, 0.0, 1.0,
             0.5, -0.5,  0.5,  0.0, 0.0, 1.0,
             0.5,  0.5,  0.5,  0.0, 0.0, 1.0,
             0.5,  0.5,  0.5,  0.0, 0.0, 1.0,
            -0.5,  0.5,  0.5,  0.0, 0.0, 1.0,
            -0.5, -0.5,  0.5,  0.0, 0.0, 1.0,

            -0.5,  0.5,  0.5,  -1.0, 0.0, 0.0,
            -0.5,  0.5, -0.5,  -1.0, 0.0, 0.0,
            -0.5, -0.5, -0.5,  -1.0, 0.0, 0.0,
            -0.5, -0.5, -0.5,  -1.0, 0.0, 0.0,
            -0.5, -0.5,  0.5,  -1.0, 0.0, 0.0,
            -0.5,  0.5,  0.5,  -1.0, 0.0, 0.0,

             0.5,  0.5,  0.5,  1.0, 0.0, 0.0,
             0.5,  0.5, -0.5,  1.0, 0.0, 0.0,
             0.5, -0.5, -0.5,  1.0, 0.0, 0.0,
             0.5, -0.5, -0.5,  1.0, 0.0, 0.0,
             0.5, -0.5,  0.5,  1.0, 0.0, 0.0,
             0.5,  0.5,  0.5,  1.0, 0.0, 0.0,

            -0.5, -0.5, -0.5,  0.0, -1.0, 0.0,
             0.5, -0.5, -0.5,  0.0, -1.0, 0.0,
             0.5, -0.5,  0.5,  0.0, -1.0, 0.0,
             0.5, -0.5,  0.5,  0.0, -1.0, 0.0,
            -0.5, -0.5,  0.5,  0.0, -1.0, 0.0,
            -0.5, -0.5, -0.5,  0.0, -1.0, 0.0,

            -0.5,  0.5, -0.5,  0.0, 1.0, 0.0,
             0.5,  0.5, -0.5,  0.0, 1.0, 0.0,
             0.5,  0.5,  0.5,  0.0, 1.0, 0.0,
             0.5,  0.5,  0.5,  0.0, 1.0, 0.0,
            -0.5,  0.5,  0.5,  0.0, 1.0, 0.0,
            -0.5,  0.5, -0.5,  0.0, 1.0, 0.0,
            ], np.float32)

        self.skyboxVertices = np.array([
            -1.0, 1.0, -1.0,
            -1.0, -1.0, -1.0,
            1.0, -1.0, -1.0,
            1.0, -1.0, -1.0,
            1.0, 1.0, -1.0,
            -1.0, 1.0, -1.0,

            -1.0, -1.0, 1.0,
            -1.0, -1.0, -1.0,
            -1.0, 1.0, -1.0,
            -1.0, 1.0, -1.0,
            -1.0, 1.0, 1.0,
            -1.0, -1.0, 1.0,

            1.0, -1.0, -1.0,
            1.0, -1.0, 1.0,
            1.0, 1.0, 1.0,
            1.0, 1.0, 1.0,
            1.0, 1.0, -1.0,
            1.0, -1.0, -1.0,

            -1.0, -1.0, 1.0,
            -1.0, 1.0, 1.0,
            1.0, 1.0, 1.0,
            1.0, 1.0, 1.0,
            1.0, -1.0, 1.0,
            -1.0, -1.0, 1.0,

            -1.0, -1.0, -1.0,
            -1.0, -1.0, 1.0,
            1.0, -1.0, -1.0,
            1.0, -1.0, -1.0,
            -1.0, -1.0, 1.0,
            1.0, -1.0, 1.0,
        ], np.float32)

        # setup cube VAO
        self.cubeVAO = glGenVertexArrays(1)
        vbo = glGenBuffers(1)

        glBindVertexArray(self.cubeVAO)

        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * vertices.itemsize, None)
        glEnableVertexAttribArray(0)

        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * vertices.itemsize, ctypes.c_void_p(3 * vertices.itemsize))
        glEnableVertexAttribArray(1)

        # setup skybox VAO
        self.skyboxVAO = glGenVertexArrays(1)
        skyboxVBO = glGenBuffers(1)

        glBindVertexArray(self.skyboxVAO)
        glBindBuffer(GL_ARRAY_BUFFER, skyboxVBO)
        glBufferData(GL_ARRAY_BUFFER, self.skyboxVertices.nbytes, self.skyboxVertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * self.skyboxVertices.itemsize, None)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

        # load and create a texture
        textures = []
        textures.append(os.path.join(abPath, '..', '..', 'resources', 'textures', 'skybox', 'right.jpg'))
        textures.append(os.path.join(abPath, '..', '..', 'resources', 'textures', 'skybox', 'left.jpg'))
        textures.append(os.path.join(abPath, '..', '..', 'resources', 'textures', 'skybox', 'top.jpg'))
        textures.append(os.path.join(abPath, '..', '..', 'resources', 'textures', 'skybox', 'bottom.jpg'))
        textures.append(os.path.join(abPath, '..', '..', 'resources', 'textures', 'skybox', 'back.jpg'))
        textures.append(os.path.join(abPath, '..', '..', 'resources', 'textures', 'skybox', 'front.jpg'))
        self.skyboxTexture = self.loadCubmap(textures)

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

        glEnable(GL_DEPTH_TEST)
        glUseProgram(self.__shaderProgram)

        view = self.camera.viewMatrix
        projection = glm.perspective(self.camera.zoom, float(self.width()) / self.height(), 0.1, 100.0)
        # get their uniform location
        modelLoc = glGetUniformLocation(self.__shaderProgram, 'model')
        viewLoc = glGetUniformLocation(self.__shaderProgram, 'view')
        projLoc = glGetUniformLocation(self.__shaderProgram, 'projection')
        glUniformMatrix4fv(viewLoc, 1, GL_FALSE, view)
        glUniformMatrix4fv(projLoc, 1, GL_FALSE, projection)
        model = np.identity(4, np.float32)
        glUniformMatrix4fv(modelLoc, 1, GL_FALSE, model)


        # Cubes
        glBindVertexArray(self.cubeVAO)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.skyboxTexture)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        glBindVertexArray(0)

        # Draw skybox as last
        glDepthFunc(GL_LEQUAL)
        glUseProgram(self.__skyboxShaderProgram)
        view = np.array(self.camera.viewMatrix)
        view[3][0] = 0.0
        view[3][1] = 0.0
        view[3][2] = 0.0
        glUniformMatrix4fv(glGetUniformLocation(self.__skyboxShaderProgram, 'view'), 1, GL_FALSE, view)
        glUniformMatrix4fv(glGetUniformLocation(self.__skyboxShaderProgram, 'projection'), 1, GL_FALSE, projection)
        # skybox cube
        glBindVertexArray(self.skyboxVAO)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.skyboxTexture)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        glBindVertexArray(0)
        glDepthFunc(GL_LESS)

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
