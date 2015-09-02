import vtk, qt, ctk, slicer, math
import numpy, csv, os
import logging
from slicer.ScriptedLoadableModule import *

#
# CalculateDisplacement
#

class Q3DC(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Q3DC "
        parent.categories = ["Shape Analysis"]
        parent.dependencies = []
        parent.contributors = ["Lucie Macron (University of Michigan)"]
        parent.helpText = """
            """
        parent.acknowledgementText = """
            This module was developed by Lucie Macron, University of Michigan
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
        ScriptedLoadableModuleWidget.setup(self)

        # GLOBALS:
        self.logic = Q3DCLogic()
        self.markupsDictionary = dict()
        self.markupsDictionary.clear()
        self.numOfMarkupsNode = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLMarkupsNode")

        self.correspondenceLandmarkDict = dict()  #  key: Landmark Index
                                                  #  Value: MarkupsNodeID

        self.computedDistanceList = list()
        self.computedAnglesList = list()

        self.renderer1 = None
        self.actor1 = None

        self.renderer2 = None
        self.actor2 = None

        self.nodeAddedTag = None
        self.sceneCloseTag = None


        # -------------- Input Models ----------------
        self.treeViewGroupBox = ctk.ctkCollapsibleButton()
        self.treeViewGroupBox.setText('Visibility of Models and Fiducials')
        self.treeViewGroupBox.collapsed = True
        self.parent.layout().addWidget(self.treeViewGroupBox)
        treeView = slicer.qMRMLTreeView()
        treeView.setMRMLScene(slicer.app.mrmlScene())
        treeView.setSceneModelType('Displayable')
        treeView.sceneModel().setHorizontalHeaderLabels(["Models"])
        treeView.sortFilterProxyModel().nodeTypes = ['vtkMRMLModelNode','vtkMRMLMarkupsFiducialNode']
        header = treeView.header()
        header.setResizeMode(0, qt.QHeaderView.Stretch)
        header.setVisible(False)
        self.treeLayout = qt.QVBoxLayout()
        self.treeLayout.addWidget(treeView)
        self.treeViewGroupBox.setLayout(self.treeLayout)

        numNodes = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode")
        for i in range (3,numNodes):
            self.elements = slicer.mrmlScene.GetNthNodeByClass(i,"vtkMRMLModelNode" )
            print('Model node: %s' % self.elements.GetName())


        landmarkFrame = qt.QFrame()
        landmarkFrame.setLayout(qt.QHBoxLayout())
        inputLabel = qt.QLabel('Model of Reference: ')
        self.modelComboBox = slicer.qMRMLNodeComboBox()
        self.modelComboBox.nodeTypes = ['vtkMRMLModelNode']
        self.modelComboBox.addEnabled = False
        self.modelComboBox.removeEnabled = False
        self.modelComboBox.noneEnabled = False
        self.modelComboBox.showHidden = False
        self.modelComboBox.showChildNodeTypes = False
        self.modelComboBox.setMRMLScene(slicer.mrmlScene)
        addLandmarkButton = qt.QPushButton(qt.QIcon(":/Icons/plus.png"), " ")
        addLandmarkButton.connect('clicked()', self.onAddLandmarkButtonClicked)
        landmarkFrame.layout().addWidget(inputLabel)
        landmarkFrame.layout().addWidget(self.modelComboBox)
        landmarkFrame.layout().addWidget(addLandmarkButton)

        self.parent.layout().addWidget(landmarkFrame)

        #        ----------------- Compute Mid Point -------------
        self.midPointGroupBox = ctk.ctkCollapsibleButton()
        self.midPointGroupBox.setText('Define middle point between two landmarks')
        self.midPointGroupBox.collapsed = True
        self.parent.layout().addWidget(self.midPointGroupBox)
        self.landmarkComboBox1 = qt.QComboBox()
        self.landmarkComboBox2 = qt.QComboBox()
        landmark1Layout = qt.QFormLayout()
        landmark1Layout.addRow('Landmark A: ', self.landmarkComboBox1)
        landmark1Layout.addRow('Landmark B: ', self.landmarkComboBox2)

        self.defineMiddlePointButton = qt.QPushButton(' Define middle  point ')
        self.midPointOnSurfaceCheckBox = qt.QCheckBox('On Surface')
        self.midPointOnSurfaceCheckBox.setChecked(False)
        exportLayout_1 = qt.QFormLayout()
        exportLayout_1.addRow(self.midPointOnSurfaceCheckBox, self.defineMiddlePointButton)
        self.midPointLayout = qt.QVBoxLayout()
        self.midPointLayout.addLayout(landmark1Layout)
        self.midPointLayout.addLayout(exportLayout_1)
        self.midPointGroupBox.setLayout(self.midPointLayout)

        self.defineMiddlePointButton.connect('clicked()', self.onDefineMidPointClicked)
        self.landmarkComboBox1.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.landmarkComboBox2.connect('currentIndexChanged(int)', self.UpdateInterface)

#        ------------------- 1st OPTION -------------------
#        GroupBox
        self.distanceGroupBox = ctk.ctkCollapsibleButton()
        self.distanceGroupBox.setText('Calculate distance between two landmarks: ')
        self.distanceGroupBox.collapsed = True
        self.parent.layout().addWidget(self.distanceGroupBox)

        self.landmarkComboBoxA = qt.QComboBox()
        self.landmarkComboBoxB = qt.QComboBox()
        landmark2Layout = qt.QFormLayout()
        landmark2Layout.addRow('Landmark A: ', self.landmarkComboBoxA)
        landmark2Layout.addRow('Landmark B: ', self.landmarkComboBoxB)
        self.computeDistancesPushButton = qt.QPushButton(' Calculate ')
        self.distanceLayout = qt.QVBoxLayout()
        self.distanceLayout.addLayout(landmark2Layout)
        self.distanceLayout.addWidget(self.computeDistancesPushButton)
        self.distanceGroupBox.setLayout(self.distanceLayout)

        self.computeDistancesPushButton.connect('clicked()', self.onComputeDistanceClicked)
        self.landmarkComboBoxA.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.landmarkComboBoxB.connect('currentIndexChanged(int)', self.UpdateInterface)

        self.distanceTable = qt.QTableWidget()
        # ---------------------------- Directory - Export Button -----------------------------
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
#       GroupBox
        self.angleGroupBox = ctk.ctkCollapsibleButton()
        self.angleGroupBox.setText('Calculate angle between two lines: ')
        self.angleGroupBox.collapsed = True
        self.parent.layout().addWidget(self.angleGroupBox)

        self.line1LAComboBox = qt.QComboBox()
        self.line1LBComboBox = qt.QComboBox()
        self.line2LAComboBox = qt.QComboBox()
        self.line2LBComboBox = qt.QComboBox()

        landmark3Layout = qt.QFormLayout()
        landmark3Layout.addRow('Line 1 Landmark A: ', self.line1LAComboBox)
        landmark3Layout.addRow('Line 1 Landmark B:', self.line1LBComboBox)
        landmark3Layout.addRow('Line 2 Landmark A: ', self.line2LAComboBox)
        landmark3Layout.addRow('Line 2 Landmark B:', self.line2LBComboBox)

        layout = qt.QHBoxLayout()
        self.pitchCheckBox = qt.QCheckBox('Calculate Pitch')
        self.rollCheckBox = qt.QCheckBox('Calculate Roll')
        self.yawCheckBox = qt.QCheckBox('Calculate Yaw')
        layout.addWidget(self.pitchCheckBox)
        layout.addWidget(self.rollCheckBox)
        layout.addWidget(self.yawCheckBox)

        self.angleLayout = qt.QVBoxLayout()
        self.angleLayout.addLayout(landmark3Layout)
        self.angleLayout.addLayout(layout)

        self.angleGroupBox.setLayout(self.angleLayout)

        self.computeAnglesPushButton = qt.QPushButton(' Calculate ')
        self.angleLayout.addWidget(self.computeAnglesPushButton)

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

        self.computeAnglesPushButton.connect('clicked()', self.onComputeAnglesClicked)
        self.line1LAComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.line1LBComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.line2LAComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.line2LBComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)

        self.pitchCheckBox.connect('clicked(bool)', self.UpdateInterface)
        self.rollCheckBox.connect('clicked(bool)', self.UpdateInterface)
        self.yawCheckBox.connect('clicked(bool)', self.UpdateInterface)


        # CONNECTIONS:
        self.nodeAddedTag = slicer.app.mrmlScene().AddObserver(slicer.mrmlScene.NodeAddedEvent, self.NodeAdded)

        def onCloseScene(obj, event):
            if self.renderer1 :
                self.renderer1.RemoveActor(self.actor1)
            if self.renderer2 :
                self.renderer2.RemoveActor(self.actor2)
            self.numOfMarkupsNode = 0
            self.UpdateInterface()
        self.sceneCloseTag = slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndCloseEvent, onCloseScene)

        self.UpdateInterface()
        self.layout.addStretch(1)

    def cleanup(self):
        if self.nodeAddedTag:
            slicer.app.mrmlScene().RemoveObserver(self.nodeAddedTag)
            self.nodeAddedTag = None
        if self.sceneCloseTag:
            slicer.app.mrmlScene().RemoveObserver(self.sceneCloseTag)
            self.sceneCloseTag = None

    def UpdateInterface(self):
        self.defineMiddlePointButton.enabled = self.landmarkComboBox1.currentText != '' and self.landmarkComboBox2.currentText != '' and self.landmarkComboBox1.currentText != self.landmarkComboBox2.currentText
        self.computeDistancesPushButton.enabled = self.landmarkComboBoxA.currentText != '' and self.landmarkComboBoxB.currentText != '' and self.landmarkComboBoxA.currentText != self.landmarkComboBoxB.currentText
        self.computeAnglesPushButton.enabled = self.line1LAComboBox.currentText != '' and self.line1LBComboBox.currentText != '' and self.line2LAComboBox.currentText != '' and self.line2LBComboBox.currentText != '' and self.line1LAComboBox.currentText != self.line1LBComboBox.currentText and self.line2LAComboBox.currentText != self.line2LBComboBox.currentText and (self.pitchCheckBox.isChecked() or self.rollCheckBox.isChecked() or self.yawCheckBox.isChecked() )

        #Clear Lines:
        if self.renderer1 :
            self.renderer1.RemoveActor(self.actor1)
            self.renderer1 = None
        if self.renderer2 :
            self.renderer2.RemoveActor(self.actor2)
            self.renderer2 = None
        if self.line1LAComboBox.currentText != '' and self.line1LBComboBox.currentText != '' and self.line1LAComboBox.currentText != self.line1LBComboBox.currentText :
            self.renderer1, self.actor1 = self.logic.drawLineBetween2Landmark(self.correspondenceLandmarkDict[self.line1LAComboBox.currentText], self.correspondenceLandmarkDict[self.line1LBComboBox.currentText], self.markupsDictionary)

        if self.line2LAComboBox.currentText != '' and self.line2LBComboBox.currentText != '' and self.line2LAComboBox.currentText != self.line2LBComboBox.currentText :
            self.renderer2, self.actor2 = self.logic.drawLineBetween2Landmark(self.correspondenceLandmarkDict[self.line2LAComboBox.currentText], self.correspondenceLandmarkDict[self.line2LBComboBox.currentText], self.markupsDictionary)


    def onAddLandmarkButtonClicked(self):
        if not self.modelComboBox.currentNode():
            slicer.util.errorDisplay("Must have a model of reference selected")
            return
        newFidNode = slicer.vtkMRMLMarkupsFiducialNode()
        slicer.mrmlScene.AddNode(newFidNode)
        print (newFidNode.GetID())
        slicer.modules.markups.logic().SetActiveListID(newFidNode)
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place)

    def onComputeDistanceClicked(self):
        if self.computedDistanceList:
            self.exportDistanceButton.disconnect('clicked()', self.onExportButton)
            self.layout.removeWidget(self.distanceTable)
            self.layout.removeItem(self.tableAndExportLayout)
        self.computedDistanceList = self.logic.addOnDistanceList(self.computedDistanceList,
                                                                 self.correspondenceLandmarkDict[self.landmarkComboBoxA.currentText],
                                                                 self.correspondenceLandmarkDict[self.landmarkComboBoxB.currentText],
                                                                 self.markupsDictionary)

        self.distanceTable = self.logic.defineDistanceTable(self.distanceTable, self.computedDistanceList, self.correspondenceLandmarkDict)
        self.distanceLayout.addLayout(self.tableAndExportLayout)
        self.exportDistanceButton.connect('clicked()', self.onExportButton)

    def onExportButton(self):
        self.logic.exportationFunction(self.directoryExportDistance, self.computedDistanceList, 'distance', self.correspondenceLandmarkDict)


    def onComputeAnglesClicked(self):
        if self.computedAnglesList:
            self.exportAngleButton.disconnect('clicked()', self.onExportAngleButton)
            self.layout.removeWidget(self.anglesTable)
            self.layout.removeItem(self.tableAndExportAngleLayout)
        self.computedAnglesList = self.logic.addOnAngleList(self.computedAnglesList,
                                                            self.correspondenceLandmarkDict[self.line1LAComboBox.currentText],
                                                            self.correspondenceLandmarkDict[self.line1LBComboBox.currentText],
                                                            self.correspondenceLandmarkDict[self.line2LAComboBox.currentText],
                                                            self.correspondenceLandmarkDict[self.line2LBComboBox.currentText],
                                                            self.markupsDictionary,
                                                            self.pitchCheckBox.isChecked(),
                                                            self.yawCheckBox.isChecked(),
                                                            self.rollCheckBox.isChecked()
                                                            )
        self.anglesTable = self.logic.defineAnglesTable(self.anglesTable, self.computedAnglesList, self.correspondenceLandmarkDict)
        self.angleLayout.addLayout(self.tableAndExportAngleLayout)
        self.exportAngleButton.connect('clicked()', self.onExportAngleButton)


    def onExportAngleButton(self):
        print("onExportAngleButton")
        self.logic.exportationFunction(self.directoryExportAngle, self.computedAnglesList, 'angle', self.correspondenceLandmarkDict)

    def onDefineMidPointClicked(self):
        newMarkupsNode = slicer.vtkMRMLMarkupsFiducialNode()
        slicer.mrmlScene.AddNode(newMarkupsNode)

        id1 = self.landmarkComboBox1.currentText
        id2 = self.landmarkComboBox2.currentText
        landmark1ID = self.correspondenceLandmarkDict[id1]
        landmark2ID = self.correspondenceLandmarkDict[id2]

        markupsNode1 = slicer.mrmlScene.GetNodeByID(self.logic.findMarkupsNodeFromLandmarkID(self.markupsDictionary, landmark1ID))
        markupsNode2 = slicer.mrmlScene.GetNodeByID(self.logic.findMarkupsNodeFromLandmarkID(self.markupsDictionary, landmark2ID))

        self.logic.calculateMidPointByMarkupsNode(newMarkupsNode, markupsNode1, landmark1ID, markupsNode2, landmark2ID)

        newMarkupsNode.SetNthMarkupLocked(0, True)
        newMarkupsNode.SetNthMarkupSelected(0, False)


        # Track the endpoints and mid point so that any changes to either
        # of the endpoints can trigger an update of the midpoint
        # TODO: this can be made more robust with a more sophisticated cephalometric landmark model
        markupsNode1.SetAttribute("Q3DC.MidpointNodeID", newMarkupsNode.GetID())
        markupsNode1.SetAttribute("Q3DC.MidpointOppositeNodeID", markupsNode2.GetID())
        markupsNode1.SetAttribute("Q3DC.MidpointLandmarkID", landmark1ID)
        markupsNode2.SetAttribute("Q3DC.MidpointNodeID", newMarkupsNode.GetID())
        markupsNode2.SetAttribute("Q3DC.MidpointOppositeNodeID", markupsNode1.GetID())
        markupsNode2.SetAttribute("Q3DC.MidpointLandmarkID", landmark2ID)
        newMarkupsNode.SetAttribute("Q3DC.MidpointLandmark1ID", markupsNode1.GetID())
        newMarkupsNode.SetAttribute("Q3DC.MidpointLandmark2ID", markupsNode2.GetID())

        if self.midPointOnSurfaceCheckBox.isChecked():
            projectionSurfaceID = self.markupsDictionary[newMarkupsNode.GetID()].landmarkDictionary.values()[0]
            self.logic.projectLandmarkOnSurface(projectionSurfaceID, newMarkupsNode.GetID())
        # track the model that the midpoint should project on (and if the projection is needed)
        midpointProjectOnSurface = "False"
        if self.midPointOnSurfaceCheckBox.isChecked():
            midpointProjectOnSurface = "True"
        newMarkupsNode.SetAttribute("Q3DC.ProjectOnSurface", midpointProjectOnSurface)
        newMarkupsNode.SetAttribute("Q3DC.ProjectionSurface", projectionSurfaceID)


    def NodeAdded(self, obj, node):
        print("NodeAdded")
        newNumOfMarkupsNode = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLMarkupsFiducialNode")
        print("newNumOfMarkupsNode , self.numOfMarkupsNode")
        print(newNumOfMarkupsNode , self.numOfMarkupsNode)
        if newNumOfMarkupsNode > self.numOfMarkupsNode:
            for i in range(self.numOfMarkupsNode, newNumOfMarkupsNode):
                node = slicer.mrmlScene.GetNthNodeByClass(i, "vtkMRMLMarkupsFiducialNode")
                if not self.markupsDictionary.has_key(node.GetID()):
                    self.markupsDictionary[node.GetID()] = self.MarkupsNodeStorage()
                    self.markupsDictionary[node.GetID()].MarkupAddedEventTag = node.AddObserver(node.MarkupAddedEvent, self.onMarkupAddedEvent)
                    self.markupsDictionary[node.GetID()].PointModifiedEventTag = node.AddObserver(node.PointModifiedEvent, self.onPointModifiedEvent)
                    self.markupsDictionary[node.GetID()].landmarkDictionary = dict()
                    self.markupsDictionary[node.GetID()].landmarkDictionary.clear()
            self.numOfMarkupsNode = newNumOfMarkupsNode


    def onMarkupAddedEvent(self, obj, event):
        print( " --------------------------------------- onMarkupAddedEvent ")
        landmarkID = obj.GetNthMarkupID(obj.GetNumberOfMarkups()-1)  # Landmark added - always the last one on the list
        landmarkIndex = obj.GetMarkupIndexByID(landmarkID)
        obj.SetNthMarkupLabel(landmarkIndex, str(self.markupsDictionary.__len__()))
        self.markupsDictionary[obj.GetID()].landmarkDictionary[landmarkID] = self.modelComboBox.currentNode().GetID()
        self.landmarkComboBox1.addItem(obj.GetNthFiducialLabel(landmarkIndex))
        self.landmarkComboBox2.addItem(obj.GetNthFiducialLabel(landmarkIndex))

        self.landmarkComboBoxA.addItem(obj.GetNthFiducialLabel(landmarkIndex))
        self.landmarkComboBoxB.addItem(obj.GetNthFiducialLabel(landmarkIndex))

        self.line1LAComboBox.addItem(obj.GetNthFiducialLabel(landmarkIndex))
        self.line1LBComboBox.addItem(obj.GetNthFiducialLabel(landmarkIndex))
        self.line2LAComboBox.addItem(obj.GetNthFiducialLabel(landmarkIndex))
        self.line2LBComboBox.addItem(obj.GetNthFiducialLabel(landmarkIndex))

        self.correspondenceLandmarkDict[obj.GetNthFiducialLabel(landmarkIndex)] = landmarkID

    def updateMidpoint(self, landmarkMarkupNode):
        """Check the attributes of the landmark and if needed update the associated midpoint node.
           See onDefineMidPointClicked for the code that sets these attributes.
        """
        midpointNodeID = landmarkMarkupNode.GetAttribute("Q3DC.MidpointNodeID")
        oppositeNodeID = landmarkMarkupNode.GetAttribute("Q3DC.MidpointOppositeNodeID")
        if not midpointNodeID or not oppositeNodeID:
            # this is not part of a midpoint set, so ignore it
            return
        midpointNode = slicer.mrmlScene.GetNodeByID(midpointNodeID)
        oppositeNode = slicer.mrmlScene.GetNodeByID(oppositeNodeID)
        if not midpointNode or not oppositeNode:
            print("Landmark marked as part of midpoint set, but the nodes are not in the scene")
            return
        landmarkNodeLandmarkID = landmarkMarkupNode.GetAttribute("Q3DC.MidpointLandmarkID")
        oppositeNodeLandmarkID = oppositeNode.GetAttribute("Q3DC.MidpointLandmarkID")
        if not landmarkNodeLandmarkID or not oppositeNodeLandmarkID:
            print("Landmarks do not have markup ids")
            return

        print("self.logic.calculateMidPointByMarkupsNode(", midpointNode, landmarkMarkupNode, landmarkNodeLandmarkID, oppositeNode, oppositeNodeLandmarkID, ")")
        # perform the calculation
        self.logic.calculateMidPointByMarkupsNode(midpointNode, landmarkMarkupNode, landmarkNodeLandmarkID, oppositeNode, oppositeNodeLandmarkID)

        if midpointNode.GetAttribute("Q3DC.ProjectOnSurface") == "True":
            projectionSurfaceID = midpointNode.GetAttribute("Q3DC.ProjectionSurface")
            if not projectionSurfaceID:
                print("Landmark marked to project on surface, but no ID")
                return
            projectionSurface = slicer.mrmlScene.GetNodeByID(projectionSurfaceID)
            if not projectionSurface:
                print("Landmark marked to project on surface, but model is missing")
                return
            self.logic.projectLandmarkOnSurface(projectionSurfaceID, landmarkMarkupNode.GetID())



    def onPointModifiedEvent(self, obj, event):
        print( " --------- onPointModifiedEvent ")
        self.updateMidpoint(obj)
        obj.RemoveObserver(self.markupsDictionary[obj.GetID()].PointModifiedEventTag)
        self.logic.projectLandmarkOnSurface(self.markupsDictionary[obj.GetID()].landmarkDictionary.values()[0], obj.GetID())
        self.markupsDictionary[obj.GetID()].PointModifiedEventTag = obj.AddObserver(obj.PointModifiedEvent, self.onPointModifiedEvent)
        if self.line1LAComboBox.currentText != '' and self.line1LBComboBox.currentText != '' and self.line1LAComboBox.currentText != self.line1LBComboBox.currentText :
            #Clear Lines, then define new ones
            if self.renderer1 :
                self.renderer1.RemoveActor(self.actor1)
            self.renderer1, self.actor1 = self.logic.drawLineBetween2Landmark(self.correspondenceLandmarkDict[self.line1LAComboBox.currentText], self.correspondenceLandmarkDict[self.line1LBComboBox.currentText], self.markupsDictionary)
        if self.line2LAComboBox.currentText != '' and self.line2LBComboBox.currentText != '' and self.line2LAComboBox.currentText != self.line2LBComboBox.currentText :
            if self.renderer2 :
                self.renderer2.RemoveActor(self.actor2)
            self.renderer2, self.actor2 = self.logic.drawLineBetween2Landmark(self.correspondenceLandmarkDict[self.line2LAComboBox.currentText], self.correspondenceLandmarkDict[self.line2LBComboBox.currentText], self.markupsDictionary)


class Q3DCLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        self.numberOfDecimals = 3
        system = qt.QLocale().system()
        self.decimalPoint = chr(system.decimalPoint())
        pass

    class distanceValuesStorage(object):
        def __init__(self):
            self.startLandmarkID = None
            self.endLandmarkID = None
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
            self.Pitch = None
            self.Roll = None
            self.Yaw = None

    def projectLandmarkOnSurface(self, inputModelID, markupsNodeID):
        markupsNode = slicer.mrmlScene.GetNodeByID(markupsNodeID)
        projectOnSurface = markupsNode.GetAttribute("Q3DC.ProjectOnSurface")
        if projectOnSurface == "False":
            # defined for midpoint landmarks that aren't requested to stay on surface
            return
        polyData = slicer.mrmlScene.GetNodeByID(inputModelID).GetPolyData()
        pointLocator = vtk.vtkPointLocator()
        pointLocator.SetDataSet(polyData)
        pointLocator.AutomaticOn()
        pointLocator.BuildLocator()
        for i in range(0, markupsNode.GetNumberOfMarkups()):
            landmarkID = markupsNode.GetNthMarkupID(i)
            landmarkIndex = markupsNode.GetMarkupIndexByID(landmarkID)
            print( " ------------------------  getClosestPointIndex ------------------------  ")
            landmarkCoord = [-1, -1, -1]
            markupsNode.GetNthFiducialPosition(landmarkIndex, landmarkCoord)
            indexClosestPoint = pointLocator.FindClosestPoint(landmarkCoord)
            print( "         closest Point:", indexClosestPoint, " Coord", landmarkCoord)
            print( " ------------------------ replaceLandmark ------------------------ ")
            polyData.GetPoints().GetPoint(indexClosestPoint, landmarkCoord)
            markupsNode.SetNthFiducialPosition(landmarkIndex,
                                               landmarkCoord[0],
                                               landmarkCoord[1],
                                               landmarkCoord[2])

    def calculateMidPointByMarkupsNode(self, newMarkupsNode, markupsNode1, landmark1ID, markupsNode2, landmark2ID):
        """Set the midpoint when you know the the mrml nodes"""
        landmark1Index = markupsNode1.GetMarkupIndexByID(landmark1ID)
        landmark2Index = markupsNode2.GetMarkupIndexByID(landmark2ID)

        coord1 = [-1, -1, -1]
        coord2 = [-1, -1, -1]
        markupsNode1.GetNthFiducialPosition(landmark1Index, coord1)
        markupsNode2.GetNthFiducialPosition(landmark2Index, coord2)

        midCoord = [-1, -1, -1]
        midCoord[0] = (coord1[0] + coord2[0])/2
        midCoord[1] = (coord1[1] + coord2[1])/2
        midCoord[2] = (coord1[2] + coord2[2])/2

        if newMarkupsNode.GetNumberOfFiducials() < 1:
            newMarkupsNode.AddFiducial(midCoord[0], midCoord[1], midCoord[2])
        else:
            newMarkupsNode.SetNthFiducialPosition(0, midCoord[0], midCoord[1], midCoord[2])


    def findMarkupsNodeFromLandmarkID(self, markupsDictionary, landmarkIDToFind):
        print("landmarkIDToFind: %s" % landmarkIDToFind)
        for key, value in markupsDictionary.iteritems():
            landmarkDict = value.landmarkDictionary
            for landmarkID in landmarkDict.iterkeys():
                if landmarkID == landmarkIDToFind:
                    return key


    def defineDistances(self, markupsNode1, landmark1Index, markupsNode2, landmark2Index):
        coord1 = [-1, -1, -1]
        coord2 = [-1, -1, -1]
        markupsNode1.GetNthFiducialPosition(landmark1Index, coord1)
        markupsNode2.GetNthFiducialPosition(landmark2Index, coord2)
        print( "point A: %s"% coord1)
        print( "point B: %s"% coord2)
        diffRAxis = coord2[0] - coord1[0]
        diffAAxis = coord2[1] - coord1[1]
        diffSAxis = coord2[2] - coord1[2]
        threeDDistance = math.sqrt(vtk.vtkMath().Distance2BetweenPoints(coord1, coord2))
        return round(diffRAxis, self.numberOfDecimals), round(diffAAxis, self.numberOfDecimals), round(diffSAxis, self.numberOfDecimals), round(threeDDistance, self.numberOfDecimals)


    def defineDistanceTable(self, table, distanceList, correspondentDict):
        table.clear()
        table.setRowCount(distanceList.__len__())
        table.setColumnCount(5)
        table.setMinimumHeight(50*distanceList.__len__())
        table.setHorizontalHeaderLabels(['  ', ' R-L Component', ' A-P Component', ' S-I Component', ' 3D Distance '])
        i = 0
        for element in distanceList:
            startLandName = correspondentDict.keys()[correspondentDict.values().index(element.startLandmarkID)]
            endLandName = correspondentDict.keys()[correspondentDict.values().index(element.endLandmarkID)]
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

    def addOnDistanceList(self, distanceList, startID, endID, markupsDictionary):
        markupsNode1 = slicer.mrmlScene.GetNodeByID(self.findMarkupsNodeFromLandmarkID(markupsDictionary, startID))
        markupsNode2 = slicer.mrmlScene.GetNodeByID(self.findMarkupsNodeFromLandmarkID(markupsDictionary, endID))
        landmark1Index = markupsNode1.GetMarkupIndexByID(startID)
        landmark2Index = markupsNode2.GetMarkupIndexByID(endID)
        print ("distance", landmark1Index, landmark2Index)
        elementToAdd = self.distanceValuesStorage()
        # if this distance has already been computed before -> replace values
        for element in distanceList:
            if element.startLandmarkID == startID and element.endLandmarkID == endID:
                element = self.removecomponentFromStorage('distance', element)
                element.RLComponent, element.APComponent, element.SIComponent, element.ThreeDComponent = self.defineDistances(markupsNode1,
                                                                                                                              landmark1Index,
                                                                                                                              markupsNode2,
                                                                                                                              landmark2Index)
                return distanceList

        elementToAdd.startLandmarkID = startID
        elementToAdd.endLandmarkID = endID
        elementToAdd.RLComponent, elementToAdd.APComponent, elementToAdd.SIComponent, elementToAdd.ThreeDComponent = self.defineDistances(markupsNode1,
                                                                                                                                          landmark1Index,
                                                                                                                                          markupsNode2,
                                                                                                                                          landmark2Index)
        distanceList.append(elementToAdd)
        return distanceList

    def computePitch(self, markupsNode1, landmark1Index, markupsNode2, landmark2Index, markupsNode3, landmark3Index, markupsNode4, landmark4Index):
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
        print ("vecline1", vectLine1, normVectLine1)
        vectLine2 = [0, coord4[1]-coord3[1], coord4[2]-coord3[2] ]
        normVectLine2 = numpy.sqrt( vectLine2[1]*vectLine2[1] + vectLine2[2]*vectLine2[2] )
        print ("vecline2", vectLine2, normVectLine2)
        pitchNotSigned = round(vtk.vtkMath().DegreesFromRadians(vtk.vtkMath().AngleBetweenVectors(vectLine1, vectLine2)), self.numberOfDecimals)
        print"PITCHCOMPUTED",  pitchNotSigned

        if normVectLine1 != 0 and normVectLine2 != 0:
            normalizedVectLine1 = [0, (1/normVectLine1)*vectLine1[1], (1/normVectLine1)*vectLine1[2]]
            print ("normalizedVectLine1" , normalizedVectLine1)
            normalizedVectLine2 = [0, (1/normVectLine2)*vectLine2[1], (1/normVectLine2)*vectLine2[2]]
            print ("normalizedVectLine2" , normalizedVectLine2)
            det2D = normalizedVectLine1[1]*normalizedVectLine2[2] - normalizedVectLine1[2]*normalizedVectLine2[1]
            print (det2D)
            print (math.copysign(pitchNotSigned, det2D))
            return math.copysign(pitchNotSigned, det2D)
        else:
            slicer.util.errorDisplay("ERROR, norm of your vector is 0! DEFINE A VECTOR!")
            return None

    def computeRoll(self, markupsNode1, landmark1Index, markupsNode2, landmark2Index, markupsNode3, landmark3Index, markupsNode4, landmark4Index):
        # Roll is computed by projection on the plan (x,z)
        coord1 = [-1, -1, -1]
        coord2 = [-1, -1, -1]
        coord3 = [-1, -1, -1]
        coord4 = [-1, -1, -1]

        markupsNode1.GetNthFiducialPosition(landmark1Index, coord1)
        print (coord1)
        markupsNode2.GetNthFiducialPosition(landmark2Index, coord2)
        print (coord2)
        markupsNode3.GetNthFiducialPosition(landmark3Index, coord3)
        print (coord3)
        markupsNode4.GetNthFiducialPosition(landmark4Index, coord4)
        print (coord4)

        vectLine1 = [coord2[0]-coord1[0], 0, coord2[2]-coord1[2] ]
        normVectLine1 = numpy.sqrt( vectLine1[0]*vectLine1[0] + vectLine1[2]*vectLine1[2] )
        print ("vecline1", vectLine1, normVectLine1)
        vectLine2 = [coord4[0]-coord3[0], 0, coord4[2]-coord3[2] ]
        normVectLine2 = numpy.sqrt( vectLine2[0]*vectLine2[0] + vectLine2[2]*vectLine2[2] )
        print ("vecline2", vectLine2, normVectLine2)
        rollNotSigned = round(vtk.vtkMath().DegreesFromRadians(vtk.vtkMath().AngleBetweenVectors(vectLine1, vectLine2)), self.numberOfDecimals)
        print"ROLLCOMPUTED",  rollNotSigned

        if normVectLine1 != 0 and normVectLine2 != 0:
            normalizedVectLine1 = [(1/normVectLine1)*vectLine1[0], 0, (1/normVectLine1)*vectLine1[2]]
            print ("normalizedVectLine1" , normalizedVectLine1)
            normalizedVectLine2 = [(1/normVectLine2)*vectLine2[0], 0, (1/normVectLine2)*vectLine2[2]]
            print ("normalizedVectLine2" , normalizedVectLine2)
            det2D = normalizedVectLine1[0]*normalizedVectLine2[2] - normalizedVectLine1[2]*normalizedVectLine2[0]
            print (det2D)
            print (math.copysign(rollNotSigned, det2D))
            return math.copysign(rollNotSigned, det2D)
        else:
            print (" ERROR, norm of your vector is 0! DEFINE A VECTOR!")
            return None

    def computeYaw(self, markupsNode1, landmark1Index, markupsNode2, landmark2Index, markupsNode3, landmark3Index, markupsNode4, landmark4Index):
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
        print ("vecline1", vectLine1, normVectLine1)
        vectLine2 = [coord4[0]-coord3[0],coord4[1]-coord3[1], 0]
        normVectLine2 = numpy.sqrt( vectLine2[0]*vectLine2[0] + vectLine2[1]*vectLine2[1] )
        print ("vecline2", vectLine2, normVectLine2)
        yawNotSigned = round(vtk.vtkMath().DegreesFromRadians(vtk.vtkMath().AngleBetweenVectors(vectLine1, vectLine2)), self.numberOfDecimals)
        print"YAWCOMPUTED",  yawNotSigned

        if normVectLine1 != 0 and normVectLine2 != 0:
            normalizedVectLine1 = [(1/normVectLine1)*vectLine1[0], (1/normVectLine1)*vectLine1[1], 0]
            print ("normalizedVectLine1" , normalizedVectLine1)
            normalizedVectLine2 = [(1/normVectLine2)*vectLine2[0], (1/normVectLine2)*vectLine2[1], 0]
            print ("normalizedVectLine2" , normalizedVectLine2)
            det2D = normalizedVectLine1[0]*normalizedVectLine2[1] - normalizedVectLine1[1]*normalizedVectLine2[0]
            print (det2D)
            print (math.copysign(yawNotSigned, det2D))
            return math.copysign(yawNotSigned, det2D)
        else:
            slicer.util.errorDisplay("ERROR, norm of your vector is 0! DEFINE A VECTOR!")
            return None

    def addOnAngleList(self, angleList, landmarkALine1ID, landmarkBLine1ID, landmarkALine2ID, landmarkBLine2ID, markupsDictionary, PitchState, YawState, RollState):
        print ("AddOnAngleList")
        markupsNode1 = slicer.mrmlScene.GetNodeByID(self.findMarkupsNodeFromLandmarkID(markupsDictionary, landmarkALine1ID))
        markupsNode2 = slicer.mrmlScene.GetNodeByID(self.findMarkupsNodeFromLandmarkID(markupsDictionary, landmarkBLine1ID))
        markupsNode3 = slicer.mrmlScene.GetNodeByID(self.findMarkupsNodeFromLandmarkID(markupsDictionary, landmarkALine2ID))
        markupsNode4 = slicer.mrmlScene.GetNodeByID(self.findMarkupsNodeFromLandmarkID(markupsDictionary, landmarkBLine2ID))

        landmark1Index = markupsNode1.GetMarkupIndexByID(landmarkALine1ID)
        landmark2Index = markupsNode2.GetMarkupIndexByID(landmarkBLine1ID)
        landmark3Index = markupsNode3.GetMarkupIndexByID(landmarkALine2ID)
        landmark4Index = markupsNode4.GetMarkupIndexByID(landmarkBLine2ID)

        # if angles has already been computed before -> replace values
        elementToAdd = self.angleValuesStorage()
        for element in angleList:
            if element.landmarkALine1ID == landmarkALine1ID and element.landmarkBLine1ID == landmarkBLine1ID and element.landmarkALine2ID == landmarkALine2ID and element.landmarkBLine2ID == landmarkBLine2ID:
                element = self.removecomponentFromStorage('angles', element)
                if PitchState:
                    element.Pitch = self.computePitch(markupsNode1, landmark1Index, markupsNode2, landmark2Index, markupsNode3, landmark3Index, markupsNode4, landmark4Index)
                if RollState:
                    element.Roll = self.computeRoll(markupsNode1, landmark1Index, markupsNode2, landmark2Index, markupsNode3, landmark3Index, markupsNode4, landmark4Index)
                if YawState:
                    element.Yaw = self.computeYaw(markupsNode1, landmark1Index, markupsNode2, landmark2Index, markupsNode3, landmark3Index, markupsNode4, landmark4Index)
                return angleList
        # create a new element depending on what the user wants
        elementToAdd.landmarkALine1ID = landmarkALine1ID
        elementToAdd.landmarkBLine1ID = landmarkBLine1ID
        elementToAdd.landmarkALine2ID = landmarkALine2ID
        elementToAdd.landmarkBLine2ID = landmarkBLine2ID
        print (PitchState, YawState, RollState)
        if PitchState:
            elementToAdd.Pitch = self.computePitch(markupsNode1, landmark1Index, markupsNode2, landmark2Index, markupsNode3, landmark3Index, markupsNode4, landmark4Index)
            print ("pitch",elementToAdd.Pitch)
        if RollState:
            elementToAdd.Roll = self.computeRoll(markupsNode1, landmark1Index, markupsNode2, landmark2Index, markupsNode3, landmark3Index, markupsNode4, landmark4Index)
            print ("Roll",elementToAdd.Roll)
        if YawState:
            elementToAdd.Yaw = self.computeYaw(markupsNode1, landmark1Index, markupsNode2, landmark2Index, markupsNode3, landmark3Index, markupsNode4, landmark4Index)
            print ("yaw",elementToAdd.Yaw)
        angleList.append(elementToAdd)
        return angleList

    def defineAnglesTable(self, table, angleList, correspondentDict):

        table.clear()
        table.setRowCount(angleList.__len__())
        table.setColumnCount(4)
        table.setMinimumHeight(50*angleList.__len__())
        table.setHorizontalHeaderLabels([' ', ' YAW ', ' PITCH ', ' ROLL '])
        i = 0

        for element in angleList:
            landmarkALine1Name = correspondentDict.keys()[correspondentDict.values().index(element.landmarkALine1ID)]
            landmarkBLine1Name = correspondentDict.keys()[correspondentDict.values().index(element.landmarkBLine1ID)]
            landmarkALine2Name = correspondentDict.keys()[correspondentDict.values().index(element.landmarkALine2ID)]
            landmarkBLine2Name = correspondentDict.keys()[correspondentDict.values().index(element.landmarkBLine2ID)]

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


    def drawLineBetween2Landmark(self, landmark1ID, landmark2ID, markupsDictionary):
        markupsNode1 = slicer.mrmlScene.GetNodeByID(self.findMarkupsNodeFromLandmarkID(markupsDictionary, landmark1ID))
        markupsNode2 = slicer.mrmlScene.GetNodeByID(self.findMarkupsNodeFromLandmarkID(markupsDictionary, landmark2ID))

        if not markupsNode1 or not markupsNode2:
            return
        landmark1Index = markupsNode1.GetMarkupIndexByID(landmark1ID)
        landmark2Index = markupsNode2.GetMarkupIndexByID(landmark2ID)

        coord1 = [-1, -1, -1]
        coord2 = [-1, -1, -1]
        markupsNode1.GetNthFiducialPosition(landmark1Index, coord1)
        markupsNode2.GetNthFiducialPosition(landmark2Index, coord2)

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

    def exportationFunction(self, directoryExport, listToExport, typeCalculation, correspondentDict):
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
            if choice == messageBox.NoToAll:
                return
        self.exportAsCSV(fileName, listToExport, typeCalculation, correspondentDict)
        slicer.util.showMessage("Saved to fileName")


    def exportAsCSV(self,filename, listToExport, typeCalculation, correspondentDict):
        #  Export fields on different csv files
        file = open(filename, 'w')
        cw = csv.writer(file, delimiter=',')
        if typeCalculation == 'distance':
            cw.writerow([' Landmark A - Landmark B',  ' R-L Component', ' A-P Component', ' S-I Component', ' 3D Distance '])
            self.writeDistance(cw, listToExport, correspondentDict)
        else:
            cw.writerow([' Line 1 (Landmark A - Landmark B) /  Line 2 (Landmark A - Landmark B)',  ' YAW ', ' PITCH ', ' ROLL '])
            self.writeAngle(cw, listToExport, correspondentDict)
        file.close()
        if self.decimalPoint != '.':
            self.replaceCharac(filename, ',', ';') # change the Delimiter and put a semicolon instead of a comma
            self.replaceCharac(filename, '.', self.decimalPoint) # change the decimal separator '.' for a comma

    def writeDistance(self, fileWriter, listToExport, correspondentDict):
        for element in listToExport:
            startLandName = correspondentDict.keys()[correspondentDict.values().index(element.startLandmarkID)]
            endLandName = correspondentDict.keys()[correspondentDict.values().index(element.endLandmarkID)]
            label = startLandName + ' - ' + endLandName
            fileWriter.writerow([label,
                                 element.RLComponent,
                                 element.APComponent,
                                 element.SIComponent,
                                 element.ThreeDComponent])

    def writeAngle(self, fileWriter, listToExport, correspondentDict):
        for element in listToExport:
            landmarkALine1Name = correspondentDict.keys()[correspondentDict.values().index(element.landmarkALine1ID)]
            landmarkBLine1Name = correspondentDict.keys()[correspondentDict.values().index(element.landmarkBLine1ID)]
            landmarkALine2Name = correspondentDict.keys()[correspondentDict.values().index(element.landmarkALine2ID)]
            landmarkBLine2Name = correspondentDict.keys()[correspondentDict.values().index(element.landmarkBLine2ID)]

            label = landmarkALine1Name + '-' + landmarkBLine1Name + ' | ' + landmarkALine2Name + '-' + landmarkBLine2Name
            signY = numpy.sign(element.Yaw)
            signP = numpy.sign(element.Pitch)
            signR = numpy.sign(element.Roll)
            print (element.Yaw, element.Pitch, element.Roll)

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


class Q3DCTest(ScriptedLoadableModuleTest):

    def __init__(self):
        ScriptedLoadableModuleTest.__init__(self,messageDelay=50)

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
        self.delayDisplay(' Tests Passed! ')

        self.test_CalculateDisplacement1()
        self.test_CalculateDisplacement2()

        self.test_SimulateTutorial()

    def test_CalculateDisplacement1(self):
        logic = Q3DCLogic()
        markupsNode1 = slicer.vtkMRMLMarkupsFiducialNode()
        markupsNode1.AddFiducial(-5.331, 51.955, 4.831)
        markupsNode1.AddFiducial(-8.018, 41.429, -52.621)
        diffXAxis, diffYAxis, diffZAxis, threeDDistance = logic.defineDistances(markupsNode1, 0, markupsNode1, 1)
        print (diffXAxis, diffYAxis, diffZAxis, threeDDistance)
        if diffXAxis != -2.687 or diffYAxis != -10.526 or diffZAxis != -57.452 or threeDDistance != 58.47:
            return False
        return True

    def test_CalculateDisplacement2(self):
        logic = Q3DCLogic()
        markupsNode1 = slicer.vtkMRMLMarkupsFiducialNode()

        markupsNode1.AddFiducial(63.90,-46.98, 6.98)
        markupsNode1.AddFiducial(43.79,-60.16,12.16)
        markupsNode1.AddFiducial(62.21,-45.31,7.41)
        markupsNode1.AddFiducial(41.97,-61.24,11.30)

        yaw = logic.computeYaw(markupsNode1, 0, markupsNode1, 1, markupsNode1, 2, markupsNode1, 3)
        roll = logic.computeRoll(markupsNode1, 0, markupsNode1, 1, markupsNode1, 2, markupsNode1, 3)
        print ("roll, pitch", yaw, roll)
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
        midpointMarkupID = q3dcWidget.markupsDictionary.keys()[3]
        if not midpointMarkupID:
            print ("Did not define a midpoint node")
            return False

        self.delayDisplay("Calculate a distance")
        q3dcWidget.distanceGroupBox.collapsed = False
        q3dcWidget.landmarkComboBoxB.currentIndex = 1
        q3dcWidget.computeDistancesPushButton.clicked()

        self.delayDisplay("Calculate angle")
        q3dcWidget.angleGroupBox.collapsed = False
        q3dcWidget.line1LAComboBox.currentIndex = 0
        q3dcWidget.line1LBComboBox.currentIndex = 1
        q3dcWidget.line2LAComboBox.currentIndex = 2
        q3dcWidget.line2LBComboBox.currentIndex = 3

        q3dcWidget.pitchCheckBox.checked = True
        q3dcWidget.rollCheckBox.checked = True
        q3dcWidget.yawCheckBox.checked = True

        q3dcWidget.computeAnglesPushButton.clicked()


        self.delayDisplay("Move endpoint, should update midpoint")
        midpointMarkup = slicer.util.getNode(midpointMarkupID)
        initialPosition = [0,]*3
        midpointMarkup.GetNthFiducialPosition(0, initialPosition)
        firstMarkupsNode.SetNthFiducialPosition(0, 45, 20, -15)
        movedPosition = [0,]*3
        midpointMarkup.GetNthFiducialPosition(0, movedPosition)
        if initialPosition == movedPosition:
            print('midpoint landmark did not move')
            return False

        return True
