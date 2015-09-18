#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ctypes

from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtOpenGL import *
from OpenGL.GL import *
from OpenGL.GL import shaders
import cffi

ffi = cffi.FFI()

def cffiToCtypeArray(cdata, type):
    carray = type * len(cdata)
    return carray.from_buffer(ffi.buffer(cdata))

vertexShaderSource = """#version 330 core
layout (location = 0) in vec3 position;
void main()
{
    gl_Position = vec4(position.x, position.y, position.z, 1.0);
}"""

fragmentShaderSource = """#version 330 core
out vec4 color;
void main()
{
    color = vec4(1.0f, 0.5f, 0.2f, 1.0f);
}"""

class GLWindow(QGLWidget):

    def __init__(self, gl_format=None):
        if gl_format is None:
            # using opengl 3.3 core profile
            gformat = QGLFormat()
            gformat.setVersion(3, 3)
            gformat.setProfile(QGLFormat.CoreProfile)
        super(GLWindow, self).__init__(gformat)
    
    def initializeGL(self):
        vertexShader = shaders.compileShader(vertexShaderSource, GL_VERTEX_SHADER)
        fragmentShader = shaders.compileShader(fragmentShaderSource, GL_FRAGMENT_SHADER)
        self.__shaderProgram = shaders.compileProgram(vertexShader, fragmentShader)

        vertices = ffi.new("float[]", 
                           [0.5, 0.5, 0.0,
                            0.5, -0.5, 0.0,
                            -0.5, -0.5, 0.0,
                            -0.5, 0.5, 0.0])
        indices = ffi.new("unsigned int[]", 
                          [0, 1, 3, 1, 2, 3])

        self.__vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        ebo = glGenBuffers(1)

        glBindVertexArray(self.__vao)

        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, ffi.sizeof(vertices), cffiToCtypeArray(vertices, ctypes.c_float), GL_STATIC_DRAW)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, ffi.sizeof(indices), cffiToCtypeArray(indices, ctypes.c_uint), GL_STATIC_DRAW)

        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * ffi.sizeof("float"), None)
        glEnableVertexAttribArray(0)

        glBindBuffer(GL_ARRAY_BUFFER, 0)

        glBindVertexArray(0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

    def paintGL(self):
        # Render
        # Clear the colorbuffer
        glClearColor(0.2, 0.3, 0.3, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

        glUseProgram(self.__shaderProgram)
        glBindVertexArray(self.__vao)
        #glDrawArrays(GL_TRIANGLES, 0, 6)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            qApp.quit()
        return super(GLWindow, self).keyPressEvent(event)


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)

    glWindow = GLWindow()
    glWindow.setFixedSize(800, 600)
    glWindow.setWindowTitle('LearnPyOpenGL')
    glWindow.show()

    sys.exit(app.exec_())






