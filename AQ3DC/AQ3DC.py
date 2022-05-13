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


# slicer.app.pythonConsole().clear()
#
# AQ3DC
#
try:
  import pandas as pd
  # import PyQt5

except: 
  slicer.util.pip_install('pandas')
  # slicer.util.pip_install('PyQt5')
  import pandas as pd
  # from PyQt5.QtCore import QObject,QModelIndex,QVariant

def  JawLandmarks(landmarks_dir):
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
  "Canine Impaction" : ["IF","ANS","UR6","UL6","UR1","UL1","UR1A","UL1A","UR2","UL2","UR2A","UL2A","UR3","UL3","UR3A","UL3A"],
  "Cranial Base" :['Ba','S','N'],
  "Mandible" : ['RCo','RGo','LR6apex','L1apex','Me','Gn','Pog','B','LL6apex','LGo','LCo','LR6d','LR6m','LItip','LL6m','LL6d'],
  "Maxilla" : ['PNS','ANS','A','UR6apex','UR3apex','U1apex','UL3apex','UL6apex','UR6d','UR6m','UR3tip','UItip','UL3tip','UL6m','UL6d'],
  "Dental" : list_tooth,
  "Landmarks" : list_type_tooth
}
# print(GROUPS_LANDMARKS)

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

DistanceResult = collections.namedtuple("DistanceResult", ("delta", "norm"))
def computeDistance(point1, point2) -> DistanceResult:
    delta = np.abs(np.subtract(point2,point1))
    return DistanceResult(
        delta,
        np.linalg.norm(delta),
    )

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


    self.lm_tab = LMTab()
    self.ui.verticalLayout_1.addWidget(self.lm_tab.widget)

    

    # self.layout_measure = TabMeasure()
    # self.ui.verticalLayout_3.addWidget(self.layout_measure.widget)


    # Buttons
    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.ui.pushButton_DataFolder_T1.connect('clicked(bool)',self.onSearchFolderButton_T1)
    self.ui.pushButton_DataFolder_T2.connect('clicked(bool)',self.onSearchFolderButton_T2)
 
    self.table_view = TableView(self.ui.tableWidget)
    self.ui.verticalLayout_2.addWidget(self.table_view.widget)


    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()


  def onSearchFolderButton_T1(self):
    surface_folder = qt.QFileDialog.getExistingDirectory(self.parent, "Select a scan folder")
    if surface_folder != '':
      self.surface_folder = surface_folder
      self.ui.lineEditLandPathT1.setText(self.surface_folder)
      
      lm_group = GetLandmarkGroup(GROUPS_LANDMARKS)
      # print(lm_group)
      available_lm,All_landmarks = GetAvailableLm(self.surface_folder,lm_group)
      # print(available_lm)
      # print(All_landmarks)
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
  def __init__(self) -> None:

    self.widget = qt.QWidget()
    layout = qt.QVBoxLayout(self.widget)

    self.LM_tab_widget = qt.QTabWidget()
    self.LM_tab_widget.minimumSize = qt.QSize(100,200)
    self.LM_tab_widget.maximumSize = qt.QSize(800,400)
    self.LM_tab_widget.setMovable(True)


    # print(self.lm_status_dic)
    # print(lcbd)
    buttons_wid = qt.QWidget()
    buttons_layout = qt.QHBoxLayout(buttons_wid)

    layout.addWidget(self.LM_tab_widget)
    layout.addWidget(buttons_wid)
    self.lm_status_dic = {}
    

  def Clear(self):
    self.LM_tab_widget.clear()

  def FillTab(self,lm_dic):

    self.lm_group_dic = lm_dic
    self.lm_group_dic["All"] = []

    cbd = {}
    lmsd = {}
    for group,lm_lst in lm_dic.items():
        for lm in lm_lst:
            if lm not in lmsd.keys():
                lmsd[lm] = False
                self.lm_group_dic["All"].append(lm)

    self.check_box_dic = cbd
    self.lm_status_dic = lmsd


    for group,lm_lst in lm_dic.items():
      lst_wid = []
      for lm in lm_lst:
        new_cb = qt.QCheckBox(lm)
        self.check_box_dic[new_cb] = lm
        lst_wid.append(new_cb)

      new_lm_tab = self.GenNewTab(lst_wid)
      self.LM_tab_widget.insertTab(0,new_lm_tab,group)
    self.LM_tab_widget.currentIndex = 0

    # print(self.check_box_dic)
    lcbd = {}
    for cb,lm in self.check_box_dic.items():
      if lm not in lcbd.keys():
        lcbd[lm] = [cb]
      else:
        lcbd[lm].append(cb)

    self.lm_cb_dic = lcbd

    for cb in self.check_box_dic.keys():
      cb.connect("toggled(bool)", self.CheckBox)
   
  def CheckBox(self, caller=None, event=None):
    for cb,lm in self.check_box_dic.items():
      if cb.checkState():
        state = True
      else:
        state = False
      
      if self.lm_status_dic[lm] != state:
        self.UpdateLmSelect(lm,state)
  
  def SelectOptions(self,idx):
    # print(idx)
    if idx == 1:
      self.SelectTab()
    elif idx == 2 :
      self.ClearTab()
    elif idx == 3:
      self.SelectAll()
    else :
      self.ClearAll()



  def GenNewTab(self,widget_lst):
      new_widget = qt.QWidget()
      vb = qt.QVBoxLayout(new_widget)
      scr_box = qt.QScrollArea()
      vb.addWidget(scr_box)
      self.buttons_options = qt.QComboBox()
      self.buttons_options.addItems(["none","Select Tab","Clear Tab","Select All","Clear All"])
      # self.buttons_options.itemIcon(qt.QIcon(":/Icons/MarkupsSelectedOrUnselected.png"))
      vb.addWidget(self.buttons_options)
      self.buttons_options.connect('currentIndexChanged(int)', self.SelectOptions)
      
      wid = qt.QWidget()
      vb2 = qt.QVBoxLayout()
      for widget in widget_lst:
          vb2.addWidget(widget)
      wid.setLayout(vb2)

      scr_box.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOn)
      scr_box.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOff)
      scr_box.setWidgetResizable(True)
      scr_box.setWidget(wid)

      return new_widget

  def UpdateLmSelect(self,lm_id,state):
    # print(lm_id,state)
    for cb in self.lm_cb_dic[lm_id]:
      cb.setChecked(state)
    self.lm_status_dic[lm_id] = state

  def UpdateAll(self,state):
    for lm_id,cb_lst in self.lm_cb_dic.items():
      for cb in cb_lst:
        cb.setChecked(state)
      self.lm_status_dic[lm_id] = state

  def Fulltab(self,state):
    idx = self.LM_tab_widget.currentIndex
    group = self.LM_tab_widget.tabText(idx)
    for lm in self.lm_group_dic[group]:
      self.UpdateLmSelect(lm,state)

  def GetSelectedLM(self):
    selectedLM = []
    for lm,state in self.lm_status_dic.items():
      if state:
        selectedLM.append(lm)
    return selectedLM

  def SelectAll(self):
    self.UpdateAll(True)
  
  def ClearAll(self):
    self.UpdateAll(False)
  
  def SelectTab(self):
    self.Fulltab(True)
  
  def ClearTab(self):
    self.Fulltab(False)

class TableView:
  def __init__(self,tableWidget) -> None:
    # self.lineEditLandPathT2 = lineEditLandPathT2
    self.tableWidget = tableWidget
    self.widget = qt.QWidget()
    self.layout = qt.QVBoxLayout(self.widget)

    self.LM_tab_widget = qt.QTabWidget()
    self.LM_tab_widget.connect('currentChanged(int)',self.Test)
    self.LM_tab_widget.minimumSize = qt.QSize(100,200)
    self.LM_tab_widget.maximumSize = qt.QSize(800,400)
    self.LM_tab_widget.setMovable(True)

    self.layout.addWidget(self.LM_tab_widget)
   
    self.dist_dic_measurment = {'point_to_point':[{'P1':'Ln1','P2':'Ln2'}],
                                'point_to_line':[{'P':'Ln1','L':{'P1':'Ln2','P2':'Ln3'}}],
                                'point_T1_to_T2':[{'PT1':'Ln1','PT2':'Ln1'}]
                              }

    # -------------------------- Gen Tab ---------------------------
    # lst_tab = ["Distance","Angle"]
    tab = "Distance"
    # print(self.lineEditLandPathT2.hasSelectedText)
    # if self.lineEditLandPathT2.hasSelectedText :
    #   lst_tab.insert(0,"Distance between T1 and T2")

    # for tab in lst_tab:   
    self.new_widget = qt.QWidget()
    self.vb = qt.QVBoxLayout(self.new_widget)
    scr_box = qt.QScrollArea()
    self.vb.addWidget(scr_box)

    wid = qt.QWidget()
    self.vb2 = qt.QVBoxLayout()
    wid.setLayout(self.vb2)
    
    self.vb2.addWidget(self.tableWidget)
    
    scr_box.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOn)
    scr_box.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOff)
    scr_box.setWidgetResizable(True)
    scr_box.setWidget(wid)
    
    self.LM_tab_widget.insertTab(-1,self.new_widget,tab)
      # self.LM_tab_widget.currentIndex = 0


    # -------------------------- Gen layout add line ---------------------------
    self.hb_add  = qt.QHBoxLayout()
    self.type_measur_combobox = qt.QComboBox()
    self.label = qt.QLabel("Type of measurment")
    self.hb_add.addWidget(self.label)
    self.hb_add.addWidget(self.type_measur_combobox)
    self.type_measur_combobox.addItems(self.lst_type_meas)
    self.type_measur_combobox.connect('currentIndexChanged(int)', self.DefinineWidget)
    self.layout.addLayout(self.hb_add)

    # -------------------------- Import/Export measurment , Compute/Export results ---------------------------
    hb = qt.QHBoxLayout()
    combobox_import_export = qt.QComboBox()
    combobox_import_export.addItems(["Import measurment","Export measurment"])
    hb.addWidget(combobox_import_export)
    combobox_compute_export = qt.QComboBox()
    combobox_compute_export.addItems(["Compute","Export results"])
    hb.addWidget(combobox_compute_export)
    self.layout.addLayout(hb)

    self.lm_status_dic = {}
    self.FillTab()

  def Test(self,idx):
    print(idx)
    # type_measur_combobox = qt.QComboBox()
    if idx == 0:
      self.lst_type_meas = ["Distance between T1 and T2","Mid point","Distance point line"]
    else:
      self.lst_type_meas = ["Angle between two lines"]
    
  def Clear(self):
    self.LM_verticalLayout_2tab_widget.clear()
  
  # def GenerateChoiceTab(self):
  #   # idx = self.LM_tab_widget.currentIndex
  #   # print(idx)
  #   if idx == 0:
  #     hb_add  = qt.QHBoxLayout()
  #     type_measur_combobox = qt.QComboBox()
  #     type_measur_combobox.addItems(["Distance between T1 and T2","Mid point","Distance point line"])
  #     hb_add.addWidget(type_measur_combobox)
  #     type_measur_combobox.connect('currentIndexChanged(int)', self.DefinineWidget)
  #     self.layout.addLayout(hb_add)

  #   else :
  #     hb_add  = qt.QHBoxLayout()
  #     type_measur_combobox = qt.QComboBox()
  #     type_measur_combobox.addItems(["Angle between two lines"])
  #     hb_add.addWidget(type_measur_combobox)
  #     type_measur_combobox.connect('currentIndexChanged(int)', self.DefinineWidget)
  #     self.layout.addLayout(hb_add)
    
  def FillTab(self):
    # "check box",
    self.columnLabels = [ "check box","type of measurment","point 1", "point 2"]
    self.tableWidget.setColumnCount(len(self.columnLabels))
    self.tableWidget.setHorizontalHeaderLabels(self.columnLabels)
    self.tableWidget.resizeColumnsToContents()
    big_list = []
    for type_measurment,lst_measurment in self.dist_dic_measurment.items():
      list_row = []
      type_measurment_label = qt.QTableWidgetItem(type_measurment)
      list_row.append(type_measurment_label)
      for dic_measurment in lst_measurment:
        checkBoxItem = qt.QTableWidgetItem()
        checkBoxItem.setCheckState(True)
        list_row.insert(0,checkBoxItem)
        for point,landmark in dic_measurment.items():
          landmark_label = qt.QTableWidgetItem(landmark)
          list_row.append(landmark_label)
      big_list.append(list_row)

    self.tableWidget.setRowCount(len(big_list))
    for row in range(len(big_list)):
      for col in range(len(self.columnLabels)):
        # item = qt.QTableWidgetItem(f'Item {row}-{col}')
        # item.setFlags(Qt.ItemFlag.ItemIsuserCheckable)
        # print(big_list[row][col])
        self.tableWidget.setItem(row,col,big_list[row][col])




    # print(list_row)
  # def FillTab(self):
  #   for type_measurment,lst_measurment in self.dist_dic_measurment.items():
  #     for dic_measurment in lst_measurment:
  #       wid = qt.QWidget()
  #       hb = qt.QHBoxLayout()
  #       wid.setLayout(hb)
  #       new_cb = qt.QCheckBox()
  #       hb.addWidget(new_cb)
  #       # print(dic_measurment)
  #       for point,landmark in dic_measurment.items():
  #         print(point,landmark)
  #         point_label = qt.QLabel(point)
  #         landmark_label = qt.QLabel(landmark)
  #         hb.addWidget(point_label)
  #         hb.addWidget(landmark_label)
  #       self.vb2.addWidget(wid)
  #   lst_tab = ['Distances','Angles']
  #   lst_wid = []
    
  #   for tab in lst_tab:   
  #     # new_lm_tab = self.GenNewTab()
  #     self.LM_tab_widget.insertTab(-1,self.new_widget,tab)

  #   self.LM_tab_widget.currentIndex = 0

    # lcbd = {}
    # for cb,lm in self.check_box_dic.items():
    #   if lm not in lcbd.keys():
    #     lcbd[lm] = [cb]
    #   else:
    #     lcbd[lm].append(cb)

    # self.lm_cb_dic = lcbd

    # for lm in lm_dic["U"]:
    #   self.UpdateLmSelect(lm,True)

    # for cb in self.check_box_dic.keys():
    #   cb.connect("toggled(bool)", self.CheckBox)

  def CheckBox(self, caller=None, event=None):
    for cb,lm in self.check_box_dic.items():
      if cb.checkState():
        state = True
      else:
        state = False
      
      if self.lm_status_dic[lm] != state:
        self.UpdateLmSelect(lm,state)

  def GenNewLine(self):
    combo_box_1 = qt.QComboBox()
    # self.combo_box_1.addItems()
    combo_box_2 = qt.QComboBox()
    # self.combo_box_2.addItems()
    combo_box_3 = qt.QComboBox()
    # self.combo_box_3.addItems()
    remove_button = qt.QPushButton("Delete")
    widget_lst = [combo_box_1,combo_box_2,combo_box_3,remove_button]
    
    # wid = qt.QWidget()
    hb = qt.QHBoxLayout()
    for widget in widget_lst:
        hb.addWidget(widget)
    self.vb2.addLayout(hb)
    # wid.setLayout(hb)
    
    # self.scr_box.setWidget(wid)

  # def GenNewTab(self):
  #   new_widget = qt.QWidget()
  #   self.vb = qt.QVBoxLayout(new_widget)
  #   scr_box = qt.QScrollArea()
  #   self.vb.addWidget(scr_box)

  #   self.hb_add  = qt.QHBoxLayout()
  #   self.type_measur_combobox = qt.QComboBox()
  #   self.type_measur_combobox.addItems(["Distance between T1 and T2","Mid point","Distance point line"])
  #   self.hb_add.addWidget(self.type_measur_combobox)
  #   self.type_measur_combobox.connect('currentIndexChanged(int)', self.DefinineWidget)
  #   self.vb.addLayout(self.hb_add)

  #   wid = qt.QWidget()
  #   self.vb2 = qt.QVBoxLayout()
  #   wid.setLayout(self.vb2)

  #   scr_box.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOn)
  #   scr_box.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOff)
  #   scr_box.setWidgetResizable(True)
  #   scr_box.setWidget(wid)

  #   return new_widget


  def DefinineWidget(self,idx):
    # index_tab = self.LM_tab_widget.currentIndex
    print('index_tab :',index_tab)
    print('index combo box :', idx)
    hbwi = qt.QHBoxLayout()
    if idx == 2:
      point_1_combobox = qt.QComboBox()
      point_2_combobox = qt.QComboBox()
      point_3_combobox = qt.QComboBox()
      button_add = qt.QPushButton("Add")
      button_add.connect('clicked(bool)', self.GenNewLine)

      hbwi.addWidget(point_1_combobox)
      hbwi.addWidget(point_2_combobox)
      hbwi.addWidget(point_3_combobox)
      hbwi.addWidget(button_add)

    elif idx == 3:
      point_1_combobox = qt.QComboBox()
      point_2_combobox = qt.QComboBox()
      point_3_combobox = qt.QComboBox()
      point_4_combobox = qt.QComboBox()
      button_add = qt.QPushButton("Add")
      button_add.connect('clicked(bool)', self.GenNewLine)

      hbwi.addWidget(point_1_combobox)
      hbwi.addWidget(point_2_combobox)
      hbwi.addWidget(point_3_combobox)
      hbwi.addWidget(point_4_combobox)
      hbwi.addWidget(button_add)
    
    else :
      point_1_combobox = qt.QComboBox()
      point_2_combobox = qt.QComboBox()
      button_add = qt.QPushButton("Add")
      button_add.connect('clicked(bool)', self.GenNewLine)

      hbwi.addWidget(point_1_combobox)
      hbwi.addWidget(point_2_combobox)
      hbwi.addWidget(button_add)
        
    self.vb.addLayout(hbwi)


  def UpdateLmSelect(self,lm_id,state):
    for cb in self.lm_cb_dic[lm_id]:
      cb.setChecked(state)
    self.lm_status_dic[lm_id] = state

  def UpdateAll(self,state):
    for lm_id,cb_lst in self.lm_cb_dic.items():
      for cb in cb_lst:
        cb.setChecked(state)
      self.lm_status_dic[lm_id] = state

  def GetSelectedLM(self):
    selectedLM = []
    for lm,state in self.lm_status_dic.items():
      if state:
        selectedLM.append(lm)
    return selectedLM

  def SelectAll(self):
    self.UpdateAll(True)
  
  def ClearAll(self):
    self.UpdateAll(False)


def GetAvailableLm(mfold,lm_group):
  All_landmarks = GetAllLandmarks(mfold)
  print(All_landmarks)
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

  return available_lm,All_landmarks


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
        label = controlPoints[i]["label"]
        if label not in All_landmarks:
          All_landmarks.append(label)

  return All_landmarks

class TabMeasure:
  def __init__(self) -> None:
    self.widget = qt.QWidget()
    self.layout = qt.QVBoxLayout(self.widget)
    
    self.new_widget_1 = qt.QWidget()
    self.hb1 = qt.QHBoxLayout(self.new_widget_1)
    self.new_widget_2 = qt.QWidget()
    self.hb2 = qt.QHBoxLayout(self.new_widget_2)    
    self.new_widget_3 = qt.QWidget()
    self.hb3 = qt.QHBoxLayout(self.new_widget_3)

    self.new_widget_2.setHidden(True)
    self.new_widget_3.setHidden(True)

    # -------------------------- Gen layout T1 T2/midpoint ---------------------------
    combo_box_1 = qt.QComboBox()
    combo_box_2 = qt.QComboBox()
    remove_button = qt.QPushButton("add")
    widget_lst = [combo_box_1,combo_box_2,remove_button]
    for widget in widget_lst:
        self.hb1.addWidget(widget)
    self.layout.addWidget(self.new_widget_1)

    # -------------------------- Gen layout point line ---------------------------
    combo_box_1 = qt.QComboBox()
    combo_box_2 = qt.QComboBox()
    combo_box_3 = qt.QComboBox()
    remove_button = qt.QPushButton("add")
    widget_lst = [combo_box_1,combo_box_2,combo_box_3,remove_button]
    for widget in widget_lst:
        self.hb2.addWidget(widget)
    self.layout.addWidget(self.new_widget_2)
    # -------------------------- Gen layout angle ---------------------------
    combo_box_1 = qt.QComboBox()
    combo_box_2 = qt.QComboBox()
    combo_box_3 = qt.QComboBox()
    combo_box_4 = qt.QComboBox()
    remove_button = qt.QPushButton("add")
    widget_lst = [combo_box_1,combo_box_2,combo_box_3,combo_box_4,remove_button]
    for widget in widget_lst:
        self.hb3.addWidget(widget)
    self.layout.addWidget(self.new_widget_3)

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

  def createDistanceTable(cls):
    names = 'R-L Component', 'A-P Component', 'S-I Component', '3D Distance'
    return cls.createTable(names)
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
