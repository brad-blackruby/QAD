# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 BREAK command to cut an object
 
                              -------------------
        last update          : 2025-05-10
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


from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsWkbTypes, QgsFeature, QgsPointXY


from .qad_generic_cmd import QadCommandClass
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_entsel_cmd import QadEntSelClass
from ..qad_msg import QadMsg
from .. import qad_layer
from .. import qad_utils
from ..qad_break_fun import breakQadGeometry
from ..qad_multi_geom import fromQadGeomToQgsGeom, setQadGeomAt


# Class that manages the BREAK command
class QadBREAKCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadBREAKCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "BREAK")

   def getEnglishName(self):
      return "BREAK"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runBREAKCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/break.svg")
   
   def getNote(self):
      # set the explanatory notes of the command      
      return QadMsg.translate("Command_BREAK", "Breaks an object.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entSelClass = None      
      self.firstPt = None
      self.secondPt = None

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.entSelClass is not None:
         self.entSelClass.entity.deselectOnLayer()
         del self.entSelClass

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 1: # when in entity selection phase
         return self.entSelClass.getPointMapTool(drawMode)
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.step == 1: # when in entity selection phase
         return self.entSelClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = 1         
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_BREAK", "Select the object to break: ")
      # exclude selection of points and polygons
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = True
      self.entSelClass.checkPolygonLayer = False
      self.entSelClass.checkDimLayers = False
      self.entSelClass.onlyEditableLayers = True

      self.entSelClass.run(msgMapTool, msg)


   # ============================================================================
   # breakFeatures
   # ============================================================================
   def breakFeatures(self):
      f = self.entSelClass.entity.getFeature()
      if f is None:
         return
      qadGeom = self.entSelClass.entity.getQadGeom()
      result = breakQadGeometry(qadGeom, self.firstPt, self.secondPt)
      if result is None: return
      
      layer = self.entSelClass.entity.layer
      LineTempLayer = None
      self.plugIn.beginEditCommand("Feature broken", layer)

      line1 = result[0]
      line2 = result[1]
      atGeom = result[2]
      atSubGeom = result[3]
      if layer.geometryType() == QgsWkbTypes.LineGeometry:
         if line1 is not None:
            updGeom = setQadGeomAt(qadGeom, line1, atGeom, atSubGeom)
            if updGeom is None:
               self.plugIn.destroyEditCommand()
               return
            brokenFeature1 = QgsFeature(f)
            # transform the geometry into the layer CRS
            brokenFeature1.setGeometry(fromQadGeomToQgsGeom(updGeom, layer))
            # plugIn, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, layer, brokenFeature1, False, False) == False:
               self.plugIn.destroyEditCommand()
               return
         if line2 is not None:
            brokenFeature2 = QgsFeature(f)      
            # transform the geometry into the layer CRS
            brokenFeature2.setGeometry(fromQadGeomToQgsGeom(line2, layer))
            # plugIn, layer, feature, coordTransform, refresh, check_validity
            if qad_layer.addFeatureToLayer(self.plugIn, layer, brokenFeature2, None, False, False, False) == False:
               self.plugIn.destroyEditCommand()
               return            
      else:
         # add the lines to the QAD temporary layers
         if LineTempLayer is None:
            LineTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.LineGeometry)
            self.plugIn.addLayerToLastEditCommand("Feature broken", LineTempLayer)
         
         lineGeoms = []
         if line1 is not None:
            lineGeoms.append(fromQadGeomToQgsGeom(line1, layer))
         if line2 is not None:
            lineGeoms.append(fromQadGeomToQgsGeom(line2, layer))

         # transform the geometry to that of the temporary layers
         # plugIn, pointGeoms, lineGeoms, polygonGeoms, coord, refresh
         if qad_layer.addGeometriesToQADTempLayers(self.plugIn, None, lineGeoms, None, None, False) == False:
            self.plugIn.destroyEditCommand()
            return
         
         updGeom = delQadGeomAt(qadGeom, atGeom, atSubGeom)

         if updGeom == False: # to be deleted
            # plugIn, layer, feature id, refresh
            if qad_layer.deleteFeatureToLayer(self.plugIn, layer, f.id(), False) == False:
               self.plugIn.destroyEditCommand()
               return
         else:
            brokenFeature1 = QgsFeature(f)
            # transform the geometry into the layer CRS
            brokenFeature1.setGeometry(fromQadGeomToQgsGeom(updGeom, layer))
            # plugIn, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, layer, brokenFeature1, False, False) == False:
               self.plugIn.destroyEditCommand()
               return

      self.plugIn.endEditCommand()

       
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command
      
      if self.step == 0:     
         self.waitForEntsel(msgMapTool, msg)
         return False # continue
      
      # =========================================================================
      # RESPONSE TO THE SELECTION OF AN ENTITY (from step = 0)
      elif self.step == 1:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               layer = self.entSelClass.entity.layer
               self.firstPt = self.entSelClass.point
               self.plugIn.setLastPoint(self.firstPt)
               
               keyWords = QadMsg.translate("Command_BREAK", "First point")
               prompt = QadMsg.translate("Command_BREAK", "Specify second break point or [{0}]: ").format(keyWords)
               
               self.step = 2
               self.getPointMapTool().refreshSnapType() # update the snapType which may have been modified by the entity selection maptool
                                   
               englishKeyWords = "First point"
               keyWords += "_" + englishKeyWords
               # prepares to wait for a point or enter or a keyword      
               # msg, inputType, default, keyWords, no check
               self.waitFor(prompt, \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                            None, \
                            keyWords, QadInputModeEnum.NONE)      
               return False
            else:
               if self.entSelClass.canceledByUsr == True: # end command
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)
         return False # continue

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR THE SECOND BREAK POINT (from step = 1)
      elif self.step == 2: # after waiting for a point or a keyword, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin that has disabled Qad has been activated
            # then the command has been reactivated which returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if used the right mouse button
                  pass # default option "second point"
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if value is None or type(value) == unicode:
            # prepares to wait for a point
            self.waitForPoint(QadMsg.translate("Command_BREAK", "Specify first break point: "))            
            self.step = 3
         elif type(value) == QgsPointXY: # if the second point has been entered
            self.secondPt = value
            self.plugIn.setLastPoint(self.secondPt)
            self.breakFeatures()            
            return True
         
         return False 

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR THE FIRST BREAK POINT (from step = 2)
      elif self.step == 3: # after waiting for a point, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin that has disabled Qad has been activated
            # then the command has been reactivated which returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if used the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         self.firstPt =  value
         self.plugIn.setLastPoint(self.firstPt)

         # prepares to wait for a point
         self.waitForPoint(QadMsg.translate("Command_BREAK", "Specify second break point: "))
         self.step = 4
         
         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR THE SECOND BREAK POINT (from step = 3)
      elif self.step == 4: # after waiting for a point, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin that has disabled Qad has been activated
            # then the command has been reactivated which returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if used the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         self.secondPt = value
         self.plugIn.setLastPoint(self.secondPt)
         self.breakFeatures()            
         
         return True
