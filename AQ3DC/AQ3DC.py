import os
import unittest
import logging
# import patsy
import vtk, qt, ctk, slicer
import glob
import numpy as np
import collections
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import csv
from PySide2.QtCore import Qt
import json
# slicer.app.pythonConsole().clear()
#
# AQ3DC
#
try:
  import pandas as pd
  import openpyxl
  import xlrd
  import xlsxwriter
  # import PyQt5
  # from PySide2.QtCore import Qt,QtWidgets

except: 
  slicer.util.pip_install('pandas')
  slicer.util.pip_install('openpyxl')
  slicer.util.pip_install('xlrd')
  slicer.util.pip_install('xlsxwriter')
  slicer.util.pip_install('PySide2')
  import pandas as pd
  import openpyxl
  import xlrd
  import xlsxwriter
  from PySide2.QtCore import Qt

GROUPS_LANDMARKS = {
  'Cranial Base/Vertebra' : ['Ba', 'S', 'N', 'RPo', 'LPo', 'RFZyg', 'LFZyg', 'C2', 'C3', 'C4'],

  'Maxilla' : ['RInfOr', 'LInfOr', 'LMZyg', 'RPF', 'LPF', 'PNS', 'ANS', 'A', 'UR3O', 'UR1O', 'UL3O', 'UR6DB', 'UR6MB', 'UL6MB', 'UL6DB', 'IF', 'ROr', 'LOr', 'RMZyg', 'RNC', 'LNC', 'UR7O', 'UR5O', 'UR4O', 'UR2O', 'UL1O', 'UL2O', 'UL4O', 'UL5O', 'UL7O', 'UL7R', 'UL5R', 'UL4R', 'UL2R', 'UL1R', 'UR2R', 'UR4R', 'UR5R', 'UR7R', 'UR6MP', 'UL6MP', 'UL6R', 'UR6R', 'UR6O', 'UL6O', 'UL3R', 'UR3R', 'UR1R'],

  'Mandible' : ['RCo', 'RGo', 'Me', 'Gn', 'Pog', 'PogL', 'B', 'LGo', 'LCo', 'LR1O', 'LL6MB', 'LL6DB', 'LR6MB', 'LR6DB', 'LAF', 'LAE', 'RAF', 'RAE', 'LMCo', 'LLCo', 'RMCo', 'RLCo', 'RMeF', 'LMeF', 'RSig', 'RPRa', 'RARa', 'LSig', 'LARa', 'LPRa', 'LR7R', 'LR5R', 'LR4R', 'LR3R', 'LL3R', 'LL4R', 'LL5R', 'LL7R', 'LL7O', 'LL5O', 'LL4O', 'LL3O', 'LL2O', 'LL1O', 'LR2O', 'LR3O', 'LR4O', 'LR5O', 'LR7O', 'LL6R', 'LR6R', 'LL6O', 'LR6O', 'LR1R', 'LL1R', 'LL2R', 'LR2R'],
  
  "Dental" :  ['LL7','LL6','LL5','LL4','LL3','LL2','LL1','LR1','LR2','LR3','LR4','LR5','LR6','LR7','UL7','UL6','UL5','UL4','UL3','UL2','UL1','UR1','UR2','UR3','UR4','UR5','UR6','UR7'] ,
  
  "Landmarks type" : ['CL','CB','O','DB','MB','R','RIP','OIP']

}


class AQ3DC(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "AQ3DC"  # TODO: make this more human readable by adding spaces
    self.parent.categories = ["Quantification"]  # TODO: set categories (folders where the module shows up in the module selector)
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Baptiste Baquero (University of Michigan)"]  # TODO: replace with "Firstname Lastname (Organization)"
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
  This is an example of scripted loadable module bundled in an extension.
  See more information in <a href="https://github.com/organization/projectname#AQ3DC">module documentation</a>.
  """
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
  This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
  and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
  """

    # Additional initialization step after application startup is complete
    slicer.app.connect("startupCompleted()", registerSampleData)

#
# Register sample data sets in Sample Data module
#

def registerSampleData():
  """
  Add data sets to Sample Data module.
  """
  # It is always recommended to provide sample data for users to make it easy to try the module,
  # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

  import SampleData
  iconsPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons')

  # To ensure that the source code repository remains small (can be downloaded and installed quickly)
  # it is recommended to store data sets that are larger than a few MB in a Github release.

  # AQ3DC1
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='AQ3DC',
    sampleName='AQ3DC1',
    # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
    # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
    thumbnailFileName=os.path.join(iconsPath, 'AQ3DC1.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
    fileNames='AQ3DC1.nrrd',
    # Checksum to ensure file integrity. Can be computed by this command:
    #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
    checksums = 'SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
    # This node name will be used when the data set is loaded
    nodeNames='AQ3DC1'
  )

  # AQ3DC2
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='AQ3DC',
    sampleName='AQ3DC2',
    thumbnailFileName=os.path.join(iconsPath, 'AQ3DC2.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
    fileNames='AQ3DC2.nrrd',
    checksums = 'SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97',
    # This node name will be used when the data set is loaded
    nodeNames='AQ3DC2'
  )
  
#
# AQ3DCWidget
#

class AQ3DCWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/AQ3DC.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = AQ3DCLogic()

    # # -------------------------- Scene ---------------------------
    # self.SceneCollapsibleButton = self.ui.SceneCollapsibleButton # this attribute is usefull for Longitudinal quantification extension
    # treeView = self.ui.TreeView
    # treeView.setMRMLScene(slicer.app.mrmlScene())
    # treeView.sceneModel().setHorizontalHeaderLabels(["Models"])
    # treeView.sortFilterProxyModel().nodeTypes = ['vtkMRMLModelNode','vtkMRMLMarkupsFiducialNode']
    # treeView.header().setVisible(False)

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)
    # self.deps = DependantMarkups.DependantMarkupsLogic 


    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).
    # self.ui.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    # self.ui.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    # self.ui.imageThresholdSliderWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
    # self.ui.invertOutputCheckBox.connect("toggled(bool)", self.updateParameterNodeFromGUI)
    # self.ui.invertedOutputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)


    # Buttons
    self.ui.pushButton_DataFolder_T1.connect('clicked(bool)',self.onSearchFolderButton_T1)
    self.ui.pushButton_DataFolder_T2.connect('clicked(bool)',self.onSearchFolderButton_T2)

    # self.distancewidget = DistanceWidget()
    # display of all the different measurment
    self.table_view = TableView(self.ui)
    self.ui.verticalLayout_2.addWidget(self.table_view.widget)

    # layout to add measurment to the tab
    self.tab_manager = TabManager(self.ui,self.table_view)
    self.ui.verticalLayout_3.addWidget(self.tab_manager.widget)
    
    self.MP_Widget = MidPointWidget(self.ui,self.tab_manager)
      
    # selection of the landmarks
    self.lm_tab = LMTab(self.tab_manager,self.MP_Widget)
    self.ui.verticalLayout_1.addWidget(self.lm_tab.widget)

 
    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()



  def onSearchFolderButton_T1(self):
    surface_folder = qt.QFileDialog.getExistingDirectory(self.parent, "Select a scan folder")
    if surface_folder != '':
      self.surface_folder = surface_folder
      self.ui.lineEditLandPathT1.setText(self.surface_folder)
      
      patients_lst_T1,patients_dict_T1,lst_files_T1 = CreateDicPatients(self.surface_folder)
      self.tab_manager.patients_lst_T1 = patients_lst_T1
      self.tab_manager.patients_dict_T1 = patients_dict_T1
      self.MP_Widget.patients_lst_T1 = patients_lst_T1
      self.MP_Widget.patients_dict_T1 = patients_dict_T1
      self.MP_Widget.lst_files_T1 = lst_files_T1
      # print(self.patients_lst_T1)

      lm_group = GetLandmarkGroup(GROUPS_LANDMARKS)
      # print('lm_group :',lm_group)
      available_lm = GetAvailableLm(self.surface_folder,lm_group)
      # print('available_lm :',available_lm)
      self.lm_tab.Clear()
      self.lm_tab.FillTab(available_lm)
 
  def onSearchFolderButton_T2(self):
    surface_folder = qt.QFileDialog.getExistingDirectory(self.parent, "Select a scan folder")
    if surface_folder != '':
      self.surface_folder_2 = surface_folder
      self.ui.lineEditLandPathT2.setText(self.surface_folder_2)
      
      patients_lst_T2,patients_dict_T2,lst_files_T2 = CreateDicPatients(self.surface_folder_2)
      self.tab_manager.patients_lst_T2 = patients_lst_T2
      self.tab_manager.patients_dict_T2 = patients_dict_T2
      # print(self.patients_lst_T2)
      # lm_group = GetLandmarkGroup(GROUPS_LANDMARKS)
      # available_lm_T2 = GetAvailableLm(self.surface_folder_2,lm_group)
      # print(available_lm_T2)

    
  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)

  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()

  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    self.setParameterNode(self.logic.getParameterNode())

    # Select default input nodes if nothing is selected yet to save a few clicks for the user
    if not self._parameterNode.GetNodeReference("InputVolume"):
      firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
      if firstVolumeNode:
        self._parameterNode.SetNodeReferenceID("InputVolume", firstVolumeNode.GetID())

  def setParameterNode(self, inputParameterNode):
    """
    Set and observe parameter node.
    Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
    """

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    # Update node selectors and sliders
    # self.ui.inputSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputVolume"))
    # self.ui.outputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolume"))
    # self.ui.invertedOutputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolumeInverse"))
    # self.ui.imageThresholdSliderWidget.value = float(self._parameterNode.GetParameter("Threshold"))
    # self.ui.invertOutputCheckBox.checked = (self._parameterNode.GetParameter("Invert") == "true")

    # Update buttons states and tooltips
    if self._parameterNode.GetNodeReference("InputVolume") and self._parameterNode.GetNodeReference("OutputVolume"):
      self.ui.applyButton.toolTip = "Compute output volume"
      self.ui.applyButton.enabled = True
    else:
      self.ui.applyButton.toolTip = "Select input and output volume nodes"
      self.ui.applyButton.enabled = False

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    self._parameterNode.SetNodeReferenceID("InputVolume", self.ui.inputSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("OutputVolume", self.ui.outputSelector.currentNodeID)
    self._parameterNode.SetParameter("Threshold", str(self.ui.imageThresholdSliderWidget.value))
    self._parameterNode.SetParameter("Invert", "true" if self.ui.invertOutputCheckBox.checked else "false")
    self._parameterNode.SetNodeReferenceID("OutputVolumeInverse", self.ui.invertedOutputSelector.currentNodeID)

    self._parameterNode.EndModify(wasModified)


class LMTab:
  def __init__(self,tab_manager,MP_Widget) -> None:
    self.tab_manager = tab_manager
    self.MP_Widget = MP_Widget
    self.widget = qt.QWidget()
    layout = qt.QVBoxLayout(self.widget)

    self.LM_tab_widget = qt.QTabWidget()
    self.LM_tab_widget.minimumSize = qt.QSize(100,200)
    self.LM_tab_widget.maximumSize = qt.QSize(800,400)
    self.LM_tab_widget.setMovable(True)


    buttons_wid = qt.QWidget()
    buttons_layout = qt.QHBoxLayout(buttons_wid)

    layout.addWidget(self.LM_tab_widget)
    layout.addWidget(buttons_wid)
    self.lm_status_dic = {}
    
  def Clear(self):
    self.LM_tab_widget.clear()

  def FillTab(self,lm_dic):
    self.lm_group_dic = lm_dic.copy()
    self.check_box_dic = {}
    self.lm_cb_dic = {}
    for group,lm_lst in self.lm_group_dic.items():
      if group == "Dental":
        for lm in lm_lst:
          if lm not in self.lm_status_dic.keys():
            for lm_type in lm_dic['Landmarks type']:
              self.lm_status_dic[lm+lm_type] = False
              
      elif group != "Landmarks type" and group != "Dental":
        for lm in lm_lst:
          if lm not in self.lm_status_dic.keys():
            self.lm_status_dic[lm] = False

    for group,lm_lst in self.lm_group_dic.items():
      lst_wid = []
      for lm in lm_lst:
        new_cb = qt.QCheckBox(lm)
        self.check_box_dic[new_cb] = lm
        lst_wid.append(new_cb)
      if group == "Dental":
        new_lm_tab = self.GenNewTab(lst_wid,'horizontal')
      else:
        new_lm_tab = self.GenNewTab(lst_wid,'vertical')
      self.LM_tab_widget.insertTab(0,new_lm_tab,group)
    self.LM_tab_widget.currentIndex = 0

    for cb,lm in self.check_box_dic.items():
      if lm not in self.lm_cb_dic.keys():
        self.lm_cb_dic[lm] = [cb]
      else:
        self.lm_cb_dic[lm].append(cb)
    
    for cb,lm in self.check_box_dic.items(): 
      if "Landmarks type" in self.lm_group_dic.keys():
        cb.connect("toggled(bool)", self.UpdateDentalLm)
      else:
        cb.connect("toggled(bool)", self.CheckBox)

  def CheckBox(self, caller=None, event=None):
    for cb,lm in self.check_box_dic.items():
      if self.lm_cb_dic[lm][0].checkState():
        state = True
      else:
        state = False
      if self.lm_status_dic[lm] != state:
        self.UpdateLmSelect(lm,state)

    self.tab_manager.GetLmListManager(self.lm_status_dic)
    self.MP_Widget.GetLmList(self.lm_status_dic)

  def UpdateDentalLm(self):
    selected_type_lst = []
    for lm in self.lm_group_dic["Landmarks type"]:
      if self.lm_cb_dic[lm][0].checkState():
        selected_type_lst.append(lm)
      else:
        if lm in selected_type_lst:
          selected_type_lst.remove(lm)
        
    for lm in self.lm_group_dic["Dental"]:      
      if self.lm_cb_dic[lm][0].checkState():
        state = True
      else:
        state = False
      for typ in self.lm_group_dic["Landmarks type"]:
        if typ in selected_type_lst:
          self.lm_status_dic[lm+typ] = state
        else:
          self.lm_status_dic[lm+typ] = False
    # print(self.lm_status_dic)

    for group,lst_lm in self.lm_group_dic.items():
      if group not in ["Landmarks type","Dental"]:
        for lm in lst_lm:        
          if self.lm_cb_dic[lm][0].checkState():
            state = True
          else:
            state = False
          if self.lm_status_dic[lm] != state:
            self.UpdateLmSelect(lm,state)
          
    self.tab_manager.GetLmListManager(self.lm_status_dic)
    self.MP_Widget.GetLmList(self.lm_status_dic)

  def GenNewTab(self,widget_lst,orientation):
    new_widget = qt.QWidget()
    vb = qt.QVBoxLayout(new_widget)
    scr_box = qt.QScrollArea()
    vb.addWidget(scr_box)
    
    if orientation == 'horizontal':
      wid = qt.QWidget()
      hb2 = qt.QHBoxLayout(wid)
      for widget in widget_lst:
        hb2.addWidget(widget)
      wid.setLayout(hb2)
    
    else:
      wid = qt.QWidget()
      vb2 = qt.QVBoxLayout(wid)
      for widget in widget_lst:
        vb2.addWidget(widget)
      wid.setLayout(vb2)

    scr_box.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOn)
    scr_box.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOn)
    scr_box.setWidgetResizable(True)
    scr_box.setWidget(wid)

    hb_widget = qt.QWidget()
    hb = qt.QHBoxLayout(hb_widget)
    self.buttons_selct_all = qt.QPushButton("Select All")
    self.buttons_clear = qt.QPushButton("Clear")
    hb.addWidget(self.buttons_selct_all)
    hb.addWidget(self.buttons_clear)
    self.buttons_selct_all.connect('clicked()', self.SelectTab)
    self.buttons_clear.connect('clicked()', self.ClearTab)
    vb.addWidget(hb_widget)

    return new_widget

  def UpdateLmSelect(self,lm_id,state):
    for cb in self.lm_cb_dic[lm_id]:
      cb.setChecked(state)
    self.lm_status_dic[lm_id] = state
  
  def Fulltab(self,state):
    idx = self.LM_tab_widget.currentIndex
    group = self.LM_tab_widget.tabText(idx)
    if group == "Landmarks type":
      for typ in self.lm_group_dic["Landmarks type"]:
        self.lm_cb_dic[typ][0].setChecked(state)

    elif group == "Dental" :      
      for dent in self.lm_group_dic["Dental"]:
        self.lm_cb_dic[dent][0].setChecked(state)
    else :
      for lm in self.lm_group_dic[group]:
        self.UpdateLmSelect(lm,state)

  def SelectTab(self):
    self.Fulltab(True)
  
  def ClearTab(self):
    self.Fulltab(False)

class MidPointWidget:
  def __init__(self,ui,tab_manager):
    self.patients_lst_T1 = []
    self.patients_dict_T1 = {}
    self.lst_files_T1 = []
    self.ui = ui
    self.tab_manager = tab_manager

    # self.widget_mp = qt.QWidget()
    hb = self.ui.horizontalLayout_2
    self.label_P1_intro = qt.QLabel('Compute midpoint:')
    self.label_P1_intro.setFixedWidth(140)
    self.label_P1 = qt.QLabel('  P1 :')
    self.label_P1.setFixedWidth(30)
    self.label_P2 = qt.QLabel('  P2 :')
    self.label_P2.setFixedWidth(30)
    self.combo_box_mp_1 = qt.QComboBox()
    self.combo_box_mp_2 = qt.QComboBox()
    self.PB_compute_midpoint = qt.QPushButton("Compute Mid Point")
    widget_lst = [self.label_P1_intro,self.label_P1,self.combo_box_mp_1,self.label_P2,self.combo_box_mp_2,self.PB_compute_midpoint]
    for widget in widget_lst:
      hb.addWidget(widget)
    self.PB_compute_midpoint.connect('clicked()',self.Compute)


  def GetLmList(self,lm_status_dic):
    self.combo_box_mp_1.clear()
    self.combo_box_mp_2.clear()
    
    self.list_lm = []
    for landmark,state in lm_status_dic.items():
      if state == True:
        self.list_lm.append(landmark)
    # print(self.list_lm)
    self.combo_box_mp_1.addItems(self.list_lm)
    self.combo_box_mp_2.addItems(self.list_lm)
  
  def Compute(self):
    self.P1_name = self.combo_box_mp_1.currentText
    self.P2_name = self.combo_box_mp_2.currentText
    self.lst_all_midpoint = []
    for self.patient in self.patients_lst_T1:
      self.midpoint_lst = []
      self.out_path = self.ui.lineEditLandPathT1.text+f'/MidPoints_P{self.patient}.json'
      print(self.out_path)
      self.P1_pos = self.patients_dict_T1[self.patient][self.P1_name]
      self.P2_pos = self.patients_dict_T1[self.patient][self.P2_name]
      self.ComputeMidPoint(np.array(self.P1_pos),np.array(self.P2_pos))
      self.GenControlePoint()
      self.WriteJson()
    
    self.FillTab()
  
  def FillTab(self):
    self.check_box_dic = {}
    self.lm_cb_dic = {}
    group = 'Midpoint'
    lst_wid = []
    for dic in self.lst_all_midpoint:
      new_cb = qt.QCheckBox(dic['label'])
      self.check_box_dic[new_cb] = dic['label']
      lst_wid.append(new_cb)

    new_lm_tab = self.GenNewTab(lst_wid)
    self.LM_tab_widget.insertTab(-1,new_lm_tab,group)
    # self.LM_tab_widget.currentIndex = 0

    for cb,lm in self.check_box_dic.items():
      if lm not in self.lm_cb_dic.keys():
        self.lm_cb_dic[lm] = [cb]
      else:
        self.lm_cb_dic[lm].append(cb)
    
    for cb,lm in self.check_box_dic.items(): 
      cb.connect("toggled(bool)", self.CheckBox)

  def CheckBox(self, caller=None, event=None):
    for cb,lm in self.check_box_dic.items():
      if self.lm_cb_dic[lm][0].checkState():
        state = True
      else:
        state = False
      if self.lm_status_dic[lm] != state:
        self.UpdateLmSelect(lm,state)

    self.tab_manager.GetLmListManager(self.lm_status_dic)
    self.GetLmList(self.lm_status_dic)
  
  def UpdateLmSelect(self,lm_id,state):
    for cb in self.lm_cb_dic[lm_id]:
      cb.setChecked(state)
    self.lm_status_dic[lm_id] = state
  
  def GenNewTab(self,widget_lst):
    new_widget = qt.QWidget()
    vb = qt.QVBoxLayout(new_widget)
    scr_box = qt.QScrollArea()
    vb.addWidget(scr_box)
    
    wid = qt.QWidget()
    vb2 = qt.QVBoxLayout(wid)
    for widget in widget_lst:
      vb2.addWidget(widget)
    wid.setLayout(vb2)

    scr_box.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOn)
    scr_box.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOn)
    scr_box.setWidgetResizable(True)
    scr_box.setWidget(wid)

    return new_widget


  def GenControlePoint(self):
    controle_point = {
      "id": str(1),
      "label": f'Mid_{self.P1_name}-{self.P2_name}_P{self.patient}',
      "description": "",
      "associatedNodeID": "",
      "position": [float(self.mp[0]), float(self.mp[1]), float(self.mp[2])],
      "orientation": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
      "selected": True,
      "locked": True,
      "visibility": True,
      "positionStatus": "preview"
    }
    self.midpoint_lst.append(controle_point)
    self.lst_all_midpoint.append(controle_point)

  def WriteJson(self)
        {
            "type": "Fiducial",
            "coordinateSystem": "LPS",
            "locked": false,
            "labelFormat": "%N-%d",
            "controlPoints": self.midpoint_lst,
            "measurements": [],
            "display": {
                "visibility": false,
                "opacity": 1.0,
                "color": [0.4, 1.0, 0.0],
                "selectedColor": [1.0, 0.5000076295109484, 0.5000076295109484],
                "activeColor": [0.4, 1.0, 0.0],
                "propertiesLabelVisibility": false,
                "pointLabelsVisibility": true,
                "textScale": 3.0,
                "glyphType": "Sphere3D",
                "glyphScale": 1.0,
                "glyphSize": 5.0,
                "useGlyphScale": true,
                "sliceProjection": false,
                "sliceProjectionUseFiducialColor": true,
                "sliceProjectionOutlinedBehindSlicePlane": false,
                "sliceProjectionColor": [1.0, 1.0, 1.0],
                "sliceProjectionOpacity": 0.6,
                "lineThickness": 0.2,
                "lineColorFadingStart": 1.0,
                "lineColorFadingEnd": 10.0,
                "lineColorFadingSaturation": 1.0,
                "lineColorFadingHueOffset": 0.0,
                "handlesInteractive": false,
                "snapMode": "toVisibleSurface"
            }
        }
    ]
    }
    with open(self.out_path, 'w', encoding='utf-8') as f:
      json.dump(file, f, ensure_ascii=False, indent=4)
    f.close
    print('file saved')
  def ComputeMidPoint(self,p1,p2):
    self.mp = (p1 + p2) / 2

class TableView:
  def __init__(self,ui) -> None:
    self.ui = ui
    self.widget = qt.QWidget()
    self.layout = qt.QVBoxLayout(self.widget)

    self.LM_tab_widget = qt.QTabWidget()
    self.LM_tab_widget.minimumSize = qt.QSize(100,200)
    self.LM_tab_widget.maximumSize = qt.QSize(800,400)
    self.LM_tab_widget.setMovable(True)
    self.layout.addWidget(self.LM_tab_widget)
    

    # -------------------------- Gen Tab ---------------------------
    lst_tab = ["Distance","Angle"]
    self.dict_tab = {}
    for idx,tab in enumerate(lst_tab): 
      tableWidget = qt.QTableWidget()
      new_widget = qt.QWidget()
      vb = qt.QVBoxLayout(new_widget)
      scr_box = qt.QScrollArea()
      vb.addWidget(scr_box)

      wid = qt.QWidget()
      vb2 = qt.QVBoxLayout()
      wid.setLayout(vb2)
      
      vb2.addWidget(tableWidget)
      
      scr_box.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOff)
      scr_box.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOff)
      scr_box.setWidgetResizable(True)
      scr_box.setWidget(wid)
      
      self.LM_tab_widget.insertTab(-1,new_widget,tab)
      self.dict_tab[idx] = tableWidget

  def Clear(self):
    self.LM_tab_widget.clear()

class Point:
  def __init__(self,name):
    self.name = name
    self.position = []
    self.group = self.GetTypeLandmark()

  def GetTypeLandmark(self):
    for land_groups in GROUPS_LANDMARKS.items():
      if self.name[:3] in land_groups[1]:
        group = land_groups[0]
      else:
        group = "Other"
    return group

class Line:
  def __init__(self,point1,point2):
    self.name = point1.name + '-' + point2.name
    self.point1 = point1
    self.point2 = point2
    # print(self.point1.position,self.point2.position)
    # self.position = np.array(self.point1.position) - np.array(self.point2.position)

class MeasurePointToPoint:
  def __init__(self,point1,point2,type_m,time):
    self.point1 = point1
    self.point2 = point2
    self.type_m = type_m
    self.time = time
    self.r_l_sign_meaning = ""
    self.a_p_sign_meaning = ""
    self.s_i_sign_meaning = ""

  def compute(self):
    # print(self.point1.position,self.point2.position)
    self.r_l,self.a_p,self.s_i,self.norm = computeDistance(np.array(self.point1.position),np.array(self.point2.position))
    print(self.point1.name,self.point2.name,self.r_l,self.a_p,self.s_i,self.norm)

class MeasurePointToLine:
  def __init__(self,point,line,type_m,time):
    self.point = point
    self.line = line
    self.type_m = type_m
    self.time = time
    # self.dict_patients = {}
    self.r_l_sign_meaning = ""
    self.a_p_sign_meaning = ""
    self.s_i_sign_meaning = ""
    
  def compute(self):
    self.r_l,self.a_p,self.s_i,self.norm = computeLinePoint(np.array(self.line.point1.position),np.array(self.line.point2.position),np.array(self.point.position))

class MeasureDifPlT1T2:
  def __init__(self,measurement_T1,measurement_T2,type_m):
    self.measurement_T1 = measurement_T1
    self.measurement_T2 = measurement_T2
    self.point1 = self.measurement_T1.point
    self.point2 = self.measurement_T2.point
    self.line1 = self.measurement_T1.line
    self.line2 = self.measurement_T2.line
    self.type_m = type_m
    self.r_l_sign_meaning = ""
    self.a_p_sign_meaning = ""
    self.s_i_sign_meaning = ""

  def compute(self):
    self.r_l = self.measurement_T2.r_l - self.measurement_T1.r_l
    self.a_p = self.measurement_T2.a_p - self.measurement_T1.a_p
    self.s_i = self.measurement_T2.s_i - self.measurement_T1.s_i
    self.norm = self.measurement_T2.norm - self.measurement_T1.norm
    self.r_l = round(self.r_l,3)
    self.a_p = round(self.a_p,3)
    self.s_i = round(self.s_i,3)
    self.norm = round(self.norm,3)

class MeasureAngles:
  def __init__(self,line1,line2,type_m,time):
    self.line1 = line1
    self.line2 = line2
    self.type_m = type_m
    self.time = time
    self.yaw_sign_meaning = ""
    self.pitch_sign_meaning = ""
    self.roll_sign_meaning = ""

  def compute(self):
    self.yaw_angle, self.pitch_angle, self.roll_angle = computeAngles(np.array(self.line1.point1.position),np.array(self.line1.point2.position),np.array(self.line2.point1.position),np.array(self.line2.point2.position))

class MeasureDifAngleT1T2:
  def __init__(self,measurement_T1,measurement_T2,type_m):
    self.measurement_T1 = measurement_T1
    self.measurement_T2 = measurement_T2
    self.line1_T1 = self.measurement_T1.line1
    self.line2_T1 = self.measurement_T1.line2
    self.line1_T2 = self.measurement_T2.line1
    self.line2_T2 = self.measurement_T2.line2
    self.type_m = type_m

    self.yaw_sign_meaning = ""
    self.pitch_sign_meaning = ""
    self.roll_sign_meaning = ""

  def compute(self):
    self.yaw_angle = self.measurement_T2.yaw_angle - self.measurement_T1.yaw_angle
    self.pitch_angle = self.measurement_T2.pitch_angle - self.measurement_T1.pitch_angle
    self.roll_angle = self.measurement_T2.roll_angle - self.measurement_T1.roll_angle

class TabLine:
  def __init__(self,measurement):
    self.measurement = measurement
    self.checkBoxItem = qt.QTableWidgetItem()
    self.checkBoxItem.setCheckState(False)
    self.lst_widget = []
    self.lst_widget.append(self.checkBoxItem)

  def gen_widget(self):
    type_measurment_item = qt.QTableWidgetItem(self.measurement.type_m)
    self.lst_widget.append(type_measurment_item)
    
    if self.measurement.type_m in ['Distance between 2 points','Distance between 2 points'+' T1 T2'] :
      P1_item = qt.QTableWidgetItem(self.measurement.point1.name)
      P2_item = qt.QTableWidgetItem(self.measurement.point2.name)
      self.lst_widget.append(P1_item)
      self.lst_widget.append(P2_item)
    
    elif self.measurement.type_m in ['Distance point line','Distance point line T1','Distance point line T2']:
      P1_item = qt.QTableWidgetItem(self.measurement.point.name)
      L_item = qt.QTableWidgetItem(self.measurement.line.name)
      self.lst_widget.append(P1_item)
      self.lst_widget.append(L_item)
    
    elif self.measurement.type_m == 'Distance point line dif T1 T2':
      P1_item = qt.QTableWidgetItem(self.measurement.point1.name+'/'+self.measurement.point2.name)
      L_item = qt.QTableWidgetItem(self.measurement.line1.name+'/'+self.measurement.line2.name)
      self.lst_widget.append(P1_item)
      self.lst_widget.append(L_item)
    
    elif self.measurement.type_m == 'Angle between 2 lines'+' dif T1 T2':
      L_T1_item = qt.QTableWidgetItem(self.measurement.line1_T1.name+'/'+self.measurement.line2_T1.name)
      L_T2_item = qt.QTableWidgetItem(self.measurement.line1_T2.name+'/'+self.measurement.line2_T2.name)
      self.lst_widget.append(L_T1_item)
      self.lst_widget.append(L_T2_item)
    else:
      L1_item = qt.QTableWidgetItem(self.measurement.line1.name)
      L2_item = qt.QTableWidgetItem(self.measurement.line2.name)
      self.lst_widget.append(L1_item)
      self.lst_widget.append(L2_item)

class TabManager:
  def __init__(self,ui,table_view):
    self.ui = ui
    self.widget = qt.QWidget()
    self.layout = qt.QVBoxLayout(self.widget)

    self.delete_button = qt.QPushButton('Delete')
    self.ui.verticalLayout_2.addWidget(self.delete_button)

    self.table_view = table_view
    self.active_tab = 0

    self.patients_lst_T1 = []
    self.patients_dict_T1 = {}
    self.patients_lst_T2 = []
    self.patients_dict_T2 = {}

    # -------------------------- Gen layout add line ---------------------------
    self.vb_measurement = qt.QVBoxLayout()
    self.layout.addLayout(self.vb_measurement)
    self.DWidget = DistanceWidget(self.vb_measurement,self)
    self.AWidget = AnglesWidget(self.vb_measurement,self)
    self.AWidget.WidgetSetHidden(True)
    self.table_view.LM_tab_widget.connect('currentChanged(int)',self.TabSelected)

    # -------------------------- Import/Export measurment ---------------------------
    self.vb_ie = qt.QVBoxLayout()
    self.layout.addLayout(self.vb_ie)
    self.hb_ie = qt.QHBoxLayout()
    self.vb_ie.addLayout(self.hb_ie)
    self.label_ie = qt.QLabel("Import/Export list of measurements :")
    self.label_ie.setFixedWidth(220)
    self.combobox_ie = qt.QComboBox()
    self.combobox_ie.addItems(["None","Import list of measurements","Export list of measurements"])
    self.hb_ie.addWidget(self.label_ie)
    self.hb_ie.addWidget(self.combobox_ie)
    self.layout.addLayout(self.hb_ie)
   
    self.import_widget,self.file_import_button,self.import_line,self.import_button = WidgetImport(self.vb_ie)
    self.export_widget,self.folder_export_button,self.export_line,self.line_edit,self.export_button = WidgetExport(self.vb_ie)
    
    # -------------------------- connect ---------------------------
    
    self.delete_button.connect('clicked()',self.OnDeleteButton)
    self.folder_export_button.connect('clicked()',self.OnExportFolder)
    self.export_button.connect('clicked()',self.OnExportMeasurment)
    self.file_import_button.connect('clicked()',self.OnImportFile)
    self.import_button.connect('clicked()',self.OnImportMeasurment)
    self.ui.folder_save_measurement.connect('clicked()',self.OnSaveMeasurementFolder)
    self.ui.compute_button.connect('clicked()',self.Computations)
    self.combobox_ie.connect('currentIndexChanged(int)',self.DisplayImportExportLayout)

  def TabSelected(self,idx):
    self.active_tab = idx
    if self.active_tab == 0:
      self.DWidget.WidgetSetHidden(False)
      self.AWidget.WidgetSetHidden(True)

    else:
      self.DWidget.WidgetSetHidden(True)
      self.AWidget.WidgetSetHidden(False)

  def DisplayImportExportLayout(self,idx):
    if idx == 0:
      self.export_widget.setHidden(True)
      self.import_widget.setHidden(True)
    elif idx == 1:
      self.export_widget.setHidden(True)
      self.import_widget.setHidden(False)
    else:
      self.import_widget.setHidden(True)
      self.export_widget.setHidden(False)

  def GetLmListManager(self,lm_status_dic):
    self.DWidget.GetLmList(lm_status_dic)
    self.AWidget.GetLmList(lm_status_dic)

  def OnDeleteButton(self):
    if self.active_tab == 0:
      for tab_line in self.DWidget.lst_tab_lines_d:
        state = tab_line.checkBoxItem.checkState()
        if state == 2:
          self.DWidget.lst_measurement_dist.remove(tab_line.measurement)
      self.DWidget.generate_table_distances()
    else:
      for tab_line in self.AWidget.lst_tab_lines_a:
        state = tab_line.checkBoxItem.checkState()
        if state == 2:
          self.AWidget.lst_measurement_angles.remove(tab_line.measurement)
      self.AWidget.generate_table_angles()    

  def OnExportFolder(self):
    self.export_folder = qt.QFileDialog.getExistingDirectory(self.widget,"Select folder")
    if self.export_folder != '':
      self.export_line.setText(self.export_folder)

  def OnExportMeasurment(self):
    csv_columns_dist = ["Type of measurement","Point 1", "Point 2 / Line"]
    csv_columns_angle = ["Type of measurement","Line 1", "Line 2"]
    lst_data_dist_pp = []
    lst_data_dist_pl = []
    lst_data_angl = []
    if len(self.DWidget.lst_measurement_dist)>0:
      for measurement in self.DWidget.lst_measurement_dist:
        if measurement.type_m in ["Distance between 2 points",'Distance between 2 points T1 T2']:
          dict_csv = {"Type of measurement":measurement.type_m,"Point 1":measurement.point1.name,"Point 2 / Line":measurement.point2.name}
          lst_data_dist_pp.append(dict_csv)
        elif measurement.type_m == 'Distance point line dif T1 T2':
          dict_csv = {"Type of measurement":measurement.type_m,"Point 1":measurement.point1.name+'/'+measurement.point2.name,"Point 2 / Line":measurement.line1.name+'/'+measurement.line2.name}
          lst_data_dist_pl.append(dict_csv)
        else:
          dict_csv = {"Type of measurement":measurement.type_m,"Point 1":measurement.point.name,"Point 2 / Line":measurement.line.name}
          lst_data_dist_pl.append(dict_csv)
    if len(self.AWidget.lst_measurement_angles)>0:
      for measurement in self.AWidget.lst_measurement_angles:
        if measurement.type_m in ['Angle between 2 lines','Angle between 2 lines T1','Angle between 2 lines T2']:
          dict_csv = {"Type of measurement":measurement.type_m,"Line 1":measurement.line1.name,"Line 2":measurement.line2.name}  
          lst_data_angl.append(dict_csv)
        else:
          dict_csv = {"Type of measurement":measurement.type_m,"Line 1":measurement.line1_T1.name+'/'+measurement.line2_T1.name,"Line 2":measurement.line1_T2.name+'/'+measurement.line2_T2.name}  
          lst_data_angl.append(dict_csv)

    
    
    with pd.ExcelWriter(f"{self.export_line.text}/{self.line_edit.text}") as writer:
      if len(lst_data_dist_pp)>0:
        df_dist_pp = pd.DataFrame(lst_data_dist_pp,index=list(range(len(lst_data_dist_pp))),columns=list(lst_data_dist_pp[0].keys()))
        df_dist_pp.to_excel(writer,sheet_name="Distance between 2 points",index=False)
      if len(lst_data_dist_pl)>0:
        df_dist_pl = pd.DataFrame(lst_data_dist_pl,index=list(range(len(lst_data_dist_pl))),columns=list(lst_data_dist_pl[0].keys()))
        df_dist_pl.to_excel(writer,sheet_name="Distance point line",index=False)
      if len(lst_data_angl)>0:
        df_angl = pd.DataFrame(lst_data_angl,index=list(range(len(lst_data_angl))),columns=list(lst_data_angl[0].keys()))
        df_angl.to_excel(writer,sheet_name="Angle between 2 lines",index=False)

    # print("Export done")

  def OnImportFile(self):
    self.import_file = qt.QFileDialog.getOpenFileName(self.widget,"Select file")
    if self.import_file != '':
      self.import_line.setText(self.import_file)

  def OnImportMeasurment(self):
    path_file = self.import_file
    wb = openpyxl.load_workbook(path_file)
    names_sheet = wb.sheetnames

    for idx,sheet_name in enumerate(names_sheet):
      ws = wb[sheet_name]
      if idx == 0:
        for idx_row,row in enumerate(ws.iter_rows()):
          if idx_row != 0:
            data_type_of_measurment = row[0].value
            point1 = Point(row[1].value)
            point2 = Point(row[2].value)
            measurement = MeasurePointToPoint(point1,point2,data_type_of_measurment)
            self.DWidget.lst_measurement_dist.append(measurement)
      
      elif idx == 1:
        for idx_row,row in enumerate(ws.iter_rows()):
          if idx_row != 0:
            data_type_of_measurment = row[0].value
            if '/' not in row[2].value:
              point = Point(row[1].value)
              point2 = row[2].value.split('-')[0]
              point3 = row[2].value.split('-')[1]
              line = Line(Point(point2),Point(point3))
              measurement = MeasurePointToLine(point,line,data_type_of_measurment)
              self.DWidget.lst_measurement_dist.append(measurement)
            else:
              measurement_T1 = self.DWidget.lst_measurement_dist[-2]
              measurement_T2 = self.DWidget.lst_measurement_dist[-1]
              measurement = MeasureDifPlT1T2(measurement_T1,measurement_T2,data_type_of_measurment)
              self.DWidget.lst_measurement_dist.append(measurement)

      else:
        for idx_row,row in enumerate(ws.iter_rows()):
          if idx_row != 0:
            data_type_of_measurment = row[0].value
            if '/' not in row[2].value:
              point1 = Point(row[1].value.split('-')[0])
              point2 = Point(row[1].value.split('-')[1])
              point3 = Point(row[2].value.split('-')[0])
              point4 = Point(row[2].value.split('-')[1])
              line1 = Line(point1,point2)
              line2 = Line(point3,point4)
              measurement = MeasureAngles(line1,line2,data_type_of_measurment)
              self.AWidget.lst_measurement_angles.append(measurement)
            else:
              measurement_T1 = self.AWidget.lst_measurement_angles[-2]
              measurement_T2 = self.AWidget.lst_measurement_angles[-1]
              measurement = MeasureDifAngleT1T2(measurement_T1,measurement_T2,data_type_of_measurment)
              self.AWidget.lst_measurement_angles.append(measurement)
      

    self.DWidget.generate_table_distances()
    self.AWidget.generate_table_angles()
    # print("Import done")

  def OnSaveMeasurementFolder(self):
    self.export_measurement_folder = qt.QFileDialog.getExistingDirectory(self.widget,"Select folder")
    if self.export_measurement_folder != '':
      self.ui.export_measurement_line.setText(self.export_measurement_folder)
  
  def SelectedLandmark(self):
    for row in self.big_list:
      cb = row[0]
      if cb.checkState():
        state = True
      else:
        state = False
      if self.status_cb[cb] != state:
        self.UpdateLmSelect(cb,state)
    
  def Computations(self): 

    self.DWidget.lst_compute_dst_pp.clear()
    self.DWidget.lst_compute_dst_pl.clear()
    self.AWidget.lst_compute_angles.clear()
    for self.patient in self.patients_lst_T1:
      self.DWidget.GenerateComputeDstLst(self.patients_dict_T1, self.patients_dict_T2)
      self.AWidget.GenerateComputeDstLstAngle(self.patients_dict_T1,self.patients_dict_T2)

    self.GenMeasurementExcel()

  def GenMeasurementExcel(self):

    full_lst_compute_dst = self.DWidget.lst_compute_dst_pp + self.DWidget.lst_compute_dst_pl + self.AWidget.lst_compute_angles
    if len(full_lst_compute_dst)>0:
      df = pd.DataFrame(full_lst_compute_dst,index=list(range(len(full_lst_compute_dst))),columns=list(full_lst_compute_dst[0].keys()))
    
    if self.ui.export_measurement_line.text == '':
      warningMessage('Missing export measurement folder')  
    elif self.ui.file_measurement_edit == '' or '.xlsx' not in self.ui.file_measurement_edit.text:
      warningMessage('Missing file name or wrong name given') 
    else:
      with pd.ExcelWriter(f"{self.ui.export_measurement_line.text}/{self.ui.file_measurement_edit.text}") as writer:
        if len(full_lst_compute_dst)>0:
          df.to_excel(writer,sheet_name="Measurement",index=False)
          for column in df:
            column_width = max(df[column].astype(str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            writer.sheets["Measurement"].set_column(col_idx, col_idx, column_width)
      self.ui.MeasurementSavedLabel.text = '  MEASUREMENTS SAVED !!'  
      # print('------------------- SAVE MEASUREMENT -------------------')

  
class DistanceWidget:
  def __init__(self,layout,parent):
    self.parent = parent
    self.layout = layout 
    self.index = 0
    self.lst_measurement_dist = []
    self.lst_compute_dst_pp = []
    self.lst_compute_dst_pl = []
    self.state_check_box_T1_T2 = 0

    #  -------------------------------------------------- WIDGETS --------------------------------------------------

    self.distance_widget = qt.QWidget()
    self.hb_add  = qt.QHBoxLayout(self.distance_widget)
    self.layout.addWidget(self.distance_widget)
    self.type_measur_combobox = qt.QComboBox()
    lst_type_meas = ["Distance between 2 points","Distance point line"]
    self.type_measur_combobox.addItems(lst_type_meas)
    self.label_type_meas = qt.QLabel("Type of measurement :")
    self.label_type_meas.setFixedWidth(140)
    self.label_T1_T2 = qt.QLabel("                  T1/T2")
    self.label_T1_T2.setFixedWidth(110)
    self.check_box_T1_T2 = qt.QCheckBox()
    self.add_button_dist = qt.QPushButton("Add")
    self.hb_add.addWidget(self.label_type_meas)
    self.hb_add.addWidget(self.type_measur_combobox)
    self.hb_add.addWidget(self.label_T1_T2)
    self.hb_add.addWidget(self.check_box_T1_T2)
    self.hb_add.addWidget(self.add_button_dist)

    #  -------------------------------------------------- Initialization of measurement widgets --------------------------------------------------

    self.WidgetPP()
    self.WidgetPL()
    self.WidgetPLT2()
    self.DisplayWidget(self.index)
    
    #  -------------------------------------------------- CONNECTIONS --------------------------------------------------
    self.type_measur_combobox.connect('currentIndexChanged(int)', self.DisplayWidget)
    self.add_button_dist.connect('clicked()',self.OnAddButtonDistances)
    self.check_box_T1_T2.connect('stateChanged(int)',self.StateT1T2)

  def WidgetPP(self):
    self.widget_pp = qt.QWidget()
    hb = qt.QHBoxLayout(self.widget_pp)
    self.label_P1 = qt.QLabel('  P1 :')
    self.label_P1.setFixedWidth(30)
    self.label_P2 = qt.QLabel('  P2 :')
    self.label_P2.setFixedWidth(30)
    self.combo_box_pp_1 = qt.QComboBox()
    self.combo_box_pp_2 = qt.QComboBox()
    widget_lst = [self.label_P1,self.combo_box_pp_1,self.label_P2,self.combo_box_pp_2]
    for widget in widget_lst:
        hb.addWidget(widget)
    self.layout.addWidget(self.widget_pp)
  
  def WidgetPL(self):
    self.widget_pl = qt.QWidget()
    hb = qt.QHBoxLayout(self.widget_pl)
    self.label_T1 = qt.QLabel('T1 :')
    self.label_T1.setFixedWidth(40)
    self.label_P1 = qt.QLabel('  P1 :')
    self.label_P1.setFixedWidth(30)
    self.label_L1 = qt.QLabel('  L1 :')
    self.label_L1.setFixedWidth(30)
    self.label_L2 = qt.QLabel('  L2 :')
    self.label_L2.setFixedWidth(30)
    self.combo_box_pl_1 = qt.QComboBox()
    self.combo_box_pl_2 = qt.QComboBox()
    self.combo_box_pl_3 = qt.QComboBox()
    widget_lst = [self.label_T1,self.label_P1,self.combo_box_pl_1,self.label_L1,self.combo_box_pl_2,self.label_L2,self.combo_box_pl_3]
    for widget in widget_lst:
        hb.addWidget(widget)
    self.layout.addWidget(self.widget_pl)
    self.widget_pl.setHidden(True)
  
  def WidgetPLT2(self):
    self.widget_pl_T2 = qt.QWidget()
    hb = qt.QHBoxLayout(self.widget_pl_T2)
    self.label_T2 = qt.QLabel('T2 :')
    self.label_T2.setFixedWidth(40)
    self.label_P1 = qt.QLabel('  P1 :')
    self.label_P1.setFixedWidth(30)
    self.label_L1 = qt.QLabel('  L1 :')
    self.label_L1.setFixedWidth(30)
    self.label_L2 = qt.QLabel('  L2 :')
    self.label_L2.setFixedWidth(30)
    self.combo_box_pl_1_T2 = qt.QComboBox()
    self.combo_box_pl_2_T2 = qt.QComboBox()
    self.combo_box_pl_3_T2 = qt.QComboBox()
    widget_lst = [self.label_T2,self.label_P1,self.combo_box_pl_1_T2,self.label_L1,self.combo_box_pl_2_T2,self.label_L2,self.combo_box_pl_3_T2]
    for widget in widget_lst:
        hb.addWidget(widget)
    self.layout.addWidget(self.widget_pl_T2)
    self.widget_pl_T2.setHidden(True)

  def StateT1T2(self):
    self.state_check_box_T1_T2 = self.check_box_T1_T2.checkState()
    if self.state_check_box_T1_T2 == 2:
      if self.index == 0:
        self.widget_pl_T2.setHidden(True)
      else:
        self.widget_pl_T2.setHidden(False)
    else:
      if self.index == 0:
        self.widget_pl_T2.setHidden(True)
      else:
        self.widget_pl_T2.setHidden(True)

    if self.state_check_box_T1_T2 == 2:
      if self.parent.ui.lineEditLandPathT2.text == '':
        warningMessage('Missing T2 folder')
        self.check_box_T1_T2.setCheckState(Qt.Unchecked)

  def WidgetSetHidden(self,hidden):
    self.distance_widget.setHidden(hidden)
    if hidden:
      self.widget_pp.setHidden(True)
      self.widget_pl.setHidden(True)
      self.widget_pl_T2.setHidden(True)
    else:
      self.DisplayWidget(self.index)
 
  def DisplayWidget(self,idx):
    self.index = idx
    if self.index == 0:
      self.widget_pp.setHidden(False)
      self.widget_pl.setHidden(True)
      self.widget_pl_T2.setHidden(True)
    else:
      self.widget_pp.setHidden(True)
      self.widget_pl.setHidden(False)
      if self.state_check_box_T1_T2 == 2:
        self.widget_pl_T2.setHidden(False)
      else:
        self.widget_pl_T2.setHidden(True)
 
  def GetLmList(self,lm_status_dic):
    self.combo_box_pp_1.clear()
    self.combo_box_pp_2.clear()
    self.combo_box_pl_1.clear()
    self.combo_box_pl_2.clear()
    self.combo_box_pl_3.clear()
    
    self.combo_box_pl_1_T2.clear()
    self.combo_box_pl_2_T2.clear()
    self.combo_box_pl_3_T2.clear()

    self.list_lm = []
    data_type_of_measurment = self.type_measur_combobox.currentText
    for landmark,state in lm_status_dic.items():
      if state == True:
        self.list_lm.append(landmark)

    self.combo_box_pp_1.addItems(self.list_lm)
    self.combo_box_pp_2.addItems(self.list_lm)
    self.combo_box_pl_1.addItems(self.list_lm)
    self.combo_box_pl_2.addItems(self.list_lm)
    self.combo_box_pl_3.addItems(self.list_lm)

    self.combo_box_pl_1_T2.addItems(self.list_lm)
    self.combo_box_pl_2_T2.addItems(self.list_lm)
    self.combo_box_pl_3_T2.addItems(self.list_lm)

  def OnAddButtonDistances(self):
    data_type_of_measurment = self.type_measur_combobox.currentText
    if data_type_of_measurment == "Distance between 2 points" :
      data_cb_1 = self.combo_box_pp_1.currentText
      data_cb_2 = self.combo_box_pp_2.currentText
      point1 = Point(data_cb_1)
      point2 = Point(data_cb_2)
      if self.state_check_box_T1_T2 == 2:
        measurement = MeasurePointToPoint(point1,point2,data_type_of_measurment+' T1 T2','T1/T2')
      else:
        measurement = MeasurePointToPoint(point1,point2,data_type_of_measurment,'T1')

      self.lst_measurement_dist.append(measurement)
      self.generate_table_distances()

    else :
      if self.state_check_box_T1_T2 == 2:
        data_cb_1_T1 = self.combo_box_pl_1.currentText
        data_cb_2_T1 = self.combo_box_pl_2.currentText
        data_cb_3_T1 = self.combo_box_pl_3.currentText
        
        data_cb_1_T2 = self.combo_box_pl_1_T2.currentText
        data_cb_2_T2 = self.combo_box_pl_2_T2.currentText
        data_cb_3_T2 = self.combo_box_pl_3_T2.currentText

        point_T1 = Point(data_cb_1_T1)
        point_T2 = Point(data_cb_1_T2)
        line_T1 = Line(Point(data_cb_2_T1),Point(data_cb_3_T1))
        line_T2 = Line(Point(data_cb_2_T2),Point(data_cb_3_T2))
        time = 'T1/T2'
        measurement_T1 = MeasurePointToLine(point_T1,line_T1,data_type_of_measurment+' T1','T1')
        measurement_T2 = MeasurePointToLine(point_T2,line_T2,data_type_of_measurment+' T2','T2')
        measurement_dif_T1T2 = MeasureDifPlT1T2(measurement_T1,measurement_T2,data_type_of_measurment+' dif T1 T2')
        self.lst_measurement_dist.append(measurement_T1)
        self.lst_measurement_dist.append(measurement_T2)
        self.lst_measurement_dist.append(measurement_dif_T1T2)
        self.generate_table_distances()
      else:
        data_cb_1 = self.combo_box_pl_1.currentText
        data_cb_2 = self.combo_box_pl_2.currentText
        data_cb_3 = self.combo_box_pl_3.currentText
        point = Point(data_cb_1)
        line = Line(Point(data_cb_2),Point(data_cb_3))
        measurement = MeasurePointToLine(point,line,data_type_of_measurment,'T1')
        self.lst_measurement_dist.append(measurement)
        self.generate_table_distances()

  def generate_table_distances(self):
    self.lst_tab_lines_d = []
    self.parent.table_view.dict_tab[0].clearContents()
    columnLabels = ["check box","type of measurement","point 1", "point 2 / Line"]
    self.parent.table_view.dict_tab[0].setColumnCount(len(columnLabels))
    self.parent.table_view.dict_tab[0].setHorizontalHeaderLabels(columnLabels)
    self.parent.table_view.dict_tab[0].resizeColumnsToContents()
    self.parent.table_view.dict_tab[0].setRowCount(len(self.lst_measurement_dist))
    for measurement in self.lst_measurement_dist:
      tab_line = TabLine(measurement)
      tab_line.gen_widget()
      self.lst_tab_lines_d.append(tab_line)
    for row in range(len(self.lst_tab_lines_d)):
      for col in range(len(columnLabels)):
       self.parent.table_view.dict_tab[0].setItem(row,col,self.lst_tab_lines_d[row].lst_widget[col])
  
  def GenerateComputeDstLst(self,patients_dict_T1,patients_dict_T2):
    for measurement in self.lst_measurement_dist:
      if len(self.lst_measurement_dist)>0:
        dict_patient_measurement = {}
        if measurement.type_m in ['Distance between 2 points','Distance between 2 points'+' T1 T2'] :
          measurement.point1.position = patients_dict_T1[self.parent.patient][measurement.point1.name]
          # print(measurement.point1.name, ':', measurement.point1.position)
          if measurement.time == 'T1/T2':
            measurement.point2.position = patients_dict_T2[self.parent.patient][measurement.point2.name]
            # print(measurement.point2.name, ':', measurement.point2.position)
          else:
            measurement.point2.position = patients_dict_T1[self.parent.patient][measurement.point2.name]
            # print(measurement.point2.name, ':', measurement.point2.position)

          measurement.compute()
          SignManager(measurement)

          dict_patient_measurement["Patient"] = os.path.basename(self.parent.patient).split('.')[0]
          dict_patient_measurement["Type of measurement"] = measurement.type_m
          dict_patient_measurement["Landmark"] = measurement.point1.name + '-' + measurement.point2.name
          dict_patient_measurement["R-L Component"] = str(abs(measurement.r_l))+'  '+measurement.r_l_sign_meaning
          dict_patient_measurement["A-P Component"] = str(abs(measurement.a_p))+'  '+measurement.a_p_sign_meaning
          dict_patient_measurement["S-I Component"] = str(abs(measurement.s_i))+'  '+measurement.s_i_sign_meaning
          dict_patient_measurement["3D Distance"] = measurement.norm
          dict_patient_measurement["Yaw Component"] = 'x'
          dict_patient_measurement["Pitch Component"] = 'x'
          dict_patient_measurement["Roll Component"] = 'x'
          self.lst_compute_dst_pp.append(dict_patient_measurement)

        elif measurement.type_m in ['Distance point line','Distance point line T1','Distance point line T2']:
          if measurement.time == 'T1':
            measurement.point.position = patients_dict_T1[self.parent.patient][measurement.point.name]
            measurement.line.point1.position = patients_dict_T1[self.parent.patient][measurement.line.point1.name]
            measurement.line.point2.position = patients_dict_T1[self.parent.patient][measurement.line.point2.name]
          else:
            measurement.point.position = patients_dict_T2[self.parent.patient][measurement.point.name]
            measurement.line.point1.position = patients_dict_T2[self.parent.patient][measurement.line.point1.name]
            measurement.line.point2.position = patients_dict_T2[self.parent.patient][measurement.line.point2.name]
          
          measurement.compute()
          SignManager(measurement)

          dict_patient_measurement["Patient"] = os.path.basename(self.parent.patient).split('.')[0]
          dict_patient_measurement["Type of measurement"] = measurement.type_m
          dict_patient_measurement["Landmark"] = measurement.point.name + '-' + measurement.line.name
          dict_patient_measurement["R-L Component"] = str(abs(measurement.r_l))+'  '+measurement.r_l_sign_meaning
          dict_patient_measurement["A-P Component"] = str(abs(measurement.a_p))+'  '+measurement.a_p_sign_meaning
          dict_patient_measurement["S-I Component"] = str(abs(measurement.s_i))+'  '+measurement.s_i_sign_meaning
          dict_patient_measurement["3D Distance"] = measurement.norm
          dict_patient_measurement["Yaw Component"] = 'x'
          dict_patient_measurement["Pitch Component"] = 'x'
          dict_patient_measurement["Roll Component"] = 'x'
          self.lst_compute_dst_pl.append(dict_patient_measurement)
          
        else: 
          measurement.point1.position = patients_dict_T1[self.parent.patient][measurement.point1.name]
          measurement.point2.position = patients_dict_T2[self.parent.patient][measurement.point2.name]
          measurement.line1.point1.position = patients_dict_T1[self.parent.patient][measurement.line1.point1.name]
          measurement.line2.point1.position = patients_dict_T2[self.parent.patient][measurement.line2.point1.name]
          measurement.line1.point2.position = patients_dict_T1[self.parent.patient][measurement.line1.point2.name]
          measurement.line2.point2.position = patients_dict_T2[self.parent.patient][measurement.line2.point2.name]


          measurement.compute()
          SignManager(measurement)

          dict_patient_measurement["Patient"] = os.path.basename(self.parent.patient).split('.')[0]
          dict_patient_measurement["Type of measurement"] = measurement.type_m
          dict_patient_measurement["Landmark"] = measurement.point1.name + '-' + measurement.line1.name+'/'+measurement.point2.name + '-' + measurement.line2.name
          dict_patient_measurement["R-L Component"] = str(measurement.r_l)
          dict_patient_measurement["A-P Component"] = str(measurement.a_p)
          dict_patient_measurement["S-I Component"] = str(measurement.s_i)
          dict_patient_measurement["3D Distance"] = measurement.norm
          dict_patient_measurement["Yaw Component"] = 'x'
          dict_patient_measurement["Pitch Component"] = 'x'
          dict_patient_measurement["Roll Component"] = 'x'
          self.lst_compute_dst_pl.append(dict_patient_measurement)

        
class AnglesWidget:
  def __init__(self,layout,parent):
    self.parent = parent
    self.layout = layout
    self.index = 0
    self.lst_measurement_angles = []
    self.lst_compute_angles = []
    self.state_check_box_T1_T2 = 0

    #  -------------------------------------------------- WIDGETS --------------------------------------------------

    self.widget_a = qt.QWidget()
    self.hb_add  = qt.QHBoxLayout(self.widget_a) 
    self.layout.addWidget(self.widget_a)
    self.type_measur_combobox = qt.QComboBox()
    lst_type_meas = ["Angle between 2 lines"]
    self.type_measur_combobox.addItems(lst_type_meas)
    self.label_type_meas = qt.QLabel("Type of measurement")
    self.label_type_meas.setFixedWidth(140)
    self.label_T1_T2 = qt.QLabel("                  T1/T2")
    self.label_T1_T2.setFixedWidth(110)
    self.check_box_T1_T2 = qt.QCheckBox()
    self.add_button_angl = qt.QPushButton("Add")
    self.hb_add.addWidget(self.label_type_meas)
    self.hb_add.addWidget(self.type_measur_combobox)
    self.hb_add.addWidget(self.label_T1_T2)
    self.hb_add.addWidget(self.check_box_T1_T2)
    self.hb_add.addWidget(self.add_button_angl)

    #  -------------------------------------------------- Initialization of measurement widgets --------------------------------------------------
    self.WidgetAnglesT1()
    self.WidgetAnglesT2()
    self.DisplayWidget(self.index)
    
    #  -------------------------------------------------- CONNECTIONS --------------------------------------------------
    self.type_measur_combobox.connect('currentIndexChanged(int)', self.DisplayWidget)
    self.add_button_angl.connect('clicked()',self.OnAddButtonAngles)
    self.check_box_T1_T2.connect('stateChanged(int)',self.StateT1T2)

  def WidgetAnglesT1(self):
    self.widget_angle_T1 = qt.QWidget()
    hb = qt.QHBoxLayout(self.widget_angle_T1)
    self.label_T1 = qt.QLabel('T1 :')
    self.label_T1.setFixedWidth(40)
    self.label_angle_P1_T1 = qt.QLabel('  P1 :')
    self.label_angle_P1_T1.setFixedWidth(30)
    self.label_angle_P2_T1 = qt.QLabel('  P2 :')
    self.label_angle_P2_T1.setFixedWidth(30)
    self.label_angle_P3_T1 = qt.QLabel('  P3 :')
    self.label_angle_P3_T1.setFixedWidth(30)
    self.label_angle_P4_T1 = qt.QLabel('  P4 :')
    self.label_angle_P4_T1.setFixedWidth(30)
    self.combo_box_1_angle_T1 = qt.QComboBox()
    self.combo_box_2_angle_T1 = qt.QComboBox()
    self.combo_box_3_angle_T1 = qt.QComboBox()
    self.combo_box_4_angle_T1 = qt.QComboBox()
    widget_lst = [self.label_T1,self.label_angle_P1_T1,self.combo_box_1_angle_T1,self.label_angle_P2_T1,self.combo_box_2_angle_T1,self.label_angle_P3_T1,self.combo_box_3_angle_T1,self.label_angle_P4_T1,self.combo_box_4_angle_T1]
    for widget in widget_lst:
        hb.addWidget(widget)
    self.layout.addWidget(self.widget_angle_T1)

  def WidgetAnglesT2(self):
    self.widget_angle_T2 = qt.QWidget()
    hb = qt.QHBoxLayout(self.widget_angle_T2)
    self.label_T2 = qt.QLabel('T2 :')
    self.label_T2.setFixedWidth(40)
    self.label_angle_P1_T2 = qt.QLabel('  P1 :')
    self.label_angle_P1_T2.setFixedWidth(30)
    self.label_angle_P2_T2 = qt.QLabel('  P2 :')
    self.label_angle_P2_T2.setFixedWidth(30)
    self.label_angle_P3_T2 = qt.QLabel('  P3 :')
    self.label_angle_P3_T2.setFixedWidth(30)
    self.label_angle_P4_T2 = qt.QLabel('  P4 :')
    self.label_angle_P4_T2.setFixedWidth(30)
    self.combo_box_1_angle_T2 = qt.QComboBox()
    self.combo_box_2_angle_T2 = qt.QComboBox()
    self.combo_box_3_angle_T2 = qt.QComboBox()
    self.combo_box_4_angle_T2 = qt.QComboBox()
    widget_lst = [self.label_T2,self.label_angle_P1_T2,self.combo_box_1_angle_T2,self.label_angle_P2_T2,self.combo_box_2_angle_T2,self.label_angle_P3_T2,self.combo_box_3_angle_T2,self.label_angle_P4_T2,self.combo_box_4_angle_T2]
    for widget in widget_lst:
        hb.addWidget(widget)
    self.layout.addWidget(self.widget_angle_T2)
    self.widget_angle_T2.setHidden(True)

  def StateT1T2(self):
    self.state_check_box_T1_T2 = self.check_box_T1_T2.checkState()
    if self.state_check_box_T1_T2 == 2:
      if self.idx == 0:
        self.widget_angle_T2.setHidden(False)
      else:
        self.widget_angle_T2.setHidden(True)
    else:
      self.widget_angle_T2.setHidden(True)
    
    if self.state_check_box_T1_T2 == 2:
      if self.parent.ui.lineEditLandPathT2.text == '':
        warningMessage('Missing T2 folder')
        self.check_box_T1_T2.setCheckState(Qt.Unchecked)

  def WidgetSetHidden(self,hidden):
    self.widget_a.setHidden(hidden)
    if hidden:
      self.widget_angle_T1.setHidden(True)
      self.widget_angle_T2.setHidden(True)    
    else:
      self.DisplayWidget(self.index)

  def DisplayWidget(self,idx): 
    self.idx = idx   
    if self.idx == 0:
      self.widget_angle_T1.setHidden(False)
      if self.state_check_box_T1_T2 == 2:
        self.widget_angle_T2.setHidden(False)
      else:
        self.widget_angle_T2.setHidden(True)
    else:
      self.widget_angle_T1.setHidden(True)
      self.widget_angle_T2.setHidden(True)

  def GetLmList(self,lm_status_dic):
    self.combo_box_1_angle_T1.clear()
    self.combo_box_2_angle_T1.clear()
    self.combo_box_3_angle_T1.clear()
    self.combo_box_4_angle_T1.clear()
    self.combo_box_1_angle_T2.clear()
    self.combo_box_2_angle_T2.clear()
    self.combo_box_3_angle_T2.clear()
    self.combo_box_4_angle_T2.clear()

    self.list_lm = []
    data_type_of_measurment = self.type_measur_combobox.currentText
    for landmark,state in lm_status_dic.items():
      if state == True:
        self.list_lm.append(landmark)

    self.combo_box_1_angle_T1.addItems(self.list_lm)
    self.combo_box_2_angle_T1.addItems(self.list_lm)
    self.combo_box_3_angle_T1.addItems(self.list_lm)
    self.combo_box_4_angle_T1.addItems(self.list_lm)
    self.combo_box_1_angle_T2.addItems(self.list_lm)
    self.combo_box_2_angle_T2.addItems(self.list_lm)
    self.combo_box_3_angle_T2.addItems(self.list_lm)
    self.combo_box_4_angle_T2.addItems(self.list_lm)
  
  def OnAddButtonAngles(self):
    data_type_of_measurement = self.type_measur_combobox.currentText
    if self.state_check_box_T1_T2 == 2:
      data_cb_1_T1 = self.combo_box_1_angle_T1.currentText
      data_cb_2_T1 = self.combo_box_2_angle_T1.currentText
      data_cb_3_T1 = self.combo_box_3_angle_T1.currentText
      data_cb_4_T1 = self.combo_box_4_angle_T1.currentText
      
      data_cb_1_T2 = self.combo_box_1_angle_T2.currentText
      data_cb_2_T2 = self.combo_box_2_angle_T2.currentText
      data_cb_3_T2 = self.combo_box_3_angle_T2.currentText
      data_cb_4_T2 = self.combo_box_4_angle_T2.currentText

      line1_T1 = Line(Point(data_cb_1_T1),Point(data_cb_2_T1))
      line2_T1 = Line(Point(data_cb_3_T1),Point(data_cb_4_T1))
      line1_T2 = Line(Point(data_cb_1_T2),Point(data_cb_2_T2))
      line2_T2 = Line(Point(data_cb_3_T2),Point(data_cb_4_T2))
      measurement_T1 = MeasureAngles(line1_T1,line2_T1,data_type_of_measurement+' T1','T1')
      measurement_T2 = MeasureAngles(line1_T2,line2_T2,data_type_of_measurement+' T2','T2')
      measurement_dif_T1T2 = MeasureDifAngleT1T2(measurement_T1,measurement_T2,data_type_of_measurement+' dif T1 T2')
      self.lst_measurement_angles.append(measurement_T1)
      self.lst_measurement_angles.append(measurement_T2)
      self.lst_measurement_angles.append(measurement_dif_T1T2)
      self.generate_table_angles()

    else:
      data_cb_1 = self.combo_box_1_angle_T1.currentText
      data_cb_2 = self.combo_box_2_angle_T1.currentText
      data_cb_3 = self.combo_box_3_angle_T1.currentText
      data_cb_4 = self.combo_box_4_angle_T1.currentText
      line1 = Line(Point(data_cb_1),Point(data_cb_2))
      line2 = Line(Point(data_cb_3),Point(data_cb_4))
      measurement = MeasureAngles(line1,line2,data_type_of_measurement,'T1')
      self.lst_measurement_angles.append(measurement)
      self.generate_table_angles()

  def generate_table_angles(self):
    self.lst_tab_lines_a = []
    self.parent.table_view.dict_tab[1].clearContents()
    columnLabels = ["check box","type of measurement","Line 1", "Line 2"]
    self.parent.table_view.dict_tab[1].setColumnCount(len(columnLabels))
    self.parent.table_view.dict_tab[1].setHorizontalHeaderLabels(columnLabels)
    self.parent.table_view.dict_tab[1].resizeColumnsToContents()
    self.parent.table_view.dict_tab[1].setRowCount(len(self.lst_measurement_angles))
    for measurement in self.lst_measurement_angles:
      tab_line = TabLine(measurement)
      tab_line.gen_widget()
      self.lst_tab_lines_a.append(tab_line)
    for row in range(len(self.lst_tab_lines_a)):
      for col in range(len(columnLabels)):
       self.parent.table_view.dict_tab[1].setItem(row,col,self.lst_tab_lines_a[row].lst_widget[col])

  def GenerateComputeDstLstAngle(self,patients_dict_T1,patients_dict_T2):
    for measurement in self.lst_measurement_angles:
      if len(self.lst_measurement_angles)>0: 
        dict_patient_measurement = {}
        if measurement.type_m in ['Angle between 2 lines','Angle between 2 lines T1','Angle between 2 lines T2']:
          if measurement.time == 'T1':
            measurement.line1.point1.position = patients_dict_T1[self.parent.patient][measurement.line1.point1.name]
            measurement.line1.point2.position = patients_dict_T1[self.parent.patient][measurement.line1.point2.name]
            measurement.line2.point1.position = patients_dict_T1[self.parent.patient][measurement.line2.point1.name]
            measurement.line2.point2.position = patients_dict_T1[self.parent.patient][measurement.line2.point2.name]
                     
          else:
            measurement.line1.point1.position = patients_dict_T2[self.parent.patient][measurement.line1.point1.name]
            measurement.line1.point2.position = patients_dict_T2[self.parent.patient][measurement.line1.point2.name]
            measurement.line2.point1.position = patients_dict_T2[self.parent.patient][measurement.line2.point1.name]
            measurement.line2.point2.position = patients_dict_T2[self.parent.patient][measurement.line2.point2.name]

          measurement.compute()
          SignManager(measurement)

          dict_patient_measurement["Patient"] = os.path.basename(self.parent.patient).split('.')[0]
          dict_patient_measurement["Type of measurement"] = measurement.type_m
          dict_patient_measurement["Landmark"] = measurement.line1.name + '-' + measurement.line2.name
          dict_patient_measurement["R-L Component"] = 'x'
          dict_patient_measurement["A-P Component"] = 'x'
          dict_patient_measurement["S-I Component"] = 'x'
          dict_patient_measurement["3D Distance"] = 'x'
          dict_patient_measurement["Yaw Component"] = str(abs(measurement.yaw_angle))+'  '+measurement.yaw_sign_meaning
          dict_patient_measurement["Pitch Component"] = str(abs(measurement.pitch_angle))+'  '+measurement.pitch_sign_meaning
          dict_patient_measurement["Roll Component"] = str(abs(measurement.roll_angle))+'  '+measurement.roll_sign_meaning
          self.lst_compute_angles.append(dict_patient_measurement)

        else:  
          measurement.line1_T1.point1.position = patients_dict_T1[self.parent.patient][measurement.line1_T1.point1.name]
          measurement.line1_T1.point2.position = patients_dict_T1[self.parent.patient][measurement.line1_T1.point2.name]
          measurement.line2_T1.point1.position = patients_dict_T1[self.parent.patient][measurement.line2_T1.point1.name]
          measurement.line2_T1.point2.position = patients_dict_T1[self.parent.patient][measurement.line2_T1.point2.name]
          measurement.line1_T2.point1.position = patients_dict_T2[self.parent.patient][measurement.line1_T2.point1.name]
          measurement.line1_T2.point2.position = patients_dict_T2[self.parent.patient][measurement.line1_T2.point2.name]
          measurement.line2_T2.point1.position = patients_dict_T2[self.parent.patient][measurement.line2_T2.point1.name]
          measurement.line2_T2.point2.position = patients_dict_T2[self.parent.patient][measurement.line2_T2.point2.name]
          
          measurement.compute()
          SignManager(measurement)

          dict_patient_measurement["Patient"] = os.path.basename(self.parent.patient).split('.')[0]
          dict_patient_measurement["Type of measurement"] = measurement.type_m
          dict_patient_measurement["Landmark"] = measurement.line1_T1.name + '-' + measurement.line2_T1.name +' / ' + measurement.line1_T2.name + '-' + measurement.line2_T2.name
          dict_patient_measurement["R-L Component"] = 'x'
          dict_patient_measurement["A-P Component"] = 'x'
          dict_patient_measurement["S-I Component"] = 'x'
          dict_patient_measurement["3D Distance"] = 'x'
          dict_patient_measurement["Yaw Component"] = str(abs(measurement.yaw_angle))+'  '+measurement.yaw_sign_meaning
          dict_patient_measurement["Pitch Component"] = str(abs(measurement.pitch_angle))+'  '+measurement.pitch_sign_meaning
          dict_patient_measurement["Roll Component"] = str(abs(measurement.roll_angle))+'  '+measurement.roll_sign_meaning
          self.lst_compute_angles.append(dict_patient_measurement)



# -------------------------- Gen layout import/export ---------------------------
def WidgetExport(layout): 
  export_widget = qt.QWidget()  
  hb = qt.QHBoxLayout(export_widget)
  folder_export_button = qt.QPushButton("Folder export")
  export_line = qt.QLineEdit()
  label = qt.QLabel("Output file name")
  line_edit = qt.QLineEdit("measurement.xlsx")
  export_button = qt.QPushButton("Export measurement")
  widget_lst = [folder_export_button,export_line,label,line_edit,export_button]
  for widget in widget_lst:
      hb.addWidget(widget)

  layout.addWidget(export_widget)
  export_widget.setHidden(True)

  return export_widget,folder_export_button,export_line,line_edit,export_button

def WidgetImport(layout):
  import_widget = qt.QWidget()
  hb_e = qt.QHBoxLayout(import_widget)
  file_import_button = qt.QPushButton("File import")
  import_line = qt.QLineEdit()
  import_button = qt.QPushButton("Import measurment")
  
  widget_import_lst = [file_import_button,import_line,import_button]
  for widget in widget_import_lst:
      hb_e.addWidget(widget)
  layout.addWidget(import_widget)
  import_widget.setHidden(True)
  return import_widget,file_import_button,import_line,import_button

def GetAvailableLm(mfold,lm_group):
  All_landmarks = GetAllLandmarks(mfold)
  available_lm = {"Other":[]}
  for lm in All_landmarks:
    if lm in lm_group.keys():
      group = lm_group[lm]
    else:
      group = "Other"

    if group not in available_lm.keys():
      available_lm[group] = [lm]
    else:
      available_lm[group].append(lm)

  return available_lm

def GetLandmarkGroup(group_landmark):
  lm_group = {}
  for group,labels in group_landmark.items():
    for label in labels:
      lm_group[label] = group
  return lm_group

def GetAllLandmarks(dir_path):
  All_landmarks = []
  normpath = os.path.normpath("/".join([dir_path, '**', '']))
  for img_fn in sorted(glob.iglob(normpath, recursive=True)):
    if os.path.isfile(img_fn) and ".json" in img_fn:
      json_file = pd.read_json(img_fn)
      markups = json_file.loc[0,'markups']
      controlPoints = markups['controlPoints']
      for i in range(len(controlPoints)):
        if "Rename" in img_fn:
          label = controlPoints[i]["label"][3:]
          tooth = controlPoints[i]["label"][:3]
          if label not in All_landmarks:
            All_landmarks.append(label)
          if tooth not in  All_landmarks:
            All_landmarks.append(tooth)
        else :
          label = controlPoints[i]["label"]
          if label not in All_landmarks:
            All_landmarks.append(label)

  return All_landmarks

def CreateDicPatients(dir_path):
  patients_dict = {}
  patients_lst = []
  lst_files = []
  normpath = os.path.normpath("/".join([dir_path, '**', '']))
  for jsonfile in sorted(glob.iglob(normpath, recursive=True)):
    if os.path.isfile(jsonfile) and ".json" in jsonfile:
      lst_files.append(jsonfile)
      patient = os.path.basename(jsonfile).split('_')[0]
      if patient not in patients_lst:
        patients_lst.append(patient)
      if patient not in patients_dict:
        patients_dict[patient] = {}
      json_file = pd.read_json(jsonfile)
      markups = json_file.loc[0,'markups']
      controlPoints = markups['controlPoints']
      for i in range(len(controlPoints)):
        landmark_name = controlPoints[i]["label"]
        position = controlPoints[i]["position"]
        patients_dict[patient][landmark_name] = position
  
  return patients_lst,patients_dict,lst_files

def warningMessage(message):
    messageBox = ctk.ctkMessageBox()
    messageBox.setWindowTitle(" /!\ WARNING /!\ ")
    messageBox.setIcon(messageBox.Warning)
    messageBox.setText(message)
    messageBox.setStandardButtons(messageBox.Ok)
    messageBox.exec_()

# -------------------------- Computation ---------------------------
def reject(vec, axis):
  vec = np.asarray(vec)
  axis = np.asarray(axis)

  return vec - axis * (np.dot(vec, axis) / np.dot(axis, axis))

def computeDistance(point1_coord, point2_coord):
  delta = point2_coord - point1_coord
  norm = np.linalg.norm(delta)

  return round(-delta[0],3),round(-delta[1],3),round(delta[2],3),round(norm,3)   
  
def computeLinePoint(line1, line2, point):
  if np.allclose(line1, line2, atol=1e-5):
    delta = point - line1
  else:
    delta = reject(
      point - line2,
      line1 - line2,
    )
  norm = np.linalg.norm(delta)
  return round(-delta[0],3),round(-delta[1],3),round(delta[2],3),round(norm,3)

def computeAngle(line1, line2, axis):
  mask = [True] * 3
  mask[axis] = False
  line1 = line1[mask]
  line2 = line2[mask]

  norm1 = np.linalg.norm(line1)
  norm2 = np.linalg.norm(line2)

  matrix = np.array([line1, line2])
  det = np.linalg.det(matrix)
  radians = np.arcsin(det / norm1 / norm2)
  return np.degrees(radians)

def computeAngles(point1, point2, point3, point4):
  line1 = point2 - point1
  line2 = point4 - point3
  axes = [
      2,  # axis=S; axial; for yaw
      0,  # axis=R; saggital; for pitch
      1,  # axis=A; coronal; for roll
  ]
  result = []
  for axis in axes:
    value = computeAngle(line1, line2, axis)
    result.append(round(value,3))

  return result[0],-result[1],-result[2]

# -------------------------- Sign Meaning ---------------------------
upper_right_back = ['UR8','UR7','UR6','UR5','UR4','UR3']
upper_right_front = ['UR1','UR2']
upper_left_back = ['UL8','UL7','UL6','UL5','UL4','UL3']
upper_left_front = ['UL1','UL2']
lower_right_back = ['LR8','LR7','LR6','LR5','LR4','LR3']
lower_right_front = ['LR1','LR2']
lower_left_back = ['LL8','LL7','LL6','LL5','LL4','LL3']
lower_left_front = ['LL1','LL2']

def SignManager(measurement):
  if measurement.type_m in ['Distance between 2 points','Distance between 2 points T1 T2']:
    if measurement.point1.name[:3] and measurement.point2.name[:3] in GROUPS_LANDMARKS["Dental"]:
      print('dental')
      measurement_point1_name = measurement.point1.name[:3]
      measurement_point2_name = measurement.point2.name[:3]
      lst_measurement = [measurement_point1_name,measurement_point2_name]
      SignMeaningDentalDst(measurement,lst_measurement)
    else:
      SignMeaningDist(measurement)
  
  elif measurement.type_m in ['Distance point line','Distance point line T1','Distance point line T2','Distance point line dif T1 T2']:
    # measurement_point1_name = measurement.point.name[:3]
    # measurement_point2_name = measurement.line.point1.name[:3]
    # measurement_point3_name = measurement.line.point1.name[:3]
    # if measurement_point1_name and measurement_point2_name and measurement_point3_name in GROUPS_LANDMARKS["Dental"]:
    #   print('dental')
    #   lst_measurement = [measurement_point1_name,measurement_point2_name,measurement_point3_name]
    #   SignMeaningDentalDst(measurement,lst_measurement)
    # else:
    SignMeaningDist(measurement)

  elif measurement.type_m == 'Distance point line dif T1 T2':
    measurement.r_l_sign_meaning = ""
    measurement.a_p_sign_meaning = ""
    measurement.s_i_sign_meaning = "" 

  elif measurement.type_m == ['Angle between 2 lines','Angle between 2 lines T1','Angle between 2 lines T2']:
    measurement_point1_name = measurement.line1.point1.name[:3]
    measurement_point2_name = measurement.line1.point2.name[:3]
    measurement_point3_name = measurement.line2.point1.name[:3]
    measurement_point4_name = measurement.line2.point2.name[:3]
    if measurement_point1_name and measurement_point2_name and measurement_point3_name and measurement_point4_name in GROUPS_LANDMARKS["Dental"]:
      lst_measurement = [measurement_point1_name,measurement_point2_name,measurement_point3_name,measurement_point4_name]
      SignMeaningDentalAngle(measurement,lst_measurement)
    else:
      measurement.yaw_sign_meaning = ""
      measurement.pitch_sign_meaning = "" 
      measurement.roll_sign_meaning = ""
  else:
    measurement.yaw_sign_meaning = ""
    measurement.pitch_sign_meaning = "" 
    measurement.roll_sign_meaning = ""

def SignMeaningDist(measurement):
  if measurement.r_l>0:
    measurement.r_l_sign_meaning = "R" #Right
  else:
    measurement.r_l_sign_meaning = "L" #Left

  if measurement.a_p>0:
    measurement.a_p_sign_meaning = "A" #Anterior
  else:
    measurement.a_p_sign_meaning = "P" #Posterior

  if measurement.s_i>0:
    measurement.s_i_sign_meaning = "S" #Superior
  else:
    measurement.s_i_sign_meaning = "I" #Inferior

def SignMeaningDentalDst(measurement,lst_measurement):
  if not False in [elem in upper_right_back for elem in lst_measurement]:
    if measurement.r_l>0:
      measurement.r_l_sign_meaning = "B"
    else:
      measurement.r_l_sign_meaning = "L"
  
    if measurement.a_p>0:
      measurement.a_p_sign_meaning = "M"
    else:
      measurement.a_p_sign_meaning = "D"

    if measurement.s_i>0:
      measurement.s_i_sign_meaning = "I"
    else:
      measurement.s_i_sign_meaning = "E"

  elif not False in [elem in upper_right_front for elem in lst_measurement]:
    if measurement.r_l>0:
      measurement.r_l_sign_meaning = "D"
    else:
      measurement.r_l_sign_meaning = "M"

    if measurement.a_p>0:
      measurement.a_p_sign_meaning = "B"
    else:
      measurement.a_p_sign_meaning = "L"

    if measurement.s_i>0:
      measurement.s_i_sign_meaning = "I"
    else:
      measurement.s_i_sign_meaning = "E"
  
  elif not False in [elem in upper_left_back for elem in lst_measurement]:
    if measurement.r_l>0:
      measurement.r_l_sign_meaning = "L"
    else:
      measurement.r_l_sign_meaning = "B"

    if measurement.a_p>0:
      measurement.a_p_sign_meaning = "M"
    else:
      measurement.a_p_sign_meaning = "D"

    if measurement.s_i>0:
      measurement.s_i_sign_meaning = "I"
    else:
      measurement.s_i_sign_meaning = "E"

  elif not False in [elem in upper_left_front for elem in lst_measurement]:
    if measurement.r_l>0:
      measurement.r_l_sign_meaning = "M"
    else:
      measurement.r_l_sign_meaning = "D"

    if measurement.a_p>0:
      measurement.a_p_sign_meaning = "B"
    else:
      measurement.a_p_sign_meaning = "L"

    if measurement.s_i>0:
      measurement.s_i_sign_meaning = "I"
    else:
      measurement.s_i_sign_meaning = "E"

  elif not False in [elem in lower_right_back for elem in lst_measurement]:
    if measurement.r_l>0:
      measurement.r_l_sign_meaning = "B"
    else:
      measurement.r_l_sign_meaning = "L"

    if measurement.a_p>0:
      measurement.a_p_sign_meaning = "M"
    else:
      measurement.a_p_sign_meaning = "D"

    if measurement.s_i>0:
      measurement.s_i_sign_meaning = "E"
    else:
      measurement.s_i_sign_meaning = "I"

  elif not False in [elem in lower_right_front for elem in lst_measurement]:
    if measurement.r_l>0:
      measurement.r_l_sign_meaning = "D"
    else:
      measurement.r_l_sign_meaning = "M"

    if measurement.a_p>0:
      measurement.a_p_sign_meaning = "B"
    else:
      measurement.a_p_sign_meaning = "L"

    if measurement.s_i>0:
      measurement.s_i_sign_meaning = "E"
    else:
      measurement.s_i_sign_meaning = "I"

  elif not False in [elem in lower_left_back for elem in lst_measurement]:
    if measurement.r_l>0:
      measurement.r_l_sign_meaning = "L"
    else:
      measurement.r_l_sign_meaning = "B"

    if measurement.a_p>0:
      measurement.a_p_sign_meaning = "M"
    else:
      measurement.a_p_sign_meaning = "D"

    if measurement.s_i>0:
      measurement.s_i_sign_meaning = "E"
    else:
      measurement.s_i_sign_meaning = "I"

  elif not False in [elem in lower_left_front for elem in lst_measurement]:
    if measurement.r_l>0:
      measurement.r_l_sign_meaning = "M"
    else:
      measurement.r_l_sign_meaning = "D"

    if measurement.a_p>0:
      measurement.a_p_sign_meaning = "B"
    else:
      measurement.a_p_sign_meaning = "L"

    if measurement.s_i>0:
      measurement.s_i_sign_meaning = "E"
    else:
      measurement.s_i_sign_meaning = "I"

def SignMeaningDentalAngle(measurement,lst_measurement):
  if not False in [elem in upper_right_back for elem in lst_measurement]:   
    if measurement.pitch_angle>0:
      measurement.pitch_sign_meaning = "M"
    else:
      measurement.pitch_sign_meaning = "D"

    if measurement.roll_angle>0:
      measurement.roll_sign_meaning = "B"
    else:
      measurement.roll_sign_meaning = "L"
    if measurement.yaw_angle>0:
      measurement.yaw_sign_meaning = "MI"
    else:
      measurement.yaw_sign_meaning = "MO"

  elif not False in [elem in upper_right_front for elem in lst_measurement]:
    if measurement.pitch_angle>0:
      measurement.pitch_sign_meaning = "B"
    else:
      measurement.pitch_sign_meaning = "L"

    if measurement.roll_angle>0:
      measurement.roll_sign_meaning = "D"
    else:
      measurement.roll_sign_meaning = "M"

    if measurement.yaw_angle>0:
      measurement.yaw_sign_meaning = "MI"
    else:
      measurement.yaw_sign_meaning = "MO"
    
  elif not False in [elem in upper_left_back for elem in lst_measurement]:
    if measurement.pitch_angle>0:
      measurement.pitch_sign_meaning = "M"
    else:
      measurement.pitch_sign_meaning = "D"

    if measurement.roll_angle>0:
      measurement.roll_sign_meaning = "L"
    else:
      measurement.roll_sign_meaning = "B"
    if measurement.yaw_angle>0:
      measurement.yaw_sign_meaning = "MO"
    else:
      measurement.yaw_sign_meaning = "MI"
  
  elif not False in [elem in upper_left_front for elem in lst_measurement]:
    if measurement.pitch_angle>0:
      measurement.pitch_sign_meaning = "B"
    else:
      measurement.pitch_sign_meaning = "L"

    if measurement.roll_angle>0:
      measurement.roll_sign_meaning = "M"
    else:
      measurement.roll_sign_meaning = "D"

    if measurement.yaw_angle>0:
      measurement.yaw_sign_meaning = "MO"
    else:
      measurement.yaw_sign_meaning = "MI"

  elif not False in [elem in lower_right_back for elem in lst_measurement]:
    if measurement.pitch_angle>0:
      measurement.pitch_sign_meaning = "D"
    else:
      measurement.pitch_sign_meaning = "M"

    if measurement.roll_angle>0:
      measurement.roll_sign_meaning = "L"
    else:
      measurement.roll_sign_meaning = "B"
    if measurement.yaw_angle>0:
      measurement.yaw_sign_meaning = "MI"
    else:
        measurement.yaw_sign_meaning = "MO"
      
  elif not False in [elem in lower_right_front for elem in lst_measurement]:
    if measurement.pitch_angle>0:
      measurement.pitch_sign_meaning = "L"
    else:
      measurement.pitch_sign_meaning = "B"

    if measurement.roll_angle>0:
      measurement.roll_sign_meaning = "M"
    else:
      measurement.roll_sign_meaning = "D"
    if measurement.yaw_angle>0:
      measurement.yaw_sign_meaning = "MI"
    else:
      measurement.yaw_sign_meaning = "MO"
      
  elif not False in [elem in lower_left_back for elem in lst_measurement]:   
    if measurement.pitch_angle>0:
      measurement.pitch_sign_meaning = "D"
    else:
      measurement.pitch_sign_meaning = "M"

    if measurement.roll_angle>0:
      measurement.roll_sign_meaning = "B"
    else:
      measurement.roll_sign_meaning = "L"
    if measurement.yaw_angle>0:
      measurement.yaw_sign_meaning = "MO"
    else:
      measurement.yaw_sign_meaning = "MI"
      
  elif not False in [elem in lower_left_front for elem in lst_measurement]:
    if measurement.pitch_angle>0:
      measurement.pitch_sign_meaning = "L"
    else:
      measurement.pitch_sign_meaning = "B"

    if measurement.roll_angle>0:
      measurement.roll_sign_meaning = "D"
    else:
      measurement.roll_sign_meaning = "M"
    if measurement.yaw_angle>0:
      measurement.yaw_sign_meaning = "MO"
    else:
      measurement.yaw_sign_meaning = "MI"



#
# AQ3DCLogic
#

class AQ3DCLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "100.0")
    if not parameterNode.GetParameter("Invert"):
      parameterNode.SetParameter("Invert", "false")

  def process(self, inputVolume, outputVolume, imageThreshold, invert=False, showResult=True):
    """
    Run the processing algorithm.
    Can be used without GUI widget.
    :param inputVolume: volume to be thresholded
    :param outputVolume: thresholding result
    :param imageThreshold: values above/below this threshold will be set to 0
    :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
    :param showResult: show output volume in slice viewers
    """

    if not inputVolume or not outputVolume:
      raise ValueError("Input or output volume is invalid")

    import time
    startTime = time.time()
    logging.info('Processing started')

    # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
    cliParams = {
      'InputVolume': inputVolume.GetID(),
      'OutputVolume': outputVolume.GetID(),
      'ThresholdValue' : imageThreshold,
      'ThresholdType' : 'Above' if invert else 'Below'
      }
    cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True, update_display=showResult)
    # We don't need the CLI module node anymore, remove it to not clutter the scene with it
    slicer.mrmlScene.RemoveNode(cliNode)

    stopTime = time.time()
    logging.info('Processing completed in {0:.2f} seconds'.format(stopTime-startTime))


#
# AQ3DCTest
#

class AQ3DCTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_AQ3DC1()

  def test_AQ3DC1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # Get/create input data

    import SampleData
    registerSampleData()
    inputVolume = SampleData.downloadSample('AQ3DC1')
    self.delayDisplay('Loaded test data set')

    inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    self.assertEqual(inputScalarRange[0], 0)
    self.assertEqual(inputScalarRange[1], 695)

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    threshold = 100

    # Test the module logic

    logic = AQ3DCLogic()

    # Test algorithm with non-inverted threshold
    logic.process(inputVolume, outputVolume, threshold, True)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], threshold)

    # Test algorithm with inverted threshold
    logic.process(inputVolume, outputVolume, threshold, False)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], inputScalarRange[1])

    self.delayDisplay('Test passed')
