#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ctypes

import numpy as np
from OpenGL.GL import *

class Texture(object):
    __slots__ = ['id', 'type', 'path']

    def __init__(self, id, type, path):
        self.id = id
        self.type = type
        self.path = path


class Mesh(object):

    def __init__(self, asset, textures):
        self.asset = asset
        self.textures = textures
        self.vao = None

        self.__setupMesh()

    def draw(self, shader):
        for texture in self.textures:
            index = self.textures.index(texture)
            name = texture.type
            if texture.type in ('texture_diffuse', 'texture_specular', 'texture_normal', 'texture_height'):
                name += str(index+1)

            glUniform1i(glGetUniformLocation(shader, name), index)
            glBindTexture(GL_TEXTURE_2D, texture.id)

        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, len(self.asset.faces), GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

        for texture in self.textures:
            glActiveTexture(GL_TEXTURE0 + self.textures.index(texture))
            glBindTexture(GL_TEXTURE_2D, 0)

    def __setupMesh(self):
        self.vao = glGenVertexArrays(1)
        vbo, ebo, nbo, tcbo, tbo, bbo = glGenBuffers(6)

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, self.asset.vertices.nbytes, self.asset.vertices, GL_STATIC_DRAW)

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, self.asset.vertices.itemsize, None)

        glBindBuffer(GL_ARRAY_BUFFER, nbo)
        glBufferData(GL_ARRAY_BUFFER, self.asset.normals.nbytes, self.asset.normals, GL_STATIC_DRAW)

        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, self.asset.normals.itemsize, None)

        glBindBuffer(GL_ARRAY_BUFFER, tcbo)
        glBufferData(GL_ARRAY_BUFFER, self.asset.textureCoords.nbytes, self.asset.textureCoords, GL_STATIC_DRAW)

        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, self.asset.textureCoords.itemsize, None)

        glBindBuffer(GL_ARRAY_BUFFER, tbo)
        glBufferData(GL_ARRAY_BUFFER, self.asset.tangents.nbytes, self.asset.tangents, GL_STATIC_DRAW)

        glEnableVertexAttribArray(3)
        glVertexAttribPointer(3, 3, GL_FLOAT, GL_FALSE, self.asset.tangents.itemsize, None)

        glBindBuffer(GL_ARRAY_BUFFER, bbo)
        glBufferData(GL_ARRAY_BUFFER, self.asset.bitangents.nbytes, self.asset.bitangents, GL_STATIC_DRAW)

        glEnableVertexAttribArray(1)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, self.asset.bitangents.itemsize, None)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.asset.faces.nbytes, self.asset.faces, GL_STATIC_DRAW)


