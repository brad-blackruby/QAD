# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Class for managing the map tool within the copy command
 
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


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_highlight import QadHighlight
from ..qad_dim import QadDimEntity, QadDimStyles, appendDimEntityIfNotExisting
from ..qad_entity import QadCacheEntitySetIterator, QadEntityTypeEnum
from ..qad_multi_geom import fromQadGeomToQgsGeom


# ===============================================================================
# Qad_copy_maptool_ModeEnum class.
# ===============================================================================
class Qad_copy_maptool_ModeEnum():
   # nothing known, request base point
   NONE_KNOWN_ASK_FOR_BASE_PT = 1     
   # base point known, request second point for copy
   BASE_PT_KNOWN_ASK_FOR_COPY_PT = 2     


# ===============================================================================
# Qad_copy_maptool class
# ===============================================================================
class Qad_copy_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)
                        
      self.basePt = None
      self.cacheEntitySet = None
      self.seriesLen = 0
      self.adjust = False
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
   # move
   # ============================================================================
   def move(self, entity, offsetX, offsetY):
      # check if the entity belongs to a dimension style
      if entity.whatIs() == "ENTITY":
         # move the entity geometry
         qadGeom = entity.getQadGeom().copy() # copy it
         qadGeom.move(offsetX, offsetY)
         self.__highlight.addGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer), entity.layer)      
      elif entity.whatIs() == "DIMENTITY":
         newDimEntity = QadDimEntity(entity) # copy it
         # move the dimension
         newDimEntity.move(offsetX, offsetY)
         self.__highlight.addGeometry(newDimEntity.textualFeature.geometry(), newDimEntity.getTextualLayer())
         self.__highlight.addGeometries(newDimEntity.getLinearGeometryCollection(), newDimEntity.getLinearLayer())
         self.__highlight.addGeometries(newDimEntity.getSymbolGeometryCollection(), newDimEntity.getSymbolLayer())
   
   
   def setCopiedGeometries(self, newPt):
      self.__highlight.reset()            

      offsetX = newPt.x() - self.basePt.x()
      offsetY = newPt.y() - self.basePt.y()
      
      dimElaboratedList = [] # list of dimensions already processed
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom() # initialize qad info
         # check if the entity belongs to a dimension style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # dimension already processed
               continue
            entity = dimEntity
         
         if self.seriesLen > 0: # need to create a series
            if self.adjust == True:
               offsetXToApply = offsetX / (self.seriesLen - 1)
               offsetYToApply = offsetY / (self.seriesLen - 1)
            else:
               offsetXToApply = offsetX
               offsetYToApply = offsetY
               
            deltaX = offsetXToApply
            deltaY = offsetYToApply
               
            for i in range(1, self.seriesLen, 1):
               self.move(entity, deltaX, deltaY)
               deltaX = deltaX + offsetXToApply
               deltaY = deltaY + offsetYToApply
                  
         else:
            self.move(entity, offsetX, offsetY)

      
   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
      
      # base point known, request second point
      if self.mode == Qad_copy_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_COPY_PT:
         self.setCopiedGeometries(self.tmpPoint)                           
         
    
   def activate(self):
      QadGetPoint.activate(self)            
      self.__highlight.show()          

   def deactivate(self):
      try: # necessary because this event is triggered when QGIS is closed even if maptool object no longer exists!
         QadGetPoint.deactivate(self)
         self.__highlight.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode
      # nothing known, request base point
      if self.mode == Qad_copy_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # base point known, request second point for copy
      elif self.mode == Qad_copy_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_COPY_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.basePt)
