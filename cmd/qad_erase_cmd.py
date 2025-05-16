# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 ERASE command for deleting objects
 
                              -------------------
        last update          : 2025-05-15
        copyright            : iiiiii
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


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_ssget_cmd import QadSSGetClass
from .. import qad_layer


# Class that manages the ERASE command
class QadERASECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadERASECommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "ERASE")

   def getEnglishName(self):
      return "ERASE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runERASECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/erase.svg")

   def getNote(self):
      # set the explanatory notes for the command
      return QadMsg.translate("Command_ERASE", "Removes objects of the map.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = True

   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass
      
   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 0: # when in the entity selection phase
         return self.SSGetClass.getPointMapTool(drawMode)
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)

   def run(self, msgMapTool = False, msg = None):
            
      # =========================================================================
      # REQUEST FIRST POINT FOR OBJECT SELECTION
      if self.step == 0: # start of the command
         if self.SSGetClass.run(msgMapTool, msg) == True:
            # selection completed
            self.step = 1
            return self.run(msgMapTool, msg)
         else:
            return False
      
      # =========================================================================
      # DELETION OF OBJECTS
      elif self.step == 1:
         self.plugIn.beginEditCommand("Feature deleted", self.SSGetClass.entitySet.getLayerList())
              
         for layerEntitySet in self.SSGetClass.entitySet.layerEntitySetList:
            # plugIn, layer, featureIds, refresh
            if qad_layer.deleteFeaturesToLayer(self.plugIn, layerEntitySet.layer, \
                                               layerEntitySet.featureIds, False) == False:
               self.plugIn.destroyEditCommand()
               return
            
         self.plugIn.endEditCommand()
            
         return True # end of command
