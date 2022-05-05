import collections
import contextlib
import json
from copy import deepcopy

import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModule
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleWidget
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleTest
from slicer.util import VTKObservationMixin
from slicer.util import NodeModify

import numpy as np

import vtk

try:
    import networkx as nx
except ModuleNotFoundError as e:
    slicer.util.pip_install("networkx")
    import networkx as nx


def normalize(arr):
    arr = np.asarray(arr)

    return arr / np.linalg.norm(arr)


def project(vec, axis):
    vec = np.asarray(vec)
    axis = np.asarray(axis)

    return axis * (np.dot(vec, axis) / np.dot(axis, axis))


def reject(vec, axis):
    vec = np.asarray(vec)
    axis = np.asarray(axis)

    return vec - axis * (np.dot(vec, axis) / np.dot(axis, axis))


class DependantMarkups(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Dependent Markups"
        parent.categories = ["Developer Tools"]
        parent.dependencies = []
        parent.contributors = [
            "David Allemang (Kitware Inc.)",
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
            if all(
                (
                    obj is ... or obj == o,
                    event is ... or event == e,
                    method is ... or method == m,
                )
            ):
                o.RemoveObserver(t)
                self.Observations.remove([o, e, m, g, t, p])
                suppressed.append([o, e, m, g, t, p])

        yield

        for o, e, m, g, _, p in suppressed:
            t = o.AddObserver(e, m, p)
            self.Observations.append([o, e, m, g, t, p])


class DependantMarkupsLogic(
    ScriptedLoadableModuleLogic, VTKSuppressibleObservationMixin
):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        VTKSuppressibleObservationMixin.__init__(self)

        self.default_projected = True
        self.ndigits = 3
        self.tolerance = 1e-5

    @staticmethod
    def recover_midpoint_provenance(landmarks):  # todo integrate into connect()
        """
        When a new list of fiducials is loaded from a file, we know which are
        midpoints, but we don't know from which points those midpoints were
        constructed. This function recovers this information.
        """
        # Build the data structures we will need.
        point_ids = []
        points = []
        ids_and_midpoints = []
        all_ids = []
        scratch_array = np.zeros(3)
        for n in range(landmarks.GetNumberOfMarkups()):
            markupID = landmarks.GetNthMarkupID(n)
            is_sel = landmarks.GetNthFiducialSelected(n)
            landmarks.GetNthFiducialPosition(n, scratch_array)
            markup_pos = np.copy(scratch_array)
            if is_sel:  # not a midpoint
                point_ids.append(markupID)
                points.append(markup_pos)
            else:  # midpoint
                ids_and_midpoints.append((markupID, markup_pos))
            all_ids.append(markupID)

        # This is the structure we want to populate to help build
        # landmarkDescription in createNewDataStructure.
        midpoint_data = {
            point_id: {
                "isMidPoint": False,
                "Point1": None,
                "Point2": None,
            }
            for point_id in all_ids
        }

        # Use a kd-tree to find points that could be the missing endpoint of a
        # hypothetical midpoint operation.
        points = np.array(points)
        n_new_points = len(points)
        while n_new_points > 0 and len(ids_and_midpoints) > 0:
            kdt = scipy.spatial.KDTree(points)
            n_new_points = 0
            new_ids_and_midpoints = []
            for mp_id, mp in ids_and_midpoints:
                provenance_found = False
                for p_idx, p in enumerate(points):
                    # hp for "hypothetical point"
                    # mp = (hp + p) / 2
                    hp = 2 * mp - p
                    max_error = np.linalg.norm(mp - p) / 10000.0
                    distance, kdt_p_idx = kdt.query(hp, distance_upper_bound=max_error)
                    # distance = np.inf on failure
                    if distance < max_error:
                        ids = (point_ids[p_idx], point_ids[kdt_p_idx])
                        midpoint_data[mp_id].update(
                            {
                                "isMidPoint": True,
                                "Point1": ids[0],
                                "Point2": ids[1],
                            }
                        )

                        provenance_found = True
                        point_ids.append(mp_id)
                        points = np.concatenate((points, mp.reshape((1, 3))))
                        n_new_points += 1
                        break
                if not provenance_found:
                    new_ids_and_midpoints.append((mp_id, mp))
            ids_and_midpoints = new_ids_and_midpoints

        return midpoint_data

    def default(self):
        return {
            "midPoint": {
                "isMidPoint": False,
                "Point1": None,
                "Point2": None,
            },
            "projection": {
                "isProjected": self.default_projected,
                "closestPointIndex": None,
            },
        }

        # todo roi radius

        # planeDescription = dict()
        # landmarks.SetAttribute("planeDescription", self.encodeJSON(planeDescription))
        # landmarks.SetAttribute("isClean", self.encodeJSON({"isClean": False}))
        # landmarks.SetAttribute("lastTransformID", None)
        # landmarks.SetAttribute("arrayName", model.GetName() + "_ROI")

    @staticmethod
    def createHardenModel(model):
        name = model.GetName()
        pid = slicer.app.applicationPid()
        name = f"SurafceRegistration_{name}_hardenCopy_{pid}"

        hardenModel = slicer.mrmlScene.GetFirstNodeByName(name)
        if hardenModel is None:
            # hardenModel = slicer.mrmlScene.
            hardenModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", name)

        hardenPolyData = vtk.vtkPolyData()
        hardenPolyData.DeepCopy(model.GetPolyData())
        hardenModel.SetAndObservePolyData(hardenPolyData)

        if model.GetParentTransformNode():
            hardenModel.SetAndObserveTransformNodeID(
                model.GetParentTransformNode().GetID()
            )

        hardenModel.HideFromEditorsOn()

        logic = slicer.vtkSlicerTransformLogic()
        logic.hardenTransform(hardenModel)
        return hardenModel

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

    def replaceLandmark(
        self, inputModelPolyData, fidNode, landmarkID, indexClosestPoint
    ):
        landmarkCoord = [-1, -1, -1]
        inputModelPolyData.GetPoints().GetPoint(indexClosestPoint, landmarkCoord)
        fidNode.SetNthControlPointPositionFromArray(
            landmarkID,
            landmarkCoord,
            slicer.vtkMRMLMarkupsNode.PositionPreview,
        )

    def getNthControlPointLabelByID(self, node, ID):
        index = node.GetNthControlPointIndexByID(ID)
        return node.GetNthControlPointLabel(index)

    def setNthControlPointLabelByID(self, node, ID, value):
        index = node.GetNthControlPointIndexByID(ID)
        node.SetNthControlPointLabel(index, value)

    def getNthControlPointPositionByID(self, node, ID):
        result = np.zeros(3)
        index = node.GetNthControlPointIndexByID(ID)
        node.GetNthControlPointPosition(index, result)
        return result

    def setNthControlPointPositionByID(self, node, ID, value):
        index = node.GetNthControlPointIndexByID(ID)
        node.SetNthControlPointPositionFromArray(index, value)

    def projectOnSurface(self, modelOnProject, fidNode, selectedFidReflID):
        if selectedFidReflID:
            markupsIndex = fidNode.GetNthControlPointIndexByID(selectedFidReflID)
            indexClosestPoint = self.getClosestPointIndex(
                fidNode, modelOnProject.GetPolyData(), markupsIndex
            )
            self.replaceLandmark(
                modelOnProject.GetPolyData(), fidNode, markupsIndex, indexClosestPoint
            )
            return indexClosestPoint

    def getModel(self, node):
        hardened = node.GetNodeReference("HARDENED_MODEL")
        model = node.GetNodeReference("MODEL")
        return hardened or model

    def computeProjection(self, node, ID):
        model = self.getModel(node)
        if not model:
            return

        self.projectOnSurface(model, node, ID)

    def connect(self, node, model):
        node.AddNodeReferenceID("MODEL", model.GetID())

        events = node.PointAddedEvent, node.PointModifiedEvent, node.PointRemovedEvent
        for event in events:
            self.addObserver(node, event, self.onPointsChanged, priority=100.0)

        self.addObserver(model, model.TransformModifiedEvent, self.onModelChanged)
        # todo remove observer when model changed.

    def getData(self, node):
        text = node.GetAttribute("descriptions")
        if not text:
            return {}
        return json.loads(text)

    def setData(self, node, data):
        text = json.dumps(data)
        node.SetAttribute("descriptions", text)

    def getUpdateOrder(self, data):
        graph = nx.DiGraph()

        for ID in data:
            graph.add_node(ID)

        for ID in data:
            if data[ID]["midPoint"]["isMidPoint"]:
                sources = [
                    data[ID]["midPoint"]["Point1"],
                    data[ID]["midPoint"]["Point2"],
                ]
                for source in sources:
                    graph.add_edge(source, ID)

        return nx.topological_sort(graph)

    def setMidPoint(self, node, ID, ID1, ID2):
        data = self.getData(node)

        data[ID]["midPoint"]["isMidPoint"] = True
        data[ID]["midPoint"]["Point1"] = ID1
        data[ID]["midPoint"]["Point2"] = ID2

        self.setData(node, data)

        self.onPointsChanged(node, None)

    def setProjected(self, node, ID, isProjected):
        data = self.getData(node)

        data[ID]["projection"]["isProjected"] = isProjected
        data[ID]["projection"]["closestPointIndex"] = None

        self.setData(node, data)

    def computeMidPoint(self, node, ID, ID1, ID2):
        p1 = self.getNthControlPointPositionByID(node, ID1)
        p2 = self.getNthControlPointPositionByID(node, ID2)

        mp = (p1 + p2) / 2

        self.setNthControlPointPositionByID(node, ID, mp)

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
                    if sub["midPoint"]["isMidPoint"]:
                        if ID in (sub["midPoint"]["Point1"], sub["midPoint"]["Point2"]):
                            sub["midPoint"]["isMidPoint"] = False
                            sub["midPoint"]["Point1"] = None
                            sub["midPoint"]["Point2"] = None

            for ID in self.getUpdateOrder(data):
                info = data[ID]
                if info["midPoint"]["isMidPoint"]:
                    self.computeMidPoint(
                        node,
                        ID,
                        info["midPoint"]["Point1"],
                        info["midPoint"]["Point2"],
                    )
                if info["projection"]["isProjected"]:
                    self.computeProjection(node, ID)

            self.setData(node, data)

    def onModelChanged(self, model, e):
        hardened = self.createHardenModel(model)

        for node in slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsNode"):
            if node.GetNodeReference("MODEL") == model:
                node.SetNodeReferenceID("HARDENED_MODEL", hardened.GetID())
                # todo re-project

    def updateLandmarkComboBox(self, node, comboBox, displayMidPoints=True):
        current = comboBox.currentData

        comboBox.blockSignals(True)
        comboBox.clear()

        if not node:
            return

        data = self.getData(node)

        for idx in range(node.GetNumberOfControlPoints()):
            ID = node.GetNthControlPointID(idx)
            label = node.GetNthControlPointLabel(idx)
            if data[ID]["midPoint"]["isMidPoint"] and not displayMidPoints:
                continue
            comboBox.addItem(label, ID)

        idx = comboBox.findData(current)
        if idx >= 0:
            comboBox.setCurrentIndex(idx)

        comboBox.blockSignals(False)

    def round(self, value):
        if value is None:
            return None

        return round(value, self.ndigits)

    def roundall(self, values):
        return [self.round(value) for value in values]

    DistanceResult = collections.namedtuple("DistanceResult", ("delta", "norm"))

    def computeDistance(self, point1, point2) -> DistanceResult:
        delta = point2 - point1
        return self.DistanceResult(
            delta,
            np.linalg.norm(delta),
        )

    def computeAngle(self, line1, line2, axis=None):
        if axis:
            line1 = reject(line1, normalize(axis))
            line2 = reject(line2, normalize(axis))

        line1 = normalize(line1)
        line2 = normalize(line2)

        radians = np.arccos(np.dot(line1, line2))

        return np.degrees(radians)

    AnglesResult = collections.namedtuple("AnglesResult", ("absolute", "byaxis"))

    def computeAngles(self, line1, line2) -> AnglesResult:
        axes = [
            (0, 0, 1),  # axis=S; axial; for yaw
            (1, 0, 0),  # axis=R; saggital; for pitch
            (0, 1, 0),  # axis=A; coronal; for roll
        ]

        return self.AnglesResult(
            self.computeAngle(line1, line2),
            [self.computeAngle(line1, line2, axis) for axis in axes],
        )

    def computeLinePoint(self, line1, line2, point) -> DistanceResult:
        if np.allclose(line1, line2, atol=self.tolerance):
            delta = point - line1
        else:
            delta = reject(
                point - line2,
                line1 - line2,
            )

        return self.DistanceResult(
            delta,
            np.linalg.norm(delta),
        )


class DependantMarkupsTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        self.setUp()
        self.delayDisplay("Tests not yet implemented.")
