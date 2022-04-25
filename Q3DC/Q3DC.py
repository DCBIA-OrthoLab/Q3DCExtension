import csv
from collections import defaultdict
import json
import logging
import os

import ctk
import numpy as np
import qt
import vtk

import DependantMarkups
import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModule
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleWidget
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleTest
from slicer.util import VTKObservationMixin
from slicer.util import NodeModify


class Q3DC(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Q3DC "
        parent.categories = ["Quantification"]
        parent.dependencies = ["DependantMarkups"]
        parent.contributors = [
            "Lucie Macron (University of Michigan)",
            "Jean-Baptiste VIMORT (University of Michigan)",
            "James Hoctor (Kitware Inc)",
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


class Q3DCWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)

    def setup(self):
        logging.debug("Q3DC Widget Setup")
        ScriptedLoadableModuleWidget.setup(self)
        # GLOBALS:
        self.interactionNode = slicer.mrmlScene.GetNodeByID(
            "vtkMRMLInteractionNodeSingleton"
        )
        self.computedAnglesList = list()
        self.renderer1 = None
        self.actor1 = None
        self.renderer2 = None
        self.actor2 = None
        self.renderer3 = None
        self.actor3 = None

        # Load widget from .ui file (created by Qt Designer)
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/Q3DC.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        self.logic = Q3DCLogic(self.ui)
        self.deps = DependantMarkups.DependantMarkupsLogic()

        # -------------------------- Scene ---------------------------
        self.SceneCollapsibleButton = (
            self.ui.SceneCollapsibleButton
        )  # this attribute is usefull for Longitudinal quantification extension
        treeView = self.ui.treeView
        treeView.setMRMLScene(slicer.app.mrmlScene())
        treeView.sceneModel().setHorizontalHeaderLabels(["Models"])
        treeView.sortFilterProxyModel().nodeTypes = [
            "vtkMRMLModelNode",
            "vtkMRMLMarkupsFiducialNode",
        ]
        treeView.header().setVisible(False)

        # ------------------ Landmark Modification -------------------
        self.inputModelLabel = (
            self.ui.inputModelLabel
        )  # this attribute is usefull for Longitudinal quantification extension
        self.inputLandmarksLabel = (
            self.ui.inputLandmarksLabel
        )  # this attribute is usefull for Longitudinal quantification extension
        self.ui.inputModelSelector.setMRMLScene(slicer.mrmlScene)
        self.ui.inputModelSelector.connect(
            "currentNodeChanged(vtkMRMLNode*)", self.onModelChanged
        )
        self.ui.addLandmarkButton.connect("clicked()", self.onAddLandmarkButtonClicked)
        self.ui.inputLandmarksSelector.setMRMLScene(slicer.mrmlScene)
        self.ui.inputLandmarksSelector.setEnabled(
            False
        )  # The "enable" property seems to not be imported from the .ui
        self.ui.inputLandmarksSelector.connect(
            "currentNodeChanged(vtkMRMLNode*)", self.onLandmarksChanged
        )
        self.ui.landmarkComboBox.connect(
            "currentIndexChanged(QString)", self.UpdateInterface
        )
        self.ui.surfaceDeplacementCheckBox.connect(
            "stateChanged(int)", self.onSurfaceDeplacementStateChanged
        )
        self.ui.loadLandmarksOnSurfaceCheckBox.connect(
            "stateChanged(int)", self.onLoadLandmarksOnSurfaceStateChanged
        )

        # --------------------- Anatomical Legend --------------------
        self.suggested_landmarks = self.logic.load_suggested_landmarks(
            self.resourcePath("Data/base_fiducial_legend.csv")
        )
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
        self.anatomical_legend_view.connect(
            "selectionChanged()", self.on_legend_row_selected
        )

        self.init_anatomical_radio_buttons()

        self.ui.legendFileButton.connect(
            "clicked()", self.on_select_legend_file_clicked
        )

        # -------------------- Compute Mid Point ---------------------
        self.ui.landmarkComboBox1.connect(
            "currentIndexChanged(int)", self.UpdateInterface
        )
        self.ui.landmarkComboBox2.connect(
            "currentIndexChanged(int)", self.UpdateInterface
        )
        self.ui.defineMiddlePointButton.connect(
            "clicked()", self.onDefineMidPointClicked
        )

        # ------------------- Calculate Distances --------------------
        self.ui.fidListComboBoxA.setMRMLScene(slicer.mrmlScene)
        self.ui.fidListComboBoxB.setMRMLScene(slicer.mrmlScene)
        self.ui.computeDistancesPushButton.connect(
            "clicked()", self.onComputeDistanceClicked
        )
        self.ui.landmarkComboBoxA.connect(
            "currentIndexChanged(int)", self.UpdateInterface
        )
        self.ui.landmarkComboBoxB.connect(
            "currentIndexChanged(int)", self.UpdateInterface
        )
        self.ui.fidListComboBoxA.connect(
            "currentNodeChanged(vtkMRMLNode*)",
            lambda: self.deps.updateLandmarkComboBox(
                self.ui.fidListComboBoxA.currentNode(),
                self.ui.landmarkComboBoxA,
            ),
        )
        self.ui.fidListComboBoxB.connect(
            "currentNodeChanged(vtkMRMLNode*)",
            lambda: self.deps.updateLandmarkComboBox(
                self.ui.fidListComboBoxB.currentNode(),
                self.ui.landmarkComboBoxB,
            ),
        )
        # ---------------------- Save Distances ----------------------
        self.distance_table = self.logic.createDistanceTable()
        slicer.mrmlScene.AddNode(self.distance_table)
        self.distance_table_view = slicer.qMRMLTableView()
        self.distance_table_view.setMRMLTableNode(self.distance_table)
        self.directoryExportDistance = ctk.ctkDirectoryButton()
        self.filenameExportDistance = qt.QLineEdit("distance.csv")
        self.exportDistanceButton = qt.QPushButton(" Export ")
        self.exportDistanceButton.connect("clicked()", self.onExportButton)
        self.exportDistanceButton.enabled = True
        self.deleteDistanceRowButton = qt.QPushButton("Delete Selected Row")
        self.deleteDistanceRowButton.connect(
            "clicked()", self.distance_table_view.deleteRow
        )
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
        self.ui.fidListComboBoxline1LA.connect(
            "currentNodeChanged(vtkMRMLNode*)",
            lambda: self.deps.updateLandmarkComboBox(
                self.ui.fidListComboBoxline1LA.currentNode(),
                self.ui.line1LAComboBox,
            ),
        )
        self.ui.fidListComboBoxline1LB.connect(
            "currentNodeChanged(vtkMRMLNode*)",
            lambda: self.deps.updateLandmarkComboBox(
                self.ui.fidListComboBoxline1LB.currentNode(),
                self.ui.line1LBComboBox,
            ),
        )
        self.ui.fidListComboBoxline2LA.connect(
            "currentNodeChanged(vtkMRMLNode*)",
            lambda: self.deps.updateLandmarkComboBox(
                self.ui.fidListComboBoxline2LA.currentNode(),
                self.ui.line2LAComboBox,
            ),
        )
        self.ui.fidListComboBoxline2LB.connect(
            "currentNodeChanged(vtkMRMLNode*)",
            lambda: self.deps.updateLandmarkComboBox(
                self.ui.fidListComboBoxline2LB.currentNode(),
                self.ui.line2LBComboBox,
            ),
        )
        self.ui.computeAnglesPushButton.connect(
            "clicked()", self.onComputeAnglesClicked
        )
        self.ui.line1LAComboBox.connect(
            "currentIndexChanged(int)", self.UpdateInterface
        )
        self.ui.line1LBComboBox.connect(
            "currentIndexChanged(int)", self.UpdateInterface
        )
        self.ui.line2LAComboBox.connect(
            "currentIndexChanged(int)", self.UpdateInterface
        )
        self.ui.line2LBComboBox.connect(
            "currentIndexChanged(int)", self.UpdateInterface
        )
        self.ui.pitchCheckBox.connect("clicked(bool)", self.UpdateInterface)
        self.ui.rollCheckBox.connect("clicked(bool)", self.UpdateInterface)
        self.ui.yawCheckBox.connect("clicked(bool)", self.UpdateInterface)
        # ----------------------- Save Angles ------------------------
        self.angles_table = self.logic.createAnglesTable()
        slicer.mrmlScene.AddNode(self.angles_table)
        self.angles_table_view = slicer.qMRMLTableView()
        self.angles_table_view.setMRMLTableNode(self.angles_table)
        self.directoryExportAngle = ctk.ctkDirectoryButton()
        self.filenameExportAngle = qt.QLineEdit("angle.csv")
        self.exportAngleButton = qt.QPushButton("Export")
        self.exportAngleButton.connect("clicked()", self.onExportAngleButton)
        self.exportAngleButton.enabled = True
        self.deleteAngleRowButton = qt.QPushButton("Delete Selected Row")
        self.deleteAngleRowButton.connect("clicked()", self.angles_table_view.deleteRow)
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
        self.ui.fidListComboBoxlineLA.connect(
            "currentNodeChanged(vtkMRMLNode*)",
            lambda: self.deps.updateLandmarkComboBox(
                self.ui.fidListComboBoxlineLA.currentNode(), self.ui.lineLAComboBox
            ),
        )
        self.ui.fidListComboBoxlineLB.connect(
            "currentNodeChanged(vtkMRMLNode*)",
            lambda: self.deps.updateLandmarkComboBox(
                self.ui.fidListComboBoxlineLB.currentNode(), self.ui.lineLBComboBox
            ),
        )
        self.ui.fidListComboBoxlinePoint.connect(
            "currentNodeChanged(vtkMRMLNode*)",
            lambda: self.deps.updateLandmarkComboBox(
                self.ui.fidListComboBoxlinePoint.currentNode(), self.ui.linePointComboBox
            ),
        )
        self.ui.computeLinePointPushButton.connect(
            "clicked()", self.onComputeLinePointClicked
        )
        self.ui.lineLAComboBox.connect("currentIndexChanged(int)", self.UpdateInterface)
        self.ui.lineLBComboBox.connect("currentIndexChanged(int)", self.UpdateInterface)
        # ---------------- Save Line-Point Distances -----------------
        self.line_point_table = self.logic.createLinePointTable()
        slicer.mrmlScene.AddNode(self.line_point_table)
        self.line_point_table_view = slicer.qMRMLTableView()
        self.line_point_table_view.setMRMLTableNode(self.line_point_table)
        self.directoryExportLinePoint = ctk.ctkDirectoryButton()
        self.filenameExportLinePoint = qt.QLineEdit("linePoint.csv")
        self.exportLinePointButton = qt.QPushButton("Export")
        self.exportLinePointButton.connect("clicked()", self.onExportLinePointButton)
        self.exportLinePointButton.enabled = True
        self.deleteLinePointRowButton = qt.QPushButton("Delete Selected Row")
        self.deleteLinePointRowButton.connect(
            "clicked()", self.line_point_table_view.deleteRow
        )
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

    def onCloseScene(self, obj, event):
        list = slicer.mrmlScene.GetNodesByClass("vtkMRMLModelNode")
        end = list.GetNumberOfItems()
        for i in range(0, end):
            model = list.GetItemAsObject(i)
            hardenModel = slicer.mrmlScene.GetNodesByName(
                model.GetName()
            ).GetItemAsObject(0)
            slicer.mrmlScene.RemoveNode(hardenModel)
        if self.renderer1:
            self.renderer1.RemoveActor(self.actor1)
        if self.renderer2:
            self.renderer2.RemoveActor(self.actor2)
        if self.renderer3:
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

    def UpdateInterface(self):
        self.ui.defineMiddlePointButton.enabled = (
            self.ui.landmarkComboBox1.currentData != ""
            and self.ui.landmarkComboBox2.currentData != ""
            and self.ui.landmarkComboBox1.currentData
            != self.ui.landmarkComboBox2.currentData
        )
        self.ui.computeDistancesPushButton.enabled = (
            self.ui.landmarkComboBoxA.currentData != ""
            and self.ui.landmarkComboBoxB.currentData != ""
            and (
                self.ui.fidListComboBoxA.currentNodeID,
                self.ui.landmarkComboBoxA.currentData,
            )
            != (
                self.ui.fidListComboBoxB.currentNodeID,
                self.ui.landmarkComboBoxB.currentData,
            )
        )
        self.ui.computeAnglesPushButton.enabled = (
            self.ui.line1LAComboBox.currentData != ""
            and self.ui.line1LBComboBox.currentData != ""
            and self.ui.line2LAComboBox.currentData != ""
            and self.ui.line2LBComboBox.currentData != ""
            and (
                self.ui.fidListComboBoxline1LA.currentNodeID,
                self.ui.line1LAComboBox.currentData,
            )
            != (
                self.ui.fidListComboBoxline1LB.currentNodeID,
                self.ui.line1LBComboBox.currentData,
            )
            and (
                self.ui.fidListComboBoxline2LA.currentNodeID,
                self.ui.line2LAComboBox.currentData,
            )
            != (
                self.ui.fidListComboBoxline2LB.currentNodeID,
                self.ui.line2LBComboBox.currentData,
            )
            and (
                self.ui.pitchCheckBox.isChecked()
                or self.ui.rollCheckBox.isChecked()
                or self.ui.yawCheckBox.isChecked()
            )
        )
        self.ui.computeLinePointPushButton.enabled = (
            self.ui.lineLAComboBox.currentData != ""
            and self.ui.lineLBComboBox.currentData != ""
            and self.ui.linePointComboBox.currentData != ""
            and (
                self.ui.fidListComboBoxlineLA.currentNodeID,
                self.ui.lineLAComboBox.currentData,
            )
            != (
                self.ui.fidListComboBoxlineLB.currentNodeID,
                self.ui.lineLBComboBox.currentData,
            )
        )

        # Clear Lines:
        if self.renderer1:
            self.renderer1.RemoveActor(self.actor1)
            self.renderer1 = None
        if self.renderer2:
            self.renderer2.RemoveActor(self.actor2)
            self.renderer2 = None
        if self.renderer3:
            self.renderer3.RemoveActor(self.actor3)
            self.renderer3 = None
        if (
            self.ui.line1LAComboBox.currentData != ""
            and self.ui.line1LBComboBox.currentData != ""
            and self.ui.line1LAComboBox.currentData
            != self.ui.line1LBComboBox.currentData
        ):
            self.renderer1, self.actor1 = self.logic.drawLineBetween2Landmark(
                self.ui.line1LAComboBox.currentData,
                self.ui.line1LBComboBox.currentData,
                self.ui.fidListComboBoxline1LA.currentNode(),
                self.ui.fidListComboBoxline1LB.currentNode(),
            )
        if (
            self.ui.line2LAComboBox.currentData != ""
            and self.ui.line2LBComboBox.currentData != ""
            and self.ui.line2LAComboBox.currentData
            != self.ui.line2LBComboBox.currentData
        ):
            self.renderer2, self.actor2 = self.logic.drawLineBetween2Landmark(
                self.ui.line2LAComboBox.currentData,
                self.ui.line2LBComboBox.currentData,
                self.ui.fidListComboBoxline2LA.currentNode(),
                self.ui.fidListComboBoxline2LB.currentNode(),
            )
        if (
            self.ui.lineLAComboBox.currentData != ""
            and self.ui.lineLBComboBox.currentData != ""
            and self.ui.lineLAComboBox.currentData != self.ui.lineLBComboBox.currentData
        ):
            self.renderer3, self.actor3 = self.logic.drawLineBetween2Landmark(
                self.ui.lineLAComboBox.currentData,
                self.ui.lineLBComboBox.currentData,
                self.ui.fidListComboBoxlineLA.currentNode(),
                self.ui.fidListComboBoxlineLB.currentNode(),
            )
        self.logic.UpdateThreeDView(self.ui.landmarkComboBox.currentData)

    def init_anatomical_legend(self):
        if self.anatomical_legend is None:
            for table_node in slicer.mrmlScene.GetNodesByClass("vtkMRMLTableNode"):
                if table_node.GetAttribute("Q3DC.is_anatomical_legend") == "True":
                    self.anatomical_legend = table_node
            if self.anatomical_legend is None:
                self.anatomical_legend = slicer.vtkMRMLTableNode()
                self.anatomical_legend.SetSaveWithScene(False)
                self.anatomical_legend.SetLocked(True)
                slicer.mrmlScene.AddNode(self.anatomical_legend)
                self.anatomical_legend.SetAttribute("Q3DC.is_anatomical_legend", "True")

        al = self.anatomical_legend
        with NodeModify(al):
            al.RemoveAllColumns()
            al.AddColumn().SetName("Landmark")
            al.AddColumn().SetName("Description")
            al.SetUseColumnNameAsColumnHeader(True)

    def init_anatomical_radio_buttons(self):
        self.anatomical_radio_buttons = [
            qt.QRadioButton(region) for region in self.suggested_landmarks.keys()
        ]
        for i in range(self.anatomical_radio_buttons_layout.count() - 1, -1, -1):
            self.anatomical_radio_buttons_layout.itemAt(i).widget().setParent(None)
        for radio_button in self.anatomical_radio_buttons:
            self.anatomical_radio_buttons_layout.addWidget(radio_button)
            radio_button.toggled.connect(
                lambda state,
                       _radio_button=radio_button: self.on_anatomical_radio_button_toggled(
                    state, _radio_button
                )
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
        selectedFidReflID = self.ui.landmarkComboBox.currentData
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
        self.deps.updateLandmarkComboBox(fidList, self.ui.landmarkComboBox, False)
        self.ui.landmarkComboBox.setCurrentText(name)
        for box in (self.ui.landmarkComboBox1, self.ui.landmarkComboBox2):
            new_selection = box.currentText
            if new_selection == old_name:
                new_selection = name
            self.deps.updateLandmarkComboBox(fidList, box)
            box.setCurrentText(new_selection)
        self.UpdateInterface()

    def on_select_legend_file_clicked(self):
        legend_filename = qt.QFileDialog.getOpenFileName(
            None, "Select File", "", "CSV (*.csv)"
        )
        if legend_filename == "":
            # User canceled the file selection dialog.
            return
        suggested_landmarks = self.logic.load_suggested_landmarks(legend_filename)
        if suggested_landmarks is None:
            return
        self.suggested_landmarks = suggested_landmarks
        self.init_anatomical_radio_buttons()

    def onModelChanged(self):
        logging.debug("Model Changed")
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
        self.logic.selectedModel = self.ui.inputModelSelector.currentNode()
        self.ui.inputLandmarksSelector.setCurrentNode(None)

        model = self.ui.inputModelSelector.currentNode()
        if model:
            self.ui.inputLandmarksSelector.setEnabled(True)
        else:
            self.ui.inputLandmarksSelector.setCurrentNode(None)
            self.ui.inputLandmarksSelector.setEnabled(False)

    def onLandmarksChanged(self):
        print("---- Landmarks Changed ----")

        model = self.ui.inputModelSelector.currentNode()
        markups = self.ui.inputLandmarksSelector.currentNode()

        self.logic.FidList = markups
        self.logic.selectedFidList = markups
        self.logic.selectedModel = model

        if markups and model:
            self.deps.connect(markups, model)
            # onSurface = self.ui.loadLandmarksOnSurfaceCheckBox.isChecked()

            self.addObserver(markups, markups.PointAddedEvent, self.onPointAdded)
            self.addObserver(markups, markups.PointModifiedEvent, self.onPointModified)
            self.addObserver(markups, markups.PointRemovedEvent, self.onPointRemoved)

            self.updateAllLandmarkComboBox(markups)
            self.UpdateInterface()
        else:
            self.ui.landmarkComboBox.clear()

    def onPointAdded(self, node, e):
        if self.logic.enable_legend_labels:
            try:
                # todo handle if midpoint, etc are added that don't match landmark names.
                n = node.GetNumberOfMarkups()
                label, descr = self.logic.current_suggested_landmarks[n - 1]
                node.SetNthMarkupLabel(n - 1, label)
            except IndexError:
                logging.error("Not changing label; wrong number of markups.")

        self.updateAllLandmarkComboBox(node)
        self.UpdateInterface()

    def onPointModified(self, node, e):
        pass

    def onPointRemoved(self, node, e):
        self.updateAllLandmarkComboBox(node)
        self.UpdateInterface()

    def updateAllLandmarkComboBox(self, fidList):
        # update of the Combobox that are always updated
        self.deps.updateLandmarkComboBox(fidList, self.ui.landmarkComboBox, False)
        self.deps.updateLandmarkComboBox(fidList, self.ui.landmarkComboBox1)
        self.deps.updateLandmarkComboBox(fidList, self.ui.landmarkComboBox2)

        # update of the Comboboxes that display the fidcial list just modified
        for combobox, node in self.logic.comboboxdict.items():
            self.deps.updateLandmarkComboBox(node, combobox)

    def updateLandmarkCombobox(self, nodeCombobox, landmarkCombobox):
        node = nodeCombobox.currentNode()
        self.logic.comboboxdict[landmarkCombobox] = node
        self.deps.updateLandmarkComboBox(node, landmarkCombobox)
        self.UpdateInterface()

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

    def onLoadLandmarksOnSurfaceStateChanged(self):
        self.logic.projectNewPoints = self.ui.loadLandmarksOnSurfaceCheckBox.isChecked()

    def onSurfaceDeplacementStateChanged(self):
        self.deps.default_projected = self.ui.surfaceDeplacementCheckBox.isChecked()

    def onDefineMidPointClicked(self):
        fidList = self.logic.selectedFidList
        if not fidList:
            self.logic.warningMessage(
                "Please select a model of reference and a fiducial List."
            )

        ID1 = self.ui.landmarkComboBox1.currentData
        ID2 = self.ui.landmarkComboBox2.currentData

        key = "{}_{}".format(
            fidList.GetNthControlPointLabel(fidList.GetNthControlPointIndexByID(ID1)),
            fidList.GetNthControlPointLabel(fidList.GetNthControlPointIndexByID(ID2)),
        )

        ID = fidList.GetNthControlPointID(
            fidList.AddControlPoint(vtk.vtkVector3d(), key)
        )

        isProjected = self.ui.midPointOnSurfaceCheckBox.checked

        self.deps.setProjected(fidList, ID, isProjected)
        self.deps.setMidPoint(fidList, ID, ID1, ID2)

        self.UpdateInterface()
        self.updateAllLandmarkComboBox(fidList)

    def onComputeDistanceClicked(self):
        self.ui.distanceLayout.addLayout(self.tableAndExportLayout)

        listA = self.ui.fidListComboBoxA.currentNode()
        listB = self.ui.fidListComboBoxB.currentNode()

        IDA = self.ui.landmarkComboBoxA.currentData
        IDB = self.ui.landmarkComboBoxB.currentData

        key = '{} - {}'.format(
            self.deps.getNthControlPointLabelByID(listA, IDA),
            self.deps.getNthControlPointLabelByID(listB, IDB),
        )

        pointA = self.deps.getNthControlPointPositionByID(listA, IDA)
        pointB = self.deps.getNthControlPointPositionByID(listB, IDB)

        data = self.deps.computeDistance(pointA, pointB)
        row = [*data.delta, data.norm]
        row = self.deps.roundall(row)

        self.logic.updateTable(self.distance_table, key, row)
        self.logic.updateTableView(self.distance_table, self.distance_table_view)

    def onComputeAnglesClicked(self):
        self.ui.angleLayout.addLayout(self.tableAndExportAngleLayout)

        list1A = self.ui.fidListComboBoxline1LA.currentNode()
        list1B = self.ui.fidListComboBoxline1LB.currentNode()
        list2A = self.ui.fidListComboBoxline2LA.currentNode()
        list2B = self.ui.fidListComboBoxline2LB.currentNode()

        ID1A = self.ui.line1LAComboBox.currentData
        ID1B = self.ui.line1LBComboBox.currentData
        ID2A = self.ui.line2LAComboBox.currentData
        ID2B = self.ui.line2LBComboBox.currentData

        key = '{}-{} / {}-{}'.format(
            self.deps.getNthControlPointLabelByID(list1A, ID1A),
            self.deps.getNthControlPointLabelByID(list1B, ID1B),
            self.deps.getNthControlPointLabelByID(list2A, ID2A),
            self.deps.getNthControlPointLabelByID(list2B, ID2B),
        )

        point1A = self.deps.getNthControlPointPositionByID(list1A, ID1A)
        point1B = self.deps.getNthControlPointPositionByID(list1B, ID1B)
        point2A = self.deps.getNthControlPointPositionByID(list2A, ID2A)
        point2B = self.deps.getNthControlPointPositionByID(list2B, ID2B)

        line1 = point1B - point1A
        line2 = point2B - point2A

        states = [
            self.ui.yawCheckBox.isChecked(),
            self.ui.pitchCheckBox.isChecked(),
            self.ui.rollCheckBox.isChecked(),
        ]

        data = self.deps.computeAngles(line1, line2)

        def fmt(deg):
            sign = np.sin(deg)
            comp = sign * (180 - np.abs(deg))

            deg = self.deps.round(deg)
            comp = self.deps.round(comp)

            return f'{deg} / {comp}'

        row = [
            fmt(deg) if state else ' - '
            for deg, state in zip(data.byaxis, states)
        ]

        self.logic.updateTable(self.angles_table, key, row)

        self.logic.updateTableView(self.angles_table, self.angles_table_view)

    def onComputeLinePointClicked(self):
        self.ui.LinePointLayout.addLayout(self.tableAndExportLinePointLayout)

        listLA = self.ui.fidListComboBoxlineLA.currentNode()
        listLB = self.ui.fidListComboBoxlineLB.currentNode()
        listPoint = self.ui.fidListComboBoxlinePoint.currentNode()

        IDLA = self.ui.lineLAComboBox.currentData
        IDLB = self.ui.lineLBComboBox.currentData
        IDPoint = self.ui.linePointComboBox.currentData

        key = "{}-{} / {}".format(
            self.deps.getNthControlPointLabelByID(listLA, IDLA),
            self.deps.getNthControlPointLabelByID(listLB, IDLB),
            self.deps.getNthControlPointLabelByID(listPoint, IDPoint),
        )

        lineA = self.deps.getNthControlPointPositionByID(listLA, IDLA)
        lineB = self.deps.getNthControlPointPositionByID(listLB, IDLB)
        point = self.deps.getNthControlPointPositionByID(listPoint, IDPoint)

        data = self.deps.computeLinePoint(lineA, lineB, point)
        row = [*data.delta, data.norm]
        row = self.deps.roundall(row)

        self.logic.updateTable(self.line_point_table, key, row)
        self.logic.updateTableView(self.line_point_table, self.line_point_table_view)

    def onExportButton(self):
        self.logic.exportationFunction(
            self.directoryExportDistance,
            self.filenameExportDistance,
            self.distance_table,
            "distance",
        )

    def onExportAngleButton(self):
        self.logic.exportationFunction(
            self.directoryExportAngle,
            self.filenameExportAngle,
            self.angles_table,
            "angle",
        )

    def onExportLinePointButton(self):
        self.logic.exportationFunction(
            self.directoryExportLinePoint,
            self.filenameExportLinePoint,
            self.line_point_table,
            "linePoint",
        )


class Q3DCLogic(ScriptedLoadableModuleLogic):
    def __init__(self, interface):
        ScriptedLoadableModuleLogic.__init__(self)

        self.interface = interface
        self.selectedModel = None
        self.selectedFidList = None
        self.current_suggested_landmarks = None
        self.enable_legend_labels = True
        self.projectNewPoints = True
        self.numberOfDecimals = 3
        self.tolerance = 1e-5
        system = qt.QLocale().system()
        self.decimalPoint = chr(system.decimalPoint())
        self.comboboxdict = {}

    @staticmethod
    def load_suggested_landmarks(filepath):
        suggested_landmarks = defaultdict(list)
        try:
            with open(filepath, newline="", encoding="utf8") as suggestions_file:
                reader = csv.DictReader(suggestions_file)
                for row in reader:
                    region = row["Region"].title()
                    landmark = row["Landmark"]
                    name = row["Name"]
                    suggested_landmarks[region].append((landmark, name))
            return suggested_landmarks
        except OSError as e:
            slicer.util.delayDisplay("Unable to find/open file.")
            logging.info("User attempted to open a landmark legend file.\n" + repr(e))
            return None
        except csv.Error as e:
            slicer.util.delayDisplay("The selected file is not formatted properly.")
            logging.info("User attempted to open a landmark legend file.\n" + repr(e))
            return None
        except KeyError as e:
            slicer.util.delayDisplay(
                "The selected file does not have the right column names."
            )
            logging.info("User attempted to open a landmark legend file.\n" + repr(e))
            return None

    def UpdateThreeDView(self, selectedFidReflID):
        # Update the 3D view on Slicer
        if not self.selectedFidList:
            return
        if not self.selectedModel:
            return
        logging.debug("UpdateThreeDView")
        active = self.selectedFidList
        # deactivate all landmarks
        list = slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsFiducialNode")
        end = list.GetNumberOfItems()
        for i in range(0, end):
            fidList = list.GetItemAsObject(i)
            logging.info("fidList ID: %s", fidList.GetID())
            landmarkDescription = self.decodeJSON(
                fidList.GetAttribute("landmarkDescription")
            )
            if landmarkDescription:
                for key in landmarkDescription.keys():
                    markupsIndex = fidList.GetNthControlPointIndexByID(key)
                    if key != selectedFidReflID:
                        fidList.SetNthMarkupLocked(markupsIndex, True)
                    else:
                        fidList.SetNthMarkupLocked(markupsIndex, False)
                        fidList.SetNthMarkupLocked(markupsIndex, False)

    # def onModelModified(self, obj, event):  # todo move to deps
    #     # recompute the harden model
    #     hardenModel = self.createIntermediateHardenModel(obj)
    #     obj.SetAttribute("hardenModelID", hardenModel.GetID())
    #     # for each fiducial list
    #     list = slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsFiducialNode")
    #     end = list.GetNumberOfItems()
    #     for i in range(0, end):
    #         # If landmarks are projected on the modified model
    #         fidList = list.GetItemAsObject(i)
    #         if fidList.GetAttribute("connectedModelID"):
    #             if fidList.GetAttribute("connectedModelID") == obj.GetID():
    #                 # replace the harden model with the new one
    #                 fidList.SetAttribute("hardenModelID", hardenModel.GetID())
    #                 # reproject the fiducials on the new model
    #                 landmarkDescription = self.decodeJSON(
    #                     fidList.GetAttribute("landmarkDescription")
    #                 )
    #                 for n in range(fidList.GetNumberOfMarkups()):
    #                     markupID = fidList.GetNthMarkupID(n)
    #                     if landmarkDescription[markupID]["projection"]["isProjected"]:
    #                         hardenModel = slicer.app.mrmlScene().GetNodeByID(
    #                             fidList.GetAttribute("hardenModelID")
    #                         )
    #                         markupsIndex = fidList.GetNthControlPointIndexByID(markupID)
    #                         self.replaceLandmark(
    #                             hardenModel.GetPolyData(),
    #                             fidList,
    #                             markupsIndex,
    #                             landmarkDescription[markupID]["projection"][
    #                                 "closestPointIndex"
    #                             ],
    #                         )
    #                     fidList.SetAttribute(
    #                         "landmarkDescription", self.encodeJSON(landmarkDescription)
    #                     )

    # def ModelChanged(  # todo move to deps
    #     self, inputModelSelector, inputLandmarksSelector
    # ):
    #     inputModel = inputModelSelector.currentNode()
    #     # if a Model Node is present
    #     if inputModel:
    #         self.selectedModel = inputModel
    #         hardenModel = self.createIntermediateHardenModel(inputModel)
    #         inputModel.SetAttribute("hardenModelID", hardenModel.GetID())
    #         modelModifieTagEvent = inputModel.AddObserver(
    #             inputModel.TransformModifiedEvent, self.onModelModified
    #         )
    #         inputModel.SetAttribute(
    #             "modelModifieTagEvent",
    #             self.encodeJSON({"modelModifieTagEvent": modelModifieTagEvent}),
    #         )
    #         inputLandmarksSelector.setEnabled(True)
    #     # if no model is selected
    #     else:
    #         # Update the fiducial list selector
    #         inputLandmarksSelector.setCurrentNode(None)
    #         inputLandmarksSelector.setEnabled(False)

    def updateLinesEvent(self, obj, event):
        if (
            self.interface.line1LAComboBox.currentData != ""
            and self.interface.line1LBComboBox.currentData != ""
            and self.interface.line1LAComboBox.currentData
            != self.interface.line1LBComboBox.currentData
        ):
            # Clear Lines, then define new ones
            if self.interface.renderer1:
                self.interface.renderer1.RemoveActor(self.interface.actor1)
            (
                self.interface.renderer1,
                self.interface.actor1,
            ) = self.drawLineBetween2Landmark(
                self.interface.line1LAComboBox.currentData,
                self.interface.line1LBComboBox.currentData,
                self.interface.fidListComboBoxline1LA.currentNode(),
                self.interface.fidListComboBoxline1LB.currentNode(),
            )
        if (
            self.interface.line2LAComboBox.currentData != ""
            and self.interface.line2LBComboBox.currentData != ""
            and self.interface.line2LAComboBox.currentData
            != self.interface.line2LBComboBox.currentData
        ):
            if self.interface.renderer2:
                self.interface.renderer2.RemoveActor(self.interface.actor2)
            (
                self.interface.renderer2,
                self.interface.actor2,
            ) = self.drawLineBetween2Landmark(
                self.interface.line2LAComboBox.currentData,
                self.interface.line2LBComboBox.currentData,
                self.interface.fidListComboBoxline2LA.currentNode(),
                self.interface.fidListComboBoxline2LB.currentNode(),
            )
        if (
            self.interface.lineLAComboBox.currentData != ""
            and self.interface.lineLBComboBox.currentData != ""
            and self.interface.lineLAComboBox.currentData
            != self.interface.lineLBComboBox.currentData
        ):
            if self.interface.renderer3:
                self.interface.renderer3.RemoveActor(self.interface.actor3)
            (
                self.interface.renderer3,
                self.interface.actor3,
            ) = self.drawLineBetween2Landmark(
                self.interface.lineLAComboBox.currentData,
                self.interface.lineLBComboBox.currentData,
                self.interface.fidListComboBoxlineLA.currentNode(),
                self.interface.fidListComboBoxlineLB.currentNode(),
            )

    def removecomponentFromStorage(self, type, element):
        if type == "angles":
            element.Yaw = None
            element.Roll = None
            element.Pitch = None
        if type == "distance":
            element.RLComponent = None
            element.APComponent = None
            element.SIComponent = None
            element.ThreeDComponent = None
        return element

    @classmethod
    def createTable(cls, col_names):
        table = slicer.vtkMRMLTableNode()
        table.SetSaveWithScene(False)
        table.SetLocked(True)

        col_names = ["  "] + [f" {name} " for name in col_names]

        with NodeModify(table):
            table.RemoveAllColumns()
            for col_name in col_names:
                table.AddColumn().SetName(col_name)
                table.SetUseColumnNameAsColumnHeader(True)

        return table

    @classmethod
    def createDistanceTable(cls):
        names = "R-L Component", "A-P Component", "S-I Component", "3D Distance"
        return cls.createTable(names)

    @classmethod
    def createAnglesTable(cls):
        names = "YAW", "PITCH", "ROLL"
        return cls.createTable(names)

    @classmethod
    def createLinePointTable(cls):
        names = "R-L Component", "A-P Component", "S-I Component", "3D Distance"
        return cls.createTable(names)

    def updateTable(self, table, key, data):
        empty = " - "  # text to use if data is not present

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

    def drawLineBetween2Landmark(self, landmark1ID, landmark2ID, fidList1, fidList2):
        if not fidList1 or not fidList2 or not landmark1ID or not landmark2ID:
            return

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

    def exportationFunction(
        self, directoryExport, filenameExport, tableToExport, typeCalculation
    ):
        messageBox = ctk.ctkMessageBox()
        messageBox.setWindowTitle(" /!\ WARNING /!\ ")
        messageBox.setIcon(messageBox.Warning)

        fileName = os.path.join(directoryExport.directory, filenameExport.text)
        if os.path.exists(fileName):
            messageBox.setText("File " + fileName + " already exists!")
            messageBox.setInformativeText("Do you want to replace it ?")
            messageBox.setStandardButtons(messageBox.No | messageBox.Yes)
            choice = messageBox.exec_()
            if choice == messageBox.No:
                return

        slicer.util.saveNode(tableToExport, fileName)
        slicer.util.delayDisplay(f"Saved to {fileName}")

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
        return json.dumps(input)

    def decodeJSON(self, input):
        if input:
            try:
                # if parsing fails, then the json was saved using the old single-quoted replacement
                return json.loads(input)
            except json.JSONDecodeError:
                # if parsing fails after the replacement, then the input would contain something like
                # ... 'landmarkName': 'UR1'', ... which cannot be automatically recovered.
                input = input.replace("'", '"')
                return json.loads(input)

        return None


class Q3DCTest(ScriptedLoadableModuleTest):
    def setUp(self):
        """Do whatever is needed to reset the state - typically a scene clear will be enough."""
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        """Run as few or as many tests as needed here."""
        self.setUp()
        self.delayDisplay(" Starting tests ", 200)

        try:
            self.delayDisplay(" Test Calculate Distance")
            self.test_CalculateDistance()

            self.delayDisplay(" Test Calculate Angles")
            self.test_CalculateAngles()

            self.delayDisplay(" Test Calculate Line Point")
            self.test_CalculateLinePoint()

            self.delayDisplay(" Test Tutorial Simulation")
            self.test_SimulateTutorial()
        except AssertionError:
            self.delayDisplay(" Test Failed")
            return

        self.delayDisplay(" Tests Passed")

    def test_CalculateDistance(self):
        logic = Q3DCLogic(slicer.modules.Q3DCWidget)
        markupsNode1 = slicer.vtkMRMLMarkupsFiducialNode()
        markupsNode1.AddFiducial(-5.331, 51.955, 4.831)
        markupsNode2 = slicer.vtkMRMLMarkupsFiducialNode()
        markupsNode2.AddFiducial(999, 999, 999)
        markupsNode2.AddFiducial(-8.018, 41.429, -52.621)

        key, args = logic.getDistanceArgs(
            markupsNode1,
            markupsNode2,
            markupsNode1.GetNthControlPointLabel(0),
            markupsNode2.GetNthControlPointLabel(1),
        )

        dx, dy, dz, dist = logic.computeDistance(*args)
        assert (dx, dy, dz, dist) == (-2.687, -10.526, -57.452, 58.47)

    def test_CalculateAngles(self):
        logic = Q3DCLogic(slicer.modules.Q3DCWidget)

        markupsNode1 = slicer.vtkMRMLMarkupsFiducialNode()
        markupsNode2 = slicer.vtkMRMLMarkupsFiducialNode()
        markupsNode3 = slicer.vtkMRMLMarkupsFiducialNode()
        markupsNode4 = slicer.vtkMRMLMarkupsFiducialNode()

        markupsNode1.AddFiducial(999, 999, 999)
        markupsNode1.AddFiducial(63.90, -46.98, 6.98)  # index 1

        markupsNode2.AddFiducial(999, 999, 999)
        markupsNode2.AddFiducial(999, 999, 999)
        markupsNode2.AddFiducial(43.79, -60.16, 12.16)  # index 2

        markupsNode3.AddFiducial(62.21, -45.31, 7.41)  # index 0

        markupsNode4.AddFiducial(999, 999, 999)
        markupsNode4.AddFiducial(999, 999, 999)
        markupsNode4.AddFiducial(999, 999, 999)
        markupsNode4.AddFiducial(41.97, -61.24, 11.30)  # index 3

        key, args = logic.getAnglesArgs(
            markupsNode1,
            markupsNode2,
            markupsNode3,
            markupsNode4,
            markupsNode1.GetNthControlPointLabel(1),
            markupsNode2.GetNthControlPointLabel(2),
            markupsNode3.GetNthControlPointLabel(0),
            markupsNode4.GetNthControlPointLabel(3),
            True,
            False,
            True,
        )

        yaw, pitch, roll = logic.computeAngles(*args)

        assert yaw == "4.964 / 175.036"
        assert pitch is None
        assert roll == "3.565 / 176.435"

        markupsNode1.RemoveAllMarkups()
        markupsNode1.AddFiducial(53.80, -53.57, 9.47)
        markupsNode1.AddFiducial(53.98, -52.13, 9.13)
        markupsNode1.AddFiducial(52.09, -53.27, 9.36)
        markupsNode1.AddFiducial(51.77, -50.10, 9.80)

        key, args = logic.getAnglesArgs(
            markupsNode1,
            markupsNode1,
            markupsNode1,
            markupsNode1,
            markupsNode1.GetNthControlPointLabel(0),
            markupsNode1.GetNthControlPointLabel(1),
            markupsNode1.GetNthControlPointLabel(2),
            markupsNode1.GetNthControlPointLabel(3),
            False,
            True,
            False,
        )

        yaw, pitch, roll = logic.computeAngles(*args)

        assert yaw is None
        assert pitch == "21.187 / 158.813"
        assert roll is None

    def test_CalculateLinePoint(self):
        logic = Q3DCLogic(slicer.modules.Q3DCWidget)

        markups1 = slicer.vtkMRMLMarkupsFiducialNode()
        markups2 = slicer.vtkMRMLMarkupsFiducialNode()
        markups3 = slicer.vtkMRMLMarkupsFiducialNode()

        # simple geometric case
        markups1.RemoveAllMarkups()
        markups1.AddFiducial(0, 1, -1)  # index 0

        markups2.AddFiducial(999, 999, 999)
        markups2.AddFiducial(999, 999, 999)
        markups2.AddFiducial(0, -1, 1)  # index 2

        markups3.AddFiducial(-1, 0, 0)  # index 0

        key, args = logic.getLinePointArgs(
            markups1,
            markups2,
            markups3,
            markups1.GetNthControlPointLabel(0),
            markups2.GetNthControlPointLabel(2),
            markups3.GetNthControlPointLabel(0),
        )

        dx, dy, dz, norm = logic.computeLinePoint(*args)
        print(dx, dy, dz, norm)
        assert (dx, dy, dz, norm) == (-1, 0, 0, 1)

        markups = slicer.vtkMRMLMarkupsFiducialNode()

        # simple geometric case where solution is outside the line segment
        markups.RemoveAllMarkups()
        markups.AddFiducial(0, 0, 1)
        markups.AddFiducial(0, 1, 1)
        markups.AddFiducial(0, -1, 0)

        key, args = logic.getLinePointArgs(
            markups,
            markups,
            markups,
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
            markups,
            markups,
            markups,
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
            markups,
            markups,
            markups,
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
            (
                "http://slicer.kitware.com/midas3/download/item/211921/Q3DCExtensionTestData.zip",
                "Q3DCExtensionTestData.zip",
            ),
        )

        self.delayDisplay("Downloading")
        for url, name in downloads:
            filePath = slicer.app.temporaryPath + "/" + name
            if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
                self.delayDisplay("Requesting download %s from %s...\n" % (name, url))
                urllib.request.urlretrieve(url, filePath)
        self.delayDisplay("Finished with download\n")

        self.delayDisplay("Unzipping")
        q3dcFilesDirectory = slicer.app.temporaryPath + "/q3dcFiles"
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

        modelNodes["AH2m"].GetDisplayNode().SetVisibility(0)
        modelNodes["AH1m"].GetDisplayNode().SetColor((1, 0, 0))

        self.delayDisplay("Enter markup mode")
        q3dcWidget = slicer.modules.Q3DCWidget

        points = ((43, 25, -10), (-49, 22, -8), (-6, 64, -53))

        firstMarkupsNode = None

        movingMarkupsFiducial = slicer.vtkMRMLMarkupsFiducialNode()
        movingMarkupsFiducial.SetName("F")
        slicer.mrmlScene.AddNode(movingMarkupsFiducial)
        q3dcWidget.inputModelSelector.setCurrentNode(modelNodes["AH2m"])
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
        interactionNode = slicer.mrmlScene.GetNodeByID(
            "vtkMRMLInteractionNodeSingleton"
        )
        interactionNode.SetCurrentInteractionMode(
            slicer.vtkMRMLInteractionNode.ViewTransform
        )

        self.delayDisplay("Define a middle point")
        q3dcWidget.midPointGroupBox.collapsed = False
        q3dcWidget.landmarkComboBox2.currentIndex = 1
        q3dcWidget.defineMiddlePointButton.clicked()
        midpointMarkupID = q3dcWidget.logic.findIDFromLabel(
            movingMarkupsFiducial, "F-4"
        )
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
        midpointMarkupIndex = movingMarkupsFiducial.GetNthControlPointIndexByID(
            midpointMarkupID
        )
        initialPosition = [
                              0,
                          ] * 3
        movingMarkupsFiducial.GetNthFiducialPosition(
            midpointMarkupIndex, initialPosition
        )
        movingMarkupsFiducial.SetNthFiducialPosition(0, 45, 20, -15)
        movedPosition = [
                            0,
                        ] * 3
        movingMarkupsFiducial.GetNthFiducialPosition(midpointMarkupIndex, movedPosition)
        if initialPosition == movedPosition:
            logging.info("midpoint landmark did not move")
            return False

        return True
