# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Class to manage the map tool for the lengthen command
 
                              -------------------
        last updat           : 2025-05-17
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


from qgis.core import QgsWkbTypes


import math


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointSelectionModeEnum
from ..qad_rubberband import QadRubberBand
from ..qad_dim import QadDimStyles
from ..qad_geom_relations import getQadGeomClosestVertex
from ..qad_multi_geom import getQadGeomAt, fromQadGeomToQgsGeom
from ..qad_snapper import QadSnapTypeEnum


# ########## BEGIN SEGMENT 1 ##########
# ===============================================================================
# Qad_lengthen_maptool_ModeEnum class.
# ===============================================================================
class Qad_lengthen_maptool_ModeEnum():
   # requesting the selection of the object to measure
   ASK_FOR_OBJ_TO_MISURE = 1
   # requesting the delta
   ASK_FOR_DELTA = 2
   # nothing is requested
   NONE = 3
   # requesting the selection of the object to lengthen
   ASK_FOR_OBJ_TO_LENGTHEN = 4
   # requesting the percentage
   ASK_FOR_PERCENT = 5
   # requesting the total
   ASK_FOR_TOTAL = 6
   # requesting the new endpoint in dynamic mode
   ASK_FOR_DYNAMIC_POINT = 7

# ===============================================================================
# Qad_lengthen_maptool class
# ===============================================================================
class Qad_lengthen_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.OpMode = None # "DElta" or "Percent" or "Total" or "DYnamic"
      self.OpType = None # "length" or "Angle"
      self.value = None
      self.tmpLinearObject = None

      self.__rubberBand = QadRubberBand(self.canvas)


   def hidePointMapToolMarkers(self):
      QadGetPoint.hidePointMapToolMarkers(self)
      self.__rubberBand.hide()

   def showPointMapToolMarkers(self):
      QadGetPoint.showPointMapToolMarkers(self)
      self.__rubberBand.show()
                             
   def clear(self):
      QadGetPoint.clear(self)
      self.__rubberBand.reset()
      self.mode = None

   def setInfo(self, entity, point):
      # sets: self.layer, self.tmpLinearObject and self.move_startPt

      if self.tmpLinearObject is not None:
         del self.tmpLinearObject
         self.tmpLinearObject = None
      
      if entity.isInitialized() == False:
         return False
         
      self.layer = entity.layer
      qadGeom = entity.getQadGeom()

      # the function returns a list with
      # (<minimum distance>
      # <closest vertex point>
      # <index of the closest geometry>
      # <index of the closest sub-geometry>
      # <index of the part of the closest sub-geometry>
      # <index of the closest vertex>
      result = getQadGeomClosestVertex(qadGeom, point)
      self.atGeom = result[2]
      self.tmpLinearObject = getQadGeomAt(qadGeom, self.atGeom, 0).copy()
                  
      if qad_utils.getDistance(self.tmpLinearObject.getStartPt(), point) <= \
         qad_utils.getDistance(self.tmpLinearObject.getEndPt(), point):
         # lengthening from start point
         self.move_startPt = True
      else:
         # lengthening from end point
         self.move_startPt = False

      return True

  def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
      
      self.__rubberBand.reset()
      res = False
       
      # requesting the selection of the object to lengthen
      if self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_OBJ_TO_LENGTHEN:
         if self.tmpEntity.isInitialized():
            if self.setInfo(self.tmpEntity, self.tmpPoint) == False:
               return

            newTmpLinearObject = self.tmpLinearObject.copy()
            if self.OpMode == "DElta":
               if self.OpType == "length":
                  res = newTmpLinearObject.lengthen_delta(self.move_startPt, self.value)
               elif self.OpType == "Angle":
                  res = newTmpLinearObject.lengthen_deltaAngle(self.move_startPt, self.value)
            elif self.OpMode == "Percent":
               value = newTmpLinearObject.length() * self.value / 100
               value = value - newTmpLinearObject.length()
               res = newTmpLinearObject.lengthen_delta(self.move_startPt, value)
            elif self.OpMode == "Total":
               if self.OpType == "length":
                  value = self.value - self.tmpLinearObject.length()
                  res = newTmpLinearObject.lengthen_delta(self.move_startPt, value)
               elif self.OpType == "Angle":
                  if newTmpLinearObject.whatIs() == "ARC":
                        value = self.value - linearObject.totalAngle()
                        res = newTmpLinearObject.lengthen_deltaAngle(self.move_startPt, value)
               
      # requesting a point for the new endpoint
      elif self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_DYNAMIC_POINT:
         newTmpLinearObject = self.tmpLinearObject.copy()
         
         if newTmpLinearObject.whatIs() == "POLYLINE":
            if self.move_startPt:
               linearObject = newTmpLinearObject.getLinearObjectAt(0)
            else:
               linearObject = newTmpLinearObject.getLinearObjectAt(-1)
         else:
            linearObject = newTmpLinearObject
            
         gType = linearObject.whatIs()
         if gType == "LINE":
            newPt = qad_utils.getPerpendicularPointOnInfinityLine(linearObject.getStartPt(), linearObject.getEndPt(), self.tmpPoint)
            ang = linearObject.getTanDirectionOnStartPt()
         elif gType == "ARC":
            newPt = qad_utils.getPolarPointByPtAngle(linearObject.center, \
                                                     qad_utils.getAngleBy2Pts(linearObject.center, self.tmpPoint), \
                                                     linearObject.radius)                  
         elif gType == "ELLIPSE_ARC":
            pass

         if self.move_startPt:
            linearObject.setStartPt(newPt)
         else:
            linearObject.setEndPt(newPt)

         if gType == "LINE" and newTmpLinearObject.whatIs() == "POLYLINE" and \
            qad_utils.TanDirectionNear(ang, linearObject.getTanDirectionOnStartPt()) == False:
            res = False
         else:
            res = True
      
      if res == False: # impossible lengthening
         return
      geom = fromQadGeomToQgsGeom(newTmpLinearObject, self.layer)
      self.__rubberBand.addGeometry(geom, self.layer)
      
    
   def activate(self):
      QadGetPoint.activate(self)            
      self.__rubberBand.show()          

   def deactivate(self):
      try: # necessary because if QGIS is closed this event fires despite the maptool object no longer existing!
         QadGetPoint.deactivate(self)
         self.__rubberBand.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode

      # requesting the selection of the object to measure
      if self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_OBJ_TO_MISURE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)

         # only linear layers that don't belong to dimensions or polygon type
         layerList = []
         for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All visible vector layers
            if layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry:
               if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                  layerList.append(layer)
         
         self.layersToCheck = layerList
         self.onlyEditableLayers = False
         self.setSnapType(QadSnapTypeEnum.DISABLE)
      # requesting the delta
      elif self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_DELTA:
         self.OpMode = "DElta"
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
      # nothing is requested
      elif self.mode == Qad_lengthen_maptool_ModeEnum.NONE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)   
      # requesting the selection of the object to lengthen
      elif self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_OBJ_TO_LENGTHEN:
         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC)

         # only editable linear layers that don't belong to dimensions
         layerList = []
         for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All visible vector layers
            if layer.geometryType() == QgsWkbTypes.LineGeometry and layer.isEditable():
               if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                  layerList.append(layer)
         
         self.layersToCheck = layerList
         self.onlyEditableLayers = True
         self.setSnapType(QadSnapTypeEnum.DISABLE)
      # requesting the percentage
      elif self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_PERCENT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION) 
         self.OpMode = "Percent"
      # requesting the total
      elif self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_TOTAL:
         self.OpMode = "Total"
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
      # requesting the new endpoint in dynamic mode
      elif self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_DYNAMIC_POINT:
         self.OpMode = "DYnamic"
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
