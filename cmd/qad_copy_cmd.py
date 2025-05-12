# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 COPY command for copying objects
 
                              -------------------
        begin                : 2025-05-11
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
from qgis.core import QgsPointXY


from .qad_copy_maptool import Qad_copy_maptool, Qad_copy_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_ssget_cmd import QadSSGetClass
from ..qad_entity import QadCacheEntitySet, QadCacheEntitySetIterator, QadEntityTypeEnum
from ..qad_variables import QadVariables
from .. import qad_utils
from .. import qad_layer
from ..qad_dim import QadDimEntity, QadDimStyles, appendDimEntityIfNotExisting
from ..qad_multi_geom import fromQadGeomToQgsGeom


# Class that manages the COPY command
class QadCOPYCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadCOPYCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "COPY")

   def getEnglishName(self):
      return "COPY"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runCOPYCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/copyEnt.svg")

   def getNote(self):
      # set explanatory notes for the command
      return QadMsg.translate("Command_COPY", "Copies selected objects a specified distance in a specified direction.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = True
      self.cacheEntitySet = QadCacheEntitySet()
      self.basePt = QgsPointXY()
      self.series = False
      self.seriesLen = 2
      self.adjust = False
      self.copyMode = QadVariables.get(QadMsg.translate("Environment variables", "COPYMODE"))
      
      self.nOperationsToUndo = 0

   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 0: # when in entity selection phase
         return self.SSGetClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_copy_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 0: # when in entity selection phase
         return None # return self.SSGetClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   # ============================================================================
   # move
   # ============================================================================
   def move(self, entity, offsetX, offsetY, openForm = True):
      # check if the entity belongs to a dimension style
      if entity.whatIs() == "ENTITY":
         # move the entity geometry
         qadGeom = entity.getQadGeom().copy() # copy it
         qadGeom.move(offsetX, offsetY)
         f = entity.getFeature()
         f.setGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer))
         # plugIn, layer, feature, coordTransform, refresh, check_validity
         if qad_layer.addFeatureToLayer(self.plugIn, entity.layer, f, None, False, False, openForm) == False:  
            return False
      elif entity.whatIs() == "DIMENTITY":
         newDimEntity = QadDimEntity(entity) # copy it
         # move the dimension
         newDimEntity.move(offsetX, offsetY)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False             
            
      return True
