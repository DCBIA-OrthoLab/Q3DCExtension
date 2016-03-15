import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import numpy, csv, os
import json
import time
import math

#
# CalculateDisplacement
#

class Q3DC(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Q3DC "
        parent.categories = ["Quantification"]
        parent.dependencies = []
        parent.contributors = ["Lucie Macron (University of Michigan)","Jean-Baptiste VIMORT (University of Michigan)"]
        parent.helpText = """
            """
        parent.acknowledgementText = """
    This work was supported by the National Institute of Dental
    & Craniofacial Research and the National Institute of Biomedical
    Imaging and Bioengineering under Award Number R01DE024450.
    The content is solely the responsibility of the authors and does
    not necessarily represent the official views of the National
    Institutes of Health.
    """
        self.parent = parent

class Q3DCWidget(ScriptedLoadableModuleWidget):

    class MarkupsNodeStorage(object):
        def __init__(self):
            self.MarkupAddedEventTag = None
            self.PointModifiedEventTag = None
            self.landmarkDictionary = None   # key: landmark ID
                                             # value: ID of the model of reference
    def setup(self):
        print "-------Q3DC Widget Setup------"
        ScriptedLoadableModuleWidget.setup(self)
        # GLOBALS:
        self.logic = Q3DCLogic(self)
        self.interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        self.computedDistanceList = list()
        self.computedAnglesList = list()
        self.computedLinePointList = list()
        self.renderer1 = None
        self.actor1 = None
        self.renderer2 = None
        self.actor2 = None
        self.renderer3 = None
        self.actor3 = None


        # UI setup
        loader = qt.QUiLoader()
        moduleName = 'Q3DC'
        scriptedModulesPath = eval('slicer.modules.%s.path' % moduleName.lower())
        scriptedModulesPath = os.path.dirname(scriptedModulesPath)
        path = os.path.join(scriptedModulesPath, 'Resources', 'UI', '%s.ui' %moduleName)

        qfile = qt.QFile(path)
        qfile.open(qt.QFile.ReadOnly)
        widget = loader.load(qfile, self.parent)
        self.layout = self.parent.layout()
        self.widget = widget
        self.layout.addWidget(widget)

        #--------------------------- Scene --------------------------#
        self.SceneCollapsibleButton = self.logic.get("SceneCollapsibleButton") # this atribute is usefull for Longitudinal quantification extension
        treeView = self.logic.get("treeView")
        treeView.setMRMLScene(slicer.app.mrmlScene())
        treeView.sceneModel().setHorizontalHeaderLabels(["Models"])
        treeView.sortFilterProxyModel().nodeTypes = ['vtkMRMLModelNode','vtkMRMLMarkupsFiducialNode']
        treeView.header().setVisible(False)
        # --------------- landmark modification --------------
        self.inputModelLabel = self.logic.get("inputModelLabel")  # this atribute is usefull for Longitudinal quantification extension
        self.inputLandmarksLabel = self.logic.get("inputLandmarksLabel")  # this atribute is usefull for Longitudinal quantification extension
        self.landmarkModif = self.logic.get("landmarkModif")
        self.inputModelSelector = self.logic.get("inputModelSelector")
        self.inputModelSelector.setMRMLScene(slicer.mrmlScene)
        self.inputModelSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onModelChanged)
        self.addLandmarkButton = self.logic.get("addLandmarkButton")
        self.addLandmarkButton.connect('clicked()', self.onAddLandmarkButtonClicked)
        self.inputLandmarksSelector = self.logic.get("inputLandmarksSelector")
        self.inputLandmarksSelector.setMRMLScene(slicer.mrmlScene)
        self.inputLandmarksSelector.setEnabled(False) # The "enable" property seems to not be imported from the .ui
        self.inputLandmarksSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onLandmarksChanged)
        self.loadLandmarksOnSurfacCheckBox = self.logic.get("loadLandmarksOnSurfacCheckBox")
        self.landmarkComboBox = self.logic.get("landmarkComboBox")
        self.landmarkComboBox.connect('currentIndexChanged(QString)', self.UpdateInterface)
        self.surfaceDeplacementCheckBox = self.logic.get("surfaceDeplacementCheckBox")
        self.surfaceDeplacementCheckBox.connect('stateChanged(int)', self.onSurfaceDeplacementStateChanged)
        #        ----------------- Compute Mid Point -------------
        self.midPointGroupBox = self.logic.get("midPointGroupBox")
        self.landmarkComboBox1 = self.logic.get("landmarkComboBox1")
        self.landmarkComboBox1.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.landmarkComboBox2 = self.logic.get("landmarkComboBox2")
        self.landmarkComboBox2.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.defineMiddlePointButton = self.logic.get("defineMiddlePointButton")
        self.defineMiddlePointButton.connect('clicked()', self.onDefineMidPointClicked)
        self.midPointOnSurfaceCheckBox = self.logic.get("midPointOnSurfaceCheckBox")
#        ------------------- 1st OPTION -------------------
        self.distanceGroupBox = self.logic.get("distanceGroupBox")
        self.landmarkComboBoxA = self.logic.get("landmarkComboBoxA")
        self.fidListComboBoxA = self.logic.get("fidListComboBoxA")
        self.fidListComboBoxA.setMRMLScene(slicer.mrmlScene)
        self.landmarkComboBoxB = self.logic.get("landmarkComboBoxB")
        self.fidListComboBoxB = self.logic.get("fidListComboBoxB")
        self.fidListComboBoxB.setMRMLScene(slicer.mrmlScene)
        self.computeDistancesPushButton = self.logic.get("computeDistancesPushButton")
        self.computeDistancesPushButton.connect('clicked()', self.onComputeDistanceClicked)
        self.landmarkComboBoxA.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.landmarkComboBoxB.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.fidListComboBoxA.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.fidListComboBoxA, self.landmarkComboBoxA))
        self.fidListComboBoxB.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.fidListComboBoxB, self.landmarkComboBoxB))
        # ---------------------------- Directory - Export Button -----------------------------
        self.distanceLayout = self.logic.get("distanceLayout")
        self.distanceTable = qt.QTableWidget()
        self.directoryExportDistance = ctk.ctkDirectoryButton()
        self.exportDistanceButton = qt.QPushButton(" Export ")
        self.exportDistanceButton.enabled = True
        self.exportDistanceLayout = qt.QHBoxLayout()
        self.exportDistanceLayout.addWidget(self.directoryExportDistance)
        self.exportDistanceLayout.addWidget(self.exportDistanceButton)
        self.tableAndExportLayout = qt.QVBoxLayout()
        self.tableAndExportLayout.addWidget(self.distanceTable)
        self.tableAndExportLayout.addLayout(self.exportDistanceLayout)
#       ------------------- 2nd OPTION -------------------
        self.angleLayout = self.logic.get("angleLayout")
        self.angleGroupBox = self.logic.get("angleGroupBox")
        self.line1LAComboBox = self.logic.get("line1LAComboBox")
        self.fidListComboBoxline1LA = self.logic.get("fidListComboBoxline1LA")
        self.fidListComboBoxline1LA.setMRMLScene(slicer.mrmlScene)
        self.line1LBComboBox = self.logic.get("line1LBComboBox")
        self.fidListComboBoxline1LB = self.logic.get("fidListComboBoxline1LB")
        self.fidListComboBoxline1LB.setMRMLScene(slicer.mrmlScene)
        self.line2LAComboBox = self.logic.get("line2LAComboBox")
        self.fidListComboBoxline2LA = self.logic.get("fidListComboBoxline2LA")
        self.fidListComboBoxline2LA.setMRMLScene(slicer.mrmlScene)
        self.line2LBComboBox = self.logic.get("line2LBComboBox")
        self.fidListComboBoxline2LB = self.logic.get("fidListComboBoxline2LB")
        self.fidListComboBoxline2LB.setMRMLScene(slicer.mrmlScene)
        self.pitchCheckBox = self.logic.get("pitchCheckBox")
        self.rollCheckBox = self.logic.get("rollCheckBox")
        self.yawCheckBox = self.logic.get("yawCheckBox")
        self.computeAnglesPushButton = self.logic.get("computeAnglesPushButton")
        self.fidListComboBoxline1LA.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.fidListComboBoxline1LA, self.line1LAComboBox))
        self.fidListComboBoxline1LB.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.fidListComboBoxline1LB, self.line1LBComboBox))
        self.fidListComboBoxline2LA.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.fidListComboBoxline2LA, self.line2LAComboBox))
        self.fidListComboBoxline2LB.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.fidListComboBoxline2LB, self.line2LBComboBox))
        self.computeAnglesPushButton.connect('clicked()', self.onComputeAnglesClicked)
        self.line1LAComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.line1LBComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.line2LAComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.line2LBComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.pitchCheckBox.connect('clicked(bool)', self.UpdateInterface)
        self.rollCheckBox.connect('clicked(bool)', self.UpdateInterface)
        self.yawCheckBox.connect('clicked(bool)', self.UpdateInterface)

        # ---------------------------- Directory - Export Button -----------------------------
        self.anglesTable = qt.QTableWidget()
        self.directoryExportAngle = ctk.ctkDirectoryButton()
        self.exportAngleButton = qt.QPushButton("Export")
        self.exportAngleButton.enabled = True
        self.exportAngleLayout = qt.QHBoxLayout()
        self.exportAngleLayout.addWidget(self.directoryExportAngle)
        self.exportAngleLayout.addWidget(self.exportAngleButton)
        self.tableAndExportAngleLayout = qt.QVBoxLayout()
        self.tableAndExportAngleLayout.addWidget(self.anglesTable)
        self.tableAndExportAngleLayout.addLayout(self.exportAngleLayout)
#       ------------------- 3rd OPTION -------------------
        self.linePointGroupBox = self.logic.get("linePointGroupBox")
        self.lineLAComboBox = self.logic.get("lineLAComboBox")
        self.fidListComboBoxlineLA = self.logic.get("fidListComboBoxlineLA")
        self.fidListComboBoxlineLA.setMRMLScene(slicer.mrmlScene)
        self.lineLBComboBox = self.logic.get("lineLBComboBox")
        self.fidListComboBoxlineLB = self.logic.get("fidListComboBoxlineLB")
        self.fidListComboBoxlineLB.setMRMLScene(slicer.mrmlScene)
        self.linePointComboBox = self.logic.get("linePointComboBox")
        self.fidListComboBoxlinePoint = self.logic.get("fidListComboBoxlinePoint")
        self.fidListComboBoxlinePoint.setMRMLScene(slicer.mrmlScene)
        self.computeLinePointPushButton = self.logic.get("computeLinePointPushButton")
        self.fidListComboBoxlineLA.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.fidListComboBoxlineLA, self.lineLAComboBox))
        self.fidListComboBoxlineLB.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.fidListComboBoxlineLB, self.lineLBComboBox))
        self.fidListComboBoxlinePoint.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.fidListComboBoxlinePoint, self.linePointComboBox))
        self.computeLinePointPushButton.connect('clicked()', self.onComputeLinePointClicked)
        self.lineLAComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.lineLBComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        # ---------------------------- Directory - Export Button -----------------------------
        self.LinePointLayout = self.logic.get("LinePointLayout")
        self.linePointTable = qt.QTableWidget()
        self.directoryExportLinePoint = ctk.ctkDirectoryButton()
        self.exportLinePointButton = qt.QPushButton("Export")
        self.exportLinePointButton.enabled = True
        self.exportLinePointLayout = qt.QHBoxLayout()
        self.exportLinePointLayout.addWidget(self.directoryExportLinePoint)
        self.exportLinePointLayout.addWidget(self.exportLinePointButton)
        self.tableAndExportLinePointLayout = qt.QVBoxLayout()
        self.tableAndExportLinePointLayout.addWidget(self.linePointTable)
        self.tableAndExportLinePointLayout.addLayout(self.exportLinePointLayout)
        # INITIALISATION:
        slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndCloseEvent, self.onCloseScene)
        self.UpdateInterface()
        self.logic.initComboboxdict()

    def onCloseScene(self, obj, event):
        list = slicer.mrmlScene.GetNodesByClass("vtkMRMLModelNode")
        end = list.GetNumberOfItems()
        for i in range(0,end):
            model = list.GetItemAsObject(i)
            hardenModel = slicer.mrmlScene.GetNodesByName(model.GetName()).GetItemAsObject(0)
            slicer.mrmlScene.RemoveNode(hardenModel)
        if self.renderer1 :
            self.renderer1.RemoveActor(self.actor1)
        if self.renderer2 :
            self.renderer2.RemoveActor(self.actor2)
        if self.renderer3 :
            self.renderer3.RemoveActor(self.actor2)
        self.landmarkComboBox1.clear()
        self.landmarkComboBox.clear()
        self.fidListComboBoxA.setCurrentNode(None)
        self.fidListComboBoxB.setCurrentNode(None)
        self.fidListComboBoxline1LA.setCurrentNode(None)
        self.fidListComboBoxline1LB.setCurrentNode(None)
        self.fidListComboBoxline2LA.setCurrentNode(None)
        self.fidListComboBoxline2LB.setCurrentNode(None)
        self.line1LAComboBox.clear()
        self.line1LBComboBox.clear()
        self.line2LAComboBox.clear()
        self.line2LBComboBox.clear()
        self.landmarkComboBox2.clear()
        self.fidListComboBoxline2LB.setCurrentNode(None)
        self.inputModelSelector.setCurrentNode(None)
        self.inputLandmarksSelector.setCurrentNode(None)
        self.computedDistanceList = []
        self.computedAnglesList = []
        self.computedLinePointList = []
        self.linePointTable.clear()
        self.linePointTable.setRowCount(0)
        self.linePointTable.setColumnCount(0)
        self.anglesTable.clear()
        self.anglesTable.setRowCount(0)
        self.anglesTable.setColumnCount(0)
        self.distanceTable.clear()
        self.distanceTable.setRowCount(0)
        self.distanceTable.setColumnCount(0)

    def enter(self):
        print "enter Q3DC"
        model = self.inputModelSelector.currentNode()
        fidlist = self.inputLandmarksSelector.currentNode()

        if fidlist:
            if fidlist.GetAttribute("connectedModelID") != model.GetID():
                self.inputModelSelector.setCurrentNode(None)
                self.inputLandmarksSelector.setCurrentNode(None)
                self.landmarkComboBox.clear()
        self.UpdateInterface()

        # Checking the names of the fiducials
        list = slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsFiducialNode")
        end = list.GetNumberOfItems()
        for i in range(0,end):
            fidList = list.GetItemAsObject(i)
            landmarkDescription = self.logic.decodeJSON(fidList.GetAttribute("landmarkDescription"))
            if landmarkDescription:
                for n in range(fidList.GetNumberOfMarkups()):
                    markupID = fidList.GetNthMarkupID(n)
                    markupLabel = fidList.GetNthMarkupLabel(n)
                    landmarkDescription[markupID]["landmarkLabel"] = markupLabel
                fidList.SetAttribute("landmarkDescription",self.logic.encodeJSON(landmarkDescription))


    def UpdateInterface(self):
        self.defineMiddlePointButton.enabled = self.landmarkComboBox1.currentText != '' and \
                                               self.landmarkComboBox2.currentText != '' and \
                                               self.landmarkComboBox1.currentText != self.landmarkComboBox2.currentText
        self.computeDistancesPushButton.enabled = self.landmarkComboBoxA.currentText != '' and\
                                                  self.landmarkComboBoxB.currentText != '' and\
                                                  self.landmarkComboBoxA.currentText != self.landmarkComboBoxB.currentText
        self.computeAnglesPushButton.enabled = self.line1LAComboBox.currentText != '' and\
                                               self.line1LBComboBox.currentText != '' and\
                                               self.line2LAComboBox.currentText != '' and\
                                               self.line2LBComboBox.currentText != '' and\
                                               self.line1LAComboBox.currentText != self.line1LBComboBox.currentText and\
                                               self.line2LAComboBox.currentText != self.line2LBComboBox.currentText and\
                                               (self.pitchCheckBox.isChecked() or
                                                self.rollCheckBox.isChecked() or
                                                self.yawCheckBox.isChecked() )
        self.computeLinePointPushButton.enabled = self.lineLAComboBox.currentText != '' and\
                                                  self.lineLBComboBox.currentText != '' and\
                                                  self.linePointComboBox.currentText != '' and\
                                                  self.lineLAComboBox.currentText != self.lineLBComboBox.currentText

        # Clear Lines:
        if self.renderer1 :
            self.renderer1.RemoveActor(self.actor1)
            self.renderer1 = None
        if self.renderer2 :
            self.renderer2.RemoveActor(self.actor2)
            self.renderer2 = None
        if self.renderer3 :
            self.renderer3.RemoveActor(self.actor3)
            self.renderer3 = None
        if self.line1LAComboBox.currentText != '' and\
                        self.line1LBComboBox.currentText != '' and\
                        self.line1LAComboBox.currentText != self.line1LBComboBox.currentText :
            self.renderer1, self.actor1 = \
                self.logic.drawLineBetween2Landmark(self.line1LAComboBox.currentText,
                                                    self.line1LBComboBox.currentText,
                                                    self.fidListComboBoxline1LA.currentNode(),
                                                    self.fidListComboBoxline1LB.currentNode())
        if self.line2LAComboBox.currentText != '' and\
                        self.line2LBComboBox.currentText != '' and\
                        self.line2LAComboBox.currentText != self.line2LBComboBox.currentText :
            self.renderer2, self.actor2 = \
                self.logic.drawLineBetween2Landmark(self.line2LAComboBox.currentText,
                                                    self.line2LBComboBox.currentText,
                                                    self.fidListComboBoxline2LA.currentNode(),
                                                    self.fidListComboBoxline2LB.currentNode())
        if self.lineLAComboBox.currentText != '' and\
                        self.lineLBComboBox.currentText != '' and\
                        self.lineLAComboBox.currentText != self.lineLBComboBox.currentText:
            self.renderer3, self.actor3 = \
                self.logic.drawLineBetween2Landmark(self.lineLAComboBox.currentText,
                                                    self.lineLBComboBox.currentText,
                                                    self.fidListComboBoxlineLA.currentNode(),
                                                    self.fidListComboBoxlineLB.currentNode())
        self.logic.UpdateThreeDView(self.landmarkComboBox.currentText)

    def onModelChanged(self):
        print "-------Model Changed--------"
        if self.logic.selectedModel:
            Model = self.logic.selectedModel
            try:
                Model.RemoveObserver(self.logic.decodeJSON(self.logic.selectedModel.GetAttribute("modelModifieTagEvent")))
            except:
                pass
        self.logic.selectedModel = self.inputModelSelector.currentNode()
        self.logic.ModelChanged(self.inputModelSelector, self.inputLandmarksSelector)
        self.inputLandmarksSelector.setCurrentNode(None)

    def onLandmarksChanged(self):
        print "-------Landmarks Changed--------"
        if self.inputModelSelector.currentNode():
            self.logic.FidList = self.inputLandmarksSelector.currentNode()
            self.logic.selectedFidList = self.inputLandmarksSelector.currentNode()
            self.logic.selectedModel = self.inputModelSelector.currentNode()
            if self.inputLandmarksSelector.currentNode():
                onSurface = self.loadLandmarksOnSurfacCheckBox.isChecked()
                self.logic.connectLandmarks(self.inputModelSelector,
                                      self.inputLandmarksSelector,
                                      onSurface)
            else:
                self.landmarkComboBox.clear()

    def onAddLandmarkButtonClicked(self):
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

    def onSurfaceDeplacementStateChanged(self):
        activeInput = self.logic.selectedModel
        if not activeInput:
            return
        fidList = self.logic.selectedFidList
        if not fidList:
            return
        selectedFidReflID = self.logic.findIDFromLabel(fidList, self.landmarkComboBox.currentText)
        isOnSurface = self.surfaceDeplacementCheckBox.isChecked()
        landmarkDescription = self.logic.decodeJSON(fidList.GetAttribute("landmarkDescription"))
        if isOnSurface:
            hardenModel = slicer.app.mrmlScene().GetNodeByID(fidList.GetAttribute("hardenModelID"))
            landmarkDescription[selectedFidReflID]["projection"]["isProjected"] = True
            landmarkDescription[selectedFidReflID]["projection"]["closestPointIndex"] =\
                self.logic.projectOnSurface(hardenModel, fidList, selectedFidReflID)
        else:
            landmarkDescription[selectedFidReflID]["projection"]["isProjected"] = False
            landmarkDescription[selectedFidReflID]["projection"]["closestPointIndex"] = None
            landmarkDescription[selectedFidReflID]["ROIradius"] = 0
        fidList.SetAttribute("landmarkDescription",self.logic.encodeJSON(landmarkDescription))

    def onDefineMidPointClicked(self):
        fidList = self.logic.selectedFidList
        if not fidList:
            self.logic.warningMessage("Please select a model of reference and afiducial List.")
        landmark1ID = self.logic.findIDFromLabel(fidList,self.landmarkComboBox1.currentText)
        landmark2ID = self.logic.findIDFromLabel(fidList,self.landmarkComboBox2.currentText)
        coord = self.logic.calculateMidPointCoord(fidList, landmark1ID, landmark2ID)
        fidList.AddFiducial(coord[0],coord[1],coord[2])
        fidList.SetNthFiducialSelected(fidList.GetNumberOfMarkups() - 1, False)
        # update of the data structure
        landmarkDescription = self.logic.decodeJSON(fidList.GetAttribute("landmarkDescription"))
        numOfMarkups = fidList.GetNumberOfMarkups()
        markupID = fidList.GetNthMarkupID(numOfMarkups - 1)
        landmarkDescription[landmark1ID]["midPoint"]["definedByThisMarkup"].append(markupID)
        landmarkDescription[landmark2ID]["midPoint"]["definedByThisMarkup"].append(markupID)
        landmarkDescription[markupID]["midPoint"]["isMidPoint"] = True
        landmarkDescription[markupID]["midPoint"]["Point1"] = landmark1ID
        landmarkDescription[markupID]["midPoint"]["Point2"] = landmark2ID
        landmarkDescription[markupID]["projection"]["isProjected"] = False
        landmarkDescription[markupID]["projection"]["closestPointIndex"] = None

        if self.midPointOnSurfaceCheckBox.isChecked():
            landmarkDescription[markupID]["projection"]["isProjected"] = True
            hardenModel = slicer.app.mrmlScene().GetNodeByID(fidList.GetAttribute("hardenModelID"))
            landmarkDescription[markupID]["projection"]["closestPointIndex"] = \
                self.logic.projectOnSurface(hardenModel, fidList, markupID)
        else:
            landmarkDescription[markupID]["projection"]["isProjected"] = False
        fidList.SetAttribute("landmarkDescription",self.logic.encodeJSON(landmarkDescription))
        self.logic.interface.UpdateInterface()
        self.logic.updateLandmarkComboBox(fidList, self.landmarkComboBox, False)
        fidList.SetNthFiducialPositionFromArray(numOfMarkups - 1, coord)

    def onComputeDistanceClicked(self):
        if self.computedDistanceList:
            self.exportDistanceButton.disconnect('clicked()', self.onExportButton)
            self.layout.removeWidget(self.distanceTable)
            self.layout.removeItem(self.tableAndExportLayout)
        self.computedDistanceList = self.logic.addOnDistanceList(self.computedDistanceList,
                                                                 self.landmarkComboBoxA.currentText,
                                                                 self.landmarkComboBoxB.currentText,
                                                                 self.fidListComboBoxA.currentNode(),
                                                                 self.fidListComboBoxB.currentNode())
        self.distanceTable = self.logic.defineDistanceTable(self.distanceTable, self.computedDistanceList)
        self.distanceLayout.addLayout(self.tableAndExportLayout)
        self.exportDistanceButton.connect('clicked()', self.onExportButton)

    def onExportButton(self):
        self.logic.exportationFunction(self.directoryExportDistance, self.computedDistanceList, 'distance')

    def onComputeAnglesClicked(self):
        if self.computedAnglesList:
            self.exportAngleButton.disconnect('clicked()', self.onExportAngleButton)
            self.layout.removeWidget(self.anglesTable)
            self.layout.removeItem(self.tableAndExportAngleLayout)
        self.computedAnglesList = self.logic.addOnAngleList(self.computedAnglesList,
                                                            self.line1LAComboBox.currentText,
                                                            self.line1LBComboBox.currentText,
                                                            self.fidListComboBoxline1LA.currentNode(),
                                                            self.fidListComboBoxline1LB.currentNode(),
                                                            self.line2LAComboBox.currentText,
                                                            self.line2LBComboBox.currentText,
                                                            self.fidListComboBoxline2LA.currentNode(),
                                                            self.fidListComboBoxline2LB.currentNode(),
                                                            self.pitchCheckBox.isChecked(),
                                                            self.yawCheckBox.isChecked(),
                                                            self.rollCheckBox.isChecked()
                                                            )
        self.anglesTable = self.logic.defineAnglesTable(self.anglesTable, self.computedAnglesList)
        self.angleLayout.addLayout(self.tableAndExportAngleLayout)
        self.exportAngleButton.connect('clicked()', self.onExportAngleButton)


    def onExportAngleButton(self):
        self.logic.exportationFunction(self.directoryExportAngle, self.computedAnglesList, 'angle')

    def onComputeLinePointClicked(self):
        if self.computedLinePointList:
            self.exportLinePointButton.disconnect('clicked()', self.onExportLinePointButton)
            self.layout.removeWidget(self.linePointTable)
            self.layout.removeItem(self.tableAndExportLinePointLayout)
        self.computedLinePointList = self.logic.addOnLinePointList(self.computedLinePointList,
                                                           self.lineLAComboBox.currentText,
                                                           self.lineLBComboBox.currentText,
                                                           self.fidListComboBoxlineLA.currentNode(),
                                                           self.fidListComboBoxlineLB.currentNode(),
                                                           self.linePointComboBox.currentText,
                                                           self.fidListComboBoxlinePoint.currentNode(),
                                                           )
        self.linePointTable = self.logic.defineDistanceLinePointTable(self.linePointTable, self.computedLinePointList)
        self.LinePointLayout.addLayout(self.tableAndExportLinePointLayout)
        self.exportLinePointButton.connect('clicked()', self.onExportLinePointButton)

    def onExportLinePointButton(self):
        self.logic.exportationFunction(self.directoryExportLinePoint, self.computedLinePointList, 'linePoint')

class Q3DCLogic(ScriptedLoadableModuleLogic):
    def __init__(self, interface):
        self.interface = interface
        self.selectedModel = None
        self.selectedFidList = None
        self.numberOfDecimals = 3
        system = qt.QLocale().system()
        self.decimalPoint = chr(system.decimalPoint())
        self.comboboxdict = dict()

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

    def initComboboxdict(self):
        self.comboboxdict[self.interface.landmarkComboBoxA] = None
        self.comboboxdict[self.interface.landmarkComboBoxB] = None
        self.comboboxdict[self.interface.line1LAComboBox] = None
        self.comboboxdict[self.interface.line1LBComboBox] = None
        self.comboboxdict[self.interface.line2LAComboBox] = None
        self.comboboxdict[self.interface.line2LBComboBox] = None
        self.comboboxdict[self.interface.lineLAComboBox] = None
        self.comboboxdict[self.interface.lineLBComboBox] = None
        self.comboboxdict[self.interface.linePointComboBox] = None

    class distanceValuesStorage(object):
        def __init__(self):
            self.startLandmarkID = None
            self.endLandmarkID = None
            self.startLandmarkName = None
            self.endLandmarkName = None
            self.RLComponent = None
            self.APComponent = None
            self.SIComponent = None
            self.ThreeDComponent = None

    class angleValuesStorage(object):
        def __init__(self):
            self.landmarkALine1ID = None
            self.landmarkBLine1ID = None
            self.landmarkALine2ID = None
            self.landmarkBLine2ID = None
            self.landmarkALine1Name = None
            self.landmarkBLine1Name = None
            self.landmarkALine2Name = None
            self.landmarkBLine2Name = None
            self.Pitch = None
            self.Roll = None
            self.Yaw = None

    class distanceLinePointStorage(object):
        def __init__(self):
            self.landmarkALineID = None
            self.landmarkBLineID = None
            self.landmarkPointID = None
            self.landmarkALineName = None
            self.landmarkBLineName = None
            self.landmarkPointName = None
            self.RLComponent = None
            self.APComponent = None
            self.SIComponent = None
            self.ThreeDComponent = None

    def UpdateThreeDView(self, landmarkLabel):
        # Update the 3D view on Slicer
        if not self.selectedFidList:
            return
        if not self.selectedModel:
            return
        print "UpdateThreeDView"
        active = self.selectedFidList
        #deactivate all landmarks
        list = slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsFiducialNode")
        end = list.GetNumberOfItems()
        selectedFidReflID = self.findIDFromLabel(active,landmarkLabel)
        for i in range(0,end):
            fidList = list.GetItemAsObject(i)
            print fidList.GetID()
            landmarkDescription = self.decodeJSON(fidList.GetAttribute("landmarkDescription"))
            for key in landmarkDescription.iterkeys():
                markupsIndex = fidList.GetMarkupIndexByID(key)
                if key != selectedFidReflID:
                    fidList.SetNthMarkupLocked(markupsIndex, True)
                else:
                    fidList.SetNthMarkupLocked(markupsIndex, False)
                    fidList.SetNthMarkupLocked(markupsIndex, False)
        displayNode = self.selectedModel.GetModelDisplayNode()
        displayNode.SetScalarVisibility(False)
        if selectedFidReflID != False:
            displayNode.SetScalarVisibility(True)

    def createIntermediateHardenModel(self, model):
        hardenModel = slicer.mrmlScene.GetNodesByName("SurfaceRegistration_" + model.GetName() + "_hardenCopy_" + str(
            slicer.app.applicationPid())).GetItemAsObject(0)
        if hardenModel is None:
            hardenModel = slicer.vtkMRMLModelNode()
        hardenPolyData = vtk.vtkPolyData()
        hardenPolyData.DeepCopy(model.GetPolyData())
        hardenModel.SetAndObservePolyData(hardenPolyData)
        hardenModel.SetName(
            "SurfaceRegistration_" + model.GetName() + "_hardenCopy_" + str(slicer.app.applicationPid()))
        if model.GetParentTransformNode():
            hardenModel.SetAndObserveTransformNodeID(model.GetParentTransformNode().GetID())
        hardenModel.HideFromEditorsOn()
        slicer.mrmlScene.AddNode(hardenModel)
        logic = slicer.vtkSlicerTransformLogic()
        logic.hardenTransform(hardenModel)
        return hardenModel

    def onModelModified(self, obj, event):
        #recompute the harden model
        hardenModel = self.createIntermediateHardenModel(obj)
        obj.SetAttribute("hardenModelID",hardenModel.GetID())
        # for each fiducial list
        list = slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsFiducialNode")
        end = list.GetNumberOfItems()
        for i in range(0,end):
            # If landmarks are projected on the modified model
            fidList = list.GetItemAsObject(i)
            if fidList.GetAttribute("connectedModelID"):
                if fidList.GetAttribute("connectedModelID") == obj.GetID():
                    #replace the harden model with the new one
                    fidList.SetAttribute("hardenModelID",hardenModel.GetID())
                    #reproject the fiducials on the new model
                    landmarkDescription = self.decodeJSON(fidList.GetAttribute("landmarkDescription"))
                    for n in range(fidList.GetNumberOfMarkups()):
                        markupID = fidList.GetNthMarkupID(n)
                        if landmarkDescription[markupID]["projection"]["isProjected"] == True:
                            hardenModel = slicer.app.mrmlScene().GetNodeByID(fidList.GetAttribute("hardenModelID"))
                            markupsIndex = fidList.GetMarkupIndexByID(markupID)
                            self.replaceLandmark(hardenModel.GetPolyData(), fidList, markupsIndex,
                                                 landmarkDescription[markupID]["projection"]["closestPointIndex"])
                        fidList.SetAttribute("landmarkDescription",self.encodeJSON(landmarkDescription))

    def ModelChanged(self, inputModelSelector, inputLandmarksSelector):
        inputModel = inputModelSelector.currentNode()
        # if a Model Node is present
        if inputModel:
            self.selectedModel = inputModel
            hardenModel = self.createIntermediateHardenModel(inputModel)
            inputModel.SetAttribute("hardenModelID",hardenModel.GetID())
            modelModifieTagEvent = inputModel.AddObserver(inputModel.TransformModifiedEvent, self.onModelModified)
            inputModel.SetAttribute("modelModifieTagEvent",self.encodeJSON({'modelModifieTagEvent':modelModifieTagEvent}))
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
            messageBox.setText("Your Markup Fiducial Node is currently modified by a transform,"
                               "if you choose to continue the program will apply the transform"
                               "before doing anything else!")
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
        messageBox.setText("The Markup Fiducial Node selected is curently projected on an"
                           "other model, if you chose to continue the fiducials will be  "
                           "reprojected, and this could impact the functioning of other modules")
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

    def createNewDataStructure(self,landmarks, model, onSurface):
        landmarks.SetAttribute("connectedModelID",model.GetID())
        landmarks.SetAttribute("hardenModelID",model.GetAttribute("hardenModelID"))
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
                hardenModel = slicer.app.mrmlScene().GetNodeByID(landmarks.GetAttribute("hardenModelID"))
                landmarkDescription[markupID]["projection"]["closestPointIndex"] = \
                    self.projectOnSurface(hardenModel, landmarks, markupID)
            else:
                landmarkDescription[markupID]["projection"]["isProjected"] = False
                landmarkDescription[markupID]["projection"]["closestPointIndex"] = None
            landmarkDescription[markupID]["midPoint"] = dict()
            landmarkDescription[markupID]["midPoint"]["definedByThisMarkup"] = list()
            landmarkDescription[markupID]["midPoint"]["isMidPoint"] = False
            landmarkDescription[markupID]["midPoint"]["Point1"] = None
            landmarkDescription[markupID]["midPoint"]["Point2"] = None
        landmarks.SetAttribute("landmarkDescription",self.encodeJSON(landmarkDescription))
        planeDescription = dict()
        landmarks.SetAttribute("planeDescription",self.encodeJSON(planeDescription))
        landmarks.SetAttribute("isClean",self.encodeJSON({"isClean":False}))
        landmarks.SetAttribute("lastTransformID",None)
        landmarks.SetAttribute("arrayName",model.GetName() + "_ROI")

    def changementOfConnectedModel(self,landmarks, model, onSurface):
        landmarks.SetAttribute("connectedModelID",model.GetID())
        landmarks.SetAttribute("hardenModelID",model.GetAttribute("hardenModelID"))
        landmarkDescription = self.decodeJSON(landmarks.GetAttribute("landmarkDescription"))
        for n in range(landmarks.GetNumberOfMarkups()):
            markupID = landmarks.GetNthMarkupID(n)
            if onSurface:
                if landmarkDescription[markupID]["projection"]["isProjected"] == True:
                    hardenModel = slicer.app.mrmlScene().GetNodeByID(landmarks.GetAttribute("hardenModelID"))
                    landmarkDescription[markupID]["projection"]["closestPointIndex"] = \
                        self.projectOnSurface(hardenModel, landmarks, markupID)
            else:
                landmarkDescription[markupID]["projection"]["isProjected"] = False
                landmarkDescription[markupID]["projection"]["closestPointIndex"] = None
            landmarks.SetAttribute("landmarkDescription",self.encodeJSON(landmarkDescription))
        landmarks.SetAttribute("isClean",self.encodeJSON({"isClean":False}))

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
            tag = self.decodeJSON(landmarks.GetAttribute("MarkupAddedEventTag"))
            landmarks.RemoveObserver(tag["MarkupAddedEventTag"])
            print "adding observers removed!"
        except:
            pass
        try:
            tag = self.decodeJSON(landmarks.GetAttribute("UpdatesLinesEventTag"))
            landmarks.RemoveObserver(tag["UpdatesLinesEventTag"])
            print "lines observers removed!"
        except:
            pass
        try:
            tag = self.decodeJSON(landmarks.GetAttribute("PointModifiedEventTag"))
            landmarks.RemoveObserver(tag["PointModifiedEventTag"])
            print "moving observers removed!"
        except:
            pass
        try:
            tag = self.decodeJSON(landmarks.GetAttribute("MarkupRemovedEventTag"))
            landmarks.RemoveObserver(tag["MarkupRemovedEventTag"])
            print "removing observers removed!"
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
                landmarks.SetAttribute("hardenModelID",model.GetAttribute("hardenModelID"))
        # creation of the data structure
        else:
            self.createNewDataStructure(landmarks, model, onSurface)
        #update of the landmark Combo Box
        self.updateLandmarkComboBox(landmarks, self.interface.landmarkComboBox, False)
        self.updateLandmarkComboBox(landmarks, self.interface.landmarkComboBox1)
        self.updateLandmarkComboBox(landmarks, self.interface.landmarkComboBox2)
        #adding of listeners
        MarkupAddedEventTag = landmarks.AddObserver(landmarks.MarkupAddedEvent, self.onMarkupAddedEvent)
        landmarks.SetAttribute("MarkupAddedEventTag",self.encodeJSON({"MarkupAddedEventTag":MarkupAddedEventTag}))
        UpdatesLinesEventTag = landmarks.AddObserver(landmarks.PointModifiedEvent, self.updateLinesEvent)
        landmarks.SetAttribute("UpdatesLinesEventTag",self.encodeJSON({"UpdatesLinesEventTag":UpdatesLinesEventTag}))
        PointModifiedEventTag = landmarks.AddObserver(landmarks.PointModifiedEvent, self.onPointModifiedEvent)
        landmarks.SetAttribute("PointModifiedEventTag",self.encodeJSON({"PointModifiedEventTag":PointModifiedEventTag}))
        MarkupRemovedEventTag = landmarks.AddObserver(landmarks.MarkupRemovedEvent, self.onMarkupRemovedEvent)
        landmarks.SetAttribute("MarkupRemovedEventTag",self.encodeJSON({"MarkupRemovedEventTag":MarkupRemovedEventTag}))

    # Called when a landmark is added on a model
    def onMarkupAddedEvent(self, obj, event):
        print "------markup adding-------"
        landmarkDescription = self.decodeJSON(obj.GetAttribute("landmarkDescription"))
        numOfMarkups = obj.GetNumberOfMarkups()
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
        obj.SetAttribute("landmarkDescription",self.encodeJSON(landmarkDescription))
        self.updateAllLandmarkComboBox(obj, markupID)
        self.interface.UpdateInterface()
        self.onPointModifiedEvent(obj,None)

    def updateLinesEvent(self, obj, event):
        if self.interface.line1LAComboBox.currentText != '' and self.interface.line1LBComboBox.currentText != '' \
                and self.interface.line1LAComboBox.currentText != self.interface.line1LBComboBox.currentText :
            # Clear Lines, then define new ones
            if self.interface.renderer1 :
                self.interface.renderer1.RemoveActor(self.interface.actor1)
            self.interface.renderer1, self.interface.actor1 = \
                self.drawLineBetween2Landmark(self.interface.line1LAComboBox.currentText,
                                              self.interface.line1LBComboBox.currentText,
                                              self.interface.fidListComboBoxline1LA.currentNode(),
                                              self.interface.fidListComboBoxline1LB.currentNode())
        if self.interface.line2LAComboBox.currentText != '' and self.interface.line2LBComboBox.currentText != '' \
                and self.interface.line2LAComboBox.currentText != self.interface.line2LBComboBox.currentText :
            if self.interface.renderer2 :
                self.interface.renderer2.RemoveActor(self.interface.actor2)
            self.interface.renderer2, self.interface.actor2 = \
                self.drawLineBetween2Landmark(self.interface.line2LAComboBox.currentText,
                                              self.interface.line2LBComboBox.currentText,
                                              self.interface.fidListComboBoxline2LA.currentNode(),
                                              self.interface.fidListComboBoxline2LB.currentNode())
        if self.interface.lineLAComboBox.currentText != '' and self.interface.lineLBComboBox.currentText != '' \
                and self.interface.lineLAComboBox.currentText != self.interface.lineLBComboBox.currentText :
            if self.interface.renderer3 :
                self.interface.renderer3.RemoveActor(self.interface.actor3)
            self.interface.renderer3, self.interface.actor3 = \
                self.drawLineBetween2Landmark(self.interface.lineLAComboBox.currentText,
                                              self.interface.lineLBComboBox.currentText,
                                              self.interface.fidListComboBoxlineLA.currentNode(),
                                              self.interface.fidListComboBoxlineLB.currentNode())

    def updateMidPoint(self, fidList, landmarkID):
        landmarkDescription = self.decodeJSON(fidList.GetAttribute("landmarkDescription"))
        for midPointID in landmarkDescription[landmarkID]["midPoint"]["definedByThisMarkup"]:
            if landmarkDescription[midPointID]["midPoint"]["isMidPoint"]:
                landmark1ID = landmarkDescription[midPointID]["midPoint"]["Point1"]
                landmark2ID = landmarkDescription[midPointID]["midPoint"]["Point2"]
                coord = self.calculateMidPointCoord(fidList, landmark1ID, landmark2ID)
                index = fidList.GetMarkupIndexByID(midPointID)
                fidList.SetNthFiducialPositionFromArray(index, coord)
                if landmarkDescription[midPointID]["projection"]["isProjected"]:
                    hardenModel = slicer.app.mrmlScene().GetNodeByID(fidList.GetAttribute("hardenModelID"))
                    landmarkDescription[midPointID]["projection"]["closestPointIndex"] = \
                        self.projectOnSurface(hardenModel, fidList, midPointID)
                    fidList.SetAttribute("landmarkDescription",self.encodeJSON(landmarkDescription))
                self.updateMidPoint(fidList, midPointID)

    # Called when a landmarks is moved
    def onPointModifiedEvent(self, obj, event):
        print "----onPointModifiedEvent Q3DC-----"
        landmarkDescription = self.decodeJSON(obj.GetAttribute("landmarkDescription"))
        if not landmarkDescription:
            return
        selectedLandmarkID = self.findIDFromLabel(obj, self.interface.landmarkComboBox.currentText)
        # remove observer to make sure, the callback function won't work..
        tag = self.decodeJSON(obj.GetAttribute("PointModifiedEventTag"))
        obj.RemoveObserver(tag["PointModifiedEventTag"])
        if selectedLandmarkID:
            activeLandmarkState = landmarkDescription[selectedLandmarkID]
            print activeLandmarkState
            if activeLandmarkState["projection"]["isProjected"]:
                hardenModel = slicer.app.mrmlScene().GetNodeByID(obj.GetAttribute("hardenModelID"))
                activeLandmarkState["projection"]["closestPointIndex"] = \
                    self.projectOnSurface(hardenModel, obj, selectedLandmarkID)
                obj.SetAttribute("landmarkDescription",self.encodeJSON(landmarkDescription))
            self.updateMidPoint(obj,selectedLandmarkID)
            self.findROI(obj)
        time.sleep(0.08)
        # Add the observer again
        PointModifiedEventTag = obj.AddObserver(obj.PointModifiedEvent, self.onPointModifiedEvent)
        obj.SetAttribute("PointModifiedEventTag",self.encodeJSON({"PointModifiedEventTag":PointModifiedEventTag}))

    def onMarkupRemovedEvent(self, obj, event):
        print "------markup deleting-------"
        landmarkDescription = self.decodeJSON(obj.GetAttribute("landmarkDescription"))
        IDs = []
        for ID, value in landmarkDescription.iteritems():
            isFound = False
            for n in range(obj.GetNumberOfMarkups()):
                markupID = obj.GetNthMarkupID(n)
                if ID == markupID:
                    isFound = True
            if not isFound:
                IDs.append(ID)
        for ID in IDs:
            self.deleteLandmark(obj, landmarkDescription[ID]["landmarkLabel"])
            landmarkDescription.pop(ID,None)
        obj.SetAttribute("landmarkDescription",self.encodeJSON(landmarkDescription))

    def addLandmarkToCombox(self, fidList, combobox, markupID):
        if not fidList:
            return
        landmarkDescription = self.decodeJSON(fidList.GetAttribute("landmarkDescription"))
        combobox.addItem(landmarkDescription[markupID]["landmarkLabel"])

    def updateAllLandmarkComboBox(self, fidList, markupID):
        # update of the Combobox that are always updated
        self.updateLandmarkComboBox(fidList, self.interface.landmarkComboBox, False)
        self.addLandmarkToCombox(fidList, self.interface.landmarkComboBox1, markupID)
        self.addLandmarkToCombox(fidList, self.interface.landmarkComboBox2, markupID)
        #update of the Comboboxes that display the fidcial list just modified
        for key,value in self.comboboxdict.iteritems():
            if value is fidList:
                self.addLandmarkToCombox(fidList, key, markupID)

    def updateLandmarkComboBox(self, fidList, combobox, displayMidPoint = True):
        combobox.blockSignals(True)
        combobox.clear()
        if not fidList:
            return
        landmarkDescription = self.decodeJSON(fidList.GetAttribute("landmarkDescription"))
        if not fidList:
            return
        numOfFid = fidList.GetNumberOfMarkups()
        if numOfFid > 0:
            for i in range(0, numOfFid):
                if displayMidPoint is False:
                    ID = fidList.GetNthMarkupID(i)
                    if not landmarkDescription[ID]["midPoint"]["isMidPoint"]:
                        landmarkLabel = fidList.GetNthMarkupLabel(i)
                        combobox.addItem(landmarkLabel)
                else:
                    landmarkLabel = fidList.GetNthMarkupLabel(i)
                    combobox.addItem(landmarkLabel)
        combobox.setCurrentIndex(combobox.count - 1)
        combobox.blockSignals(False)


    def deleteLandmark(self, fidList, label):
        # update of the Combobox that are always updated
        self.interface.landmarkComboBox.removeItem(self.interface.landmarkComboBox.findText(label))
        self.interface.landmarkComboBox1.removeItem(self.interface.landmarkComboBox1.findText(label))
        self.interface.landmarkComboBox2.removeItem(self.interface.landmarkComboBox2.findText(label))
        for key,value in self.comboboxdict.iteritems():
            if value is fidList:
                key.removeItem(key.findText(label))

    def findIDFromLabel(self, fidList, landmarkLabel):
        # find the ID of the markupsNode from the label of a landmark!
        landmarkDescription = self.decodeJSON(fidList.GetAttribute("landmarkDescription"))
        for ID, value in landmarkDescription.iteritems():
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

    def replaceLandmark(self, inputModelPolyData, fidNode, landmarkID, indexClosestPoint):
        landmarkCoord = [-1, -1, -1]
        inputModelPolyData.GetPoints().GetPoint(indexClosestPoint, landmarkCoord)
        print landmarkCoord
        fidNode.SetNthFiducialPositionFromArray(landmarkID,landmarkCoord)

    def projectOnSurface(self, modelOnProject, fidNode, selectedFidReflID):
        if selectedFidReflID:
            markupsIndex = fidNode.GetMarkupIndexByID(selectedFidReflID)
            indexClosestPoint = self.getClosestPointIndex(fidNode, modelOnProject.GetPolyData(), markupsIndex)
            self.replaceLandmark(modelOnProject.GetPolyData(), fidNode, markupsIndex, indexClosestPoint)
            return indexClosestPoint

    def calculateMidPointCoord(self, fidList, landmark1ID, landmark2ID):
        """Set the midpoint when you know the the mrml nodes"""
        landmark1Index = fidList.GetMarkupIndexByID(landmark1ID)
        landmark2Index = fidList.GetMarkupIndexByID(landmark2ID)
        coord1 = [-1, -1, -1]
        coord2 = [-1, -1, -1]
        fidList.GetNthFiducialPosition(landmark1Index, coord1)
        fidList.GetNthFiducialPosition(landmark2Index, coord2)
        midCoord = [-1, -1, -1]
        midCoord[0] = (coord1[0] + coord2[0])/2
        midCoord[1] = (coord1[1] + coord2[1])/2
        midCoord[2] = (coord1[2] + coord2[2])/2
        return midCoord

    def removecomponentFromStorage(self, type, element):
        if type == 'angles':
            element.Yaw = None
            element.Roll = None
            element.Pitch = None
        if type == 'distance':
            element.RLComponent = None
            element.APComponent = None
            element.SIComponent = None
            element.ThreeDComponent = None
        return element

    def defineDistances(self, markupsNode1, landmark1Index, markupsNode2, landmark2Index):
        coord1 = [-1, -1, -1]
        coord2 = [-1, -1, -1]
        markupsNode1.GetNthFiducialPosition(landmark1Index, coord1)
        markupsNode2.GetNthFiducialPosition(landmark2Index, coord2)
        diffRAxis = coord2[0] - coord1[0]
        diffAAxis = coord2[1] - coord1[1]
        diffSAxis = coord2[2] - coord1[2]
        threeDDistance = math.sqrt(vtk.vtkMath().Distance2BetweenPoints(coord1, coord2))
        return round(diffRAxis, self.numberOfDecimals),\
               round(diffAAxis, self.numberOfDecimals),\
               round(diffSAxis, self.numberOfDecimals),\
               round(threeDDistance, self.numberOfDecimals)

    def addOnDistanceList(self, distanceList, fidLabel1, fidLabel2, fidlist1, fidlist2):
        fidID1 = self.findIDFromLabel(fidlist1,fidLabel1)
        fidID2 = self.findIDFromLabel(fidlist2,fidLabel2)
        landmark1Index = fidlist1.GetMarkupIndexByID(fidID1)
        landmark2Index = fidlist2.GetMarkupIndexByID(fidID2)
        elementToAdd = self.distanceValuesStorage()
        # if this distance has already been computed before -> replace values
        for element in distanceList:
            if element.startLandmarkID == fidID1 and element.endLandmarkID == fidID2:
                element = self.removecomponentFromStorage('distance', element)
                element.startLandmarkName = fidLabel1
                element.endLandmarkName = fidLabel2
                element.RLComponent, element.APComponent, element.SIComponent, element.ThreeDComponent = \
                    self.defineDistances(fidlist1, landmark1Index, fidlist2, landmark2Index)
                return distanceList
        elementToAdd.startLandmarkID = fidID1
        elementToAdd.endLandmarkID = fidID2
        elementToAdd.startLandmarkName = fidLabel1
        elementToAdd.endLandmarkName = fidLabel2
        elementToAdd.RLComponent, elementToAdd.APComponent, elementToAdd.SIComponent, elementToAdd.ThreeDComponent = \
            self.defineDistances(fidlist1, landmark1Index, fidlist2, landmark2Index)
        distanceList.append(elementToAdd)
        return distanceList

    def defineDistanceTable(self, table, distanceList):
        table.clear()
        table.setRowCount(distanceList.__len__())
        table.setColumnCount(5)
        table.setMinimumHeight(50*distanceList.__len__())
        table.setHorizontalHeaderLabels(['  ', ' R-L Component', ' A-P Component', ' S-I Component', ' 3D Distance '])
        i = 0
        for element in distanceList:
            startLandName = element.startLandmarkName
            endLandName = element.endLandmarkName
            label = qt.QLabel(' ' + startLandName + ' - ' + endLandName + ' ')
            label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
            table.setCellWidget(i, 0,label)
            if element.RLComponent != None:
                label = qt.QLabel(element.RLComponent)
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 1, label)
            else:
                label = qt.QLabel(' - ')
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 1, label)

            if element.APComponent != None:
                label = qt.QLabel(element.APComponent)
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 2, label)
            else:
                label = qt.QLabel(' - ')
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 2, label)

            if element.SIComponent != None:
                label = qt.QLabel(element.SIComponent)
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 3, label)
            else:
                label = qt.QLabel(' - ')
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 3, label)

            if element.ThreeDComponent != None:
                label = qt.QLabel(element.ThreeDComponent)
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 4, label)
            else:
                label = qt.QLabel(' - ')
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 4, label)

            i += 1
        return table

    def computePitch(self, markupsNode1, landmark1Index,
                     markupsNode2, landmark2Index,
                     markupsNode3, landmark3Index,
                     markupsNode4, landmark4Index):
        # Pitch is computed by projection on the plan (y,z)
        coord1 = [-1, -1, -1]
        coord2 = [-1, -1, -1]
        coord3 = [-1, -1, -1]
        coord4 = [-1, -1, -1]

        markupsNode1.GetNthFiducialPosition(landmark1Index, coord1)
        markupsNode2.GetNthFiducialPosition(landmark2Index, coord2)
        markupsNode3.GetNthFiducialPosition(landmark3Index, coord3)
        markupsNode4.GetNthFiducialPosition(landmark4Index, coord4)

        vectLine1 = [0, coord2[1]-coord1[1], coord2[2]-coord1[2] ]
        normVectLine1 = numpy.sqrt( vectLine1[1]*vectLine1[1] + vectLine1[2]*vectLine1[2] )
        vectLine2 = [0, coord4[1]-coord3[1], coord4[2]-coord3[2] ]
        normVectLine2 = numpy.sqrt( vectLine2[1]*vectLine2[1] + vectLine2[2]*vectLine2[2] )
        pitchNotSigned = round(vtk.vtkMath().DegreesFromRadians(vtk.vtkMath().AngleBetweenVectors(vectLine1, vectLine2)),
                               self.numberOfDecimals)

        if normVectLine1 != 0 and normVectLine2 != 0:
            normalizedVectLine1 = [0, (1/normVectLine1)*vectLine1[1], (1/normVectLine1)*vectLine1[2]]
            normalizedVectLine2 = [0, (1/normVectLine2)*vectLine2[1], (1/normVectLine2)*vectLine2[2]]
            det2D = normalizedVectLine1[1]*normalizedVectLine2[2] - normalizedVectLine1[2]*normalizedVectLine2[1]
            return math.copysign(pitchNotSigned, det2D)
        else:
            slicer.util.errorDisplay("ERROR, norm of your vector is 0! DEFINE A VECTOR!")
            return None

    def computeRoll(self, markupsNode1, landmark1Index,
                    markupsNode2, landmark2Index,
                    markupsNode3, landmark3Index,
                    markupsNode4, landmark4Index):
        # Roll is computed by projection on the plan (x,z)
        coord1 = [-1, -1, -1]
        coord2 = [-1, -1, -1]
        coord3 = [-1, -1, -1]
        coord4 = [-1, -1, -1]

        markupsNode1.GetNthFiducialPosition(landmark1Index, coord1)
        markupsNode2.GetNthFiducialPosition(landmark2Index, coord2)
        markupsNode3.GetNthFiducialPosition(landmark3Index, coord3)
        markupsNode4.GetNthFiducialPosition(landmark4Index, coord4)

        vectLine1 = [coord2[0]-coord1[0], 0, coord2[2]-coord1[2] ]
        normVectLine1 = numpy.sqrt( vectLine1[0]*vectLine1[0] + vectLine1[2]*vectLine1[2] )
        vectLine2 = [coord4[0]-coord3[0], 0, coord4[2]-coord3[2] ]
        normVectLine2 = numpy.sqrt( vectLine2[0]*vectLine2[0] + vectLine2[2]*vectLine2[2] )
        rollNotSigned = round(vtk.vtkMath().DegreesFromRadians(vtk.vtkMath().AngleBetweenVectors(vectLine1, vectLine2)),
                              self.numberOfDecimals)

        if normVectLine1 != 0 and normVectLine2 != 0:
            normalizedVectLine1 = [(1/normVectLine1)*vectLine1[0], 0, (1/normVectLine1)*vectLine1[2]]
            normalizedVectLine2 = [(1/normVectLine2)*vectLine2[0], 0, (1/normVectLine2)*vectLine2[2]]
            det2D = normalizedVectLine1[0]*normalizedVectLine2[2] - normalizedVectLine1[2]*normalizedVectLine2[0]
            return math.copysign(rollNotSigned, det2D)
        else:
            print (" ERROR, norm of your vector is 0! DEFINE A VECTOR!")
            return None

    def computeYaw(self, markupsNode1, landmark1Index,
                   markupsNode2, landmark2Index,
                   markupsNode3, landmark3Index,
                   markupsNode4, landmark4Index):
        # Yaw is computed by projection on the plan (x,y)
        coord1 = [-1, -1, -1]
        coord2 = [-1, -1, -1]
        coord3 = [-1, -1, -1]
        coord4 = [-1, -1, -1]

        markupsNode1.GetNthFiducialPosition(landmark1Index, coord1)
        markupsNode2.GetNthFiducialPosition(landmark2Index, coord2)
        markupsNode3.GetNthFiducialPosition(landmark3Index, coord3)
        markupsNode4.GetNthFiducialPosition(landmark4Index, coord4)

        vectLine1 = [coord2[0]-coord1[0], coord2[1]-coord1[1], 0 ]
        normVectLine1 = numpy.sqrt( vectLine1[0]*vectLine1[0] + vectLine1[1]*vectLine1[1] )
        vectLine2 = [coord4[0]-coord3[0],coord4[1]-coord3[1], 0]
        normVectLine2 = numpy.sqrt( vectLine2[0]*vectLine2[0] + vectLine2[1]*vectLine2[1] )
        yawNotSigned = round(vtk.vtkMath().DegreesFromRadians(vtk.vtkMath().AngleBetweenVectors(vectLine1, vectLine2)),
                             self.numberOfDecimals)

        if normVectLine1 != 0 and normVectLine2 != 0:
            normalizedVectLine1 = [(1/normVectLine1)*vectLine1[0], (1/normVectLine1)*vectLine1[1], 0]
            normalizedVectLine2 = [(1/normVectLine2)*vectLine2[0], (1/normVectLine2)*vectLine2[1], 0]
            det2D = normalizedVectLine1[0]*normalizedVectLine2[1] - normalizedVectLine1[1]*normalizedVectLine2[0]
            return math.copysign(yawNotSigned, det2D)
        else:
            slicer.util.errorDisplay("ERROR, norm of your vector is 0! DEFINE A VECTOR!")
            return None

    def addOnAngleList(self, angleList,
                       fidLabel1A, fidLabel1B, fidlist1A, fidlist1B,
                       fidLabel2A, fidLabel2B, fidlist2A, fidlist2B,
                       PitchState, YawState, RollState):
        fidID1A = self.findIDFromLabel(fidlist1A,fidLabel1A)
        fidID1B= self.findIDFromLabel(fidlist1B,fidLabel1B)
        fidID2A = self.findIDFromLabel(fidlist2A,fidLabel2A)
        fidID2B = self.findIDFromLabel(fidlist2B,fidLabel2B)
        landmark1Index = fidlist1A.GetMarkupIndexByID(fidID1A)
        landmark2Index = fidlist1B.GetMarkupIndexByID(fidID1B)
        landmark3Index = fidlist2A.GetMarkupIndexByID(fidID2A)
        landmark4Index = fidlist2B.GetMarkupIndexByID(fidID2B)
        # if angles has already been computed before -> replace values
        elementToAdd = self.angleValuesStorage()
        for element in angleList:
            if element.landmarkALine1ID == fidID1A and\
                            element.landmarkBLine1ID == fidID1B and\
                            element.landmarkALine2ID == fidID2A and\
                            element.landmarkBLine2ID == fidID2B:
                element = self.removecomponentFromStorage('angles', element)
                if PitchState:
                    element.Pitch = self.computePitch(fidlist1A, landmark1Index,
                                                      fidlist1B, landmark2Index,
                                                      fidlist2A, landmark3Index,
                                                      fidlist2B, landmark4Index)
                if RollState:
                    element.Roll = self.computeRoll(fidlist1A, landmark1Index,
                                                    fidlist1B, landmark2Index,
                                                    fidlist2A, landmark3Index,
                                                    fidlist2B, landmark4Index)
                if YawState:
                    element.Yaw = self.computeYaw(fidlist1A, landmark1Index,
                                                  fidlist1B, landmark2Index,
                                                  fidlist2A, landmark3Index,
                                                  fidlist2B, landmark4Index)
                element.landmarkALine1Name = fidLabel1A
                element.landmarkBLine1Name = fidLabel1B
                element.landmarkALine2Name = fidLabel2A
                element.landmarkBLine2Name = fidLabel2B
                return angleList
        # create a new element depending on what the user wants
        elementToAdd.landmarkALine1ID = fidID1A
        elementToAdd.landmarkBLine1ID = fidID1B
        elementToAdd.landmarkALine2ID = fidID2A
        elementToAdd.landmarkBLine2ID = fidID2B
        elementToAdd.landmarkALine1Name = fidLabel1A
        elementToAdd.landmarkBLine1Name = fidLabel1B
        elementToAdd.landmarkALine2Name = fidLabel2A
        elementToAdd.landmarkBLine2Name = fidLabel2B
        if PitchState:
            elementToAdd.Pitch = self.computePitch(fidlist1A, landmark1Index,
                                                   fidlist1B, landmark2Index,
                                                   fidlist2A, landmark3Index,
                                                   fidlist2B, landmark4Index)
        if RollState:
            elementToAdd.Roll = self.computeRoll(fidlist1A, landmark1Index,
                                                 fidlist1B, landmark2Index,
                                                 fidlist2A, landmark3Index,
                                                 fidlist2B, landmark4Index)
        if YawState:
            elementToAdd.Yaw = self.computeYaw(fidlist1A, landmark1Index,
                                               fidlist1B, landmark2Index,
                                               fidlist2A, landmark3Index,
                                               fidlist2B, landmark4Index)
        angleList.append(elementToAdd)
        return angleList

    def defineAnglesTable(self, table, angleList):

        table.clear()
        table.setRowCount(angleList.__len__())
        table.setColumnCount(4)
        table.setMinimumHeight(50*angleList.__len__())
        table.setHorizontalHeaderLabels([' ', ' YAW ', ' PITCH ', ' ROLL '])
        i = 0

        for element in angleList:
            landmarkALine1Name = element.landmarkALine1Name
            landmarkBLine1Name = element.landmarkBLine1Name
            landmarkALine2Name = element.landmarkALine2Name
            landmarkBLine2Name = element.landmarkBLine2Name

            label = qt.QLabel(' ' + landmarkALine1Name + '-' + landmarkBLine1Name + ' / ' + landmarkALine2Name + '-' + landmarkBLine2Name)
            label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
            table.setCellWidget(i, 0, label)
            if element.Yaw != None:
                sign = numpy.sign(element.Yaw)
                label = qt.QLabel(str(element.Yaw)+' / '+str(sign*(180-abs(element.Yaw))))
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 1, label)
            else:
                label = qt.QLabel(' - ')
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 1, label)

            if element.Pitch != None:
                sign = numpy.sign(element.Pitch)
                label = qt.QLabel(str(element.Pitch) + ' / ' + str(sign*(180 - abs(element.Pitch))))
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 2, label)
            else:
                label = qt.QLabel(' - ')
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 2, label)

            if element.Roll != None:
                sign = numpy.sign(element.Roll)
                label = qt.QLabel(str(element.Roll) + ' / ' + str(sign * (180 - abs(element.Roll))))
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 3, label)
            else:
                label = qt.QLabel(' - ')
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 3, label)

            i += 1
        return table

    def defineDistancesLinePoint(self, markupsNodeLine1, landmarkLine1Index,
                                 markupsNodeLine2, landmarkLine2Index,
                                 markupsNodepoint, landmarkpointIndex):
        line = vtk.vtkLine()
        coordLine1 = [-1, -1, -1]
        coordLine2 = [-1, -1, -1]
        coordPoint = [-1, -1, -1]
        markupsNodeLine1.GetNthFiducialPosition(landmarkLine1Index, coordLine1)
        markupsNodeLine2.GetNthFiducialPosition(landmarkLine2Index, coordLine2)
        markupsNodepoint.GetNthFiducialPosition(landmarkpointIndex, coordPoint)
        parametric = vtk.mutable(0)
        projectCoord = [0, 0, 0]
        distance = line.DistanceToLine(coordPoint, coordLine1, coordLine2, parametric, projectCoord)
        diffRAxis = coordPoint[0] - projectCoord[0]
        diffAAxis = coordPoint[1] - projectCoord[1]
        diffSAxis = coordPoint[2] - projectCoord[2]
        return round(diffRAxis, self.numberOfDecimals), \
               round(diffAAxis, self.numberOfDecimals), \
               round(diffSAxis, self.numberOfDecimals), \
               round(math.sqrt(distance), self.numberOfDecimals)

    def addOnLinePointList(self, linePointList,
                           fidLabelLineA, fidLabelLineB,
                           fidListLineLA, fidListLineLB,
                           fidLabelPoint, fidListPoint):
        lineLAID = self.findIDFromLabel(fidListLineLA, fidLabelLineA)
        lineLAIndex = fidListLineLA.GetMarkupIndexByID(lineLAID)
        lineLBID = self.findIDFromLabel(fidListLineLB, fidLabelLineB)
        lineLBIndex = fidListLineLB.GetMarkupIndexByID(lineLBID)
        PointID = self.findIDFromLabel(fidListPoint, fidLabelPoint)
        PointIndex = fidListPoint.GetMarkupIndexByID(PointID)
        elementToAdd = self.distanceLinePointStorage()
        # if this distance has already been computed before -> replace values
        for element in linePointList:
            if element.landmarkALineID == lineLAID and \
                            element.landmarkBLineID == lineLBID and\
                            element.landmarkPointID == PointID:
                element = self.removecomponentFromStorage('distance', element)
                element.landmarkALineID = lineLAID
                element.landmarkBLineID = lineLBID
                element.landmarkPointID = PointID
                element.landmarkALineName = fidLabelLineA
                element.landmarkBLineName = fidLabelLineB
                element.landmarkPointName = fidLabelPoint
                element.RLComponent, element.APComponent, element.SIComponent, element.ThreeDComponent = \
                    self.defineDistancesLinePoint(fidListLineLA, lineLAIndex,
                                                  fidListLineLB, lineLBIndex,
                                                  fidListPoint, PointIndex)
                return linePointList
        elementToAdd.landmarkALineID = lineLAID
        elementToAdd.landmarkBLineID = lineLBID
        elementToAdd.landmarkPointID = PointID
        elementToAdd.landmarkALineName = fidLabelLineA
        elementToAdd.landmarkBLineName = fidLabelLineB
        elementToAdd.landmarkPointName = fidLabelPoint
        elementToAdd.RLComponent, elementToAdd.APComponent, elementToAdd.SIComponent, elementToAdd.ThreeDComponent = \
            self.defineDistancesLinePoint(fidListLineLA, lineLAIndex,
                                          fidListLineLB, lineLBIndex,
                                          fidListPoint, PointIndex)
        linePointList.append(elementToAdd)
        return linePointList

    def defineDistanceLinePointTable(self, table, distanceList):
        table.clear()
        table.setRowCount(distanceList.__len__())
        table.setColumnCount(5)
        table.setMinimumHeight(50*distanceList.__len__())
        table.setHorizontalHeaderLabels(['  ', ' R-L Component', ' A-P Component', ' S-I Component', ' 3D Distance '])
        i = 0
        for element in distanceList:
            landmarkALineName = element.landmarkALineName
            landmarkBLineName = element.landmarkBLineName
            landmarkPoint = element.landmarkPointName

            label = qt.QLabel(' ' + str(landmarkALineName) + ' - ' + str(landmarkBLineName) + ' / ' + str(landmarkPoint) + ' ')
            label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
            table.setCellWidget(i, 0,label)
            if element.RLComponent != None:
                label = qt.QLabel(element.RLComponent)
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 1, label)
            else:
                label = qt.QLabel(' - ')
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 1, label)

            if element.APComponent != None:
                label = qt.QLabel(element.APComponent)
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 2, label)
            else:
                label = qt.QLabel(' - ')
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 2, label)

            if element.SIComponent != None:
                label = qt.QLabel(element.SIComponent)
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 3, label)
            else:
                label = qt.QLabel(' - ')
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 3, label)

            if element.ThreeDComponent != None:
                label = qt.QLabel(element.ThreeDComponent)
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 4, label)
            else:
                label = qt.QLabel(' - ')
                label.setStyleSheet('QLabel{qproperty-alignment:AlignCenter;}')
                table.setCellWidget(i, 4, label)

            i += 1
        return table

    def drawLineBetween2Landmark(self, landmark1label, landmark2label, fidList1, fidList2):
        if not fidList1 or not fidList2 or not landmark1label or not landmark2label:
            return
        landmark1ID = self.findIDFromLabel(fidList1, landmark1label)
        landmark2ID = self.findIDFromLabel(fidList2, landmark2label)

        if not fidList1 or not fidList2:
            return None, None
        landmark1Index = fidList1.GetMarkupIndexByID(landmark1ID)
        landmark2Index = fidList2.GetMarkupIndexByID(landmark2ID)

        coord1 = [-1, -1, -1]
        coord2 = [-1, -1, -1]
        fidList1.GetNthFiducialPosition(landmark1Index, coord1)
        fidList2.GetNthFiducialPosition(landmark2Index, coord2)

        line = vtk.vtkLineSource()
        line.SetPoint1(coord1)
        line.SetPoint2(coord2)
        line.Update()

        mapper = vtk.vtkPolyDataMapper()
        actor = vtk.vtkActor()
        mapper.SetInputData(line.GetOutput())
        mapper.Update()
        actor.SetMapper(mapper)

        layoutManager = slicer.app.layoutManager()
        threeDWidget = layoutManager.threeDWidget(0)
        threeDView = threeDWidget.threeDView()
        renderWindow = threeDView.renderWindow()
        renderers = renderWindow.GetRenderers()
        renderer = renderers.GetFirstRenderer()
        renderWindow.AddRenderer(renderer)
        renderer.AddActor(actor)
        renderWindow.Render()

        return renderer, actor

    def exportationFunction(self, directoryExport, listToExport, typeCalculation):
        directory = directoryExport.directory.encode('utf-8')
        messageBox = ctk.ctkMessageBox()
        messageBox.setWindowTitle(' /!\ WARNING /!\ ')
        messageBox.setIcon(messageBox.Warning)

        fileName = directory + '/' + typeCalculation + '.csv'
        if os.path.exists(fileName):
            messageBox.setText('File ' + fileName + ' already exists!')
            messageBox.setInformativeText('Do you want to replace it ?')
            messageBox.setStandardButtons( messageBox.No | messageBox.Yes)
            choice = messageBox.exec_()
            if choice == messageBox.No:
                return
        self.exportAsCSV(fileName, listToExport, typeCalculation)
        slicer.util.delayDisplay("Saved to fileName")


    def exportAsCSV(self,filename, listToExport, typeCalculation):
        #  Export fields on different csv files
        file = open(filename, 'w')
        cw = csv.writer(file, delimiter=',')
        print typeCalculation
        if typeCalculation == 'distance':
            cw.writerow([' Landmark A - Landmark B',  ' R-L Component', ' A-P Component', ' S-I Component', ' 3D Distance '])
            self.writeDistance(cw, listToExport)
        elif typeCalculation == 'linePoint':
            cw.writerow([' Landmark A - Landmark B',  ' R-L Component', ' A-P Component', ' S-I Component', ' 3D Distance '])
            self.writeLinePoint(cw, listToExport)
        else:
            cw.writerow([' Line 1 (Landmark A - Landmark B) /  Line 2 (Landmark A - Landmark B)',  ' YAW ', ' PITCH ', ' ROLL '])
            self.writeAngle(cw, listToExport)
        file.close()
        if self.decimalPoint != '.':
            self.replaceCharac(filename, ',', ';') # change the Delimiter and put a semicolon instead of a comma
            self.replaceCharac(filename, '.', self.decimalPoint) # change the decimal separator '.' for a comma

    def writeDistance(self, fileWriter, listToExport):
        for element in listToExport:
            startLandName = element.startLandmarkName
            endLandName = element.endLandmarkName
            label = startLandName + ' - ' + endLandName
            fileWriter.writerow([label,
                                 element.RLComponent,
                                 element.APComponent,
                                 element.SIComponent,
                                 element.ThreeDComponent])

    def writeLinePoint(self, fileWriter, listToExport):
        for element in listToExport:
            landmarkALineName = element.landmarkALineName
            landmarkBLineName = element.landmarkBLineName
            landmarkPoint = element.landmarkPointName
            label = landmarkALineName + ' - ' + landmarkBLineName + ' / ' + landmarkPoint
            fileWriter.writerow([label,
                                 element.RLComponent,
                                 element.APComponent,
                                 element.SIComponent,
                                 element.ThreeDComponent])

    def writeAngle(self, fileWriter, listToExport):
        for element in listToExport:
            print "element"
            print element
            landmarkALine1Name = element.landmarkALine1Name
            landmarkBLine1Name = element.landmarkBLine1Name
            landmarkALine2Name = element.landmarkALine2Name
            landmarkBLine2Name = element.landmarkBLine2Name

            label = landmarkALine1Name + '-' + landmarkBLine1Name + ' | ' + landmarkALine2Name + '-' + landmarkBLine2Name
            signY = numpy.sign(element.Yaw)
            signP = numpy.sign(element.Pitch)
            signR = numpy.sign(element.Roll)

            if element.Yaw:
                YawLabel = str(element.Yaw) +' | '+str(signY*(180-abs(element.Yaw)))
            else:
                YawLabel = '-'

            if element.Pitch:
                PitchLabel = str(element.Pitch)+' | '+str(signP*(180-abs(element.Pitch)))
            else:
                PitchLabel = '-'

            if element.Roll:
                RollLabel = str(element.Roll)+' | '+str(signR*(180-abs(element.Roll)))
            else:
                RollLabel = '-'

            fileWriter.writerow([label,
                                 YawLabel,
                                 PitchLabel,
                                 RollLabel])

    def replaceCharac(self, filename, oldCharac, newCharac):
        #  Function to replace a charactere (oldCharac) in a file (filename) by a new one (newCharac)
        file = open(filename,'r')
        lines = file.readlines()
        with open(filename, 'r') as file:
            lines = [line.replace(oldCharac, newCharac) for line in file.readlines()]
        file.close()
        file = open(filename, 'w')
        file.writelines(lines)
        file.close()

    def GetConnectedVertices(self, connectedVerticesIDList, polyData, pointID):
        # Return IDs of all the vertices that compose the first neighbor.
        cellList = vtk.vtkIdList()
        connectedVerticesIDList.InsertUniqueId(pointID)
        # Get cells that vertex 'pointID' belongs to
        polyData.GetPointCells(pointID, cellList)
        numberOfIds = cellList.GetNumberOfIds()
        for i in range(0, numberOfIds):
            # Get points which compose all cells
            pointIdList = vtk.vtkIdList()
            polyData.GetCellPoints(cellList.GetId(i), pointIdList)
            for j in range(0, pointIdList.GetNumberOfIds()):
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
        for i in range(0, inputModelNodePolydata.GetNumberOfPoints()):
            arrayToAdd.InsertNextValue(0.0)
        for i in range(0, numberofIds):
            arrayToAdd.SetValue(connectedIdList.GetId(i), 1.0)
        lut = vtk.vtkLookupTable()
        tableSize = 2
        lut.SetNumberOfTableValues(tableSize)
        lut.Build()
        displayNode = inputModelNode.GetDisplayNode()
        rgb = displayNode.GetColor()
        lut.SetTableValue(0, rgb[0], rgb[1], rgb[2], 1)
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
        hardenModel = slicer.app.mrmlScene().GetNodeByID(fidList.GetAttribute("hardenModelID"))
        connectedModel = slicer.app.mrmlScene().GetNodeByID(fidList.GetAttribute("connectedModelID"))
        landmarkDescription = self.decodeJSON(fidList.GetAttribute("landmarkDescription"))
        arrayName = fidList.GetAttribute("arrayName")
        ROIPointListID = vtk.vtkIdList()
        for key,activeLandmarkState in landmarkDescription.iteritems():
            tempROIPointListID = vtk.vtkIdList()
            if activeLandmarkState["ROIradius"] != 0:
                self.defineNeighbor(tempROIPointListID,
                                    hardenModel.GetPolyData(),
                                    activeLandmarkState["projection"]["closestPointIndex"],
                                    activeLandmarkState["ROIradius"])
            for j in range(0, tempROIPointListID.GetNumberOfIds()):
                ROIPointListID.InsertUniqueId(tempROIPointListID.GetId(j))
        listID = ROIPointListID
        self.addArrayFromIdList(listID, connectedModel, arrayName)
        self.displayROI(connectedModel, arrayName)
        return ROIPointListID

    def warningMessage(self, message):
        messageBox = ctk.ctkMessageBox()
        messageBox.setWindowTitle(" /!\ WARNING /!\ ")
        messageBox.setIcon(messageBox.Warning)
        messageBox.setText(message)
        messageBox.setStandardButtons(messageBox.Ok)
        messageBox.exec_()

    def encodeJSON(self, input):
        encodedString = json.dumps(input)
        encodedString = encodedString.replace('\"', '\'')
        return encodedString

    def decodeJSON(self, input):
        if input:
            input = input.replace('\'','\"')
            return self.byteify(json.loads(input))
        return None

    def byteify(self, input):
        if isinstance(input, dict):
            return {self.byteify(key):self.byteify(value) for key,value in input.iteritems()}
        elif isinstance(input, list):
            return [self.byteify(element) for element in input]
        elif isinstance(input, unicode):
            return input.encode('utf-8')
        else:
            return input

    def UpdateLandmarkComboboxA(self, fidListCombobox, landmarkCombobox):
        self.comboboxdict[landmarkCombobox] = fidListCombobox.currentNode()
        self.updateLandmarkComboBox(fidListCombobox.currentNode(), landmarkCombobox)
        self.interface.UpdateInterface()

class Q3DCTest(ScriptedLoadableModuleTest):

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
            """
        slicer.mrmlScene.Clear(0)


    def runTest(self):
        """Run as few or as many tests as needed here.
            """
        self.setUp()
        self.delayDisplay(' Starting tests ', 200)
        self.delayDisplay(' Test 3Dcomponents ')
        self.assertTrue(self.test_CalculateDisplacement1())
        self.delayDisplay(' Test Angles Components')
        self.assertTrue(self.test_CalculateDisplacement2())

        self.test_CalculateDisplacement1()
        self.test_CalculateDisplacement2()

        self.test_SimulateTutorial()
        self.delayDisplay(' Tests Passed! ')

    def test_CalculateDisplacement1(self):
        logic = Q3DCLogic(slicer.modules.Q3DCWidget)
        markupsNode1 = slicer.vtkMRMLMarkupsFiducialNode()
        markupsNode1.AddFiducial(-5.331, 51.955, 4.831)
        markupsNode1.AddFiducial(-8.018, 41.429, -52.621)
        diffXAxis, diffYAxis, diffZAxis, threeDDistance = logic.defineDistances(markupsNode1, 0, markupsNode1, 1)
        if diffXAxis != -2.687 or diffYAxis != -10.526 or diffZAxis != -57.452 or threeDDistance != 58.47:
            return False
        return True

    def test_CalculateDisplacement2(self):
        logic = Q3DCLogic(slicer.modules.Q3DCWidget)
        markupsNode1 = slicer.vtkMRMLMarkupsFiducialNode()

        markupsNode1.AddFiducial(63.90,-46.98, 6.98)
        markupsNode1.AddFiducial(43.79,-60.16,12.16)
        markupsNode1.AddFiducial(62.21,-45.31,7.41)
        markupsNode1.AddFiducial(41.97,-61.24,11.30)

        yaw = logic.computeYaw(markupsNode1, 0, markupsNode1, 1, markupsNode1, 2, markupsNode1, 3)
        roll = logic.computeRoll(markupsNode1, 0, markupsNode1, 1, markupsNode1, 2, markupsNode1, 3)
        if yaw != 4.964 or roll != 3.565:
            return False

        markupsNode1.AddFiducial(53.80,-53.57,9.47)
        markupsNode1.AddFiducial(53.98,-52.13,9.13)
        markupsNode1.AddFiducial(52.09,-53.27,9.36)
        markupsNode1.AddFiducial(51.77,-50.10,9.80)
        pitch = logic.computePitch(markupsNode1, 4, markupsNode1, 5, markupsNode1, 6, markupsNode1, 7)
        if pitch != 21.187:
            return False

        return True

    def test_SimulateTutorial(self):

        #
        # first, get the data - a zip file of example data
        #
        import urllib
        downloads = (
            ('http://slicer.kitware.com/midas3/download/item/211921/Q3DCExtensionTestData.zip', 'Q3DCExtensionTestData.zip'),
            )

        self.delayDisplay("Downloading")
        for url,name in downloads:
          filePath = slicer.app.temporaryPath + '/' + name
          if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
            self.delayDisplay('Requesting download %s from %s...\n' % (name, url))
            urllib.urlretrieve(url, filePath)
        self.delayDisplay('Finished with download\n')

        self.delayDisplay("Unzipping")
        q3dcFilesDirectory = slicer.app.temporaryPath + '/q3dcFiles'
        qt.QDir().mkpath(q3dcFilesDirectory)
        slicer.app.applicationLogic().Unzip(filePath, q3dcFilesDirectory)

        modelNodes = {}
        mandibleFiles = ("AH1m.vtk", "AH2m.vtk")
        fiducialFiles = ("AH1f.vtk", "AH2f.vtk")
        for mandibleFile in mandibleFiles:
            name = os.path.splitext(mandibleFile)[0]
            self.delayDisplay("loading: %s" % name)
            filePath = q3dcFilesDirectory + "/" + mandibleFile
            success, modelNodes[name] = slicer.util.loadModel(filePath, returnNode=True)
            if not success:
                self.delayDisplay("load failed for %s" % filePath)
                return False

        modelNodes['AH2m'].GetDisplayNode().SetVisibility(0)
        modelNodes['AH1m'].GetDisplayNode().SetColor((1,0,0))

        self.delayDisplay("Enter markup mode")
        q3dcWidget = slicer.modules.Q3DCWidget

        points = ( (43, 25, -10), (-49, 22, -8), (-6, 64, -53) )

        firstMarkupsNode = None
        firstMarkupID = None

        movingMarkupsFiducial = slicer.vtkMRMLMarkupsFiducialNode()
        movingMarkupsFiducial.SetName("F")
        slicer.mrmlScene.AddNode(movingMarkupsFiducial)
        q3dcWidget.inputModelSelector.setCurrentNode(modelNodes['AH2m'])
        q3dcWidget.inputLandmarksSelector.setCurrentNode(movingMarkupsFiducial)

        index = 0
        for point in points:
            q3dcWidget.onAddLandmarkButtonClicked()
            markupsNodeID = slicer.modules.markups.logic().GetActiveListID()
            if not markupsNodeID:
                self.delayDisplay("No markupsNodeID")
                return False
            markupsNode = slicer.util.getNode(markupsNodeID)
            if not markupsNode:
                self.delayDisplay("No markupsNode")
                return False
            markupsNode.AddFiducial(*point)
            if not firstMarkupsNode:
                firstMarkupsNode = markupsNode
                firstMarkupID = markupsNode.GetNthMarkupID(0)
            self.delayDisplay("Added point %d" % index)
            index += 1

        # reset the interaction node - since we are bypassing the clicks we don't need it
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)

        self.delayDisplay("Define a middle point")
        q3dcWidget.midPointGroupBox.collapsed = False
        q3dcWidget.landmarkComboBox2.currentIndex = 1
        q3dcWidget.defineMiddlePointButton.clicked()
        midpointMarkupID = q3dcWidget.logic.findIDFromLabel(movingMarkupsFiducial,"F-4")
        if not midpointMarkupID:
            print ("Did not define a midpoint node")
            return False

        self.delayDisplay("Calculate a distance")
        q3dcWidget.distanceGroupBox.collapsed = False
        q3dcWidget.fidListComboBoxA.setCurrentNode(movingMarkupsFiducial)
        q3dcWidget.fidListComboBoxB.setCurrentNode(movingMarkupsFiducial)
        q3dcWidget.landmarkComboBoxA.currentIndex = 0
        q3dcWidget.landmarkComboBoxB.currentIndex = 1
        q3dcWidget.computeDistancesPushButton.clicked()

        self.delayDisplay("Calculate angle")
        q3dcWidget.angleGroupBox.collapsed = False
        q3dcWidget.fidListComboBoxline1LA.setCurrentNode(movingMarkupsFiducial)
        q3dcWidget.fidListComboBoxline1LB.setCurrentNode(movingMarkupsFiducial)
        q3dcWidget.fidListComboBoxline2LA.setCurrentNode(movingMarkupsFiducial)
        q3dcWidget.fidListComboBoxline2LB.setCurrentNode(movingMarkupsFiducial)
        q3dcWidget.line1LAComboBox.currentIndex = 0
        q3dcWidget.line1LBComboBox.currentIndex = 1
        q3dcWidget.line2LAComboBox.currentIndex = 2
        q3dcWidget.line2LBComboBox.currentIndex = 3

        q3dcWidget.pitchCheckBox.checked = True
        q3dcWidget.rollCheckBox.checked = True
        q3dcWidget.yawCheckBox.checked = True

        q3dcWidget.computeAnglesPushButton.clicked()

        self.delayDisplay("Calculate a distance between a line and a point")
        q3dcWidget.angleGroupBox.collapsed = False
        q3dcWidget.fidListComboBoxlineLA.setCurrentNode(movingMarkupsFiducial)
        q3dcWidget.fidListComboBoxlineLB.setCurrentNode(movingMarkupsFiducial)
        q3dcWidget.fidListComboBoxlinePoint.setCurrentNode(movingMarkupsFiducial)
        q3dcWidget.lineLAComboBox.currentIndex = 0
        q3dcWidget.lineLBComboBox.currentIndex = 1
        q3dcWidget.linePointComboBox.currentIndex = 2

        q3dcWidget.landmarkComboBox.setCurrentIndex(0)
        self.delayDisplay("Move endpoint, should update midpoint")
        midpointMarkupIndex = movingMarkupsFiducial.GetMarkupIndexByID(midpointMarkupID)
        initialPosition = [0,]*3
        movingMarkupsFiducial.GetNthFiducialPosition(midpointMarkupIndex, initialPosition)
        movingMarkupsFiducial.SetNthFiducialPosition(0, 45, 20, -15)
        movedPosition = [0,]*3
        movingMarkupsFiducial.GetNthFiducialPosition(midpointMarkupIndex, movedPosition)
        if initialPosition == movedPosition:
            print('midpoint landmark did not move')
            return False

        return True