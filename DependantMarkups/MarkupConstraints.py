import abc
import collections
import contextlib
import json
import unittest
import weakref

from copy import deepcopy
from typing import Union, Tuple, List, Optional, Any

import numpy as np

import slicer
import vtk

from slicer.ScriptedLoadableModule import ScriptedLoadableModule
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleWidget
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleTest

from slicer.util import VTKObservationMixin
from slicer.util import NodeModify

try:
    import networkx as nx
except ModuleNotFoundError:
    slicer.util.pip_install("networkx")
    import networkx as nx


class MarkupConstraints(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)

        parent.title = "Markup Constraints"
        parent.categories = ["Developer Tools"]
        parent.dependencies = []
        parent.contributors = [
            "David Allemang (Kitawre Inc.)",
        ]
        parent.helpText = """
        Markup Constraints is a collection of utilities to constrain the
        positions of markup control points based on the positions of other
        control points or models in the scene.
        """
        parent.acknowledgementText = """
        This work was supported by the National Institute of Dental and
        Craniofacial Research and the National Institute of Biomedical
        Imaging and Bioengineering of the National Institutes of Health.
        """
        self.parent = parent


class MarkupConstraintsWidget(ScriptedLoadableModuleWidget):
    pass


from DependantMarkups import VTKSuppressibleObservationMixin


class ControlPoint:
    def __init__(self, node: "vtkMRMLMarkupsNode", id_: str):
        self.node = node
        self.id = id_

    @property
    def idx(self):
        return self.node.GetNthControlPointIndexByID(self.id)

    @property
    def position(self):
        return self.node.GetNthControlPointPositionVector(self.idx)

    @position.setter
    def position(self, pos):
        self.node.SetNthControlPointPositionFromArray(self.idx, pos)


class MarkupConstraintsLogic(
    ScriptedLoadableModuleLogic,
    VTKSuppressibleObservationMixin,
):
    CONSTRAINTS = {}

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        VTKSuppressibleObservationMixin.__init__(self)

        self._constraints = {}
        self._dependencies = {}

    def _updateDependencies(self):
        self._dependencies.clear()

        for tgt, (kind, deps) in self._constraints.items():
            for dep in deps:
                if dep not in self._dependencies:
                    self._dependencies[dep.node] = set()
                self._dependencies[dep.node].add(tgt)

        events = (
            slicer.vtkMRMLMarkupsNode.PointAddedEvent,
            slicer.vtkMRMLMarkupsNode.PointModifiedEvent,
            slicer.vtkMRMLMarkupsNode.PointRemovedEvent,
        )

        self.removeObservers()

        for node in self._dependencies:
            for event in events:
                self.addObserver(
                    node,
                    event,
                    self.onNodeModify,
                    priority=100.0,
                )

    @classmethod
    def register(cls, kind):
        def decorator(func):
            cls.CONSTRAINTS[kind] = func
            return func

        return decorator

    def onNodeModify(self, node, event):
        for tgt in self._dependencies[node]:
            kind, deps = self._constraints[tgt]
            self.CONSTRAINTS[kind](tgt, deps)

    def delConstraint(self, tgt: ControlPoint):
        del self._constraints[tgt]
        self._updateDependencies()

    def setConstraint(
        self,
        tgt: ControlPoint,
        deps: List[ControlPoint],
        kind: str,
    ):
        self._constraints[tgt] = (kind, deps)
        self._updateDependencies()
        self.CONSTRAINTS[kind](tgt, deps)


@MarkupConstraintsLogic.register("midpoint")
def update_midpoint(tgt: ControlPoint, deps: List[ControlPoint]):
    """Set tgt position to the mean of deps positions"""

    pos = vtk.vtkVector3d()

    for dep in deps:
        vtk.vtkMath.Add(pos, dep.position, pos)

    vtk.vtkMath.MultiplyScalar(pos, 1 / len(deps))

    tgt.position = pos


def new_control_point(node, pos=None):
    if pos is None:
        pos = vtk.vtkVector3d()
    elif not isinstance(pos, vtk.vtkVector3d):
        pos = vtk.vtkVector3d(pos)

    idx = node.AddControlPoint(pos or vtk.vtkVector3d())
    id_ = node.GetNthControlPointID(idx)
    return ControlPoint(node, id_)


class MarkupConstraintsTest(
    ScriptedLoadableModuleTest,
    unittest.TestCase,
):
    # def assertVector3dAlmostEqual(self, first, second, places=..., ):
    #     self.assertAlmostEqual()

    def runTest(self):
        slicer.mrmlScene.Clear()

        self.delayDisplay("Testing constraints creation.")

        src = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        tgt = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")

        logic = MarkupConstraintsLogic()

        srca = new_control_point(src, [1, 4, 3])
        srcb = new_control_point(src, [-1, -3, -2])

        mid = new_control_point(tgt)

        logic.setConstraint(mid, [srca, srcb], "midpoint")

        self.delayDisplay(f"mid: {mid.position}")
        print(srca.position, srcb.position, mid.position)

        srca.position = [11, 4, 3]

        self.delayDisplay(f"mid: {mid.position}")
        print(srca.position, srcb.position, mid.position)

        # logic.delConstraint(mid)
        #
        # srca.position = 0, 0, 0
        # self.delayDisplay(f"mid: {mid.position}")
        # print(srca.position, srcb.position, mid.position)
