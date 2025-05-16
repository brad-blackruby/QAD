# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Class to manage the map tool for the fillet command
 
                              -------------------
        last updated         : 2025-05-15
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


from qgis.core import QgsWkbTypes, QgsGeometry


from .. import qad_utils
from ..qad_snapper import QadSnapTypeEnum
from ..qad_getpoint import QadGetPoint, QadGetPointSelectionModeEnum, QadGetPointDrawModeEnum
from ..qad_rubberband import QadRubberBand
from ..qad_dim import QadDimStyles
from ..qad_fillet_fun import fillet2QadGeometries, filletAllPartsQadPolyline, filletQadPolyline
from ..qad_multi_geom import fromQadGeomToQgsGeom, getQadGeomAt, setQadGeomAt
from ..qad_geom_relations import getQadGeomClosestPart


# ===============================================================================
# Qad_fillet_maptool_ModeEnum class.
# ===============================================================================
class Qad_fillet_maptool_ModeEnum():
   # requesting selection of the first object
   ASK_FOR_FIRST_LINESTRING = 1     
   # requesting selection of the second object
   ASK_FOR_SECOND_LINESTRING = 2    
   # nothing is requested
   NONE = 3
   # requesting selection of the polyline
   ASK_FOR_POLYLINE = 4     


# ===============================================================================
# Qad_fillet_maptool class
# ===============================================================================
class Qad_fillet_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.filletMode = 1 # fillet mode; 1=Trim-extend, 2=No trim-extend
      self.radius = 0.0
      
      self.layer = None
      self.entity1 = None
      self.atGeom1 = None
      self.atSubGeom1 = None
      self.partAt1 = None
      self.pointAt1 = None

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

   def setEntityInfo(self, entity, atGeom, atSubGeom, partAt, pointAt):
      """
      Sets self.entity1, self.atGeom1, self.atSubGeom1, self.partAt1, self.pointAt1
      """
      self.entity1 = entity
      self.atGeom1 = atGeom
      self.atSubGeom1 = atSubGeom
      self.partAt1 = partAt
      self.pointAt1 = pointAt


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
      
      self.__rubberBand.reset()
      newQadGeom = None
       
      # requesting selection of the second object
      if self.mode == Qad_fillet_maptool_ModeEnum.ASK_FOR_SECOND_LINESTRING:
         if self.tmpEntity.isInitialized():
            tmpQadGeom = self.tmpEntity.getQadGeom()
            """
            the function returns a list with:
            (<minimum distance>
             <closest point>
             <index of the closest geometry>
             <index of the closest sub-geometry>
             <index of the part of the closest sub-geometry>
             <"on left of" if the point is to the left of the part with the following values:
             -   < 0 = left (for line, arc or ellipse arc) or inside (for circles, ellipses)
             -   > 0 = right (for line, arc or ellipse arc) or outside (for circles, ellipses)
             )
            """
            res = getQadGeomClosestPart(tmpQadGeom, self.tmpPoint)
            tmpPointAt = res[1]
            tmpAtGeom = res[2]
            tmpAtSubGeom = res[3]
            tmpPartAt = res[4]

            # same entity and same part
            if self.entity1.layer.id() == self.tmpEntity.layer.id() and \
               self.entity1.featureId == self.tmpEntity.featureId and \
               self.atGeom1 == tmpAtGeom and self.atSubGeom1 == tmpAtSubGeom:
               # if also same part
               if self.partAt1 == tmpPartAt: return
               subQadGeom = getQadGeomAt(self.entity1.getQadGeom(),self.atGeom1, self.atSubGeom1)
               if subQadGeom.whatIs() != "POLYLINE": return
               
               if self.tmpShiftKey == True: # shift key pressed during mouse movement
                  # filletMode = 1 # fillet mode; 1=Trim-extend
                  # radius = 0
                  newQadGeom = filletQadPolyline(subQadGeom, self.partAt1, self.pointAt1, tmpPartAt, tmpPointAt, \
                                                 1, 0)
               else:               
                  newQadGeom = filletQadPolyline(subQadGeom, self.partAt1, self.pointAt1, tmpPartAt, tmpPointAt, \
                                                 self.filletMode, self.radius)
      
            # different geometries      
            else:
               if self.tmpShiftKey == True: # shift key pressed during mouse movement
                  # filletMode = 1 # fillet mode; 1=Trim-extend
                  # radius = 0
                  res = fillet2QadGeometries(self.entity1.getQadGeom(), self.atGeom1, self.atSubGeom1, self.partAt1, self.pointAt1, \
                                             tmpQadGeom, tmpAtGeom, tmpAtSubGeom, tmpPartAt, tmpPointAt, \
                                             1, 0)
               else:               
                  res = fillet2QadGeometries(self.entity1.getQadGeom(), self.atGeom1, self.atSubGeom1, self.partAt1, self.pointAt1, \
                                             tmpQadGeom, tmpAtGeom, tmpAtSubGeom, tmpPartAt, tmpPointAt, \
                                             self.filletMode, self.radius)
               if res is None: # fillet not possible
                  return
               
               newQadGeom = res[0]
                        
      # requesting selection of the polyline
      elif self.mode == Qad_fillet_maptool_ModeEnum.ASK_FOR_POLYLINE:
         if self.tmpEntity.isInitialized():
            tmpQadGeom = self.tmpEntity.getQadGeom()
            """
            the function returns a list with:
            (<minimum distance>
             <closest point>
             <index of the closest geometry>
             <index of the closest sub-geometry>
             <index of the part of the closest sub-geometry>
             <"on left of" if the point is to the left of the part with the following values:
             -   < 0 = left (for line, arc or ellipse arc) or inside (for circles, ellipses)
             -   > 0 = right (for line, arc or ellipse arc) or outside (for circles, ellipses)
             )
            """
            res = getQadGeomClosestPart(tmpQadGeom, self.tmpPoint)
            tmpAtGeom = res[2]
            tmpAtSubGeom = res[3]
            tmpSubQadGeom = getQadGeomAt(tmpQadGeom, tmpAtGeom, tmpAtSubGeom).copy()
            if filletAllPartsQadPolyline(tmpSubQadGeom, self.radius):
               newQadGeom = setQadGeomAt(tmpQadGeom, tmpSubQadGeom, tmpAtGeom, tmpAtSubGeom)

      if newQadGeom is not None:
         self.__rubberBand.addGeometry(fromQadGeomToQgsGeom(newQadGeom, self.tmpEntity.layer), self.tmpEntity.layer)
      
    
   def activate(self):
      QadGetPoint.activate(self)            
      self.__rubberBand.show()          

   def deactivate(self):
      try: # necessary because if QGIS is closed this event is triggered despite the maptool object no longer exists!
         QadGetPoint.deactivate(self)
         self.__rubberBand.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode

      # requesting selection of the first object
      # requesting selection of the second object
      if self.mode == Qad_fillet_maptool_ModeEnum.ASK_FOR_FIRST_LINESTRING or \
         self.mode == Qad_fillet_maptool_ModeEnum.ASK_FOR_SECOND_LINESTRING:
         
         if self.mode == Qad_fillet_maptool_ModeEnum.ASK_FOR_FIRST_LINESTRING:
            self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
         else:
            self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC)

         # only editable linear layers that don't belong to dimensions
         layerList = []
         for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All visible vector layers
            if layer.geometryType() == QgsWkbTypes.LineGeometry and layer.isEditable():
               if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                  layerList.append(layer)
         
         self.layersToCheck = layerList
         self.setSnapType(QadSnapTypeEnum.DISABLE)
      # nothing is requested
      elif self.mode == Qad_fillet_maptool_ModeEnum.NONE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)   
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # requesting selection of the polyline
      elif self.mode == Qad_fillet_maptool_ModeEnum.ASK_FOR_POLYLINE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC)

         # only editable linear or polygon layers that don't belong to dimensions
         layerList = []
         for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All visible vector layers
            if (layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry) and \
               layer.isEditable():
               if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                  layerList.append(layer)
         
         self.layersToCheck = layerList
         self.setSnapType(QadSnapTypeEnum.DISABLE)
