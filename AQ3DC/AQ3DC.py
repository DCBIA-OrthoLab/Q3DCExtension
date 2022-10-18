from email.message import Message
import os
import unittest
import logging
from warnings import WarningMessage
from xmlrpc.client import Boolean
import vtk, qt, ctk, slicer
import glob
import numpy as np
import collections
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import csv
import json
from qt import QWidget, QVBoxLayout, QScrollArea, QCheckBox, QStandardItemModel, QTableWidgetItem

#
# AQ3DC
#
try:
  import pandas as pd

except: 
  slicer.util.pip_install('pandas')


try :
  import openpyxl
except:
  slicer.util.pip_install('openpyxl')
  #we need this package because pandas use it
GROUPS_LANDMARKS = {
  'Cranial Base/Vertebra' : ['Ba', 'S', 'N', 'RPo', 'LPo', 'RFZyg', 'LFZyg'],#, 'C2', 'C3', 'C4'],

  'Maxilla' : ['RInfOr', 'LInfOr', 'LMZyg', 'RPF', 'LPF', 'PNS', 'ANS', 'A', 'UR3O', 'UR1O', 'UL3O', 'UR6DB', 'UR6MB', 'UL6MB', 'UL6DB', 'IF', 'ROr', 'LOr', 'RMZyg', 'RNC', 'LNC', 'UR7O', 'UR5O', 'UR4O', 'UR2O', 'UL1O', 'UL2O', 'UL4O', 'UL5O', 'UL7O', 'UL7R', 'UL5R', 'UL4R', 'UL2R', 'UL1R', 'UR2R', 'UR4R', 'UR5R', 'UR7R', 'UR6MP', 'UL6MP', 'UL6R', 'UR6R', 'UR6O', 'UL6O', 'UL3R', 'UR3R', 'UR1R'],

  'Mandible' : ['RCo', 'RGo', 'Me', 'Gn', 'Pog', 'PogL', 'B', 'LGo', 'LCo', 'LR1O', 'LL6MB', 'LL6DB', 'LR6MB', 'LR6DB', 'LAF', 'LAE', 'RAF', 'RAE', 'LMCo', 'LLCo', 'RMCo', 'RLCo', 'RMeF', 'LMeF', 'RSig', 'RPRa', 'RARa', 'LSig', 'LARa', 'LPRa', 'LR7R', 'LR5R', 'LR4R', 'LR3R', 'LL3R', 'LL4R', 'LL5R', 'LL7R', 'LL7O', 'LL5O', 'LL4O', 'LL3O', 'LL2O', 'LL1O', 'LR2O', 'LR3O', 'LR4O', 'LR5O', 'LR7O', 'LL6R', 'LR6R', 'LL6O', 'LR6O', 'LR1R', 'LL1R', 'LL2R', 'LR2R'],
  
  "Dental" : ['CL','CB','O','DB','MB','R','RIP','OIP'],

  'Other' : []

}

DICO_TEETH = {"Lower" :  ['LL7','LL6','LL5','LL4','LL3','LL2','LL1','LR1','LR2','LR3','LR4','LR5','LR6','LR7'],
              "Upper" : ['UL7','UL6','UL5','UL4','UL3','UL2','UL1','UR1','UR2','UR3','UR4','UR5','UR6','UR7'] }


MID_POINTS = []

ORDER_TAB = {'Maxilla':0,'Mandible':1,'Cranial Base/Vertebra':2,"Dental":3,'Other':4,'Midpoint':5}

upper_right_back = ['UR8','UR7','UR6','UR5','UR4','UR3']
upper_right_front = ['UR1','UR2']
upper_left_back = ['UL8','UL7','UL6','UL5','UL4','UL3']
upper_left_front = ['UL1','UL2']
lower_right_back = ['LR8','LR7','LR6','LR5','LR4','LR3']
lower_right_front = ['LR1','LR2']
lower_left_back = ['LL8','LL7','LL6','LL5','LL4','LL3']
lower_left_front = ['LL1','LL2']



'''
TODO :  next step import export measure
        comment all code
       create file ui for warning

      put all class variable in setup with comment

      organize function
      add measure Distance between 2 points T1 T2
      error with computation angle
      
   
'''







print("-------------------------------AQ3DC---------------------------------")
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


    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)


    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()











    """
 __     __     _      ____    ___      _      ____    _       _____   ____  
 \ \   / /    / \    |  _ \  |_ _|    / \    | __ )  | |     | ____| / ___| 
  \ \ / /    / _ \   | |_) |  | |    / _ \   |  _ \  | |     |  _|   \___ \ 
   \ V /    / ___ \  |  _ <   | |   / ___ \  | |_) | | |___  | |___   ___) |
    \_/    /_/   \_\ |_| \_\ |___| /_/   \_\ |____/  |_____| |_____| |____/ 
                                                                                                                                                 
     """




                                                                            
    self.list_CbLandmark = [self.ui.CbMidpointP1,self.ui.CbMidpointP2,
              self.ui.CbAB2LT1P1,self.ui.CbAB2LT1P2,self.ui.CbAB2LT1P3,self.ui.CbAB2LT1P4,
              self.ui.CbAB2LT1T2P1T1, self.ui.CbAB2LT1T2P1T2, self.ui.CbAB2LT1T2P2T1, self.ui.CbAB2LT1T2P2T2,
              self.ui.CbAB2LT1T2P3T1, self.ui.CbAB2LT1T2P4T1, self.ui.CbAB2LT1T2P3T2, self.ui.CbAB2LT1T2P4T2,
              self.ui.CbALT1T2L1P1, self.ui.CbALT1T2L1P2, self.ui.CbALT1T2L2P3, self.ui.CbALT1T2L2P4,
              self.ui.CbD2PP1, self.ui.CbD2PP2,
              self.ui.CbDPLT1T2L1T1, self.ui.CbDPLT1T2L2T1, self.ui.CbDPLT1T2L2T2, self.ui.CbDPLT1T2P1T1, self.ui.CbDPLT1T2P1T2,self.ui.CbDPLT1T2L1T2,
              self.ui.CbDPLT1L1, self.ui.CbDPLT1L2, self.ui.CbDPLT1P1]

    self.list_LandMarkCheck=[]
    self.dic_patient_T1 = None
    self.dic_patient_T2 = None
    self.list_measure=[]

    self.GROUPS_LANDMARKS = {
  'Cranial Base/Vertebra' : ['Ba', 'S', 'N', 'RPo', 'LPo', 'RFZyg', 'LFZyg'],#, 'C2', 'C3', 'C4'],

  'Maxilla' : ['RInfOr', 'LInfOr', 'LMZyg', 'RPF', 'LPF', 'PNS', 'ANS', 'A', 'UR3O', 'UR1O', 'UL3O', 'UR6DB', 'UR6MB', 'UL6MB', 'UL6DB', 'IF', 'ROr', 'LOr', 'RMZyg', 'RNC', 'LNC', 'UR7O', 'UR5O', 'UR4O', 'UR2O', 'UL1O', 'UL2O', 'UL4O', 'UL5O', 'UL7O', 'UL7R', 'UL5R', 'UL4R', 'UL2R', 'UL1R', 'UR2R', 'UR4R', 'UR5R', 'UR7R', 'UR6MP', 'UL6MP', 'UL6R', 'UR6R', 'UR6O', 'UL6O', 'UL3R', 'UR3R', 'UR1R'],

  'Mandible' : ['RCo', 'RGo', 'Me', 'Gn', 'Pog', 'PogL', 'B', 'LGo', 'LCo', 'LR1O', 'LL6MB', 'LL6DB', 'LR6MB', 'LR6DB', 'LAF', 'LAE', 'RAF', 'RAE', 'LMCo', 'LLCo', 'RMCo', 'RLCo', 'RMeF', 'LMeF', 'RSig', 'RPRa', 'RARa', 'LSig', 'LARa', 'LPRa', 'LR7R', 'LR5R', 'LR4R', 'LR3R', 'LL3R', 'LL4R', 'LL5R', 'LL7R', 'LL7O', 'LL5O', 'LL4O', 'LL3O', 'LL2O', 'LL1O', 'LR2O', 'LR3O', 'LR4O', 'LR5O', 'LR7O', 'LL6R', 'LR6R', 'LL6O', 'LR6O', 'LR1R', 'LL1R', 'LL2R', 'LR2R'],
  
  "Dental" : ['CL','CB','O','DB','MB','R','RIP','OIP']

}
    """
 __     __     _      ____    ___      _      ____    _       _____   ____  
 \ \   / /    / \    |  _ \  |_ _|    / \    | __ )  | |     | ____| / ___| 
  \ \ / /    / _ \   | |_) |  | |    / _ \   |  _ \  | |     |  _|   \___ \ 
   \ V /    / ___ \  |  _ <   | |   / ___ \  | |_) | | |___  | |___   ___) |
    \_/    /_/   \_\ |_| \_\ |___| /_/   \_\ |____/  |_____| |_____| |____/ 
                                                                                                                                                 
    """


















    """
 __        __  ___   ____     ____   _____   _____      ____    ___    _   _   _   _   _____    ____   _____ 
 \ \      / / |_ _| |  _ \   / ___| | ____| |_   _|    / ___|  / _ \  | \ | | | \ | | | ____|  / ___| |_   _|
  \ \ /\ / /   | |  | | | | | |  _  |  _|     | |     | |     | | | | |  \| | |  \| | |  _|   | |       | |  
   \ V  V /    | |  | |_| | | |_| | | |___    | |     | |___  | |_| | | |\  | | |\  | | |___  | |___    | |  
    \_/\_/    |___| |____/   \____| |_____|   |_|      \____|  \___/  |_| \_| |_| \_| |_____|  \____|   |_|  
                                                                                                             
    """





    self.ui.TabLandmarks.clear()
    self.ui.TabMeasure.currentChanged.connect(self.manageCblistMeasurement)
    self.ui.CbListMeasurement.activated.connect(self.managepage)
    self.ui.CheckBoxT1T2.toggled.connect(self.manageCblistMeasurement)
    self.ui.ButtonPathT1.clicked.connect(self.connectButtonPathT1)
    self.ui.ButtonPathT2.clicked.connect(self.connectButtonPathT2)
    self.ui.ButtonImportLandmarks.clicked.connect(self.ImportLandmarks)
    self.ui.ButtonSelectTabLandmarks.clicked.connect(self.SelectAllLandmarks)
    self.ui.ButtonClearTabLandmarks.clicked.connect(self.ClearAllLandmarks)
    self.ui.ButtonAddMidpoint.clicked.connect(self.AddMidpoint)
    self.ui.ButtonFolderMidpoint.clicked.connect(self.FolderMidpoint)
    self.ui.ButtonSaveMidpoint.clicked.connect(self.SaveMidpoint)
    self.ui.ButtonAddMeasure.clicked.connect(self.test)
    self.ui.ButtonDeleteMeasurement.clicked.connect(self.RemoveMeasureTabMeasure)
    self.ui.CbImportExportMeasure.activated.connect(self.ManageStakedImportExportMeasure)
    self.ui.ButtonFolderExportMeasure.clicked.connect(self.FolderExportMeasure)
    self.ui.ButtonFileImportMeasure.clicked.connect(self.FileImportMeasure)
    self.ui.ButtonExportMeasure.clicked.connect(self.ExportMeasure)
    self.ui.ButtonImportMeasure.clicked.connect(self.ImportMeasure)
    self.ui.ButtonCompute.clicked.connect(self.Computation)
    self.ui.ButtonFolderCompute.clicked.connect(self.ComputationFolder)



    """
 __        __  ___   ____     ____   _____   _____      ____    ___    _   _   _   _   _____    ____   _____ 
 \ \      / / |_ _| |  _ \   / ___| | ____| |_   _|    / ___|  / _ \  | \ | | | \ | | | ____|  / ___| |_   _|
  \ \ /\ / /   | |  | | | | | |  _  |  _|     | |     | |     | | | | |  \| | |  \| | |  _|   | |       | |  
   \ V  V /    | |  | |_| | | |_| | | |___    | |     | |___  | |_| | | |\  | | |\  | | |___  | |___    | |  
    \_/\_/    |___| |____/   \____| |_____|   |_|      \____|  \___/  |_| \_| |_| \_| |_____|  \____|   |_|  
                                                                                                             
    """

  def ComputationFolder(self):
    computation_folder = qt.QFileDialog.getExistingDirectory(self.parent, "Select a scan folder")
    if computation_folder != '' :
      self.ui.LineEditFolderComputation.setText(computation_folder)



  def Computation(self):
    print(self.dic_patient_T1["P10"])
    path = self.ui.LineEditFolderComputation.text
    file_name = self.ui.LineEditComputationFile.text
    if path != '' and (file_name!='.xlsx' or ''):
      print("Computation")
      patient_compute = self.logic.ComputeManager(self.list_measure,self.dic_patient_T1)
      print("During computation")
      print(patient_compute)
      self.logic.GenMeasurementExcel(patient_compute,path,file_name)



  def ManageStakedImportExportMeasure(self):
    dic = {"None":0,'Import list of measurements':1,"Export list of measurements":2}
    choice = self.ui.CbImportExportMeasure.currentText
    self.ui.StackedImportExport.setCurrentIndex(dic[choice])

  def FolderExportMeasure(self):
    measure_folder = qt.QFileDialog.getExistingDirectory(self.parent, "Select a scan folder")
    if measure_folder != '' :
      self.ui.LineEditFolderExportMeasure.setText(measure_folder)


  def ExportMeasure(self):
      name_file = self.ui.LineEditFileExportMeasure.text
      measure_folder = self.ui.LineEditFolderExportMeasure.text
      if name_file != '' and measure_folder != '':
        
        self.logic.OnExportMeasurement(measure_folder+'/'+name_file,self.list_measure)


  def FileImportMeasure(self):
    file_measure = qt.QFileDialog.getOpenFileName(self.parent,"Select file")
    if file_measure != '':
      self.ui.LineEditImportMeasure.setText(file_measure)


  def ImportMeasure(self):
    print("--"*5,"import measure",'--'*5)
    list_measure = self.logic.OnImportMeasure(self.ui.LineEditImportMeasure.text)
    print(list_measure)
    for measure in list_measure:
      self.AddMeasureTabMeasure(measure)


  def test(self):
    print("--"*5,"call manager measure",'--'*5)
    out = []

    dic_page2combobox = {  "PageAngleBetween2LinesT1":[    self.ui.CbAB2LT1P1,self.ui.CbAB2LT1P2,self.ui.CbAB2LT1P3,self.ui.CbAB2LT1P4],
             "PageAngleBetween2LinesT1T2":[ self.ui.CbAB2LT1T2P1T1, self.ui.CbAB2LT1T2P2T1, self.ui.CbAB2LT1T2P1T2 , self.ui.CbAB2LT1T2P2T2,
              self.ui.CbAB2LT1T2P3T1, self.ui.CbAB2LT1T2P4T1, self.ui.CbAB2LT1T2P3T2, self.ui.CbAB2LT1T2P4T2],
              "PageAngleLineT1T2":[self.ui.CbALT1T2L1P1, self.ui.CbALT1T2L1P2, self.ui.CbALT1T2L2P3, self.ui.CbALT1T2L2P4],
              "PageDistance2Points" : [self.ui.CbD2PP1, self.ui.CbD2PP2],
              "PageDistancePointLineT1T2" :[ self.ui.CbDPLT1T2P1T1, self.ui.CbDPLT1T2L1T1, self.ui.CbDPLT1T2L2T1,self.ui.CbDPLT1T2P1T2,self.ui.CbDPLT1T2L1T2, self.ui.CbDPLT1T2L2T2 ],

              "PageDistancePointLineT1":[self.ui.CbDPLT1L1, self.ui.CbDPLT1L2, self.ui.CbDPLT1P1]}


    dic_page2namemeasure = {"PageDistancePointLineT1":"Distance point line T1","PageDistancePointLineT1T2":"Distance between 2 points dif T1 T2",
                        "PageAngleBetween2LinesT1":"Angle between 2 lines T1","PageAngleBetween2LinesT1T2":"Angle between 2 lines dif T1 T2","PageDistance2Points":"Distance between 2 points T1",
                        "PageDistancePointLineT1T2":"Distance point line dif T1 T2","PageAngleLineT1T2" : "Angle line T1 and line T2"}


  

    page = self.ui.StackedMeasure.currentWidget().name
    list_point=[]
    for point in dic_page2combobox[page] :
      list_point.append(point.currentText)

    out = self.logic.CreateMeasure(dic_page2namemeasure[page],list_point)
   



    print("list of measure to add ",out,page)
    for measure in out :
      self.AddMeasureTabMeasure(measure)

    print('--'*5,"fin manage measure",'--'*5)
    

    



  def ImportLandmarks(self):
    """Open window to chose the file with a file with all landmark that use doctor
    add landmark in the tablandmarks and up date combo box with all landmark



    idea for next time, if you want to display landmark

    """
    dic_landmarks = {}
    path_listlandmarks = qt.QFileDialog.getOpenFileName(self.parent,"Select file")
    if path_listlandmarks != '':
      self.ui.LineEditImportLandmarks.setText(path_listlandmarks)
      reader = pd.read_excel(path_listlandmarks)

      for header in reader.keys() :
        #if header != "Unnamed":
        dic_landmarks[header]=[]
        for landmarks in reader[header].tolist() :
          if type(landmarks) == str :
            dic_landmarks[header].append(landmarks)

      self.GROUPS_LANDMARKS = dic_landmarks
      list_landmarks, self.GROUPS_LANDMARKS = self.logic.CheckAllPatientSameLm( self.dic_patient_T1 ,self.GROUPS_LANDMARKS)
      self.ManageTabLandmarks(list_landmarks, self.GROUPS_LANDMARKS)

      self.manageCblistMeasurement()













  def connectButtonPathT1(self):

    surface_folder = qt.QFileDialog.getExistingDirectory(self.parent, "Select a scan folder")
    if surface_folder != '' :
      self.ui.LineEditPathT1.setText(surface_folder)
      self.list_patient_T1, self.dic_patient_T1, lst_files = self.logic.CreateDicPatient(surface_folder)

      list_landmarks, self.GROUPS_LANDMARKS = self.logic.CheckAllPatientSameLm( self.dic_patient_T1 ,self.GROUPS_LANDMARKS)
      self.ManageTabLandmarks(list_landmarks, self.GROUPS_LANDMARKS)







  def connectButtonPathT2(self):
    if self.dic_patient_T1 == None:
      self.warningMessage('Missing T1 folder')
    else :

      surface_folder = qt.QFileDialog.getExistingDirectory(self.parent, "Select a scan folder")
      if surface_folder != '' :
        self.ui.LineEditPathT2.setText(surface_folder)
        self.lst_patient_T2, self.dic_patient_T2, lst_files = self.logic.CreateDicPatient(surface_folder)
        self.logic.compareT1T2(self.dic_patient_T1, self.dic_patient_T2)









  def ManageTabLandmarks(self,list_landmarks : list ,dico_landmarks : dict ):
    self.ui.TabLandmarks.clear()
    self.dic_checkbox = {}
    self.dic_Checkbox2Landmark ={}
    self.dic_Landmark2Checkbox ={}
    self.dic_Group2Layout = {}


    index = 0
    for group , landmarks in dico_landmarks.items():

      self.addGroupTabLandmarks(group,index)

      for landmark in landmarks :
        status = True
        if not landmark in list_landmarks :
          status = False

        self.addLandmarksTabLandmarks(group,landmark,status)

      index += 1 

    #for remove all checkbox
    self.list_LandMarkCheck=[]
    self.ComboboxManageLandmark()


  def addGroupTabLandmarks(self,group : str, index : int):
    

    new_widget = QWidget()
    new_widget.setMinimumHeight(250)

    layout = QVBoxLayout(new_widget)

    scr_box = QScrollArea(new_widget)
    scr_box.setMinimumHeight(200)

    layout.addWidget(scr_box)

    new_widget2 = QWidget(scr_box)
    layout2 = QVBoxLayout(new_widget2)

    
    layout.addStretch()
    scr_box.setWidgetResizable(True)
    scr_box.setWidget(new_widget2)

    
    self.ui.TabLandmarks.insertTab(index,new_widget,group)



    self.dic_checkbox[group]=[]
    self.dic_Group2Layout[group]=[layout2,scr_box]




  def addLandmarksTabLandmarks(self,group : str , landmark : str, status : bool ):
      check = QCheckBox(landmark)
      check.setEnabled(status)
      self.dic_Checkbox2Landmark[check]=[landmark,status,group]
      self.dic_Landmark2Checkbox[landmark]=[check,status]
      self.dic_checkbox[group].append(check)
      check.connect("toggled(bool)" ,self.CheckboxTabLandmarks)
      self.dic_Group2Layout[group][0].addWidget(check)

      # parent =  self.dic_Group2Layout[group][1]
      # parent.adjustSize()









      





  def CheckboxTabLandmarks(self):
    self.list_LandMarkCheck=[]
    for group, lst_checkbox in self.dic_checkbox.items():
      for checkbox in lst_checkbox:

        if checkbox.checkState():
          self.list_LandMarkCheck.append(self.dic_Checkbox2Landmark[checkbox][0])
    self.ComboboxManageLandmark()




  def ComboboxManageLandmark(self):
    """manage landmark in each combo box 
    """
    for Cb in self.list_CbLandmark :
      Cb.clear()
      Cb.addItems(self.list_LandMarkCheck)

  

  def SelectAllLandmarks(self):
    self.TabSelectLandmarks(True)

  
  def ClearAllLandmarks(self):
    self.TabSelectLandmarks(False)



  def TabSelectLandmarks(self,status : bool):
    """Check or decheck all checkbox enable in tanlandmark open in utilisator interface

    Args:
        status (bool): True -> check all checkbox in tablandmark open
                        False -> decheck all checkbox in tablandmark open
    """
    index = self.ui.TabLandmarks.currentIndex
    group =self.ui.TabLandmarks.tabText(index)
    print(group)
    for landmark in self.GROUPS_LANDMARKS[group]:
      if self.dic_Landmark2Checkbox[landmark][1]:
        self.dic_Landmark2Checkbox[landmark][0].setChecked(status)
        print(landmark)
    
    self.ComboboxManageLandmark()




  def AddMidpoint(self):
    """
    Add midpoint in tablandmark 
    """
    P1 = self.ui.CbMidpointP1.currentText
    P2 = self.ui.CbMidpointP2.currentText
    mid_point = 'Mid_'+ P1 +'_'+P2
    MID_POINTS.append(mid_point)
    if not 'Midpoint' in self.GROUPS_LANDMARKS.keys():
      self.GROUPS_LANDMARKS['Midpoint']=[]
    self.GROUPS_LANDMARKS['Midpoint'].append(mid_point)

    if not 'Midpoint' in self.dic_Group2Layout :
      index = 0
      for i in self.dic_Group2Layout.keys():
        index+=1

      self.addGroupTabLandmarks('Midpoint',index )

    self.addLandmarksTabLandmarks('Midpoint', mid_point, True)



  def FolderMidpoint(self):
    folder_midpoint = qt.QFileDialog.getExistingDirectory( self.parent, "Select a scan folder")
    if folder_midpoint != '':
      self.ui.LineEditPathMidpoint.setText(folder_midpoint)


  def SaveMidpoint(self):
    out_path_T1 = self.ui.LineEditPathMidpoint.text + '/T1'
    out_path_T2 = self.ui.LineEditPathMidpoint.text + '/T2'
    # print(self.patients_lst_T1,self.patients_dict_T1)
    if not os.path.exists(out_path_T1):
      os.makedirs(out_path_T1)
    self.logic.SaveJson(self.list_patient_T1,self.dic_patient_T1,out_path_T1)
    if self.ui.LineEditPathT2.text != '':
      if not os.path.exists(out_path_T2):
        os.makedirs(out_path_T2)
      self.logic.SaveJson(self.lst_patient_T2,self.dic_patient_T2,out_path_T2)







  def AddMeasureTabMeasure(self,measure):
    dic_typeofmeasure2group = {"Distance between 2 points":"Distance","Distance point line":"Distance",'Angle between 2 lines':"Angle",'Angle between 2 lines T1':"Angle",
                            'Angle between 2 lines':"Angle",'Angle line T1 and line T2':"Angle",
                               "Angle between 2 lines":"Angle"}
    
    for allmeasure in self.list_measure :
      print(allmeasure,measure)
      if allmeasure == measure:
        print('--'*5,"never double",'--'*5)
        print(allmeasure, measure)
        return
    
    
    num = 0
    group = dic_typeofmeasure2group[measure["Type of measurement"]]
    for lmeasure in self.list_measure :
      if group == dic_typeofmeasure2group[lmeasure["Type of measurement"]]:
        num += 1
    dic={"Distance":self.ui.TableDistance,"Angle":self.ui.TableAngle}
    dic[group].setRowCount(num+1) 
    a =QCheckBox()
    dic[group].setCellWidget(num, 0 , a)


    for count , value in enumerate(measure):
      b = QTableWidgetItem(value)
      dic[group].setItem(num,count+1,b)

    measure["checkbox"] = a
    self.list_measure.append(measure)

    
    

    

  def RemoveMeasureTabMeasure(self):
    print('--'*5,"call remove measure",'--'*5)
    print(self.list_measure)
    dic_typeofmeasure2group = {"Distance between 2 points":"Distance","Distance point line":"Distance",'Angle between 2 lines':"Angle",'Angle between 2 lines T1':"Angle",
                            'Angle between 2 lines':"Angle",'Angle line T1 and line T2':"Angle",
                               "Angle between 2 lines":"Angle"}
    text  = self.ui.TabMeasure.currentWidget().name
    text = text[3:]

    dic_table={"Distance":self.ui.TableDistance,"Angle":self.ui.TableAngle}


    row_remove=[]
    i = 0
    for count , measure in enumerate(self.list_measure):

      if dic_typeofmeasure2group[measure["Type of measurement"]] == text :
        if measure["checkbox"].checkState():
          dic_table[text].removeRow(i-len(row_remove))
          row_remove.append(count-len(row_remove))

 

        i+=1


    for idremove in row_remove:
      self.list_measure.pop(idremove)

    print(self.list_measure)
    print('--'*5,'end remove measure','--'*5)




  










  """
  ____    _                    _        __  __                                                                         _   
 / ___|  | |_    __ _    ___  | | __   |  \/  |   ___    __ _   ___   _   _   _ __    ___   _ __ ___     ___   _ __   | |_ 
 \___ \  | __|  / _` |  / __| | |/ /   | |\/| |  / _ \  / _` | / __| | | | | | '__|  / _ \ | '_ ` _ \   / _ \ | '_ \  | __|
  ___) | | |_  | (_| | | (__  |   <    | |  | | |  __/ | (_| | \__ \ | |_| | | |    |  __/ | | | | | | |  __/ | | | | | |_ 
 |____/   \__|  \__,_|  \___| |_|\_\   |_|  |_|  \___|  \__,_| |___/  \__,_| |_|     \___| |_| |_| |_|  \___| |_| |_|  \__|
                                                                                                                           
                                                                                         
  """


  def managepage(self):
      """_summary_
      Manage StackedMeasure to display the good page in function TabMeasure, CheckboxT1T2 and ComboBox

      This function is called by self.ui.CbListMeasurement and self.manageCbListMeasurement
      """
      text = self.ui.CbListMeasurement.currentText
      currentTab = self.ui.TabMeasure.currentWidget().name
      dic = {'TabDistance':{False:{"Distance point line":1,"Distance between 2 points":0},
                          True:{"Distance point line":2,"Distance between 2 points":0}},
              'TabAngle':{False:{"Angle between 2 lines":3},
                          True:{"Angle between 2 lines":4,'Angle line T1 and line T2':5}}}
      #print("cb: ",text,", tab : ",currentTab,", indice : ",dic[currentTab][self.ui.CheckBoxT1T2.isChecked()][text])
      self.ui.StackedMeasure.setCurrentIndex(dic[currentTab][self.ui.CheckBoxT1T2.isChecked()][text])





  def manageCblistMeasurement(self):
    """_summary_
    Manage items in CbListMeasurement in function TabMeasure and CheckboxT1T2
    And update StackedMeasure with self.managepage

    This function is calld by TabMeasure and CheckBoxT1T2
    """
    currentTab = self.ui.TabMeasure.currentWidget().name
    for i in range(self.ui.CbListMeasurement.count):
      self.ui.CbListMeasurement.removeItem(0)

    if currentTab == "TabDistance":
      self.ui.CbListMeasurement.addItems(["Distance point line","Distance between 2 points"])
    else :
      if self.ui.CheckBoxT1T2.isChecked() == True :
        self.ui.CbListMeasurement.addItem("Angle line T1 and line T2")
      self.ui.CbListMeasurement.addItem("Angle between 2 lines")
    self.managepage()





  """
  ____    _                    _        __  __                                                                         _   
 / ___|  | |_    __ _    ___  | | __   |  \/  |   ___    __ _   ___   _   _   _ __    ___   _ __ ___     ___   _ __   | |_ 
 \___ \  | __|  / _` |  / __| | |/ /   | |\/| |  / _ \  / _` | / __| | | | | | '__|  / _ \ | '_ ` _ \   / _ \ | '_ \  | __|
  ___) | | |_  | (_| | | (__  |   <    | |  | | |  __/ | (_| | \__ \ | |_| | | |    |  __/ | | | | | | |  __/ | | | | | |_ 
 |____/   \__|  \__,_|  \___| |_|\_\   |_|  |_|  \___|  \__,_| |___/  \__,_| |_|     \___| |_| |_| |_|  \___| |_| |_|  \__|
                                                                                                                           
                                                                                         
  """



















  """
   ___    _     _                   
  / _ \  | |_  | |__     ___   _ __ 
 | | | | | __| | '_ \   / _ \ | '__|
 | |_| | | |_  | | | | |  __/ | |   
  \___/   \__| |_| |_|  \___| |_|   
                                    
  """



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









  def warningMessage(self,message):
      messageBox = ctk.ctkMessageBox()
      messageBox.setWindowTitle(" /!\ WARNING /!\ ")
      messageBox.setIcon(messageBox.Warning)
      messageBox.setText(message)
      messageBox.setStandardButtons(messageBox.Ok)
      messageBox.exec_()



  """
   ___    _     _                   
  / _ \  | |_  | |__     ___   _ __ 
 | | | | | __| | '_ \   / _ \ | '__|
 | |_| | | |_  | | | | |  __/ | |   
  \___/   \__| |_| |_|  \___| |_|   
                                    
  """





















#============================================================================================================================#
#     _       ___    _____   ____     ____   _                       _        
#    / \     / _ \  |___ /  |  _ \   / ___| | |       ___     __ _  (_)   ___ 
#   / _ \   | | | |   |_ \  | | | | | |     | |      / _ \   / _` | | |  / __|
#  / ___ \  | |_| |  ___) | | |_| | | |___  | |___  | (_) | | (_| | | | | (__ 
# /_/   \_\  \__\_\ |____/  |____/   \____| |_____|  \___/   \__, | |_|  \___|
#                                                            |___/            
#============================================================================================================================#

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













  def CreateDicPatient(self,dir_path : str) -> tuple[list,dict,list] :
    
    """
    Read each file in the folder, or file in folder in folder. Return all necessety information (patient, landmark) and list file in folder
    Read only .json file.
    Args:
        dir_path (str):  The path is folder path with all landmarks of all patient. The folder can contain an other folder with 

    Returns:
        list : list of patients 
        dict : dict with num of patient and all landmark link patient
              dict = {patient 1 : {landmarks1 : [0 , 0, 0], landmarks2 : [0 , 0, 0], ... },
                                    .
                                    .
                                    .
                                patient n :{landmarks1 : [0 , 0, 0], landmarks2 : [0 , 0, 0], ...}}
        list : list of file in the folder
    """
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
    return patients_lst, patients_dict, lst_files
      










  def compareT1T2(self,dic_patinetT1 : dict , dic_patientT2 : dict):
    """Check if patient T1 and T2 have the same landmark

    Display in the consol difference between T1 and T2

    Args:
        dic_patinetT1 (dict): dict with all patients and landmarks at time T1
        dic_patientT2 (dict): dict with all patients and landmarks at time T2
    """

    error = 0
    for patientT1, landmarks in dic_patinetT1.items() :
      for landmark in landmarks.keys():
        if patientT1 in dic_patientT2.keys():
          if not landmark in dic_patientT2[patientT1].keys():
            #TODO: add window warning

            error +=1
        else :
          print("patient :", patientT1)
          error +=1
    print("number difference between T1 and T2:", error)












  def CheckAllPatientSameLm(self,dico : dict ,all_landmarks : dict):
    """
    Check if all patients have the same landmarks and transform dico with all patient, landmarks and postion 
    into list with all landmarks in the patient

    Args:
        dico ( dict ): dict with patient, landmarks and position like this
                  dico = {patient 1 : {landmarks1 : [0 , 0, 0], landmarks2 : [0 , 0, 0], ... },
                              .
                              .
                              .
                          patient n :{landmarks1 : [0 , 0, 0], landmarks2 : [0 , 0, 0], ...}}

        all_landmarks ( dict ) : dict with all landmark use by the doctor
                  dict = {group 1 : [ landmark1, landmark 2, ...],
                            .
                            .
                            .
                          group n :[landmark1, landmark 2 , ...]}

    Returns:
        list : list with all landmarks in the first patient 
        dict : dict with all landmarks use by the doctor and one more group with name other. This group is for landmark is not exist in all_patient
    """
    list_landmark=[]
    miss_landmarks ={}
    error = 0
    first = 0
    for  patient , landmarks in dico.items():
      list_landmark_patient = []
      miss_landmarks[patient] = 0
      for landmark in landmarks.keys():

        if first == 0:


          if not landmark in list_landmark :
            list_landmark.append(landmark)
          else :
            #TODO : create a warning if patient have 2 landmarks with the same name
            print("one patient have 2 landmarks with the same name")



        else :


          if not landmark in list_landmark_patient :
            list_landmark_patient.append(landmark)
          else :
            #TODO : create a warning if patient have 2 landmarks with the same name
            print("one patient have 2 landmarks with the same name")
          
      for i in list_landmark_patient:
        if not i in list_landmark :
          miss_landmarks[patient] += 1
          error += 1 
    if error != 0 :

      #TODO : make a pop-up to tell all patients dont have the same landmarks
      print(" all patients dont have the same landmarks")


    list_otherlandmarks=[]
    list_midlandmarks=[]
    list_alllandmarks=[]
    for landmarks in all_landmarks.values():
      for landmark in landmarks :
        list_alllandmarks.append(landmark)
    for landmark in list_landmark :
      if landmark[:3] == "Mid":
          list_midlandmarks.append(landmark)
      elif not landmark in list_alllandmarks  :
        list_otherlandmarks.append(landmark)
          
    all_landmarks["Other"]=list_otherlandmarks
    all_landmarks['Midpoint']=list_midlandmarks
    

    return list_landmark, all_landmarks





  def SaveJson(self,patients_lst,patients_dict,out_path):
    midpoint_dic = {}
    
    # print(patients_lst)
    # print(patients_dict)
    for patient in patients_lst:
      lst_mid_point = []
      for mid_point in MID_POINTS:
        P1_name = mid_point.split('_')[1]
        P2_name = mid_point.split('_')[2]
        # print(P1_name)
        if P1_name and P2_name in patients_dict[patient]:
          P1_pos = patients_dict[patient][P1_name]
          P2_pos = patients_dict[patient][P2_name]
          mp = self.ComputeMidPoint(np.array(P1_pos),np.array(P2_pos))
          controle_point = self.GenControlePoint(P1_name,P2_name,mp)
          lst_mid_point.append(controle_point)
          patients_dict[patient][controle_point['label']] = controle_point['position']
      
      if patient not in midpoint_dic.keys():
        midpoint_dic[patient] = lst_mid_point
    
    for patient,cp_lst in midpoint_dic.items():
      self.WriteJson(patient,cp_lst,out_path)




  def WriteJson(self,patient,cp_lst,out_path):
    true = True
    false = False
    file = {
      "@schema": "https://raw.githubusercontent.com/slicer/slicer/master/Modules/Loadable/Markups/Resources/Schema/markups-schema-v1.0.0.json#",
      "markups": [
        {
          "type": "Fiducial",
          "coordinateSystem": "LPS",
          "locked": false,
          "labelFormat": "%N-%d",
          "controlPoints": cp_lst,
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
    with open(out_path+'/'+f"P{patient}_Midpoint.json", 'w', encoding='utf-8') as f:
      json.dump(file, f, ensure_ascii=False, indent=4)
    f.close



  def ComputeMidPoint(self,p1,p2):
    mp = (p1 + p2) / 2
    return mp



  def GenControlePoint(self,P1_name,P2_name,mp):
    controle_point = {
      "id": str(1),
      "label": f'Mid_{P1_name}_{P2_name}',
      "description": "",
      "associatedNodeID": "",
      "position": [float(mp[0]), float(mp[1]), float(mp[2])],
      "orientation": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
      "selected": True,
      "locked": True,
      "visibility": True,
      "positionStatus": "preview"
    }
    return controle_point




  def OnExportMeasurement(self,path_file : str ,measures : list):
    print("--"*5,"on export measure",'--'*5)
    dic_data_dist_pp = {"Type of measurement":[],"Point 1":[],"Point 2 / Line":[]}
    dic_data_dist_pl = {"Type of measurement":[],"Point 1":[],"Point 2 / Line":[]}
    dic_data_angl = {"Type of measurement":[],"Line 1":[], "Line 2":[]}
    for measure in measures :
      itmersure = iter(measure)
      print(measure['Type of measurement'])
      if measure['Type of measurement'] =="Distance between 2 points":
        dic_data_dist_pp['Type of measurement'].append(next(itmersure))
        dic_data_dist_pp['Point 1'].append(next(itmersure))
        dic_data_dist_pp['Point 2 / Line'].append(next(itmersure))

      elif measure['Type of measurement'] == "Distance point line" :
        dic_data_dist_pl['Type of measurement'].append(next(itmersure))
        dic_data_dist_pl['Point 1'].append(next(itmersure))
        dic_data_dist_pl['Point 2 / Line'].append(next(itmersure))

      else :
        dic_data_angl['Type of measurement'].append(next(itmersure))
        dic_data_angl['Line 1'].append(next(itmersure))
        dic_data_angl['Line 2'].append(next(itmersure))

    with pd.ExcelWriter(path_file) as writer:
      if len(dic_data_dist_pp['Type of measurement'])>0:
        df_dist_pp = pd.DataFrame(dic_data_dist_pp)
        df_dist_pp.to_excel(writer,sheet_name="Distance between 2 points",index=False)
      if len(dic_data_dist_pl['Type of measurement'])>0:
        df_dist_pl = pd.DataFrame(dic_data_dist_pl)
        df_dist_pl.to_excel(writer,sheet_name="Distance point line",index=False)
      if len(dic_data_angl['Type of measurement'])>0:
        df_angl = pd.DataFrame(dic_data_angl)
        df_angl.to_excel(writer,sheet_name="Angle between 2 lines",index=False)





  def OnImportMeasure(self,path_file):
    reader = pd.read_excel(path_file,sheet_name=None)
    newreader={"Distance between 2 points":{"Type of measurement":[],"Point 1":[],"Point 2 / Line":[]},
    'Distance point line':{"Type of measurement":[],"Point 1":[],"Point 2 / Line":[]},
    'Angle between 2 lines':{"Type of measurement":[],"Line 1":[], "Line 2":[]}}

    
    list_measure= []
    for name_sheet in reader:
        for name_column in reader[name_sheet]:
            for i in reader[name_sheet][name_column] :
                newreader[name_sheet][name_column].append(i)
    print(newreader)
    for name_sheet , sheet in newreader.items():
      list_point=[]
      for i in range(len(sheet['Type of measurement'])):
        if name_sheet == "Distance between 2 points":
          list_point = [sheet["Point 1"][i], sheet["Point 2 / Line"][i]]

        elif name_sheet == "Distance point line":
          if '/' in sheet['Point 2 / Line'][i]:
            point1 = sheet['Point 1'][i].split('/')
            point2 = sheet['Point 2 / Line'][i].split('/')
            list_point = [ point1[0],point2[0].split('-')[0],point2[0].split('-')[1],point1[1],point2[1].split('-')[0],point2[1].split('-')[1] ]
          else :
            list_point = [ sheet['Point 1'][i],sheet['Point 2 / Line'][i].split('-')[0], sheet['Point 2 / Line'][i].split('-')[1] ]

        else :
          if '/' in sheet['Line 1'][i]:
            line1 = sheet["Line 1"][i].split('/')
            line2 = sheet['Line 2'][i].split('/')
            list_point = [ line1[0].split('-')[0],line1[0].split('-')[1], line2[0].split('-')[0],line2[0].split('-')[1],line1[1].split('-')[0],line1[1].split('-')[1], line2[1].split('-')[0],line2[1].split('-')[1]]
          else :
            list_point = [ sheet["Line 1"][i].split('-')[0], sheet["Line 1"][i].split('-')[1], sheet["Line 2"][i].split('-')[0], sheet["Line 2"][i].split('-')[1]]

        print("--"*5,"Call create measure",'--'*5)
        print(sheet['Type of measurement'][i])

        measures = self.CreateMeasure (sheet['Type of measurement'][i],list_point)
        for measure in measures :
          list_measure.append(measure)


    return list_measure






  def CreateMeasure(self,type_of_measure,list_point):

    out = []

    if type_of_measure == "Angle between 2 lines T1" :

        L1 = Line(Point(list_point[0]),Point(list_point[1]))
        L2 = Line(Point(list_point[2]),Point(list_point[3]))
        measure = Angle(L1,L2,type_of_measure[:-3],"T1")
        out.append(measure)

    elif type_of_measure == "Angle between 2 lines dif T1 T2":
        T1L1 = Line(Point(list_point[0]),Point(list_point[1]))
        T2L1 = Line(Point(list_point[2]),Point(list_point[3]))
        T1L2 = Line(Point(list_point[4]),Point(list_point[5]))
        T2L2 = Line(Point(list_point[6]),Point(list_point[7]))

        measure1 = Angle(T1L1,T1L2,type_of_measure[:-10],"T1")
        measure2 = Angle(T2L1,T2L2,type_of_measure[:-10],"T2")
        measure_dif = Diff2Measure(measure1,measure2)

        out.append(measure1)
        out.append(measure2)
        out.append(measure_dif)


    elif type_of_measure == "Angle line T1 and line T2":
        LT1 = Line(Point(list_point[0]),Point(list_point[1]))
        LT2 = Line(Point(list_point[2]),Point(list_point[3]))

        measure = Angle(LT1, LT2, type_of_measure)
        out.append(measure)



    elif type_of_measure =="Distance between 2 points T1":
        P1 = Point(list_point[0])
        P2 = Point(list_point[1])

        measure = Distance(P1,P2,type_of_measure[:-3],time='T1')
        out.append(measure)

    elif type_of_measure ==  "Distance point line T1":
        P = Point(list_point[0])
        L = Line(Point(list_point[1]),Point(list_point[2]))

        measure = Distance(P,L,type_of_measure[:-3],time='T1')
        out.append(measure)


    elif type_of_measure == "Distance point line dif T1 T2" :
        PT1 = Point(list_point[0])
        LT1 = Line(Point(list_point[1]),Point(list_point[2]))
        PT2 = Point(list_point[3])
        LT2 = Line (Point(list_point[4]), Point(list_point[5]))

        measure1 = Distance(PT1, LT1, type_of_measure[:-10],time='T1')
        measure2 = Distance(PT2, LT2, type_of_measure[:-10],time='T2')
        measure_dif = Diff2Measure(measure1,measure2)

        out.append(measure1)
        out.append(measure2)
        out.append(measure_dif)

    else:
      print("pas trouver")


    return out

  

  def GenerateComputePatient(patient,dic_patientT1,dic_patientT2):
    print("oui")




  def computeDistance(self,point1_coord, point2_coord):
    delta = point2_coord - point1_coord
    norm = np.linalg.norm(delta)

    return round(-delta[0],3),round(-delta[1],3),round(delta[2],3),round(norm,3)   


  def reject(self,vec, axis):
    vec = np.asarray(vec)
    axis = np.asarray(axis)

  def computeLinePoint(self,line1, line2, point):
    if np.allclose(line1, line2, atol=1e-5):
      delta = point - line1
    else:
      delta = self.reject(
        point - line2,
        line1 - line2,
      )
    norm = np.linalg.norm(delta)
    return round(-delta[0],3),round(-delta[1],3),round(delta[2],3),round(norm,3)

  def computeAngle(self,line1, line2, axis):
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


  def computeAngles(self,point1, point2, point3, point4):
    line1 = point2 - point1
    line2 = point4 - point3
    axes = [
        2,  # axis=S; axial; for yaw
        0,  # axis=R; saggital; for pitch
        1,  # axis=A; coronal; for roll
    ]
    result = []
    for axis in axes:
      value = self.computeAngle(line1, line2, axis)
      result.append(round(value,3))

    return result[0],-result[1],-result[2]





  def ComputeManager(self,list_measure,dic_patient):
    print("Call ComputeManager")
    list_computation = []
    dic_patient__computation={"Patient":[],"Type of measurement":[],"Landmarks":[],"R-L Component":[],"R-L Meaning":[],"A-P Component":[],"A-P Meaning":[],"S-I Component":[],"S-I Meaning":[],
    "3D Distance":[],"Yaw Component":[],"Yam Meaning":[],"Picth Component":[],"Pitch Meaning":[],"Roll Component":[],"Roll Meaning":[]}
    list_title=["Type of measurement","Landmarks","R-L Component","R-L Meaning","A-P Component","A-P Meaning",
    "S-I Component","S-I Meaning","3D Distance","Yaw Component","Yam Meaning","Picth Component","Pitch Meaning","Roll Component","Roll Meaning"]

    for measure in list_measure :
      print("measure : ",measure)
      for patient, point in dic_patient.items() :
        print("patient : ",patient)
        try: 
          measure['position'] = point
        except KeyError:
          print("the landmark's measure doesnt exist in this patient",patient)
          continue
        measure.computation()
        measure.SignManager()
        dic_patient__computation["Patient"].append(patient)
        for title in list_title :
          dic_patient__computation[title].append(measure[title])
        print("dic_patient__computation : ", dic_patient__computation)
      
    print("end ConputeManager")
    return dic_patient__computation
        


  def GenMeasurementExcel(self,list_computation,path,name_file):
    print("Call GenMeasurementExcel")
    print(list_computation)

    if len(list_computation)>0:
      df = pd.DataFrame(list_computation)
    
    df.to_excel(f"{path}/{name_file}")


    # with pd.ExcelWriter(f"{path}/{name_file}") as writer:
    #   if len(list_computation)>0:
    #     df.to_excel(writer,sheet_name="Measurement",index=False)
    #     for column in df:
    #       column_width = max(df[column].astype(str).map(len).max(), len(column))
    #       col_idx = df.columns.get_loc(column)
    #       writer.sheets["Measurement"].set_column(col_idx, col_idx, column_width)
    #     writer.save()
    print('------------------- SAVE MEASUREMENT -------------------')








    
#
# AQ3DCTest
#

#============================================================================================================================#
 #    _       ___    _____   ____     ____   _____                _   
 #   / \     / _ \  |___ /  |  _ \   / ___| |_   _|   ___   ___  | |_ 
 #  / _ \   | | | |   |_ \  | | | | | |       | |    / _ \ / __| | __|
 # / ___ \  | |_| |  ___) | | |_| | | |___    | |   |  __/ \__ \ | |_ 
 #/_/   \_\  \__\_\ |____/  |____/   \____|   |_|    \___| |___/  \__|
 #============================================================================================================================#
                                                                     
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









class Point :
  def __init__(self,name : str)   :
    self.name = name
    self.position = []

  def __str__(self):

    return self.name

  def __getitem__(self,key):
    if key == "name":
      return self.name
    elif key == "position":
      return self.position

  def __setitem__(self,key,value):
    if key == "position":
      print("Point change : Position : ",value)
      self.position = value

  def __eq__(self, __o: object) -> bool:
    out = False
    if self.name == __o["name"]:
      out = True
    return out 


  

class Line :
    def __init__(self,point1 : Point ,point2 :Point):
      self.point1 = point1
      self.point2 = point2
    
    def __str__(self):
      return f"{self.point1}-{self.point2}"


    def __getitem__(self,key):
      if key == "point 1" or key == 1:
        return self.point1
      elif key =="point 2" or key ==2:
        return self.point2

    def __eq__(self, __o: object) -> bool:
      out = False 
      if self.point1 == __o[1] and self.point2 == __o[2]:
        out = True
      return out

    def __setitem__(self,key,value):
      if key == "position":
        self.point1["position"] = value[0]
        self.point2["position"] = value [1]
      



class Measure:
  def __init__(self,time : str ,measure :str) :
    self.time = time

    self.measure = measure
    self.checkbox = None
    self.lr_sign_meaning = ""
    self.ap_sign_meaning = ""
    self.si_sign_meaning = ""
    self.lr,self.ap,self.si,self.norm =0, 0 , 0 , 0


    #for angle normaly the name of calcul should Pitch, Roll, Yam
    #but it s not necessary in the code to distinguish the name of calcul distance and angle
    # so lr = Pitch, Roll = ap, si = Yam. for translation


  
  def __str__(self):
    strs = self.measure
    if self.time:
      strs += " "+self.time
    if self.checkbox:
      if self.checkbox.checkState():
        strs += " True "
      else :
        strs += " False "
    return strs


  def __setitem__(self,key,value):
    if key == "checkbox":
      self.checkbox = value

  def __getitem__(self,key):
    if key == "checkbox" or key == "check box":
      return self.checkbox
    elif key == "Type of measurement":
      return self.measure
    elif key == "Type of measurement + time":
      if self.time:
        return self.measure+" "+self.time
      else :
        return self.measure
    return 'x'


  def __eq__(self, __o: object) -> bool:
    out = False 
    if self["Type of measurement + time"] == __o["Type of measurement + time"]:
      out = True
    return out

    

  

class Distance(Measure) :
  def __init__(self,Point1 : Point, Point2Line,measure :str ,time : str = None) -> None:
    super().__init__(time,measure)

    self.point1 = Point1
    self.point2line= Point2Line


  def __str__(self) -> str:
    strs = f"{Measure.__str__(self)} Point 1 : {self.point1} Point 2 /Line :{self.point2line}"
    return strs



  def __repr__(self) -> str:
    return self.__str__()

  def __setitem__(self, key, value):
    if key == 'position':
      self.point1['position'] = value[self.point1['name']]
      print("In Distance ")
      print("type(self.point2line) :", type(self.point2line), "value :", value,"self.point2line['name'] :", self.point2line['name'])
      if isinstance(self.point2line,Line):
        self.point2line["position"] = [value[self.point2line[1]["name"]], value[self.point2line[2]["name"]]]
      else :
        self.point2line["postion"] = value[self.point2line['name']]

    Measure.__setitem__(self,key, value)

  def __getitem__(self, key):
    if key == "point 1" or key == 1:
      return self.point1
    elif key == "point 2" or key == 2:
      return self.point2line
    elif key == "Landmarks" :
      return str(self.point1)+" & "+str(self.point2line)
    elif key =="R-L Component":
      return str(abs(self.lr))
    elif key =="R-L Meaning" :
      return self.lr_sign_meaning
    elif key == "A-P Component" :
      return str(abs(self.ap))
    elif key == "A-P Meaning" :
      return self.ap_sign_meaning
    elif key == "S-I Component" :
      return str(abs(self.si))
    elif key == "S-I Meaning" :
      return self.si_sign_meaning
    elif key == "3D Distance":
      return self.norm
    return Measure.__getitem__(self,key)


  def __iter__(self):
    self.iter=1
    return self
  
  def __next__(self):
    out = None
    if self.iter == 1 :
      out = Measure.__getitem__(self,"Type of measurement + time")

    elif self.iter == 2 :
      out = str(self.point1)

    elif self.iter == 3 :
        out = str(self.point2line)
    else :
        raise StopIteration
    
    self.iter +=1
    return out

  def get(self):
    return [Measure.__getitem__(self,"Type of measurement"), self.point1, self.point2line]


  def __eq__(self, __o: object) -> bool:
    print('--'*5,"eq distance",'--'*5)
    out = False 
    if super().__eq__(__o):
      if self.point1 == __o[1] and self.point2line == __o[2]:
        
        out = True
    return out  


  def computation(self):
    if self["Type of measurement"] == "Distance between 2 points":
      self.lr,self.ap,self.si,self.norm = AQ3DCLogic.computeDistance(self,np.array(self.point1["position"]),np.array(self.point2line["position"]))
    elif self["Type of measurement"] == "Distance point line" :
      print("self.point2line[1]['position'] :",self.point2line[1]['position'])
      self.lr,self.ap,self.si,self.norm = AQ3DCLogic.computeLinePoint(self,np.array(self.point2line[1]['position']),np.array(self.point2line[1]['position']),np.array(self.point1['position']))



  def SignManager(self):
    if self.measure == 'Distance between 2 points':
      if self.point1["name"] and self.point2line['name'] in DICO_TEETH["Lower"]+DICO_TEETH["Upper"]:
        self.__SignMeaningDentalDst()
      else :
        self.__SignMeaningDist()

    else :
      self.__SignMeaningDist()


  def __SignMeaningDist(self):
    self.lr_sign_meaning = "L"
    self.ap_sign_meaning = "P"
    self.si_sign_meaning = "I"
    if self.lr>0:
      self.lr_sign_meaning = "R" #Right

    if self.ap>0:
      self.ap_sign_meaning = "A" #Anterior
   
    if self.si>0:
      self.si_sign_meaning = "S" #Superior




  def __SignMeaningDentalDst(self):
    lst_measurement = [self.point1["name"],self.point2line["name"]]
    if not False in [elem in upper_right_back for elem in lst_measurement]:
      self.lr_sign_meaning = "L"
      self.ap_sign_meaning = "D"
      self.si_sign_meaning = "E"
      if self.lr>0:
        self.lr_sign_meaning = "B"

      if self.ap>0:
        self.ap_sign_meaning = "M"

      if self.si>0:
        self.si_sign_meaning = "I"

    elif not False in [elem in upper_right_front for elem in lst_measurement]:
      self.lr_sign_meaning = "M"
      self.ap_sign_meaning = "L"
      self.si_sign_meaning = "E"
      if self.lr>0:
        self.lr_sign_meaning = "D"

      if self.ap>0:
        self.ap_sign_meaning = "B"

      if self.si>0:
        self.si_sign_meaning = "I"

    elif not False in [elem in upper_left_back for elem in lst_measurement]:
      self.rl_sign_meaning = "B"
      self.ap_sign_meaning = "D"
      self.si_sign_meaning = "E"
      if self.rl>0:
        self.rl_sign_meaning = "L"

      if self.ap>0:
        self.ap_sign_meaning = "M"

      if self.si>0:
        self.si_sign_meaning = "I"


    elif not False in [elem in upper_left_front for elem in lst_measurement]:
      self.si_sign_meaning = "E"
      self.ap_sign_meaning = "L"
      self.rl_sign_meaning = "D"
      if self.rl>0:
        self.rl_sign_meaning = "M"

      if self.ap>0:
        self.ap_sign_meaning = "B"

      if self.si>0:
        self.si_sign_meaning = "I"

    elif not False in [elem in lower_right_back for elem in lst_measurement]:
      self.rl_sign_meaning = "L"
      self.ap_sign_meaning = "D"
      self.si_sign_meaning = "I"
      if self.rl>0:
        self.rl_sign_meaning = "B"

      if self.ap>0:
        self.ap_sign_meaning = "M"

      if self.si>0:
        self.si_sign_meaning = "E"

    elif not False in [elem in lower_right_front for elem in lst_measurement]:
      self.rl_sign_meaning = "M"
      self.ap_sign_meaning = "L"
      self.si_sign_meaning = "I"
      if self.rl>0:
        self.rl_sign_meaning = "D"

      if self.ap>0:
        self.ap_sign_meaning = "B"

      if self.si>0:
        self.si_sign_meaning = "E"


    elif not False in [elem in lower_left_back for elem in lst_measurement]:
      self.rl_sign_meaning = "B"
      self.ap_sign_meaning = "D"
      self.si_sign_meaning = "I"
      if self.rl>0:
        self.rl_sign_meaning = "L"       

      if self.ap>0:
        self.ap_sign_meaning = "M"

      if self.si>0:
        self.si_sign_meaning = "E"
  

    elif not False in [elem in lower_left_front for elem in lst_measurement]:
      self.rl_sign_meaning = "D"
      self.ap_sign_meaning = "L"
      self.si_sign_meaning = "I"
      if self.rl>0:
        self.rl_sign_meaning = "M"       

      if self.ap>0:
        self.ap_sign_meaning = "B"

      if self.si>0:
        self.si_sign_meaning = "E"

  
class Angle(Measure):
  def __init__(self, Line1 : Line, Line2 : Line,  measure: str,time: str =None ):
    super().__init__(time, measure)
    self.line1 = Line1
    self.line2 = Line2
    
  def __str__(self) -> str:
    return f"{Measure.__str__(self)} Line 1 : {self.line1} Line 2 : {self.line2}"

  def __repr__(self) -> str:
    return self.__str__()

  def __getitem__(self, key):
    if key == "line 1" or key == 1:
      return self.line1
    elif key == "line 2" or key == 2:
      return self.line2
    elif key == "Landmarks":
      return str(self.line1)+" & "+str(self.line2)
    elif key == "Yaw Component" :
      return str(abs(self.lr))
    elif key == "Yam Meaning":
      return self.lr_sign_meaning
    elif key == "Pitch Component":
      return self.ap
    elif key == "Pitch Meaning" :
      return self.ap_sign_meaning
    elif key == "Roll Component":
      return str(abs(self.si))
    elif key == "Roll Meaning":
      return self.si_sign_meaning
    return Measure.__getitem__(self,key)


  def __setitem__(self, key, value):
    if key == "position" :
      self.line1["position"] = [value[self.line1[1]["name"]],value[self.line1[2]['name']]]
      self.line2["position"] = [value[self.line2[1]["name"]],value[self.line2[2]['name']]]
    return super().__setitem__(key, value)


  def __iter__(self):
    self.iter =1 
    return self

  def __next__(self):
    out = None

    if self.iter == 1 :

        out = Measure.__getitem__(self,"Type of measurement + time")

    elif self.iter == 2 :
      out = str(self.line1)

    elif self.iter == 3 :
      out = str(self.line2)

    else :
        raise StopIteration


    self.iter+=1
    return out
  
  def get(self):
    return [super().measure,self.line1,self.line2]


  def __eq__(self, __o: object) -> bool:
    out = False 
    if Measure.__eq__(self,__o) :
      if self.line1 == __o[1] and self.line2 == __o[2]:
        out = True
    return out
      
  def computation(self):
    self.lr, self.ap, self.si = AQ3DCLogic.computeAngles(self,np.array(self.line1[1]['position']),np.array(self.line1[2]['position']),np.array(self.line2[1]['position']),np.array(self.line2[2]['position']))


  def SignManager(self):
    if self.line1[1]['name'] and self.line1[2]['name'] and self.line2[1]['name'] and self.line2[2]['name'] in  DICO_TEETH["Lower"]+DICO_TEETH["Upper"]:
      self.__SignMeaningDentalAngle()



  def __SignMeaningDentalAngle(self):
    lst_measurement = [self.line1[1]['name'],self.line1[2]['name'],self.line2[1]['name'],self.line2[2]['name']]
  #print("function angle")
    if not False in [elem in upper_right_back for elem in lst_measurement]: 
      self.lr_sign_meaning = "D"  
      self.ap_sign_meaning = "L"
      self.si_sign_meaning = "DR"
      if self.lr>0:
        self.lr_sign_meaning = "M"

      if self.ap>0:
        self.ap_sign_meaning = "B"

      if self.si>0:
        self.si_sign_meaning = "MR"

    elif not False in [elem in upper_right_front for elem in lst_measurement]:
      self.lr_sign_meaning = "L"
      self.ap_sign_meaning = "M"
      self.si_sign_meaning = "DR"
      if self.lr>0:
        self.lr_sign_meaning = "B"

      if self.ap>0:
        self.ap_sign_meaning = "D"

      if self.si>0:
        self.si_sign_meaning = "MR"

      
    elif not False in [elem in upper_left_back for elem in lst_measurement]:
      self.lr_sign_meaning = "D"
      self.ap_sign_meaning = "B"
      self.si_sign_meaning = "MR"
      if self.lr>0:
        self.lr_sign_meaning = "M"

      if self.ap>0:
        self.ap_sign_meaning = "L"
     
      if self.si>0:
        self.si_sign_meaning = "DR"
  
    
    elif not False in [elem in upper_left_front for elem in lst_measurement]:
      self.lr_sign_meaning = "L"
      self.ap_sign_meaning = "D"
      self.si_sign_meaning = "MR"
      if self.lr>0:
        self.lr_sign_meaning = "B"
    
      if self.ap>0:
        self.ap_sign_meaning = "M"
       
      if self.si>0:
        self.si_sign_meaning = "DR"

    elif not False in [elem in lower_right_back for elem in lst_measurement]:
      self.lr_sign_meaning = "M"
      self.ap_sign_meaning = "B"
      self.si_sign_meaning = "DR"
      if self.lr>0:
        self.lr_sign_meaning = "D"

      if self.ap>0:
        self.ap_sign_meaning = "L"
     
      if self.si>0:
        self.si_sign_meaning = "MR"
        
    elif not False in [elem in lower_right_front for elem in lst_measurement]:
      self.lr_sign_meaning = "B"
      self.ap_sign_meaning = "D"
      self.si_sign_meaning = "DR"
      if self.lr>0:
        self.lr_sign_meaning = "L" 

      if self.ap>0:
        self.ap_sign_meaning = "M"
   
      if self.si>0:
        self.si_sign_meaning = "MR"     
        
    elif not False in [elem in lower_left_back for elem in lst_measurement]:   
      self.lr_sign_meaning = "M"
      self.ap_sign_meaning = "L"
      self.si_sign_meaning = "MR"
      if self.lr>0:
        self.lr_sign_meaning = "D"

      if self.ap>0:
        self.ap_sign_meaning = "B"
    
      if self.si>0:
        self.si_sign_meaning = "DR"

        
    elif not False in [elem in lower_left_front for elem in lst_measurement]:
      self.lr_sign_meaning = "B"
      self.ap_sign_meaning = "M"
      self.si_sign_meaning = "MR"
      if self.lr>0:
        self.lr_sign_meaning = "L"

      if self.ap>0:
        self.ap_sign_meaning = "D"
    
      if self.si>0:
        self.si_sign_meaning = "DR"




class Diff2Measure(Measure):
  def __init__(self,measure1, measure2) -> None:
    super().__init__(time=" T1 T2", measure=measure1["Type of measurement"])
    self.T1PL1 = measure1[1]
    self.T1PL2 = measure1[2]
    self.T2PL1 = measure2[1]
    self.T2PL2 = measure2[2]
    self.measure1= measure1
    self.measure2=measure2

  def __str__(self):


    out = f"{Measure.__str__(self)} {self.T1PL1}/{self.T2PL1} {self.T1PL2}/{self.T2PL2}"
    return out

  def __iter__(self):
    self.iter =1
    return self

  def __next__(self):
    out = None

    if self.iter == 1 :

        out = Measure.__getitem__(self,"Type of measurement")+" dif T1 T2"

    elif self.iter == 2 :
      out = f"{self.T1PL1}/{self.T2PL1}"

    elif self.iter == 3 :
      out = f"{self.T1PL2}/{self.T2PL2}"

    else :
        raise StopIteration


    self.iter+=1
    return out


  def __getitem__(self, key):
    if key == "measure 1" or key == 1:
      return self.measure1
    elif key == "measure 2" or key ==2:
      return self.measure1
    elif key == "Landmarks" :
      return self.measure1["Landmarks"]+" && "+self.measure2
    return super().__getitem__(key)


  def __setitem__(self, key, value):
    if key == "position" :
      self.measure1['position'] = value
      self.measure2['position'] = value
    return super().__setitem__(key, value)



  def __eq__(self, __o: object) -> bool:
    out = False 
    if Measure.__eq__(self,__o):
      if self.measure1 == __o[1] and self.measure2 == __o[2]:
        out = True
    return out


  def compute(self):
    self.measure1.compute()
    self.measure2.compute()
    self.lr = self.measure2.lr - self.measure1.lr
    self.ap = self.measure2.ap - self.measure1.ap
    self.si = self.measure2.si - self.measure1.si
    self.lr = round(self.lr,3)
    self.ap = round(self.ap,3)
    self.si = round(self.norm,3)



  def SignManager(self):
    pass






