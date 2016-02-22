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
        self.shadows = True

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
        return vertexShader, fragmentShader, geometryShader

    def initializeGL(self):
        # setup some OpenGL options
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)

        _shaders = self.loadShaders('3.2.point_shadows.vs', '3.2.point_shadows.frag')
        self.__shader = glCreateProgram()
        [glAttachShader(self.__shader, s) for s in _shaders if s]
        self.__shader = shaders.ShaderProgram(self.__shader)
        glLinkProgram(self.__shader)
        glUseProgram(self.__shader)
        glUniform1i(glGetUniformLocation(self.__shader, 'diffuseTexture'), 0)
        glUniform1i(glGetUniformLocation(self.__shader, 'depthMap'), 1)
        self.__shader.check_validate()
        self.__shader.check_linked()
        [glDeleteShader(s) for s in _shaders if s]

        vertexShader, fragmentShader, geometryShader = self.loadShaders('3.2.point_shadows_depth.vs', '3.2.point_shadows_depth.frag', '3.2.point_shadows_depth.gs')
        self.__simpleDepthShader = shaders.compileProgram(vertexShader, fragmentShader)

        # light source
        self.lightPos = np.array([0.0, 0.0, 0.0], np.float32)

        # load texture
        self.woodTexture = loadTexture(os.path.join(abPath, '..', '..', 'resources', 'textures', 'wood.png'))

        # Configure depth map FBO
        self.shadowWidth = 1024
        self.shadowHeight = 1024
        self.depthMapFBO = glGenFramebuffers(1)
        # Create depth texture
        self.depthCubeMap = glGenTextures(1)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.depthCubeMap)
        for i in range(6):
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, GL_DEPTH_COMPONENT, self.shadowWidth, self.shadowHeight, 0, GL_DEPTH_COMPONENT, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
        # Attach cubemap as depth map FBO's color buffer
        glBindFramebuffer(GL_FRAMEBUFFER, self.depthMapFBO)
        glFramebufferTexture(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, self.depthCubeMap, 0)
        glDrawBuffer(GL_NONE)
        glReadBuffer(GL_NONE)
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

        # change light position over time
        #self.lightPos[2] = math.cos(currentTime) * 2.0

        # 0. Create depth cubemap transformation matrices
        aspect = float(self.shadowWidth) / self.shadowHeight
        near_plane = 1.0
        far_plane = 25.0
        shadowProj = glm.perspective(90.0, aspect, near_plane, far_plane)
        shadowTransforms = []
        shadowTransforms.append(shadowProj * glm.lookAt(self.lightPos, self.lightPos + np.array([1.0, 0.0, 0.0], np.float32), np.array([0.0, -1.0, 0.0], np.float32)))
        shadowTransforms.append(shadowProj * glm.lookAt(self.lightPos, self.lightPos + np.array([-1.0, 0.0, 0.0], np.float32), np.array([0.0, -1.0, 0.0], np.float32)))
        shadowTransforms.append(shadowProj * glm.lookAt(self.lightPos, self.lightPos + np.array([0.0, 1.0, 0.0], np.float32), np.array([0.0, 0.0, 1.0], np.float32)))
        shadowTransforms.append(shadowProj * glm.lookAt(self.lightPos, self.lightPos + np.array([0.0, -1.0, 0.0], np.float32), np.array([0.0, 0.0, -1.0], np.float32)))
        shadowTransforms.append(shadowProj * glm.lookAt(self.lightPos, self.lightPos + np.array([0.0, 0.0, 1.0], np.float32), np.array([0.0, -1.0, 0.0], np.float32)))
        shadowTransforms.append(shadowProj * glm.lookAt(self.lightPos, self.lightPos + np.array([0.0, 0.0, -1.0], np.float32), np.array([0.0, -1.0, 0.0], np.float32)))
        # shadowTransforms = np.array(shadowTransforms, np.float32)

        # 1. Render scene to depth cubemap
        glViewport(0, 0, self.shadowWidth, self.shadowHeight)
        glBindFramebuffer(GL_FRAMEBUFFER, self.depthMapFBO)
        glClear(GL_DEPTH_BUFFER_BIT)
        glUseProgram(self.__simpleDepthShader)
        for i in range(6):
            glUniformMatrix4fv(glGetUniformLocation(self.__simpleDepthShader, 'shadowTransforms[{}]'.format(i)), 1, GL_FALSE, shadowTransforms[i])
        glUniform1f(glGetUniformLocation(self.__simpleDepthShader, 'far_plane'), far_plane)
        glUniform3fv(glGetUniformLocation(self.__simpleDepthShader, 'lightPos'), 1, self.lightPos)
        self.renderScene(self.__simpleDepthShader)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        # 2. render scene as normal
        glViewport(0, 0, self.width(), self.height())
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(self.__shader)
        projection = glm.perspective(self.camera.zoom, float(self.width())/self.height(), 0.1, 100.0)
        view = self.camera.viewMatrix
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'projection'), 1, GL_FALSE, projection)
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'view'), 1, GL_FALSE, view)
        # set light uniforms
        glUniform3fv(glGetUniformLocation(self.__shader, 'lightPos'), 1, self.lightPos)
        glUniform3fv(glGetUniformLocation(self.__shader, 'viewPos'), 1, self.camera.position)
        # Enable/Disable shadows by pressing 'SPACE'
        glUniform1i(glGetUniformLocation(self.__shader, 'shadows'), self.shadows)
        glUniform1f(glGetUniformLocation(self.__shader, 'far_plane'), far_plane)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.woodTexture)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.depthCubeMap)
        self.renderScene(self.__shader)

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
        if event.key() == Qt.Key_Space:
            self.shadows = not self.shadows

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
