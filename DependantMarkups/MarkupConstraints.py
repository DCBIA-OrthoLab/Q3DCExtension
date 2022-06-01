import abc
import collections
import contextlib
import json
import unittest
import weakref

from copy import deepcopy
from typing import Union, Tuple, List, Optional, Any, Dict

import numpy as np
import numpy.testing as npt

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

    def setLocked(self, locked):
        self.node.SetNthControlPointLocked(self.idx, locked)

    @classmethod
    def new(cls, node: "vtkMRMLMarkupsNode", pos=None):
        if pos is None:
            pos = vtk.vtkVector3d()
        elif not isinstance(pos, vtk.vtkVector3d):
            pos = vtk.vtkVector3d(pos)

        idx = node.AddControlPoint(pos or vtk.vtkVector3d())
        id_ = node.GetNthControlPointID(idx)
        return cls(node, id_)


class MarkupConstraintsLogic(
    ScriptedLoadableModuleLogic,
    VTKSuppressibleObservationMixin,
):
    CONSTRAINTS = {}

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        VTKSuppressibleObservationMixin.__init__(self)

        self._constraints = {}
        self._dependencies = weakref.WeakKeyDictionary()
        self._cached = weakref.WeakKeyDictionary()

    def _updateDependencies(self):
        self._dependencies.clear()

        for tgt, (kind, deps) in self._constraints.items():
            for dep in deps + [tgt]:
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

            unchanged = all(
                dep in self._cached and np.allclose(dep.position, self._cached[dep])
                for dep in deps + [tgt]
            )

            for dep in deps + [tgt]:
                self._cached[dep] = dep.position

            if not unchanged:
                self.CONSTRAINTS[kind](tgt, deps)

    def delConstraint(
        self,
        tgt: ControlPoint,
    ):
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
def update_tgt(tgt: ControlPoint, deps: List[ControlPoint]):
    """Set tgt position to the mean of deps positions"""

    pos = vtk.vtkVector3d()
    for dep in deps:
        vtk.vtkMath.Add(pos, dep.position, pos)
    vtk.vtkMath.MultiplyScalar(pos, 1 / len(deps))

    tgt.position = pos


@MarkupConstraintsLogic.register("lock")
def update_tgt(tgt: ControlPoint, deps: List[ControlPoint]):
    """Set tgt position to match dep position"""

    (dep,) = deps

    tgt.position = dep.position


@MarkupConstraintsLogic.register("project")
def update_tgt(tgt: ControlPoint, deps: List[ControlPoint]):
    """Set tgt position to lie on line defined by deps."""

    root, axis = deps
    root = root.position
    axis = axis.position
    pos = tgt.position

    vtk.vtkMath.Subtract(axis, root, axis)
    vtk.vtkMath.Subtract(pos, root, pos)

    t = vtk.vtkMath.Dot(pos, axis) / vtk.vtkMath.Dot(axis, axis)

    # t = np.clip(t, 0, 1)

    vtk.vtkMath.MultiplyScalar(axis, t)
    vtk.vtkMath.Add(axis, root, axis)
    tgt.position = axis


class MarkupConstraintsTest(
    ScriptedLoadableModuleTest,
    unittest.TestCase,
):
    def runTest(self):
        slicer.mrmlScene.Clear()

        logic = MarkupConstraintsLogic()
        # todo assert logic.constraints is empty

        # constraints within a node
        node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")

        a = ControlPoint.new(node, [1, 2, 3])
        b = ControlPoint.new(node, [2, 3, 4])
        t = ControlPoint.new(node, [3, 4, 5])

        np.testing.assert_almost_equal(
            t.position,
            [3, 4, 5],
            err_msg="ControlPoint.position invalid",
        )

        # midpoint within node
        logic.setConstraint(t, [a, b], "midpoint")
        np.testing.assert_almost_equal(
            t.position,
            [1.5, 2.5, 3.5],
            err_msg="initial midpoint (intra) invalid",
        )
        a.position = [0, 1, 2]
        np.testing.assert_almost_equal(
            t.position,
            [1, 2, 3],
            err_msg="midpoint update (intra) invalid",
        )

        # lock within node
        logic.setConstraint(t, [a], "lock")
        np.testing.assert_almost_equal(
            t.position,
            [0, 1, 2],
            err_msg="initial lock (intra) invalid",
        )
        a.position = [1, 2, 3]
        np.testing.assert_almost_equal(
            t.position,
            [1, 2, 3],
            err_msg="lock update (intra) invalid",
        )

        # project within node
        logic.setConstraint(t, [a, b], "project")
        np.testing.assert_almost_equal(
            t.position,
            [0, 1, 2],
            err_msg="initial project (intra) invalid",
        )
        a.position = [0, 0, 0]
        b.position = [5, -5, 5]
        t.position = [1, 1, 1]
        np.testing.assert_almost_equal(
            t.position,
            [0.3333333, -0.3333333, 0.3333333],
            err_msg="project update (intra) invalid",
        )

        # remove constraint
        logic.delConstraint(t)
        a.position = [0, 0, 0]
        b.position = [0, 0, 0]
        np.testing.assert_almost_equal(
            t.position,
            [0.3333333, -0.3333333, 0.3333333],
            err_msg="initial delConstraint (intra) invalid",
        )
        t.position = [1, 1, 1]
        np.testing.assert_almost_equal(
            t.position,
            [1, 1, 1],
            err_msg="delConstraint (intra) invalid",
        )

        slicer.mrmlScene.RemoveNode(node)
        del node, a, b, t  # todo fix memory leaks
        # todo assert logic.constraints is empty

        # constraints between nodes
        srcNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        tgtNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")

        a = ControlPoint.new(srcNode, [1, 2, 3])
        b = ControlPoint.new(srcNode, [2, 3, 4])
        t = ControlPoint.new(tgtNode, [3, 4, 5])

        np.testing.assert_almost_equal(
            t.position,
            [3, 4, 5],
            err_msg="ControlPoint.position invalid",
        )

        # midpoint between nodes
        logic.setConstraint(t, [a, b], "midpoint")
        np.testing.assert_almost_equal(
            t.position,
            [1.5, 2.5, 3.5],
            err_msg="initial midpoint (inter) invalid",
        )
        a.position = [0, 1, 2]
        np.testing.assert_almost_equal(
            t.position,
            [1, 2, 3],
            err_msg="midpoint update (inter) invalid",
        )

        # lock between nodes
        logic.setConstraint(t, [a], "lock")
        np.testing.assert_almost_equal(
            t.position,
            [0, 1, 2],
            err_msg="initial lock (inter) invalid",
        )
        a.position = [1, 2, 3]
        np.testing.assert_almost_equal(
            t.position,
            [1, 2, 3],
            err_msg="lock update (inter) invalid",
        )

        # project between nodes
        logic.setConstraint(t, [a, b], "project")
        np.testing.assert_almost_equal(
            t.position,
            [0, 1, 2],
            err_msg="initial project (inter) invalid",
        )
        a.position = [0, 0, 0]
        b.position = [5, -5, 5]
        t.position = [1, 1, 1]
        np.testing.assert_almost_equal(
            t.position,
            [0.3333333, -0.3333333, 0.3333333],
            err_msg="project update (inter) invalid",
        )

        # remove constraint
        logic.delConstraint(t)
        a.position = [0, 0, 0]
        b.position = [0, 0, 0]
        np.testing.assert_almost_equal(
            t.position,
            [0.3333333, -0.3333333, 0.3333333],
            err_msg="initial delConstraint (inter) invalid",
        )
        t.position = [1, 1, 1]
        np.testing.assert_almost_equal(
            t.position,
            [1, 1, 1],
            err_msg="delConstraint (inter) invalid",
        )

        slicer.mrmlScene.RemoveNode(srcNode)
        slicer.mrmlScene.RemoveNode(tgtNode)
        del srcNode, tgtNode, a, b, t
        # todo assert logic.constraints is empty

        # todo failing tests
        # chained dependency
        node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        a = ControlPoint.new(node, [0, 1, 2])
        b = ControlPoint.new(node, [-1, -2, 3])
        r = ControlPoint.new(node, [0, 0, 0])
        u = ControlPoint.new(node)
        v = ControlPoint.new(node)

        logic.setConstraint(u, [a, b], "midpoint")
        logic.setConstraint(v, [r, u], "midpoint")

        np.testing.assert_almost_equal(
            u.position,
            [-0.5, -0.5, 2.5],
            err_msg="initial chained midpoint u invalid",
        )
        np.testing.assert_almost_equal(
            v.position,
            [-0.25, -0.25, 1.25],
            err_msg="initial chained midpoint v invalid",
        )

        a.position = [1, 1, 2]

        np.testing.assert_almost_equal(
            u.position,
            [0, -0.5, 2.5],
            err_msg="update (a) chained midpoint u",
        )
        np.testing.assert_almost_equal(
            v.position,
            [0, -0.25, 1.25],
            err_msg="update (a) chained midpoint v",
        )

        r.position = [0, 1, 0]

        np.testing.assert_almost_equal(
            u.position,
            [0, -0.5, 2.5],
            err_msg="update (r) chained midpoint u",
        )
        np.testing.assert_almost_equal(
            v.position,
            [0, 0.25, 1.25],
            err_msg="update (r) chained midpoint v",
        )

        slicer.mrmlScene.RemoveNode(node)
        del node, a, b, r, u, v
        # todo assert logic.constraints is empty

        # todo constrain to model
