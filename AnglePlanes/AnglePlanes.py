import json
import logging

import DependantMarkups
import numpy
import os
import pickle
import time
import vtk, qt, ctk

from math import acos, pi, sqrt

import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModule
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleWidget
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleTest
from slicer.util import VTKObservationMixin
from slicer.util import NodeModify


class AnglePlanes(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Angle Planes"
        parent.categories = ["Quantification"]
        parent.dependencies = ["DependantMarkups"]
        parent.contributors = [
            "Julia Lopinto",
            "Juan Carlos Prieto",
            "Francois Budin",
            "Jean-Baptiste Vimort",
        ]
        parent.helpText = """
            This Module is used to calculate the angle between two planes by using the normals.
            The user gets the choice to use two planes which are already implemented on Slicer
            or they can define a plane by using landmarks (at least 3 landmarks).
            Plane can also be saved to be reused for other models.
            This is an alpha version of the module.
            It can't be used for the moment.
            """

        parent.acknowledgementText = """
            This work was supported by the National
            Institutes of Dental and Craniofacial Research
            and Biomedical Imaging and Bioengineering of
            the National Institutes of Health under Award
            Number R01DE024450.
            """

        self.parent = parent


class AnglePlanesWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None

    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        self.i = 0
        self.logic = AnglePlanesLogic()
        self.deps = DependantMarkups.DependantMarkupsLogic()
        self.planeControlsId = 0
        self.planeControlsDictionary = {}
        self.planeCollection = vtk.vtkPlaneCollection()
        self.ignoredNodeNames = (
            "Red Volume Slice",
            "Yellow Volume Slice",
            "Green Volume Slice",
        )
        self.colorSliceVolumes = dict()
        self.interactionNode = slicer.mrmlScene.GetNodeByID(
            "vtkMRMLInteractionNodeSingleton"
        )

        # Load widget from .ui file (created by Qt Designer)
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/AnglePlanes.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # --------------------------- Scene --------------------------#
        self.ui.treeView.setMRMLScene(slicer.app.mrmlScene())
        self.ui.treeView.sceneModel().setHorizontalHeaderLabels(["Models"])
        self.ui.treeView.sortFilterProxyModel().nodeTypes = ["vtkMRMLModelNode"]
        self.ui.treeView.header().setVisible(False)
        self.autoChangeLayout = self.ui.autoChangeLayout
        self.computeBox = self.ui.computeBox
        # -------------------------------Manage planes---------------------------------
        self.CollapsibleButton = self.ui.CollapsibleButton
        self.managePlanesFormLayout = self.ui.managePlanesFormLayout
        self.inputModelSelector = self.ui.inputModelSelector
        self.inputModelSelector.setMRMLScene(slicer.mrmlScene)
        self.inputLandmarksSelector = self.ui.inputLandmarksSelector
        self.inputLandmarksSelector.setMRMLScene(slicer.mrmlScene)
        self.inputLandmarksSelector.setEnabled(
            False
        )  # The "enable" property seems to not be imported from the .ui
        self.addPlaneButton = self.ui.addPlaneButton
        self.landmarkComboBox = self.ui.landmarkComboBox
        self.surfaceDeplacementCheckBox = self.ui.surfaceDeplacementCheckBox
        # ----------------- Compute Mid Point -------------
        self.midPointGroupBox = self.ui.midPointGroupBox
        self.selectPlaneForMidPoint = self.ui.selectPlaneForMidPoint
        self.landmarkComboBox1MidPoint = self.ui.landmarkComboBox1MidPoint
        self.landmarkComboBox2MidPoint = self.ui.landmarkComboBox2MidPoint
        self.midPointOnSurfaceCheckBox = self.ui.midPointOnSurfaceCheckBox
        self.defineMiddlePointButton = self.ui.defineMiddlePointButton
        # -------- Choose planes ------------
        self.CollapsibleButtonPlane = self.ui.CollapsibleButtonPlane
        self.planeComboBox1 = self.ui.planeComboBox1
        self.planeComboBox2 = self.ui.planeComboBox2
        # -------- Calculate angles between planes ------------
        self.CollapsibleButton2 = self.ui.CollapsibleButton2
        self.results = self.ui.results
        self.tableResult = self.ui.tableResult
        self.getAngle_RL = qt.QLabel("0")
        self.getAngle_RL.setStyleSheet("QLabel{qproperty-alignment:AlignCenter;}")
        self.getAngle_SI = qt.QLabel("0")
        self.getAngle_SI.setStyleSheet("QLabel{qproperty-alignment:AlignCenter;}")
        self.getAngle_AP = qt.QLabel("0")
        self.getAngle_AP.setStyleSheet("QLabel{qproperty-alignment:AlignCenter;}")
        self.getAngle_RL_comp = qt.QLabel("0")
        self.getAngle_RL_comp.setStyleSheet("QLabel{qproperty-alignment:AlignCenter;}")
        self.getAngle_SI_comp = qt.QLabel("0")
        self.getAngle_SI_comp.setStyleSheet("QLabel{qproperty-alignment:AlignCenter;}")
        self.getAngle_AP_comp = qt.QLabel("0")
        self.getAngle_AP_comp.setStyleSheet("QLabel{qproperty-alignment:AlignCenter;}")
        self.tableResult.setColumnWidth(1, 180)
        self.tableResult.setCellWidget(0, 0, self.getAngle_RL)
        self.tableResult.setCellWidget(0, 1, self.getAngle_RL_comp)
        self.tableResult.setCellWidget(1, 0, self.getAngle_SI)
        self.tableResult.setCellWidget(1, 1, self.getAngle_SI_comp)
        self.tableResult.setCellWidget(2, 0, self.getAngle_AP)
        self.tableResult.setCellWidget(2, 1, self.getAngle_AP_comp)
        # -------------------------------- PLANES --------------------------------#
        self.CollapsibleButton3 = self.ui.CollapsibleButton3
        self.save = self.ui.save
        self.read = self.ui.read
        # -------------------------------- CONNECTIONS --------------------------------#
        self.computeBox.connect("clicked()", self.onComputeBox)
        self.inputModelSelector.connect(
            "currentNodeChanged(vtkMRMLNode*)", self.onModelChanged
        )
        self.inputLandmarksSelector.connect(
            "currentNodeChanged(vtkMRMLNode*)", self.onLandmarksChanged
        )
        self.planeComboBox1.connect("currentIndexChanged(QString)", self.valueComboBox)
        self.planeComboBox2.connect("currentIndexChanged(QString)", self.valueComboBox)
        self.addPlaneButton.connect("clicked()", self.addNewPlane)
        self.landmarkComboBox.connect(
            "currentIndexChanged(QString)", self.UpdateInterface
        )
        self.surfaceDeplacementCheckBox.connect(
            "stateChanged(int)", self.onSurfaceDeplacementStateChanged
        )
        self.selectPlaneForMidPoint.connect(
            "currentIndexChanged(int)", self.onChangeMiddlePointFiducialNode
        )
        self.defineMiddlePointButton.connect("clicked()", self.onAddMidPoint)
        self.results.connect("clicked()", self.angleValue)
        self.save.connect("clicked(bool)", self.onSavePlanes)
        self.read.connect("clicked(bool)", self.onReadPlanes)

        slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndCloseEvent, self.onCloseScene)

        for i in self.getPositionOfModelNodes(False):
            modelnode = slicer.mrmlScene.GetNthNodeByClass(i, "vtkMRMLModelNode")
            modelnode.AddObserver(
                modelnode.DisplayModifiedEvent, self.onChangeModelDisplay
            )

        self.addObserver(
            slicer.mrmlScene, slicer.vtkMRMLScene.NodeAddedEvent, self.nodeAddedCallback
        )
        self.addObserver(
            slicer.mrmlScene,
            slicer.vtkMRMLScene.NodeRemovedEvent,
            self.nodeRemovedCallback,
        )

        # ------------------------------ INITIALISATION ---------------------------------
        self.fillColorsComboBox(self.planeComboBox1)
        self.fillColorsComboBox(self.planeComboBox2)
        self.planeComboBox1.setCurrentIndex(0)
        self.planeComboBox2.setCurrentIndex(0)
        self.valueComboBox()

        # These attributes are useful for Longitudinal quantification extension
        self.SceneCollapsibleButton = self.ui.SceneCollapsibleButton
        self.inputModelLabel = self.ui.inputModelLabel
        self.inputLandmarksLabel = self.ui.inputLandmarksLabel

    def cleanup(self):
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()

    def enter(self):
        model = self.inputModelSelector.currentNode()
        fidlist = self.inputLandmarksSelector.currentNode()

        if fidlist:
            if fidlist.GetNodeReference("connectedModel") != model:
                self.inputModelSelector.setCurrentNode(None)
                self.inputLandmarksSelector.setCurrentNode(None)
                self.landmarkComboBox.clear()
        self.UpdateInterface()

    def UpdateInterface(self):
        print("--- UpdateInterface ---")
        self.logic.UpdateThreeDView(self.landmarkComboBox.currentData)

    @vtk.calldata_type(vtk.VTK_OBJECT)
    def nodeAddedCallback(self, caller, eventId, callData):
        if isinstance(callData, slicer.vtkMRMLModelNode):
            callData.AddObserver(
                callData.DisplayModifiedEvent, self.onChangeModelDisplay
            )
            self.addObserver(
                callData,
                callData.PolyDataModifiedEvent,
                self.onModelNodePolyDataModified,
            )
            self.updateOnSurfaceCheckBoxes()

    @vtk.calldata_type(vtk.VTK_OBJECT)
    def nodeRemovedCallback(self, caller, eventId, callData):
        if isinstance(callData, slicer.vtkMRMLModelNode):
            self.removeObserver(
                callData,
                callData.PolyDataModifiedEvent,
                self.onModelNodePolyDataModified,
            )
            callData.RemoveObservers(callData.DisplayModifiedEvent)
            self.updateOnSurfaceCheckBoxes()
        if isinstance(callData, slicer.vtkMRMLMarkupsFiducialNode):
            name = callData.GetName()
            planeid = name[len("P") :]
            name = "Plane " + planeid
            if name in self.planeControlsDictionary.keys():
                self.RemoveManualPlane(planeid)

    def onModelNodePolyDataModified(self, caller, eventId):
        pass

    def onModelChanged(self):
        print("-------Model Changed--------")
        if self.logic.selectedModel:
            Model = self.logic.selectedModel
            try:
                Model.RemoveObserver(
                    self.logic.decodeJSON(
                        self.logic.selectedModel.GetAttribute("modelModifieTagEvent")
                    )
                )
            except:
                pass
        self.logic.selectedModel = self.inputModelSelector.currentNode()
        self.logic.ModelChanged(self.inputModelSelector, self.inputLandmarksSelector)
        self.inputLandmarksSelector.setCurrentNode(None)
        self.addPlaneButton.setEnabled(False)

    def onLandmarksChanged(self):
        print("-------Landmarks Changed--------")

        markups = self.inputLandmarksSelector.currentNode()
        model = self.inputModelSelector.currentNode()

        self.logic.FidList = markups
        self.logic.selectedFidList = markups
        self.logic.selectedModel = model

        if markups and model:
            self.deps.connect(markups, model)

            markups.AddObserver(markups.PointAddedEvent, self.onPointAdded)
            markups.AddObserver(markups.PointModifiedEvent, self.onPointModified)
            markups.AddObserver(markups.PointRemovedEvent, self.onPointRemoved)

            self.deps.updateLandmarkComboBox(markups, self.landmarkComboBox, False)
            self.addPlaneButton.setEnabled(True)
            self.UpdateInterface()
        else:
            self.addPlaneButton.setEnabled(False)
            self.landmarkComboBox.clear()

    def onPointAdded(self, obj, event):
        self.updateAllLandmarkComboBox(obj)
        self.UpdateInterface()

    def onPointModified(self, obj, event):
        for planeControls in self.planeControlsDictionary.values():
            if planeControls.fidlist is obj:
                planeControls.update()

    def onPointRemoved(self, obj, event):
        self.updateAllLandmarkComboBox(obj)
        self.UpdateInterface()

    def updateAllLandmarkComboBox(self, fidList):
        # update of the Combobox that are always updated
        self.deps.updateLandmarkComboBox(fidList, self.landmarkComboBox, False)

        for control in self.planeControlsDictionary.values():
            self.deps.updateLandmarkComboBox(control.fidlist, control.landmark1ComboBox)
            self.deps.updateLandmarkComboBox(control.fidlist, control.landmark2ComboBox)
            self.deps.updateLandmarkComboBox(control.fidlist, control.landmark3ComboBox)

        control = self.selectPlaneForMidPoint.currentData
        self.deps.updateLandmarkComboBox(
            control.fidlist, self.landmarkComboBox1MidPoint
        )
        self.deps.updateLandmarkComboBox(
            control.fidlist, self.landmarkComboBox2MidPoint
        )

    def onSurfaceDeplacementStateChanged(self):
        self.deps.default_projected = self.surfaceDeplacementCheckBox.isChecked()

    def onChangeMiddlePointFiducialNode(self):
        key = self.selectPlaneForMidPoint.currentText
        if key is "":
            return
        plane = self.planeControlsDictionary[key]
        fidList = plane.fidlist
        self.deps.updateLandmarkComboBox(fidList, self.landmarkComboBox1MidPoint)
        self.deps.updateLandmarkComboBox(fidList, self.landmarkComboBox2MidPoint)

    def onChangeModelDisplay(self, obj, event):
        self.updateOnSurfaceCheckBoxes()

    def fillColorsComboBox(self, planeComboBox):
        planeComboBox.clear()
        planeComboBox.addItem("None")
        planeComboBox.addItem("Red")
        planeComboBox.addItem("Yellow")
        planeComboBox.addItem("Green")
        try:
            for x in self.planeControlsDictionary.keys():
                if self.planeControlsDictionary[x].PlaneIsDefined():
                    planeComboBox.addItem(x)
        except NameError:
            print("exept in fillColorsComboBox")

    def updateOnSurfaceCheckBoxes(self):
        numberOfVisibleModels = len(self.getPositionOfModelNodes(True))
        if numberOfVisibleModels > 0:
            self.computeBox.setDisabled(False)
        else:
            self.computeBox.setDisabled(True)

    def getPositionOfModelNodes(self, onlyVisible):
        numNodes = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode")
        positionOfNodes = list()
        for i in range(0, numNodes):
            node = slicer.mrmlScene.GetNthNodeByClass(i, "vtkMRMLModelNode")
            if node.GetName() in self.ignoredNodeNames:
                continue
            if onlyVisible is True and node.GetDisplayVisibility() == 0:
                continue
            positionOfNodes.append(i)
        return positionOfNodes

    def addNewPlane(self, keyLoad=-1):
        print("------- New plane created -------")
        if keyLoad != -1:
            self.planeControlsId = keyLoad
        else:
            self.planeControlsId += 1
        planeControls = AnglePlanesWidgetPlaneControl(
            self,
            self.planeControlsId,
            self.planeCollection,
            self.inputLandmarksSelector.currentNode(),
        )
        self.managePlanesFormLayout.addWidget(planeControls.widget)
        key = "Plane " + str(self.planeControlsId)
        self.planeControlsDictionary[key] = planeControls
        self.updatePlanesComboBoxes()
        self.midPointGroupBox.setDisabled(False)
        self.selectPlaneForMidPoint.addItem(key, planeControls)

    def RemoveManualPlane(self, id):
        print("--- Remove a plan ---")
        key = "Plane " + str(id)
        # If the plane has already been removed (for example, when removing this plane in this function,
        # the callback on removing the nodes will be called, and therefore this function will be called again
        # We need to not do anything the second time this function is called for the same plane
        if key not in self.planeControlsDictionary.keys():
            print("Key error")
            return
        if self.planeComboBox1.currentText == key:
            self.planeComboBox1.setCurrentIndex(0)
        if self.planeComboBox2.currentText == key:
            self.planeComboBox2.setCurrentIndex(0)
        planeControls = self.planeControlsDictionary[key]
        self.managePlanesFormLayout.removeWidget(planeControls.widget)
        planeControls.widget.hide()
        planeControls.deleteLater()
        planeControls.remove()
        self.planeControlsDictionary.pop(key)
        self.addPlaneButton.setDisabled(False)
        if len(self.planeControlsDictionary.keys()) == 0:
            self.midPointGroupBox.setDisabled(True)
            self.midPointGroupBox.collapsed = True
        self.updatePlanesComboBoxes()
        self.valueComboBox()
        if self.selectPlaneForMidPoint.findText(key) > -1:
            self.selectPlaneForMidPoint.removeItem(
                self.selectPlaneForMidPoint.findText(key)
            )

    def onComputeBox(self):
        positionOfVisibleNodes = self.getPositionOfModelNodes(True)
        if len(positionOfVisibleNodes) == 0:
            return
        try:
            maxValue = slicer.sys.float_info.max
        except:
            maxValue = self.logic.sys.float_info.max
        bound = [maxValue, -maxValue, maxValue, -maxValue, maxValue, -maxValue]
        for i in positionOfVisibleNodes:
            node = slicer.mrmlScene.GetNthNodeByClass(i, "vtkMRMLModelNode")
            model = self.logic.createIntermediateHardenModel(node)
            polydata = model.GetPolyData()
            if polydata is None or not hasattr(polydata, "GetBounds"):
                continue
            tempbound = polydata.GetBounds()
            bound[0] = min(bound[0], tempbound[0])
            bound[2] = min(bound[2], tempbound[2])
            bound[4] = min(bound[4], tempbound[4])

            bound[1] = max(bound[1], tempbound[1])
            bound[3] = max(bound[3], tempbound[3])
            bound[5] = max(bound[5], tempbound[5])
        # --------------------------- Box around the model --------------------------#
        dim = []
        origin = []
        for x in range(0, 3):
            dim.append(bound[x * 2 + 1] - bound[x * 2])
            origin.append(bound[x * 2] + int(dim[x] / 2))
            dim[x] *= 1.1
        # ---------definition of planes for clipping around the bounding box ---------#
        self.planeCollection = vtk.vtkPlaneCollection()
        self.planeXmin = vtk.vtkPlane()
        self.planeXmin.SetOrigin(bound[0], bound[2], bound[4])
        self.planeXmin.SetNormal(1, 0, 0)
        self.planeCollection.AddItem(self.planeXmin)
        self.planeYmin = vtk.vtkPlane()
        self.planeYmin.SetOrigin(bound[0], bound[2], bound[4])
        self.planeYmin.SetNormal(0, 1, 0)
        self.planeCollection.AddItem(self.planeYmin)
        self.planeZmin = vtk.vtkPlane()
        self.planeZmin.SetOrigin(bound[0], bound[2], bound[4])
        self.planeZmin.SetNormal(0, 0, 1)
        self.planeCollection.AddItem(self.planeZmin)
        self.planeXmax = vtk.vtkPlane()
        self.planeXmax.SetOrigin(bound[1], bound[3], bound[5])
        self.planeXmax.SetNormal(-1, 0, 0)
        self.planeCollection.AddItem(self.planeXmax)
        self.planeYmax = vtk.vtkPlane()
        self.planeYmax.SetOrigin(bound[1], bound[3], bound[5])
        self.planeYmax.SetNormal(0, -1, 0)
        self.planeCollection.AddItem(self.planeYmax)
        self.planeZmax = vtk.vtkPlane()
        self.planeZmax.SetOrigin(bound[1], bound[3], bound[5])
        self.planeZmax.SetNormal(0, 0, -1)
        self.planeCollection.AddItem(self.planeZmax)
        # print self.planeCollection
        dictColors = {"Red": 32, "Yellow": 15, "Green": 1}
        for x in dictColors.keys():
            sampleVolumeNode = self.CreateNewNode(x, dictColors[x], dim, origin)
            compNode = slicer.util.getNode("vtkMRMLSliceCompositeNode" + x)
            compNode.SetLinkedControl(False)
            compNode.SetBackgroundVolumeID(sampleVolumeNode.GetID())
            # print "set background" + x
        lm = slicer.app.layoutManager()
        # Reset and fit 2D-views
        lm.resetSliceViews()
        for x in dictColors.keys():
            logic = lm.sliceWidget(x)
            node = logic.mrmlSliceNode()
            node.SetSliceResolutionMode(node.SliceResolutionMatch2DView)
            logic.fitSliceToBackground()
        # Reset pink box around models
        for i in range(0, lm.threeDViewCount):
            threeDView = lm.threeDWidget(i).threeDView()
            threeDView.resetFocalPoint()
            # Reset camera in 3D view to center the models and position the camera so that all actors can be seen
            threeDView.renderWindow().GetRenderers().GetFirstRenderer().ResetCamera()

    def CreateNewNode(self, colorName, color, dim, origin):
        # we add a pseudo-random number to the name of our empty volume to avoid the risk of having a volume called
        #  exactly the same by the user which could be confusing. We could also have used slicer.app.sessionId()
        if colorName not in self.colorSliceVolumes.keys():
            VolumeName = (
                "AnglePlanes_EmptyVolume_"
                + str(slicer.app.applicationPid())
                + "_"
                + colorName
            )
            # Do NOT set the spacing and the origin of imageData (vtkImageData)
            # The spacing and the origin should only be set in the vtkMRMLScalarVolumeNode!!!!!!
            # We only create an image of 1 voxel (as we only use it to color the planes
            imageData = vtk.vtkImageData()
            imageData.SetDimensions(1, 1, 1)
            imageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
            imageData.SetScalarComponentFromDouble(0, 0, 0, 0, color)
            if hasattr(slicer, "vtkMRMLLabelMapVolumeNode"):
                sampleVolumeNode = slicer.vtkMRMLLabelMapVolumeNode()
            else:
                sampleVolumeNode = slicer.vtkMRMLScalarVolumeNode()
            sampleVolumeNode = slicer.mrmlScene.AddNode(sampleVolumeNode)
            sampleVolumeNode.SetName(VolumeName)
            labelmapVolumeDisplayNode = slicer.vtkMRMLLabelMapVolumeDisplayNode()
            slicer.mrmlScene.AddNode(labelmapVolumeDisplayNode)
            colorNode = slicer.util.getNode("GenericAnatomyColors")
            labelmapVolumeDisplayNode.SetAndObserveColorNodeID(colorNode.GetID())
            sampleVolumeNode.SetAndObserveImageData(imageData)
            sampleVolumeNode.SetAndObserveDisplayNodeID(
                labelmapVolumeDisplayNode.GetID()
            )
            labelmapVolumeDisplayNode.VisibilityOn()
            self.colorSliceVolumes[colorName] = sampleVolumeNode.GetID()
        sampleVolumeNode = slicer.mrmlScene.GetNodeByID(
            self.colorSliceVolumes[colorName]
        )
        sampleVolumeNode.HideFromEditorsOn()
        sampleVolumeNode.SetOrigin(origin[0], origin[1], origin[2])
        sampleVolumeNode.SetSpacing(dim[0], dim[1], dim[2])
        if not hasattr(slicer, "vtkMRMLLabelMapVolumeNode"):
            sampleVolumeNode.SetLabelMap(1)
        sampleVolumeNode.SetHideFromEditors(True)
        sampleVolumeNode.SetSaveWithScene(False)
        return sampleVolumeNode

    def onAddMidPoint(self):
        key = self.selectPlaneForMidPoint.currentText
        plane = self.planeControlsDictionary[key]
        fidList = plane.fidlist

        if not fidList:
            self.logic.warningMessage("Fiducial list problem.")

        ID1 = self.landmarkComboBox1MidPoint.currentData
        ID2 = self.landmarkComboBox2MidPoint.currentData

        key = "{}_{}".format(
            fidList.GetNthControlPointLabel(fidList.GetNthControlPointIndexByID(ID1)),
            fidList.GetNthControlPointLabel(fidList.GetNthControlPointIndexByID(ID2)),
        )

        ID = fidList.GetNthControlPointID(
            fidList.AddControlPoint(vtk.vtkVector3d(), key)
        )

        self.deps.setMidPoint(fidList, ID, ID1, ID2)

        self.UpdateInterface()
        self.deps.updateLandmarkComboBox(fidList, self.landmarkComboBox, False)

    def onCloseScene(self, obj, event):
        self.colorSliceVolumes = dict()
        self.planeControlsId = 0
        models = slicer.mrmlScene.GetNodesByClass("vtkMRMLModelNode")
        end = models.GetNumberOfItems()
        for i in range(0, end):
            model = models.GetItemAsObject(i)
            hardenModel = slicer.mrmlScene.GetNodesByName(
                model.GetName()
            ).GetItemAsObject(0)
            slicer.mrmlScene.RemoveNode(hardenModel)
        keys = list(self.planeControlsDictionary.keys())
        for x in keys:
            self.RemoveManualPlane(x[len("Plane ") :])
        self.planeControlsDictionary = dict()
        self.addPlaneButton.setDisabled(True)
        self.getAngle_RL.setText("0")
        self.getAngle_RL_comp.setText("0")
        self.getAngle_SI.setText("0")
        self.getAngle_SI_comp.setText("0")
        self.getAngle_AP.setText("0")
        self.getAngle_AP_comp.setText("0")
        self.landmarkComboBox.clear()

    def angleValue(self):
        self.valueComboBox()
        self.getAngle_RL.setText(self.logic.angle_degre_RL)
        self.getAngle_RL_comp.setText(self.logic.angle_degre_RL_comp)
        self.getAngle_SI.setText(self.logic.angle_degre_SI)
        self.getAngle_SI_comp.setText(self.logic.angle_degre_SI_comp)
        self.getAngle_AP.setText(self.logic.angle_degre_AP)
        self.getAngle_AP_comp.setText(self.logic.angle_degre_AP_comp)

    def setFirstItemInComboBoxNotGivenString(self, comboBox, oldString, noThisString):
        if comboBox.findText(oldString) == -1:
            comboBox.setCurrentIndex(1)
        else:
            comboBox.setCurrentIndex(comboBox.findText(oldString))

    def updatePlanesComboBoxes(self):
        print("---- update plane combobox ----")
        self.planeComboBox1.blockSignals(True)
        self.planeComboBox2.blockSignals(True)
        colorPlane1 = self.planeComboBox1.currentText
        colorPlane2 = self.planeComboBox2.currentText
        # Reset Combo boxes
        self.fillColorsComboBox(self.planeComboBox1)
        self.fillColorsComboBox(self.planeComboBox2)
        if colorPlane1 != "None":
            self.planeComboBox2.removeItem(self.planeComboBox2.findText(colorPlane1))
        if colorPlane2 != "None":
            self.planeComboBox1.removeItem(self.planeComboBox1.findText(colorPlane2))
        self.setFirstItemInComboBoxNotGivenString(
            self.planeComboBox1, colorPlane1, colorPlane2
        )
        self.setFirstItemInComboBoxNotGivenString(
            self.planeComboBox2, colorPlane2, colorPlane1
        )
        self.planeComboBox1.blockSignals(False)
        self.planeComboBox2.blockSignals(False)

    def valueComboBox(self):
        self.updatePlanesComboBoxes()
        # Hide everything before showing what is necessary
        for x in self.logic.ColorNodeCorrespondence.keys():
            compNode = slicer.util.getNode("vtkMRMLSliceCompositeNode" + x)
            compNode.SetLinkedControl(False)
            slice = slicer.mrmlScene.GetNodeByID(self.logic.ColorNodeCorrespondence[x])
            slice.SetWidgetVisible(False)
            slice.SetSliceVisible(False)
        colorPlane1 = self.planeComboBox1.currentText
        colorPlane2 = self.planeComboBox2.currentText
        self.defineAngle(colorPlane1, colorPlane2)

    def defineAngle(self, colorPlane1, colorPlane2):
        print("--- defineAngle ---")
        # print colorPlane1
        if colorPlane1 != "None":
            if colorPlane1 in self.logic.ColorNodeCorrespondence:
                slice1 = slicer.util.getNode(
                    self.logic.ColorNodeCorrespondence[colorPlane1]
                )
                self.logic.getMatrix(slice1)
                slice1.SetWidgetVisible(True)
                slice1.SetSliceVisible(True)
                matrix1 = self.logic.getMatrix(slice1)
                normal1 = self.logic.defineNormal(matrix1)
            else:
                normal1 = self.planeControlsDictionary[colorPlane1].normal
        else:
            return
        # print colorPlane2
        if colorPlane2 != "None":
            if colorPlane2 in self.logic.ColorNodeCorrespondence:
                slice2 = slicer.util.getNode(
                    self.logic.ColorNodeCorrespondence[colorPlane2]
                )
                self.logic.getMatrix(slice2)
                slice2.SetWidgetVisible(True)
                slice2.SetSliceVisible(True)
                matrix2 = self.logic.getMatrix(slice2)
                normal2 = self.logic.defineNormal(matrix2)
            else:
                normal2 = self.planeControlsDictionary[colorPlane2].normal
        else:
            return
        print("normal 1")
        print(normal1)
        print("normal 2")
        print(normal2)
        self.logic.getAngle(normal1, normal2)

    def onSavePlanes(self):
        filename = qt.QFileDialog.getSaveFileName(self.parent, "Save file")
        self.logic.savePlanes(filename)

    def onReadPlanes(self):
        filename = qt.QFileDialog.getOpenFileName(self.parent, "Open file")
        self.logic.readPlanes(filename)
        self.onComputeBox()


class AnglePlanesWidgetPlaneControl(qt.QFrame):
    """This widget controls each of the planes that are added to the interface.

    The widget contains its own logic, i.e. an object of AnglePlanesLogic.
    Each plane contains a separate fiducial list. The planes are named P1, P2, ..., PN.
    The landmarks are named P1-1, P1-2, P1-N.
    """

    def __init__(self, anglePlanes, id, planeCollection, fidlist):
        # ------------- variables -------------------
        self.anglePlanes = anglePlanes
        self.deps = anglePlanes.deps
        self.logic = anglePlanes.logic
        self.planeCollection = planeCollection
        self.id = id
        self.fidlist = fidlist
        self.actor = vtk.vtkActor()
        self.normal = None
        # -------------- interface -------------------
        qt.QFrame.__init__(self)
        # UI setup
        scriptedModulesPath = os.path.dirname(slicer.util.modulePath("AnglePlanes"))
        uiFile = os.path.join(scriptedModulesPath, "Resources", "UI/PlaneControl.ui")
        uiWidget = slicer.util.loadUI(uiFile)
        self.widget = uiWidget
        self.ui = slicer.util.childWidgetVariables(uiWidget)
        # self.anglePlanes.layout.addWidget(widget)

        self.planeLabel = self.ui.planeLabel
        self.planeLabel.setText("Plane " + str(id) + ":")
        self.addFiducialButton = self.ui.addFiducialButton
        self.landmark1ComboBox = self.ui.landmark1ComboBox
        self.landmark2ComboBox = self.ui.landmark2ComboBox
        self.landmark3ComboBox = self.ui.landmark3ComboBox
        self.slideOpacity = self.ui.slideOpacity
        self.AdaptToBoundingBoxCheckBox = self.ui.AdaptToBoundingBoxCheckBox
        self.HidePlaneCheckBox = self.ui.HidePlaneCheckBox
        self.removePlaneButton = self.ui.removePlaneButton
        # connections
        self.addFiducialButton.connect("clicked()", self.addLandMarkClicked)
        self.landmark1ComboBox.connect(
            "currentIndexChanged(QString)", self.placePlaneClicked
        )
        self.landmark2ComboBox.connect(
            "currentIndexChanged(QString)", self.placePlaneClicked
        )
        self.landmark3ComboBox.connect(
            "currentIndexChanged(QString)", self.placePlaneClicked
        )
        self.slideOpacity.connect("valueChanged(double)", self.placePlaneClicked)
        self.AdaptToBoundingBoxCheckBox.connect("stateChanged(int)", self.onBBox)
        self.AdaptToBoundingBoxCheckBox.connect(
            "stateChanged(int)", self.placePlaneClicked
        )
        self.HidePlaneCheckBox.connect("stateChanged(int)", self.update)
        self.removePlaneButton.connect("clicked(bool)", self.onRemove)
        # fiducial list for the plane
        self.anglePlanes.updateLandmarkComboBox(self.fidlist, self.landmark1ComboBox)
        self.anglePlanes.updateLandmarkComboBox(self.fidlist, self.landmark2ComboBox)
        self.anglePlanes.updateLandmarkComboBox(self.fidlist, self.landmark3ComboBox)

    def PlaneIsDefined(self):
        landmarkIDs = (
            self.landmark1ComboBox.currentData,
            self.landmark2ComboBox.currentData,
            self.landmark3ComboBox.currentData,
        )

        if not all(landmarkIDs):
            return False

        if len(set(landmarkIDs)) != len(landmarkIDs):
            return False

        return True

    def onRemove(self):
        self.anglePlanes.RemoveManualPlane(self.id)

    def getFiducials(self):
        listCoord = list()

        coord = numpy.zeros(3)
        self.fidlist.GetNthFiducialPosition(
            int(self.landmark1ComboBox.currentIndex) - 1, coord
        )
        listCoord.append(coord)

        self.fidlist.GetNthFiducialPosition(
            int(self.landmark2ComboBox.currentIndex) - 1, coord
        )
        listCoord.append(coord)

        self.fidlist.GetNthFiducialPosition(
            int(self.landmark3ComboBox.currentIndex) - 1, coord
        )
        listCoord.append(coord)

        return listCoord

    def placePlaneClicked(self):
        self.anglePlanes.valueComboBox()
        self.update()

    def onBBox(self):
        self.anglePlanes.onComputeBox()
        self.update()

    def update(self):
        self.planeCollection = self.anglePlanes.planeCollection
        if self.PlaneIsDefined():
            if self.HidePlaneCheckBox.isChecked():
                self.normal = self.logic.planeLandmarks(
                    self.fidlist,
                    self.landmark1ComboBox.currentData,
                    self.landmark2ComboBox.currentData,
                    self.landmark3ComboBox.currentData,
                    self.normal,
                    self.AdaptToBoundingBoxCheckBox,
                    0,
                    self.planeCollection,
                    self.actor,
                )
            else:
                self.normal = self.logic.planeLandmarks(
                    self.fidlist,
                    self.landmark1ComboBox.currentData,
                    self.landmark2ComboBox.currentData,
                    self.landmark3ComboBox.currentData,
                    self.normal,
                    self.AdaptToBoundingBoxCheckBox,
                    self.slideOpacity.value,
                    self.planeCollection,
                    self.actor,
                )

    def addLandMarkClicked(self):
        print("Add landmarks")
        connectedModel = self.deps.getModel(self.fidlist)
        self.anglePlanes.inputModelSelector.setCurrentNode(connectedModel)
        self.anglePlanes.inputLandmarksSelector.setCurrentNode(self.fidlist)
        # Place landmarks in the 3D scene
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        selectionNode.SetActivePlaceNodeID(self.fidlist.GetID())
        # print selectionNode
        interactionNode = slicer.mrmlScene.GetNodeByID(
            "vtkMRMLInteractionNodeSingleton"
        )
        interactionNode.SetCurrentInteractionMode(1)
        # To select multiple points in the 3D view, we want to have to click
        # on the "place fiducial" button multiple times
        placeModePersistence = 0
        interactionNode.SetPlaceModePersistence(placeModePersistence)

    def remove(self):
        renderer = list()
        renderWindow = list()
        layoutManager = slicer.app.layoutManager()
        for i in range(0, layoutManager.threeDViewCount):
            threeDWidget = layoutManager.threeDWidget(i)
            threeDView = threeDWidget.threeDView()
            renderWindow.append(threeDView.renderWindow())
            renderers = renderWindow[i].GetRenderers()
            renderer.append(renderers.GetFirstRenderer())
            renderer[i].RemoveViewProp(self.actor)
            renderWindow[i].AddRenderer(renderer[i])
            renderer[i].Render()
        self.actor.RemoveAllObservers()
        self.actor = None


class AnglePlanesLogic(ScriptedLoadableModuleLogic):
    try:
        slicer.sys
    except:
        import sys

    def __init__(self):
        super().__init__()

        self.ColorNodeCorrespondence = {
            "Red": "vtkMRMLSliceNodeRed",
            "Yellow": "vtkMRMLSliceNodeYellow",
            "Green": "vtkMRMLSliceNodeGreen",
        }
        self.selectedFidList = None
        self.selectedModel = None

    def UpdateThreeDView(self, selectedFidReflID):
        print("--- UpdateThreeDView ---")

        if not self.selectedFidList:
            return
        if not self.selectedModel:
            return

        # activate all landmarks
        for fidList in slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsFiducialNode"):
            for idx in range(fidList.GetNumberOfControlPoints()):
                fidList.SetNthControlPointLocked(idx, False)

        # deactivate all landmarks in selected fidlist
        for idx in range(self.selectedFidList.GetNumberOfControlPoints()):
            self.selectedFidList.SetNthControlPointLocked(idx, True)

        # activate selected landmark in selected fidlist
        idx = self.selectedFidList.GetNthControlPointIndexByID(selectedFidReflID)
        self.selectedFidList.SetNthControlPointLocked(idx, False)

        displayNode = self.selectedModel.GetModelDisplayNode()
        displayNode.SetScalarVisibility(False)
        if selectedFidReflID != False:
            displayNode.SetScalarVisibility(True)

    def createIntermediateHardenModel(self, model):
        hardenModel = slicer.mrmlScene.GetNodesByName(
            "SurfaceRegistration_"
            + model.GetName()
            + "_hardenCopy_"
            + str(slicer.app.applicationPid())
        ).GetItemAsObject(0)
        if hardenModel is None:
            hardenModel = slicer.vtkMRMLModelNode()
        hardenPolyData = vtk.vtkPolyData()
        hardenPolyData.DeepCopy(model.GetPolyData())
        hardenModel.SetAndObservePolyData(hardenPolyData)
        hardenModel.SetName(
            "SurfaceRegistration_"
            + model.GetName()
            + "_hardenCopy_"
            + str(slicer.app.applicationPid())
        )
        if model.GetParentTransformNode():
            hardenModel.SetAndObserveTransformNodeID(
                model.GetParentTransformNode().GetID()
            )
        hardenModel.HideFromEditorsOn()
        slicer.mrmlScene.AddNode(hardenModel)
        logic = slicer.vtkSlicerTransformLogic()
        logic.hardenTransform(hardenModel)
        return hardenModel

    def onModelModified(self, obj, event):  # todo move to deps
        # recompute the harden model
        hardenModel = self.createIntermediateHardenModel(obj)
        obj.SetNodeReferenceID("hardenModel", hardenModel.GetID())
        # for each fiducial list
        list = slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsFiducialNode")
        end = list.GetNumberOfItems()
        for i in range(0, end):
            # If landmarks are projected on the modified model
            fidList = list.GetItemAsObject(i)
            if fidList.GetNodeReference("connectedModel") == obj:
                # replace the harden model with the new one
                fidList.SetNodeReferenceID("hardenModel", hardenModel.GetID())
                # reproject the fiducials on the new model
                landmarkDescription = self.decodeJSON(
                    fidList.GetAttribute("landmarkDescription")
                )
                for n in range(fidList.GetNumberOfMarkups()):
                    markupID = fidList.GetNthMarkupID(n)
                    if (
                        landmarkDescription[markupID]["projection"]["isProjected"]
                        == True
                    ):
                        hardenModel = fidList.GetNodeReference("hardenModel")
                        markupsIndex = fidList.GetNthControlPointIndexByID(markupID)
                        self.replaceLandmark(
                            hardenModel.GetPolyData(),
                            fidList,
                            markupsIndex,
                            landmarkDescription[markupID]["projection"][
                                "closestPointIndex"
                            ],
                        )
                    fidList.SetAttribute(
                        "landmarkDescription", self.encodeJSON(landmarkDescription)
                    )

    def ModelChanged(  # todo move to deps
        self, inputModelSelector, inputLandmarksSelector
    ):
        inputModel = inputModelSelector.currentNode()
        # if a Model Node is present
        if inputModel:
            self.selectedModel = inputModel
            hardenModel = self.createIntermediateHardenModel(inputModel)
            inputModel.SetNodeReferenceID("hardenModel", hardenModel.GetID())
            modelModifieTagEvent = inputModel.AddObserver(
                inputModel.TransformModifiedEvent, self.onModelModified
            )
            inputModel.SetAttribute(
                "modelModifieTagEvent",
                self.encodeJSON({"modelModifieTagEvent": modelModifieTagEvent}),
            )
            inputLandmarksSelector.setEnabled(True)
        # if no model is selected
        else:
            # Update the fiducial list selector
            inputLandmarksSelector.setCurrentNode(None)
            inputLandmarksSelector.setEnabled(False)

    def getMatrix(self, slice):
        # print "--- get Matrix ---"
        self.mat = slice.GetSliceToRAS()
        # print self.mat
        # Matrix with the elements of SliceToRAS
        m = numpy.matrix(
            [
                [
                    self.mat.GetElement(0, 0),
                    self.mat.GetElement(0, 1),
                    self.mat.GetElement(0, 2),
                    self.mat.GetElement(0, 3),
                ],
                [
                    self.mat.GetElement(1, 0),
                    self.mat.GetElement(1, 1),
                    self.mat.GetElement(1, 2),
                    self.mat.GetElement(1, 3),
                ],
                [
                    self.mat.GetElement(2, 0),
                    self.mat.GetElement(2, 1),
                    self.mat.GetElement(2, 2),
                    self.mat.GetElement(2, 3),
                ],
                [
                    self.mat.GetElement(3, 0),
                    self.mat.GetElement(3, 1),
                    self.mat.GetElement(3, 2),
                    self.mat.GetElement(3, 3),
                ],
            ]
        )
        # print m
        return m

    def defineNormal(self, matrix):
        # print "--- defineNormal ---"
        # Normal vector to the Red slice:
        n_vector = numpy.matrix([[0], [0], [1], [1]])

        # point on the Red slice:
        A = numpy.matrix([[0], [0], [0], [1]])

        normalVector = matrix * n_vector
        # print "n : \n", normalVector
        A = matrix * A

        normalVector1 = normalVector

        normalVector1[0] = normalVector[0] - A[0]
        normalVector1[1] = normalVector[1] - A[1]
        normalVector1[2] = normalVector[2] - A[2]

        # print normalVector1

        return normalVector1

    def getAngle(self, normalVect1, normalVect2):
        # print "--- getAngle ---"
        norm1 = sqrt(
            normalVect1[0] * normalVect1[0]
            + normalVect1[1] * normalVect1[1]
            + normalVect1[2] * normalVect1[2]
        )
        # print "norme 1: \n", norm1
        norm2 = sqrt(
            normalVect2[0] * normalVect2[0]
            + normalVect2[1] * normalVect2[1]
            + normalVect2[2] * normalVect2[2]
        )
        # print "norme 2: \n", norm2

        scalar_product = (
            normalVect1[0] * normalVect2[0]
            + normalVect1[1] * normalVect2[1]
            + normalVect1[2] * normalVect2[2]
        )
        # print "scalar product : \n", scalar_product

        angle = acos(scalar_product / (norm1 * norm2))

        # print "radian angle : ", angle

        angle_degree = angle * 180 / pi
        # print "Angle in degree", angle_degree

        norm1_RL = sqrt(
            normalVect1[1] * normalVect1[1] + normalVect1[2] * normalVect1[2]
        )
        # print "norme RL: \n", norm1_RL
        norm2_RL = sqrt(
            normalVect2[1] * normalVect2[1] + normalVect2[2] * normalVect2[2]
        )
        # print "norme RL: \n", norm2_RL

        if norm1_RL == 0 or norm2_RL == 0:
            self.angle_degre_RL = 0
            self.angle_degre_RL_comp = 0
        else:
            scalar_product_RL = (
                normalVect1[1] * normalVect2[1] + normalVect1[2] * normalVect2[2]
            )
            # print "scalar product : \n", scalar_product_RL
            inter = scalar_product_RL / (norm1_RL * norm2_RL)
            if inter >= [[0.99999]]:
                angleRL = 0
            else:
                angleRL = acos(inter)
            # print "radian angle : ", angleRL

            self.angle_degre_RL = angleRL * 180 / pi
            self.angle_degre_RL = round(self.angle_degre_RL, 2)
            # print self.angle_degre_RL
            self.angle_degre_RL_comp = 180 - self.angle_degre_RL

        norm1_SI = sqrt(
            normalVect1[0] * normalVect1[0] + normalVect1[1] * normalVect1[1]
        )
        # print "norme1_SI : \n", norm1_SI
        norm2_SI = sqrt(
            normalVect2[0] * normalVect2[0] + normalVect2[1] * normalVect2[1]
        )
        # print "norme2_SI : \n", norm2_SI

        if norm1_SI == 0 or norm2_SI == 0:
            self.angle_degre_SI = 0
            self.angle_degre_SI_comp = 0
        else:
            scalar_product_SI = (
                normalVect1[0] * normalVect2[0] + normalVect1[1] * normalVect2[1]
            )
            # print "scalar product_SI : \n", scalar_product_SI

            inter = scalar_product_SI / (norm1_SI * norm2_SI)
            if inter >= [[0.99999]]:
                angleSI = 0
            else:
                angleSI = acos(inter)
            # print "radian angle : ", angleSI

            self.angle_degre_SI = angleSI * 180 / pi
            self.angle_degre_SI = round(self.angle_degre_SI, 2)
            # print self.angle_degre_SI
            self.angle_degre_SI_comp = 180 - self.angle_degre_SI
            # print self.angle_degre_SI_comp

        norm1_AP = sqrt(
            normalVect1[0] * normalVect1[0] + normalVect1[2] * normalVect1[2]
        )
        # print "norme1_SI : \n", norm1_AP
        norm2_AP = sqrt(
            normalVect2[0] * normalVect2[0] + normalVect2[2] * normalVect2[2]
        )
        # print "norme2_SI : \n", norm2_AP

        if norm1_AP == 0 or norm2_AP == 0:
            self.angle_degre_AP = 0
            self.angle_degre_AP_comp = 0
        else:
            scalar_product_AP = (
                normalVect1[0] * normalVect2[0] + normalVect1[2] * normalVect2[2]
            )
            # print "scalar product_SI : \n", scalar_product_AP

            # print "VALUE :", scalar_product_AP/(norm1_AP*norm2_AP)
            inter = scalar_product_AP / (norm1_AP * norm2_AP)
            if inter >= [[0.99999]]:
                angleAP = 0
            else:
                angleAP = acos(inter)

            # print "radian angle : ", angleAP

            self.angle_degre_AP = angleAP * 180 / pi
            self.angle_degre_AP = round(self.angle_degre_AP, 2)
            # print self.angle_degre_AP
            self.angle_degre_AP_comp = 180 - self.angle_degre_AP

    def normalLandmarks(self, GA, GB):
        # print "--- normalLandmarks ---"
        Vn = numpy.matrix([[0], [0], [0]])
        Vn[0] = GA[1] * GB[2] - GA[2] * GB[1]
        Vn[1] = GA[2] * GB[0] - GA[0] * GB[2]
        Vn[2] = GA[0] * GB[1] - GA[1] * GB[0]

        # print "Vn = ",Vn

        norm_Vn = sqrt(Vn[0] * Vn[0] + Vn[1] * Vn[1] + Vn[2] * Vn[2])

        # print "norm_Vn = ",norm_Vn

        Normal = Vn / norm_Vn

        # print "N = ",Normal

        return Normal

    def planeLandmarks(
        self,
        fidList,
        landmark1ID,
        landmark2ID,
        landmark3ID,
        Normal,
        AdaptToBoundingBoxCheckBox,
        sliderOpacity,
        planeCollection,
        actor,
    ):
        # Limit the number of 3 landmarks to define a plane
        # Keep the coordinates of the landmarks

        if AdaptToBoundingBoxCheckBox.isChecked():
            slider = 10000
        else:
            slider = 1

        coord = numpy.zeros(3)
        landmark1Index = fidList.GetNthControlPointIndexByID(landmark1ID)
        fidList.GetNthFiducialPosition(landmark1Index, coord)
        # print "Landmark1Value: ", coord
        r1 = coord[0]
        a1 = coord[1]
        s1 = coord[2]
        landmark2Index = fidList.GetNthControlPointIndexByID(landmark2ID)
        fidList.GetNthFiducialPosition(landmark2Index, coord)
        # print "Landmark2Value: ", coord
        r2 = coord[0]
        a2 = coord[1]
        s2 = coord[2]
        landmark3Index = fidList.GetNthControlPointIndexByID(landmark3ID)
        fidList.GetNthFiducialPosition(landmark3Index, coord)
        # print "Landmark3Value: ", coord
        r3 = coord[0]
        a3 = coord[1]
        s3 = coord[2]

        points = vtk.vtkPoints()
        if points.GetNumberOfPoints() == 0:
            points.InsertNextPoint(r1, a1, s1)
            points.InsertNextPoint(r2, a2, s2)
            points.InsertNextPoint(r3, a3, s3)
        else:
            points.SetPoint(0, r1, a1, s1)
            points.SetPoint(1, r2, a2, s2)
            points.SetPoint(2, r3, a3, s3)
        # print "points ", points

        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)

        centerOfMass = vtk.vtkCenterOfMass()
        centerOfMass.SetInputData(polydata)
        centerOfMass.SetUseScalarsAsWeights(False)
        centerOfMass.Update()

        G = centerOfMass.GetCenter()

        # print "Center of mass = ",G

        A = (r1, a1, s1)
        B = (r2, a2, s2)
        C = (r3, a3, s3)

        # Vector GA
        GA = numpy.matrix([[0.0], [0.0], [0.0]])
        GA[0] = A[0] - G[0]
        GA[1] = A[1] - G[1]
        GA[2] = A[2] - G[2]

        # print "GA = ", GA

        # Vector BG
        GB = numpy.matrix([[0.0], [0.0], [0.0]])
        GB[0] = B[0] - G[0]
        GB[1] = B[1] - G[1]
        GB[2] = B[2] - G[2]

        # print "GB = ", GB

        # Vector CG
        GC = numpy.matrix([[0.0], [0.0], [0.0]])
        GC[0] = C[0] - G[0]
        GC[1] = C[1] - G[1]
        GC[2] = C[2] - G[2]

        # print "GC = ", GC

        normal = self.normalLandmarks(GA, GB)

        D = numpy.matrix([[0.0], [0.0], [0.0]])
        E = numpy.matrix([[0.0], [0.0], [0.0]])
        F = numpy.matrix([[0.0], [0.0], [0.0]])

        D[0] = slider * GA[0] + G[0]
        D[1] = slider * GA[1] + G[1]
        D[2] = slider * GA[2] + G[2]

        # print "Slider value : ", slider

        # print "D = ",D

        E[0] = slider * GB[0] + G[0]
        E[1] = slider * GB[1] + G[1]
        E[2] = slider * GB[2] + G[2]

        # print "E = ",E

        F[0] = slider * GC[0] + G[0]
        F[1] = slider * GC[1] + G[1]
        F[2] = slider * GC[2] + G[2]

        # print "F = ",F

        planeSource = vtk.vtkPlaneSource()
        planeSource.SetNormal(normal[0], normal[1], normal[2])

        planeSource.SetOrigin(D[0], D[1], D[2])
        planeSource.SetPoint1(E[0], E[1], E[2])
        planeSource.SetPoint2(F[0], F[1], F[2])

        planeSource.Update()

        if AdaptToBoundingBoxCheckBox.isChecked():
            clipper = vtk.vtkClipClosedSurface()
            clipper.SetClippingPlanes(planeCollection)
            clipper.SetInputData(planeSource.GetOutput())
            clipper.Update()
            plane = clipper.GetOutput()
        else:
            plane = planeSource.GetOutput()

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(plane)
        mapper.Update()

        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0, 0.4, 0.8)
        actor.GetProperty().SetOpacity(sliderOpacity)

        renderer = list()
        renderWindow = list()
        layoutManager = slicer.app.layoutManager()
        for i in range(0, layoutManager.threeDViewCount):
            threeDWidget = layoutManager.threeDWidget(i)
            threeDView = threeDWidget.threeDView()
            renderWindow.append(threeDView.renderWindow())
            renderers = renderWindow[i].GetRenderers()
            renderer.append(renderers.GetFirstRenderer())
            renderer[i].AddViewProp(actor)
            renderWindow[i].AddRenderer(renderer[i])
            renderer[i].Render()
            renderWindow[i].Render()
        return normal

    # def GetConnectedVertices(self, connectedVerticesIDList, polyData, pointID):
    #     # Return IDs of all the vertices that compose the first neighbor.
    #     cellList = vtk.vtkIdList()
    #     connectedVerticesIDList.InsertUniqueId(pointID)
    #     # Get cells that vertex 'pointID' belongs to
    #     polyData.GetPointCells(pointID, cellList)
    #     numberOfIds = cellList.GetNumberOfIds()
    #     for i in range(0, numberOfIds):
    #         # Get points which compose all cells
    #         pointIdList = vtk.vtkIdList()
    #         polyData.GetCellPoints(cellList.GetId(i), pointIdList)
    #         for j in range(0, pointIdList.GetNumberOfIds()):
    #             connectedVerticesIDList.InsertUniqueId(pointIdList.GetId(j))
    #     return connectedVerticesIDList

    # def addArrayFromIdList(self, connectedIdList, inputModelNode, arrayName):
    #     if not inputModelNode:
    #         return
    #     inputModelNodePolydata = inputModelNode.GetPolyData()
    #     pointData = inputModelNodePolydata.GetPointData()
    #     numberofIds = connectedIdList.GetNumberOfIds()
    #     hasArrayInt = pointData.HasArray(arrayName)
    #     if hasArrayInt == 1:  # ROI Array found
    #         pointData.RemoveArray(arrayName)
    #     arrayToAdd = vtk.vtkDoubleArray()
    #     arrayToAdd.SetName(arrayName)
    #     for i in range(0, inputModelNodePolydata.GetNumberOfPoints()):
    #         arrayToAdd.InsertNextValue(0.0)
    #     for i in range(0, numberofIds):
    #         arrayToAdd.SetValue(connectedIdList.GetId(i), 1.0)
    #     lut = vtk.vtkLookupTable()
    #     tableSize = 2
    #     lut.SetNumberOfTableValues(tableSize)
    #     lut.Build()
    #     displayNode = inputModelNode.GetDisplayNode()
    #     rgb = displayNode.GetColor()
    #     lut.SetTableValue(0, rgb[0], rgb[1], rgb[2], 1)
    #     lut.SetTableValue(1, 1.0, 0.0, 0.0, 1)
    #     arrayToAdd.SetLookupTable(lut)
    #     pointData.AddArray(arrayToAdd)
    #     inputModelNodePolydata.Modified()
    #     return True

    # def displayROI(self, inputModelNode, scalarName):
    #     PolyData = inputModelNode.GetPolyData()
    #     PolyData.Modified()
    #     displayNode = inputModelNode.GetModelDisplayNode()
    #     displayNode.SetScalarVisibility(False)
    #     disabledModify = displayNode.StartModify()
    #     displayNode.SetActiveScalarName(scalarName)
    #     displayNode.SetScalarVisibility(True)
    #     displayNode.EndModify(disabledModify)

    # def findROI(self, fidList):
    #     hardenModel = fidList.GetNodeReference("hardenModel")
    #     connectedModel = fidList.GetNodeReference("connectedModel")
    #     landmarkDescription = self.decodeJSON(
    #         fidList.GetAttribute("landmarkDescription"))
    #     arrayName = fidList.GetAttribute("arrayName")
    #     ROIPointListID = vtk.vtkIdList()
    #     for key, activeLandmarkState in landmarkDescription.items():
    #         tempROIPointListID = vtk.vtkIdList()
    #         if activeLandmarkState["ROIradius"] != 0:
    #             self.defineNeighbor(tempROIPointListID,
    #                                 hardenModel.GetPolyData(),
    #                                 activeLandmarkState["projection"][
    #                                     "closestPointIndex"],
    #                                 activeLandmarkState["ROIradius"])
    #         for j in range(0, tempROIPointListID.GetNumberOfIds()):
    #             ROIPointListID.InsertUniqueId(tempROIPointListID.GetId(j))
    #     listID = ROIPointListID
    #     self.addArrayFromIdList(listID, connectedModel, arrayName)
    #     self.displayROI(connectedModel, arrayName)
    #     return ROIPointListID

    def savePlanes(self, filename=None):
        tempDictionary = {}
        for key in self.ColorNodeCorrespondence:
            slice = slicer.util.getNode(self.ColorNodeCorrespondence[key])
            tempDictionary[key] = self.getMatrix(slice).tolist()
        if filename != "":
            fileObj = open(filename, "wb")
            pickle.dump(tempDictionary, fileObj)
            fileObj.close()

    def readPlanes(self, filename=None):
        if filename != "":
            fileObj = open(filename, "rb")
            tempDictionary = pickle.load(fileObj)
            for key in self.ColorNodeCorrespondence:
                node = slicer.mrmlScene.GetNodeByID(self.ColorNodeCorrespondence[key])
                matList = tempDictionary[key]
                matNode = node.GetSliceToRAS()
                for col in range(0, len(matList)):
                    for row in range(0, len(matList[col])):
                        matNode.SetElement(col, row, matList[col][row])
            fileObj.close()

    def warningMessage(self, message):
        messageBox = ctk.ctkMessageBox()
        messageBox.setWindowTitle(" /!\ WARNING /!\ ")
        messageBox.setIcon(messageBox.Warning)
        messageBox.setText(message)
        messageBox.setStandardButtons(messageBox.Ok)
        messageBox.exec_()

    def encodeJSON(self, input):
        encodedString = json.dumps(input)
        encodedString = encodedString.replace('"', "'")
        return encodedString

    def decodeJSON(self, input):
        if input:
            input = input.replace("'", '"')
            return json.loads(input)
        return None


class AnglePlanesTest(ScriptedLoadableModuleTest):
    def setUp(self):
        # reset the state - clear scene
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        # run all tests needed
        self.delayDisplay("Clear the scene")
        self.setUp()
        self.delayDisplay("Download and load datas")
        self.downloaddata()
        self.delayDisplay("Starting the tests")
        self.assertTrue(self.test_AnglePlanes())
        self.delayDisplay("All tests passed!")

    def downloaddata(self):
        import urllib.request, urllib.parse, urllib.error

        downloads = (
            (
                "http://slicer.kitware.com/midas3/download?items=213632",
                "01.vtk",
                slicer.util.loadModel,
            ),
            (
                "http://slicer.kitware.com/midas3/download?items=213633",
                "02.vtk",
                slicer.util.loadModel,
            ),
        )
        for url, name, loader in downloads:
            filePath = slicer.app.temporaryPath + "/" + name
            print(filePath)
            if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
                logging.info("Requesting download %s from %s...\n" % (name, url))
                urllib.request.urlretrieve(url, filePath)
            if loader:
                logging.info("Loading %s..." % (name,))
                loader(filePath)

        layoutManager = slicer.app.layoutManager()
        threeDWidget = layoutManager.threeDWidget(0)
        threeDView = threeDWidget.threeDView()
        threeDView.resetFocalPoint()

    def test_AnglePlanes(self):

        widget = slicer.modules.AnglePlanesWidget

        self.delayDisplay("Saving planes")
        widget.logic.savePlanes("test.p")

        self.delayDisplay("Loading planes")
        widget.logic.readPlanes("test.p")

        self.delayDisplay("Adding planes")

        widget.inputModelSelector.setCurrentNode(
            slicer.mrmlScene.GetNodesByName("01").GetItemAsObject(0)
        )
        movingMarkupsFiducial = slicer.vtkMRMLMarkupsFiducialNode()
        movingMarkupsFiducial.SetName("F1")
        slicer.mrmlScene.AddNode(movingMarkupsFiducial)
        widget.inputLandmarksSelector.setCurrentNode(movingMarkupsFiducial)
        widget.addNewPlane()
        plane1 = widget.planeControlsDictionary["Plane 1"]
        movingMarkupsFiducial.AddFiducial(8.08220491, -98.03022892, 93.12060543)
        widget.logic.onPointModifiedEvent(movingMarkupsFiducial, None)
        movingMarkupsFiducial.AddFiducial(-64.97482242, -26.20270453, 40.0195569)
        widget.logic.onPointModifiedEvent(movingMarkupsFiducial, None)
        movingMarkupsFiducial.AddFiducial(-81.14900734, -108.26332837, 121.16330592)
        widget.logic.onPointModifiedEvent(movingMarkupsFiducial, None)
        plane1.landmark1ComboBox.setCurrentIndex(0)
        plane1.landmark2ComboBox.setCurrentIndex(1)
        plane1.landmark3ComboBox.setCurrentIndex(2)

        widget.inputModelSelector.setCurrentNode(
            slicer.mrmlScene.GetNodesByName("02").GetItemAsObject(0)
        )
        movingMarkupsFiducial = slicer.vtkMRMLMarkupsFiducialNode()
        movingMarkupsFiducial.SetName("F2")
        slicer.mrmlScene.AddNode(movingMarkupsFiducial)
        widget.inputLandmarksSelector.setCurrentNode(movingMarkupsFiducial)
        widget.addNewPlane()
        plane2 = widget.planeControlsDictionary["Plane 2"]
        movingMarkupsFiducial.AddFiducial(-39.70435272, -97.08191652, 91.88711809)
        widget.logic.onPointModifiedEvent(movingMarkupsFiducial, None)
        movingMarkupsFiducial.AddFiducial(-96.02709079, -18.26063616, 21.47774342)
        widget.logic.onPointModifiedEvent(movingMarkupsFiducial, None)
        movingMarkupsFiducial.AddFiducial(-127.93278815, -106.45001448, 92.35628815)
        widget.logic.onPointModifiedEvent(movingMarkupsFiducial, None)
        plane2.landmark1ComboBox.setCurrentIndex(0)
        plane2.landmark2ComboBox.setCurrentIndex(1)
        plane2.landmark3ComboBox.setCurrentIndex(2)

        self.delayDisplay("Hide Planes")
        plane1.HidePlaneCheckBox.setChecked(True)
        plane2.HidePlaneCheckBox.setChecked(True)

        self.delayDisplay("Adapt on bounding box")
        plane1.HidePlaneCheckBox.setChecked(False)
        plane2.HidePlaneCheckBox.setChecked(False)
        plane1.AdaptToBoundingBoxCheckBox.setChecked(True)
        plane2.AdaptToBoundingBoxCheckBox.setChecked(True)

        self.delayDisplay("Selecting planes")
        widget.planeComboBox1.setCurrentIndex(4)
        widget.planeComboBox2.setCurrentIndex(4)

        self.delayDisplay("Calculating angle")
        widget.angleValue()

        test = (
            widget.logic.angle_degre_RL != 03.55
            or widget.logic.angle_degre_RL_comp != 176.45
            or widget.logic.angle_degre_SI != 17.91
            or widget.logic.angle_degre_SI_comp != 162.09
            or widget.logic.angle_degre_AP != 16.34
            or widget.logic.angle_degre_AP_comp != 163.66
        )

        self.delayDisplay("Testing angles")
        if test:

            print("", "Angle", "Complementary")
            print(
                "R-L-View",
                widget.logic.angle_degre_RL,
                widget.logic.angle_degre_RL_comp,
            )
            print(
                "S-I-View",
                widget.logic.angle_degre_SI,
                widget.logic.angle_degre_SI_comp,
            )
            print(
                "A-P-View",
                widget.logic.angle_degre_AP,
                widget.logic.angle_degre_AP_comp,
            )
            self.delayDisplay("Test Failure!")
            return False

        else:
            self.delayDisplay("Test passed!")
            return True
