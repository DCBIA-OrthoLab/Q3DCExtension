import csv
import logging
import os
from collections import defaultdict

import ctk
import numpy as np
import qt
import slicer
import vtk
from slicer.ScriptedLoadableModule import *
from slicer.util import NodeModify

try:
    from MarkupConstraints.MarkupConstraints import MarkupConstraintsLogic, ControlPoint, constraint
except:
    from MarkupConstraints import MarkupConstraintsLogic, ControlPoint, constraint

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


@constraint
def named_midpoint(target: ControlPoint, *sources: ControlPoint):
    """Move target position to the mean of source positions."""

    pos = vtk.vtkVector3d()
    for dep in sources:
        vtk.vtkMath.Add(pos, dep.position, pos)
    vtk.vtkMath.MultiplyScalar(pos, 1 / len(sources))

    target.position = pos

    target.label = '_'.join(dep.label for dep in sources)


class Q3DCWidget(ScriptedLoadableModuleWidget, slicer.util.VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        slicer.util.VTKObservationMixin.__init__(self)

        self.ui = None

        self.current_suggested_landmarks = []

        self.logic = Q3DCLogic()

    def setup(self):
        logging.debug("Q3DC Widget Setup")
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer)
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/Q3DC.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # -------------------------- Scene ---------------------------
        treeView = self.ui.treeView
        treeView.setMRMLScene(slicer.app.mrmlScene())
        treeView.sceneModel().setHorizontalHeaderLabels(["Models"])
        treeView.sortFilterProxyModel().nodeTypes = ['vtkMRMLModelNode', 'vtkMRMLMarkupsFiducialNode']
        treeView.header().setVisible(False)

        # ------------------ Landmark Modification -------------------
        self.ui.inputModelSelector.setMRMLScene(slicer.mrmlScene)
        self.ui.inputModelSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onModelChanged)

        self.ui.inputLandmarksSelector.setMRMLScene(slicer.mrmlScene)
        self.ui.inputLandmarksSelector.enabled = False  # The "enable" property seems to not be imported from the .ui
        self.ui.inputLandmarksSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onLandmarksChanged)

        self.synchronizeControlPointComboboxes(self.ui.inputLandmarksSelector, self.ui.landmarkComboBox)
        self.synchronizeControlPointComboboxes(self.ui.inputLandmarksSelector, self.ui.landmarkComboBox1)
        self.synchronizeControlPointComboboxes(self.ui.inputLandmarksSelector, self.ui.landmarkComboBox2)

        # self.ui.loadLandmarksOnSurfaceCheckBox.connect('stateChanged(int)', self.onLoadLandmarksOnSurfaceStateChanged)  # todo projection

        self.ui.addLandmarkButton.connect('clicked()', self.onAddLandmarkButtonClicked)
        self.ui.addLandmarkButton.enabled = False

        self.ui.landmarkComboBox.connect('currentIndexChanged(QString)', self.UpdateInterface)
        # self.ui.surfaceDeplacementCheckBox.connect('stateChanged(int)', self.onSurfaceDeplacementStateChanged)  # todo projection

        # --------------------- Anatomical Legend --------------------
        landmarks_path = self.resourcePath('Data/base_fiducial_legend.csv')
        self.suggested_landmarks = self.logic.load_suggested_landmarks(landmarks_path)
        self.anatomical_radio_buttons_layout = qt.QHBoxLayout()  # todo move to qml
        self.ui.landmarkModifLayout.addLayout(self.anatomical_radio_buttons_layout)

        self.anatomical_legend = None
        self.init_anatomical_legend()
        self.anatomical_legend_view = slicer.qMRMLTableView()
        self.anatomical_legend_view.setMRMLTableNode(self.anatomical_legend)
        self.ui.landmarkModifLayout.addWidget(self.anatomical_legend_view)
        self.anatomical_legend_view.show()
        self.anatomical_legend_view.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.anatomical_legend_view.connect('selectionChanged()', self.on_legend_row_selected)

        self.init_anatomical_radio_buttons()

        self.ui.legendFileButton.connect('clicked()', self.on_select_legend_file_clicked)

        # ---------------------- Compute Mid Point ---------------------
        self.ui.landmarkComboBox1.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.landmarkComboBox2.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.defineMiddlePointButton.connect('clicked()', self.onDefineMidPointClicked)

        # ------------------- Calculate Distances --------------------
        self.ui.fidListComboBoxA.setMRMLScene(slicer.mrmlScene)
        self.ui.fidListComboBoxB.setMRMLScene(slicer.mrmlScene)

        self.synchronizeControlPointComboboxes(self.ui.fidListComboBoxA, self.ui.landmarkComboBoxA)
        self.synchronizeControlPointComboboxes(self.ui.fidListComboBoxB, self.ui.landmarkComboBoxB)

        self.ui.landmarkComboBoxA.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.landmarkComboBoxB.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.computeDistancesPushButton.connect('clicked()', self.onComputeDistanceClicked)

        # ---------------------- Save Distances ----------------------
        self.distance_table = self.logic.createDistanceTable()
        slicer.mrmlScene.AddNode(self.distance_table)
        self.distance_table_view = slicer.qMRMLTableView()
        self.distance_table_view.setMRMLTableNode(self.distance_table)
        self.directoryExportDistance = ctk.ctkDirectoryButton()  # todo move to qml
        self.filenameExportDistance = qt.QLineEdit('distance.csv')
        self.exportDistanceButton = qt.QPushButton(" Export ")
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

        self.synchronizeControlPointComboboxes(self.ui.fidListComboBoxline1LA, self.ui.line1LAComboBox)
        self.synchronizeControlPointComboboxes(self.ui.fidListComboBoxline1LB, self.ui.line1LBComboBox)
        self.synchronizeControlPointComboboxes(self.ui.fidListComboBoxline2LA, self.ui.line2LAComboBox)
        self.synchronizeControlPointComboboxes(self.ui.fidListComboBoxline2LB, self.ui.line2LBComboBox)

        self.ui.line1LAComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.line1LBComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.line2LAComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.line2LBComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.pitchCheckBox.connect('clicked(bool)', self.UpdateInterface)
        self.ui.rollCheckBox.connect('clicked(bool)', self.UpdateInterface)
        self.ui.yawCheckBox.connect('clicked(bool)', self.UpdateInterface)

        self.ui.computeAnglesPushButton.connect('clicked()', self.onComputeAnglesClicked)

        # ----------------------- Save Angles ------------------------
        self.angles_table = self.logic.createAnglesTable()
        slicer.mrmlScene.AddNode(self.angles_table)
        self.angles_table_view = slicer.qMRMLTableView()
        self.angles_table_view.setMRMLTableNode(self.angles_table)
        self.directoryExportAngle = ctk.ctkDirectoryButton()  # todo move to qml
        self.filenameExportAngle = qt.QLineEdit('angle.csv')
        self.exportAngleButton = qt.QPushButton("Export")
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

        self.synchronizeControlPointComboboxes(self.ui.fidListComboBoxlineLA, self.ui.lineLAComboBox)
        self.synchronizeControlPointComboboxes(self.ui.fidListComboBoxlineLB, self.ui.lineLBComboBox)
        self.synchronizeControlPointComboboxes(self.ui.fidListComboBoxlinePoint, self.ui.linePointComboBox)

        self.ui.computeLinePointPushButton.connect('clicked()', self.onComputeLinePointClicked)
        self.ui.lineLAComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)
        self.ui.lineLBComboBox.connect('currentIndexChanged(int)', self.UpdateInterface)

        # ---------------- Save Line-Point Distances -----------------
        self.line_point_table = self.logic.createLinePointTable()
        slicer.mrmlScene.AddNode(self.line_point_table)
        self.line_point_table_view = slicer.qMRMLTableView()
        self.line_point_table_view.setMRMLTableNode(self.line_point_table)
        self.directoryExportLinePoint = ctk.ctkDirectoryButton()  # todo move to qml
        self.filenameExportLinePoint = qt.QLineEdit('linePoint.csv')
        self.exportLinePointButton = qt.QPushButton("Export")
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

        # Viewing-Aid Line Markups
        self.synchronizeLineViewingAid(self.ui.lineLAComboBox, self.ui.lineLBComboBox)
        self.synchronizeLineViewingAid(self.ui.line1LAComboBox, self.ui.line1LBComboBox)
        self.synchronizeLineViewingAid(self.ui.line2LAComboBox, self.ui.line2LBComboBox)

        # ---------------------- Data Export -------------------------

        self.exportDistanceButton.connect(
            'clicked()',
            lambda: self.logic.exportTable(
                self.directoryExportDistance,
                self.filenameExportDistance,
                self.distance_table,
            )
        )

        self.exportAngleButton.connect(
            'clicked()',
            lambda: self.logic.exportTable(
                self.directoryExportAngle,
                self.filenameExportAngle,
                self.angles_table,
            )
        )

        self.exportLinePointButton.connect(
            'clicked()',
            lambda: self.logic.exportTable(
                self.directoryExportLinePoint,
                self.filenameExportLinePoint,
                self.line_point_table,
            )
        )

        # INITIALISATION:
        slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndCloseEvent, self.onCloseScene)
        self.UpdateInterface()

    def onCloseScene(self, obj, event):
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
        self.UpdateInterface()

    def UpdateInterface(self):
        # todo parameter node
        self.ui.defineMiddlePointButton.enabled = all((
            self.ui.landmarkComboBox1.currentText != '',
            self.ui.landmarkComboBox2.currentText != '',
            self.ui.landmarkComboBox1.currentText != self.ui.landmarkComboBox2.currentText,
        ))

        self.ui.computeDistancesPushButton.enabled = all((
            self.ui.landmarkComboBoxA.currentText != '',
            self.ui.landmarkComboBoxB.currentText != '',
            (self.ui.fidListComboBoxA.currentNodeID, self.ui.landmarkComboBoxA.currentText) !=
            (self.ui.fidListComboBoxB.currentNodeID, self.ui.landmarkComboBoxB.currentText),
        ))

        self.ui.computeAnglesPushButton.enabled = all((
            self.ui.line1LAComboBox.currentText != '',
            self.ui.line1LBComboBox.currentText != '',
            self.ui.line2LAComboBox.currentText != '',
            self.ui.line2LBComboBox.currentText != '',
            (self.ui.fidListComboBoxline1LA.currentNodeID, self.ui.line1LAComboBox.currentText) !=
            (self.ui.fidListComboBoxline1LB.currentNodeID, self.ui.line1LBComboBox.currentText),
            (self.ui.fidListComboBoxline2LA.currentNodeID, self.ui.line2LAComboBox.currentText) !=
            (self.ui.fidListComboBoxline2LB.currentNodeID, self.ui.line2LBComboBox.currentText),
            any((
                self.ui.pitchCheckBox.checked,
                self.ui.rollCheckBox.checked,
                self.ui.yawCheckBox.checked,
            )),
        ))

        self.ui.computeLinePointPushButton.enabled = all((
            self.ui.lineLAComboBox.currentText != '',
            self.ui.lineLBComboBox.currentText != '',
            self.ui.linePointComboBox.currentText != '',
            (self.ui.fidListComboBoxlineLA.currentNodeID, self.ui.lineLAComboBox.currentText) !=
            (self.ui.fidListComboBoxlineLB.currentNodeID, self.ui.lineLBComboBox.currentText),
        ))

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
        self.anatomical_radio_buttons = [qt.QRadioButton(region) for region in self.suggested_landmarks.keys()]
        for i in range(self.anatomical_radio_buttons_layout.count() - 1, -1, -1):
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
            self.current_suggested_landmarks = self.suggested_landmarks[region]

            al = self.anatomical_legend
            with NodeModify(al):
                for landmark, description in self.current_suggested_landmarks:
                    new_row_index = al.AddEmptyRow()
                    al.SetCellText(new_row_index, 0, landmark)
                    al.SetCellText(new_row_index, 1, description)
            self.anatomical_legend_view.resizeColumnsToContents()

    def on_legend_row_selected(self):
        point: ControlPoint = self.ui.landmarkComboBox.currentData

        # todo prevent duplicate names

        indexes = self.anatomical_legend_view.selectedIndexes()
        if len(indexes) != 2:
            return

        label_idx, description_idx = indexes
        point.label = self.anatomical_legend.GetCellText(
            label_idx.row(),
            label_idx.column(),
        )
        point.description = self.anatomical_legend.GetCellText(
            description_idx.row(),
            description_idx.column(),
        )

    def on_select_legend_file_clicked(self):
        legend_filename = qt.QFileDialog.getOpenFileName(
            None, 'Select File', '', 'CSV (*.csv)')
        if legend_filename == '':
            # User canceled the file selection dialog.
            return
        suggested_landmarks = self.logic.load_suggested_landmarks(
            legend_filename)
        if suggested_landmarks is None:
            return
        self.suggested_landmarks = suggested_landmarks
        self.init_anatomical_radio_buttons()

    def onModelChanged(self, model):
        self.ui.inputLandmarksSelector.enabled = model is not None
        self.ui.inputLandmarksSelector.setCurrentNode(None)
        # todo parameter node
        # todo update projection targets

    def onLandmarksChanged(self, node):
        self.ui.addLandmarkButton.enabled = node is not None

    def synchronizeControlPointComboboxes(self, node_combobox, point_combobox):
        """Ensure that point_combobox enumerates the controlpoints of the node currently selected by node_combobox"""

        def repopulate(node, event=None):
            original = point_combobox.currentData
            point_combobox.clear()

            if node:
                for idx in range(node.GetNumberOfControlPoints()):
                    id_ = node.GetNthControlPointID(idx)
                    point = ControlPoint(node, id_)
                    point_combobox.addItem(point.label, point)

            if original:
                point_combobox.currentText = original.label
            else:
                point_combobox.currentIndex = 0

        observers = slicer.util.VTKObservationMixin()

        def onNodeChanged(node):
            repopulate(node)
            observers.removeObservers(repopulate)
            if node:
                observers.addObserver(node, node.PointAddedEvent, repopulate)
                observers.addObserver(node, node.PointModifiedEvent, repopulate)
                observers.addObserver(node, node.PointRemovedEvent, repopulate)

        node_combobox.connect('currentNodeChanged(vtkMRMLNode*)', onNodeChanged)

    def synchronizeLineViewingAid(self, tgtA_combobox, tgtB_combobox):
        line = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsLineNode')
        line.CreateDefaultDisplayNodes()
        line.HideFromEditorsOn()
        line.LockedOn()
        line.GetDisplayNode().PointLabelsVisibilityOff()
        line.GetDisplayNode().PropertiesLabelVisibilityOff()
        line.GetDisplayNode().VisibilityOff()

        A = ControlPoint.new(line)
        B = ControlPoint.new(line)

        def setConstraints():
            tgtA = tgtA_combobox.currentData
            tgtB = tgtB_combobox.currentData

            if tgtA and tgtB:
                self.logic.constraints.setConstraint(A, 'lock', tgtA)
                self.logic.constraints.setConstraint(B, 'lock', tgtB)
                line.GetDisplayNode().VisibilityOn()
            else:
                self.logic.constraints.delConstraint(A)
                self.logic.constraints.delConstraint(B)
                line.GetDisplayNode().VisibilityOff()

        tgtA_combobox.currentIndexChanged.connect(setConstraints)
        tgtB_combobox.currentIndexChanged.connect(setConstraints)

        return line

    def onAddLandmarkButtonClicked(self):
        selection = slicer.mrmlScene.GetSingletonNode('Singleton', 'vtkMRMLSelectionNode')
        selection.SetReferenceActivePlaceNodeClassName('vtkMRMLMarkupsFiducialNode')

        interaction = slicer.mrmlScene.GetSingletonNode('Singleton', 'vtkMRMLInteractionNode')

        # todo parameter node
        model = self.ui.inputModelSelector.currentNode()
        landmarks = self.ui.inputLandmarksSelector.currentNode()

        if model and landmarks:
            idx = landmarks.AddControlPoint((0, 0, 0))
            landmarks.UnsetNthControlPointPosition(idx)  # so that placement modifies this point

            # todo should be aware of the last point placed using the legend
            try:
                label, description = self.current_suggested_landmarks[idx]
                landmarks.SetNthControlPointLabel(idx, label)
                landmarks.SetNthControlPointDescription(idx, description)
            except IndexError:
                pass

            selection.SetActivePlaceNodeID(landmarks.GetID())
            interaction.SetCurrentInteractionMode(interaction.Place)
        else:
            # todo show error. shouldn't be possible to reach this state.
            pass

    def onDefineMidPointClicked(self):
        # todo parameter node
        landmarks = self.ui.inputLandmarksSelector.currentNode()

        self.logic.defineMidPoint(
            self.ui.inputLandmarksSelector.currentNode(),
            self.ui.landmarkComboBox1.currentData,
            self.ui.landmarkComboBox2.currentData,
        )

    def onComputeDistanceClicked(self):
        # todo parameter node

        A = self.ui.landmarkComboBoxA.currentData
        B = self.ui.landmarkComboBoxB.currentData

        key = f'{A.label} - {B.label}'
        data = self.logic.computeDistance(A.position, B.position)

        self.ui.distanceLayout.addLayout(self.tableAndExportLayout)
        self.logic.updateTable(self.distance_table, key, data)
        self.logic.updateTableView(self.distance_table, self.distance_table_view)

    def onComputeAnglesClicked(self):
        # todo parameter node

        states = (
            self.ui.yawCheckBox.isChecked(),
            self.ui.pitchCheckBox.isChecked(),
            self.ui.rollCheckBox.isChecked(),
        )

        A = self.ui.line1LAComboBox.currentData
        B = self.ui.line1LBComboBox.currentData
        C = self.ui.line2LAComboBox.currentData
        D = self.ui.line2LBComboBox.currentData

        key = f'{A.label}-{B.label} / {C.label}-{D.label}'
        data = self.logic.computeAngles(A.position, B.position, C.position, D.position, states)

        self.ui.angleLayout.addLayout(self.tableAndExportAngleLayout)
        self.logic.updateTable(self.angles_table, key, data)
        self.logic.updateTableView(self.angles_table, self.angles_table_view)

    def onComputeLinePointClicked(self):
        # todo parameter node

        A = self.ui.lineLAComboBox.currentData
        B = self.ui.lineLBComboBox.currentData
        P = self.ui.linePointComboBox.currentData

        key = f'{A.label}-{B.label} / {P.label}'
        data = self.logic.computeLinePoint(A.position, B.position, P.position)

        self.ui.LinePointLayout.addLayout(self.tableAndExportLinePointLayout)
        self.logic.updateTable(self.line_point_table, key, data)
        self.logic.updateTableView(self.line_point_table, self.line_point_table_view)


class Q3DCLogic(ScriptedLoadableModuleLogic):
    #     def __init__(self, interface):
    #         self.enable_legend_labels = True
    #         self.projectNewPoints = True
    #
    #     def connectedModelChangement(self):
    #         messageBox = ctk.ctkMessageBox()
    #         messageBox.setWindowTitle(" /!\ WARNING /!\ ")
    #         messageBox.setIcon(messageBox.Warning)
    #         messageBox.setText("The Markup Fiducial Node selected is curently projected on an"
    #                            "other model, if you chose to continue the fiducials will be  "
    #                            "reprojected, and this could impact the functioning of other modules")
    #         messageBox.setInformativeText("Do you want to continue?")
    #         messageBox.setStandardButtons(messageBox.No | messageBox.Yes)
    #         choice = messageBox.exec_()
    #         if choice == messageBox.Yes:
    #             return True
    #         else:
    #             messageBox.setText(" Node not modified")
    #             messageBox.setStandardButtons(messageBox.Ok)
    #             messageBox.setInformativeText("")
    #             messageBox.exec_()
    #             return False

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)

        self.numberOfDecimals = 3
        self.tolerance = 1e-5

        self.constraints = MarkupConstraintsLogic()

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

    def defineMidPoint(self, node, a: ControlPoint, b: ControlPoint):
        c = ControlPoint.new(node)

        # todo respect projection

        self.constraints.setConstraint(c, 'named_midpoint', a, b)

    def round(self, value):  # todo use numpy rounding
        return round(value, self.numberOfDecimals)

    def computeDistance(self, point1, point2):
        point1 = np.asarray(point1)
        point2 = np.asarray(point2)

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

    def computeAngles(self, line1a, line1b, line2a, line2b, states):
        line1a = np.asarray(line1a)
        line1b = np.asarray(line1b)
        line2a = np.asarray(line2a)
        line2b = np.asarray(line2b)

        line1 = line1b - line1a
        line2 = line2b - line2a

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
        lineA = np.asarray(lineA)
        lineB = np.asarray(lineB)
        point = np.asarray(point)

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

    def exportTable(self, directoryExport, filenameExport, tableToExport):
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
        markupsNode2 = slicer.vtkMRMLMarkupsFiducialNode()
        markupsNode2.AddFiducial(999, 999, 999)
        markupsNode2.AddFiducial(-8.018, 41.429, -52.621)

        key, args = logic.getDistanceArgs(
            markupsNode1, markupsNode2,
            markupsNode1.GetNthControlPointLabel(0),
            markupsNode2.GetNthControlPointLabel(1)
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
            markupsNode1, markupsNode2, markupsNode3, markupsNode4,
            markupsNode1.GetNthControlPointLabel(1),
            markupsNode2.GetNthControlPointLabel(2),
            markupsNode3.GetNthControlPointLabel(0),
            markupsNode4.GetNthControlPointLabel(3),
            True, False, True
        )

        yaw, pitch, roll = logic.computeAngles(*args)

        assert yaw == '4.964 / 175.036'
        assert pitch is None
        assert roll == '3.565 / 176.435'

        markupsNode1.RemoveAllMarkups()
        markupsNode1.AddFiducial(53.80, -53.57, 9.47)
        markupsNode1.AddFiducial(53.98, -52.13, 9.13)
        markupsNode1.AddFiducial(52.09, -53.27, 9.36)
        markupsNode1.AddFiducial(51.77, -50.10, 9.80)

        key, args = logic.getAnglesArgs(
            markupsNode1, markupsNode1, markupsNode1, markupsNode1,
            markupsNode1.GetNthControlPointLabel(0),
            markupsNode1.GetNthControlPointLabel(1),
            markupsNode1.GetNthControlPointLabel(2),
            markupsNode1.GetNthControlPointLabel(3),
            False, True, False
        )

        yaw, pitch, roll = logic.computeAngles(*args)

        assert yaw is None
        assert pitch == '21.187 / 158.813'
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
            markups1, markups2, markups3,
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
            ('http://slicer.kitware.com/midas3/download/item/211921/Q3DCExtensionTestData.zip',
             'Q3DCExtensionTestData.zip'),
        )

        self.delayDisplay("Downloading")
        for url, name in downloads:
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
        modelNodes['AH1m'].GetDisplayNode().SetColor((1, 0, 0))

        self.delayDisplay("Enter markup mode")
        q3dcWidget = slicer.modules.Q3DCWidget

        points = ((43, 25, -10), (-49, 22, -8), (-6, 64, -53))

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
        midpointMarkupID = q3dcWidget.logic.findIDFromLabel(movingMarkupsFiducial, "F-4")
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
        initialPosition = [0, ] * 3
        movingMarkupsFiducial.GetNthFiducialPosition(midpointMarkupIndex, initialPosition)
        movingMarkupsFiducial.SetNthFiducialPosition(0, 45, 20, -15)
        movedPosition = [0, ] * 3
        movingMarkupsFiducial.GetNthFiducialPosition(midpointMarkupIndex, movedPosition)
        if initialPosition == movedPosition:
            logging.info('midpoint landmark did not move')
            return False

        return True
