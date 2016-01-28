import vtk, qt, ctk, slicer
import os
from slicer.ScriptedLoadableModule import *
import Q3DCLogic

#
# CalculateDisplacement
#

class Q3DC(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Q3DC "
        parent.categories = ["Shape Analysis"]
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
        print "------Setup-----"
        ScriptedLoadableModuleWidget.setup(self)
        # GLOBALS:
        reload(Q3DCLogic)
        self.logic = Q3DCLogic.Q3DCLogic(self)
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
        treeView = self.logic.get("treeView")
        treeView.setMRMLScene(slicer.app.mrmlScene())
        treeView.sceneModel().setHorizontalHeaderLabels(["Models"])
        treeView.sortFilterProxyModel().nodeTypes = ['vtkMRMLModelNode','vtkMRMLMarkupsFiducialNode']
        treeView.header().setVisible(False)
        # --------------- landmark modification --------------
        self.landmarkModif = self.logic.get("landmarkModif")
        self.inputModelSelector = self.logic.get("inputModelSelector")
        self.inputModelSelector.setMRMLScene(slicer.mrmlScene)
        self.inputModelSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onModelChanged)
        self.addLandmarkButton = self.logic.get("addLandmarkButton")
        self.addLandmarkButton.connect('clicked()', self.onAddLandmarkButtonClicked)
        self.inputLandmarksSelector = self.logic.get("inputLandmarksSelector")
        self.inputLandmarksSelector.setMRMLScene(slicer.mrmlScene)
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
        logic = Q3DCLogic.Q3DCLogic(slicer.modules.Q3DCWidget)
        markupsNode1 = slicer.vtkMRMLMarkupsFiducialNode()
        markupsNode1.AddFiducial(-5.331, 51.955, 4.831)
        markupsNode1.AddFiducial(-8.018, 41.429, -52.621)
        diffXAxis, diffYAxis, diffZAxis, threeDDistance = logic.defineDistances(markupsNode1, 0, markupsNode1, 1)
        if diffXAxis != -2.687 or diffYAxis != -10.526 or diffZAxis != -57.452 or threeDDistance != 58.47:
            return False
        return True

    def test_CalculateDisplacement2(self):
        logic = Q3DCLogic.Q3DCLogic(slicer.modules.Q3DCWidget)
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