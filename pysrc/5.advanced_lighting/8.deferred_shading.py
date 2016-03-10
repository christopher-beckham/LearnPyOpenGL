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
        self.wireframe = False

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

        vertexShader, fragmentShader = self.loadShaders('8.g_buffer.vs', '8.g_buffer.frag')
        self.__geometyPassShader = shaders.compileProgram(vertexShader, fragmentShader)
        vertexShader, fragmentShader = self.loadShaders('8.deferred_light_box.vs', '8.deferred_light_box.frag')
        self.__lightBoxShader = shaders.compileProgram(vertexShader, fragmentShader)
        _shaders = self.loadShaders('8.deferred_shading.vs', '8.deferred_shading.frag')
        self.__lightingPassShader = glCreateProgram()
        [glAttachShader(self.__lightingPassShader, s) for s in _shaders if s]
        self.__lightingPassShader = shaders.ShaderProgram(self.__lightingPassShader)
        glLinkProgram(self.__lightingPassShader)
        glUseProgram(self.__lightingPassShader)
        glUniform1i(glGetUniformLocation(self.__lightingPassShader, 'gPosition'), 0)
        glUniform1i(glGetUniformLocation(self.__lightingPassShader, 'gNormal'), 1)
        glUniform1i(glGetUniformLocation(self.__lightingPassShader, 'gAlbedoSpec'), 2)
        self.__lightingPassShader.check_validate()
        self.__lightingPassShader.check_linked()
        [glDeleteShader(s) for s in _shaders if s]

        # models
        modelPath = os.path.join(abPath, '..', '..', 'resources', 'objects', 'nanosuit', 'nanosuit.obj')
        self.cyborg = Model(modelPath)
        self.objectPosition = [
            np.array([-3.0, -3.0, -3.0], np.float32),
            np.array([ 0.0, -3.0, -3.0], np.float32),
            np.array([ 3.0, -3.0, -3.0], np.float32),
            np.array([-3.0, -3.0,  0.0], np.float32),
            np.array([ 0.0, -3.0,  0.0], np.float32),
            np.array([ 3.0, -3.0,  0.0], np.float32),
            np.array([-3.0, -3.0,  3.0], np.float32),
            np.array([ 0.0, -3.0,  3.0], np.float32),
            np.array([ 3.0, -3.0,  3.0], np.float32),
        ]

        # light position
        self.lightPos = []
        self.lightColors = []
        random.seed(13)
        for i in range(32):
            # calculate slightly random offsets
            xpos = (random.randint(0, 99) / 100.0) * 6.0 - 3.0
            ypos = (random.randint(0, 99) / 100.0) * 6.0 - 4.0
            zpos = (random.randint(0, 99) / 100.0) * 6.0 - 3.0
            self.lightPos.append(np.array([xpos, ypos, zpos], np.float32))
            # also calculate random color
            rcolor = (random.randint(0, 99) / 200.0) + 0.5 # Between 0.5 and 1.0
            gcolor = (random.randint(0, 99) / 200.0) + 0.5 # Between 0.5 and 1.0
            bcolor = (random.randint(0, 99) / 200.0) + 0.5 # Between 0.5 and 1.0
            self.lightColors.append(np.array([rcolor, gcolor, bcolor], np.float32))

        # set up G-Buffer
        # 3 textures:
        # 1. Position (RGB)
        # 2. Color (RGB) + Specular (A)
        # 3. Normals (RGB)
        self.gbuffer = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.gbuffer)
        self.gPosition, self.gNormal, self.gAlbedoSpec = glGenTextures(3)
        # position color buffer
        glBindTexture(GL_TEXTURE_2D, self.gPosition)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB16F, self.width(), self.height(), 0, GL_RGB, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.gPosition, 0)
        # normal color buffer
        glBindTexture(GL_TEXTURE_2D, self.gNormal)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB16F, self.width(), self.height(), 0, GL_RGB, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT1, GL_TEXTURE_2D, self.gNormal, 0)
        # color + specular buffer
        glBindTexture(GL_TEXTURE_2D, self.gAlbedoSpec)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width(), self.height(), 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT2, GL_TEXTURE_2D, self.gAlbedoSpec, 0)
        # tell OpenGL which color attachments we'll use (of this framebuffer)
        attachments = [GL_COLOR_ATTACHMENT0, GL_COLOR_ATTACHMENT1, GL_COLOR_ATTACHMENT2]
        glDrawBuffers(3, attachments)
        # create depth buffer (renderbuffer)
        self.rboDepth = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, self.rboDepth)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT, self.width(), self.height())
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

        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if self.wireframe else GL_FILL)

        # 1. Geometry Pass: render scene's geometry/color data into gbuffer
        glBindFramebuffer(GL_FRAMEBUFFER, self.gbuffer)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        projection = glm.perspective(self.camera.zoom, float(self.width()) / self.height(), 0.1, 100.0)
        view = self.camera.viewMatrix
        glUseProgram(self.__geometyPassShader)
        glUniformMatrix4fv(glGetUniformLocation(self.__geometyPassShader, 'projection'), 1, GL_FALSE, projection)
        glUniformMatrix4fv(glGetUniformLocation(self.__geometyPassShader, 'view'), 1, GL_FALSE, view)
        for pos in self.objectPosition:
            model = glm.scale(np.identity(4, np.float32), 0.25, 0.25, 0.25)
            model = glm.translate(model, pos[0], pos[1], pos[2])
            glUniformMatrix4fv(glGetUniformLocation(self.__geometyPassShader, 'model'), 1, GL_FALSE, model)
            self.cyborg.draw(self.__geometyPassShader)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        # 2. Lighting Pass: calculate lighting by iterating over a screen filled quad pixel-by-pixel using the gbuffer's content.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(self.__lightingPassShader)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.gPosition)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.gNormal)
        glActiveTexture(GL_TEXTURE2)
        glBindTexture(GL_TEXTURE_2D, self.gAlbedoSpec)
        # also send light relevent uniforms
        for i in range(len(self.lightPos)):
            glUniform3fv(glGetUniformLocation(self.__lightingPassShader, 'lights[{}].Position'.format(i)), 1, self.lightPos[i])
            glUniform3fv(glGetUniformLocation(self.__lightingPassShader, 'lights[{}].Color'.format(i)), 1, self.lightColors[i])
            # Update attenuation parameters and calculate radius
            _constant = 1.0 # Note that we don't send this to the shader, we assume it is always 1.0 (in our case)
            linear = 0.7
            quadratic = 1.8
            glUniform1f(glGetUniformLocation(self.__lightingPassShader, 'lights[{}].Linear'.format(i)), linear)
            glUniform1f(glGetUniformLocation(self.__lightingPassShader, 'lights[{}].Quadratic'.format(i)), quadratic)
            # Then calculate radius of light volume/sphere
            lightThreshold = 5.0 # 5 # 256
            maxBrightness = max(max(self.lightColors[i][0], self.lightColors[i][1]), self.lightColors[i][2])
            radius = (-linear + math.sqrt(linear * linear - 4 * quadratic * (_constant - (256.0 / lightThreshold) * maxBrightness))) / (2 * quadratic)
            glUniform1f(glGetUniformLocation(self.__lightingPassShader, 'lights[{}].Radius'.format(i)), radius)
        glUniform3fv(glGetUniformLocation(self.__lightingPassShader, 'viewPos'), 1, self.camera.position)
        glUniform1i(glGetUniformLocation(self.__lightingPassShader, 'draw_mode'), self.draw_mode)
        self.renderQuad()

        # 2.5. Copy content of geometry's depth buffer to default framebuffer's depth buffer
        glBindFramebuffer(GL_READ_FRAMEBUFFER, self.gbuffer)
        glBindFramebuffer(GL_DRAW_FRAMEBUFFER, 0) # write to default framebuffer
        glBlitFramebuffer(0, 0, self.width(), self.height(), 0, 0, self.width(), self.height(), GL_DEPTH_BUFFER_BIT, GL_NEAREST)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        # 3. Render lights on top of scene, by blitting
        glUseProgram(self.__lightBoxShader)
        glUniformMatrix4fv(glGetUniformLocation(self.__lightBoxShader, 'projection'), 1, GL_FALSE, projection)
        glUniformMatrix4fv(glGetUniformLocation(self.__lightBoxShader, 'view'), 1, GL_FALSE, view)
        for i in range(len(self.lightPos)):
            model = glm.scale(np.identity(4, np.float32), 0.25, 0.25, 0.25)
            model = glm.translate(model, self.lightPos[i][0], self.lightPos[i][1], self.lightPos[i][2])
            glUniformMatrix4fv(glGetUniformLocation(self.__lightBoxShader, 'model'), 1, GL_FALSE, model)
            glUniform3fv(glGetUniformLocation(self.__lightBoxShader, 'lightColor'), 1, self.lightColors[i])
            self.renderCube()

        glUseProgram(0)

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
        if event.key() == Qt.Key_Z:
            self.wireframe = not self.wireframe
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
