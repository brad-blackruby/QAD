# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 EXTEND command for extending or trimming graphic objects
 
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
from qgis.core import QgsWkbTypes, QgsFeature, QgsPointXY, QgsGeometry


from ..qad_point import QadPoint
from ..qad_getpoint import QadGetPointDrawModeEnum, QadGetPointSelectionModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_pline_cmd import QadPLINECommandClass
from .qad_rectangle_cmd import QadRECTANGLECommandClass
from .qad_generic_cmd import QadCommandClass
from ..qad_entity import QadEntitySet, getSelSet, QadLayerEntitySetIterator
from ..qad_msg import QadMsg
from .. import qad_utils
from .. import qad_layer
from ..qad_variables import QadVariables
from .qad_ssget_cmd import QadSSGetClass
from ..qad_dim import QadDimStyles
from ..qad_extend_trim_fun import extendQadGeometry, trimQadGeometry
from ..qad_geom_relations import getQadGeomClosestPart, QadIntersections
from ..qad_multi_geom import fromQadGeomToQgsGeom, setQadGeomAt


# Class for managing the EXTEND command
class QadEXTENDCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadEXTENDCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "EXTEND")

   def getEnglishName(self):
      return "EXTEND"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runEXTENDCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/extend.svg")

   def getNote(self):
      # set the explanatory notes for the command
      return QadMsg.translate("Command_EXTEND", "Extends (or trims) objects to meet the edges of other objects.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.PLINECommand = None      
      self.RECTANGLECommand = None
      self.entitySet = QadEntitySet() # entities to extend or trim
      self.limitEntitySet = QadEntitySet() # entities that serve as limits
      self.edgeMode = QadVariables.get(QadMsg.translate("Environment variables", "EDGEMODE"))
      self.defaultValue = None # used to manage the right mouse button
      self.nOperationsToUndo = 0

   def __del__(self):
      QadCommandClass.__del__(self)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 3: # when in the line drawing phase
         return self.PLINECommand.getPointMapTool(drawMode)
      elif self.step == 4: # when in the rectangle drawing phase
         return self.RECTANGLECommand.getPointMapTool(drawMode)      
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.step == 3: # when in the line drawing phase
         return self.PLINECommand.getCurrentContextualMenu()
      elif self.step == 4: # when in the rectangle drawing phase
         return self.RECTANGLECommand.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   # ============================================================================
   # extendFeatures
   # ============================================================================
   def extendFeatures(self, geom, toExtend):
      # geom is in map coordinates
      LineTempLayer = None
      self.plugIn.beginEditCommand("Feature extended" if toExtend else "Feature trimmed", \
                                   self.entitySet.getLayerList())
           
      for limitLayerEntitySet in self.entitySet.layerEntitySetList:
         layer = limitLayerEntitySet.layer

         entityIterator = QadLayerEntitySetIterator(limitLayerEntitySet)
         for entity in entityIterator:
            # for each entity in the layer
            f = entity.getFeature()
            if f is None:
               continue
            
            qadGeom = entity.getQadGeom()
            if geom.whatIs() == "POINT":
               # the function returns a list with 
               # (<minimum distance>
               #  <closest point>
               #  <index of the closest geometry>
               #  <index of the closest sub-geometry>
               #  <index of the part of the closest sub-geometry>
               #  <"to the left of" if the point is to the left of the part with the following values:
               #  -   < 0 = left (for line, arc or elliptical arc) or inside (for circles, ellipses)
               #  -   > 0 = right (for line, arc or elliptical arc) or outside (for circles, ellipses)
               # )
               result = getQadGeomClosestPart(qadGeom, geom)
               intPts = [result[1]]
            else:
               intPts = QadIntersections.twoGeomObjects(qadGeom, geom)
               
            for intPt in intPts:
               if toExtend:
                  newGeom = extendQadGeometry(qadGeom, intPt, \
                                              self.limitEntitySet, self.edgeMode)
                  if newGeom is not None:
                     # update the feature with the extended geometry
                     extendedFeature = QgsFeature(f)
                     # transform the geometry to the layer's CRS
                     extendedFeature.setGeometry(fromQadGeomToQgsGeom(newGeom, layer))
                     # plugIn, layer, feature, refresh, check_validity
                     if qad_layer.updateFeatureToLayer(self.plugIn, layer, extendedFeature, False, False) == False:
                        self.plugIn.destroyEditCommand()
                        return
               else: # trim
                  result = trimQadGeometry(qadGeom, intPt, \
                                           self.limitEntitySet, self.edgeMode)                  
                  if result is not None:
                     line1 = result[0]
                     line2 = result[1]
                     atGeom = result[2]
                     atSubGeom = result[3]
                     if layer.geometryType() == QgsWkbTypes.LineGeometry:
                        newQadGeom = setQadGeomAt(qadGeom, line1, atGeom, atSubGeom)
                        if newQadGeom is None:
                           self.plugIn.destroyEditCommand()
                           return
                           
                        trimmedFeature1 = QgsFeature(f)
                        # transform the geometry to the layer's CRS
                        trimmedFeature1.setGeometry(fromQadGeomToQgsGeom(newQadGeom, layer))
                        # plugIn, layer, feature, refresh, check_validity
                        if qad_layer.updateFeatureToLayer(self.plugIn, layer, trimmedFeature1, False, False) == False:
                           self.plugIn.destroyEditCommand()
                           return
                        if line2 is not None:
                           trimmedFeature2 = QgsFeature(f)      
                           # transform the geometry to the layer's CRS
                           trimmedFeature2.setGeometry(fromQadGeomToQgsGeom(line2, layer))
                           # plugIn, layer, feature, coordTransform, refresh, check_validity
                           if qad_layer.addFeatureToLayer(self.plugIn, layer, trimmedFeature2, None, False, False, False) == False:
                              self.plugIn.destroyEditCommand()
                              return
                        
                     else:
                        # add lines to QAD temporary layers
                        if LineTempLayer is None:
                           LineTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.LineGeometry)
                           self.plugIn.addLayerToLastEditCommand("Feature trimmed", LineTempLayer)
                        
                        lineGeoms = [line1]
                        if line2 is not None:
                           lineGeoms.append(line2)

                        # transform the geometry to temporary layers
                        # plugIn, pointGeoms, lineGeoms, polygonGeoms, coord, refresh
                        if qad_layer.addGeometriesToQADTempLayers(self.plugIn, None, lineGeoms, None, None, False) == False:
                           self.plugIn.destroyEditCommand()
                           return
                                                      
                        if delQadGeomAt(qadGeom, atGeom, atSubGeom) == False or updGeom.isEmpty(): # to be deleted
                           # plugIn, layer, feature id, refresh
                           if qad_layer.deleteFeatureToLayer(self.plugIn, layer, f.id(), False) == False:
                              self.plugIn.destroyEditCommand()
                              return
                        else:
                           trimmedFeature1 = QgsFeature(f)
                           # transform the geometry to the layer's CRS
                           trimmedFeature1.setGeometry(fromQadGeomToQgsGeom(qadGeom, layer))
                           # plugIn, layer, feature, refresh, check_validity
                           if qad_layer.updateFeatureToLayer(self.plugIn, layer, trimmedFeature1, False, False) == False:
                              self.plugIn.destroyEditCommand()
                              return

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1
                                                      
      
   # ============================================================================
   # waitForObjectSel
   # ============================================================================
   def waitForObjectSel(self):      
      self.step = 2      
      # set the map tool
      self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC)
      # only editable linear layers that don't belong to dimensions
      layerList = []
      for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All visible vector layers
         if layer.geometryType() == QgsWkbTypes.LineGeometry and layer.isEditable():
            if len(QadDimStyles.getDimListByLayer(layer)) == 0:
               layerList.append(layer)
      
      self.getPointMapTool().layersToCheck = layerList
      self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.NONE)
      self.getPointMapTool().onlyEditableLayers = True
      
      keyWords = QadMsg.translate("Command_EXTEND", "Fence") + "/" + \
                 QadMsg.translate("Command_EXTEND", "Crossing") + "/" + \
                 QadMsg.translate("Command_EXTEND", "Edge") + "/" + \
                 QadMsg.translate("Command_EXTEND", "Undo")
      prompt = QadMsg.translate("Command_EXTEND", "Select the object to extend or shift-select to trim or [{0}]: ").format(keyWords)
      
      englishKeyWords = "Fence" + "/" + "Crossing" + "/" + "Edge" + "/" + "Undo"
      keyWords += "_" + englishKeyWords
      # prepares to wait for a point or enter or a keyword         
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)      


   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      # =========================================================================
      # REQUEST FOR BOUNDARY OBJECTS SELECTION
      if self.step == 0: # beginning of the command
         CurrSettingsMsg = QadMsg.translate("QAD", "\nCurrent settings: ")
         if self.edgeMode == 0: # 0 = no extension
            CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_EXTEND", "Edge = No extend")
         else:
            CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_EXTEND", "Edge = Extend")
                  
         self.showMsg(CurrSettingsMsg)         
         self.showMsg(QadMsg.translate("Command_EXTEND", "\nSelect extension limits..."))
         
         if self.SSGetClass.run(msgMapTool, msg) == True:
            # selection completed
            self.step = 1
            return self.run(msgMapTool, msg)        
      
      # =========================================================================
      # RESPONSE TO BOUNDARY OBJECTS SELECTION
      elif self.step == 1:
         self.limitEntitySet.set(self.SSGetClass.entitySet)
         
         if self.limitEntitySet.count() == 0:
            return True # end command

         # prepares to wait for the selection of objects to extend/trim
         self.waitForObjectSel()
         return False
      
      # =========================================================================
      # RESPONSE TO SELECTION OF OBJECTS TO EXTEND
      elif self.step == 2:
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # then the command was reactivated and returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if using the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # the point arrives as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_EXTEND", "Fence") or value == "Fence":
               # Select all objects that intersect a polyline
               self.PLINECommand = QadPLINECommandClass(self.plugIn)
               # if this flag = True, the command is used inside another command to draw a line
               # that will not be saved on a layer
               self.PLINECommand.virtualCmd = True   
               self.PLINECommand.run(msgMapTool, msg)
               self.step = 3
               return False               
            elif value == QadMsg.translate("Command_EXTEND", "Crossing") or value == "Crossing":
               # Select all objects that intersect a rectangle                                  
               self.RECTANGLECommand = QadRECTANGLECommandClass(self.plugIn)
               # if this flag = True, the command is used inside another command to draw a line
               # that will not be saved on a layer
               self.RECTANGLECommand.virtualCmd = True   
               self.RECTANGLECommand.run(msgMapTool, msg)
               self.step = 4
               return False               
            elif value == QadMsg.translate("Command_EXTEND", "Edge") or value == "Edge":
               # To extend an object using also the extensions of reference objects
               # see variable EDGEMODE
               keyWords = QadMsg.translate("Command_EXTEND", "Extend") + "/" + \
                          QadMsg.translate("Command_EXTEND", "No extend")                                              

               if self.edgeMode == 0: # 0 = no extension
                  self.defaultValue = QadMsg.translate("Command_EXTEND", "No extend")
               else: 
                  self.defaultValue = QadMsg.translate("Command_EXTEND", "Extend")                   
               prompt = QadMsg.translate("Command_EXTEND", "Specify an extension mode [{0}] <{1}>: ").format(keyWords, self.defaultValue)
                   
               englishKeyWords = "Extend" + "/" + "No extend"
               keyWords += "_" + englishKeyWords
               # prepares to wait for enter or a keyword         
               # msg, inputType, default, keyWords, no check
               self.waitFor(prompt, \
                            QadInputTypeEnum.KEYWORDS, \
                            self.defaultValue, \
                            keyWords, QadInputModeEnum.NONE)
               self.step = 5               
               return False               
            elif value == QadMsg.translate("Command_EXTEND", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0: 
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))
         elif type(value) == QgsPointXY: # if a point has been selected
            self.entitySet.clear()
            if self.getPointMapTool().entity.isInitialized():
               self.entitySet.addEntity(self.getPointMapTool().entity)
               ToExtend = True if self.getPointMapTool().shiftKey == False else False
               self.extendFeatures(QadPoint().set(value), ToExtend)
            else:
               # looking for entities at the indicated point, considering
               # only editable linear layers that don't belong to dimensions
               layerList = []
               for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All visible vector layers
                  if layer.geometryType() == QgsWkbTypes.LineGeometry and layer.isEditable():
                     if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                        layerList.append(layer)
                                     
               result = qad_utils.getEntSel(self.getPointMapTool().toCanvasCoordinates(value), \
                                            self.getPointMapTool(), \
                                            QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                            layerList)
               if result is not None:
                  feature = result[0]
                  layer = result[1]
                  point = result[2]
                  self.entitySet.addEntity(QadEntity().set(layer, feature.id()))
                  self.extendFeatures(QadPoint().set(value), True)
         else:
            return True # end command
         
         # prepares to wait for the selection of objects to extend/trim
         self.waitForObjectSel()
                                          
         return False 

      # =========================================================================
      # RESPONSE TO POINT REQUEST FOR FENCE MODE (from step = 2)
      elif self.step == 3: # after waiting for a point, restart the command
         if self.PLINECommand.run(msgMapTool, msg) == True:
            if self.PLINECommand.polyline.qty() > 0:
               if msgMapTool == True: # if the polyline comes from a graphic selection
                  ToExtend = True if self.getPointMapTool().shiftKey == False else False
               else:
                  ToExtend = True

               # looking for all geometries passing through the polyline, considering
               # only editable linear layers that don't belong to dimensions
               layerList = []
               for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All visible vector layers
                  if layer.geometryType() == QgsWkbTypes.LineGeometry and layer.isEditable():
                     if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                        layerList.append(layer)
               
               self.entitySet = getSelSet("F", self.getPointMapTool(), self.PLINECommand.polyline.asPolyline(), \
                                                    layerList)            
               self.extendFeatures(self.PLINECommand.polyline, ToExtend)
            del self.PLINECommand
            self.PLINECommand = None

            # prepares to wait for the selection of objects to extend/trim
            self.waitForObjectSel()                                 
            self.getPointMapTool().refreshSnapType() # update snapType which may have been changed by the pline maptool                     
         return False

      # =========================================================================
      # RESPONSE TO POINT REQUEST FOR CROSSING MODE (from step = 2)
      elif self.step == 4: # after waiting for a point, restart the command
         if self.RECTANGLECommand.run(msgMapTool, msg) == True:            
            if self.RECTANGLECommand.polyline.qty() > 0:
               if msgMapTool == True: # if the polyline comes from a graphic selection
                  ToExtend = True if self.getPointMapTool().shiftKey == False else False
               else:
                  ToExtend = True
               
               # looking for all geometries passing through the rectangle, considering
               # only editable linear layers that don't belong to dimensions
               layerList = []
               for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All visible vector layers
                  if layer.geometryType() == QgsWkbTypes.LineGeometry and layer.isEditable():
                     if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                        layerList.append(layer)
                        
               self.entitySet = getSelSet("F", self.getPointMapTool(), self.RECTANGLECommand.polyline.asPolyline(), \
                                                    layerList)            
               self.extendFeatures(self.RECTANGLECommand.polyline, ToExtend)
            del self.RECTANGLECommand
            self.RECTANGLECommand = None

            # prepares to wait for the selection of objects to extend/trim
            self.waitForObjectSel()                                 
            self.getPointMapTool().refreshSnapType() # update snapType which may have been changed by the rectangle maptool                   
         return False

      # =========================================================================
      # RESPONSE TO EXTENSION TYPE REQUEST (from step = 2)
      elif self.step == 5: # after waiting for a point or a real number, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # then the command was reactivated and returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().rightButton == True: # if using the right mouse button
               value = self.defaultValue 
            else:
               self.setMapTool(self.getPointMapTool()) # reactivate the maptool
               return False
         else: # the value arrives as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_EXTEND", "No extend") or value == "No extend":
               self.edgeMode = 0
               QadVariables.set(QadMsg.translate("Environment variables", "EDGEMODE"), self.edgeMode)
               QadVariables.save()
               # prepares to wait for the selection of objects to extend/trim
               self.waitForObjectSel()
            elif value == QadMsg.translate("Command_EXTEND", "Extend") or value == "Extend":
               self.edgeMode = 1
               QadVariables.set(QadMsg.translate("Environment variables", "EDGEMODE"), self.edgeMode)
               QadVariables.save()
               # prepares to wait for the selection of objects to extend/trim
               self.waitForObjectSel()
         
         return False
