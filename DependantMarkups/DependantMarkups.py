from __future__ import print_function

import contextlib
import json
from copy import deepcopy

import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.util import NodeModify

import numpy as np

import vtk


class DependantMarkups(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Dependent Markups"
        parent.categories = ["Developer Tools"]
        parent.dependencies = []
        parent.contributors = [
            'David Allemang (Kitware Inc.)',
        ]
        parent.helpText = """
        Dependent Markups is a collection of utilities to manage markups that 
        depend on the status of other markups or models in the scene.
        """
        parent.acknowledgementText = """
        This work was supported by the National Institute of Dental and
        Craniofacial Research and the National Institute of Biomedical
        Imaging and Bioengineering of the National Institutes of Health.
        """
        self.parent = parent


class VTKSuppressibleObservationMixin(VTKObservationMixin):
    @contextlib.contextmanager
    def suppress(self, obj=..., event=..., method=...):
        suppressed = []
        for o, e, m, g, t, p in self.Observations:
            if obj is not ... and obj != o: continue
            if event is not ... and event != e: continue
            if method is not ... and method != m: continue

            o.RemoveObserver(t)
            self.Observations.remove([o, e, m, g, t, p])
            suppressed.append([o, e, m, g, t, p])

        yield

        for o, e, m, g, _, p in suppressed:
            t = o.AddObserver(e, m, p)
            self.Observations.append([o, e, m, g, t, p])


class DependantMarkupsLogic(
    ScriptedLoadableModuleLogic,
    VTKSuppressibleObservationMixin
):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        VTKSuppressibleObservationMixin.__init__(self)

        self.default_projected = True

    def default(self):
        return {
            'midPoint': {
                'definedByThisMarkup': [],
                'isMidPoint': False,
                'Point1': None,
                'Point2': None,
            },
            'projection': {
                'isProjected': self.default_projected,
                'closestPointIndex': None
            },
        }

        # todo roi radius

    #     planeDescription = dict()
    #     landmarks.SetAttribute("planeDescription", self.encodeJSON(planeDescription))
    #     landmarks.SetAttribute("isClean", self.encodeJSON({"isClean": False}))
    #     landmarks.SetAttribute("lastTransformID", None)
    #     landmarks.SetAttribute("arrayName", model.GetName() + "_ROI")

    def getClosestPointIndex(self, fidNode, inputPolyData, landmarkID):
        landmarkCoord = np.zeros(3)
        landmarkCoord[1] = 42
        fidNode.GetNthFiducialPosition(landmarkID, landmarkCoord)
        pointLocator = vtk.vtkPointLocator()
        pointLocator.SetDataSet(inputPolyData)
        pointLocator.AutomaticOn()
        pointLocator.BuildLocator()
        indexClosestPoint = pointLocator.FindClosestPoint(landmarkCoord)
        return indexClosestPoint

    def replaceLandmark(self, inputModelPolyData, fidNode, landmarkID,
                        indexClosestPoint):
        landmarkCoord = [-1, -1, -1]
        inputModelPolyData.GetPoints().GetPoint(indexClosestPoint, landmarkCoord)
        fidNode.SetNthControlPointPositionFromArray(
            landmarkID, landmarkCoord,
            slicer.vtkMRMLMarkupsNode.PositionPreview,
        )

    def projectOnSurface(self, modelOnProject, fidNode, selectedFidReflID):
        if selectedFidReflID:
            markupsIndex = fidNode.GetNthControlPointIndexByID(selectedFidReflID)
            indexClosestPoint = self.getClosestPointIndex(fidNode,
                                                          modelOnProject.GetPolyData(),
                                                          markupsIndex)
            self.replaceLandmark(modelOnProject.GetPolyData(), fidNode, markupsIndex,
                                 indexClosestPoint)
            return indexClosestPoint

    def getModel(self, node):
        return node.GetNodeReference('MODEL')

    def computeProjection(self, node, ID):
        model = self.getModel(node)
        if not model: return

        self.projectOnSurface(model, node, ID)

    def connect(self, node, model):
        self.addObserver(node, node.PointAddedEvent, self.onPointsChanged, priority=100.0)
        self.addObserver(node, node.PointModifiedEvent, self.onPointsChanged, priority=100.0)
        self.addObserver(node, node.PointRemovedEvent, self.onPointsChanged, priority=100.0)

        node.AddNodeReferenceID('MODEL', model.GetID())

    def getData(self, node):
        text = node.GetAttribute('descriptions')
        if not text:
            return {}
        return json.loads(text)

    def setData(self, node, data):
        text = json.dumps(data)
        node.SetAttribute('descriptions', text)

    def setMidPoint(self, node, ID, ID1, ID2):
        data = self.getData(node)

        data[ID]['midPoint']['isMidPoint'] = True
        data[ID]['midPoint']['Point1'] = ID1
        data[ID]['midPoint']['Point2'] = ID2

        data[ID1]['midPoint']['definedByThisMarkup'].append(ID)
        data[ID2]['midPoint']['definedByThisMarkup'].append(ID)

        self.setData(node, data)

        self.onPointsChanged(node, None)

    def setProjected(self, node, ID, isProjected):
        data = self.getData(node)

        data[ID]['projection']['isProjected'] = isProjected
        data[ID]['projection']['closestPointIndex'] = None

        self.setData(node, data)

    def computeMidPoint(self, node, ID, ID1, ID2):
        p1 = np.zeros(3)
        p2 = np.zeros(3)

        node.GetNthControlPointPosition(node.GetNthControlPointIndexByID(ID1), p1)

        node.GetNthControlPointPosition(node.GetNthControlPointIndexByID(ID2), p2)

        mp = (p1 + p2) / 2

        node.SetNthControlPointPositionFromArray(node.GetNthControlPointIndexByID(ID), mp)

    def onPointsChanged(self, node, e):
        with self.suppress(node, method=self.onPointsChanged):
            data = self.getData(node)

            current = {
                node.GetNthControlPointID(i)
                for i in range(node.GetNumberOfControlPoints())
            }
            previous = set(data)

            for ID in current - previous:
                data[ID] = self.default()

            for ID in previous - current:
                del data[ID]
                for sub in data.values():
                    if sub['midPoint']['isMidPoint']:
                        if ID in (sub['midPoint']['Point1'], sub['midPoint']['Point2']):
                            sub['midPoint']['isMidPoint'] = False
                            sub['midPoint']['Point1'] = None
                            sub['midPoint']['Point2'] = None

            for ID, desc in data.items():
                if desc['midPoint']['isMidPoint']:
                    self.computeMidPoint(
                        node,
                        ID,
                        desc['midPoint']['Point1'],
                        desc['midPoint']['Point2'],
                    )
                if desc['projection']['isProjected']:
                    self.computeProjection(
                        node, ID
                    )

            self.setData(node, data)


class DependantMarkupsTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        self.setUp()
        self.delayDisplay('Tests not yet implemented.')
