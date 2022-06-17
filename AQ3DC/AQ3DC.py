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

except: 
  slicer.util.pip_install('pandas')
  slicer.util.pip_install('openpyxl')
  slicer.util.pip_install('xlrd')
  slicer.util.pip_install('xlsxwriter')
  import pandas as pd
  import openpyxl
  import xlrd
  import xlsxwriter

def JawLandmarks(landmarks_dir):
  dic_patient = {} 
  dic_time = {}
  normpath = os.path.normpath("/".join([landmarks_dir,'**','']))
  
  for jsonfile in sorted(glob.iglob(normpath, recursive=True)):
    # print(jsonfile)
    if os.path.isfile(jsonfile) and True in [ext in jsonfile for ext in [".json"]]:
      num_patient= os.path.basename(jsonfile).split("_")[2][1:]
      # print(num_patient)
      time = os.path.basename(jsonfile).split("_")[1]
      if "_L." in jsonfile:
        if num_patient in dic_patient.keys():
          if time in dic_time.keys():
            dic_time[time]['path_landmark_L'] = jsonfile
            dic_patient[num_patient] = dic_time
          else :
            dic_time[time] = {'path_landmark_L' : jsonfile}
            dic_patient[num_patient] = dic_time
        else:
          dic_time[time] = {'path_landmark_L' : jsonfile}
          dic_patient[num_patient] = dic_time
      else :
        if num_patient in dic_patient.keys():
          if time in dic_time.keys():
            dic_time[time]['path_landmark_U'] = jsonfile
            dic_patient[num_patient] = dic_time
          else :
            dic_time[time] = {'path_landmark_U' : jsonfile}
            dic_patient[num_patient] = dic_time
        else:
          dic_time[time] = {'path_landmark_U' : jsonfile}
          dic_patient[num_patient] = dic_time
  
  # print(dic_patient)\
  list_tooth = []
  list_type_tooth = []
  for obj in dic_patient.items():
    obj=obj[1]    
    for patient_t in obj.items():
      time = patient_t[0]
      dic_path_patient = patient_t[1]
      # print(dic_path_patient)
      # print(dic_path_patient.items())
      for path_patient in dic_path_patient.items():
        # print('path_patient :',path_patient)
        json_file = pd.read_json(path_patient[1])
        markups = json_file.loc[0,'markups']
        controlPoints = markups['controlPoints']
        for i in range(len(controlPoints)):
          label = controlPoints[i]["label"]#.split("-")[1]
          tooth = label[:3]
          type_land = label[3:]
          if tooth not in list_tooth:
            list_tooth.append(tooth)
          if type_land not in list_type_tooth:
            list_type_tooth.append(type_land)
          
          
  return list_tooth,list_type_tooth
list_tooth,list_type_tooth = JawLandmarks('/home/luciacev-admin/Desktop/AQ3DC_data/renamed_data/T1')
# print(list_tooth,list_type_tooth)

GROUPS_LANDMARKS = {
  "Mandible" : ['RCo','RGo','LR6apex','L1apex','Me','Gn','Pog','B','LL6apex','LGo','LCo','LR6d','LR6m','LItip','LL6m','LL6d'],
  "Maxilla" : ['PNS','ANS','A','UR6apex','UR3apex','U1apex','UL3apex','UL6apex','UR6d','UR6m','UR3tip','UItip','UL3tip','UL6m','UL6d',"IF","ANS","UR6","UL6","UR1","UL1","UR1A","UL1A","UR2","UL2","UR2A","UL2A","UR3","UL3","UR3A","UL3A"],
  "Cranial Base" :['Ba','S','N'],
  "Dental" : list_tooth,
  "Landmarks type" : list_type_tooth
}

def ReadFolder(landmarks_dir_T1,landmarks_dir_T2):
  dic_patient = {} 
  dic_time = {}
  dic_tooth = {}
  normpath_T1 = os.path.normpath("/".join([landmarks_dir_T1,'**','']))
  normpath_T2 = os.path.normpath("/".join([landmarks_dir_T2,'**','']))
  lst_normpath = [normpath_T1,normpath_T2]
  
  for normpath in lst_normpath:
    for jsonfile in sorted(glob.iglob(normpath, recursive=True)):
      # print(jsonfile)
      if os.path.isfile(jsonfile) and True in [ext in jsonfile for ext in [".json"]]:
        num_patient= os.path.basename(jsonfile).split("_")[2][1:]
        # print(num_patient)
        time = os.path.basename(jsonfile).split("_")[1]
        if "_L." in jsonfile:
          if num_patient in dic_patient.keys():
            if time in dic_time.keys():
              dic_time[time]['path_landmark_L'] = jsonfile
              dic_patient[num_patient] = dic_time
            else :
              dic_time[time] = {'path_landmark_L' : jsonfile}
              dic_patient[num_patient] = dic_time
          else:
            dic_time[time] = {'path_landmark_L' : jsonfile}
            dic_patient[num_patient] = dic_time
        else :
          if num_patient in dic_patient.keys():
            if time in dic_time.keys():
              dic_time[time]['path_landmark_U'] = jsonfile
              dic_patient[num_patient] = dic_time
            else :
              dic_time[time] = {'path_landmark_U' : jsonfile}
              dic_patient[num_patient] = dic_time
          else:
            dic_time[time] = {'path_landmark_U' : jsonfile}
            dic_patient[num_patient] = dic_time
  
  # print(dic_patient)\
  list_label = []
  for obj in dic_patient.items():
    obj=obj[1]    
    for patient_t in obj.items():
      time = patient_t[0]
      dic_path_patient = patient_t[1]
      # print(dic_path_patient)
      # print(dic_path_patient.items())
      for path_patient in dic_path_patient.items():
        # print('path_patient :',path_patient)
        json_file = pd.read_json(path_patient[1])
        markups = json_file.loc[0,'markups']
        controlPoints = markups['controlPoints']
        for i in range(len(controlPoints)):
          label = controlPoints[i]["label"]#.split("-")[1]
          if label not in list_label:
            list_label.append(label)
          tooth = label[:3]
          # print(tooth)
          type_land = label[3:]
          position = controlPoints[i]["position"]
          if tooth not in dic_tooth.keys():
            dic_tooth[tooth] = {}
          if type_land not in dic_tooth[tooth]:
            dic_tooth[tooth][type_land] = {}
          
          dic_tooth[tooth][type_land][time] = position
  # print(list_label)
  return dic_tooth



def compute_distance_T1T2(dic_tooth,type):
  dic_distance = {}
  for landmark in dic_tooth.items():
    land = landmark[1]
    name = landmark[0]
    point_T1 = np.array(land[type]['T1'])
    point_T2 = np.array(land[type]['T2'])
    distance = computeDistance(point_T2,point_T1)
    if name not in dic_distance.keys(): 
      dic_distance[name] = {}
    dic_distance[name] = distance
  print(dic_distance)
  return dic_distance


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

    # -------------------------- Scene ---------------------------
    self.SceneCollapsibleButton = self.ui.SceneCollapsibleButton # this attribute is usefull for Longitudinal quantification extension
    treeView = self.ui.TreeView
    treeView.setMRMLScene(slicer.app.mrmlScene())
    treeView.sceneModel().setHorizontalHeaderLabels(["Models"])
    treeView.sortFilterProxyModel().nodeTypes = ['vtkMRMLModelNode','vtkMRMLMarkupsFiducialNode']
    treeView.header().setVisible(False)

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
    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.ui.pushButton_DataFolder_T1.connect('clicked(bool)',self.onSearchFolderButton_T1)
    self.ui.pushButton_DataFolder_T2.connect('clicked(bool)',self.onSearchFolderButton_T2)

    # self.distancewidget = DistanceWidget()
    # display of all the different measurment
    self.table_view = TableView(self.ui)
    self.ui.verticalLayout_2.addWidget(self.table_view.widget)

    # layout to add measurment to the tab
    self.tab_manager = TabManager(self.ui,self.table_view)
    self.ui.verticalLayout_3.addWidget(self.tab_manager.widget)
    
    # selection of the landmarks
    self.lm_tab = LMTab(self.tab_manager)
    self.ui.verticalLayout_1.addWidget(self.lm_tab.widget)
 
    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()



  def onSearchFolderButton_T1(self):
    surface_folder = qt.QFileDialog.getExistingDirectory(self.parent, "Select a scan folder")
    if surface_folder != '':
      self.surface_folder = surface_folder
      self.ui.lineEditLandPathT1.setText(self.surface_folder)
      
      lm_group = GetLandmarkGroup(GROUPS_LANDMARKS)
      # print(lm_group)
      available_lm = GetAvailableLm(self.surface_folder,lm_group)
      # print('available_lm :',available_lm)
      self.lm_tab.Clear()
      self.lm_tab.FillTab(available_lm)
 
  def onSearchFolderButton_T2(self):
    surface_folder = qt.QFileDialog.getExistingDirectory(self.parent, "Select a scan folder")
    if surface_folder != '':
      self.surface_folder_2 = surface_folder
      self.ui.lineEditLandPathT2.setText(self.surface_folder_2)
      # self.lm_tab.Clear()
      # self.lm_tab.FillTab(self.dic_tooth)

    



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

  def onApplyButton(self):
    """
    Run processing when user clicks "Apply" button.
    """
    try:

      # Compute output
      self.logic.process(self.ui.inputSelector.currentNode(), self.ui.outputSelector.currentNode(),
        self.ui.imageThresholdSliderWidget.value, self.ui.invertOutputCheckBox.checked)

      # Compute inverted output (if needed)
      if self.ui.invertedOutputSelector.currentNode():
        # If additional output volume is selected then result with inverted threshold is written there
        self.logic.process(self.ui.inputSelector.currentNode(), self.ui.invertedOutputSelector.currentNode(),
          self.ui.imageThresholdSliderWidget.value, not self.ui.invertOutputCheckBox.checked, showResult=False)

    except Exception as e:
      slicer.util.errorDisplay("Failed to compute results: "+str(e))
      import traceback
      traceback.print_exc()

class LMTab:
  def __init__(self,layout_measure) -> None:
    self.layout_measure = layout_measure
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
    # print('lm_dic :',lm_dic)
    self.lm_group_dic = lm_dic.copy()
    # self.lm_group_dic["All"] = []
    self.check_box_dic = {}
    self.lm_cb_dic = {}
    for group,lm_lst in self.lm_group_dic.items():
      if group == "Dental":
        for lm in lm_lst:
          if lm not in self.lm_status_dic.keys():
            for lm_type in lm_dic['Landmarks type']:
              self.lm_status_dic[lm+lm_type] = False
              # self.lm_group_dic["All"].append(lm+lm_type)
              
      elif group != "Landmarks type" and group != "Dental":
        for lm in lm_lst:
          if lm not in self.lm_status_dic.keys():
            self.lm_status_dic[lm] = False
            # self.lm_group_dic["All"].append(lm)

    for group,lm_lst in self.lm_group_dic.items():
      lst_wid = []
      for lm in lm_lst:
        new_cb = qt.QCheckBox(lm)
        self.check_box_dic[new_cb] = lm
        lst_wid.append(new_cb)
      new_lm_tab = self.GenNewTab(lst_wid)
      self.LM_tab_widget.insertTab(0,new_lm_tab,group)
    self.LM_tab_widget.currentIndex = 0

    # print('self.lm_group_dic :',self.lm_group_dic)
    # print('lm_dic :',lm_dic)
    # print('self.check_box_dic :',self.check_box_dic)

    for cb,lm in self.check_box_dic.items():
      if lm not in self.lm_cb_dic.keys():
        self.lm_cb_dic[lm] = [cb]
      else:
        self.lm_cb_dic[lm].append(cb)
    # print('self.lm_cb_dic :',self.lm_cb_dic)
    # print(self.check_box_dic.items())

    # for cb in self.check_box_dic.keys():
    #   cb.connect("toggled(bool)", self.CheckBox)
    # print(self.lm_group_dic["Landmarks type"])
    # print(self.lm_group_dic["Dental"])
    # print(self.lm_status_dic)
    for cb,lm in self.check_box_dic.items(): 
      if lm in self.lm_group_dic["Landmarks type"]+self.lm_group_dic["Dental"]:
        print('dental')
        cb.connect("toggled(bool)", self.UpdateDentalLm)
      else:
        print('other')
        cb.connect("toggled(bool)", self.CheckBox)

  def CheckBox(self, caller=None, event=None):
    for cb,lm in self.check_box_dic.items():
      if cb.checkState():
        state = True
      else:
        state = False
  
      if self.lm_status_dic[lm] != state:
        self.UpdateLmSelect(lm,state)
    # print(self.lm_status_dic)
    self.layout_measure.GetLmList(self.lm_status_dic)
  # print(self.lm_status_dic)

  def UpdateDentalLm(self):
    selected_type = []
    if "Landmarks type" in self.lm_group_dic.keys() :
      for lm_type in self.lm_group_dic["Landmarks type"]:
        # print(self.lm_cb_dic[lm_type])
        if self.lm_cb_dic[lm_type][0].checkState():
          selected_type.append(lm_type)
      print(selected_type)
      for dental in self.lm_group_dic["Dental"]:
        if self.lm_cb_dic[dental][0].checkState():
          for typ in selected_type:
            key = dental+typ
            state = True
            if self.lm_status_dic[key] != state:
              self.lm_status_dic[key] = state
        else:
          for typ in selected_type:
            key = dental+typ
            state = False
            if self.lm_status_dic[key] != state:
              self.lm_status_dic[key] = state
    self.layout_measure.GetLmList(self.lm_status_dic)
    # print(self.lm_status_dic)

           
  # def SelectOptions(self,idx):
  #   # print(idx)
  #   if idx == 1:
  #     self.SelectTab()
  #   elif idx == 2 :
  #     self.ClearTab()
  #   elif idx == 3:
  #     self.SelectAll()
  #   else :
  #     self.ClearAll()

  def GenNewTab(self,widget_lst):
      new_widget = qt.QWidget()
      vb = qt.QVBoxLayout(new_widget)
      scr_box = qt.QScrollArea()
      vb.addWidget(scr_box)

      # self.buttons_options.addItems(["Selection options","Select Tab","Clear Tab","Select All","Clear All"])
      # self.buttons_options.itemIcon(qt.QIcon(":/Icons/MarkupsSelectedOrUnselected.png"))
      # vb.addWidget(self.buttons_options)
      
      wid = qt.QWidget()
      vb2 = qt.QVBoxLayout(wid)
      for widget in widget_lst:
          vb2.addWidget(widget)
      wid.setLayout(vb2)

      scr_box.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOn)
      scr_box.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOff)
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
    for lm in self.lm_group_dic[group]:
      self.UpdateLmSelect(lm,state)

  def SelectTab(self):
    self.Fulltab(True)
  
  def ClearTab(self):
    self.Fulltab(False)


class TableView:
  def __init__(self,ui) -> None:
   # self.lineEditLandPathT2 = lineEditLandPathT2
    self.ui = ui
    self.widget = qt.QWidget()
    self.layout = qt.QVBoxLayout(self.widget)

    self.LM_tab_widget = qt.QTabWidget()
    # self.LM_tab_widget.connect('currentChanged(int)',self.Test)
    self.LM_tab_widget.minimumSize = qt.QSize(100,200)
    self.LM_tab_widget.maximumSize = qt.QSize(800,400)
    self.LM_tab_widget.setMovable(True)
    self.layout.addWidget(self.LM_tab_widget)
    # self.current_tab = self.LM_tab_widget.currentIndex
    

    # -------------------------- Gen Tab ---------------------------
    lst_tab = ["Distance","Angle"]
    # tab = "Distance"
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
  def __init__(self,name,coord=''):
    self.name = name
    # self.coord = coord
    self.position = []
    self.group = self.GetTypeLandmark()

  def GetTypeLandmark(self):
    for land_groups in GROUPS_LANDMARKS.items():
      if self.name[:3] in land_groups[1]:
        group = land_groups[0]
    return group

class Line:
  def __init__(self,point1,point2):
    self.name = point1.name + '-' + point2.name
    self.point1 = point1
    self.point2 = point2
    print(self.point1.position,self.point2.position)
    self.position = np.array(self.point1.position) - np.array(self.point2.position)

class MeasurePointToPoint:
  def __init__(self,point1,point2,type_m):
    self.point1 = point1
    self.point2 = point2
    self.type_m = type_m
    self.r_l_sign_meaning = ""
    self.a_p_sign_meaning = ""
    self.s_i_sign_meaning = ""

  def compute(self):
    print(self.point1.position,self.point2.position)
    self.r_l,self.a_p,self.s_i,self.norm = computeDistance(np.array(self.point1.position),np.array(self.point2.position))
    # print(self.r_l,self.a_p,self.s_i,self.norm)


class MeasurePointToLine:
  def __init__(self,point,line,type_m):
    self.point = point
    self.line = line
    self.type_m = type_m
    # self.dict_patients = {}
    
  def compute(self):
    self.r_l,self.a_p,self.s_i,self.norm = computeLinePoint(np.array(self.line.point1.position),np.array(self.line.point2.position),np.array(self.point.position))

class MeasureAngles:
  def __init__(self,line1,line2,type_m):
    self.line1 = line1
    self.line2 = line2
    self.type_m = type_m

  def compute(self):
    self.yaw_angle, self.pitch_angle, self.roll_angle = computeAngles(np.array(self.line1.position),np.array(self.line2.position))

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
    
    if self.measurement.type_m == 'Distance between 2 points':
      P1_item = qt.QTableWidgetItem(self.measurement.point1.name)
      P2_item = qt.QTableWidgetItem(self.measurement.point2.name)
      self.lst_widget.append(P1_item)
      self.lst_widget.append(P2_item)
    
    elif self.measurement.type_m == 'Distance point line':
      P1_item = qt.QTableWidgetItem(self.measurement.point.name)
      L_item = qt.QTableWidgetItem(self.measurement.line.name)
      self.lst_widget.append(P1_item)
      self.lst_widget.append(L_item)
    
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

    # -------------------------- Gen layout add line ---------------------------
    self.vb_measurement = qt.QVBoxLayout()
    self.layout.addLayout(self.vb_measurement)
    self.DWidget = DistanceWidget(self.vb_measurement,self)
    self.AWidget = AnglesWidget(self.vb_measurement,self)
    self.AWidget.setHidden(True)
    self.table_view.LM_tab_widget.connect('currentChanged(int)',self.TabSelected)

    # -------------------------- Import/Export measurment ---------------------------
    self.vb_ie = qt.QVBoxLayout()
    self.layout.addLayout(self.vb_ie)
    self.hb_ie = qt.QHBoxLayout()
    self.vb_ie.addLayout(self.hb_ie)
    self.label_ie = qt.QLabel("Import/Export measurement")
    self.combobox_ie = qt.QComboBox()
    self.combobox_ie.addItems(["none","Import measurement","Export measurement"])
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
    print(self.active_tab)
    if self.active_tab == 0:
      self.DWidget.setHidden(False)
      self.AWidget.setHidden(True)
      # self.DWidget.type_measur_combobox.connect('currentIndexChanged(int)', self.DWidget.DisplayWidget)

    else:
      self.DWidget.setHidden(True)
      self.AWidget.setHidden(False)
      # self.AWidget.type_measur_combobox.connect('currentIndexChanged(int)', self.AWidget.DisplayWidget)    

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

  def GetLmList(self,lm_status_dic):
    self.DWidget.GetLmList(lm_status_dic)
    self.AWidget.GetLmList(lm_status_dic)

  def OnDeleteButton(self):
    for idx,tab_line in enumerate(self.DWidget.lst_tab_lines_d):
      state = tab_line.checkBoxItem.checkState()
      # print(state)
      if state == 2:
        del self.DWidget.lst_measurement_dist[idx]
    self.DWidget.generate_table_distances()
    
    for idx,tab_line in enumerate(self.AWidget.lst_tab_lines_a):
      state = tab_line.checkBoxItem.checkState()
      # print(state)
      if state == 2:
        del self.AWidget.lst_measurement_angles[idx]
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
    for measurement in self.DWidget.lst_measurement_dist:
      if measurement.type_m == "Distance between 2 points":
        dict_csv = {"Type of measurement":measurement.type_m,"Point 1":measurement.point1.name,"Point 2 / Line":measurement.point2.name}
        lst_data_dist_pp.append(dict_csv)
      else :
        dict_csv = {"Type of measurement":measurement.type_m,"Point 1":measurement.point.name,"Point 2 / Line":measurement.line.name}
        lst_data_dist_pl.append(dict_csv)
    
    for measurement in self.AWidget.lst_measurement_angles:
      dict_csv = {"Type of measurement":measurement.type_m,"Line 1":measurement.line1.name,"Line 2":measurement.line2.name}  
      lst_data_angl.append(dict_csv)
    
    
    # print(lst_data_dist_pp)
    # print(list(range(len(lst_data_dist_pp))))
    # print(list(lst_data_dist_pp[0].keys()))
    df_dist_pp = pd.DataFrame(lst_data_dist_pp,index=list(range(len(lst_data_dist_pp))),columns=list(lst_data_dist_pp[0].keys()))
    df_dist_pl = pd.DataFrame(lst_data_dist_pl,index=list(range(len(lst_data_dist_pl))),columns=list(lst_data_dist_pl[0].keys()))
    df_angl = pd.DataFrame(lst_data_angl,index=list(range(len(lst_data_angl))),columns=list(lst_data_angl[0].keys()))


    # full_path = self.export_line.text +'/'+ self.line_edit.text
    # print(full_path)
    with pd.ExcelWriter(f"{self.export_line.text}/{self.line_edit.text}") as writer:
      df_dist_pp.to_excel(writer,sheet_name="Distance between 2 points",index=False)
      df_dist_pl.to_excel(writer,sheet_name="Distance between a point and a line",index=False)
      df_angl.to_excel(writer,sheet_name="Angle between 2 lines",index=False)

    print("Export done")

    # with open(full_path, 'w') as csvfile:
      # writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
      # writer.writeheader()
      # for data in lst_data_dist:
      #   writer.writerow(data)

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
            # print(row[0].value,row[1].value,row[2].value)
            data_type_of_measurment = row[0].value
            point1 = Point(row[1].value)
            point2 = Point(row[2].value)
            measurement = MeasurePointToPoint(point1,point2,data_type_of_measurment)
            self.DWidget.lst_measurement_dist.append(measurement)
      
      elif idx == 1:
        for idx_row,row in enumerate(ws.iter_rows()):
          if idx_row != 0:
            # print(row[0].value,row[1].value,row[2].value.split('-')[0],row[2].value.split('-')[1])
            data_type_of_measurment = row[0].value
            point = Point(row[1].value)
            point2 = row[2].value.split('-')[0]
            point3 = row[2].value.split('-')[1]
            line = Line(Point(point2),Point(point3))
            measurement = MeasurePointToLine(point,line,data_type_of_measurment)
            self.DWidget.lst_measurement_dist.append(measurement)
      else:
        for idx_row,row in enumerate(ws.iter_rows()):
          if idx_row != 0:
            # print(row[0].value,row[1].value.split('-')[0],row[1].value.split('-')[1],row[2].value.split('-')[0],row[2].value.split('-')[1])
            data_type_of_measurment = row[0].value
            point1 = Point(row[1].value.split('-')[0])
            point2 = Point(row[1].value.split('-')[1])
            point3 = Point(row[2].value.split('-')[0])
            point4 = Point(row[2].value.split('-')[1])
            line1 = Line(point1,point2)
            line2 = Line(point3,point4)
            measurement = MeasureAngles(line1,line2,data_type_of_measurment)
            self.AWidget.lst_measurement_angles.append(measurement)
      
    # print(self.DWidget.lst_measurement_dist)
    # print(self.AWidget.lst_measurement_angles)
    self.DWidget.generate_table_distances()
    self.AWidget.generate_table_angles()
    print("Import done")

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
    self.lst_compute_dst_pp = []
    self.lst_compute_dst_pl = []
    self.lst_compute_angles = []
    
    landmarks_dir = self.ui.lineEditLandPathT1.text
    # print('landmarks_dir :',landmarks_dir)
    normpath = os.path.normpath("/".join([landmarks_dir,'**','']))
    for self.jsonfile in sorted(glob.iglob(normpath, recursive=True)):
      if os.path.isfile(self.jsonfile) and True in [ext in self.jsonfile for ext in [".json"]]:
        # print('jsonfile :',jsonfile)
        json_file = pd.read_json(self.jsonfile)
        markups = json_file.loc[0,'markups']
        self.controlPoints = markups['controlPoints']
        self.lst_label = []
        for controlPoint in self.controlPoints:
          self.lst_label.append(controlPoint['label'])
        print('lst_measurement_dist :',self.DWidget.lst_measurement_dist)
        if len(self.DWidget.lst_measurement_dist)>0:
          for measurement in self.DWidget.lst_measurement_dist:
            if measurement.point1.name and measurement.point2.name in self.lst_label:
              self.GenerateComputeDstLst()
            
    #         else:
    #           dict_patient_measurement = {}
    #           for landmark in controlPoints:
    #             if landmark['label'] == measurement.point.name:
    #               measurement.point.position = landmark['position']
    #               # print(measurement.point.name, ':', measurement.point.position)
    #             if landmark['label'] == measurement.line.point1.name:
    #               measurement.line.point1.position = landmark['position']
    #               # print(measurement.line.point1.name, ':', measurement.line.point1.position)
    #             if landmark['label'] == measurement.line.point2.name:
    #               measurement.line.point2.position = landmark['position']
    #               # print(measurement.line.point2.name, ':', measurement.line.point2.position)
            
    #           measurement.compute()
    #           dict_patient_measurement["Patient"] = os.path.basename(jsonfile).split('.')[0]
    #           dict_patient_measurement["Type of measurement"] = measurement.type_m
    #           dict_patient_measurement["Landmark"] = measurement.point.name + '-' + measurement.line.name
    #           dict_patient_measurement["R-L Component"] = measurement.r_l
    #           dict_patient_measurement["A-P Component"] = measurement.a_p
    #           dict_patient_measurement["S-I Component"] = measurement.s_i
    #           dict_patient_measurement["3D Distance"] = measurement.norm
    #           self.lst_compute_dst_pl.append(dict_patient_measurement)
        
    #     if len(self.AWidget.lst_measurement_angles)>0:
    #       for measurement in self.AWidget.lst_measurement_angles:
    #         dict_patient_measurement = {}
    #         for landmark in controlPoints:
    #           if landmark['label'] == measurement.line1.point1.name:
    #             measurement.line1.point1.position = landmark['position']
    #             # print(measurement.line1.name, ':', measurement.line1.position)
    #           if landmark['label'] == measurement.line1.point2.name:
    #             measurement.line1.point2.position = landmark['position']
    #             # print(measurement.line2.name, ':', measurement.line2.position)  
    #           if landmark['label'] == measurement.line2.point1.name:
    #             measurement.line2.point1.position = landmark['position']
    #           if landmark['label'] == measurement.line2.point1.name:
    #             measurement.line2.point2.position = landmark['position']
    #         print(measurement.line1.point1.position,measurement.line1.point2.position,measurement.line2.point1.position,measurement.line2.point2.position)
    #         print(measurement.line1.position,measurement.line2.position)
    #         measurement.compute()
    #         dict_patient_measurement["Patient"] = os.path.basename(jsonfile).split('.')[0]
    #         dict_patient_measurement["Type of measurement"] = measurement.type_m
    #         dict_patient_measurement["Landmark"] = measurement.line1.name + '-' + measurement.line2.name 
    #         dict_patient_measurement["Yaw Component"] = measurement.yaw_angle
    #         dict_patient_measurement["Pitch Component"] = measurement.pitch_angle
    #         dict_patient_measurement["Roll Component"] = measurement.roll_angle
    #         self.lst_compute_angles.append(dict_patient_measurement)
      
    # print(self.lst_compute_dst_pp)
    # print(self.lst_compute_dst_pl)
    # print(self.lst_compute_angles) 
    self.GenMeasurementExcel()

  def SignMeaning(self,lst_measurement):
    upper_right_back = ['UR8','UR7','UR6','UR5','UR4','UR3']
    upper_right_front = ['UR1','UR2']
    upper_left_back = ['UL8','UL7','UL6','UL5','UL4','UL3']
    upper_left_front = ['UL1','UL2']
    lower_right_back = ['LR8','LR7','LR6','LR5','LR4','LR3']
    lower_right_front = ['LR1','LR2']
    lower_left_back = ['LL8','LL7','LL6','LL5','LL4','LL3']
    lower_left_front = ['LL1','LL2']
    # print('lst_measurement :',lst_measurement)
    for measurement in lst_measurement:
      # print('signmeaning')
      measurement_point1_name = measurement.point1.name[:3]
      measurement_point2_name = measurement.point2.name[:3]
  
      if measurement.point1.group and measurement.point2.group  == "Dental":

        if measurement_point1_name and measurement_point2_name in upper_right_back:
          if measurement.r_l>0:
            measurement.r_l_sign_meaning = "Right Expension Buccal"
          else:
            measurement.r_l_sign_meaning = "Left Contraction Lingual"

          if measurement.a_p>0:
            measurement.a_p_sign_meaning = "Anterior Mesial"
          else:
            measurement.a_p_sign_meaning = "Posterior Mesial"

          if measurement.s_i>0:
            measurement.s_i_sign_meaning = "Superior Intrusion"
          else:
            measurement.s_i_sign_meaning = "Inferior Extrusion"

        if measurement_point1_name and measurement_point2_name in upper_right_front :
          if measurement.r_l>0:
            measurement.r_l_sign_meaning = "Right Distal"
          else:
            measurement.r_l_sign_meaning = "Left Mesial"

          if measurement.a_p>0:
            measurement.a_p_sign_meaning = "Anterior Expension Buccal"
          else:
            measurement.a_p_sign_meaning = "Posterior Contraction Lingual"

          if measurement.s_i>0:
            measurement.s_i_sign_meaning = "Superior Intrusion"
          else:
            measurement.s_i_sign_meaning = "Inferior Extrusion"
        
        if measurement_point1_name and measurement_point2_name in upper_left_back:
          if measurement.r_l>0:
            measurement.r_l_sign_meaning = "Right Contraction Lingual"
          else:
            measurement.r_l_sign_meaning = "Left Expension Buccal"

          if measurement.a_p>0:
            measurement.a_p_sign_meaning = "Anterior Mesial"
          else:
            measurement.a_p_sign_meaning = "Posterior Distal"

          if measurement.s_i>0:
            measurement.s_i_sign_meaning = "Superior Intrusion"
          else:
            measurement.s_i_sign_meaning = "Inferior Extrusion"
        
        if measurement_point1_name and measurement_point2_name in upper_left_front:
          if measurement.r_l>0:
            measurement.r_l_sign_meaning = "Right Mesial"
          else:
            measurement.r_l_sign_meaning = "Left Distal"

          if measurement.a_p>0:
            measurement.a_p_sign_meaning = "Anterior Expension Buccal"
          else:
            measurement.a_p_sign_meaning = "Posterior Contraction Mesial"

          if measurement.s_i>0:
            measurement.s_i_sign_meaning = "Superior Intrusion"
          else:
            measurement.s_i_sign_meaning = "Inferior Extrusion"

        if measurement_point1_name and measurement_point2_name in lower_right_back:
          if measurement.r_l>0:
            measurement.r_l_sign_meaning = "Right Expension Buccal"
          else:
            measurement.r_l_sign_meaning = "Left Contraction Lingual"

          if measurement.a_p>0:
            measurement.a_p_sign_meaning = "Anterior Mesial"
          else:
            measurement.a_p_sign_meaning = "Posterior Distal"

          if measurement.s_i>0:
            measurement.s_i_sign_meaning = "Superior Extrusion"
          else:
            measurement.s_i_sign_meaning = "Inferior Intrusion"
        
        if measurement_point1_name and measurement_point2_name in lower_right_front:
          if measurement.r_l>0:
            measurement.r_l_sign_meaning = "Right Distal"
          else:
            measurement.r_l_sign_meaning = "Left Mesial"

          if measurement.a_p>0:
            measurement.a_p_sign_meaning = "Anterior Expension Buccal"
          else:
            measurement.a_p_sign_meaning = "Posterior Contraction Lingual"

          if measurement.s_i>0:
            measurement.s_i_sign_meaning = "Superior Extrusion"
          else:
            measurement.s_i_sign_meaning = "Inferior Intrusion"
        
        if measurement_point1_name and measurement_point2_name in lower_left_back:
          if measurement.r_l>0:
            measurement.r_l_sign_meaning = "Right Contraction Lingual"
          else:
            measurement.r_l_sign_meaning = "Left Expension Buccal"

          if measurement.a_p>0:
            measurement.a_p_sign_meaning = "Anterior Mesial"
          else:
            measurement.a_p_sign_meaning = "Posterior Distal"

          if measurement.s_i>0:
            measurement.s_i_sign_meaning = "Superior Extrusion"
          else:
            measurement.s_i_sign_meaning = "Inferior Intrusion"
      
        if measurement_point1_name and measurement_point2_name in lower_left_front:
          if measurement.r_l>0:
            measurement.r_l_sign_meaning = "Right Mesial"
          else:
            measurement.r_l_sign_meaning = "Left Distal"

          if measurement.a_p>0:
            measurement.a_p_sign_meaning = "Anterior Expension Buccal"
          else:
            measurement.a_p_sign_meaning = "Posterior Contraction Lingual"

          if measurement.s_i>0:
            measurement.s_i_sign_meaning = "Superior Extrusion"
          else:
            measurement.s_i_sign_meaning = "Inferior Intrusion"
      
      else:

        if measurement.r_l<0:
          measurement.r_l_sign_meaning = "Left"
        else:
          measurement.r_l_sign_meaning = "Right"

        if measurement.a_p<0:
          measurement.a_p_sign_meaning = "Posterior"
        else:
          measurement.a_p_sign_meaning = "Anterior"

        if measurement.s_i<0:
          measurement.s_i_sign_meaning = "Inferior"
        else:
          measurement.s_i_sign_meaning = "Superior"

   





  def GenMeasurementExcel(self):
    # csv_columns_dist = ["Patient","Type of measurement","Landmark","R-L Component","A-P Component","S-I Component","3D Distance"]
    # csv_columns_angles = ["Patient","Type of measurement","Landmark","Yaw Component","Pitch Component","Roll Component"]
    # print(self.lst_compute_dst_pp)
    # print(self.lst_compute_dst_pl)
    # print(self.lst_compute_angles)    
    
    df_dist_pp = pd.DataFrame(self.lst_compute_dst_pp,index=list(range(len(self.lst_compute_dst_pp))),columns=list(self.lst_compute_dst_pp[0].keys()))
    # df_dist_pl = pd.DataFrame(self.lst_compute_dst_pl,index=list(range(len(self.lst_compute_dst_pl))),columns=list(self.lst_compute_dst_pl[0].keys()))
    # df_angl = pd.DataFrame(self.lst_compute_angles,index=list(range(len(self.lst_compute_angles))),columns=list(self.lst_compute_angles[0].keys()))
    
    with pd.ExcelWriter(f"{self.ui.export_measurement_line.text}/{self.ui.file_measurement_edit.text}") as writer:
      df_dist_pp.to_excel(writer,sheet_name="Distance between 2 points",index=False)
      # df_dist_pl.to_excel(writer,sheet_name="Distance between a point and a line",index=False)
      # df_angl.to_excel(writer,sheet_name="Angle between 2 lines",index=False)
      for column in df_dist_pp:
        column_width = max(df_dist_pp[column].astype(str).map(len).max(), len(column))
        col_idx = df_dist_pp.columns.get_loc(column)
        writer.sheets["Distance between 2 points"].set_column(col_idx, col_idx, column_width)

    print('------------------- SAVE MEASUREMENT -------------------')

  def GenerateComputeDstLst(self):
    for measurement in self.DWidget.lst_measurement_dist:
      if measurement.type_m == 'Distance between 2 points':
        dict_patient_measurement = {}
        # print('self.controlPoints :',self.controlPoints)
        for landmark in self.controlPoints:         
          if landmark['label'] == measurement.point1.name:
            measurement.point1.position = landmark['position']
            print(measurement.point1.name, ':', measurement.point1.position)
          if landmark['label'] == measurement.point2.name:
            measurement.point2.position = landmark['position']
            print(measurement.point2.name, ':', measurement.point2.position)

        measurement.compute()
        self.SignMeaning(self.DWidget.lst_measurement_dist)

        dict_patient_measurement["Patient"] = os.path.basename(self.jsonfile).split('.')[0]
        dict_patient_measurement["Type of measurement"] = measurement.type_m
        dict_patient_measurement["Landmark"] = measurement.point1.name + '-' + measurement.point2.name
        dict_patient_measurement["R-L Component"] = measurement.r_l
        dict_patient_measurement["R-L Sign Meaning"] = measurement.r_l_sign_meaning
        dict_patient_measurement["A-P Component"] = measurement.a_p
        dict_patient_measurement["A-P Sign Meaning"] = measurement.a_p_sign_meaning
        dict_patient_measurement["S-I Component"] = measurement.s_i
        dict_patient_measurement["S-I Sign Meaning"] = measurement.s_i_sign_meaning
        dict_patient_measurement["3D Distance"] = measurement.norm
        self.lst_compute_dst_pp.append(dict_patient_measurement)

  def OnSaveMeasurementFolder(self):
    self.export_measurement_folder = qt.QFileDialog.getExistingDirectory(self.widget,"Select folder")
    if self.export_measurement_folder != '':
      self.ui.export_measurement_line.setText(self.export_measurement_folder)
  
class DistanceWidget:
  def __init__(self,layout,parent):
    self.parent = parent
    self.layout = layout 
    self.index = 0
    self.lst_measurement_dist = []

    #  -------------------------------------------------- WIDGETS --------------------------------------------------

    self.distance_widget = qt.QWidget()
    self.hb_add  = qt.QHBoxLayout(self.distance_widget)
    self.layout.addWidget(self.distance_widget)
    self.type_measur_combobox = qt.QComboBox()
    lst_type_meas = ["Distance between 2 points","Distance point line"]
    self.type_measur_combobox.addItems(lst_type_meas)
    self.label = qt.QLabel("Type of measurement")
    self.hb_add.addWidget(self.label)
    self.hb_add.addWidget(self.type_measur_combobox)

    self.widget_pp = qt.QWidget()
    hb = qt.QHBoxLayout(self.widget_pp)
    self.combo_box_pp_1 = qt.QComboBox()
    self.combo_box_pp_2 = qt.QComboBox()
    self.add_button_pp = qt.QPushButton("add")
    widget_lst = [self.combo_box_pp_1,self.combo_box_pp_2,self.add_button_pp]
    for widget in widget_lst:
        hb.addWidget(widget)
    self.layout.addWidget(self.widget_pp)
    
    self.widget_pl = qt.QWidget()
    hb = qt.QHBoxLayout(self.widget_pl)
    self.combo_box_pl_1 = qt.QComboBox()
    self.combo_box_pl_2 = qt.QComboBox()
    self.combo_box_pl_3 = qt.QComboBox()
    self.add_button_pl = qt.QPushButton("add")
    widget_lst = [self.combo_box_pl_1,self.combo_box_pl_2,self.combo_box_pl_3,self.add_button_pl]
    for widget in widget_lst:
        hb.addWidget(widget)
    self.layout.addWidget(self.widget_pl)

    self.DisplayWidget(self.index)
    
    #  -------------------------------------------------- CONNECTIONS --------------------------------------------------
    self.type_measur_combobox.connect('currentIndexChanged(int)', self.DisplayWidget)
    self.add_button_pp.connect('clicked()',self.OnAddButtonDistances)
    self.add_button_pl.connect('clicked()',self.OnAddButtonDistances)

  def setHidden(self,hidden):
    self.distance_widget.setHidden(hidden)
    if hidden:
      self.widget_pp.setHidden(True)
      self.widget_pl.setHidden(True)
    else:
      self.DisplayWidget(self.index)
 
  def DisplayWidget(self,idx):
    self.index = idx
    if self.index == 0:
      self.widget_pp.setHidden(False)
      self.widget_pl.setHidden(True)
    else:
      self.widget_pp.setHidden(True)
      self.widget_pl.setHidden(False)
  
  def GetLmList(self,lm_status_dic):
    self.combo_box_pp_1.clear()
    self.combo_box_pp_2.clear()
    self.combo_box_pl_1.clear()
    self.combo_box_pl_2.clear()
    self.combo_box_pl_3.clear()

    self.list_lm = []
    data_type_of_measurment = self.type_measur_combobox.currentText
    for landmark,state in lm_status_dic.items():
      if state == True:
        self.list_lm.append(landmark)

    # print('list_lm :',self.list_lm)
    self.combo_box_pp_1.addItems(self.list_lm)
    self.combo_box_pp_2.addItems(self.list_lm)
    self.combo_box_pl_1.addItems(self.list_lm)
    self.combo_box_pl_2.addItems(self.list_lm)
    self.combo_box_pl_3.addItems(self.list_lm)

  def OnAddButtonDistances(self):
    data_type_of_measurment = self.type_measur_combobox.currentText
    if data_type_of_measurment == "Distance between 2 points" :
      data_cb_1 = self.combo_box_pp_1.currentText
      data_cb_2 = self.combo_box_pp_2.currentText
      point1 = Point(data_cb_1)
      point2 = Point(data_cb_2)
      measurement = MeasurePointToPoint(point1,point2,data_type_of_measurment)
      self.lst_measurement_dist.append(measurement)
      self.generate_table_distances()

    else :
      data_cb_1 = self.combo_box_pl_1.currentText
      data_cb_2 = self.combo_box_pl_2.currentText
      data_cb_3 = self.combo_box_pl_3.currentText
      point1 = Point(data_cb_1)
      line = Line(Point(data_cb_2),Point(data_cb_3))
      measurement = MeasurePointToLine(point1,line,data_type_of_measurment)
      self.lst_measurement_dist.append(measurement)
      self.generate_table_distances()
  
  def generate_table_distances(self):
    self.parent.table_view.dict_tab[0].clearContents()
    self.lst_tab_lines_d = []
    columnLabels = ["check box","type of measurement","point 1", "point 2 / Line"]
    self.parent.table_view.dict_tab[0].setColumnCount(len(columnLabels))
    self.parent.table_view.dict_tab[0].setHorizontalHeaderLabels(columnLabels)
    self.parent.table_view.dict_tab[0].resizeColumnsToContents()
    self.parent.table_view.dict_tab[0].setRowCount(len(self.lst_measurement_dist))
    print('lst_measurement_dist :' , self.lst_measurement_dist)
    for measurement in self.lst_measurement_dist:
      tab_line = TabLine(measurement)
      tab_line.gen_widget()
      # widget_line = tab_line.widget
      self.lst_tab_lines_d.append(tab_line)
    # print(self.lst_tab_lines)
    for row in range(len(self.lst_tab_lines_d)):
      for col in range(len(columnLabels)):
       self.parent.table_view.dict_tab[0].setItem(row,col,self.lst_tab_lines_d[row].lst_widget[col])
  
class AnglesWidget:
  def __init__(self,layout,parent):
    self.parent = parent
    self.layout = layout
    self.index = 0
    self.lst_measurement_angles = []

    #  -------------------------------------------------- WIDGETS --------------------------------------------------

    self.widget_a = qt.QWidget()
    self.hb_add  = qt.QHBoxLayout(self.widget_a) 
    self.layout.addWidget(self.widget_a)
    self.type_measur_combobox = qt.QComboBox()
    lst_type_meas = ["Angle between 2 lines"]
    self.type_measur_combobox.addItems(lst_type_meas)
    self.label = qt.QLabel("Type of measurement")
    self.hb_add.addWidget(self.label)
    self.hb_add.addWidget(self.type_measur_combobox)

    self.widget_angle = qt.QWidget()
    hb = qt.QHBoxLayout(self.widget_angle)
    self.combo_box_1_angle = qt.QComboBox()
    self.combo_box_2_angle = qt.QComboBox()
    self.combo_box_3_angle = qt.QComboBox()
    self.combo_box_4_angle = qt.QComboBox()
    self.add_button_angles = qt.QPushButton("add")
    widget_lst = [self.combo_box_1_angle,self.combo_box_2_angle,self.combo_box_3_angle,self.combo_box_4_angle,self.add_button_angles]
    for widget in widget_lst:
        hb.addWidget(widget)
    self.layout.addWidget(self.widget_angle)
  
    self.DisplayWidget(self.index)
    
    #  -------------------------------------------------- CONNECTIONS --------------------------------------------------
    self.type_measur_combobox.connect('currentIndexChanged(int)', self.DisplayWidget)
    self.add_button_angles.connect('clicked()',self.OnAddButtonAngles)

  def setHidden(self,hidden):
    self.widget_a.setHidden(hidden)
    if hidden:
      self.widget_angle.setHidden(True)
    else:
      self.DisplayWidget(self.index)

  def DisplayWidget(self,idx): 
    if idx == 0:
      self.widget_angle.setHidden(False) 
    else:
      self.widget_angle.setHidden(True)

  def GetLmList(self,lm_status_dic):
    self.combo_box_1_angle.clear()
    self.combo_box_2_angle.clear()
    self.combo_box_3_angle.clear()
    self.combo_box_4_angle.clear()

    self.list_lm = []
    data_type_of_measurment = self.type_measur_combobox.currentText
    for landmark,state in lm_status_dic.items():
      if state == True:
        self.list_lm.append(landmark)

    # print('list_lm :',self.list_lm)
    self.combo_box_1_angle.addItems(self.list_lm)
    self.combo_box_2_angle.addItems(self.list_lm)
    self.combo_box_3_angle.addItems(self.list_lm)
    self.combo_box_4_angle.addItems(self.list_lm)
  
  def OnAddButtonAngles(self):
    data_type_of_measurment = self.type_measur_combobox.currentText
    data_cb_1 = self.combo_box_1_angle.currentText
    data_cb_2 = self.combo_box_2_angle.currentText
    data_cb_3 = self.combo_box_3_angle.currentText
    data_cb_4 = self.combo_box_4_angle.currentText
    line1 = Line(Point(data_cb_1),Point(data_cb_2))
    line2 = Line(Point(data_cb_3),Point(data_cb_4))
    measurement = MeasureAngles(line1,line2,data_type_of_measurment)
    self.lst_measurement_angles.append(measurement)
    # print(self.lst_measurement_dist)
    self.generate_table_angles()

  def generate_table_angles(self):
    self.parent.table_view.dict_tab[1].clearContents()
    self.lst_tab_lines_a = []
    columnLabels = ["check box","type of measurement","Line 1", "Line 2"]
    self.parent.table_view.dict_tab[1].setColumnCount(len(columnLabels))
    self.parent.table_view.dict_tab[1].setHorizontalHeaderLabels(columnLabels)
    self.parent.table_view.dict_tab[1].resizeColumnsToContents()
    self.parent.table_view.dict_tab[1].setRowCount(len(self.lst_measurement_angles))
    print('lst_measurement_angles :', self.lst_measurement_angles)
    for measurement in self.lst_measurement_angles:
      tab_line = TabLine(measurement)
      tab_line.gen_widget()
      # widget_line = tab_line.widget
      self.lst_tab_lines_a.append(tab_line)
    # print(self.lst_tab_lines)
    for row in range(len(self.lst_tab_lines_a)):
      for col in range(len(columnLabels)):
       self.parent.table_view.dict_tab[1].setItem(row,col,self.lst_tab_lines_a[row].lst_widget[col])

# -------------------------- Gen layout import/export ---------------------------
def WidgetExport(layout): 
  export_widget = qt.QWidget()  
  hb = qt.QHBoxLayout(export_widget)
  folder_export_button = qt.QPushButton("Folder export")
  export_line = qt.QLineEdit()
  label = qt.QLabel("Output file name")
  line_edit = qt.QLineEdit("measurement.xlsx")
  export_button = qt.QPushButton("Export measurment")
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
  # print(All_landmarks)
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
  # print(lm_group)
  return lm_group

def GetAllLandmarks(dir_path):
  All_landmarks = []
  normpath = os.path.normpath("/".join([dir_path, '**', '']))
  for img_fn in sorted(glob.iglob(normpath, recursive=True)):
    #  print(img_fn)
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


def normalize(arr):
    arr = np.asarray(arr)
    return arr / np.linalg.norm(arr)

def reject(vec, axis):
    vec = np.asarray(vec)
    axis = np.asarray(axis)

    return vec - axis * (np.dot(vec, axis) / np.dot(axis, axis))

def computeDistance(point1_coord, point2_coord):
  delta = point2_coord - point1_coord
  norm = np.linalg.norm(delta)
  print("delta :", delta)
  print("norm :", norm)
  return round(delta[0],3),round(delta[1],3),round(delta[2],3),round(norm,3)   
  
def computeLinePoint(line1, line2, point):
  if np.allclose(line1, line2, atol=1e-5):
    delta = point - line1
  else:
    delta = reject(
      point - line2,
      line1 - line2,
    )
  norm = np.linalg.norm(delta)
  return round(delta[0],3),round(delta[1],3),round(delta[2],3),round(norm,3)

def computeAngle(line1, line2, axis=None):
  if axis:
    line1 = reject(line1, normalize(axis))
    line2 = reject(line2, normalize(axis))
  line1 = normalize(line1)
  line2 = normalize(line2)
  radians = np.arccos(np.dot(line1, line2))

  return np.degrees(radians)

def computeAngles(line1, line2):
    axes = [
        (0, 0, 1),  # axis=S; axial; for yaw
        (1, 0, 0),  # axis=R; saggital; for pitch
        (0, 1, 0),  # axis=A; coronal; for roll
    ]
    yaw_angle = computeAngle(line1, line2, axes[0])
    pitch_angle = computeAngle(line1, line2, axes[1])
    roll_angle = computeAngle(line1, line2, axes[2])
   
    return yaw_angle, pitch_angle, roll_angle
    



    # # -------------------------- Gen layout angle ---------------------------
    # combo_box_1 = qt.QComboBox()
    # combo_box_2 = qt.QComboBox()
    # combo_box_3 = qt.QComboBox()
    # combo_box_4 = qt.QComboBox()
    # remove_button = qt.QPushButton("add")
    # widget_lst = [combo_box_1,combo_box_2,combo_box_3,combo_box_4,remove_button]
    # for widget in widget_lst:
    #     self.hb3.addWidget(widget)
    # self.layout.addWidget(self.new_widget_3)



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
