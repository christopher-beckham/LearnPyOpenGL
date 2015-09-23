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
        self.__lastX = self.width() / 2.0
        self.__lastY = self.height() / 2.0
        self.__firstMouse = True

        self.lightPos = np.array([1.2, 1.0, 2.0], np.float32)

        self.__deltaTime = 0.0
        self.__lastTime = 0.0

        # if you want press mouse button to active camera rotation set it to false 
        self.setMouseTracking(True)

    def loadShaders(self, vertexShader, fragmentShader):
        vertexShaderFile = os.path.join(abPath, vertexShader)
        fragmentShaderFile = os.path.join(abPath, fragmentShader)
        vertexShaderSource = ''
        with open(vertexShaderFile) as vs:
            vertexShaderSource = vs.read()
        fragmentShaderSource = ''
        with open(fragmentShaderFile) as fg:
            fragmentShaderSource = fg.read()

        vertexShader = shaders.compileShader(vertexShaderSource, GL_VERTEX_SHADER)
        fragmentShader = shaders.compileShader(fragmentShaderSource, GL_FRAGMENT_SHADER)
        shaderProgram = shaders.compileProgram(vertexShader, fragmentShader)
        return shaderProgram
    
    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)

        self.__lightingShader = self.loadShaders("4.lighting_maps.vs", "4.lighting_maps.frag")
        self.__lampShader = self.loadShaders("0.lamp.vs", "0.lamp.frag")

        vertices = np.array([
            -0.5, -0.5, -0.5,  0.0, 0.0, -1.0,  0.0, 0.0,
             0.5, -0.5, -0.5,  0.0, 0.0, -1.0,  1.0, 0.0,
             0.5,  0.5, -0.5,  0.0, 0.0, -1.0,  1.0, 1.0,
             0.5,  0.5, -0.5,  0.0, 0.0, -1.0,  1.0, 1.0,
            -0.5,  0.5, -0.5,  0.0, 0.0, -1.0,  0.0, 1.0,
            -0.5, -0.5, -0.5,  0.0, 0.0, -1.0,  0.0, 0.0,

            -0.5, -0.5,  0.5,  0.0, 0.0, 1.0,  0.0, 0.0,
             0.5, -0.5,  0.5,  0.0, 0.0, 1.0,  1.0, 0.0,
             0.5,  0.5,  0.5,  0.0, 0.0, 1.0,  1.0, 1.0,
             0.5,  0.5,  0.5,  0.0, 0.0, 1.0,  1.0, 1.0,
            -0.5,  0.5,  0.5,  0.0, 0.0, 1.0,  0.0, 1.0,
            -0.5, -0.5,  0.5,  0.0, 0.0, 1.0,  0.0, 0.0,

            -0.5,  0.5,  0.5,  -1.0, 0.0, 0.0,  1.0, 0.0,
            -0.5,  0.5, -0.5,  -1.0, 0.0, 0.0,  1.0, 1.0,
            -0.5, -0.5, -0.5,  -1.0, 0.0, 0.0,  0.0, 1.0,
            -0.5, -0.5, -0.5,  -1.0, 0.0, 0.0,  0.0, 1.0,
            -0.5, -0.5,  0.5,  -1.0, 0.0, 0.0,  0.0, 0.0,
            -0.5,  0.5,  0.5,  -1.0, 0.0, 0.0,  1.0, 0.0,

             0.5,  0.5,  0.5,  1.0, 0.0, 0.0,  1.0, 0.0,
             0.5,  0.5, -0.5,  1.0, 0.0, 0.0,  1.0, 1.0,
             0.5, -0.5, -0.5,  1.0, 0.0, 0.0,  0.0, 1.0,
             0.5, -0.5, -0.5,  1.0, 0.0, 0.0,  0.0, 1.0,
             0.5, -0.5,  0.5,  1.0, 0.0, 0.0,  0.0, 0.0,
             0.5,  0.5,  0.5,  1.0, 0.0, 0.0,  1.0, 0.0,

            -0.5, -0.5, -0.5,  0.0, -1.0, 0.0,  0.0, 1.0,
             0.5, -0.5, -0.5,  0.0, -1.0, 0.0,  1.0, 1.0,
             0.5, -0.5,  0.5,  0.0, -1.0, 0.0,  1.0, 0.0,
             0.5, -0.5,  0.5,  0.0, -1.0, 0.0,  1.0, 0.0,
            -0.5, -0.5,  0.5,  0.0, -1.0, 0.0,  0.0, 0.0,
            -0.5, -0.5, -0.5,  0.0, -1.0, 0.0,  0.0, 1.0,

            -0.5,  0.5, -0.5,  0.0, 1.0, 0.0,  0.0, 1.0,
             0.5,  0.5, -0.5,  0.0, 1.0, 0.0,  1.0, 1.0,
             0.5,  0.5,  0.5,  0.0, 1.0, 0.0,  1.0, 0.0,
             0.5,  0.5,  0.5,  0.0, 1.0, 0.0,  1.0, 0.0,
            -0.5,  0.5,  0.5,  0.0, 1.0, 0.0,  0.0, 0.0,
            -0.5,  0.5, -0.5,  0.0, 1.0, 0.0,  0.0, 1.0,
            ], np.float32)

        self.__containerVAO = glGenVertexArrays(1)
        vbo = glGenBuffers(1)

        glBindVertexArray(self.__containerVAO)

        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 8 * vertices.itemsize, None)
        glEnableVertexAttribArray(0)

        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 8 * vertices.itemsize, ctypes.c_void_p(3 * vertices.itemsize))
        glEnableVertexAttribArray(1)

        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 8 * vertices.itemsize, ctypes.c_void_p(6 * vertices.itemsize))
        glEnableVertexAttribArray(2)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

        self.__lightVAO = glGenVertexArrays(1)
        glBindVertexArray(self.__lightVAO)
        # we only need to bind to the vbo (to link it with glVertexAttribPointer), no need to fill it; the VBO's data already contains all we need.
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        # set the vertex attributes (only position data for the lamp))
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 8 * vertices.itemsize, None)
        glEnableVertexAttribArray(0)
        glBindVertexArray(0)

        # load textures
        self.diffuseMap, self.specularMap, self.emissionMap = glGenTextures(3)
        # diffuse map
        texturePath = os.path.join(abPath, '..', '..', 'resources', 'textures', 'container2.png')
        im = Image.open(texturePath)
        #im = im.transpose(Image.FLIP_TOP_BOTTOM)

        glBindTexture(GL_TEXTURE_2D, self.diffuseMap)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, im.size[0], im.size[1], 0, GL_RGBA, GL_UNSIGNED_BYTE, im.tostring())
        glGenerateMipmap(GL_TEXTURE_2D)
        im.close()
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST_MIPMAP_NEAREST)

        # specular map
        texturePath = os.path.join(abPath, '..', '..', 'resources', 'textures', 'container2_specular.png')
        im = Image.open(texturePath)
        #im = im.transpose(Image.FLIP_TOP_BOTTOM)

        glBindTexture(GL_TEXTURE_2D, self.specularMap)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, im.size[0], im.size[1], 0, GL_RGBA, GL_UNSIGNED_BYTE, im.tostring())
        glGenerateMipmap(GL_TEXTURE_2D)
        im.close()
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST_MIPMAP_NEAREST)
        glBindTexture(GL_TEXTURE_2D, 0)

        # set texture units
        glUseProgram(self.__lightingShader)
        glUniform1i(glGetUniformLocation(self.__lightingShader, 'material.diffuse'), 0)
        glUniform1i(glGetUniformLocation(self.__lightingShader, 'material.specular'), 1)
        glUseProgram(0)

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

        glUseProgram(self.__lightingShader)
        lightPosLoc = glGetUniformLocation(self.__lightingShader, 'light.position')
        viewPosLoc = glGetUniformLocation(self.__lightingShader, 'viewPos')
        glUniform3f(lightPosLoc, self.lightPos[0], self.lightPos[1], self.lightPos[2])
        glUniform3f(viewPosLoc, self.camera.position[0], self.camera.position[1], self.camera.position[2])
        # set lights properties
        glUniform3f(glGetUniformLocation(self.__lightingShader, 'light.ambient'),
                    0.2, 0.2, 0.2)
        glUniform3f(glGetUniformLocation(self.__lightingShader, 'light.diffuse'),
                    0.5, 0.5, 0.5)
        glUniform3f(glGetUniformLocation(self.__lightingShader, 'light.specular'),
                    1.0, 1.0, 1.0)
        # set material properties
        glUniform1f(glGetUniformLocation(self.__lightingShader, 'material.shininess'), 32.0)

        view = self.camera.viewMatrix
        projection = glm.perspective(self.camera.zoom, float(self.width()) / self.height(), 0.1, 100.0)
        # get their uniform location
        modelLoc = glGetUniformLocation(self.__lightingShader, 'model')
        viewLoc = glGetUniformLocation(self.__lightingShader, 'view')
        projLoc = glGetUniformLocation(self.__lightingShader, 'projection')
        glUniformMatrix4fv(viewLoc, 1, GL_FALSE, view)
        glUniformMatrix4fv(projLoc, 1, GL_FALSE, projection)

        # bind diffuse map
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.diffuseMap)
        # bind specular map
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.specularMap)

        # Draw the container (using container's vertex attributes)
        glBindVertexArray(self.__containerVAO)
        model = np.identity(4, np.float32)
        glUniformMatrix4fv(modelLoc, 1, GL_FALSE, model)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        glBindVertexArray(0)

        # Also draw the lamp object, again binding the appropriate shader
        glUseProgram(self.__lampShader)
        # Get location objects for the matrices on the lamp shader (these could be different on a different shader)
        modelLoc = glGetUniformLocation(self.__lampShader, 'model')
        viewLoc = glGetUniformLocation(self.__lampShader, 'view')
        projLoc = glGetUniformLocation(self.__lampShader, 'projection')
        # set matrices
        glUniformMatrix4fv(viewLoc, 1, GL_FALSE, view)
        glUniformMatrix4fv(projLoc, 1, GL_FALSE, projection)
        model = np.identity(4, np.float32)
        model = glm.scale(model, 0.2, 0.2, 0.2)
        model = glm.translate(model, self.lightPos[0], self.lightPos[1], self.lightPos[2])
        glUniformMatrix4fv(modelLoc, 1, GL_FALSE, model)
        # Draw the light object (using light's vertex attributes)
        glBindVertexArray(self.__lightVAO)
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
