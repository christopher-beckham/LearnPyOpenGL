#!/usr/bin/env python
# -*- coding: utf-8 -*-

from OpenGL.GL import *
from PIL import Image

import pyassimp as assimp
from mesh import Mesh

def textureFromFile(path, gamma):
    textureID = glGenTextures(1)
    im = Image.open(path)
    glBindTexture(GL_TEXTURE_2D, textureID)
    if path.lower().endswith('jpg'):
        iformat = GL_SRGB
        pformat = GL_RGB
    elif path.lower().endswith('png'):
        iformat = GL_SRGB_ALPHA
        pformat = GL_RGBA
    else:
        iformat = GL_RGB
        pformat = GL_RGB
    glTexImage2D(GL_TEXTURE_2D, 0, iformat, im.size[0], im.size[1], 0, pformat, GL_UNSIGNED_BYTE, im.tostring())
    glGenerateMipmap(GL_TEXTURE_2D)
    im.close()
    glBindTexture(GL_TEXTURE_2D, 0)
    return textureID


class Model(object):

    def __init__(self, path, gamma=False):
        self.gammaCorrection = gamma
        self.meshes = []
        self.loadModel(path)

    def draw(self, shader):
        for mesh in self.meshes:
            mesh.draw(shader)

    def loadModel(self, path):
        scene = assimp.load(path, processing=(assimp.postprocess.aiProcess_Triangulate |
                                              assimp.postprocess.aiProcess_FlipUVs |
                                              assimp.postprocess.aiProcess_CalcTangentSpace))
        if not scene:
            raise Exception("ASSIMP can't load model")

        self.__processNode(scene)

    def __processNode(self, scene):
        for mesh in scene.meshes:
            self.meshes.append(Mesh(mesh))