#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math
import ctypes
import random
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
from model import Model

currentFile = inspect.getframeinfo(inspect.currentframe()).filename
abPath = os.path.dirname(os.path.abspath(currentFile))

def lerp(a, b, f):
    return a + f * (b - a)


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
        self.draw_mode = 1

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

        vertexShader, fragmentShader = self.loadShaders('9.ssao_geometry.vs', '9.ssao_geometry.frag')
        self.__geometyPassShader = shaders.compileProgram(vertexShader, fragmentShader)
        vertexShader, fragmentShader = self.loadShaders('9.ssao.vs', '9.ssao_blur.frag')
        self.__ssaoBlurShader = shaders.compileProgram(vertexShader, fragmentShader)
        _shaders = self.loadShaders('9.ssao.vs', '9.ssao_lighting.frag')
        self.__lightingPassShader = glCreateProgram()
        [glAttachShader(self.__lightingPassShader, s) for s in _shaders if s]
        self.__lightingPassShader = shaders.ShaderProgram(self.__lightingPassShader)
        glLinkProgram(self.__lightingPassShader)
        glUseProgram(self.__lightingPassShader)
        glUniform1i(glGetUniformLocation(self.__lightingPassShader, 'gPositionDepth'), 0)
        glUniform1i(glGetUniformLocation(self.__lightingPassShader, 'gNormal'), 1)
        glUniform1i(glGetUniformLocation(self.__lightingPassShader, 'gAlbedo'), 2)
        glUniform1i(glGetUniformLocation(self.__lightingPassShader, 'ssao'), 3)
        self.__lightingPassShader.check_validate()
        self.__lightingPassShader.check_linked()
        [glDeleteShader(s) for s in _shaders if s]
        _shaders = self.loadShaders('9.ssao.vs', '9.ssao.frag')
        self.__ssaoShader = glCreateProgram()
        [glAttachShader(self.__ssaoShader, s) for s in _shaders if s]
        self.__ssaoShader = shaders.ShaderProgram(self.__ssaoShader)
        glLinkProgram(self.__ssaoShader)
        glUseProgram(self.__ssaoShader)
        glUniform1i(glGetUniformLocation(self.__ssaoShader, 'gPositionDepth'), 0)
        glUniform1i(glGetUniformLocation(self.__ssaoShader, 'gNormal'), 1)
        glUniform1i(glGetUniformLocation(self.__ssaoShader, 'texNoise'), 2)
        self.__ssaoShader.check_validate()
        self.__ssaoShader.check_linked()
        [glDeleteShader(s) for s in _shaders if s]

        # models
        modelPath = os.path.join(abPath, '..', '..', 'resources', 'objects', 'nanosuit', 'nanosuit.obj')
        self.cyborg = Model(modelPath)

        # light position
        self.lightPos = np.array([2.0, 4.0, -2.0], np.float32)
        self.lightColor = np.array([0.2, 0.2, 0.7], np.float32)

        # set up G-Buffer
        # 3 textures:
        # 1. Position (RGB)
        # 2. Color (RGB) + Specular (A)
        # 3. Normals (RGB)
        self.gbuffer = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.gbuffer)
        self.gPositionDepth, self.gNormal, self.gAlbedo = glGenTextures(3)
        # position color buffer
        glBindTexture(GL_TEXTURE_2D, self.gPositionDepth)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB16F, self.width(), self.height(), 0, GL_RGB, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.gPositionDepth, 0)
        # normal color buffer
        glBindTexture(GL_TEXTURE_2D, self.gNormal)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB16F, self.width(), self.height(), 0, GL_RGB, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT1, GL_TEXTURE_2D, self.gNormal, 0)
        # color + specular buffer
        glBindTexture(GL_TEXTURE_2D, self.gAlbedo)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB16F, self.width(), self.height(), 0, GL_RGB, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT2, GL_TEXTURE_2D, self.gAlbedo, 0)
        # tell OpenGL which color attachments we'll use (of this framebuffer)
        attachments = [GL_COLOR_ATTACHMENT0, GL_COLOR_ATTACHMENT1, GL_COLOR_ATTACHMENT2]
        glDrawBuffers(3, attachments)
        # create depth buffer (renderbuffer)
        self.rboDepth = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, self.rboDepth)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT, self.width(), self.height())
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, self.rboDepth)
        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            print 'GBuffer Framebuffer not complete!'
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        # Also create framebuffer to hold SSAO processing stage
        self.ssaoFBO, self.ssaoBlurFBO = glGenFramebuffers(2)
        glBindFramebuffer(GL_FRAMEBUFFER, self.ssaoFBO)
        self.ssaoColorBuffer, self.ssaoColorBufferBlur = glGenTextures(2)
        # SSAO Color buffer
        glBindTexture(GL_TEXTURE_2D, self.ssaoColorBuffer)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, self.width(), self.height(), 0, GL_RGB, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.ssaoColorBuffer, 0)
        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            print 'SSAO Framebuffer not complete!'
        # and blur stage
        glBindFramebuffer(GL_FRAMEBUFFER, self.ssaoBlurFBO)
        glBindTexture(GL_TEXTURE_2D, self.ssaoColorBufferBlur)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, self.width(), self.height(), 0, GL_RGB, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.ssaoColorBufferBlur, 0)
        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            print 'SSAO Blur Framebuffer not complete!'
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        # Sample kernel
        self.ssaoKernel = []
        for i in range(64):
            sample = np.array([random.random() * 2.0 - 1.0,
                               random.random() * 2.0 - 1.0,
                               random.random()], np.float32)
            sample = glm.normalize(sample)
            sample *= random.random()
            scale = i / 64.0
            # scale samples s.t. they're more aligned to center of kernel
            scale = lerp(0.1, 1.0, scale * scale)
            sample *= scale
            self.ssaoKernel.append(sample)

        # Noise texture
        self.ssaoNoise = [np.array([random.random() * 2.0 - 1.0, random.random() * 2.0 - 1.0, 0.0], np.float32) for i in range(16)]
        self.ssaoNoise = np.array(self.ssaoNoise, np.float32)
        # for i in range(16):
        #     noise = np.array([random.random() * 2.0 - 1.0, random.random() * 2.0 - 1.0, 0.0], np.float32)
        self.noiseTexture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.noiseTexture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB16F, 4, 4, 0, GL_RGB, GL_FLOAT, self.ssaoNoise)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

        glClearColor(0.1, 0.1, 0.1, 1.0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

    def paintGL(self):
        currentTime = self.__timer.elapsed() / 1000.0
        self.__deltaTime = currentTime - self.__lastTime
        self.__lastTime = currentTime

        # 1. Geometry Pass: render scene's geometry/color data into gbuffer
        glBindFramebuffer(GL_FRAMEBUFFER, self.gbuffer)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        projection = glm.perspective(self.camera.zoom, float(self.width()) / self.height(), 0.1, 100.0)
        view = self.camera.viewMatrix
        glUseProgram(self.__geometyPassShader)
        glUniformMatrix4fv(glGetUniformLocation(self.__geometyPassShader, 'projection'), 1, GL_FALSE, projection)
        glUniformMatrix4fv(glGetUniformLocation(self.__geometyPassShader, 'view'), 1, GL_FALSE, view)
        # Floor cube
        model = glm.scale(np.identity(4, np.float32), 20.0, 1.0, 28.0)
        model = glm.translate(model, 0.0, -1.0, 0.0)
        glUniformMatrix4fv(glGetUniformLocation(self.__geometyPassShader, 'model'), 1, GL_FALSE, model)
        self.renderCube()
        # Nanosuit model on the floor
        model = glm.scale(np.identity(4, np.float32), 0.5, 0.5, 0.5)
        model = glm.rotate(model, -90.0, 1.0, 0.0, 0.0)
        model = glm.translate(model, 0.0, 0.0, 5.0)
        glUniformMatrix4fv(glGetUniformLocation(self.__geometyPassShader, 'model'), 1, GL_FALSE, model)
        self.cyborg.draw(self.__geometyPassShader)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        
        # 2. Create SSAO texture
        glBindFramebuffer(GL_FRAMEBUFFER, self.ssaoFBO)
        glClear(GL_COLOR_BUFFER_BIT)
        glUseProgram(self.__ssaoShader)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.gPositionDepth)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.gNormal)
        glActiveTexture(GL_TEXTURE2)
        glBindTexture(GL_TEXTURE_2D, self.noiseTexture)
        # send kernel + rotation
        [glUniform3fv(glGetUniformLocation(self.__ssaoShader, 'samples[{}]'.format(i)), 1, self.ssaoKernel[i]) for i in range(64)]
        glUniformMatrix4fv(glGetUniformLocation(self.__ssaoShader, 'projection'), 1, GL_FALSE, projection)
        self.renderQuad()
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        
        # 3. Blur SSAO texture to remove noise
        glBindFramebuffer(GL_FRAMEBUFFER, self.ssaoBlurFBO)
        glClear(GL_COLOR_BUFFER_BIT)
        glUseProgram(self.__ssaoBlurShader)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.ssaoColorBuffer)
        self.renderQuad()
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        # 4. Lighting Pass: calculate lighting by iterating over a screen filled quad pixel-by-pixel using the gbuffer's content.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(self.__lightingPassShader)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.gPositionDepth)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.gNormal)
        glActiveTexture(GL_TEXTURE2)
        glBindTexture(GL_TEXTURE_2D, self.gAlbedo)
        glActiveTexture(GL_TEXTURE3) # add extra SSAO texture to lighting pass
        glBindTexture(GL_TEXTURE_2D, self.ssaoColorBufferBlur)
        # also send light relevent uniforms
        lightPosView = (self.camera.viewMatrix * np.array([self.lightPos[0], self.lightPos[1], self.lightPos[2], 1.0], np.float32))[3, :4]
        glUniform3fv(glGetUniformLocation(self.__lightingPassShader, 'lightsPosition'), 1, lightPosView)
        glUniform3fv(glGetUniformLocation(self.__lightingPassShader, 'lightsColor'), 1, self.lightColor)
        # Update attenuation parameters and calculate radius
        _constant = 1.0 # Note that we don't send this to the shader, we assume it is always 1.0 (in our case)
        linear = 0.09
        quadratic = 0.032
        glUniform1f(glGetUniformLocation(self.__lightingPassShader, 'lights.Linear'), linear)
        glUniform1f(glGetUniformLocation(self.__lightingPassShader, 'lights.Quadratic'), quadratic)
        glUniform1i(glGetUniformLocation(self.__lightingPassShader, 'draw_mode'), self.draw_mode)
        self.renderQuad()

        glUseProgram(0)

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

        if event.key() == Qt.Key_1:
            self.draw_mode = 1
        if event.key() == Qt.Key_2:
            self.draw_mode = 2
        if event.key() == Qt.Key_3:
            self.draw_mode = 3
        if event.key() == Qt.Key_4:
            self.draw_mode = 4
        if event.key() == Qt.Key_5:
            self.draw_mode = 5

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
