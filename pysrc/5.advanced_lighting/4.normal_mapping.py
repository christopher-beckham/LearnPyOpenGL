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
        self.startTimer(5)

        self.camera = camera.Camera(0.0, 0.0, 3.0)
        self.__lastX = 400
        self.__lastY = 300
        self.__firstMouse = True

        self.__deltaTime = 0.0
        self.__lastTime = 0.0

        self.quadVAO = 0

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
        return vertexShader, fragmentShader

    def initializeGL(self):
        # setup some OpenGL options
        glEnable(GL_DEPTH_TEST)

        _shaders = self.loadShaders('4.normal_mapping.vs', '4.normal_mapping.frag')
        self.__shader = glCreateProgram()
        [glAttachShader(self.__shader, s) for s in _shaders if s]
        self.__shader = shaders.ShaderProgram(self.__shader)
        glLinkProgram(self.__shader)
        glUseProgram(self.__shader)
        glUniform1i(glGetUniformLocation(self.__shader, 'diffuseMap'), 0)
        glUniform1i(glGetUniformLocation(self.__shader, 'normalMap'), 1)
        self.__shader.check_validate()
        self.__shader.check_linked()
        [glDeleteShader(s) for s in _shaders if s]

        # light source
        self.lightPos = np.array([0.5, 1.0, 0.3], np.float32)

        # load texture
        self.diffuseMap = loadTexture(os.path.join(abPath, '..', '..', 'resources', 'textures', 'brickwall.jpg'))
        self.normalMap = loadTexture(os.path.join(abPath, '..', '..', 'resources', 'textures', 'brickwall.jpg'))

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

    def paintGL(self):
        currentTime = self.__timer.elapsed() / 1000.0
        self.__deltaTime = currentTime - self.__lastTime
        self.__lastTime = currentTime

        # clear the colorbuffer
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # configure view/projection matrices
        glUseProgram(self.__shader)
        view = self.camera.viewMatrix
        projection = glm.perspective(self.camera.zoom, float(self.width())/self.height(), 0.1, 100.0)
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'view'), 1, GL_FALSE, view)
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'projection'), 1, GL_FALSE, projection)
        # render normal-mapped quad
        rotVec = glm.normalize(np.array([1.0, 0.0, 1.0], np.float32))
        model = glm.rotate(np.identity(4, np.float32), currentTime * -10.0, rotVec[0], rotVec[1], rotVec[2])
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'model'), 1, GL_FALSE, model)
        glUniform3fv(glGetUniformLocation(self.__shader, 'lightPos'), 1, self.lightPos)
        glUniform3fv(glGetUniformLocation(self.__shader, 'viewPos'), 1, self.camera.position)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.diffuseMap)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.normalMap)
        self.renderQuad()

        # render light source (simply re-renders a smaller plane at the light's position for debugging/visualization)
        model = glm.scale(np.identity(4, np.float32), 0.1, 0.1, 0.1)
        model = glm.translate(model, self.lightPos[0], self.lightPos[1], self.lightPos[2])
        glUniformMatrix4fv(glGetUniformLocation(self.__shader, 'model'), 1, GL_FALSE, model)
        self.renderQuad()

        glUseProgram(0)

    def renderQuad(self):
        if self.quadVAO == 0:
            # positions
            pos1 = np.array((-1.0, 1.0, 0.0), np.float32)
            pos2 = np.array((-1.0, -1.0, 0.0), np.float32)
            pos3 = np.array((1.0, -1.0, 0.0), np.float32)
            pos4 = np.array((1.0, 1.0, 0.0), np.float32)
            # texture coordinates
            uv1 = np.array((0.0, 1.0), np.float32)
            uv2 = np.array((0.0, 0.0), np.float32)
            uv3 = np.array((1.0, 0.0), np.float32)
            uv4 = np.array((1.0, 1.0), np.float32)
            # normal vector
            nm = np.array((0.0, 0.0, 1.0), np.float32)

            # calculate tangent/bitangent vectors of both triangles
            # triangle 1
            edge1 = pos2 - pos1
            edge2 = pos3 - pos1
            deltaUV1 = uv2 - uv1
            deltaUV2 = uv3 - uv1

            f = 1.0 / (deltaUV1[0] * deltaUV2[1] - deltaUV2[0] * deltaUV1[1])

            tangent1 = np.array([
                f * (deltaUV2[1] * edge1[0] - deltaUV1[1] * edge2[0]),
                f * (deltaUV2[1] * edge1[1] - deltaUV1[1] * edge2[1]),
                f * (deltaUV2[1] * edge1[2] - deltaUV1[1] * edge2[2])
            ], np.float32)
            tangent1 = glm.normalize(tangent1)

            bitangent1 = np.array([
                f * (-deltaUV2[0] * edge1[0] + deltaUV1[0] * edge2[0]),
                f * (-deltaUV2[0] * edge1[1] + deltaUV1[0] * edge2[1]),
                f * (-deltaUV2[0] * edge1[2] + deltaUV1[0] * edge2[2])
            ], np.float32)
            bitangent1 = glm.normalize(bitangent1)

            # triangle 2
            edge1 = pos3 - pos1
            edge2 = pos4 - pos1
            deltaUV1 = uv3 - uv1
            deltaUV2 = uv4 - uv1

            f = 1.0 / (deltaUV1[0] * deltaUV2[1] - deltaUV2[0] * deltaUV1[1])

            tangent2 = np.array([
                f * (deltaUV2[1] * edge1[0] - deltaUV1[1] * edge2[0]),
                f * (deltaUV2[1] * edge1[1] - deltaUV1[1] * edge2[1]),
                f * (deltaUV2[1] * edge1[2] - deltaUV1[1] * edge2[2])
            ], np.float32)
            tangent2 = glm.normalize(tangent2)

            bitangent2 = np.array([
                f * (-deltaUV2[0] * edge1[0] + deltaUV1[0] * edge2[0]),
                f * (-deltaUV2[0] * edge1[1] + deltaUV1[0] * edge2[1]),
                f * (-deltaUV2[0] * edge1[2] + deltaUV1[0] * edge2[2])
            ], np.float32)
            bitangent2 = glm.normalize(bitangent2)

            quadVertices = np.hstack([
                # positions, normal, texture coords, tangent, bittangent
                pos1, nm, uv1, tangent1, bitangent1,
                pos2, nm, uv2, tangent1, bitangent1,
                pos3, nm, uv3, tangent1, bitangent1,

                pos1, nm, uv1, tangent2, bitangent2,
                pos3, nm, uv3, tangent2, bitangent2,
                pos4, nm, uv4, tangent2, bitangent2,
            ])

            # setup plane VAO
            self.quadVAO = glGenVertexArrays(1)
            quadVBO = glGenBuffers(1)
            glBindVertexArray(self.quadVAO)
            glBindBuffer(GL_ARRAY_BUFFER, quadVBO)
            glBufferData(GL_ARRAY_BUFFER, quadVertices.nbytes, quadVertices, GL_STATIC_DRAW)
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 14 * quadVertices.itemsize, None)
            glEnableVertexAttribArray(1)
            glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 14 * quadVertices.itemsize, ctypes.c_void_p(3 * quadVertices.itemsize))
            glEnableVertexAttribArray(2)
            glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 14 * quadVertices.itemsize, ctypes.c_void_p(6 * quadVertices.itemsize))
            glEnableVertexAttribArray(3)
            glVertexAttribPointer(3, 3, GL_FLOAT, GL_FALSE, 14 * quadVertices.itemsize, ctypes.c_void_p(8 * quadVertices.itemsize))
            glEnableVertexAttribArray(4)
            glVertexAttribPointer(4, 3, GL_FLOAT, GL_FALSE, 14 * quadVertices.itemsize, ctypes.c_void_p(11 * quadVertices.itemsize))

        glBindVertexArray(self.quadVAO)
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

    def timerEvent(self, event):
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
