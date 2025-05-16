# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Command to be inserted in other commands for feature selection
 
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
from qgis.core import QgsWkbTypes, QgsPointXY


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from ..qad_entity import QadEntity
from ..qad_getpoint import QadGetPointSelectionModeEnum
from .. import qad_utils
from ..qad_dim import QadDimStyles
from ..qad_variables import QadVariables


# ===============================================================================
# QadEntSelClass
# ===============================================================================
class QadEntSelClass(QadCommandClass):
   """
      This class selects an entity. It is not able to select a dimension but only a component of a dimension.
   """

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadEntSelClass(self.plugIn)
      
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entity = QadEntity()
      self.point = None
      # options to limit objects to be selected
      self.onlyEditableLayers = False     
      self.checkPointLayer = True
      self.checkLineLayer = True
      self.checkPolygonLayer = True
      self.checkDimLayers = True
      self.selDimEntity = False # whether to return a QadDimEntity object or not
      self.msg = QadMsg.translate("QAD", "Select object: ")
      self.deselectOnFinish = False
      self.canceledByUsr = False # becomes true if the user doesn't want to choose anything (e.g. if right mouse button is used)
      
   def __del__(self):
      QadCommandClass.__del__(self)
      if self.deselectOnFinish:
         self.entity.deselectOnLayer()


   # ============================================================================
   # setEntity
   # ============================================================================
   def setEntity(self, layer, fid):
      del self.entity
      if self.selDimEntity: # if it's possible to return a QadDimEntity object
         # check if the entity belongs to a dimension style
         self.entity = QadDimStyles.getDimEntity(layer, fid)
         if self.entity is None: # if it's not a dimension
            self.entity = QadEntity()
            self.entity.set(layer, fid)
      else:
         self.entity = QadEntity()
         self.entity.set(layer, fid)
      
      self.entity.selectOnLayer()


   # ============================================================================
   # getLayersToCheck
   # ============================================================================
   def getLayersToCheck(self):
      layerList = []
      for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All visible vector layers
         # consider only vector layers that are filtered by type
         if ((layer.geometryType() == QgsWkbTypes.PointGeometry and self.checkPointLayer == True) or \
             (layer.geometryType() == QgsWkbTypes.LineGeometry and self.checkLineLayer == True) or \
             (layer.geometryType() == QgsWkbTypes.PolygonGeometry and self.checkPolygonLayer == True)) and \
             (self.onlyEditableLayers == False or layer.isEditable()):
            # if dimension layers must be included
            if self.checkDimLayers == True or \
               len(QadDimStyles.getDimListByLayer(layer)) == 0:
               layerList.append(layer)
         
      return layerList

            
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      # =========================================================================
      # POINT or ENTITY REQUEST
      if self.step == 0: # beginning of the command
         # set the map tool
         self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
         # set the layers to check on the maptool
         self.getPointMapTool().layersToCheck = self.getLayersToCheck()
                  
         keyWords = QadMsg.translate("Command_ENTSEL", "Last")
                  
         englishKeyWords = "Last"
         keyWords += "_" + englishKeyWords
         # preparing to wait for a point or enter or a keyword         
         # msg, inputType, default, keyWords, no check
         self.waitFor(self.msg, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NONE)
         
         self.step = 1
         return False

      # =========================================================================
      # RESPONSE TO POINT or ENTITY REQUEST
      elif self.step == 1: # after waiting for a point, the command restarts
         entity = None
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # then the command was reactivated which returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if right mouse button was used
                  self.canceledByUsr = True
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False
               
            value = self.getPointMapTool().point
            if self.getPointMapTool().entity.isInitialized():
               entity = self.getPointMapTool().entity               
         else: # the point comes as a parameter of the function
            value = msg

         if value is None:
            self.canceledByUsr = True
            return True # end command
         
         if type(value) == str:
            if value == QadMsg.translate("Command_ENTSEL", "Last") or value == "Last":
               # Select the last inserted entity
               lastEnt = self.plugIn.getLastEntity()
               if lastEnt is not None:
                  # check on layer
                  if self.onlyEditableLayers == False or lastEnt.layer.isEditable() == True:
                     # check on type
                     if (self.checkPointLayer == True and lastEnt.layer.geometryType() == QgsWkbTypes.PointGeometry) or \
                        (self.checkLineLayer == True and lastEnt.layer.geometryType() == QgsWkbTypes.LineGeometry) or \
                        (self.checkPolygonLayer == True and lastEnt.layer.geometryType() == QgsWkbTypes.PolygonGeometry):
                        # check on dimension layers
                        if self.checkDimLayers == True or QadDimStyles.isDimEntity(lastEnt) == False:
                           self.setEntity(lastEnt.layer, lastEnt.featureId)
         elif type(value) == QgsPointXY:
            if entity is None:
               # look for entities at the indicated point
               result = qad_utils.getEntSel(self.getPointMapTool().toCanvasCoordinates(value),
                                            self.getPointMapTool(), \
                                            QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                            self.getLayersToCheck())
               if result is not None:
                  feature = result[0]
                  layer = result[1]
                  self.setEntity(layer, feature.id())               
            else:
               self.setEntity(entity.layer, entity.featureId)

            self.point = value
                                   
         if self.deselectOnFinish:
            self.entity.deselectOnLayer()

         return True # end command
