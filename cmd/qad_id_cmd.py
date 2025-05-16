# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 ID command that returns the coordinate of a selected point
 
                              -------------------
        begin                : 2025-05-16
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

from qgis.core import QgsPointXY
from qgis.PyQt.QtGui import QIcon

from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg


# Class that manages the ID command
class QadIDCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadIDCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "ID")

   def getEnglishName(self):
      return "ID"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runIDCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/id.svg")

   def getNote(self):
      # set the explanatory notes for the command
      return QadMsg.translate("Command_ID", "Displays the coordinate values of a specified location.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
        
   def run(self, msgMapTool = False, msg = None):           
      if self.step == 0: # beginning of the command
         self.waitForPoint() # prepares to wait for a point
         self.step = self.step + 1
         return False
      elif self.step == 1: # after waiting for a point, restart the command
         if msgMapTool == True: # the point comes from a graphical selection
            # the following condition occurs if during the selection of a point
            # another plugin has been activated that has deactivated Qad
            # then the command was reactivated and returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            pt = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            pt = msg

         if type(pt) == QgsPointXY:
            self.plugIn.setLastPoint(pt)            
            self.showMsg("\n" + pt.toString())
         return True
