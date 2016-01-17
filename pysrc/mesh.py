#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path

import numpy as np
from PIL import Image
from OpenGL.GL import *

TextureType = {'texture_diffuse' : 1,
               'texture_specular' : 2,
               'texture_normal' : 5,
               'texture_height' : 3}

def textureFromFile(path, gamma=False):
    textureID = glGenTextures(1)
    im = Image.open(path)
    iformat = GL_RGB
    pformat = GL_RGB
    if im.mode == 'RGBA':
        if gamma:
            iformat = GL_SRGB_ALPHA
        else:
            iformat = GL_RGBA
        pformat = GL_RGBA
    glBindTexture(GL_TEXTURE_2D, textureID)
    glTexImage2D(GL_TEXTURE_2D, 0, iformat, im.size[0], im.size[1], 0, pformat, GL_UNSIGNED_BYTE, im.tobytes())
    glGenerateMipmap(GL_TEXTURE_2D)

    # parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    im.close()
    glBindTexture(GL_TEXTURE_2D, 0)
    return textureID

class Texture(object):
    __slots__ = ['id', 'type', 'path']

    def __init__(self, id, type, path):
        self.id = id
        self.type = type
        self.path = path


class Mesh(object):

    def __init__(self, asset, assetDir):
        self.asset = asset
        self.assetDir = assetDir
        self.textures = []
        self.vao = None

        self.__setupMesh()
        self.__loadTextures()

    def draw(self, shader):
        textureNr = {}.fromkeys(TextureType.keys(), 1)
        for texture in self.textures:
            index = self.textures.index(texture)
            # Active proper texture unit before binding
            glActiveTexture(GL_TEXTURE0 + index)
            name = texture.type
            if texture.type in TextureType:
                name += str(textureNr[texture.type])
                textureNr[texture.type] += 1

            glUniform1i(glGetUniformLocation(shader, name), index)
            glBindTexture(GL_TEXTURE_2D, texture.id)

        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.asset.faces.size, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

        for texture in self.textures:
            glActiveTexture(GL_TEXTURE0 + self.textures.index(texture))
            glBindTexture(GL_TEXTURE_2D, 0)

    def __setupMesh(self):
        self.vao = glGenVertexArrays(1)
        vbo, ebo, nbo, tcbo, tbo, bbo = glGenBuffers(6)

        glBindVertexArray(self.vao)
        # vertex position
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, self.asset.vertices.nbytes, self.asset.vertices, GL_STATIC_DRAW)
        # set vertex attribute pointers
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

        # vertex normal
        glBindBuffer(GL_ARRAY_BUFFER, nbo)
        glBufferData(GL_ARRAY_BUFFER, self.asset.normals.nbytes, self.asset.normals, GL_STATIC_DRAW)
        # set normal attribute pointers
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, None)

        # vertex texture coords
        texCoords = np.compress([True, True, False], self.asset.texturecoords[0], axis=1)
        glBindBuffer(GL_ARRAY_BUFFER, tcbo)
        glBufferData(GL_ARRAY_BUFFER, texCoords.nbytes, texCoords, GL_STATIC_DRAW)
        # set texture coords attribute pointers
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 0, None)

        # vertex tangent
        glBindBuffer(GL_ARRAY_BUFFER, tbo)
        glBufferData(GL_ARRAY_BUFFER, self.asset.tangents.nbytes, self.asset.tangents, GL_STATIC_DRAW)
        # set tangent attribute pointers
        glEnableVertexAttribArray(3)
        glVertexAttribPointer(3, 3, GL_FLOAT, GL_FALSE, 0, None)

        # vertex bitangent
        glBindBuffer(GL_ARRAY_BUFFER, bbo)
        glBufferData(GL_ARRAY_BUFFER, self.asset.bitangents.nbytes, self.asset.bitangents, GL_STATIC_DRAW)
        # set bitangent attribute pointers
        glEnableVertexAttribArray(4)
        glVertexAttribPointer(4, 3, GL_FLOAT, GL_FALSE, 0, None)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.asset.faces.nbytes, self.asset.faces, GL_STATIC_DRAW)

        glBindVertexArray(0)

    def __loadTextures(self):
        for i in TextureType:
            key = ('file', TextureType[i])
            if not self.asset.material.properties.has_key(key):
                continue

            textureName = self.asset.material.properties[key]
            texturePath = os.path.join(self.assetDir, textureName)
            if not os.path.exists(texturePath): continue
            textureId = textureFromFile(texturePath)

            texture = Texture(textureId, i, texturePath)
            self.textures.append(texture)
