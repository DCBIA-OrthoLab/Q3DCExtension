

import os
import logging
import vtk, qt, ctk, slicer
import glob
import numpy as np

from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import json
from functools import partial
from qt import QWidget, QVBoxLayout, QScrollArea, QCheckBox, QTableWidgetItem, QTabWidget, QGridLayout 
from Classes import Angle, Distance, Diff2Measure, Point, Line, Group_landmark, MyList, MyDict


#
# AQ3DC
#
try:
  import pandas as pd

except: 
  slicer.util.pip_install('pandas')
  import pandas as pd


try :
  import openpyxl
except:
  slicer.util.pip_install('openpyxl')
  #we need this package because pandas use it

  











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





    #need initialise the tab measurement 
    #if we dont do this, if user add a measure without click on tabmeasurement or chekcbox. we get an issue
    self.manageCblistMeasurement()
    





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
    self.dic_patient_T1 = {}
    self.dic_patient_T2 = {}
    self.list_measure=[]
    self.list_landmark=[]
    self.exeption_display_group_landmark={} #link between the name of group and index of stackedwidget
    self.dic_checkbox={} #dic = {'A':checkbox , 'B':checkbox,...}

    #landmark available on tab landmark
    self.GROUPS_LANDMARKS = {}
    """
 __     __     _      ____    ___      _      ____    _       _____   ____  
 \ \   / /    / \    |  _ \  |_ _|    / \    | __ )  | |     | ____| / ___| 
  \ \ / /    / _ \   | |_) |  | |    / _ \   |  _ \  | |     |  _|   \___ \ 
   \ V /    / ___ \  |  _ <   | |   / ___ \  | |_) | | |___  | |___   ___) |
    \_/    /_/   \_\ |_| \_\ |___| /_/   \_\ |____/  |_____| |_____| |____/ 
                                                                                                                                                 
    """







    #init self.group landmark 
    self.ImportLandmarks(path_listlandmarks=self.resourcePath('name_landmark.xlsx'))









    """
 __        __  ___   ____     ____   _____   _____      ____    ___    _   _   _   _   _____    ____   _____ 
 \ \      / / |_ _| |  _ \   / ___| | ____| |_   _|    / ___|  / _ \  | \ | | | \ | | | ____|  / ___| |_   _|
  \ \ /\ / /   | |  | | | | | |  _  |  _|     | |     | |     | | | | |  \| | |  \| | |  _|   | |       | |  
   \ V  V /    | |  | |_| | | |_| | | |___    | |     | |___  | |_| | | |\  | | |\  | | |___  | |___    | |  
    \_/\_/    |___| |____/   \____| |_____|   |_|      \____|  \___/  |_| \_| |_| \_| |_____|  \____|   |_|  
                                                                                                             
    """





    # self.ui.TabLandmarks.clear()
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
    self.ui.ButtonAddMeasure.clicked.connect(self.ManageMeasure)
    self.ui.ButtonDeleteMeasurement.clicked.connect(self.RemoveMeasureTabMeasure)
    self.ui.CbImportExportMeasure.activated.connect(self.ManageStakedImportExportMeasure)
    self.ui.ButtonFolderExportMeasure.clicked.connect(self.FolderExportMeasure)
    self.ui.ButtonFileImportMeasure.clicked.connect(self.FileImportMeasure)
    self.ui.ButtonExportMeasure.clicked.connect(self.ExportMeasure)
    self.ui.ButtonImportMeasure.clicked.connect(self.ImportMeasure)
    self.ui.ButtonCompute.clicked.connect(self.Computation)
    self.ui.ButtonFolderCompute.clicked.connect(self.ComputationFolder)
    self.ui.TabLandmarks.currentChanged.connect(self.manageStackedWidgetLandmark)

    self.ui.TableAngle.horizontalHeader().sectionDoubleClicked.connect(partial(self.ChechAllCheckbox,'Angle'))
    self.ui.TableDistance.horizontalHeader().sectionDoubleClicked.connect(partial(self.ChechAllCheckbox,'Distance'))



    """
 __        __  ___   ____     ____   _____   _____      ____    ___    _   _   _   _   _____    ____   _____ 
 \ \      / / |_ _| |  _ \   / ___| | ____| |_   _|    / ___|  / _ \  | \ | | | \ | | | ____|  / ___| |_   _|
  \ \ /\ / /   | |  | | | | | |  _  |  _|     | |     | |     | | | | |  \| | |  \| | |  _|   | |       | |  
   \ V  V /    | |  | |_| | | |_| | | |___    | |     | |___  | |_| | | |\  | | |\  | | |___  | |___    | |  
    \_/\_/    |___| |____/   \____| |_____|   |_|      \____|  \___/  |_| \_| |_| \_| |_____|  \____|   |_|  
                                                                                                             
    """














    """
   _____                                       _             _     _                 
  / ____|                                     | |           | |   (_)                
 | |        ___    _ __ ___    _ __    _   _  | |_    __ _  | |_   _    ___    _ __  
 | |       / _ \  | '_ ` _ \  | '_ \  | | | | | __|  / _` | | __| | |  / _ \  | '_ \ 
 | |____  | (_) | | | | | | | | |_) | | |_| | | |_  | (_| | | |_  | | | (_) | | | | |
  \_____|  \___/  |_| |_| |_| | .__/   \__,_|  \__|  \__,_|  \__| |_|  \___/  |_| |_|
                              | |                                                    
                              |_|                                                    
    """

  def ComputationFolder(self):
    """Ask user, where he want to put his result
    Display the selected folder

    Call by ButtonFolderCompute
    """
    computation_folder = qt.QFileDialog.getExistingDirectory(self.parent, "Select a scan folder")
    if computation_folder != '' :
      self.ui.LineEditFolderComputation.setText(computation_folder)



  def Computation(self):
    """
    Compute measurement 

    Call by ButtonCompute
    """

    path = self.ui.LineEditFolderComputation.text
    file_name = self.ui.LineEditComputationFile.text
    if path != '' and (file_name!='.xlsx' or ''):
      #concatenate patient T1 and T2
      dic_patient = self.logic.CatPatientT1T2(self.dic_patient_T1,self.dic_patient_T2) 

      # compute all measure
      patient_compute = self.logic.ComputeManager(self.list_measure,dic_patient) 



      #write measure
      self.logic.GenMeasurementExcel(patient_compute,path,file_name)























  """
  ______                                 _         __  _____                                      _   
 |  ____|                               | |       / / |_   _|                                    | |  
 | |__    __  __  _ __     ___    _ __  | |_     / /    | |    _ __ ___    _ __     ___    _ __  | |_ 
 |  __|   \ \/ / | '_ \   / _ \  | '__| | __|   / /     | |   | '_ ` _ \  | '_ \   / _ \  | '__| | __|
 | |____   >  <  | |_) | | (_) | | |    | |_   / /     _| |_  | | | | | | | |_) | | (_) | | |    | |_ 
 |______| /_/\_\ | .__/   \___/  |_|     \__| /_/     |_____| |_| |_| |_| | .__/   \___/  |_|     \__|
                 | |                                                      | |                         
                 |_|                                                      |_|                         
  """





  def ManageStakedImportExportMeasure(self):
    """
    Manage Interface if user want export list of measurement or export
    
    Call by CbImportExportMeasure
    """
    dic = {"None":0,'Import list of measurements':1,"Export list of measurements":2}
    choice = self.ui.CbImportExportMeasure.currentText
    self.ui.StackedImportExport.setCurrentIndex(dic[choice])



  def FolderExportMeasure(self):
    """Ask to user, where he want to put his measurement file,
        Dislay the selected folder

    Call by ButtonFolderExportMeasure
    """
    measure_folder = qt.QFileDialog.getExistingDirectory(self.parent, "Select a scan folder")
    if measure_folder != '' :
      self.ui.LineEditFolderExportMeasure.setText(measure_folder)


  def ExportMeasure(self):
      """Export Measure

      call by ButtonExportMeasure
      """
      name_file = self.ui.LineEditFileExportMeasure.text
      measure_folder = self.ui.LineEditFolderExportMeasure.text
      if name_file != '' and measure_folder != '':
        
        self.logic.OnExportMeasurement(measure_folder+'/'+name_file,self.list_measure)


  def FileImportMeasure(self):
    """Ask to user, where he want to put his measurement file,
        Dislay the file chose

      call by ButtonFileImportMeasure
    """
    file_measure = qt.QFileDialog.getOpenFileName(self.parent,"Select file")
    if file_measure != '':
      self.ui.LineEditImportMeasure.setText(file_measure)


  def ImportMeasure(self):
    """Import Measure

    ButtonImportMeasure
    """
    list_measure = self.logic.OnImportMeasure(self.ui.LineEditImportMeasure.text)
    for measure in list_measure:
      self.AddMeasureTabMeasure(measure)
















    

    













































  """
   _____   _                     _      ____                     _                            _                              _    
  / ____| | |                   | |    |  _ \                   | |                          | |                            | |   
 | |      | |__     ___    ___  | | __ | |_) |   ___   __  __   | |        __ _   _ __     __| |  _ __ ___     __ _   _ __  | | __
 | |      | '_ \   / _ \  / __| | |/ / |  _ <   / _ \  \ \/ /   | |       / _` | | '_ \   / _` | | '_ ` _ \   / _` | | '__| | |/ /
 | |____  | | | | |  __/ | (__  |   <  | |_) | | (_) |  >  <    | |____  | (_| | | | | | | (_| | | | | | | | | (_| | | |    |   < 
  \_____| |_| |_|  \___|  \___| |_|\_\ |____/   \___/  /_/\_\   |______|  \__,_| |_| |_|  \__,_| |_| |_| |_|  \__,_| |_|    |_|\_\
                                                                                                                                  
                                                                                                                                  
  """




  def ManageTabLandmarks(self,list_landmarks : list ,dico_landmarks : Group_landmark ):
    """_summary_
    Manage Creation of Tab landmark

    Args:
        list_landmarks (list): for checkbox status
        dico_landmarks (dict): group landmark
    """
    self.ui.TabLandmarks.clear()
    self.dic_checkbox = {}
    self.dic_Checkbox2Landmark ={}
    self.dic_Landmark2Checkbox ={}
    self.dic_Group2Layout = {}


    #create dic to know each landmark is available
    status = dico_landmarks.exits(list_landmarks)  



    index = 0
    for group , landmarks in dico_landmarks.items():


      #create tab
      self.addGroupTabLandmarks(self.ui.TabLandmarks,group,index)



      if not isinstance(landmarks,MyDict):
        #if landmarks need only one tab to be display
        for landmark in landmarks :
          self.addLandmarksTabLandmarks(group,landmark,status[landmark])




      else :
        #to display 2 tab landmark
        prefix , suffix = landmarks.get()
        for suf in suffix :
          self.addLandmarksTabLandmarks(group,suf,status[suf])


      
        self.addTabWidget(index,prefix,group)
        for key , values in prefix.items():
          for value in values:
            self.addLandmarksTabLandmarks(key+group,value,status[value])


      index += 1 

    self.list_LandMarkCheck=[]
    self.ComboboxManageLandmark()







  def addTabWidget(self,i, dico ,parent):
    """add TabWidget if the group need 2 TabWidget

    Args:
        i (int): index
        dico (dict): _description_
        parent (str): group link
    """


    new_tabwidget = QTabWidget()
    new_tabwidget.setHidden(True)
    self.ui.LayoutLandmarks.addWidget(new_tabwidget)
    self.exeption_display_group_landmark[i]=new_tabwidget



    for group in dico.keys():
      self.addGroupTabLandmarks(new_tabwidget,group,i,parent=parent)



  def addGroupTabLandmarks(self,tabWidget : QTabWidget, group : str, index : int, parent : str = ''):
    """Add a new Tab in tabWidget

    Args:
        tabWidget (QTabWidget): _description_
        group (str): tab's name
        index (int): index tab
        parent (str, optional):to make a link with another tabwidget Defaults to ''.
    """


    new_widget = QWidget()
    new_widget.setMinimumHeight(250)

    layout = QGridLayout(new_widget)

    scr_box = QScrollArea(new_widget)
    scr_box.setMinimumHeight(200)

    layout.addWidget(scr_box,0,0)

    new_widget2 = QWidget(scr_box)
    layout2 = QVBoxLayout(new_widget2)

    
    scr_box.setWidgetResizable(True)
    scr_box.setWidget(new_widget2)

    
    tabWidget.insertTab(index,new_widget,group)




    self.dic_Group2Layout[group+parent]=[layout2,scr_box]




  def addLandmarksTabLandmarks(self,group : str , landmark : str, status : bool ):
      """Add landmark in tab

      Args:
          group (str): to know in which tab landmark to add
          landmark (str): landmark to add
          status (bool): to know if the checkbox of landmark is enable
      """
      check = QCheckBox(landmark)
      check.setEnabled(status)
      self.dic_Checkbox2Landmark[check]=[landmark,status,group]
      self.dic_Landmark2Checkbox[landmark]=[check,status]
      self.dic_checkbox[landmark]= check
      check.connect("toggled(bool)" ,self.CheckboxTabLandmarks)
      self.dic_Group2Layout[group][0].addWidget(check)




  def manageStackedWidgetLandmark(self):
    """ manage the 2 tab widget
    """
    for tablandmark in self.exeption_display_group_landmark.values():
      tablandmark.setHidden(True)
    if self.ui.TabLandmarks.currentIndex in self.exeption_display_group_landmark:
      self.exeption_display_group_landmark[self.ui.TabLandmarks.currentIndex].setHidden(False)


      

  def CheckboxTabLandmarks(self):
    """funtion connect to checkbox in tablelandmark

      update list landmark checked
    """

    self.list_LandMarkCheck=[]
    for landmark, checkbox in self.dic_checkbox.items():
      if checkbox.checkState():
        self.list_LandMarkCheck.append(landmark)



    self.ComboboxManageLandmark()







  def ComboboxManageLandmark(self):
    """manage landmark in each combo box 
    """
    for Cb in self.list_CbLandmark :
      Cb.clear()
      Cb.addItems(self.list_LandMarkCheck)

















  """
  _                            _                              _          
 | |                          | |                            | |         
 | |        __ _   _ __     __| |  _ __ ___     __ _   _ __  | | __  ___ 
 | |       / _` | | '_ \   / _` | | '_ ` _ \   / _` | | '__| | |/ / / __|
 | |____  | (_| | | | | | | (_| | | | | | | | | (_| | | |    |   <  \__ \
 |______|  \__,_| |_| |_|  \__,_| |_| |_| |_|  \__,_| |_|    |_|\_\ |___/
                                                                         
                                                                         
                                                                   
  """


  def ImportLandmarks(self,path_listlandmarks = None):
    """
    Ask user, which excel file is use for group landmark
    add landmark in the tablandmarks and update combo box with all landmark

    Call by ButtonImportLandmarks

    """
    if path_listlandmarks is  None :
      path_listlandmarks = qt.QFileDialog.getOpenFileName(self.parent,"Select file")

    if path_listlandmarks != '':
      self.ui.LineEditImportLandmarks.setText(path_listlandmarks)


      self.GROUPS_LANDMARKS = Group_landmark(path_listlandmarks)
      list_landmarks, self.GROUPS_LANDMARKS = self.logic.CheckAllPatientSameLm( self.dic_patient_T1 ,self.GROUPS_LANDMARKS)
      self.ManageTabLandmarks(list_landmarks, self.GROUPS_LANDMARKS)

      self.manageCblistMeasurement()
  




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

    for landmark in self.GROUPS_LANDMARKS[group]:
      if self.dic_Landmark2Checkbox[landmark][1]:
        self.dic_Landmark2Checkbox[landmark][0].setChecked(status)

    self.ComboboxManageLandmark()



























  """
  __  __   _       _   _____            _           _   
 |  \/  | (_)     | | |  __ \          (_)         | |  
 | \  / |  _    __| | | |__) |   ___    _   _ __   | |_ 
 | |\/| | | |  / _` | |  ___/   / _ \  | | | '_ \  | __|
 | |  | | | | | (_| | | |      | (_) | | | | | | | | |_ 
 |_|  |_| |_|  \__,_| |_|       \___/  |_| |_| |_|  \__|
                                                        
                                                        
  """



  def AddMidpoint(self):
    """
    Add midpoint in tablandmark 
    """
    P1 = self.ui.CbMidpointP1.currentText
    P2 = self.ui.CbMidpointP2.currentText
    mid_point = 'Mid_'+ P1 +'_'+P2
    self.GROUPS_LANDMARKS['Midpoint'] = mid_point


    self.addLandmarksTabLandmarks('Midpoint', mid_point, True)
    self.GROUPS_LANDMARKS['Midpoint'] = mid_point
    self.dic_patient_T1 = self.logic.AddMidpointToPatient(self.dic_patient_T1,P1, P2)
    if len(self.dic_patient_T2) > 0 :
      self.dic_patient_T2 = self.logic.AddMidpointToPatient(self.dic_patient_T2,P1, P2)




  def FolderMidpoint(self):
    """Ask user, which folder he want to save midpoint
      Display the folder chose

      Call by ButtonFolderMidpoint
    """
    folder_midpoint = qt.QFileDialog.getExistingDirectory( self.parent, "Select a scan folder")
    if folder_midpoint != '':
      self.ui.LineEditPathMidpoint.setText(folder_midpoint)


  def SaveMidpoint(self):
    """Save Midpoint in folder T1 and T2
    """
    out_path_T1 = os.path.join(self.ui.LineEditPathMidpoint.text ,'T1')
    out_path_T2 = os.path.join(self.ui.LineEditPathMidpoint.text,'T2')
    if not os.path.exists(out_path_T1):
      os.makedirs(out_path_T1)
    self.logic.SaveJsonMidpoint(self.list_patient_T1,self.dic_patient_T1,out_path_T1,self.GROUPS_LANDMARKS['Midpoint'])
    if self.ui.LineEditPathT2.text != '':
      if not os.path.exists(out_path_T2):
        os.makedirs(out_path_T2)
      self.logic.SaveJsonMidpoint(self.lst_patient_T2,self.dic_patient_T2,out_path_T2,self.GROUPS_LANDMARKS['Midpoint'])
























  










  """
  __  __                                                                         _   
 |  \/  |                                                                       | |  
 | \  / |   ___    __ _   ___   _   _   _ __    ___   _ __ ___     ___   _ __   | |_ 
 | |\/| |  / _ \  / _` | / __| | | | | | '__|  / _ \ | '_ ` _ \   / _ \ | '_ \  | __|
 | |  | | |  __/ | (_| | \__ \ | |_| | | |    |  __/ | | | | | | |  __/ | | | | | |_ 
 |_|  |_|  \___|  \__,_| |___/  \__,_| |_|     \___| |_| |_| |_|  \___| |_| |_|  \__|
                                                                                     
                                                                                     
                                                                                                                           
                                                                                         
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




  def AddMeasureTabMeasure(self,measure):
    """Add new measure in tabmeasure

    Args:
        measure (Measure): new measure to add
    """

    
    for allmeasure in self.list_measure :

      if allmeasure == measure:

        return
    
    
    num = 0
    group = measure["group"]
    for lmeasure in self.list_measure :
      if group == lmeasure["group"]:
        num += 1
    dic={"Distance":self.ui.TableDistance,"Angle":self.ui.TableAngle}
    dic[group].setRowCount(num+1) 
    a =QCheckBox()
    dic[group].setCellWidget(num, 0 , a)


    for count , value in enumerate(measure):
      b = QTableWidgetItem(value)
      dic[group].setItem(num,count+1,b)




    if group == 'Angle' :
      #add checkbox to choose if user want the complementary angle
      checkbox_angle_complement = QCheckBox()
      dic[group].setCellWidget(num,4,checkbox_angle_complement)
      measure['complement'] = checkbox_angle_complement





    measure["checkbox"] = a
    self.list_measure.append(measure)





      


  def ChechAllCheckbox(self,group,column):
    if column == 0 :
      list_checkbox = []
      for mea in self.list_measure:
        if mea['group'] == group:
          list_checkbox.append(mea['checkbox'])

      for checkbox in list_checkbox:
        checkbox.setChecked(True)

    




  def RemoveMeasureTabMeasure(self):
    """
    Remove all measurement with checkbox checked

    call by ButtonDeleteMeasurement
    """


    text  = self.ui.TabMeasure.currentWidget().name
    text = text[3:]

    dic_table={"Distance":self.ui.TableDistance,"Angle":self.ui.TableAngle}


    row_remove=[]
    i = 0
    for count , measure in enumerate(self.list_measure):

      if measure["group"] == text :
        if measure["checkbox"].checkState():
          dic_table[text].removeRow(i-len(row_remove))
          row_remove.append(count-len(row_remove))

        i+=1


    for idremove in row_remove:
      self.list_measure.pop(idremove)






  def ManageMeasure(self):
    """
    call by ButtonAddMeasure

    """
    out = []

    dic_page2combobox = {  "PageAngleBetween2LinesT1":[    self.ui.CbAB2LT1P1,self.ui.CbAB2LT1P2,self.ui.CbAB2LT1P3,self.ui.CbAB2LT1P4],
             "PageAngleBetween2LinesT1T2":[ self.ui.CbAB2LT1T2P1T1, self.ui.CbAB2LT1T2P2T1, self.ui.CbAB2LT1T2P1T2 , self.ui.CbAB2LT1T2P2T2,
              self.ui.CbAB2LT1T2P3T1, self.ui.CbAB2LT1T2P4T1, self.ui.CbAB2LT1T2P3T2, self.ui.CbAB2LT1T2P4T2],
              "PageAngleLineT1T2":[self.ui.CbALT1T2L1P1, self.ui.CbALT1T2L1P2, self.ui.CbALT1T2L2P3, self.ui.CbALT1T2L2P4],
              "PageDistance2Points" : [self.ui.CbD2PP1, self.ui.CbD2PP2],
              "PageDistancePointLineT1T2" :[ self.ui.CbDPLT1T2P1T1, self.ui.CbDPLT1T2L1T1, self.ui.CbDPLT1T2L2T1,self.ui.CbDPLT1T2P1T2,self.ui.CbDPLT1T2L1T2, self.ui.CbDPLT1T2L2T2 ],

              "PageDistancePointLineT1":[self.ui.CbDPLT1L1, self.ui.CbDPLT1L2, self.ui.CbDPLT1P1]}


    dic_page2namemeasure = {"PageDistancePointLineT1":"Distance point line T1","PageDistancePointLineT1T2":"Distance point line T1 T2",
                        "PageAngleBetween2LinesT1":"Angle between 2 lines T1","PageAngleBetween2LinesT1T2":"Angle between 2 lines dif T1 T2","PageDistance2Points":"Distance between 2 points T1",
                      'PageDistance2PointsT1T2':"Distance between 2 points T1 T2","PageAngleLineT1T2" : "Angle line T1 and line T2"}


  

    page = self.ui.StackedMeasure.currentWidget().name
    list_point=[]
    for point in dic_page2combobox[page] :
      list_point.append(point.currentText)

    if page == 'PageDistance2Points' and self.ui.CheckBoxT1T2.isChecked():
        page = 'PageDistance2PointsT1T2'
    out = self.logic.CreateMeasure(dic_page2namemeasure[page],list_point)
   




    for measure in out :
      self.AddMeasureTabMeasure(measure)



























  """
   ___    _     _                   
  / _ \  | |_  | |__     ___   _ __ 
 | | | | | __| | '_ \   / _ \ | '__|
 | |_| | | |_  | | | | |  __/ | |   
  \___/   \__| |_| |_|  \___| |_|   
                                    
  """






  def connectButtonPathT1(self):

    surface_folder = qt.QFileDialog.getExistingDirectory(self.parent, "Select a scan folder")
    if surface_folder != '' :
      self.ui.LineEditPathT1.setText(surface_folder)
      self.list_patient_T1, self.dic_patient_T1, lst_files = self.logic.CreateDicPatient(surface_folder)


      self.list_landmarks_exist, self.GROUPS_LANDMARKS = self.logic.CheckAllPatientSameLm( self.dic_patient_T1 ,self.GROUPS_LANDMARKS)
      self.ManageTabLandmarks(self.list_landmarks_exist, self.GROUPS_LANDMARKS)




  def connectButtonPathT2(self):
    if self.dic_patient_T1 == None:
      self.warningMessage('Missing T1 folder')
    else :

      surface_folder = qt.QFileDialog.getExistingDirectory(self.parent, "Select a scan folder")
      if surface_folder != '' :
        self.ui.LineEditPathT2.setText(surface_folder)
        self.lst_patient_T2, self.dic_patient_T2, lst_files = self.logic.CreateDicPatient(surface_folder)
        self.logic.compareT1T2(self.dic_patient_T1, self.dic_patient_T2)






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















  def CatPatientT1T2(self,dic_patients_T1 : dict ,dic_patients_T2 : dict ):
    """ concatene dic patient T1 and dic patient T2
        This function manage dic_patient_T2 if it avoid

    Args:
        dic_patients_T1 (dict): patient Dict T1 with this organisation
          dic = {"001":{"A":[0,0,2],"B":[0,2,3],..},
                  ...,
                 '29':{"A":[0,3,5],"B":[3,6,2],...}
                }

        dic_patients_T2 (dict):patient dict T2 with organiation that dic_patient_T2

    Returns:
        dict: concatenate 2 dicts like this
        dic = {"001":
                    {"T1":{"A":[0,0,2],"B":[0,2,3],...},
                    "T2":{"A":[0,5,2],"B":[5,0,1],...}
                    },
                "029":
                    {"T1":{"A":[0,3,5],"B":[3,6,2],...},
                    "T2":{"A":[535,0,1],"B":[3,5,1],...}
                    }
              }
    """
    dic_patient ={}
    for patient , points in dic_patients_T1.items():
      try :
        dic_patient[patient]={"T1":{landmark.upper() : value for landmark , value in points.items()},"T2":{landmark.upper() : value for landmark , value in dic_patients_T2[patient].items()}}
      except KeyError:
        dic_patient[patient]={"T1":{landmark.upper() : value for landmark , value in points.items()}}
    return dic_patient








  def CreateDicPatient(self,dir_path : str) -> tuple[list,dict,list] :
    
    """
    Read each file in the folder. Return all necessety information (patient, landmark) and list file in folder
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

          #check the patient have many times the same landmark
          if landmark_name in patients_dict[patient]:
            print(f'This patient {patient} have many times this landmark {landmark_name}')



          patients_dict[patient][landmark_name] = position



          #check if landmarks are useable
          good = False
          if isinstance(position,list):
            if len(position) == 3 :
              if not False in [isinstance(value,(int,float,np.ndarray)) for value in position] and not True in np.isnan(position):
                good = True
          if not good:
            print(f'For this file {jsonfile} this landmark {landmark_name} are not good ')




    return patients_lst, patients_dict, lst_files
      










  def compareT1T2(self,dic_patinetT1 : dict , dic_patientT2 : dict):
    """Check if patient T1 and T2 have the same landmark, and the same patient

    Display in the consol difference between T1 and T2

    Args:
        dic_patinetT1 (dict): dict with all patients and landmarks at time T1
        dic_patientT2 (dict): dict with all patients and landmarks at time T2
    """

    #compare landmark patient T1 and T2
    for patientT1, landmarks in dic_patinetT1.items() :
      if set(landmarks) != set(dic_patientT2[patientT1]): 
        dif = set(landmarks) - set(dic_patientT2[patientT1])
        dif.union(set(dic_patientT2[patientT1]) - set(landmarks))
        print(f"T1 and T2 of this patient {patientT1} doesnt have the same landmark, landmark dif {dif}")



    # compare the name patient T1 and T2
    if set(dic_patinetT1.keys()) != set(dic_patientT2.keys()):
      dif = set(dic_patinetT1.keys()) - set(dic_patientT2.keys())
      dif.union(set(dic_patientT2.keys()) - set(dic_patinetT1.keys()) )
      print(f'T1 and T2 doesnt have the same patient, dif patient {dif}')














  def CheckAllPatientSameLm(self,dico : dict ,all_landmarks : Group_landmark):
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
    list_landmark=set()
    for  patient , landmarks in dico.items():
        list_landmark = list_landmark.union(set(landmarks.keys()))


    for patient, landamrks in dico.items():
      dif = list_landmark.difference(set(landamrks.keys()))
      if len(dif) != 0 :
        print(f'this patient {patient} doesnat have this landmark {dif}') 



    list_landmark = list(list_landmark)

    list_otherlandmarks=[]
    list_midlandmarks=[]

    for landmark in list_landmark :
      if landmark[:3].upper() == "Mid".upper():
          list_midlandmarks.append(landmark)
      elif not landmark in all_landmarks  :
        list_otherlandmarks.append(landmark)
          
    all_landmarks["Other"]=list_otherlandmarks
    all_landmarks['Midpoint']=list_midlandmarks
    

    return list_landmark, all_landmarks




  def SaveJsonMidpoint(self,patients_lst,patients_dict,out_path,midpoints):
    midpoint_dic = {}
    

    for patient in patients_lst:
      lst_mid_point = []
      for mid_point in midpoints:
        P1_name = mid_point.split('_')[1]
        P2_name = mid_point.split('_')[2]
        if P1_name and P2_name in patients_dict[patient]:
          try :
            P1_pos = patients_dict[patient][P1_name]
            P2_pos = patients_dict[patient][P2_name]
            mp = self.ComputeMidPoint(np.array(P1_pos),np.array(P2_pos))
          except :
            print(f'Save Midpoint, Warning this patient : {patient}, landmark : {mid_point}, it s not save. Please verify your folder')
            continue
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
    with open(os.path.join(out_path,f"{patient}_Midpoint.json"), 'w', encoding='utf-8') as f:
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
    """ Write an excel with all measurement

    Args:
        path_file (str): excel measurement path
        measures (list): list = [measurement, measurement ,mesasurement] measurement is Measure class

    """
    dic_data_dist_pp = {"Type of measurement":[],"Point 1":[],"Point 2 / Line":[]}
    dic_data_dist_pl = {"Type of measurement":[],"Point 1":[],"Point 2 / Line":[]}
    dic_data_angl = {"Type of measurement":[],"Line 1":[], "Line 2":[]}
    for measure in measures :
      itmersure = iter(measure)
      if measure['Type of measurement'] =="Distance between 2 points" or  measure['Type of measurement'] == 'Distance between 2 points T1 T2':
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





  def OnImportMeasure(self,path_file : str):
    """_summary_

    Args:
        path_file (str): excel measurement path

    Returns:
        list: list measurement like this list = [measure, measure, measure]
    """
    reader = pd.read_excel(path_file,sheet_name=None)
    newreader={"Distance between 2 points":{"Type of measurement":[],"Point 1":[],"Point 2 / Line":[]},
    'Distance point line':{"Type of measurement":[],"Point 1":[],"Point 2 / Line":[]},
    'Angle between 2 lines':{"Type of measurement":[],"Line 1":[], "Line 2":[]}}

    
    list_measure= []
    for name_sheet in reader:
        for name_column in reader[name_sheet]:
            for i in reader[name_sheet][name_column] :
                newreader[name_sheet][name_column].append(i)

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
            list_point = [ line1[0].split('-')[0],line1[0].split('-')[1], line1[1].split('-')[0],line1[1].split('-')[1],line2[0].split('-')[0],line2[0].split('-')[1], line2[1].split('-')[0],line2[1].split('-')[1]]
          else :
            list_point = [ sheet["Line 1"][i].split('-')[0], sheet["Line 1"][i].split('-')[1], sheet["Line 2"][i].split('-')[0], sheet["Line 2"][i].split('-')[1]]



        measures = self.CreateMeasure(sheet['Type of measurement'][i],list_point)
        for measure in measures :
          list_measure.append(measure)


    return list_measure






  def CreateMeasure(self,type_of_measure :str ,list_point: list):
    """ Create Measure

    Args:
        type_of_measure (str): name of measure
        list_point (list): list = [[0,3,5],[35,6,23],[2,56,2],[235,5,2]] the size depend of the measurement

    Returns:
        list: list = [measure , measure , measure]
    """

    out = []

    if type_of_measure == "Angle between 2 lines T1" :

        L1 = Line(Point(list_point[0],"T1"),Point(list_point[1],"T1"))
        L2 = Line(Point(list_point[2],"T1"),Point(list_point[3],"T1"))
        measure = Angle(L1,L2,type_of_measure[:-3],"T1")
        out.append(measure)

    elif type_of_measure == "Angle between 2 lines dif T1 T2":
        T1L1 = Line(Point(list_point[0],"T1"),Point(list_point[1],"T1"))
        T2L1 = Line(Point(list_point[2],"T2"),Point(list_point[3],"T2"))
        T1L2 = Line(Point(list_point[4],"T1"),Point(list_point[5],"T1"))
        T2L2 = Line(Point(list_point[6],"T2"),Point(list_point[7],"T2"))

        measure1 = Angle(T1L1,T1L2,type_of_measure[:-10],"T1")
        measure2 = Angle(T2L1,T2L2,type_of_measure[:-10],"T2")
        measure_dif = Diff2Measure(measure1,measure2)

        out.append(measure1)
        out.append(measure2)
        out.append(measure_dif)


    elif type_of_measure == "Angle line T1 and line T2":
        LT1 = Line(Point(list_point[0],"T1"),Point(list_point[1],"T1"))
        LT2 = Line(Point(list_point[2],"T2"),Point(list_point[3],"T2"))

        measure = Angle(LT1, LT2, type_of_measure)
        out.append(measure)



    elif type_of_measure =="Distance between 2 points T1":
        P1 = Point(list_point[0],"T1")
        P2 = Point(list_point[1],"T1")

        measure = Distance(P1,P2,type_of_measure[:-3],time='T1')
        out.append(measure)

    elif type_of_measure ==  "Distance point line T1":
        P = Point(list_point[0],"T1")
        L = Line(Point(list_point[1],"T1"),Point(list_point[2],"T1"))

        measure = Distance(P,L,type_of_measure[:-3],time='T1')
        out.append(measure)


    elif type_of_measure == "Distance point line T1 T2" or type_of_measure == "Distance point line dif T1 T2":
        PT1 = Point(list_point[0],"T1")
        LT1 = Line(Point(list_point[1],"T1"),Point(list_point[2],"T1"))
        PT2 = Point(list_point[3],"T2")
        LT2 = Line (Point(list_point[4],"T2"), Point(list_point[5],"T2"))

        measure1 = Distance(PT1, LT1, type_of_measure[:-6],time='T1')
        measure2 = Distance(PT2, LT2, type_of_measure[:-6],time='T2')
        measure_dif = Diff2Measure(measure1,measure2)

        out.append(measure1)
        out.append(measure2)
        out.append(measure_dif)

    elif type_of_measure == "Distance between 2 points T1 T2":
        P1 = Point(list_point[0],"T1")
        P2 = Point(list_point[1],"T2")

        measure = Distance(P1,P2,type_of_measure)


        P1 = Point(list_point[0],"T1")
        P2 = Point(list_point[1],"T1")

        T1measure = Distance(P1,P2,type_of_measure[:-6],time='T1')


        P1 = Point(list_point[0],"T2")
        P2 = Point(list_point[1],"T2")

        T2measure = Distance(P1,P2,type_of_measure[:-6],time='T2')

        out.append(measure)
        out.append(T1measure)
        out.append(T2measure)


    else:
      print("doesnt found")


    return out

  



  def ComputeManager(self,list_measure : list ,dic_patient : dict):
    """Compute measure

    Args:
        list_measure (list): list = [measure , measure , measure]
        dic_patient (dic):  dic = {"001":
                                        {"T1":{"A":[0,0,2],"B":[0,2,3],...},
                                        "T2":{"A":[0,5,2],"B":[5,0,1],...}
                                        },
                                    "029":
                                        {"T1":{"A":[0,3,5],"B":[3,6,2],...},
                                        "T2":{"A":[535,0,1],"B":[3,5,1],...}
                                        }
                                      }

    Returns:
        dict: return dic_patient_conmputation, there exemple just below
    """
    dic_patient__computation={"Patient":[],"Type of measurement":[],"Landmarks":[],"R-L Component":[],"R-L Meaning":[],"A-P Component":[],"A-P Meaning":[],"S-I Component":[],"S-I Meaning":[],
    "3D Distance":[],"Yaw Component":[],"Yaw Meaning":[],"Pitch Component":[],"Pitch Meaning":[],"Roll Component":[],"Roll Meaning":[]}
    list_title=["Landmarks","R-L Component","R-L Meaning","A-P Component","A-P Meaning",
    "S-I Component","S-I Meaning","3D Distance","Yaw Component","Yaw Meaning","Pitch Component","Pitch Meaning","Roll Component","Roll Meaning"]

    

    for patient, point in dic_patient.items() :
      for measure in list_measure :
        try: 
          measure['position'] = point
        except KeyError as key:
          print(f"this landmark {key} doesnt exist for this patient",patient)
          continue

        try :
          measure.computation()
        except ZeroDivisionError as Zero :
          print(f'impossible to compute this measure {measure} for this patient {patient} a reason divide by 0 {Zero}')
          continue


        measure.SignManager()

        if measure.isUtilMeasure():
          dic_patient__computation["Patient"].append(patient)
          dic_patient__computation["Type of measurement"].append(measure["Type of measurement + time"])
          for title in list_title :
            dic_patient__computation[title].append(measure[title])

        else :
          print(f'dont write this measure {measure} for this patient {patient} because is useless measure')
          continue
          

      
    print("end ConputeManager")
    return dic_patient__computation
        


  def GenMeasurementExcel(self,list_computation,path,name_file):
    """Create excel file with result of computation

    Args:
        list_computation (list): _description_
        path (str): file's path
        name_file (str): name file
    """


    if len(list_computation['Patient'])>0:
      df = pd.DataFrame(list_computation)
    
      df.to_excel(os.path.join(path,name_file))

    print('------------------- SAVE MEASUREMENT -------------------')




  def AddMidpointToPatient(self,dic_patient : dict , landmark1 : str, landmark2 : str):
    """
    Add midpoint for each patient

    Args:
        dic_patient (dict): dic_patient 
                            dict = {'patient1':{'landmark1':[0,1,0],'landmark2':[0,4,4],...},
                                        .
                                        .
                                    'patientn':{'landmark1':[1,1,0],'landmark2':[0,5,4],...}}
        landmark1 (str): _description
        landmark2 (str): _description_

    Returns:
        dict: _description_
                  dict = {'patient1':{'landmark1':[0,1,0],'landmark2':[0,4,4],'Mid_landmark1_landmark2':[x,x,x],...},
                      .
                      .
                  'patientn':{'landmark1':[1,1,0],'landmark2':[0,5,4],'Mid_landmark1_landmark2':[x,x,x],...}}
    """
    for patient , landmark in dic_patient.items():
      try :
        p1 = landmark[landmark1]
        p2 = landmark[landmark2]
      except KeyError as key:
        print(f'Warning midpoint, dont found landmark {key} for this patient {patient}')
        continue


      try:
        p = list((np.array(p1)+np.array(p2))/2)
      except :
        print(f'Warning compute midpoint error, patient : {patient}, landmarks : {landmark1} {landmark2}')
        continue

      dic_patient[patient][f'Mid_{landmark1}_{landmark2}'] = p



    return dic_patient

      


    
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








