#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path

from OpenGL.GL import *

import pyassimp as assimp
from mesh import Mesh


class Model(object):

    def __init__(self, path, gamma=False):
        self.gammaCorrection = gamma
        self.meshes = []
        self.textures_loaded = []
        self.directory = ''

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

        self.directory = os.path.dirname(path)

        for mesh in scene.meshes:
            self.meshes.append(Mesh(mesh, self.directory))

        assimp.release(scene)

    #     self.__processNode(scene)
    #
    # def __processNode(self, scene):
    #     for mesh in scene.meshes:
    #         self.meshes.append(Mesh(mesh))
    #
    #     assimp.release(scene)