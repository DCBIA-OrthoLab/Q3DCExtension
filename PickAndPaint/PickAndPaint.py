from __future__ import print_function

import json
import logging
import os
import time

import ctk
import numpy
import qt
import vtk

import slicer
from slicer.ScriptedLoadableModule import *


class PickAndPaint(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Pick 'n Paint "
        parent.categories = ["Quantification"]
        parent.dependencies = ["DependantMarkups"]
        parent.contributors = [
            "Lucie Macron (University of Michigan)",
            "Jean-Baptiste Vimort (University of Michigan)",
            "James Hoctor (Kitware Inc.)",
        ]
        parent.helpText = """
        The Pick 'n Paint tool allows users to select ROIs on a
        reference model and to propagate them over different time point
        models.
        """
        parent.acknowledgementText = """
        This work was supported by the National Institute of Dental and
        Craniofacial Research and the National Institute of Biomedical
        Imaging and Bioengineering of the National Institutes of Health
        under Award Number R01DE024450.
        """
        self.parent = parent


class PickAndPaintWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        logging.debug("-------Pick And Paint Widget Setup--------")
        ScriptedLoadableModuleWidget.setup(self)
        # reload the logic if there is any change
        self.logic = PickAndPaintLogic(self)
        self.interactionNode = slicer.mrmlScene.GetNodeByID(
            "vtkMRMLInteractionNodeSingleton"
        )

        # UI setup
        loader = qt.QUiLoader()
        moduleName = "PickAndPaint"
        scriptedModulesPath = eval("slicer.modules.%s.path" % moduleName.lower())
        scriptedModulesPath = os.path.dirname(scriptedModulesPath)
        path = os.path.join(
            scriptedModulesPath, "Resources", "UI", "%s.ui" % moduleName
        )

        qfile = qt.QFile(path)
        qfile.open(qt.QFile.ReadOnly)
        widget = loader.load(qfile, self.parent)
        self.layout = self.parent.layout()
        self.widget = widget
        self.layout.addWidget(widget)

        # this attribute is useful for Longitudinal quantification extension
        self.inputModelLabel = self.logic.get("inputModelLabel")
        # this attribute is useful for Longitudinal quantification extension
        self.inputLandmarksLabel = self.logic.get("inputLandmarksLabel")
        self.inputModelSelector = self.logic.get("inputModelSelector")
        self.inputModelSelector.setMRMLScene(slicer.mrmlScene)
        self.inputLandmarksSelector = self.logic.get("inputLandmarksSelector")
        self.inputLandmarksSelector.setMRMLScene(slicer.mrmlScene)
        self.inputLandmarksSelector.addEnabled = True
        # The "enable" property seems to not be imported from the .ui
        self.inputLandmarksSelector.setEnabled(False)
        self.loadLandmarksOnSurfacCheckBox = self.logic.get(
            "loadLandmarksOnSurfacCheckBox"
        )
        self.landmarksScaleWidget = self.logic.get("landmarksScaleWidget")
        self.addLandmarksButton = self.logic.get("addLandmarksButton")
        self.surfaceDeplacementCheckBox = self.logic.get("surfaceDeplacementCheckBox")
        self.landmarkComboBox = self.logic.get("landmarkComboBox")
        self.radiusDefinitionWidget = self.logic.get("radiusDefinitionWidget")
        self.cleanerButton = self.logic.get("cleanerButton")
        self.correspondentShapes = self.logic.get("correspondentShapes")
        self.nonCorrespondentShapes = self.logic.get("nonCorrespondentShapes")
        self.propagationInputComboBox = self.logic.get("propagationInputComboBox")
        self.propagationInputComboBox.setMRMLScene(slicer.mrmlScene)
        self.propagateButton = self.logic.get("propagateButton")

        # ------------------------------------------------------------------------------------
        #                                   CONNECTIONS
        # ------------------------------------------------------------------------------------
        self.inputModelSelector.connect(
            "currentNodeChanged(vtkMRMLNode*)", self.onModelChanged
        )
        self.inputLandmarksSelector.connect(
            "currentNodeChanged(vtkMRMLNode*)", self.onLandmarksChanged
        )
        self.addLandmarksButton.connect("clicked()", self.onAddButton)
        self.cleanerButton.connect("clicked()", self.onCleanButton)
        self.landmarksScaleWidget.connect(
            "valueChanged(double)", self.onLandmarksScaleChanged
        )
        self.surfaceDeplacementCheckBox.connect(
            "stateChanged(int)", self.onSurfaceDeplacementStateChanged
        )
        self.landmarkComboBox.connect(
            "currentIndexChanged(QString)", self.onLandmarkComboBoxChanged
        )
        self.radiusDefinitionWidget.connect(
            "valueChanged(double)", self.onRadiusValueChanged
        )
        self.propagationInputComboBox.connect(
            "checkedNodesChanged()", self.onPropagationInputComboBoxCheckedNodesChanged
        )
        self.propagateButton.connect("clicked()", self.onPropagateButton)

        slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndCloseEvent, self.onCloseScene)

    def enter(self):
        logging.debug("------- in function: enter --------")
        # See Slicer/Base/QTGUI/qSlicerAbstractModuleWidget.h for an
        # explanation of when this is called.
        model = self.inputModelSelector.currentNode()
        fidlist = self.inputLandmarksSelector.currentNode()

        if fidlist:
            if fidlist.GetAttribute("connectedModelID") != model.GetID():
                self.inputModelSelector.setCurrentNode(None)
                self.inputLandmarksSelector.setCurrentNode(None)
                self.landmarkComboBox.clear()
        self.UpdateInterface()

        # Checking the names of the fiducials
        list_ = slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsFiducialNode")
        end = list_.GetNumberOfItems()
        for i in range(end):
            fidList = list_.GetItemAsObject(i)
            landmarkDescription = self.logic.decodeJSON(
                fidList.GetAttribute("landmarkDescription")
            )
            if landmarkDescription:
                for n in range(fidList.GetNumberOfMarkups()):
                    markupID = fidList.GetNthMarkupID(n)
                    markupLabel = fidList.GetNthMarkupLabel(n)
                    landmarkDescription[markupID]["landmarkLabel"] = markupLabel
                fidList.SetAttribute(
                    "landmarkDescription", self.logic.encodeJSON(landmarkDescription)
                )

    def onCloseScene(self, obj, event):
        list_ = slicer.mrmlScene.GetNodesByClass("vtkMRMLModelNode")
        end = list_.GetNumberOfItems()
        for i in range(end):
            model = list_.GetItemAsObject(i)
            hardenModel = slicer.mrmlScene.GetNodesByName(
                model.GetName()
            ).GetItemAsObject(0)
            slicer.mrmlScene.RemoveNode(hardenModel)
        self.radiusDefinitionWidget.value = 0.0
        self.landmarksScaleWidget.value = 2.0
        self.landmarkComboBox.clear()
        self.logic.selectedFidList = None
        self.logic.selectedModel = None

    def UpdateInterface(self):
        if not self.logic.selectedModel:
            return
        activeInput = self.logic.selectedModel
        if not self.logic.selectedFidList:
            return
        fidList = self.logic.selectedFidList
        selectedFidReflID = self.logic.findIDFromLabel(
            fidList, self.landmarkComboBox.currentText
        )

        if activeInput:
            # Update values on widgets.
            landmarkDescription = self.logic.decodeJSON(
                fidList.GetAttribute("landmarkDescription")
            )
            if landmarkDescription and selectedFidReflID:
                activeDictLandmarkValue = landmarkDescription[selectedFidReflID]
                self.radiusDefinitionWidget.value = activeDictLandmarkValue["ROIradius"]
                if activeDictLandmarkValue["projection"]["isProjected"]:
                    self.surfaceDeplacementCheckBox.setChecked(True)
                else:
                    self.surfaceDeplacementCheckBox.setChecked(False)
            else:
                self.radiusDefinitionWidget.value = 0.0
            self.logic.UpdateThreeDView(self.landmarkComboBox.currentText)

    def onModelChanged(self):
        logging.debug("-------Model Changed--------")
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

    def onLandmarksChanged(self):
        logging.debug("-------Landmarks Changed--------")
        if self.inputModelSelector.currentNode():
            self.logic.FidList = self.inputLandmarksSelector.currentNode()
            self.logic.selectedFidList = self.inputLandmarksSelector.currentNode()
            self.logic.selectedModel = self.inputModelSelector.currentNode()
            if self.inputLandmarksSelector.currentNode():
                onSurface = self.loadLandmarksOnSurfacCheckBox.isChecked()
                self.logic.connectLandmarks(
                    self.inputModelSelector, self.inputLandmarksSelector, onSurface
                )
            else:
                self.landmarkComboBox.clear()

    def onAddButton(self):
        # Add fiducial on the scene.
        # If no input model selected, the addition of fiducial shouldn't be possible.
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        if self.logic.selectedModel:
            if self.logic.selectedFidList:
                selectionNode.SetActivePlaceNodeID(self.logic.selectedFidList.GetID())
                self.interactionNode.SetCurrentInteractionMode(1)
            else:
                self.logic.warningMessage("Please select a fiducial list")
        else:
            self.logic.warningMessage("Please select a model")

    def onLandmarksScaleChanged(self):
        if not self.logic.selectedFidList:
            self.logic.warningMessage("Please select a fiducial list")
            return
        logging.debug("------------Landmark scaled change-----------")
        displayFiducialNode = self.logic.selectedFidList.GetMarkupsDisplayNode()
        disabledModify = displayFiducialNode.StartModify()
        displayFiducialNode.SetGlyphScale(self.landmarksScaleWidget.value)
        displayFiducialNode.SetTextScale(self.landmarksScaleWidget.value)
        displayFiducialNode.EndModify(disabledModify)

    def onSurfaceDeplacementStateChanged(self):
        activeInput = self.logic.selectedModel
        if not activeInput:
            return
        fidList = self.logic.selectedFidList
        if not fidList:
            return
        # The following case can occur if a new MarkupsFiducial is generated to hold new
        # landmarks. The list will start empty and the landmark combo box will hold nothing.
        # In this case there is no need to continue with this routine.
        if self.landmarkComboBox.currentText == "":
            return
        selectedFidReflID = self.logic.findIDFromLabel(
            fidList, self.landmarkComboBox.currentText
        )
        isOnSurface = self.surfaceDeplacementCheckBox.isChecked()
        landmarkDescription = self.logic.decodeJSON(
            fidList.GetAttribute("landmarkDescription")
        )
        if isOnSurface:
            hardenModel = slicer.app.mrmlScene().GetNodeByID(
                fidList.GetAttribute("hardenModelID")
            )
            landmarkDescription[selectedFidReflID]["projection"]["isProjected"] = True
            landmarkDescription[selectedFidReflID]["projection"][
                "closestPointIndex"
            ] = self.logic.projectOnSurface(hardenModel, fidList, selectedFidReflID)
        else:
            landmarkDescription[selectedFidReflID]["projection"]["isProjected"] = False
            landmarkDescription[selectedFidReflID]["projection"][
                "closestPointIndex"
            ] = None
            landmarkDescription[selectedFidReflID]["ROIradius"] = 0
        fidList.SetAttribute(
            "landmarkDescription", self.logic.encodeJSON(landmarkDescription)
        )

    def onLandmarkComboBoxChanged(self):
        logging.debug("-------- ComboBox changement --------")
        self.UpdateInterface()

    def onRadiusValueChanged(self):
        logging.debug("--------- ROI radius modification ----------")
        fidList = self.logic.selectedFidList
        if not fidList:
            return
        selectedFidReflID = self.logic.findIDFromLabel(
            fidList, self.landmarkComboBox.currentText
        )
        if selectedFidReflID:
            landmarkDescription = self.logic.decodeJSON(
                fidList.GetAttribute("landmarkDescription")
            )
            activeLandmarkState = landmarkDescription[selectedFidReflID]
            activeLandmarkState["ROIradius"] = self.radiusDefinitionWidget.value
            if not activeLandmarkState["projection"]["isProjected"]:
                self.surfaceDeplacementCheckBox.setChecked(True)
                hardenModel = slicer.app.mrmlScene().GetNodeByID(
                    fidList.GetAttribute("hardenModelID")
                )
                landmarkDescription[selectedFidReflID]["projection"][
                    "isProjected"
                ] = True
                landmarkDescription[selectedFidReflID]["projection"][
                    "closestPointIndex"
                ] = self.logic.projectOnSurface(hardenModel, fidList, selectedFidReflID)
            fidList.SetAttribute(
                "landmarkDescription", self.logic.encodeJSON(landmarkDescription)
            )
            self.logic.findROI(fidList)

    def onCleanButton(self):
        messageBox = ctk.ctkMessageBox()
        messageBox.setWindowTitle(" /!\ WARNING /!\ ")
        messageBox.setIcon(messageBox.Warning)
        messageBox.setText("Your model is about to be modified")
        messageBox.setInformativeText("Do you want to continue?")
        messageBox.setStandardButtons(messageBox.No | messageBox.Yes)
        choice = messageBox.exec_()
        if choice == messageBox.Yes:
            selectedLandmark = self.landmarkComboBox.currentText
            self.logic.cleanMesh(selectedLandmark)
            self.onRadiusValueChanged()
        else:
            messageBox.setText(" Region not modified")
            messageBox.setStandardButtons(messageBox.Ok)
            messageBox.setInformativeText("")
            messageBox.exec_()

    def onPropagationInputComboBoxCheckedNodesChanged(self):
        if not self.inputModelSelector.currentNode():
            return
        if not self.inputLandmarksSelector.currentNode():
            return
        modelToPropList = self.propagationInputComboBox.checkedNodes()
        finalList = list()
        for model in modelToPropList:
            if model.GetID() != self.inputModelSelector.currentNode().GetID():
                finalList.append(model.GetID())
        self.inputLandmarksSelector.currentNode().SetAttribute(
            "modelToPropList", self.logic.encodeJSON({"modelToPropList": finalList})
        )

    def onPropagateButton(self):
        logging.debug(
            " ------------------------------------ onPropagateButton -------------------------------------- "
        )
        if not self.inputModelSelector.currentNode():
            return
        if not self.inputLandmarksSelector.currentNode():
            return
        model = self.inputModelSelector.currentNode()
        self.logic.cleanerAndTriangleFilter(model)
        hardenModel = self.logic.createIntermediateHardenModel(model)
        model.SetAttribute("hardenModelID", hardenModel.GetID())
        fidList = self.inputLandmarksSelector.currentNode()

        decoded_json = self.logic.decodeJSON(fidList.GetAttribute("modelToPropList"))
        modelToPropagateList = []
        if decoded_json is not None:
            modelToPropagateList = decoded_json["modelToPropList"]

        for IDmodelToPropagate in modelToPropagateList:
            modelToPropagate = slicer.mrmlScene.GetNodeByID(IDmodelToPropagate)
            isClean = self.logic.decodeJSON(fidList.GetAttribute("isClean"))
            if isClean:
                if not isClean["isClean"]:
                    self.logic.cleanerAndTriangleFilter(modelToPropagate)
                    hardenModel = self.logic.createIntermediateHardenModel(
                        modelToPropagate
                    )
                    modelToPropagate.SetAttribute("hardenModelID", hardenModel.GetID())
            else:
                self.logic.cleanerAndTriangleFilter(modelToPropagate)
                hardenModel = self.logic.createIntermediateHardenModel(modelToPropagate)
                modelToPropagate.SetAttribute("hardenModelID", hardenModel.GetID())
            if self.correspondentShapes.isChecked():
                fidList.SetAttribute("typeOfPropagation", "correspondentShapes")
                self.logic.propagateCorrespondent(fidList, model, modelToPropagate)
            else:
                fidList.SetAttribute("typeOfPropagation", "nonCorrespondentShapes")
                self.logic.propagateNonCorrespondent(fidList, modelToPropagate)
        self.UpdateInterface()


class PickAndPaintLogic(ScriptedLoadableModuleLogic):
    ROI_ARRAY_NAME = "{0}_{1}_ROI"

    def __init__(self, interface):
        self.selectedModel = None
        self.selectedFidList = None
        self.interface = interface

    def get(self, objectName):
        return self.findWidget(self.interface.widget, objectName)

    def findWidget(self, widget, objectName):
        if widget.objectName == objectName:
            return widget
        else:
            for w in widget.children():
                resulting_widget = self.findWidget(w, objectName)
                if resulting_widget:
                    return resulting_widget
            return None

    def UpdateThreeDView(self, landmarkLabel):
        # Update the 3D view on Slicer
        if not self.selectedFidList:
            return
        if not self.selectedModel:
            return
        logging.debug("UpdateThreeDView")
        active = self.selectedFidList
        # deactivate all landmarks
        list_ = slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsFiducialNode")
        end = list_.GetNumberOfItems()
        selectedFidReflID = self.findIDFromLabel(active, landmarkLabel)
        for i in range(end):
            fidList = list_.GetItemAsObject(i)
            landmarkDescription = self.decodeJSON(
                fidList.GetAttribute("landmarkDescription")
            )
            if not landmarkDescription:
                # Not a PickAndPaint markup fiducial list
                continue
            for key in landmarkDescription.keys():
                markupsIndex = fidList.GetNthControlPointIndexByID(key)
                if key != selectedFidReflID:
                    fidList.SetNthMarkupLocked(markupsIndex, True)
                else:
                    fidList.SetNthMarkupLocked(markupsIndex, False)
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

    def onModelModified(self, obj, event):
        # recompute the harden model
        hardenModel = self.createIntermediateHardenModel(obj)
        obj.SetAttribute("hardenModelID", hardenModel.GetID())
        # for each fiducial list
        list_ = slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsFiducialNode")
        end = list_.GetNumberOfItems()
        for i in range(end):
            # If landmarks are projected on the modified model
            fidList = list_.GetItemAsObject(i)
            if fidList.GetAttribute("connectedModelID"):
                if fidList.GetAttribute("connectedModelID") == obj.GetID():
                    # replace the harden model with the new one
                    fidList.SetAttribute("hardenModelID", hardenModel.GetID())
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
                            hardenModel = slicer.app.mrmlScene().GetNodeByID(
                                fidList.GetAttribute("hardenModelID")
                            )
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

    def ModelChanged(self, inputModelSelector, inputLandmarksSelector):
        inputModel = inputModelSelector.currentNode()
        # if a Model Node is present
        if inputModel:
            self.selectedModel = inputModel
            hardenModel = self.createIntermediateHardenModel(inputModel)
            inputModel.SetAttribute("hardenModelID", hardenModel.GetID())
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

    def isUnderTransform(self, markups):
        if markups.GetParentTransformNode():
            messageBox = ctk.ctkMessageBox()
            messageBox.setWindowTitle(" /!\ WARNING /!\ ")
            messageBox.setIcon(messageBox.Warning)
            messageBox.setText(
                "Your Markup Fiducial Node is currently modified by a transform,"
                "if you choose to continue the program will apply the transform"
                "before doing anything else!"
            )
            messageBox.setInformativeText("Do you want to continue?")
            messageBox.setStandardButtons(messageBox.No | messageBox.Yes)
            choice = messageBox.exec_()
            if choice == messageBox.Yes:
                logic = slicer.vtkSlicerTransformLogic()
                logic.hardenTransform(markups)
                return False
            else:
                messageBox.setText(" Node not modified")
                messageBox.setStandardButtons(messageBox.Ok)
                messageBox.setInformativeText("")
                messageBox.exec_()
                return True
        else:
            return False

    def connectedModelChangement(self):
        messageBox = ctk.ctkMessageBox()
        messageBox.setWindowTitle(" /!\ WARNING /!\ ")
        messageBox.setIcon(messageBox.Warning)
        messageBox.setText(
            "The Markup Fiducial Node selected is curently projected on an"
            "other model, if you chose to continue the fiducials will be  "
            "reprojected, and this could impact the functioning of other modules"
        )
        messageBox.setInformativeText("Do you want to continue?")
        messageBox.setStandardButtons(messageBox.No | messageBox.Yes)
        choice = messageBox.exec_()
        if choice == messageBox.Yes:
            return True
        else:
            messageBox.setText(" Node not modified")
            messageBox.setStandardButtons(messageBox.Ok)
            messageBox.setInformativeText("")
            messageBox.exec_()
            return False

    def createNewDataStructure(self, landmarks, model, onSurface):
        landmarks.SetAttribute("connectedModelID", model.GetID())
        landmarks.SetAttribute("hardenModelID", model.GetAttribute("hardenModelID"))
        landmarkDescription = dict()
        for n in range(landmarks.GetNumberOfMarkups()):
            markupID = landmarks.GetNthMarkupID(n)
            landmarkDescription[markupID] = dict()
            landmarkLabel = landmarks.GetNthMarkupLabel(n)
            landmarkDescription[markupID]["landmarkLabel"] = landmarkLabel
            landmarkDescription[markupID]["ROIradius"] = 0
            landmarkDescription[markupID]["projection"] = dict()
            if onSurface:
                landmarkDescription[markupID]["projection"]["isProjected"] = True
                hardenModel = slicer.app.mrmlScene().GetNodeByID(
                    landmarks.GetAttribute("hardenModelID")
                )
                landmarkDescription[markupID]["projection"][
                    "closestPointIndex"
                ] = self.projectOnSurface(hardenModel, landmarks, markupID)
            else:
                landmarkDescription[markupID]["projection"]["isProjected"] = False
                landmarkDescription[markupID]["projection"]["closestPointIndex"] = None
            landmarkDescription[markupID]["midPoint"] = dict()
            landmarkDescription[markupID]["midPoint"]["definedByThisMarkup"] = []
            landmarkDescription[markupID]["midPoint"]["isMidPoint"] = False
            landmarkDescription[markupID]["midPoint"]["Point1"] = None
            landmarkDescription[markupID]["midPoint"]["Point2"] = None
        landmarks.SetAttribute(
            "landmarkDescription", self.encodeJSON(landmarkDescription)
        )
        planeDescription = dict()
        landmarks.SetAttribute("planeDescription", self.encodeJSON(planeDescription))
        landmarks.SetAttribute("isClean", self.encodeJSON({"isClean": False}))
        landmarks.SetAttribute("lastTransformID", None)
        landmarks.SetAttribute(
            "arrayName",
            self.ROI_ARRAY_NAME.format(model.GetName(), landmarks.GetName()),
        )
        landmarks.SetAttribute("arrayPartNames", self.encodeJSON([]))

    def changementOfConnectedModel(self, landmarks, model, onSurface):
        landmarks.SetAttribute("connectedModelID", model.GetID())
        landmarks.SetAttribute("hardenModelID", model.GetAttribute("hardenModelID"))
        landmarkDescription = self.decodeJSON(
            landmarks.GetAttribute("landmarkDescription")
        )
        for n in range(landmarks.GetNumberOfMarkups()):
            markupID = landmarks.GetNthMarkupID(n)
            if onSurface:
                if landmarkDescription[markupID]["projection"]["isProjected"] == True:
                    hardenModel = slicer.app.mrmlScene().GetNodeByID(
                        landmarks.GetAttribute("hardenModelID")
                    )
                    landmarkDescription[markupID]["projection"][
                        "closestPointIndex"
                    ] = self.projectOnSurface(hardenModel, landmarks, markupID)
            else:
                landmarkDescription[markupID]["projection"]["isProjected"] = False
                landmarkDescription[markupID]["projection"]["closestPointIndex"] = None
            landmarks.SetAttribute(
                "landmarkDescription", self.encodeJSON(landmarkDescription)
            )
        landmarks.SetAttribute("isClean", self.encodeJSON({"isClean": False}))

    def connectLandmarks(self, modelSelector, landmarkSelector, onSurface):
        model = modelSelector.currentNode()
        landmarks = landmarkSelector.currentNode()
        self.selectedFidList = landmarks
        self.selectedModel = model
        if not (model and landmarks):
            return

        if self.isUnderTransform(landmarks):
            landmarkSelector.setCurrentNode(None)
            return
        connectedModelID = landmarks.GetAttribute("connectedModelID")
        try:
            tag = self.decodeJSON(landmarks.GetAttribute("PointAddedEventTag"))
            landmarks.RemoveObserver(tag["PointAddedEventTag"])
            logging.debug("PointAddedEvent observers removed!")
        except:
            pass
        try:
            tag = self.decodeJSON(landmarks.GetAttribute("PointModifiedEventTag"))
            landmarks.RemoveObserver(tag["PointModifiedEventTag"])
            logging.debug("PointModifiedEvent observers removed!")
        except:
            pass
        try:
            tag = self.decodeJSON(landmarks.GetAttribute("PointRemovedEventTag"))
            landmarks.RemoveObserver(tag["PointRemovedEventTag"])
            logging.debug("PointRemovedEvent observers removed!")
        except:
            pass
        if connectedModelID:
            if connectedModelID != model.GetID():
                if self.connectedModelChangement():
                    self.changementOfConnectedModel(landmarks, model, onSurface)
                else:
                    landmarkSelector.setCurrentNode(None)
                    return
            else:
                landmarks.SetAttribute(
                    "hardenModelID", model.GetAttribute("hardenModelID")
                )
        # creation of the data structure
        else:
            self.createNewDataStructure(landmarks, model, onSurface)
        # update of the landmark Combo Box
        self.updateLandmarkComboBox(landmarks)
        # adding of listeners
        PointAddedEventTag = landmarks.AddObserver(
            landmarks.PointAddedEvent, self.onPointAddedEvent
        )
        landmarks.SetAttribute(
            "PointAddedEventTag",
            self.encodeJSON({"PointAddedEventTag": PointAddedEventTag}),
        )
        PointModifiedEventTag = landmarks.AddObserver(
            landmarks.PointModifiedEvent, self.onPointModifiedEvent
        )
        landmarks.SetAttribute(
            "PointModifiedEventTag",
            self.encodeJSON({"PointModifiedEventTag": PointModifiedEventTag}),
        )
        PointRemovedEventTag = landmarks.AddObserver(
            landmarks.PointRemovedEvent, self.onPointRemovedEvent
        )
        landmarks.SetAttribute(
            "PointRemovedEventTag",
            self.encodeJSON({"PointRemovedEventTag": PointRemovedEventTag}),
        )

    # Called when a landmark is added on a model
    def onPointAddedEvent(self, obj, event):
        logging.debug("------markup adding-------")
        landmarkDescription = self.decodeJSON(obj.GetAttribute("landmarkDescription"))
        numOfMarkups = obj.GetNumberOfMarkups()
        # because every time a new node is added, its index is the last one on the list:
        markupID = obj.GetNthMarkupID(numOfMarkups - 1)
        landmarkDescription[markupID] = dict()
        landmarkLabel = obj.GetNthMarkupLabel(numOfMarkups - 1)
        landmarkDescription[markupID]["landmarkLabel"] = landmarkLabel
        landmarkDescription[markupID]["ROIradius"] = 0
        landmarkDescription[markupID]["projection"] = dict()
        landmarkDescription[markupID]["projection"]["isProjected"] = True
        # The landmark will be projected by onPointModifiedEvent
        landmarkDescription[markupID]["midPoint"] = dict()
        landmarkDescription[markupID]["midPoint"]["definedByThisMarkup"] = list()
        landmarkDescription[markupID]["midPoint"]["isMidPoint"] = False
        landmarkDescription[markupID]["midPoint"]["Point1"] = None
        landmarkDescription[markupID]["midPoint"]["Point2"] = None
        obj.SetAttribute("landmarkDescription", self.encodeJSON(landmarkDescription))
        self.interface.landmarkComboBox.addItem(landmarkLabel)
        self.interface.landmarkComboBox.setCurrentIndex(
            self.interface.landmarkComboBox.count - 1
        )
        self.interface.UpdateInterface()
        qt.QTimer.singleShot(0, lambda: self.onPointModifiedEvent(obj, None))

    def calculateMidPointCoord(self, fidList, landmark1ID, landmark2ID):
        """Set the midpoint when you know the the mrml nodes"""
        landmark1Index = fidList.GetNthControlPointIndexByID(landmark1ID)
        landmark2Index = fidList.GetNthControlPointIndexByID(landmark2ID)
        coord1 = [-1, -1, -1]
        coord2 = [-1, -1, -1]
        fidList.GetNthFiducialPosition(landmark1Index, coord1)
        fidList.GetNthFiducialPosition(landmark2Index, coord2)
        midCoord = [-1, -1, -1]
        midCoord[0] = (coord1[0] + coord2[0]) / 2
        midCoord[1] = (coord1[1] + coord2[1]) / 2
        midCoord[2] = (coord1[2] + coord2[2]) / 2
        return midCoord

    def updateMidPoint(self, fidList, landmarkID):
        landmarkDescription = self.decodeJSON(
            fidList.GetAttribute("landmarkDescription")
        )
        for midPointID in landmarkDescription[landmarkID]["midPoint"][
            "definedByThisMarkup"
        ]:
            if landmarkDescription[midPointID]["midPoint"]["isMidPoint"]:
                landmark1ID = landmarkDescription[midPointID]["midPoint"]["Point1"]
                landmark2ID = landmarkDescription[midPointID]["midPoint"]["Point2"]
                coord = self.calculateMidPointCoord(fidList, landmark1ID, landmark2ID)
                index = fidList.GetNthControlPointIndexByID(midPointID)
                fidList.SetNthFiducialPositionFromArray(index, coord)
                if landmarkDescription[midPointID]["projection"]["isProjected"]:
                    hardenModel = slicer.app.mrmlScene().GetNodeByID(
                        fidList.GetAttribute("hardenModelID")
                    )
                    landmarkDescription[midPointID]["projection"][
                        "closestPointIndex"
                    ] = self.projectOnSurface(hardenModel, fidList, landmarkID)
                    fidList.SetAttribute(
                        "landmarkDescription", self.encodeJSON(landmarkDescription)
                    )
                self.updateMidPoint(fidList, midPointID)

    # Called when a landmarks is moved
    def onPointModifiedEvent(self, obj, event):
        logging.debug("----onPointModifiedEvent PandP-----")
        landmarkDescription = self.decodeJSON(obj.GetAttribute("landmarkDescription"))
        if not landmarkDescription:
            return
        selectedLandmarkID = self.findIDFromLabel(
            obj, self.interface.landmarkComboBox.currentText
        )
        # remove observer to make sure, the callback function won't work..
        tag = self.decodeJSON(obj.GetAttribute("PointModifiedEventTag"))
        obj.RemoveObserver(tag["PointModifiedEventTag"])
        if selectedLandmarkID:
            activeLandmarkState = landmarkDescription[selectedLandmarkID]
            if activeLandmarkState["projection"]["isProjected"]:
                hardenModel = slicer.app.mrmlScene().GetNodeByID(
                    obj.GetAttribute("hardenModelID")
                )
                activeLandmarkState["projection"][
                    "closestPointIndex"
                ] = self.projectOnSurface(hardenModel, obj, selectedLandmarkID)
                obj.SetAttribute(
                    "landmarkDescription", self.encodeJSON(landmarkDescription)
                )
            self.updateMidPoint(obj, selectedLandmarkID)
            self.findROI(obj)
        time.sleep(0.08)
        # Add the observer again
        PointModifiedEventTag = obj.AddObserver(
            obj.PointModifiedEvent, self.onPointModifiedEvent
        )
        obj.SetAttribute(
            "PointModifiedEventTag",
            self.encodeJSON({"PointModifiedEventTag": PointModifiedEventTag}),
        )

    def onPointRemovedEvent(self, obj, event):
        logging.debug("------markup deleting-------")
        landmarkDescription = self.decodeJSON(obj.GetAttribute("landmarkDescription"))
        IDs = []
        for ID, value in landmarkDescription.items():
            isFound = False
            for n in range(obj.GetNumberOfMarkups()):
                markupID = obj.GetNthMarkupID(n)
                if ID == markupID:
                    isFound = True
            if not isFound:
                logging.debug(ID)
                IDs.append(ID)
        for ID in IDs:
            landmarkDescription.pop(ID, None)
        obj.SetAttribute("landmarkDescription", self.encodeJSON(landmarkDescription))
        self.updateLandmarkComboBox(obj)

    def updateLandmarkComboBox(self, fidList, displayMidPoint=True):
        if not fidList:
            return
        landmarkDescription = self.decodeJSON(
            fidList.GetAttribute("landmarkDescription")
        )
        self.interface.landmarkComboBox.blockSignals(True)
        self.interface.landmarkComboBox.clear()
        numOfFid = fidList.GetNumberOfMarkups()
        if numOfFid > 0:
            for i in range(numOfFid):
                ID = fidList.GetNthMarkupID(i)
                if not landmarkDescription[ID]["midPoint"]["isMidPoint"]:
                    landmarkLabel = fidList.GetNthMarkupLabel(i)
                    self.interface.landmarkComboBox.addItem(landmarkLabel)
        self.interface.landmarkComboBox.blockSignals(False)

    def findIDFromLabel(self, fidList, landmarkLabel):
        # find the ID of the markupsNode from the label of a landmark!
        landmarkDescription = self.decodeJSON(
            fidList.GetAttribute("landmarkDescription")
        )
        for ID, value in landmarkDescription.items():
            if value["landmarkLabel"] == landmarkLabel:
                return ID
        return None

    def getClosestPointIndex(self, fidNode, inputPolyData, landmarkID):
        landmarkCoord = numpy.zeros(3)
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
        fidNode.SetNthFiducialPositionFromArray(landmarkID, landmarkCoord)

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

    def defineNeighbor(
        self, connectedVerticesList, inputModelNodePolyData, indexClosestPoint, distance
    ):
        self.GetConnectedVertices(
            connectedVerticesList, inputModelNodePolyData, indexClosestPoint
        )
        if distance > 1:
            for dist in range(1, int(distance)):
                for i in range(connectedVerticesList.GetNumberOfIds()):
                    self.GetConnectedVertices(
                        connectedVerticesList,
                        inputModelNodePolyData,
                        connectedVerticesList.GetId(i),
                    )
        return connectedVerticesList

    def GetConnectedVertices(self, connectedVerticesIDList, polyData, pointID):
        # Return IDs of all the vertices that compose the first neighbor.
        cellList = vtk.vtkIdList()
        connectedVerticesIDList.InsertUniqueId(pointID)
        # Get cells that vertex 'pointID' belongs to
        polyData.GetPointCells(pointID, cellList)
        numberOfIds = cellList.GetNumberOfIds()
        for i in range(numberOfIds):
            # Get points which compose all cells
            pointIdList = vtk.vtkIdList()
            polyData.GetCellPoints(cellList.GetId(i), pointIdList)
            for j in range(pointIdList.GetNumberOfIds()):
                connectedVerticesIDList.InsertUniqueId(pointIdList.GetId(j))
        return connectedVerticesIDList

    def addArrayFromIdList(self, connectedIdList, inputModelNode, arrayName):
        if not inputModelNode:
            return
        inputModelNodePolydata = inputModelNode.GetPolyData()
        pointData = inputModelNodePolydata.GetPointData()
        numberofIds = connectedIdList.GetNumberOfIds()
        hasArrayInt = pointData.HasArray(arrayName)
        if hasArrayInt == 1:  # ROI Array found
            pointData.RemoveArray(arrayName)
        arrayToAdd = vtk.vtkDoubleArray()
        arrayToAdd.SetName(arrayName)
        for i in range(inputModelNodePolydata.GetNumberOfPoints()):
            arrayToAdd.InsertNextValue(0.0)
        for i in range(numberofIds):
            arrayToAdd.SetValue(connectedIdList.GetId(i), 1.0)
        lut = vtk.vtkLookupTable()
        tableSize = 2
        lut.SetNumberOfTableValues(tableSize)
        lut.Build()
        displayNode = inputModelNode.GetDisplayNode()
        if displayNode:
            rgb = displayNode.GetColor()
            lut.SetTableValue(0, rgb[0], rgb[1], rgb[2], 1)
        else:
            lut.SetTableValue(0, 0.0, 1.0, 0.0, 1)
        lut.SetTableValue(1, 1.0, 0.0, 0.0, 1)
        arrayToAdd.SetLookupTable(lut)
        pointData.AddArray(arrayToAdd)
        inputModelNodePolydata.Modified()
        return True

    def displayROI(self, inputModelNode, scalarName):
        PolyData = inputModelNode.GetPolyData()
        PolyData.Modified()
        displayNode = inputModelNode.GetModelDisplayNode()
        displayNode.SetScalarVisibility(False)
        disabledModify = displayNode.StartModify()
        displayNode.SetActiveScalarName(scalarName)
        displayNode.SetScalarVisibility(True)
        displayNode.EndModify(disabledModify)

    def findROI(self, fidList):
        hardenModel = slicer.app.mrmlScene().GetNodeByID(
            fidList.GetAttribute("hardenModelID")
        )
        connectedModel = slicer.app.mrmlScene().GetNodeByID(
            fidList.GetAttribute("connectedModelID")
        )
        landmarkDescription = self.decodeJSON(
            fidList.GetAttribute("landmarkDescription")
        )
        arrayName = fidList.GetAttribute("arrayName")
        arrayPartNames = set()

        ROIPointListID = vtk.vtkIdList()
        for key, activeLandmarkState in landmarkDescription.items():
            currentROIPointListID = vtk.vtkIdList()
            currentArrayPartName = self.ROI_ARRAY_NAME.format(
                connectedModel.GetName(),
                activeLandmarkState["landmarkLabel"],
            )
            if activeLandmarkState["ROIradius"] != 0:
                self.defineNeighbor(
                    currentROIPointListID,
                    hardenModel.GetPolyData(),
                    activeLandmarkState["projection"]["closestPointIndex"],
                    activeLandmarkState["ROIradius"],
                )
                self.addArrayFromIdList(
                    currentROIPointListID, connectedModel, currentArrayPartName
                )
                arrayPartNames.add(currentArrayPartName)
            for j in range(currentROIPointListID.GetNumberOfIds()):
                ROIPointListID.InsertUniqueId(currentROIPointListID.GetId(j))

        fidList.SetAttribute("arrayPartNames", self.encodeJSON(list(arrayPartNames)))

        listID = ROIPointListID
        self.addArrayFromIdList(listID, connectedModel, arrayName)
        self.displayROI(connectedModel, arrayName)
        return ROIPointListID

    def cleanerAndTriangleFilter(self, inputModel):
        cleanerPolydata = vtk.vtkCleanPolyData()
        cleanerPolydata.SetInputData(inputModel.GetPolyData())
        cleanerPolydata.Update()
        triangleFilter = vtk.vtkTriangleFilter()
        triangleFilter.SetInputData(cleanerPolydata.GetOutput())
        triangleFilter.Update()
        inputModel.SetAndObservePolyData(triangleFilter.GetOutput())

    def cleanMesh(self, selectedLandmark):
        activeInput = self.selectedModel
        fidList = self.selectedFidList
        hardenModel = slicer.app.mrmlScene().GetNodeByID(
            activeInput.GetAttribute("hardenModelID")
        )
        if activeInput:
            # Clean the mesh with vtkCleanPolyData cleaner and vtkTriangleFilter:
            self.cleanerAndTriangleFilter(activeInput)
            self.cleanerAndTriangleFilter(hardenModel)
            # Define the new ROI:
            selectedLandmarkID = self.findIDFromLabel(fidList, selectedLandmark)
            if selectedLandmarkID:
                landmarkDescription = self.decodeJSON(
                    fidList.GetAttribute("landmarkDescription")
                )
                landmarkDescription[selectedLandmarkID]["projection"][
                    "closestPointIndex"
                ] = self.projectOnSurface(hardenModel, fidList, selectedLandmarkID)
                fidList.SetAttribute(
                    "landmarkDescription", self.encodeJSON(landmarkDescription)
                )
            fidList.SetAttribute("isClean", self.encodeJSON({"isClean": True}))

    def propagateCorrespondent(
        self, fidList, referenceInputModel, propagatedInputModel
    ):
        arrayName = fidList.GetAttribute("arrayName")
        arrayPartNames = self.decodeJSON(fidList.GetAttribute("arrayPartNames"))

        referencePointData = referenceInputModel.GetPolyData().GetPointData()
        propagatedPointData = propagatedInputModel.GetPolyData().GetPointData()

        for name in [arrayName, *arrayPartNames]:
            arrayToPropagate = referencePointData.GetArray(name)
            if arrayToPropagate:
                if propagatedPointData.GetArray(name):  # Array already exists
                    propagatedPointData.RemoveArray(name)
                propagatedPointData.AddArray(arrayToPropagate)
                self.displayROI(propagatedInputModel, name)
            else:
                logging.warning(
                    " NO ROI ARRAY %s FOUND. PLEASE DEFINE ONE BEFORE.", name
                )
                continue

    def propagateNonCorrespondent(self, fidList, modelToPropagate):
        logging.debug(modelToPropagate.GetAttribute("hardenModelID"))
        connectedModel = slicer.app.mrmlScene().GetNodeByID(
            fidList.GetAttribute("connectedModel")
        )
        hardenModel = slicer.app.mrmlScene().GetNodeByID(
            modelToPropagate.GetAttribute("hardenModelID")
        )
        landmarkDescription = self.decodeJSON(
            fidList.GetAttribute("landmarkDescription")
        )
        arrayName = fidList.GetAttribute("arrayName")

        ROIPointListID = vtk.vtkIdList()
        for key, activeLandmarkState in landmarkDescription.items():
            currentROIPointListID = vtk.vtkIdList()
            currentArrayPartName = self.ROI_ARRAY_NAME.format(
                connectedModel.GetName(), activeLandmarkState["landmarkLabel"]
            )
            markupsIndex = fidList.GetNthControlPointIndexByID(key)
            indexClosestPoint = self.getClosestPointIndex(
                fidList, modelToPropagate.GetPolyData(), markupsIndex
            )
            if activeLandmarkState["ROIradius"] != 0:
                self.defineNeighbor(
                    currentROIPointListID,
                    hardenModel.GetPolyData(),
                    indexClosestPoint,
                    activeLandmarkState["ROIradius"],
                )
                self.addArrayFromIdList(
                    currentROIPointListID, modelToPropagate, currentArrayPartName
                )
            for j in range(currentROIPointListID.GetNumberOfIds()):
                ROIPointListID.InsertUniqueId(currentROIPointListID.GetId(j))

        listID = ROIPointListID
        self.addArrayFromIdList(listID, modelToPropagate, arrayName)
        self.displayROI(modelToPropagate, arrayName)

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


class PickAndPaintTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        self.setUp()
        self.delayDisplay(" Starting tests ")

        self.delayDisplay(" Test getClosestPointIndex Function ")
        self.assertTrue(self.testGetClosestPointIndexFunction())

        self.delayDisplay(" Test replaceLandmark Function ")
        self.assertTrue(self.testReplaceLandmarkFunction())

        self.delayDisplay(" Test DefineNeighbors Function ")
        self.assertTrue(self.testDefineNeighborsFunction())

        self.delayDisplay(" Test addArrayFromIdList Function ")
        self.assertTrue(self.testAddArrayFromIdListFunction())

        self.delayDisplay(" Tests Passed! ")

    def testGetClosestPointIndexFunction(self):
        sphereModel = self.defineSphere()
        slicer.mrmlScene.AddNode(sphereModel)
        closestPointIndexList = list()
        polyData = sphereModel.GetPolyData()
        logic = PickAndPaintLogic(slicer.modules.PickAndPaintWidget)
        markupsLogic = self.defineMarkupsLogic()

        closestPointIndexList.append(
            logic.getClosestPointIndex(
                slicer.mrmlScene.GetNodeByID(markupsLogic.GetActiveListID()),
                polyData,
                0,
            )
        )
        closestPointIndexList.append(
            logic.getClosestPointIndex(
                slicer.mrmlScene.GetNodeByID(markupsLogic.GetActiveListID()),
                polyData,
                1,
            )
        )
        closestPointIndexList.append(
            logic.getClosestPointIndex(
                slicer.mrmlScene.GetNodeByID(markupsLogic.GetActiveListID()),
                polyData,
                2,
            )
        )

        if (
            closestPointIndexList[0] != 9
            or closestPointIndexList[1] != 35
            or closestPointIndexList[2] != 1
        ):
            return False
        return True

    def testReplaceLandmarkFunction(self):
        logging.info(" Test replaceLandmark Function ")
        logic = PickAndPaintLogic(slicer.modules.PickAndPaintWidget)
        sphereModel = self.defineSphere()
        polyData = sphereModel.GetPolyData()
        markupsLogic = self.defineMarkupsLogic()
        listCoordinates = list()
        listCoordinates.append(
            [55.28383255004883, 55.28383255004883, 62.34897994995117]
        )
        listCoordinates.append(
            [-68.93781280517578, -68.93781280517578, -22.252094268798828]
        )
        listCoordinates.append([0.0, 0.0, -100.0])
        closestPointIndexList = [9, 35, 1]
        coord = [-1, -1, -1]
        for i in range(
            slicer.mrmlScene.GetNodeByID(
                markupsLogic.GetActiveListID()
            ).GetNumberOfFiducials()
        ):
            logic.replaceLandmark(
                polyData,
                slicer.mrmlScene.GetNodeByID(markupsLogic.GetActiveListID()),
                i,
                closestPointIndexList[i],
            )
            slicer.mrmlScene.GetNodeByID(
                markupsLogic.GetActiveListID()
            ).GetNthFiducialPosition(i, coord)
            if coord != listCoordinates[i]:
                logging.warning(f"{i}  - Failed ")
                return False
            else:
                logging.info(f"{i}  - Passed! ")
        return True

    def testDefineNeighborsFunction(self):
        logic = PickAndPaintLogic(slicer.modules.PickAndPaintWidget)
        sphereModel = self.defineSphere()
        polyData = sphereModel.GetPolyData()
        closestPointIndexList = [9, 35, 1]
        connectedVerticesReferenceList = list()
        connectedVerticesReferenceList.append([9, 2, 3, 8, 10, 15, 16])
        connectedVerticesReferenceList.append(
            [35, 28, 29, 34, 36, 41, 42, 21, 22, 27, 23, 30, 33, 40, 37, 43, 47, 48, 49]
        )
        connectedVerticesReferenceList.append(
            [
                1,
                7,
                13,
                19,
                25,
                31,
                37,
                43,
                49,
                6,
                48,
                12,
                18,
                24,
                30,
                36,
                42,
                5,
                47,
                41,
                11,
                17,
                23,
                29,
                35,
            ]
        )
        connectedVerticesTestedList = list()

        for i in range(3):
            inter = vtk.vtkIdList()
            logic.defineNeighbor(inter, polyData, closestPointIndexList[i], i + 1)
            connectedVerticesTestedList.append(inter)
            list1 = list()
            for j in range(connectedVerticesTestedList[i].GetNumberOfIds()):
                list1.append(int(connectedVerticesTestedList[i].GetId(j)))
            connectedVerticesTestedList[i] = list1
            if connectedVerticesTestedList[i] != connectedVerticesReferenceList[i]:
                logging.warning(f"test  {i}  AddArrayFromIdList: failed")
                return False
            else:
                logging.info(f"test  {i}  AddArrayFromIdList: succeed")
        return True

    def testAddArrayFromIdListFunction(self):
        logic = PickAndPaintLogic(slicer.modules.PickAndPaintWidget)
        sphereModel = self.defineSphere()
        polyData = sphereModel.GetPolyData()
        closestPointIndexList = [9, 35, 1]
        for i in range(3):
            inter = vtk.vtkIdList()
            logic.defineNeighbor(inter, polyData, closestPointIndexList[i], i + 1)
            logic.addArrayFromIdList(inter, sphereModel, "Test_" + str(i + 1))
            if polyData.GetPointData().HasArray("Test_" + str(i + 1)) != 1:
                logging.warning(f"test  {i}  AddArrayFromIdList: failed")
                return False
            else:
                logging.info(f"test  {i}  AddArrayFromIdList: succeed")
        return True

    def defineSphere(self):
        sphereSource = vtk.vtkSphereSource()
        sphereSource.SetRadius(100.0)
        sphereSource.Update()
        model = slicer.vtkMRMLModelNode()
        model.SetAndObservePolyData(sphereSource.GetOutput())
        modelDisplay = slicer.vtkMRMLModelDisplayNode()
        slicer.mrmlScene.AddNode(modelDisplay)
        model.SetAndObserveDisplayNodeID(modelDisplay.GetID())
        modelDisplay.SetInputPolyDataConnection(sphereSource.GetOutputPort())
        return model

    def defineMarkupsLogic(self):
        slicer.mrmlScene.Clear(0)
        markupsLogic = slicer.modules.markups.logic()
        markupsLogic.AddFiducial(58.602, 41.692, 62.569)
        markupsLogic.AddFiducial(-59.713, -67.347, -19.529)
        markupsLogic.AddFiducial(-10.573, -3.036, -93.381)
        return markupsLogic
