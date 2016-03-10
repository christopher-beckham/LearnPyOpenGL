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

        self.quadVAO = 0
        self.cubeVAO = 0
        self.hdr = True
        self.exposure = 1.0

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
        glViewport(0, 0, self.width(), self.height())
        # setup some OpenGL options
        glEnable(GL_DEPTH_TEST)

        vertexShader, fragmentShader = self.loadShaders('6.lighting.vs', '6.lighting.frag')
        self.__shader = shaders.compileProgram(vertexShader, fragmentShader)
        vertexShader, fragmentShader = self.loadShaders('6.hdr.vs', '6.hdr.frag')
        self.__hdrShader = shaders.compileProgram(vertexShader, fragmentShader)

        # light source
        self.lightPos = [np.array([0.0, 0.0, 49.5], np.float32),
                         np.array([-1.4, -1.9, 9.0], np.float32),
                         np.array([0.0, -1.0, 4.0], np.float32),
                         np.array([0.8, -1.7, 6.0], np.float32),]

        self.lightColors = [np.array([200.0, 200.0, 200.0], np.float32),
                            np.array([0.1, 0.0, 0.0], np.float32),
                            np.array([0.0, 0.0, 0.2], np.float32),
                            np.array([0.0, 0.1, 0.0], np.float32),]

        # load texture
        self.woodTexture = loadTexture(os.path.join(abPath, '..', '..', 'resources', 'textures', 'wood.png'))

        # Set up floating point framebuffer to render scene to
        self.hdrFBO = glGenFramebuffers(1)
        # Create floating point color buffer
        self.colorBuffer = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.colorBuffer)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA16F, self.width(), self.height(), 0, GL_RGBA, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        # create depth buffer (renderbuffer)
        self.rboDepth = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, self.rboDepth)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT, self.width(), self.height())
        # Attach buffer
        glBindFramebuffer(GL_FRAMEBUFFER, self.hdrFBO)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.colorBuffer, 0)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, self.rboDepth)
        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            print 'Framebuffer not complete!'
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        glClearColor(0.1, 0.1, 0.1, 1.0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

    def paintGL(self):
        currentTime = self.__timer.elapsed() / 1000.0
        self.__deltaTime = currentTime - self.__lastTime
        self.__lastTime = currentTime

        # 1. Render scene into floating point framebuffer
        glBindFramebuffer(GL_FRAMEBUFFER, self.hdrFBO)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        projection = glm.perspective(self.camera.zoom, float(self.width())/self.height(), 0.1, 100.0)
        view = self.camera.viewMatrix
        glUseProgram(self.__shader)
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'projection'), 1, GL_FALSE, projection)
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'view'), 1, GL_FALSE, view)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.woodTexture)
        # set lighting uniforms
        for i in range(len(self.lightPos)):
            glUniform3fv(glGetUniformLocation(self.__shader, 'lights[{}].Position'.format(i)), 1, self.lightPos[i])
            glUniform3fv(glGetUniformLocation(self.__shader, 'lights[{}].Color'.format(i)), 1, self.lightColors[i])
        glUniform3fv(glGetUniformLocation(self.__shader, 'viewPos'), 1, self.camera.position)
        # render tunnel
        model = glm.scale(np.identity(4, np.float32), 5.0, 5.0, 55.0)
        model = glm.translate(model, 0.0, 0.0, 25.0)
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'model'), 1, GL_FALSE, model)
        glUniform1i(glGetUniformLocation(self.__shader, 'inverse_normals'), GL_TRUE)
        self.renderCube()
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        # 2. Now render floating point color buffer to 2D quad and tonemap HDR colors to default framebuffer's (clamped) color range
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(self.__hdrShader)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.colorBuffer)
        glUniform1i(glGetUniformLocation(self.__hdrShader, 'hdr'), self.hdr)
        glUniform1f(glGetUniformLocation(self.__hdrShader, 'exposure'), self.exposure)
        self.renderQuad()

        glUseProgram(0)

        print 'exposure: {}'.format(self.exposure)

    def renderScene(self, shader):
        # Room cube
        model = np.identity(4, np.float32)
        model = glm.scale(model, 10.0, 10.0, 10.0)
        glUniformMatrix4fv(glGetUniformLocation(shader, 'model'), 1, GL_FALSE, model)
        glDisable(GL_CULL_FACE) # Note that we disable culling here since we render 'inside' the cube instead of the usual 'outside' which throws off the normal culling methods.
        glUniform1i(glGetUniformLocation(shader, 'reverse_normals'), 1) #A small little hack to invert normals when drawing cube from the inside so lighting still works.
        self.renderCube()
        glEnable(GL_CULL_FACE)
        # Cubes
        model = np.identity(4, np.float32)
        model = glm.translate(model, 4.0, -3.5, 0.0)
        glUniformMatrix4fv(glGetUniformLocation(shader, 'model'), 1, GL_FALSE, model)
        self.renderCube()
        model = glm.translate(np.identity(4, np.float32), 2.0, 3.0, 1.0)
        glUniformMatrix4fv(glGetUniformLocation(shader, 'model'), 1, GL_FALSE, model)
        self.renderCube()
        model = glm.translate(np.identity(4, np.float32), -3.0, -1.0, 0.0)
        glUniformMatrix4fv(glGetUniformLocation(shader, 'model'), 1, GL_FALSE, model)
        self.renderCube()
        model = glm.translate(np.identity(4, np.float32), -1.5, 1.0, 1.5)
        glUniformMatrix4fv(glGetUniformLocation(shader, 'model'), 1, GL_FALSE, model)
        self.renderCube()
        model = glm.rotate(np.identity(4, np.float32), 60.0, 1.0, 0.0, 1.0)
        model = glm.scale(model, 1.5, 1.5, 1.5)
        model = glm.translate(model, -1.5, 2.0, -3.0)
        glUniformMatrix4fv(glGetUniformLocation(shader, 'model'), 1, GL_FALSE, model)
        self.renderCube()

    def renderQuad(self):
        if self.quadVAO == 0:
            quadVertices = np.array([
                # positions       # texture coords
                -1.0,  1.0, 0.0,  0.0, 1.0,
                -1.0, -1.0, 0.0,  0.0, 0.0,
                 1.0,  1.0, 0.0,  1.0, 1.0,
                 1.0, -1.0, 0.0,  1.0, 0.0,
            ], np.float32)

            # setup plane VAO
            self.quadVAO = glGenVertexArrays(1)
            quadVBO = glGenBuffers(1)
            glBindVertexArray(self.quadVAO)
            glBindBuffer(GL_ARRAY_BUFFER, quadVBO)
            glBufferData(GL_ARRAY_BUFFER, quadVertices.nbytes, quadVertices, GL_STATIC_DRAW)
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * quadVertices.itemsize, None)
            glEnableVertexAttribArray(1)
            glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * quadVertices.itemsize, ctypes.c_void_p(3 * quadVertices.itemsize))

        glBindVertexArray(self.quadVAO)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        glBindVertexArray(0)

    def renderCube(self):
        # initilize (if necessary)
        if self.cubeVAO == 0:
            vertices = np.array([
                # Back face
                -0.5, -0.5, -0.5, 0.0, 0.0, -1.0, 0.0, 0.0, # Bottom-left
                0.5, 0.5, -0.5, 0.0, 0.0, -1.0, 1.0, 1.0, # top-right
                0.5, -0.5, -0.5, 0.0, 0.0, -1.0, 1.0, 0.0, # bottom-right
                0.5, 0.5, -0.5, 0.0, 0.0, -1.0, 1.0, 1.0,  # top-right
                -0.5, -0.5, -0.5, 0.0, 0.0, -1.0, 0.0, 0.0,  # bottom-left
                -0.5, 0.5, -0.5, 0.0, 0.0, -1.0, 0.0, 1.0,# top-left
                # Front face
                -0.5, -0.5, 0.5, 0.0, 0.0, 1.0, 0.0, 0.0, # bottom-left
                0.5, -0.5, 0.5, 0.0, 0.0, 1.0, 1.0, 0.0,  # bottom-right
                0.5, 0.5, 0.5, 0.0, 0.0, 1.0, 1.0, 1.0,  # top-right
                0.5, 0.5, 0.5, 0.0, 0.0, 1.0, 1.0, 1.0, # top-right
                -0.5, 0.5, 0.5, 0.0, 0.0, 1.0, 0.0, 1.0,  # top-left
                -0.5, -0.5, 0.5, 0.0, 0.0, 1.0, 0.0, 0.0,  # bottom-left
                # Left face
                -0.5, 0.5, 0.5, -1.0, 0.0, 0.0, 1.0, 0.0, # top-right
                -0.5, 0.5, -0.5, -1.0, 0.0, 0.0, 1.0, 1.0, # top-left
                -0.5, -0.5, -0.5, -1.0, 0.0, 0.0, 0.0, 1.0,  # bottom-left
                -0.5, -0.5, -0.5, -1.0, 0.0, 0.0, 0.0, 1.0, # bottom-left
                -0.5, -0.5, 0.5, -1.0, 0.0, 0.0, 0.0, 0.0,  # bottom-right
                -0.5, 0.5, 0.5, -1.0, 0.0, 0.0, 1.0, 0.0, # top-right
                # Right face
                0.5, 0.5, 0.5, 1.0, 0.0, 0.0, 1.0, 0.0, # top-left
                0.5, -0.5, -0.5, 1.0, 0.0, 0.0, 0.0, 1.0, # bottom-right
                0.5, 0.5, -0.5, 1.0, 0.0, 0.0, 1.0, 1.0, # top-right
                0.5, -0.5, -0.5, 1.0, 0.0, 0.0, 0.0, 1.0,  # bottom-right
                0.5, 0.5, 0.5, 1.0, 0.0, 0.0, 1.0, 0.0,  # top-left
                0.5, -0.5, 0.5, 1.0, 0.0, 0.0, 0.0, 0.0, # bottom-left
                # Bottom face
                -0.5, -0.5, -0.5, 0.0, -1.0, 0.0, 0.0, 1.0, # top-right
                0.5, -0.5, -0.5, 0.0, -1.0, 0.0, 1.0, 1.0, # top-left
                0.5, -0.5, 0.5, 0.0, -1.0, 0.0, 1.0, 0.0,# bottom-left
                0.5, -0.5, 0.5, 0.0, -1.0, 0.0, 1.0, 0.0, # bottom-left
                -0.5, -0.5, 0.5, 0.0, -1.0, 0.0, 0.0, 0.0, # bottom-right
                -0.5, -0.5, -0.5, 0.0, -1.0, 0.0, 0.0, 1.0, # top-right
                # Top face
                -0.5, 0.5, -0.5, 0.0, 1.0, 0.0, 0.0, 1.0,# top-left
                0.5, 0.5, 0.5, 0.0, 1.0, 0.0, 1.0, 0.0, # bottom-right
                0.5, 0.5, -0.5, 0.0, 1.0, 0.0, 1.0, 1.0, # top-right
                0.5, 0.5, 0.5, 0.0, 1.0, 0.0, 1.0, 0.0, # bottom-right
                -0.5, 0.5, -0.5, 0.0, 1.0, 0.0, 0.0, 1.0,# top-left
                -0.5, 0.5, 0.5, 0.0, 1.0, 0.0, 0.0, 0.0, # bottom-left
            ], np.float32)

            self.cubeVAO = glGenVertexArrays(1)
            cubeVBO = glGenBuffers(1)
            glBindVertexArray(self.cubeVAO)
            # fill buffer
            glBindBuffer(GL_ARRAY_BUFFER, cubeVBO)
            glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
            # link vertex attributes
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 8 * vertices.itemsize, None)
            glEnableVertexAttribArray(1)
            glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 8 * vertices.itemsize, ctypes.c_void_p(3 * vertices.itemsize))
            glEnableVertexAttribArray(2)
            glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 8 * vertices.itemsize, ctypes.c_void_p(6 * vertices.itemsize))
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            glBindVertexArray(0)
        # render cube
        glBindVertexArray(self.cubeVAO)
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
        if event.key() == Qt.Key_Space:
            self.hdr = not self.hdr
        if event.key() == Qt.Key_Q:
            self.exposure -= 0.5 * self.__deltaTime
        if event.key() == Qt.Key_E:
            self.exposure += 0.5 * self.__deltaTime

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
