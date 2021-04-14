import csv
from collections import defaultdict
import json
import logging
import math
import os
import time

import ctk
import numpy as np
import qt
import scipy.spatial
import vtk

import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import NodeModify

# needed for topological sort. Yes, this is basically just DFS.
try:
    import networkx as nx
except ModuleNotFoundError as e:
    # This requires a network connection!
    slicer.util.pip_install('networkx')
    import networkx as nx


#
# CalculateDisplacement
#

class Q3DC(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Q3DC "
        parent.categories = ["Quantification"]
        parent.dependencies = []
        parent.contributors = [
            'Lucie Macron (University of Michigan)',
            'Jean-Baptiste VIMORT (University of Michigan)',
            'James Hoctor (Kitware Inc)',
        ]
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

    def setup(self):
        logging.debug("Q3DC Widget Setup")
        ScriptedLoadableModuleWidget.setup(self)
        # GLOBALS:
        self.interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        self.computedAnglesList = list()
        self.renderer1 = None
        self.actor1 = None
        self.renderer2 = None
        self.actor2 = None
        self.renderer3 = None
        self.actor3 = None

        # Load widget from .ui file (created by Qt Designer)
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/Q3DC.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        self.logic = Q3DCLogic(self.ui)
        self.logic.UpdateInterface = self.UpdateInterface

        # -------------------------- Scene ---------------------------
        self.SceneCollapsibleButton = self.ui.SceneCollapsibleButton # this attribute is usefull for Longitudinal quantification extension
        treeView = self.ui.treeView
        treeView.setMRMLScene(slicer.app.mrmlScene())
        treeView.sceneModel().setHorizontalHeaderLabels(["Models"])
        treeView.sortFilterProxyModel().nodeTypes = ['vtkMRMLModelNode','vtkMRMLMarkupsFiducialNode']
        treeView.header().setVisible(False)

        # ------------------ Landmark Modification -------------------
        self.inputModelLabel = self.ui.inputModelLabel  # this attribute is usefull for Longitudinal quantification extension
        self.inputLandmarksLabel = self.ui.inputLandmarksLabel  # this attribute is usefull for Longitudinal quantification extension
        self.ui.inputModelSelector.setMRMLScene(slicer.mrmlScene)
        self.ui.inputModelSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onModelChanged)
        self.ui.addLandmarkButton.connect('clicked()', self.onAddLandmarkButtonClicked)
        self.ui.inputLandmarksSelector.setMRMLScene(slicer.mrmlScene)
        self.ui.inputLandmarksSelector.setEnabled(False) # The "enable" property seems to not be imported from the .ui
        self.ui.inputLandmarksSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onLandmarksChanged)
        self.ui.landmarkComboBox.connect('currentIndexChanged(QString)', self.UpdateInterface)
        self.ui.surfaceDeplacementCheckBox.connect('stateChanged(int)', self.onSurfaceDeplacementStateChanged)

        # --------------------- Anatomical Legend --------------------
        self.suggested_landmarks = self.logic.load_suggested_landmarks(
            self.resourcePath('Data/base_fiducial_legend.csv'))
        self.anatomical_legend_space = self.ui.landmarkModifLayout
        self.anatomical_radio_buttons_layout = qt.QHBoxLayout()
        self.anatomical_legend_space.addLayout(self.anatomical_radio_buttons_layout)

        self.anatomical_legend = None
        self.init_anatomical_legend()
        self.anatomical_legend_view = slicer.qMRMLTableView()
        self.anatomical_legend_view.setMRMLTableNode(self.anatomical_legend)
        self.anatomical_legend_space.addWidget(self.anatomical_legend_view)
        self.anatomical_legend_view.show()
        self.anatomical_legend_view.setSelectionBehavior(
            qt.QAbstractItemView.SelectRows
        )
        self.anatomical_legend_view.connect('selectionChanged()', self.on_legend_row_selected)

        self.init_anatomical_radio_buttons()

        self.ui.legendFileButton.connect('clicked()', self.on_select_legend_file_clicked)

        # -------------------- Compute Mid Point ---------------------
        self.ui.landmarkComboBox1.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.landmarkComboBox2.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.defineMiddlePointButton.connect('clicked()', self.onDefineMidPointClicked)

        # ------------------- Calculate Distances --------------------
        self.ui.fidListComboBoxA.setMRMLScene(slicer.mrmlScene)
        self.ui.fidListComboBoxB.setMRMLScene(slicer.mrmlScene)
        self.ui.computeDistancesPushButton.connect('clicked()', self.onComputeDistanceClicked)
        self.ui.landmarkComboBoxA.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.landmarkComboBoxB.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.fidListComboBoxA.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.ui.fidListComboBoxA, self.ui.landmarkComboBoxA))
        self.ui.fidListComboBoxB.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.ui.fidListComboBoxB, self.ui.landmarkComboBoxB))
        # ---------------------- Save Distances ----------------------
        self.distance_table = self.logic.createDistanceTable()
        slicer.mrmlScene.AddNode(self.distance_table)
        self.distance_table_view = slicer.qMRMLTableView()
        self.distance_table_view.setMRMLTableNode(self.distance_table)
        self.directoryExportDistance = ctk.ctkDirectoryButton()
        self.filenameExportDistance = qt.QLineEdit('distance.csv')
        self.exportDistanceButton = qt.QPushButton(" Export ")
        self.exportDistanceButton.connect('clicked()', self.onExportButton)
        self.exportDistanceButton.enabled = True
        self.deleteDistanceRowButton = qt.QPushButton("Delete Selected Row")
        self.deleteDistanceRowButton.connect('clicked()', self.distance_table_view.deleteRow)
        self.pathExportDistanceLayout = qt.QVBoxLayout()
        self.pathExportDistanceLayout.addWidget(self.directoryExportDistance)
        self.pathExportDistanceLayout.addWidget(self.filenameExportDistance)
        self.exportDistanceLayout = qt.QHBoxLayout()
        self.exportDistanceLayout.addLayout(self.pathExportDistanceLayout)
        self.exportDistanceLayout.addWidget(self.exportDistanceButton)
        self.tableAndExportLayout = qt.QVBoxLayout()
        self.tableAndExportLayout.addWidget(self.distance_table_view)
        self.tableAndExportLayout.addWidget(self.deleteDistanceRowButton)
        self.tableAndExportLayout.addLayout(self.exportDistanceLayout)

        # --------------------- Calculate Angles ---------------------
        self.ui.fidListComboBoxline1LA.setMRMLScene(slicer.mrmlScene)
        self.ui.fidListComboBoxline1LB.setMRMLScene(slicer.mrmlScene)
        self.ui.fidListComboBoxline2LA.setMRMLScene(slicer.mrmlScene)
        self.ui.fidListComboBoxline2LB.setMRMLScene(slicer.mrmlScene)
        self.ui.fidListComboBoxline1LA.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.ui.fidListComboBoxline1LA, self.ui.line1LAComboBox))
        self.ui.fidListComboBoxline1LB.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.ui.fidListComboBoxline1LB, self.ui.line1LBComboBox))
        self.ui.fidListComboBoxline2LA.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.ui.fidListComboBoxline2LA, self.ui.line2LAComboBox))
        self.ui.fidListComboBoxline2LB.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.ui.fidListComboBoxline2LB, self.ui.line2LBComboBox))
        self.ui.computeAnglesPushButton.connect('clicked()', self.onComputeAnglesClicked)
        self.ui.line1LAComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.line1LBComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.line2LAComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.line2LBComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.pitchCheckBox.connect('clicked(bool)', self.UpdateInterface)
        self.ui.rollCheckBox.connect('clicked(bool)', self.UpdateInterface)
        self.ui.yawCheckBox.connect('clicked(bool)', self.UpdateInterface)
        # ----------------------- Save Angles ------------------------
        self.angles_table = self.logic.createAnglesTable()
        slicer.mrmlScene.AddNode(self.angles_table)
        self.angles_table_view = slicer.qMRMLTableView()
        self.angles_table_view.setMRMLTableNode(self.angles_table)
        self.directoryExportAngle = ctk.ctkDirectoryButton()
        self.filenameExportAngle = qt.QLineEdit('angle.csv')
        self.exportAngleButton = qt.QPushButton("Export")
        self.exportAngleButton.connect('clicked()', self.onExportAngleButton)
        self.exportAngleButton.enabled = True
        self.deleteAngleRowButton = qt.QPushButton("Delete Selected Row")
        self.deleteAngleRowButton.connect('clicked()', self.angles_table_view.deleteRow)
        self.pathExportAngleLayout = qt.QVBoxLayout()
        self.pathExportAngleLayout.addWidget(self.directoryExportAngle)
        self.pathExportAngleLayout.addWidget(self.filenameExportAngle)
        self.exportAngleLayout = qt.QHBoxLayout()
        self.exportAngleLayout.addLayout(self.pathExportAngleLayout)
        self.exportAngleLayout.addWidget(self.exportAngleButton)
        self.tableAndExportAngleLayout = qt.QVBoxLayout()
        self.tableAndExportAngleLayout.addWidget(self.angles_table_view)
        self.tableAndExportAngleLayout.addWidget(self.deleteAngleRowButton)
        self.tableAndExportAngleLayout.addLayout(self.exportAngleLayout)

        # -------------- Calculate Line-Point Distances --------------
        self.ui.fidListComboBoxlineLA.setMRMLScene(slicer.mrmlScene)
        self.ui.fidListComboBoxlineLB.setMRMLScene(slicer.mrmlScene)
        self.ui.fidListComboBoxlinePoint.setMRMLScene(slicer.mrmlScene)
        self.ui.fidListComboBoxlineLA.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.ui.fidListComboBoxlineLA, self.ui.lineLAComboBox))
        self.ui.fidListComboBoxlineLB.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.ui.fidListComboBoxlineLB, self.ui.lineLBComboBox))
        self.ui.fidListComboBoxlinePoint.connect('currentNodeChanged(vtkMRMLNode*)',
                                      lambda: self.logic.UpdateLandmarkComboboxA(self.ui.fidListComboBoxlinePoint, self.ui.linePointComboBox))
        self.ui.computeLinePointPushButton.connect('clicked()', self.onComputeLinePointClicked)
        self.ui.lineLAComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.lineLBComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        # ---------------- Save Line-Point Distances -----------------
        self.line_point_table = self.logic.createLinePointTable()
        slicer.mrmlScene.AddNode(self.line_point_table)
        self.line_point_table_view = slicer.qMRMLTableView()
        self.line_point_table_view.setMRMLTableNode(self.line_point_table)
        self.directoryExportLinePoint = ctk.ctkDirectoryButton()
        self.filenameExportLinePoint = qt.QLineEdit('linePoint.csv')
        self.exportLinePointButton = qt.QPushButton("Export")
        self.exportLinePointButton.connect('clicked()', self.onExportLinePointButton)
        self.exportLinePointButton.enabled = True
        self.deleteLinePointRowButton = qt.QPushButton("Delete Selected Row")
        self.deleteLinePointRowButton.connect('clicked()', self.line_point_table_view.deleteRow)
        self.pathExportLinePointLayout = qt.QVBoxLayout()
        self.pathExportLinePointLayout.addWidget(self.directoryExportLinePoint)
        self.pathExportLinePointLayout.addWidget(self.filenameExportLinePoint)
        self.exportLinePointLayout = qt.QHBoxLayout()
        self.exportLinePointLayout.addLayout(self.pathExportLinePointLayout)
        self.exportLinePointLayout.addWidget(self.exportLinePointButton)
        self.tableAndExportLinePointLayout = qt.QVBoxLayout()
        self.tableAndExportLinePointLayout.addWidget(self.line_point_table_view)
        self.tableAndExportLinePointLayout.addWidget(self.deleteLinePointRowButton)
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
        self.ui.landmarkComboBox1.clear()
        self.ui.landmarkComboBox.clear()
        self.ui.fidListComboBoxA.setCurrentNode(None)
        self.ui.fidListComboBoxB.setCurrentNode(None)
        self.ui.fidListComboBoxline1LA.setCurrentNode(None)
        self.ui.fidListComboBoxline1LB.setCurrentNode(None)
        self.ui.fidListComboBoxline2LA.setCurrentNode(None)
        self.ui.fidListComboBoxline2LB.setCurrentNode(None)
        self.ui.line1LAComboBox.clear()
        self.ui.line1LBComboBox.clear()
        self.ui.line2LAComboBox.clear()
        self.ui.line2LBComboBox.clear()
        self.ui.landmarkComboBox2.clear()
        self.ui.fidListComboBoxline2LB.setCurrentNode(None)
        self.ui.inputModelSelector.setCurrentNode(None)
        self.ui.inputLandmarksSelector.setCurrentNode(None)
        self.distance_table.RemoveAllColumns()
        self.angles_table.RemoveAllColumns()
        self.line_point_table.RemoveAllColumns()

    def enter(self):
        logging.debug("enter Q3DC")
        model = self.ui.inputModelSelector.currentNode()
        fidlist = self.ui.inputLandmarksSelector.currentNode()

        if fidlist:
            if fidlist.GetAttribute("connectedModelID") != model.GetID():
                self.ui.inputModelSelector.setCurrentNode(None)
                self.ui.inputLandmarksSelector.setCurrentNode(None)
                self.ui.landmarkComboBox.clear()
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
        self.ui.defineMiddlePointButton.enabled = self.ui.landmarkComboBox1.currentText != '' and \
                                               self.ui.landmarkComboBox2.currentText != '' and \
                                               self.ui.landmarkComboBox1.currentText != self.ui.landmarkComboBox2.currentText
        self.ui.computeDistancesPushButton.enabled = self.ui.landmarkComboBoxA.currentText != '' and\
                                                  self.ui.landmarkComboBoxB.currentText != '' and\
                                                  (self.ui.fidListComboBoxA.currentNodeID, self.ui.landmarkComboBoxA.currentText) != \
                                                  (self.ui.fidListComboBoxB.currentNodeID, self.ui.landmarkComboBoxB.currentText)
        self.ui.computeAnglesPushButton.enabled = self.ui.line1LAComboBox.currentText != '' and\
                                               self.ui.line1LBComboBox.currentText != '' and\
                                               self.ui.line2LAComboBox.currentText != '' and\
                                               self.ui.line2LBComboBox.currentText != '' and\
                                               (self.ui.fidListComboBoxline1LA.currentNodeID, self.ui.line1LAComboBox.currentText) != \
                                               (self.ui.fidListComboBoxline1LB.currentNodeID, self.ui.line1LBComboBox.currentText) and\
                                               (self.ui.fidListComboBoxline2LA.currentNodeID, self.ui.line2LAComboBox.currentText) != \
                                               (self.ui.fidListComboBoxline2LB.currentNodeID, self.ui.line2LBComboBox.currentText) and\
                                               (self.ui.pitchCheckBox.isChecked() or
                                                self.ui.rollCheckBox.isChecked() or
                                                self.ui.yawCheckBox.isChecked() )
        self.ui.computeLinePointPushButton.enabled = self.ui.lineLAComboBox.currentText != '' and\
                                                  self.ui.lineLBComboBox.currentText != '' and\
                                                  self.ui.linePointComboBox.currentText != '' and\
                                                  (self.ui.fidListComboBoxlineLA.currentNodeID, self.ui.lineLAComboBox.currentText) != \
                                                  (self.ui.fidListComboBoxlineLB.currentNodeID, self.ui.lineLBComboBox.currentText)

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
        if self.ui.line1LAComboBox.currentText != '' and\
                        self.ui.line1LBComboBox.currentText != '' and\
                        self.ui.line1LAComboBox.currentText != self.ui.line1LBComboBox.currentText :
            self.renderer1, self.actor1 = \
                self.logic.drawLineBetween2Landmark(self.ui.line1LAComboBox.currentText,
                                                    self.ui.line1LBComboBox.currentText,
                                                    self.ui.fidListComboBoxline1LA.currentNode(),
                                                    self.ui.fidListComboBoxline1LB.currentNode())
        if self.ui.line2LAComboBox.currentText != '' and\
                        self.ui.line2LBComboBox.currentText != '' and\
                        self.ui.line2LAComboBox.currentText != self.ui.line2LBComboBox.currentText :
            self.renderer2, self.actor2 = \
                self.logic.drawLineBetween2Landmark(self.ui.line2LAComboBox.currentText,
                                                    self.ui.line2LBComboBox.currentText,
                                                    self.ui.fidListComboBoxline2LA.currentNode(),
                                                    self.ui.fidListComboBoxline2LB.currentNode())
        if self.ui.lineLAComboBox.currentText != '' and\
                        self.ui.lineLBComboBox.currentText != '' and\
                        self.ui.lineLAComboBox.currentText != self.ui.lineLBComboBox.currentText:
            self.renderer3, self.actor3 = \
                self.logic.drawLineBetween2Landmark(self.ui.lineLAComboBox.currentText,
                                                    self.ui.lineLBComboBox.currentText,
                                                    self.ui.fidListComboBoxlineLA.currentNode(),
                                                    self.ui.fidListComboBoxlineLB.currentNode())
        self.logic.UpdateThreeDView(self.ui.landmarkComboBox.currentText)

    def init_anatomical_legend(self):
        if self.anatomical_legend is None:
            for table_node in slicer.mrmlScene.GetNodesByClass('vtkMRMLTableNode'):
                if table_node.GetAttribute('Q3DC.is_anatomical_legend') == 'True':
                    self.anatomical_legend = table_node
            if self.anatomical_legend is None:
                self.anatomical_legend = slicer.vtkMRMLTableNode()
                self.anatomical_legend.SetSaveWithScene(False)
                self.anatomical_legend.SetLocked(True)
                slicer.mrmlScene.AddNode(self.anatomical_legend)
                self.anatomical_legend.SetAttribute('Q3DC.is_anatomical_legend', 'True')

        al = self.anatomical_legend
        with NodeModify(al):
            al.RemoveAllColumns()
            al.AddColumn().SetName('Landmark')
            al.AddColumn().SetName('Description')
            al.SetUseColumnNameAsColumnHeader(True)

    def init_anatomical_radio_buttons(self):
        self.anatomical_radio_buttons = \
            [qt.QRadioButton(region) for region in self.suggested_landmarks.keys()]
        for i in range(self.anatomical_radio_buttons_layout.count()-1, -1, -1):
            self.anatomical_radio_buttons_layout.itemAt(i).widget().setParent(None)
        for radio_button in self.anatomical_radio_buttons:
            self.anatomical_radio_buttons_layout.addWidget(radio_button)
            radio_button.toggled.connect(
                lambda state, _radio_button=radio_button:
                    self.on_anatomical_radio_button_toggled(state, _radio_button)
            )
        self.anatomical_radio_buttons[0].toggle()

    def on_anatomical_radio_button_toggled(self, state, radio_button):
        if state:
            self.init_anatomical_legend()
            region = radio_button.text

            # set this in the logic rather than the widget since events are handled there.
            self.logic.current_suggested_landmarks = self.suggested_landmarks[region]

            al = self.anatomical_legend
            with NodeModify(al):
                for landmark, description in self.logic.current_suggested_landmarks:
                    new_row_index = al.AddEmptyRow()
                    al.SetCellText(new_row_index, 0, landmark)
                    al.SetCellText(new_row_index, 1, description)
            self.anatomical_legend_view.resizeColumnsToContents()

    def on_legend_row_selected(self):
        # Calculate the index of the selected point.
        fidList = self.logic.selectedFidList
        if not fidList:
            return
        selectedFidReflID = self.logic.findIDFromLabel(
            fidList,
            self.ui.landmarkComboBox.currentText
        )
        if selectedFidReflID is None:
            # code would run correctly if we continued but wouldn't do anything
            return
        fid_index = fidList.GetNthControlPointIndexByID(selectedFidReflID)
        old_name = fidList.GetNthControlPointLabel(fid_index)

        # Look in the legend for the info from the selected row.
        selected_indices = self.anatomical_legend_view.selectedIndexes()
        if len(selected_indices) != 2:
            return
        name_index, description_index = selected_indices
        row_index = name_index.row()
        name = self.anatomical_legend.GetCellText(row_index, 0)
        description = self.anatomical_legend.GetCellText(row_index, 1)

        # Refuse to create multiple fiducials with the same name.
        for i in range(fidList.GetNumberOfControlPoints()):
            if name == fidList.GetNthControlPointLabel(i):
                return

        # Set the name and description of the selected point.
        fidList.SetNthControlPointLabel(fid_index, name)
        fidList.SetNthControlPointDescription(fid_index, description)

        # Update the landmark combo boxes to reflect the name change.
        self.logic.updateLandmarkComboBox(fidList, self.ui.landmarkComboBox, False)
        self.ui.landmarkComboBox.setCurrentText(name)
        for box in (self.ui.landmarkComboBox1, self.ui.landmarkComboBox2):
            new_selection = box.currentText
            if new_selection == old_name:
                new_selection = name
            self.logic.updateLandmarkComboBox(fidList, box)
            box.setCurrentText(new_selection)
        self.UpdateInterface()

    def on_select_legend_file_clicked(self):
        legend_filename = qt.QFileDialog.getOpenFileName(
            None,'Select File', '', 'CSV (*.csv)')
        if legend_filename == '':
            # User canceled the file selection dialog.
            return
        suggested_landmarks = self.logic.load_suggested_landmarks(
            legend_filename)
        if suggested_landmarks is None:
            return
        self.suggested_landmarks = suggested_landmarks
        self.init_anatomical_radio_buttons()

    def onModelChanged(self):
        logging.debug("Model Changed")
        if self.logic.selectedModel:
            Model = self.logic.selectedModel
            try:
                Model.RemoveObserver(self.logic.decodeJSON(self.logic.selectedModel.GetAttribute("modelModifieTagEvent")))
            except:
                pass
        self.logic.selectedModel = self.ui.inputModelSelector.currentNode()
        self.logic.ModelChanged(self.ui.inputModelSelector, self.ui.inputLandmarksSelector)
        self.ui.inputLandmarksSelector.setCurrentNode(None)

    def onLandmarksChanged(self):
        logging.debug("Landmarks Changed")
        if self.ui.inputModelSelector.currentNode():
            self.logic.FidList = self.ui.inputLandmarksSelector.currentNode()
            self.logic.selectedFidList = self.ui.inputLandmarksSelector.currentNode()
            self.logic.selectedModel = self.ui.inputModelSelector.currentNode()
            if self.ui.inputLandmarksSelector.currentNode():
                onSurface = self.ui.loadLandmarksOnSurfacCheckBox.isChecked()
                self.logic.connectLandmarks(self.ui.inputModelSelector,
                                      self.ui.inputLandmarksSelector,
                                      onSurface)
            else:
                self.ui.landmarkComboBox.clear()

    def onAddLandmarkButtonClicked(self):
        # Add fiducial on the scene.
        # If no input model selected, the addition of fiducial shouldn't be possible.
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        self.logic.enable_legend_labels = self.ui.enableLegendLabels.isChecked()
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
        selectedFidReflID = self.logic.findIDFromLabel(fidList, self.ui.landmarkComboBox.currentText)
        isOnSurface = self.ui.surfaceDeplacementCheckBox.isChecked()
        landmarkDescription = self.logic.decodeJSON(fidList.GetAttribute("landmarkDescription"))
        if isOnSurface:
            hardenModel = slicer.app.mrmlScene().GetNodeByID(fidList.GetAttribute("hardenModelID"))
            landmarkDescription[selectedFidReflID]["projection"]["isProjected"] = True
            landmarkDescription[selectedFidReflID]["projection"]["closestPointIndex"] =\
                self.logic.projectOnSurface(hardenModel, fidList, selectedFidReflID)
        else:
            landmarkDescription[selectedFidReflID]["projection"]["isProjected"] = False
            landmarkDescription[selectedFidReflID]["projection"]["closestPointIndex"] = None
        fidList.SetAttribute("landmarkDescription",self.logic.encodeJSON(landmarkDescription))

    def onDefineMidPointClicked(self):
        fidList = self.logic.selectedFidList
        if not fidList:
            self.logic.warningMessage("Please select a model of reference and a fiducial List.")
        label1 = self.ui.landmarkComboBox1.currentText
        label2 = self.ui.landmarkComboBox2.currentText
        landmark1ID = self.logic.findIDFromLabel(fidList, label1)
        landmark2ID = self.logic.findIDFromLabel(fidList, label2)
        coord = self.logic.calculateMidPointCoord(fidList, landmark1ID, landmark2ID)
        fidList.AddFiducial(coord[0],coord[1],coord[2], f'{label1}_{label2}')
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

        if self.ui.midPointOnSurfaceCheckBox.isChecked():
            landmarkDescription[markupID]["projection"]["isProjected"] = True
            hardenModel = slicer.app.mrmlScene().GetNodeByID(fidList.GetAttribute("hardenModelID"))
            landmarkDescription[markupID]["projection"]["closestPointIndex"] = \
                self.logic.projectOnSurface(hardenModel, fidList, markupID)
        else:
            landmarkDescription[markupID]["projection"]["isProjected"] = False
        fidList.SetAttribute("landmarkDescription",self.logic.encodeJSON(landmarkDescription))
        self.logic.UpdateInterface()
        self.logic.updateLandmarkComboBox(fidList, self.ui.landmarkComboBox, False)
        fidList.SetNthFiducialPositionFromArray(numOfMarkups - 1, coord)

    def onComputeDistanceClicked(self):
        fidList = self.logic.selectedFidList
        fidListA = self.ui.fidListComboBoxA.currentNode()
        fidListB = self.ui.fidListComboBoxB.currentNode()
        nameList = [fidListA.GetName(), fidListB.GetName()]
        if not fidList:
            self.logic.warningMessage("Please connect a fiducial list to a model.")
            return
        for fidListIter in list(set(nameList)):
            landmarkDescription = slicer.mrmlScene.GetNodesByName(fidListIter).GetItemAsObject(0). \
                GetAttribute("landmarkDescription")
            if not landmarkDescription:
                self.logic.warningMessage(
                    f'{fidListIter} is not connected to a model. Please use "Add and Move '
                    'Landmarks" panel to connect the landmarks to a model.')
                return

        self.ui.distanceLayout.addLayout(self.tableAndExportLayout)

        key, args = self.logic.getDistanceArgs(
            fidListA=self.ui.fidListComboBoxA.currentNode(),
            fidListB=self.ui.fidListComboBoxB.currentNode(),
            fidLabelA=self.ui.landmarkComboBoxA.currentText,
            fidLabelB=self.ui.landmarkComboBoxB.currentText
        )
        data = self.logic.computeDistance(*args)

        self.logic.updateTable(self.distance_table, key, data)
        self.logic.updateTableView(self.distance_table, self.distance_table_view)

    def onComputeAnglesClicked(self):
        fidList = self.logic.selectedFidList
        fidListline1LA = self.ui.fidListComboBoxline1LA.currentNode()
        fidListline1LB = self.ui.fidListComboBoxline1LB.currentNode()
        fidListline2LA = self.ui.fidListComboBoxline2LA.currentNode()
        fidListline2LB = self.ui.fidListComboBoxline2LB.currentNode()
        nameList = [fidListline1LA.GetName(), fidListline1LB.GetName(), fidListline2LA.GetName(), fidListline2LB.GetName()]
        if not fidList:
            self.logic.warningMessage("Please connect a fiducial list to a model.")
            return
        for fidListIter in list(set(nameList)):
            landmarkDescription = slicer.mrmlScene.GetNodesByName(fidListIter).GetItemAsObject(0). \
                GetAttribute("landmarkDescription")
            if not landmarkDescription:
                self.logic.warningMessage(
                    f'{fidListIter} is not connected to a model. Please use "Add and Move '
                    'Landmarks" panel to connect the landmarks to a model.')
                return

        self.ui.angleLayout.addLayout(self.tableAndExportAngleLayout)

        key, args = self.logic.getAnglesArgs(
            fidlist1A=self.ui.fidListComboBoxline1LA.currentNode(),
            fidlist1B=self.ui.fidListComboBoxline1LB.currentNode(),
            fidlist2A=self.ui.fidListComboBoxline2LA.currentNode(),
            fidlist2B=self.ui.fidListComboBoxline2LB.currentNode(),
            fidLabel1A=self.ui.line1LAComboBox.currentText,
            fidLabel1B=self.ui.line1LBComboBox.currentText,
            fidLabel2A=self.ui.line2LAComboBox.currentText,
            fidLabel2B=self.ui.line2LBComboBox.currentText,
            yawState=self.ui.yawCheckBox.isChecked(),
            pitchState=self.ui.pitchCheckBox.isChecked(),
            rollState=self.ui.rollCheckBox.isChecked()
        )
        data = self.logic.computeAngles(*args)

        self.logic.updateTable(self.angles_table, key, data)
        self.logic.updateTableView(self.angles_table, self.angles_table_view)

    def onComputeLinePointClicked(self):
        fidList = self.logic.selectedFidList
        if not fidList:
            self.logic.warningMessage("Please connect a fiducial list to a model.")
            return
        fidListlineLA = self.ui.fidListComboBoxlineLA.currentNode()
        fidListlineLB = self.ui.fidListComboBoxlineLB.currentNode()
        fidListPoint = self.ui.fidListComboBoxlinePoint.currentNode()
        nameList = [fidListlineLA.GetName(), fidListlineLB.GetName(), fidListPoint.GetName()]
        for fidListIter in list(set(nameList)):
            landmarkDescription = slicer.mrmlScene.GetNodesByName(fidListIter).GetItemAsObject(0). \
                GetAttribute("landmarkDescription")
            if not landmarkDescription:
                self.logic.warningMessage(
                    f'{fidListIter} is not connected to a model. Please use "Add and Move '
                    'Landmarks" panel to connect the landmarks to a model.')
                return

        self.ui.LinePointLayout.addLayout(self.tableAndExportLinePointLayout)

        key, args = self.logic.getLinePointArgs(
            fidListLineA=self.ui.fidListComboBoxlineLA.currentNode(),
            fidListLineB=self.ui.fidListComboBoxlineLB.currentNode(),
            fidListPoint=self.ui.fidListComboBoxlinePoint.currentNode(),
            fidLabelLineA=self.ui.lineLAComboBox.currentText,
            fidLabelLineB=self.ui.lineLBComboBox.currentText,
            fidLabelPoint=self.ui.linePointComboBox.currentText
        )
        data = self.logic.computeLinePoint(*args)

        self.logic.updateTable(self.line_point_table, key, data)
        self.logic.updateTableView(self.line_point_table, self.line_point_table_view)

    def onExportButton(self):
        self.logic.exportationFunction(
            self.directoryExportDistance,
            self.filenameExportDistance,
            self.distance_table,
            'distance'
        )

    def onExportAngleButton(self):
        self.logic.exportationFunction(
            self.directoryExportAngle,
            self.filenameExportAngle,
            self.angles_table,
            'angle'
        )

    def onExportLinePointButton(self):
        self.logic.exportationFunction(
            self.directoryExportLinePoint,
            self.filenameExportLinePoint,
            self.line_point_table,
            'linePoint'
        )


class Q3DCLogic(ScriptedLoadableModuleLogic):
    def __init__(self, interface):
        self.interface = interface
        self.selectedModel = None
        self.selectedFidList = None
        self.current_suggested_landmarks = None
        self.enable_legend_labels = True
        self.numberOfDecimals = 3
        self.tolerance = 1e-5
        system = qt.QLocale().system()
        self.decimalPoint = chr(system.decimalPoint())
        self.comboboxdict = dict()

    @staticmethod
    def load_suggested_landmarks(filepath):
        suggested_landmarks = defaultdict(list)
        try:
            with open(filepath, newline='', encoding='utf8') as suggestions_file:
                reader = csv.DictReader(suggestions_file)
                for row in reader:
                    region = row['Region'].title()
                    landmark = row['Landmark']
                    name = row['Name']
                    suggested_landmarks[region].append((landmark, name))
            return suggested_landmarks
        except OSError as e:
            slicer.util.delayDisplay('Unable to find/open file.')
            logging.info('User attempted to open a landmark legend file.\n' + repr(e))
            return None
        except csv.Error as e:
            slicer.util.delayDisplay('The selected file is not formatted properly.')
            logging.info('User attempted to open a landmark legend file.\n' + repr(e))
            return None
        except KeyError as e:
            slicer.util.delayDisplay('The selected file does not have the right column names.')
            logging.info('User attempted to open a landmark legend file.\n' + repr(e))
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

    def UpdateThreeDView(self, landmarkLabel):
        # Update the 3D view on Slicer
        if not self.selectedFidList:
            return
        if not self.selectedModel:
            return
        logging.debug("UpdateThreeDView")
        active = self.selectedFidList
        #deactivate all landmarks
        list = slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsFiducialNode")
        end = list.GetNumberOfItems()
        selectedFidReflID = self.findIDFromLabel(active,landmarkLabel)
        for i in range(0,end):
            fidList = list.GetItemAsObject(i)
            logging.info('fidList ID: %s', fidList.GetID())
            landmarkDescription = self.decodeJSON(fidList.GetAttribute("landmarkDescription"))
            if landmarkDescription:
                for key in landmarkDescription.keys():
                    markupsIndex = fidList.GetNthControlPointIndexByID(key)
                    if key != selectedFidReflID:
                        fidList.SetNthMarkupLocked(markupsIndex, True)
                    else:
                        fidList.SetNthMarkupLocked(markupsIndex, False)
                        fidList.SetNthMarkupLocked(markupsIndex, False)

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
                            markupsIndex = fidList.GetNthControlPointIndexByID(markupID)
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

    @staticmethod
    def recover_midpoint_provenance(landmarks):
        '''
        When a new list of fiducials is loaded from a file, we know which are
        midpoints, but we don't know from which points those midpoints were
        constructed. This function recovers this information.
        '''
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
            else:       # midpoint
                ids_and_midpoints.append((markupID, markup_pos))
            all_ids.append(markupID)

        # This is the structure we want to populate to help build
        # landmarkDescription in createNewDataStructure.
        midpoint_data = {
                point_id: {
                    'definedByThisMarkup': [],
                    'isMidPoint': False,
                    'Point1': None,
                    'Point2': None,
                } for point_id in all_ids
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
                    hp = 2*mp - p
                    max_error = np.linalg.norm(mp - p) / 10000.0
                    distance, kdt_p_idx = kdt.query(
                            hp, distance_upper_bound=max_error)
                    # distance = np.inf on failure
                    if distance < max_error:
                        ids = (point_ids[p_idx], point_ids[kdt_p_idx])
                        midpoint_data[mp_id].update({
                                'isMidPoint': True,
                                'Point1': ids[0],
                                'Point2': ids[1],
                            })
                        for id_ in ids:
                            midpoint_data[id_]['definedByThisMarkup'].append(mp_id)

                        provenance_found = True
                        point_ids.append(mp_id)
                        points = np.concatenate((points, mp.reshape((1, 3))))
                        n_new_points += 1
                        break
                if not provenance_found:
                    new_ids_and_midpoints.append((mp_id, mp))
            ids_and_midpoints = new_ids_and_midpoints

        return midpoint_data

    def createNewDataStructure(self, landmarks, model, onSurface):
        landmarks.SetAttribute("connectedModelID",model.GetID())
        landmarks.SetAttribute("hardenModelID",model.GetAttribute("hardenModelID"))
        landmarkDescription = dict()

        midpoint_data = self.recover_midpoint_provenance(landmarks)
        for n in range(landmarks.GetNumberOfMarkups()):
            markupID = landmarks.GetNthMarkupID(n)
            landmarkDescription[markupID] = {'midPoint': midpoint_data[markupID]}

        for n in range(landmarks.GetNumberOfMarkups()):
            markupID = landmarks.GetNthMarkupID(n)
            landmarkLabel = landmarks.GetNthMarkupLabel(n)
            landmarkDescription[markupID]["landmarkLabel"] = landmarkLabel
            landmarkDescription[markupID]["projection"] = dict()
            if onSurface and not landmarkDescription[markupID]['midPoint']['isMidPoint']:
                landmarkDescription[markupID]["projection"]["isProjected"] = True
                hardenModel = slicer.app.mrmlScene().GetNodeByID(landmarks.GetAttribute("hardenModelID"))
                landmarkDescription[markupID]["projection"]["closestPointIndex"] = \
                    self.projectOnSurface(hardenModel, landmarks, markupID)
            else:
                landmarkDescription[markupID]["projection"]["isProjected"] = False
                landmarkDescription[markupID]["projection"]["closestPointIndex"] = None

        if onSurface:
            for n in range(landmarks.GetNumberOfMarkups()):
                markupID = landmarks.GetNthMarkupID(n)
                nth_midpoint_data = landmarkDescription[markupID]['midPoint']
                if nth_midpoint_data['isMidPoint']:
                    parent_id1 = nth_midpoint_data['Point1']
                    parent_id2 = nth_midpoint_data['Point2']
                    coord = self.calculateMidPointCoord(landmarks, parent_id1, parent_id2)
                    index = landmarks.GetNthControlPointIndexByID(markupID)
                    landmarks.SetNthFiducialPositionFromArray(index, coord)

        landmarks.SetAttribute("landmarkDescription",self.encodeJSON(landmarkDescription))
        planeDescription = dict()
        landmarks.SetAttribute("planeDescription",self.encodeJSON(planeDescription))
        landmarks.SetAttribute("isClean",self.encodeJSON({"isClean":False}))
        landmarks.SetAttribute("lastTransformID",None)

        self.conform_selectedness_to_midpoint_status(landmarks)

    def conform_selectedness_to_midpoint_status(self, landmarks):
        landmarkDescription = self.decodeJSON(landmarks.GetAttribute("landmarkDescription"))
        for n in range(landmarks.GetNumberOfMarkups()):
            markupID = landmarks.GetNthMarkupID(n)
            isMidPoint = landmarkDescription[markupID]['midPoint']['isMidPoint']
            landmarks.SetNthFiducialSelected(n, not isMidPoint)

    def changementOfConnectedModel(self, landmarks, model, onSurface):
        landmarks.SetAttribute("connectedModelID", model.GetID())
        landmarks.SetAttribute("hardenModelID", model.GetAttribute("hardenModelID"))
        landmarkDescription = self.decodeJSON(landmarks.GetAttribute("landmarkDescription"))

        D = nx.DiGraph()
        for n in range(landmarks.GetNumberOfMarkups()):
            markupID = landmarks.GetNthMarkupID(n)
            D.add_node(markupID)
            dbtm = landmarkDescription[markupID]['midPoint']['definedByThisMarkup']
            for dependent_point in dbtm:
                D.add_edge(markupID, dependent_point)

        for markupID in nx.topological_sort(D):
            if onSurface:
                if landmarkDescription[markupID]["projection"]["isProjected"] == True:
                    hardenModel = slicer.app.mrmlScene().GetNodeByID(landmarks.GetAttribute("hardenModelID"))
                    landmarkDescription[markupID]["projection"]["closestPointIndex"] = \
                        self.projectOnSurface(hardenModel, landmarks, markupID)
                elif landmarkDescription[markupID]['midPoint']['isMidPoint']:
                    parent_id1 = landmarkDescription[markupID]['midPoint']['Point1']
                    parent_id2 = landmarkDescription[markupID]['midPoint']['Point2']
                    coord = self.calculateMidPointCoord(landmarks, parent_id1, parent_id2)
                    index = landmarks.GetNthControlPointIndexByID(markupID)
                    landmarks.SetNthFiducialPositionFromArray(index, coord)
            else:
                landmarkDescription[markupID]["projection"]["isProjected"] = False
                landmarkDescription[markupID]["projection"]["closestPointIndex"] = None

        landmarks.SetAttribute("landmarkDescription", self.encodeJSON(landmarkDescription))
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
            tag = self.decodeJSON(landmarks.GetAttribute("PointAddedEventTag"))
            landmarks.RemoveObserver(tag["PointAddedEventTag"])
            logging.debug("adding observers removed!")
        except:
            pass
        try:
            tag = self.decodeJSON(landmarks.GetAttribute("UpdatesLinesEventTag"))
            landmarks.RemoveObserver(tag["UpdatesLinesEventTag"])
            logging.debug("lines observers removed!")
        except:
            pass
        try:
            tag = self.decodeJSON(landmarks.GetAttribute("PointModifiedEventTag"))
            landmarks.RemoveObserver(tag["PointModifiedEventTag"])
            logging.debug("moving observers removed!")
        except:
            pass
        try:
            tag = self.decodeJSON(landmarks.GetAttribute("PointRemovedEventTag"))
            landmarks.RemoveObserver(tag["PointRemovedEventTag"])
            logging.debug("removing observers removed!")
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
        PointAddedEventTag = landmarks.AddObserver(landmarks.PointAddedEvent, self.onPointAddedEvent)
        landmarks.SetAttribute("PointAddedEventTag",self.encodeJSON({"PointAddedEventTag":PointAddedEventTag}))
        UpdatesLinesEventTag = landmarks.AddObserver(landmarks.PointModifiedEvent, self.updateLinesEvent)
        landmarks.SetAttribute("UpdatesLinesEventTag",self.encodeJSON({"UpdatesLinesEventTag":UpdatesLinesEventTag}))
        PointModifiedEventTag = landmarks.AddObserver(landmarks.PointModifiedEvent, self.onPointModifiedEvent)
        landmarks.SetAttribute("PointModifiedEventTag",self.encodeJSON({"PointModifiedEventTag":PointModifiedEventTag}))
        PointRemovedEventTag = landmarks.AddObserver(landmarks.PointRemovedEvent, self.onPointRemovedEvent)
        landmarks.SetAttribute("PointRemovedEventTag",self.encodeJSON({"PointRemovedEventTag":PointRemovedEventTag}))

    # Called when a landmark is added on a model
    def onPointAddedEvent(self, obj, event):
        logging.debug("markup adding")

        if self.enable_legend_labels:
            try:
                # Find the index of the last-placed landmark and get the landmark label at that position.
                # Ex. if the last-placed landmark was at the 3rd position, we want to use the 3rd landmark label.
                n = obj.GetNumberOfMarkups()
                label, description = self.current_suggested_landmarks[n - 1]
                obj.SetNthMarkupLabel(n - 1, label)
            except IndexError:
                # If there are more landmarks than suggested labels then fetching the label would fail.
                logging.error('Not changing label; wrong number of markups.')

        landmarkDescription = self.decodeJSON(obj.GetAttribute("landmarkDescription"))
        numOfMarkups = obj.GetNumberOfMarkups()
        markupID = obj.GetNthMarkupID(numOfMarkups - 1)
        landmarkDescription[markupID] = dict()
        landmarkLabel = obj.GetNthMarkupLabel(numOfMarkups - 1)
        landmarkDescription[markupID]["landmarkLabel"] = landmarkLabel
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
        self.UpdateInterface()
        qt.QTimer.singleShot(0, lambda : self.onPointModifiedEvent(obj,None))

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
                index = fidList.GetNthControlPointIndexByID(midPointID)
                fidList.SetNthControlPointPositionFromArray(index, coord, fidList.PositionPreview)
                if landmarkDescription[midPointID]["projection"]["isProjected"]:
                    hardenModel = slicer.app.mrmlScene().GetNodeByID(fidList.GetAttribute("hardenModelID"))
                    landmarkDescription[midPointID]["projection"]["closestPointIndex"] = \
                        self.projectOnSurface(hardenModel, fidList, midPointID)
                    fidList.SetAttribute("landmarkDescription",self.encodeJSON(landmarkDescription))
                self.updateMidPoint(fidList, midPointID)

    # Called when a landmarks is moved
    def onPointModifiedEvent(self, obj, event):
        logging.debug("onPointModifiedEvent Q3DC")
        landmarkDescription = self.decodeJSON(obj.GetAttribute("landmarkDescription"))
        if not landmarkDescription:
            return
        selectedLandmarkID = self.findIDFromLabel(obj, self.interface.landmarkComboBox.currentText)
        # remove observer to make sure, the callback function won't work..
        tag = self.decodeJSON(obj.GetAttribute("PointModifiedEventTag"))
        obj.RemoveObserver(tag["PointModifiedEventTag"])
        if selectedLandmarkID:
            activeLandmarkState = landmarkDescription[selectedLandmarkID]
            logging.debug('activeLandmarkState: %s', activeLandmarkState)
            if activeLandmarkState["projection"]["isProjected"]:
                hardenModel = slicer.app.mrmlScene().GetNodeByID(obj.GetAttribute("hardenModelID"))
                activeLandmarkState["projection"]["closestPointIndex"] = \
                    self.projectOnSurface(hardenModel, obj, selectedLandmarkID)
                obj.SetAttribute("landmarkDescription",self.encodeJSON(landmarkDescription))
            self.updateMidPoint(obj,selectedLandmarkID)
        time.sleep(0.08)
        # Add the observer again
        PointModifiedEventTag = obj.AddObserver(obj.PointModifiedEvent, self.onPointModifiedEvent)
        obj.SetAttribute("PointModifiedEventTag",self.encodeJSON({"PointModifiedEventTag":PointModifiedEventTag}))

    def onPointRemovedEvent(self, obj, event):
        logging.debug("markup deleting")

        # ensure that onPointModified won't be called
        tag = self.decodeJSON(obj.GetAttribute("PointModifiedEventTag"))
        logging.info('Modified %r', tag)
        obj.RemoveObserver(tag["PointModifiedEventTag"])

        landmarkDescription = self.decodeJSON(obj.GetAttribute("landmarkDescription"))
        IDs = []
        for ID, value in landmarkDescription.items():
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
        for key,value in self.comboboxdict.items():
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
        for key,value in self.comboboxdict.items():
            if value is fidList:
                key.removeItem(key.findText(label))

    @staticmethod
    def findIDFromLabel(fidList, landmarkLabel):
        # find the ID of the markupsNode from the label of a landmark!
        for i in range(fidList.GetNumberOfFiducials()):
            if landmarkLabel == fidList.GetNthFiducialLabel(i):
                return fidList.GetNthMarkupID(i)
        return None

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

    def replaceLandmark(self, inputModelPolyData, fidNode, landmarkID, indexClosestPoint):
        landmarkCoord = [-1, -1, -1]
        inputModelPolyData.GetPoints().GetPoint(indexClosestPoint, landmarkCoord)
        logging.debug('ReplaceLandmark Coord: %s', landmarkCoord)
        fidNode.SetNthControlPointPositionFromArray(landmarkID, landmarkCoord, fidNode.PositionPreview)

    def projectOnSurface(self, modelOnProject, fidNode, selectedFidReflID):
        if selectedFidReflID:
            markupsIndex = fidNode.GetNthControlPointIndexByID(selectedFidReflID)
            indexClosestPoint = self.getClosestPointIndex(fidNode, modelOnProject.GetPolyData(), markupsIndex)
            self.replaceLandmark(modelOnProject.GetPolyData(), fidNode, markupsIndex, indexClosestPoint)
            return indexClosestPoint

    def calculateMidPointCoord(self, fidList, landmark1ID, landmark2ID):
        """Set the midpoint when you know the the mrml nodes"""
        landmark1Index = fidList.GetNthControlPointIndexByID(landmark1ID)
        landmark2Index = fidList.GetNthControlPointIndexByID(landmark2ID)
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

    def round(self, value):
        return round(value, self.numberOfDecimals)

    def computeDistance(self, point1, point2):
        delta = point2 - point1
        norm = np.linalg.norm(delta)

        result = [*delta, norm]
        return [self.round(value) for value in result]

    def computeAngle(self, line1, line2, axis):
        """
        line1: np.array of the first line
        line2: np.array of the second line

        axis: project the lines onto the plane defined by this axis.
        ex. axis=3 (z) would project lines to the 0-1 (x-y) plane
        """

        # create a mask which removes the coordinate on axis. this performs the projection
        mask = [True] * 3
        mask[axis] = False
        line1 = line1[mask]
        line2 = line2[mask]

        norm1 = np.linalg.norm(line1)
        norm2 = np.linalg.norm(line2)

        if norm1 == 0 or norm2 == 0:
            slicer.util.errorDisplay("ERROR, norm of your vector is 0! DEFINE A VECTOR!")
            return None

        try:
            # find the _signed_ angle using the determinant of a 2x2 matrix
            # https://en.wikipedia.org/wiki/Determinant#2_%C3%97_2_matrices
            # |A| = |u||v|sin(t) where u, v are columns of A and t is the angle between them

            matrix = np.array([line1, line2])
            det = np.linalg.det(matrix)
            radians = np.arcsin(det / norm1 / norm2)
            return np.degrees(radians)
        except np.linalg.LinAlgError:
            slicer.util.errorDisplay('ERROR: failed to project vectors. Only able to compute angles in one plane.')

    def computeAngles(self, line1, line2, states):
        axes = [
            2,  # axis=S; axial; for yaw
            0,  # axis=R; saggital; for pitch
            1,  # axis=A; coronal; for roll
        ]

        result = []
        for axis, state in zip(axes, states):
            if state:
                value = self.computeAngle(line1, line2, axis)
                value = self.round(value)

                # we want to show the angle and the complementary angle, signed
                sign = np.sign(value)
                complement = sign * (180 - abs(value))
                formatted = f'{value} / {complement}'

                result.append(formatted)
            else:
                result.append(None)

        return result

    def computeLinePoint(self, lineA, lineB, point):
        if np.allclose(lineA, lineB, atol=self.tolerance):
            # if lineA and lineB overlap, then just compute the distance to that overlapping point
            delta = point - lineA
            norm = np.linalg.norm(delta)

        else:
            # make vectors relative to lineB
            line = lineA - lineB
            offset = point - lineB

            # project relative point onto line
            proj = np.dot(line, offset) / np.dot(line, line) * line

            # get distance from relative point to projection
            delta = offset - proj
            norm = np.linalg.norm(delta)

        result = [*delta, norm]
        return [self.round(value) for value in result]

    def getDistanceArgs(self,
                        fidListA, fidListB,
                        fidLabelA, fidLabelB):
        """ returns: key, (point1, point2) """
        fidIDA = self.findIDFromLabel(fidListA, fidLabelA)
        fidIDB = self.findIDFromLabel(fidListB, fidLabelB)

        fidIndexA = fidListA.GetNthControlPointIndexByID(fidIDA)
        fidIndexB = fidListB.GetNthControlPointIndexByID(fidIDB)

        point1 = np.array(fidListA.GetMarkupPointVector(fidIndexA, 0))
        point2 = np.array(fidListA.GetMarkupPointVector(fidIndexB, 0))

        args = point1, point2

        key = f'{fidLabelA} - {fidLabelB}'

        return key, args

    def getAnglesArgs(self,
                      fidlist1A, fidlist1B, fidlist2A, fidlist2B,
                      fidLabel1A, fidLabel1B, fidLabel2A, fidLabel2B,
                      yawState, pitchState, rollState
                      ):
        """ returns: key, (line1, line2, states) """
        fidID1A = self.findIDFromLabel(fidlist1A, fidLabel1A)
        fidID1B = self.findIDFromLabel(fidlist1B, fidLabel1B)
        fidID2A = self.findIDFromLabel(fidlist2A, fidLabel2A)
        fidID2B = self.findIDFromLabel(fidlist2B, fidLabel2B)

        landmark1Index = fidlist1A.GetNthControlPointIndexByID(fidID1A)
        landmark2Index = fidlist1B.GetNthControlPointIndexByID(fidID1B)
        landmark3Index = fidlist2A.GetNthControlPointIndexByID(fidID2A)
        landmark4Index = fidlist2B.GetNthControlPointIndexByID(fidID2B)

        coord1 = np.array(fidlist1A.GetMarkupPointVector(landmark1Index, 0))
        coord2 = np.array(fidlist1B.GetMarkupPointVector(landmark2Index, 0))
        coord3 = np.array(fidlist2A.GetMarkupPointVector(landmark3Index, 0))
        coord4 = np.array(fidlist2B.GetMarkupPointVector(landmark4Index, 0))

        line1 = coord2 - coord1
        line2 = coord4 - coord3

        states = (
            yawState,
            pitchState,
            rollState,
        )

        args = line1, line2, states

        key = f'{fidLabel1A}-{fidLabel1B} / {fidLabel2A}-{fidLabel2B}'

        return key, args

    def getLinePointArgs(self,
                         fidListLineA, fidListLineB, fidListPoint,
                         fidLabelLineA, fidLabelLineB, fidLabelPoint):
        fidIDLineA = self.findIDFromLabel(fidListLineA, fidLabelLineA)
        fidIDLineB = self.findIDFromLabel(fidListLineB, fidLabelLineB)
        fidIDPoint = self.findIDFromLabel(fidListPoint, fidLabelPoint)

        landmarkLineAIndex = fidListLineA.GetNthControlPointIndexByID(fidIDLineA)
        landmarkLineBIndex = fidListLineB.GetNthControlPointIndexByID(fidIDLineB)
        landmarkPointIndex = fidListPoint.GetNthControlPointIndexByID(fidIDPoint)

        lineA = np.array(fidListLineA.GetMarkupPointVector(landmarkLineAIndex, 0))
        lineB = np.array(fidListLineB.GetMarkupPointVector(landmarkLineBIndex, 0))
        point = np.array(fidListPoint.GetMarkupPointVector(landmarkPointIndex, 0))

        args = lineA, lineB, point

        key = f'{fidLabelLineA}-{fidLabelLineB} / {fidLabelPoint}'

        return key, args

    @classmethod
    def createTable(cls, col_names):
        table = slicer.vtkMRMLTableNode()
        table.SetSaveWithScene(False)
        table.SetLocked(True)

        col_names = ['  '] + [f' {name} ' for name in col_names]

        with NodeModify(table):
            table.RemoveAllColumns()
            for col_name in col_names:
                table.AddColumn().SetName(col_name)
                table.SetUseColumnNameAsColumnHeader(True)

        return table

    @classmethod
    def createDistanceTable(cls):
        names = 'R-L Component', 'A-P Component', 'S-I Component', '3D Distance'
        return cls.createTable(names)

    @classmethod
    def createAnglesTable(cls):
        names = 'YAW', 'PITCH', 'ROLL'
        return cls.createTable(names)

    @classmethod
    def createLinePointTable(cls):
        names = 'R-L Component', 'A-P Component', 'S-I Component', '3D Distance'
        return cls.createTable(names)

    def updateTable(self, table, key, data):
        empty = ' - '  # text to use if data is not present

        with NodeModify(table):
            for row in range(table.GetNumberOfRows()):
                if table.GetCellText(row, 0) == key:
                    break
            else:
                row = table.AddEmptyRow()
                table.SetCellText(row, 0, key)

            for col, value in enumerate(data, start=1):
                if value is None:
                    text = empty
                else:
                    text = str(value)
                table.SetCellText(row, col, text or empty)

    @classmethod
    def updateTableView(cls, table, table_view):
        table_view.resizeColumnsToContents()
        table_view.setMinimumHeight(50 * table.GetNumberOfRows())

    def drawLineBetween2Landmark(self, landmark1label, landmark2label, fidList1, fidList2):
        if not fidList1 or not fidList2 or not landmark1label or not landmark2label:
            return
        landmark1ID = self.findIDFromLabel(fidList1, landmark1label)
        landmark2ID = self.findIDFromLabel(fidList2, landmark2label)

        if not fidList1 or not fidList2:
            return None, None
        landmark1Index = fidList1.GetNthControlPointIndexByID(landmark1ID)
        landmark2Index = fidList2.GetNthControlPointIndexByID(landmark2ID)

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

    def exportationFunction(self, directoryExport, filenameExport, tableToExport, typeCalculation):
        messageBox = ctk.ctkMessageBox()
        messageBox.setWindowTitle(' /!\ WARNING /!\ ')
        messageBox.setIcon(messageBox.Warning)

        fileName = os.path.join(directoryExport.directory, filenameExport.text)
        if os.path.exists(fileName):
            messageBox.setText('File ' + fileName + ' already exists!')
            messageBox.setInformativeText('Do you want to replace it ?')
            messageBox.setStandardButtons( messageBox.No | messageBox.Yes)
            choice = messageBox.exec_()
            if choice == messageBox.No:
                return

        slicer.util.saveNode(tableToExport, fileName)
        slicer.util.delayDisplay(f'Saved to {fileName}')

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
            return json.loads(input)
        return None

    def UpdateLandmarkComboboxA(self, fidListCombobox, landmarkCombobox):
        self.comboboxdict[landmarkCombobox] = fidListCombobox.currentNode()
        self.updateLandmarkComboBox(fidListCombobox.currentNode(), landmarkCombobox)
        self.UpdateInterface()


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

        try:
            self.delayDisplay(' Test Calculate Distance')
            self.test_CalculateDistance()

            self.delayDisplay(' Test Calculate Angles')
            self.test_CalculateAngles()

            self.delayDisplay(' Test Calculate Line Point')
            self.test_CalculateLinePoint()

            self.delayDisplay(' Test Tutorial Simulation')
            self.test_SimulateTutorial()
        except AssertionError:
            self.delayDisplay(' Test Failed')
            return

        self.delayDisplay(' Tests Passed')

    def test_CalculateDistance(self):
        logic = Q3DCLogic(slicer.modules.Q3DCWidget)
        markupsNode1 = slicer.vtkMRMLMarkupsFiducialNode()
        markupsNode1.AddFiducial(-5.331, 51.955, 4.831)
        markupsNode1.AddFiducial(-8.018, 41.429, -52.621)

        key, args = logic.getDistanceArgs(
            markupsNode1, markupsNode1,
            markupsNode1.GetNthControlPointLabel(0),
            markupsNode1.GetNthControlPointLabel(1)
        )

        dx, dy, dz, dist = logic.computeDistance(*args)
        assert (dx, dy, dz, dist) == (-2.687, -10.526, -57.452, 58.47)

    def test_CalculateAngles(self):
        logic = Q3DCLogic(slicer.modules.Q3DCWidget)
        markupsNode1 = slicer.vtkMRMLMarkupsFiducialNode()

        markupsNode1.AddFiducial(63.90, -46.98, 6.98)
        markupsNode1.AddFiducial(43.79, -60.16, 12.16)
        markupsNode1.AddFiducial(62.21, -45.31, 7.41)
        markupsNode1.AddFiducial(41.97, -61.24, 11.30)

        key, args = logic.getAnglesArgs(
            markupsNode1, markupsNode1, markupsNode1, markupsNode1,
            markupsNode1.GetNthControlPointLabel(0),
            markupsNode1.GetNthControlPointLabel(1),
            markupsNode1.GetNthControlPointLabel(2),
            markupsNode1.GetNthControlPointLabel(3),
            True, False, True
        )

        yaw, pitch, roll = logic.computeAngles(*args)

        assert yaw == '4.964 / 175.036'
        assert pitch is None
        assert roll == '3.565 / 176.435'

        markupsNode1.AddFiducial(53.80,-53.57,9.47)
        markupsNode1.AddFiducial(53.98,-52.13,9.13)
        markupsNode1.AddFiducial(52.09,-53.27,9.36)
        markupsNode1.AddFiducial(51.77,-50.10,9.80)

        key, args = logic.getAnglesArgs(
            markupsNode1,markupsNode1,markupsNode1,markupsNode1,
            markupsNode1.GetNthControlPointLabel(4),
            markupsNode1.GetNthControlPointLabel(5),
            markupsNode1.GetNthControlPointLabel(6),
            markupsNode1.GetNthControlPointLabel(7),
            False, True, False
        )

        yaw, pitch, roll = logic.computeAngles(*args)

        assert yaw is None
        assert pitch == '21.187 / 158.813'
        assert roll is None

    def test_CalculateLinePoint(self):
        logic = Q3DCLogic(slicer.modules.Q3DCWidget)

        markups = slicer.vtkMRMLMarkupsFiducialNode()

        # simple geometric case
        markups.RemoveAllMarkups()
        markups.AddFiducial(0, 1, -1)
        markups.AddFiducial(0, -1, 1)
        markups.AddFiducial(-1, 0, 0)

        key, args = logic.getLinePointArgs(
            markups, markups, markups,
            markups.GetNthControlPointLabel(0),
            markups.GetNthControlPointLabel(1),
            markups.GetNthControlPointLabel(2),
        )

        dx, dy, dz, norm = logic.computeLinePoint(*args)
        print(dx, dy, dz, norm)
        assert (dx, dy, dz, norm) == (-1, 0, 0, 1)

        # simple geometric case where solution is outside the line segment
        markups.RemoveAllMarkups()
        markups.AddFiducial(0, 0, 1)
        markups.AddFiducial(0, 1, 1)
        markups.AddFiducial(0, -1, 0)

        key, args = logic.getLinePointArgs(
            markups, markups, markups,
            markups.GetNthControlPointLabel(0),
            markups.GetNthControlPointLabel(1),
            markups.GetNthControlPointLabel(2),
        )

        dx, dy, dz, norm = logic.computeLinePoint(*args)
        print(dx, dy, dz, norm)
        assert (dx, dy, dz, norm) == (0, 0, -1, 1)

        # Random values; Answer is validated with Wolfram
        markups.RemoveAllMarkups()
        markups.AddFiducial(12.93, 13.17, 8.26)
        markups.AddFiducial(14.45, 11.94, 9.36)
        markups.AddFiducial(16.67, 6.96, 4.87)

        key, args = logic.getLinePointArgs(
            markups, markups, markups,
            markups.GetNthControlPointLabel(0),
            markups.GetNthControlPointLabel(1),
            markups.GetNthControlPointLabel(2),
        )

        dx, dy, dz, norm = logic.computeLinePoint(*args)
        print(dx, dy, dz, norm)
        assert (dx, dy, dz, norm) == (0.843, -3.865, -5.487, 6.764)

        # Degenerate case, when lineA and lineB are the same.
        # computeLinePoint should instead just compute distance to the overlapping point
        markups.RemoveAllMarkups()
        markups.AddFiducial(1, 0, 0)
        markups.AddFiducial(1, 0, 0)
        markups.AddFiducial(0, 0, 0)

        key, args = logic.getLinePointArgs(
            markups, markups, markups,
            markups.GetNthControlPointLabel(0),
            markups.GetNthControlPointLabel(1),
            markups.GetNthControlPointLabel(2),
        )

        dx, dy, dz, norm = logic.computeLinePoint(*args)
        print(dx, dy, dz, norm)
        assert (dx, dy, dz, norm) == (-1, 0, 0, 1)

    def test_SimulateTutorial(self):
        #
        # first, get the data - a zip file of example data
        #
        import urllib.request
        downloads = (
            ('http://slicer.kitware.com/midas3/download/item/211921/Q3DCExtensionTestData.zip', 'Q3DCExtensionTestData.zip'),
            )

        self.delayDisplay("Downloading")
        for url,name in downloads:
          filePath = slicer.app.temporaryPath + '/' + name
          if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
            self.delayDisplay('Requesting download %s from %s...\n' % (name, url))
            urllib.request.urlretrieve(url, filePath)
        self.delayDisplay('Finished with download\n')

        self.delayDisplay("Unzipping")
        q3dcFilesDirectory = slicer.app.temporaryPath + '/q3dcFiles'
        qt.QDir().mkpath(q3dcFilesDirectory)
        slicer.app.applicationLogic().Unzip(filePath, q3dcFilesDirectory)

        modelNodes = {}
        mandibleFiles = ("AH1m.vtk", "AH2m.vtk")
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
            logging.error("Did not define a midpoint node")
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
        midpointMarkupIndex = movingMarkupsFiducial.GetNthControlPointIndexByID(midpointMarkupID)
        initialPosition = [0,]*3
        movingMarkupsFiducial.GetNthFiducialPosition(midpointMarkupIndex, initialPosition)
        movingMarkupsFiducial.SetNthFiducialPosition(0, 45, 20, -15)
        movedPosition = [0,]*3
        movingMarkupsFiducial.GetNthFiducialPosition(midpointMarkupIndex, movedPosition)
        if initialPosition == movedPosition:
            logging.info('midpoint landmark did not move')
            return False

        return True
