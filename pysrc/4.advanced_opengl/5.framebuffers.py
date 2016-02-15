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

    # Generate a texture that is suited for attachments to a framebufer
    def generateAttachmentTexture(self, depth, stencil):
        # what enum to use?
        attachment_type = GL_RGB
        if not depth and not stencil:
            #attachment_type = GL_RGB
            pass
        elif depth and not stencil:
            attachment_type = GL_DEPTH_COMPONENT
        elif not depth and stencil:
            attachment_type = GL_STENCIL_INDEX

        # generate texture ID and load texture data
        textureId = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, textureId)
        if not depth and not stencil:
            glTexImage2D(GL_TEXTURE_2D, 0, attachment_type, self.width(), self.height(), 0,
                         attachment_type, GL_UNSIGNED_BYTE, ctypes.c_void_p(0))
        else:
            # Using both a stencil and depth test, needs special format arguments
            glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH24_STENCIL8, self.width(), self.height(), 0,
                         GL_DEPTH_STENCIL, GL_UNSIGNED_INT_24_8, ctypes.c_void_p(0))
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)
        return textureId
    
    def initializeGL(self):
        # setup some OpenGL options
        glDepthFunc(GL_LESS)

        vertexShader, fragmentShader = self.loadShaders('5.framebuffers.vs', '5.framebuffers.frag')
        self.__shaderProgram = shaders.compileProgram(vertexShader, fragmentShader)
        vertexShader, fragmentShader = self.loadShaders('5.framebuffers_screen.vs', '5.framebuffers_screen.frag')
        self.__screenShaderProgram = shaders.compileProgram(vertexShader, fragmentShader)

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

        self.floorVertices = np.array([
            # Positions     Texture Coords (note we set these higher than 1 that together with GL_REPEAT as texture wrapping mode will cause the floor texture to repeat)
            5.0, -0.5, 5.0, 2.0, 0.0,
            -5.0, -0.5, 5.0, 0.0, 0.0,
            -5.0, -0.5, -5.0, 0.0, 2.0,

            5.0, -0.5, 5.0, 2.0, 0.0,
            -5.0, -0.5, -5.0, 0.0, 2.0,
            5.0, -0.5, -5.0, 2.0, 2.0
        ], np.float32)

        self.quadVertices = np.array([
            # Position     # Texture Coords (swapped y coordinates because texture is flipped upside down)
            -1.0, 1.0,         0.0, 1.0,
            -1.0, -1.0,        0.0, 0.0,
            1.0, -1.0,        1.0, 0.0,
            
            -1.0, 1.0,        0.0, 1.0,
            1.0, -1.0,        1.0, 0.0,
            1.0, 1.0,        1.0, 1.0,
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
        self.floorVAO = glGenVertexArrays(1)
        planeVBO = glGenBuffers(1)

        glBindVertexArray(self.floorVAO)
        glBindBuffer(GL_ARRAY_BUFFER, planeVBO)
        glBufferData(GL_ARRAY_BUFFER, self.floorVertices.nbytes, self.floorVertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * self.floorVertices.itemsize, None)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * self.floorVertices.itemsize, ctypes.c_void_p(3 * self.floorVertices.itemsize))
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        glBindVertexArray(0)

        # setup transparent plane VAO
        self.quadVAO = glGenVertexArrays(1)
        transparentVBO = glGenBuffers(1)
        glBindVertexArray(self.quadVAO)
        glBindBuffer(GL_ARRAY_BUFFER, transparentVBO)
        glBufferData(GL_ARRAY_BUFFER, self.quadVertices.nbytes, self.quadVertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 4 * self.quadVertices.itemsize, None)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * self.quadVertices.itemsize, ctypes.c_void_p(2 * self.quadVertices.itemsize))
        glBindVertexArray(0)

        # load and create a texture
        texturePath = os.path.join(abPath, '..', '..', 'resources', 'textures', 'container.jpg')
        self.cubeTexture = loadTexture(texturePath)
        texture2Path = os.path.join(abPath, '..', '..', 'resources', 'textures', 'metal.png')
        self.floorTexture = loadTexture(texture2Path)

        # Framebuffers
        self.framebuffer = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.framebuffer)
        # create a color attachment texture
        self.textureColorBuffer = self.generateAttachmentTexture(False, False)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.textureColorBuffer, 0)
        # create a renderbuffer object for depth and stencil attachment (we won't be sampling these)
        self.rbo = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, self.rbo)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, self.width(), self.height())
        glBindRenderbuffer(GL_RENDERBUFFER, 0)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, self.rbo)
        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            print 'ERROR::FRAMEBUFFER:: Framebuffer is not complete!'
            #raise Exception('ERROR::FRAMEBUFFER:: Framebuffer is not complete!')
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

    def paintGL(self):
        currentTime = self.__timer.elapsed() / 1000.0
        self.__deltaTime = currentTime - self.__lastTime
        self.__lastTime = currentTime

        # Bind to framebuffer and draw to color texture
        # as we normally would
        glBindFramebuffer(GL_FRAMEBUFFER, self.framebuffer)
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

        # Floor
        glBindVertexArray(self.floorVAO)
        glBindTexture(GL_TEXTURE_2D, self.floorTexture)
        glUniformMatrix4fv(modelLoc, 1, GL_FALSE, np.identity(4))
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)

        # Cubes
        glBindVertexArray(self.cubeVAO)
        glBindTexture(GL_TEXTURE_2D, self.cubeTexture)
        model = glm.translate(np.identity(4), -1, 0, -1)
        glUniformMatrix4fv(modelLoc, 1, GL_FALSE, model)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        model = glm.translate(np.identity(4), 2, 0, 0)
        glUniformMatrix4fv(modelLoc, 1, GL_FALSE, model)
        glDrawArrays(GL_TRIANGLES, 0, 36)
        glBindVertexArray(0)


        # Bind to default framebuffer again and draw the
        # quad plane with attched screen texture
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        # Clear all relevant buffers
        glClearColor(1.0, 1.0, 1.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        glDisable(GL_DEPTH_TEST)

        # Draw Screen
        glUseProgram(self.__screenShaderProgram)
        glBindVertexArray(self.quadVAO)
        glBindTexture(GL_TEXTURE_2D, self.textureColorBuffer)
        glDrawArrays(GL_TRIANGLES, 0, 6)
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

    def closeEvent(self, event):
        glDeleteFramebuffers(1, self.framebuffer)
        return super(GLWindow, self).closeEvent(event)

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
