# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 OFFSET command to create offset of an object
 
                              -------------------
        begin                : 2025-05-07
        copyright            : GPL
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
from qgis.core import QgsPointXY, QgsWkbTypes, QgsGeometry, QgsFeature
from qgis.PyQt.QtGui import QIcon


from .qad_offset_maptool import Qad_offset_maptool, Qad_offset_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum   
from ..qad_entity import QadEntity
from ..qad_variables import QadVariables
from .. import qad_utils
from .. import qad_layer
from ..qad_rubberband import createRubberBand
from ..qad_offset_fun import offsetPolyline, offsetQGSGeom
from ..qad_geom_relations import getQadGeomClosestPart
from ..qad_multi_geom import getQadGeomAt, fromQgsGeomToQadGeom


# Class that manages the OFFSET command
class QadOFFSETCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiate a new command of the same type """
      return QadOFFSETCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "OFFSET")

   def getEnglishName(self):
      return "OFFSET"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runOFFSETCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/offset.svg")

   def getNote(self):
      # set explanatory notes for the command
      return QadMsg.translate("Command_OFFSET", "Creates concentric circles, parallel lines, and parallel curves.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entity = QadEntity()
      self.subGeom = None
      self.partNum = None
      self.offset = QadVariables.get(QadMsg.translate("Environment variables", "OFFSETDIST"))
      self.lastOffSetOnLeftSide = 0
      self.lastOffSetOnRightSide = 0
      self.firstPt = QgsPointXY()
      self.eraseEntity = False
      self.multi = False
      self.OnlySegment = False
      self.gapType = QadVariables.get(QadMsg.translate("Environment variables", "OFFSETGAPTYPE"))
      
      self.featureCache = [] # list of (layer, feature)
      self.undoFeatureCacheIndexes = [] # positions in featureCache for undo points
      self.rubberBand = createRubberBand(self.plugIn.canvas, QgsWkbTypes.LineGeometry)
      self.rubberBandPolygon = createRubberBand(self.plugIn.canvas, QgsWkbTypes.PolygonGeometry)

   def __del__(self):
      QadCommandClass.__del__(self)
      self.rubberBand.hide()
      self.plugIn.canvas.scene().removeItem(self.rubberBand)
      self.rubberBandPolygon.hide()
      self.plugIn.canvas.scene().removeItem(self.rubberBandPolygon)
      
   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_offset_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None

   # ============================================================================
   # addFeatureCache
   # ============================================================================
   def addFeatureCache(self, newPt):
      featureCacheLen = len(self.featureCache)
      layer = self.entity.layer
      f = self.entity.getFeature()

      offsetDistance = None
      if self.offset > 0:
         offsetDistance = self.offset                     
         if self.multi == True:
            # the function returns a list with:
            # (<minimum distance>
            # <closest point>
            # <index of the closest geometry>
            # <index of the closest sub-geometry>
            # <index of the part of the closest sub-geometry>
            # <"left of" if the point is to the left of the part with the following values:
            # -   < 0 = left (for line, arc or ellipse arc) or inside (for circles, ellipses)
            # -   > 0 = right (for line, arc or ellipse arc) or outside (for circles, ellipses)
            dummy = getQadGeomClosestPart(self.subGeom, newPt)
            leftOf = dummy[5]         
                 
            if leftOf < 0: # to the left (for line, arc or ellipse arc) or inside (for circles, ellipses)            
               offsetDistance = self.offset + self.lastOffSetOnLeftSide
               self.lastOffSetOnLeftSide = offsetDistance
               self.getPointMapTool().lastOffSetOnLeftSide = self.lastOffSetOnLeftSide
            else: # to the right
               offsetDistance = self.offset + self.lastOffSetOnRightSide         
               self.lastOffSetOnRightSide = offsetDistance            
               self.getPointMapTool().lastOffSetOnRightSide = self.lastOffSetOnRightSide

      # if self.subGeom implements the isClosed method
      closed = self.subGeom.isClosed() if hasattr(self.subGeom, "isClosed") and callable(getattr(self.subGeom, "isClosed")) else False

      if layer.geometryType() == QgsWkbTypes.PolygonGeometry or closed == True:
         qgsGeom = QgsGeometry.fromPolygonXY([self.subGeom.asPolyline()])
      else:
         qgsGeom = QgsGeometry.fromPolylineXY(self.subGeom.asPolyline())

      offsetQGSGeomList = offsetQGSGeom(qgsGeom, \
                                        newPt, \
                                        self.gapType, \
                                        offsetDistance)

      added = False
      for g in offsetQGSGeomList:
         # convert to QAD geometry to recognize curves
         g = fromQgsGeomToQadGeom(g).asGeom(layer.wkbType())        
         
         if g.type() == QgsWkbTypes.LineGeometry or g.type() == QgsWkbTypes.PolygonGeometry:           
            offsetFeature = QgsFeature(f)
            # transform the geometry to the layer CRS
            offsetFeature.setGeometry(self.mapToLayerCoordinates(layer, g))
            self.featureCache.append([layer, offsetFeature])
            self.addFeatureToRubberBand(layer, offsetFeature)            
            added = True           

      if added:      
         self.undoFeatureCacheIndexes.append(featureCacheLen)


   # ============================================================================
   # undoGeomsInCache
   # ============================================================================
   def undoGeomsInCache(self):
      tot = len(self.featureCache)
      if tot > 0:
         iEnd = self.undoFeatureCacheIndexes[-1]
         i = tot - 1
         
         del self.undoFeatureCacheIndexes[-1] # delete last undo
         while i >= iEnd:
            del self.featureCache[-1] # delete feature
            i = i - 1
         self.refreshRubberBand()

            
   # ============================================================================
   # addFeatureToRubberBand
   # ============================================================================
   def addFeatureToRubberBand(self, layer, feature):
      if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
         if feature.geometry().type() == QgsWkbTypes.PolygonGeometry:
            self.rubberBandPolygon.addGeometry(feature.geometry(), layer)
         else:
            self.rubberBand.addGeometry(feature.geometry(), layer)
      else:
         self.rubberBand.addGeometry(feature.geometry(), layer)
      
      
   # ============================================================================
   # refreshRubberBand
   # ============================================================================
   def refreshRubberBand(self):
      self.rubberBand.reset(QgsWkbTypes.LineGeometry)
      self.rubberBandPolygon.reset(QgsWkbTypes.PolygonGeometry)
      for f in self.featureCache:
         layer = f[0]
         feature = f[1]
         if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            if feature.geometry().type() == QgsWkbTypes.PolygonGeometry:
               self.rubberBandPolygon.addGeometry(feature.geometry(), layer)
            else:
               self.rubberBand.addGeometry(feature.geometry(), layer)            
         else:
            self.rubberBand.addGeometry(feature.geometry(), layer)            


   # ============================================================================
   # addToLayer
   # ============================================================================
   def addToLayer(self, currLayer):
      featuresLayers = [] # list of (layer, features)
      
      for f in self.featureCache:
         layer = f[0]
         feature = f[1]
         found = False
         for featuresLayer in featuresLayers:
            if featuresLayer[0].id() == layer.id():
               found = True
               featuresLayer[1].append(feature)
               break
         # if the layer wasn't there yet
         if not found:
            featuresLayers.append([layer, [feature]])

      layerList = []
      for featuresLayer in featuresLayers:
         layerList.append(featuresLayer[0])

      PointTempLayer = None
      LineTempLayer = None
      PolygonTempLayer = None
      self.plugIn.beginEditCommand("Feature offseted", layerList)

      for featuresLayer in featuresLayers:
         # filter features by type
         pointGeoms, lineGeoms, polygonGeoms = qad_utils.filterFeaturesByType(featuresLayer[1], \
                                                                              currLayer.geometryType())
         # add features with the correct geometry type
         if currLayer.geometryType() == QgsWkbTypes.LineGeometry:
            polygonToLines = []
            # Reduce geometries to lines
            for g in polygonGeoms:
               lines = qad_utils.asPointOrPolyline(g)
               for l in lines:
                  if l.type() == QgsWkbTypes.LineGeometry:
                      polygonToLines.append(l)
            # plugIn, layer, geoms, coordTransform, refresh, check_validity
            if qad_layer.addGeomsToLayer(self.plugIn, currLayer, polygonToLines, None, False, False) == False:
               self.plugIn.destroyEditCommand()
               return
               
            del polygonGeoms[:] # empty the list

         # plugIn, layer, features, coordTransform, refresh, check_validity
         if qad_layer.addFeaturesToLayer(self.plugIn, currLayer, featuresLayer[1], None, False, False) == False:
            self.plugIn.destroyEditCommand()
            return

         if pointGeoms is not None and len(pointGeoms) > 0 and PointTempLayer is None:
            PointTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.PointGeometry)
            self.plugIn.addLayerToLastEditCommand("Feature offseted", PointTempLayer)
         
         if lineGeoms is not None and len(lineGeoms) > 0 and LineTempLayer is None:
            LineTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.LineGeometry)
            self.plugIn.addLayerToLastEditCommand("Feature offseted", LineTempLayer)
            
         if polygonGeoms is not None and len(polygonGeoms) > 0 and PolygonTempLayer is None:
            PolygonTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.PolygonGeometry)
            self.plugIn.addLayerToLastEditCommand("Feature offseted", PolygonTempLayer)
         
         # add discards to QAD temporary layers
         # transform the geometry to that of the temporary layers 
         # plugIn, pointGeoms, lineGeoms, polygonGeoms, coord, refresh
         if qad_layer.addGeometriesToQADTempLayers(self.plugIn, pointGeoms, lineGeoms, polygonGeoms, \
                                                 featuresLayer[0].crs(), False) == False:
            self.plugIn.destroyEditCommand()
            return

      self.plugIn.endEditCommand()

 
   # ============================================================================
   # waitForDistance
   # ============================================================================
   def waitForDistance(self):      
      # set the map tool
      self.getPointMapTool().setMode(Qad_offset_maptool_ModeEnum.ASK_FOR_FIRST_OFFSET_PT)
      self.getPointMapTool().gapType = self.gapType                        

      keyWords = QadMsg.translate("Command_OFFSET", "Through") + "/" + \
                 QadMsg.translate("Command_OFFSET", "Erase")                
      if self.offset < 0:
         default = QadMsg.translate("Command_OFFSET", "Through")
      else:
         default = self.offset
      prompt = QadMsg.translate("Command_OFFSET", "Specify the offset distance or [{0}] <{1}>: ").format(keyWords, str(default))

      englishKeyWords = "Through" + "/" + "Erase"
      keyWords += "_" + englishKeyWords
      # prepares to wait for a point or enter or a keyword or a real number     
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                   default, \
                   keyWords, \
                   QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)      
      self.step = 1      
   
   # ============================================================================
   # waitForObjectSel
   # ============================================================================
   def waitForObjectSel(self):      
      # set the map tool
      self.getPointMapTool().setMode(Qad_offset_maptool_ModeEnum.ASK_FOR_ENTITY_SELECTION)                                      
      self.lastOffSetOnLeftSide = 0
      self.getPointMapTool().lastOffSetOnLeftSide = self.lastOffSetOnLeftSide
      self.lastOffSetOnRightSide = 0
      self.getPointMapTool().lastOffSetOnRightSide = self.lastOffSetOnRightSide
      
      # "Exit" "Undo"
      keyWords = QadMsg.translate("Command_OFFSET", "Exit") + "/" + \
                 QadMsg.translate("Command_OFFSET", "Undo")
      default = QadMsg.translate("Command_OFFSET", "Exit")
      prompt = QadMsg.translate("Command_OFFSET", "Select object to offset or [{0}] <{1}>: ").format(keyWords, default)
      
      englishKeyWords = "Exit" + "/" + "Undo"
      keyWords += "_" + englishKeyWords
      # prepares to wait for a point or enter or a keyword         
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   default, \
                   keyWords, QadInputModeEnum.NONE)      
      self.step = 2      
        
   # ============================================================================
   # waitForSidePt
   # ============================================================================
   def waitForSidePt(self):      
      # set the map tool
      self.getPointMapTool().setMode(Qad_offset_maptool_ModeEnum.OFFSET_KNOWN_ASK_FOR_SIDE_PT)                                

      if self.multi == False:
         keyWords = QadMsg.translate("Command_OFFSET", "Exit") + "/" + \
                    QadMsg.translate("Command_OFFSET", "Multiple") + "/" + \
                    QadMsg.translate("Command_OFFSET", "Undo")
         defaultMsg = QadMsg.translate("Command_OFFSET", "Exit")        
         default = QadMsg.translate("Command_OFFSET", "Exit")
         englishKeyWords = "Exit" + "/" + "Multiple" + "/" + "Undo"
      else:
         keyWords = QadMsg.translate("Command_OFFSET", "Exit") + "/" + \
                    QadMsg.translate("Command_OFFSET", "Undo")
         defaultMsg = QadMsg.translate("Command_OFFSET", "next object")
         default = None
         englishKeyWords = "Exit" + "/" + "Undo"

      if self.OnlySegment == False:
         keyWords = keyWords + "/" + \
                    QadMsg.translate("Command_OFFSET", "Segment")
         englishKeyWords = englishKeyWords + "/" + "Segment"

      prompt = QadMsg.translate("Command_OFFSET", "Specify point on side to offset or [{0}] <{1}>: ").format(keyWords, default)

      keyWords += "_" + englishKeyWords
      # prepares to wait for a point or enter or a keyword         
      # msg, inputType, default, keyWords, null value not allowed
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   default, \
                   keyWords, QadInputModeEnum.NONE)      
      self.step = 3
        
   # ============================================================================
   # waitForPassagePt
   # ============================================================================
   def waitForPassagePt(self):
      # set the map tool
      self.getPointMapTool().setMode(Qad_offset_maptool_ModeEnum.ASK_FOR_PASSAGE_PT)                                

      if self.multi == False:
         keyWords = QadMsg.translate("Command_OFFSET", "Exit") + "/" + \
                    QadMsg.translate("Command_OFFSET", "Multiple") + "/" + \
                    QadMsg.translate("Command_OFFSET", "Undo")
         defaultMsg = QadMsg.translate("Command_OFFSET", "Exit")
         default = QadMsg.translate("Command_OFFSET", "Exit")
         englishKeyWords = "Exit" + "/" + "Multiple" + "/" + "Undo"
      else:
         keyWords = QadMsg.translate("Command_OFFSET", "Exit") + "/" + \
                    QadMsg.translate("Command_OFFSET", "Undo")
         defaultMsg = QadMsg.translate("Command_OFFSET", "next object")
         default = None
         englishKeyWords = "Exit" + "/" + "Undo"

      if self.OnlySegment == False:
         keyWords = keyWords + "/" + \
                    QadMsg.translate("Command_OFFSET", "Segment")
         englishKeyWords = englishKeyWords + "/" + "Segment"

      prompt = QadMsg.translate("Command_OFFSET", "Specify through point or [{0}] <{1}>: ").format(keyWords, defaultMsg)

      keyWords += "_" + englishKeyWords
      # prepares to wait for a point or enter or a keyword         
      # msg, inputType, default, keyWords, null value not allowed
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   default, \
                   keyWords, QadInputModeEnum.NONE)      
      self.step = 4

   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      # the current layer must be editable and of line or polygon type
      currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry])
      if currLayer is None:
         self.showErr(errMsg)
         return True # end command

      # =========================================================================
      # OFFSET DISTANCE REQUEST
      if self.step == 0: # command start
         CurrSettingsMsg = QadMsg.translate("QAD", "\nCurrent settings: ")
         CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_OFFSET", "OFFSETGAPTYPE = ") + str(self.gapType)                        
         if self.gapType == 0:
            CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_OFFSET", " (extends the segments)")
         elif self.gapType == 1:
            CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_OFFSET", " (fillets the segments)")
         elif self.gapType == 2:
            CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_OFFSET", " (chamfers the segments)")
         
         self.showMsg(CurrSettingsMsg)         

         self.waitForDistance()
            
      # =========================================================================
      # RESPONSE TO OFFSET DISTANCE REQUEST (from step = 0)
      elif self.step == 1: # after waiting for a point or a real number, the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during point selection
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated and returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  if self.offset < 0:
                     value = QadMsg.translate("Command_OFFSET", "Through")
                  else:
                     value = self.offset
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # the point comes as parameter of the function
            value = msg
         
         if type(value) == str:
            if value == QadMsg.translate("Command_OFFSET", "Through") or value == "Through":
               self.offset = -1
               self.getPointMapTool().offset = self.offset
               QadVariables.set(QadMsg.translate("Environment variables", "OFFSETDIST"), self.offset)
               QadVariables.save()               
               # prepares to wait for object selection
               self.waitForObjectSel()
            elif value == QadMsg.translate("Command_OFFSET", "Erase") or value == "Erase":
               keyWords = QadMsg.translate("QAD", "Yes") + "/" + \
                          QadMsg.translate("QAD", "No")
              
               if self.eraseEntity == True:
                  default = QadMsg.translate("QAD", "Yes")
               else: 
                  default = QadMsg.translate("QAD", "No")
               prompt = QadMsg.translate("Command_OFFSET", "Erase source object after offsetting ? [{0}] <{1}>: ").format(keyWords, default)
                   
               englishKeyWords = "Yes" + "/" + "No"
               keyWords += "_" + englishKeyWords
               # prepares to wait for enter or a keyword
               # msg, inputType, default, keyWords, no check
               self.waitFor(prompt, \
                            QadInputTypeEnum.KEYWORDS, \
                            default, \
                            keyWords, QadInputModeEnum.NONE)
               self.step = 5
            elif value == QadMsg.translate("Command_OFFSET", "Multiple") or value == "Multiple":
               self.multi = True
               self.waitForBasePt()                         
         elif type(value) == QgsPointXY: # if the first point for distance calculation has been entered
            self.firstPt.set(value.x(), value.y())
            # set the map tool
            self.getPointMapTool().firstPt = self.firstPt           
            self.getPointMapTool().setMode(Qad_offset_maptool_ModeEnum.FIRST_OFFSET_PT_KNOWN_ASK_FOR_SECOND_PT)
            # prepares to wait for a point
            self.waitForPoint(QadMsg.translate("Command_OFFSET", "Specify second point: "))
            self.step = 6
         elif type(value) == float:
            self.offset = value
            self.getPointMapTool().offset = self.offset
            QadVariables.set(QadMsg.translate("Environment variables", "OFFSETDIST"), self.offset)
            QadVariables.save()
            # prepares to wait for object selection
            self.waitForObjectSel()
         
         return False 

      # =========================================================================
      # RESPONSE TO OBJECT SELECTION
      elif self.step == 2:
         entity = None
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated and returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  value = QadMsg.translate("Command_OFFSET", "Exit")
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False
            else:
               entity = self.getPointMapTool().entity
               value = self.getPointMapTool().point
         else: # the point comes as parameter of the function
            value = msg
         
         if type(value) == str:
            if value == QadMsg.translate("Command_OFFSET", "Exit") or value == "Exit":
               self.addToLayer(currLayer)
               return True
            elif value == QadMsg.translate("Command_OFFSET", "Undo") or value == "Undo":
               self.undoGeomsInCache()
               # prepares to wait for object selection
               self.waitForObjectSel()
         elif type(value) == QgsPointXY: # if a point has been selected
            if entity is not None and entity.isInitialized(): # if an entity has been selected
               self.entity.set(entity)
               self.getPointMapTool().layer = self.entity.layer
               
               qadGeom = self.entity.getQadGeom()
               
               # the function returns a list with 
               # (<minimum distance>
               # <closest point>
               # <index of the closest geometry>
               # <index of the closest sub-geometry>
               # <index of the part of the closest sub-geometry>
               # <"left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
               result = getQadGeomClosestPart(qadGeom, value)
               self.atGeom = result[2]
               self.atSubGeom = result[3]
               self.subGeom = getQadGeomAt(qadGeom, self.atGeom, self.atSubGeom)
               self.partNum = result[4]
               
               self.getPointMapTool().subGeom = self.subGeom
               if self.offset < 0: # through point request
                  self.waitForPassagePt()
               else:  # object part request
                  self.waitForSidePt()
            else:
               # prepares to wait for object selection
               self.waitForObjectSel()

         return False

# =========================================================================
# RESPONSE TO POINT REQUEST TO ESTABLISH OFFSET PART (from step = 2)
elif self.step == 3:
   if msgMapTool == True: # the point comes from a graphic selection
      # the following condition occurs if during the selection of a point
      # another plugin has been activated that has deactivated Qad
      # then the command has been reactivated and returns here without the maptool
      # having selected a point            
      if self.getPointMapTool().point is None: # the maptool has been activated without a point
         if self.getPointMapTool().rightButton == True: # if the right mouse button was used
            if self.multi == False: # default = exit                     
               self.addToLayer(currLayer)
               return True # end command
         else:
            self.setMapTool(self.getPointMapTool()) # reactivate the maptool
            return False

      value = self.getPointMapTool().point
   else: # the point comes as parameter of the function
      value = msg

   if value is None: # next object
      # prepares to wait for object selection
      self.waitForObjectSel()
   else:
      if type(value) == str:
         if value == QadMsg.translate("Command_OFFSET", "Exit") or value == "Exit":
            self.addToLayer(currLayer)
            return True # end command
         elif value == QadMsg.translate("Command_OFFSET", "Multiple") or value == "Multiple":
            self.multi = True
            self.waitForSidePt()               
         elif value == QadMsg.translate("Command_OFFSET", "Undo") or value == "Undo":
            self.undoGeomsInCache()               
            # prepares to wait for object selection
            self.waitForObjectSel()
         elif value == QadMsg.translate("Command_OFFSET", "Segment") or value == "Segment":
            self.OnlySegment = True
            if self.subGeom.whatIs() == "POLYLINE":
               self.subGeom = self.subGeom.getLinearObjectAt(self.partNum)
               self.getPointMapTool().subGeom = self.subGeom
            
            self.waitForSidePt()                  
      elif type(value) == QgsPointXY: # if a point has been selected            
         self.addFeatureCache(value) 
         if self.multi == False:
            # prepares to wait for object selection
            self.waitForObjectSel()
         else:
            # object part request
            self.waitForSidePt()

   return False

# =========================================================================
# RESPONSE TO THROUGH POINT REQUEST FOR OFFSET (from step = 2)
elif self.step == 4:
   if msgMapTool == True: # the point comes from a graphic selection
      # the following condition occurs if during the selection of a point
      # another plugin has been activated that has deactivated Qad
      # then the command has been reactivated and returns here without the maptool
      # having selected a point            
      if self.getPointMapTool().point is None: # the maptool has been activated without a point
         if self.getPointMapTool().rightButton == True: # if the right mouse button was used
            if self.multi == False: # default = exit                     
               self.addToLayer(currLayer)
               return True # end command
         else:
            self.setMapTool(self.getPointMapTool()) # reactivate the maptool
            return False

      value = self.getPointMapTool().point
   else: # the point comes as parameter of the function
      value = msg

   if value is None: # next object
      # prepares to wait for object selection
      self.waitForObjectSel()
   else:
      if type(value) == str:
         if value == QadMsg.translate("Command_OFFSET", "Exit") or value == "Exit":
            self.addToLayer(currLayer)
            return True # end command
         elif value == QadMsg.translate("Command_OFFSET", "Multiple") or value == "Multiple":
            self.multi = True
            self.waitForPassagePt()     
         elif value == QadMsg.translate("Command_OFFSET", "Undo") or value == "Undo":
            self.undoGeomsInCache()               
            # prepares to wait for object selection
            self.waitForObjectSel()
         elif value == QadMsg.translate("Command_OFFSET", "Segment") or value == "Segment":
            self.OnlySegment = True
            if self.subGeom.whatIs() == "POLYLINE":
               self.subGeom = self.subGeom.getLinearObjectAt(self.partNum)
               self.getPointMapTool().subGeom = self.subGeom
            
            self.waitForPassagePt()     
      elif type(value) == QgsPointXY: # if a point has been selected            
         self.addFeatureCache(value)       
         if self.multi == False:
            # prepares to wait for object selection
            self.waitForObjectSel()
         else:
            # through point request
            self.waitForPassagePt()

   return False

# =========================================================================
# RESPONSE TO SOURCE OBJECT DELETION REQUEST (from step = 1)
elif self.step == 5: # after waiting for a point or a real number, the command restarts
   if msgMapTool == True: # the point comes from a graphic selection
      # the following condition occurs if during the selection of a point
      # another plugin has been activated that has deactivated Qad
      # then the command has been reactivated and returns here without the maptool
      # having selected a point            
      if self.getPointMapTool().rightButton == True: # if the right mouse button was used
         value = QadMsg.translate("QAD", "No")   
      else:
         self.setMapTool(self.getPointMapTool()) # reactivate the maptool
         return False
   else: # the value comes as parameter of the function
      value = msg

   if type(value) == str:
      if value == QadMsg.translate("QAD", "Yes") or value == "Yes":
         self.eraseEntity = True
         self.waitForDistance()
      elif value == QadMsg.translate("QAD", "No") or value == "No":
         self.eraseEntity = False
         self.waitForDistance()
   
   return False

# =========================================================================
# RESPONSE TO SECOND POINT REQUEST FOR OFFSET LENGTH (from step = 1)
elif self.step == 6: # after waiting for a point or a real number, the command restarts
   if msgMapTool == True: # the point comes from a graphic selection
      # the following condition occurs if during the selection of a point
      # another plugin has been activated that has deactivated Qad
      # then the command has been reactivated and returns here without the maptool
      # having selected a point            
      if self.getPointMapTool().point is None: # the maptool has been activated without a point
         if self.getPointMapTool().rightButton == True: # if the right mouse button was used
            return True # end command
         else:
            self.setMapTool(self.getPointMapTool()) # reactivate the maptool
            return False

      value = self.getPointMapTool().point
   else: # the point comes as parameter of the function
      value = msg

   if type(value) == QgsPointXY: # if a point has been selected
      if value == self.firstPt:
         self.showMsg(QadMsg.translate("QAD", "\nThe value must be positive and not zero."))
         # prepares to wait for a point
         self.waitForPoint(QadMsg.translate("Command_OFFSET", "Specify second point: "))
         return False
            
      self.offset = qad_utils.getDistance(self.firstPt, value)
      self.getPointMapTool().offset = self.offset
      QadVariables.set(QadMsg.translate("Environment variables", "OFFSETDIST"), self.offset)
      QadVariables.save()
      # prepares to wait for object selection
      self.waitForObjectSel()

   return False
