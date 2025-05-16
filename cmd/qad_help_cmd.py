# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 HELP command that opens the QAD guide
 
                              -------------------
        last update          : 2025-05-16
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
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QDir
import pathlib

from ..qad_utils import getMacAddress, getQADPath
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg, qadShowPluginPDFHelp, qadShowSupportersPage


# Class that manages the HELP command
class QadHELPCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadHELPCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "HELP")

   def getEnglishName(self):
      return "HELP"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runHELPCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/help.svg")

   def getNote(self):
      # set the explanatory notes for the command
      return QadMsg.translate("Command_HELP", "The QAD manual will be showed.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
        
   def run(self, msgMapTool = False, msg = None):
      qadShowPluginPDFHelp()       
      return True


# Class that manages the SUPPORTERS command
class QadSUPPORTERSCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadSUPPORTERSCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "SUPPORTERS")

   def getEnglishName(self):
      return "SUPPORTERS"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runSUPPORTERSCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/supporters.svg")

   def getNote(self):
      # set the explanatory notes for the command
      return QadMsg.translate("Command_SUPPORTERS", "The QAD supporting members page will be showed.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
        
   def run(self, msgMapTool = False, msg = None):
      msg1 = QadMsg.translate("Command_SUPPORTERS", "Your mac address is")
      msg2 = QadMsg.translate("Command_SUPPORTERS", "QAD installation path is")
      self.showMsg("\n" + msg1 + " " + getMacAddress() + ". " + msg2 + " " + getQADPath())
      qadShowSupportersPage()       
      return True
