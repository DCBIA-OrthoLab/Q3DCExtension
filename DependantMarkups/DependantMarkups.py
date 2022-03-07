from __future__ import print_function

import slicer
from slicer.ScriptedLoadableModule import *


class DependantMarkups(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Dependent Markups"
        parent.categories = ["Developer Tools"]
        parent.dependencies = []
        parent.contributors = [
            'David Allemang (Kitware Inc.)',
        ]
        parent.helpText = """
        Dependent Markups is a collection of utilities to manage markups that 
        depend on the status of other markups or models in the scene.
        """
        parent.acknowledgementText = """
        This work was supported by the National Institute of Dental and
        Craniofacial Research and the National Institute of Biomedical
        Imaging and Bioengineering of the National Institutes of Health.
        """
        self.parent = parent


class DependantMarkupsLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)


class DependantMarkupsTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        self.setUp()
        self.delayDisplay('Tests not yet implemented.')
