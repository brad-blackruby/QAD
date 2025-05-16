# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 DIMSTYLE command for dimension style settings
 
                              -------------------
        last update          : 2025-05-15
        copyright            : iiiii
        email                : brad@blackruby.dev
        developers           : Brad, ClaudeAI
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""


# Import the PyQt and QGIS libraries
from qgis.PyQt.QtGui import QIcon
from qgis.core import *


from ..qad_dimstyle_dlg import QadDIMSTYLEDialog


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg


# Class that manages the DIMSTYLE command
class QadDIMSTYLECommandClass(QadCommandClass):
   
   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadDIMSTYLECommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "DIMSTYLE")

   def getEnglishName(self):
      return "DIMSTYLE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runDIMSTYLECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/dimStyle.svg")

   def getNote(self):
      # set explanatory notes for the command
      return QadMsg.translate("Command_DIMSTYLE", "Creates new styles, sets the current style, modifies styles, sets overrides on the current style, and compares styles.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
            
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command
      Form = QadDIMSTYLEDialog(self.plugIn)
      Form.exec_()
      return True
