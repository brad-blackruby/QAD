# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Class to manage the map tool in the context of the array command
 
                              -------------------
        begin                : 2025-05-10
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


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointSelectionModeEnum, QadGetPointDrawModeEnum
from ..qad_highlight import QadHighlight
from ..qad_dim import QadDimStyles, appendDimEntityIfNotExisting
from ..qad_entity import QadCacheEntitySetIterator, QadEntityTypeEnum
from .. import qad_array_fun


# ===============================================================================
# Qad_array_maptool_ModeEnum class.
# ===============================================================================
class Qad_array_maptool_ModeEnum():
   # nothing is requested
   NONE = 0
   # base point is requested
   ASK_FOR_BASE_PT = 1
   # first point for the distance between columns is requested
   ASK_FOR_COLUMN_SPACE_FIRST_PT = 2
   # first point for the cell dimension is requested
   ASK_FOR_1PT_CELL = 3
   # second point for the cell dimension is requested
   ASK_FOR_2PT_CELL = 4
   # first point for the distance between rows is requested
   ASK_FOR_ROW_SPACE_FIRST_PT = 5


# ===============================================================================
# Qad_array_maptool class
# ===============================================================================
class Qad_array_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)
                        
      self.cacheEntitySet = None
      self.basePt = None
      self.arrayType = None
      self.distanceBetweenRows = None
      self.distanceBetweenCols = None
      self.itemsRotation = None

      # rectangular array
      self.rectangleAngle = None
      self.rectangleCols = None
      self.rectangleRows = None
      self.firstPt = None

      # path array
      self.pathTangentDirection = None
      self.pathRows = None
      self.pathItemsNumber = None
      self.pathPolyline = None

      # polar array
      self.centerPt = None
      self.polarItemsNumber = None
      self.polarAngleBetween = None
      self.polarRows = None

      self.__highlight = QadHighlight(self.canvas)

   def hidePointMapToolMarkers(self):
      QadGetPoint.hidePointMapToolMarkers(self)
      self.__highlight.hide()

   def showPointMapToolMarkers(self):
      QadGetPoint.showPointMapToolMarkers(self)
      self.__highlight.show()
                             
   def clear(self):
      QadGetPoint.clear(self)
      self.__highlight.reset()
      self.mode = None    


   # ============================================================================
   # doRectangleArray
   # ============================================================================
   def doRectangleArray(self):
      self.__highlight.reset()

      dimElaboratedList = [] # list of already processed dimension styles
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom().copy() # initializing qad info
         # verify if the entity belongs to a dimension style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # dimension already processed
               continue
            entity = dimEntity

         if qad_array_fun.arrayRectangleEntity(self.plugIn, entity, self.basePt, self.rectangleRows, self.rectangleCols, \
                                               self.distanceBetweenRows, self.distanceBetweenCols, self.rectangleAngle, self.itemsRotation,
                                               False, self.__highlight) == False:
            return


   # ============================================================================
   # doPathArray
   # ============================================================================
   def doPathArray(self):
      self.__highlight.reset()

      dimElaboratedList = [] # list of already processed dimension styles
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom().copy() # initializing qad info
         # verify if the entity belongs to a dimension style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # dimension already processed
               continue
            entity = dimEntity

         if qad_array_fun.arrayPathEntity(self.plugIn, entity, self.basePt, self.pathRows, self.pathItemsNumber, \
                                          self.distanceBetweenRows, self.distanceBetweenCols, self.pathTangentDirection, self.itemsRotation, \
                                          self.pathPolyline, self.distanceFromStartPt, \
                                          False, self.__highlight) == False:
            return


   # ============================================================================
   # doPolarArray
   # ============================================================================
   def doPolarArray(self):
      self.__highlight.reset()

      dimElaboratedList = [] # list of already processed dimension styles
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom().copy() # initializing qad info
         # verify if the entity belongs to a dimension style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # dimension already processed
               continue
            entity = dimEntity

         if qad_array_fun.arrayPolarEntity(self.plugIn, entity, self.basePt, self.centerPt, self.polarItemsNumber, \
                                           self.polarAngleBetween, self.polarRows, self.distanceBetweenRows, self.itemsRotation, \
                                           False, self.__highlight) == False:
            return


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
      
#       # when base point is known, the second point is requested
#       if self.mode == Qad_array_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_COPY_PT:
#          self.setCopiedGeometries(self.tmpPoint)                           
         
    
   def activate(self):
      QadGetPoint.activate(self)            
      self.__highlight.show()          

   def deactivate(self):
      try: # necessary because if QGIS is closed this event is triggered despite the maptool object is no longer available!
         QadGetPoint.deactivate(self)
         self.__highlight.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode
      # nothing is requested
      if self.mode == Qad_array_maptool_ModeEnum.NONE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.NONE)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # base point is requested
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_BASE_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # first point for the distance between columns is requested
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_COLUMN_SPACE_FIRST_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # first point for the cell dimension is requested
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_1PT_CELL:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # second point for the cell dimension is requested
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_2PT_CELL:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_RECTANGLE)
         self.setStartPoint(self.firstPt)
      # first point for the distance between rows is requested
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_ROW_SPACE_FIRST_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)


      # second point for the distance between columns is requested
#       elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_COLUMN_SPACE_SECOND_PT:
#          self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
#          self.setStartPoint(self.firstPt)
