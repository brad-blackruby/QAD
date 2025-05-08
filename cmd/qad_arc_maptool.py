# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Class to manage the map tool for requesting a point in the context of the arc command
 
                              -------------------
        begin                : 2025-05-07
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


from qgis.core import QgsCoordinateTransform, QgsGeometry, QgsProject, QgsWkbTypes


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_line import QadLine
from ..qad_polyline import QadPolyline
from ..qad_arc import QadArc
from ..qad_rubberband import QadRubberBand
from ..qad_highlight import QadHighlight
from ..qad_entity import QadEntity


# ===============================================================================
# Qad_arc_maptool_ModeEnum class.
# ===============================================================================
class Qad_arc_maptool_ModeEnum():
   # nothing known, request the first point
   NONE_KNOWN_ASK_FOR_START_PT = 1     
   # start point of the arc known, request the second point
   START_PT_KNOWN_ASK_FOR_SECOND_PT = 2     
   # start point and second point of the arc known, request the end point
   START_SECOND_PT_KNOWN_ASK_FOR_END_PT = 3     
   # start point of the arc known, request the center
   START_PT_KNOWN_ASK_FOR_CENTER_PT = 4     
   # start point and center of the arc known, request the end point
   START_CENTER_PT_KNOWN_ASK_FOR_END_PT = 5     
   # start point and center of the arc known, request the inscribed angle
   START_CENTER_PT_KNOWN_ASK_FOR_ANGLE = 6     
   # start point and center of the arc known, request the chord length
   START_CENTER_PT_KNOWN_ASK_FOR_CHORD = 7
   # start point of the arc known, request the end point
   START_PT_KNOWN_ASK_FOR_END_PT = 8     
   # start point and end point of the arc known, request the center
   START_END_PT_KNOWN_ASK_FOR_CENTER = 9
   # start point and end point of the arc known, request the inscribed angle
   START_END_PT_KNOWN_ASK_FOR_ANGLE = 10
   # start point and end point of the arc known, request the direction of the tangent at the start point
   START_END_PT_KNOWN_ASK_FOR_TAN = 11
   # start point and end point of the arc known, request the radius
   START_END_PT_KNOWN_ASK_FOR_RADIUS = 12        
   # nothing known, request the center
   NONE_KNOWN_ASK_FOR_CENTER_PT = 13
   # center of the arc known, request the start point
   CENTER_PT_KNOWN_ASK_FOR_START_PT = 14      
   # start point and tangent at start point known, request the end point
   START_PT_TAN_KNOWN_ASK_FOR_END_PT = 15
   # start point of the arc known, request the inscribed angle
   START_PT_KNOWN_ASK_FOR_ANGLE = 16     
   # start point and inscribed angle of the arc known, request the end point
   START_PT_ANGLE_KNOWN_ASK_FOR_END_PT = 17     
   # start point and inscribed angle of the arc known, request the center
   START_PT_ANGLE_KNOWN_ASK_FOR_CENTER_PT = 18
   # start point and inscribed angle of the arc known, request the radius
   START_PT_ANGLE_KNOWN_ASK_FOR_RADIUS = 19
   # start point and inscribed angle of the arc known, request the second point to measure the radius
   START_PT_ANGLE_KNOWN_ASK_FOR_SECONDPTRADIUS = 20
   # start point, inscribed angle and radius of the arc known, request the chord direction
   START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION = 21
   # start point and radius of the arc known, request the end point
   START_PT_RADIUS_KNOWN_ASK_FOR_END_PT = 22        


# ===============================================================================
# Qad_arc_maptool class
# ===============================================================================
class Qad_arc_maptool(QadGetPoint):
    
   def __init__(self, plugIn, asToolForMPolygon = False):
      QadGetPoint.__init__(self, plugIn)
      self.arcStartPt = None
      self.arcSecondPt = None
      self.arcEndPt = None
      self.arcCenterPt = None
      self.arcTanOnStartPt = None
      self.arcAngle = None
      self.arcStartPtForRadius = None
      self.arcRadius = None
      self.__rubberBand = QadRubberBand(self.canvas)
 
      self.asToolForMPolygon = asToolForMPolygon # if True it means that it's used to draw a polygon
      if self.asToolForMPolygon:
         self.__polygonRubberBand = QadRubberBand(self.plugIn.canvas, True)
         self.endVertex = None # points to the initial and final vertex of the polygon in QadPLINECommandClass
      else:
         self.__polygonRubberBand = None
         
      self.layer = None


   def hidePointMapToolMarkers(self):
      QadGetPoint.hidePointMapToolMarkers(self)
      self.__rubberBand.hide()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.hide()
 
   def showPointMapToolMarkers(self):
      QadGetPoint.showPointMapToolMarkers(self)
      self.__rubberBand.show()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.show()
                                   
   def clear(self):
      QadGetPoint.clear(self)
      self.__rubberBand.reset()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.reset()
      self.mode = None

      
   # ============================================================================
   # removeItems
   # ============================================================================
   def removeItems(self):
      QadGetPoint.removeItems(self)
      # first detach from canvas otherwise it won't be removed because it's used by canvas
      if self.__rubberBand is not None:
         del self.__rubberBand
         self.__rubberBand = None

      if self.__polygonRubberBand is not None:
         del self.__polygonRubberBand
         self.__polygonRubberBand = None

      
   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
      
      self.__rubberBand.reset()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.reset()
      
      result = False
      arc = QadArc()    
       
      # first and second point of the arc known, request the third point
      if self.mode == Qad_arc_maptool_ModeEnum.START_SECOND_PT_KNOWN_ASK_FOR_END_PT:
         result = arc.fromStartSecondEndPts(self.arcStartPt, self.arcSecondPt, self.tmpPoint)
      # first point and center of the arc known, request the end point
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_END_PT:
         result = arc.fromStartCenterEndPts(self.arcStartPt, self.arcCenterPt, self.tmpPoint)
         if result == True and self.tmpCtrlKey: # reverse initial-final angle
            arc.inverseAngles()
      # first point and center of the arc known, request the inscribed angle
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_ANGLE:
         angle = qad_utils.getAngleBy2Pts(self.arcCenterPt, self.tmpPoint)
         result = arc.fromStartCenterPtsAngle(self.arcStartPt, self.arcCenterPt, angle)
         if result == True and self.tmpCtrlKey: # reverse initial-final angle
            arc.inverseAngles()
      # first point and center of the arc known, request the chord length
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_CHORD:     
         chord = qad_utils.getDistance(self.arcStartPt, self.tmpPoint)
         result = arc.fromStartCenterPtsChord(self.arcStartPt, self.arcCenterPt, chord)
         if result == True and self.tmpCtrlKey: # reverse initial-final angle
            arc.inverseAngles()
      # start point and end point of the arc known, request the center
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_CENTER:     
         result = arc.fromStartCenterEndPts(self.arcStartPt, self.tmpPoint, self.arcEndPt)
         if result == True and self.tmpCtrlKey: # reverse initial-final angle
            arc.inverseAngles()
      # start point and end point of the arc known, request the inscribed angle
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_ANGLE:     
         angle = qad_utils.getAngleBy2Pts(self.arcStartPt, self.tmpPoint)
         result = arc.fromStartEndPtsAngle(self.arcStartPt, self.arcEndPt, angle)
         if result == True and self.tmpCtrlKey: # reverse initial-final angle
            arc.inverseAngles()
      # start point and end point of the arc known, request the tangent direction
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_TAN:     
         tan = qad_utils.getAngleBy2Pts(self.arcStartPt, self.tmpPoint)
         result = arc.fromStartEndPtsTan(self.arcStartPt, self.arcEndPt, tan)
         if result == True and self.tmpCtrlKey: # reverse initial-final angle
            arc.inverseAngles()
      # start point and end point of the arc known, request the radius
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_RADIUS:     
         radius = qad_utils.getDistance(self.arcEndPt, self.tmpPoint)
         result = arc.fromStartEndPtsRadius(self.arcStartPt, self.arcEndPt, radius)
         if result == True and self.tmpCtrlKey: # reverse initial-final angle
            arc.inverseAngles()
      # start point and tangent at start point known, request the end point
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_TAN_KNOWN_ASK_FOR_END_PT:     
         result = arc.fromStartEndPtsTan(self.arcStartPt, self.tmpPoint, self.arcTanOnStartPt)         
         if result == True and self.tmpCtrlKey: # reverse initial-final angle
            arc.inverseAngles()
      # start point and inscribed angle of the arc known, request the end point
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_END_PT:     
         result = arc.fromStartEndPtsAngle(self.arcStartPt, self.tmpPoint, self.arcAngle)
         if result == True and self.tmpCtrlKey: # reverse initial-final angle
            arc.inverseAngles()
      # start point and inscribed angle of the arc known, request the center
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_CENTER_PT:     
         result = arc.fromStartCenterPtsAngle(self.arcStartPt, self.tmpPoint, self.arcAngle)
         if result == True and self.tmpCtrlKey: # reverse initial-final angle
            arc.inverseAngles()
      # start point, inscribed angle and radius of the arc known, request the chord direction
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION:     
         chordDirection = qad_utils.getAngleBy2Pts(self.arcStartPt, self.tmpPoint)
         result = arc.fromStartPtAngleRadiusChordDirection(self.arcStartPt, self.arcAngle, \
                                                           self.arcRadius, chordDirection)
         if result == True and self.tmpCtrlKey: # reverse initial-final angle
            arc.inverseAngles()
      # start point and radius of the arc known, request the end point
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_RADIUS_KNOWN_ASK_FOR_END_PT:     
         result = arc.fromStartEndPtsRadius(self.arcStartPt, self.tmpPoint, self.arcRadius)
         if result == True and self.tmpCtrlKey: # reverse initial-final angle
            arc.inverseAngles()
      
      if result == True:
         if self.__polygonRubberBand is None: # means that it's NOT used to draw a polygon
            if self.layer is not None:
               g = arc.asGeom(self.layer.wkbType())
            else:
               g = arc.asGeom(QgsWkbTypes.CompoundCurve) # it's a virtual arc that won't be saved by this command

            if g is not None: self.__rubberBand.setGeometry(g) 
         else: # means it's used to draw a polygon
            pline = QadPolyline()
            pline.append(arc)
            
            if self.endVertex is not None:
               line = QadLine()
               line.set(arc.getEndPt(), self.endVertex)
               pline.append(line)
               line = QadLine()
               line.set(self.endVertex, arc.getStartPt())
               pline.append(line)
            else:
               line = QadLine()
               line.set(arc.getEndPt(), arc.getStartPt())
               pline.append(line)
               
            if self.layer is not None:
               g = pline.asGeom(self.layer.wkbType())
            else:
               g = pline.asGeom(QgsWkbTypes.CurvePolygon) # it's a virtual arc that won't be saved by this command            
            
            self.__polygonRubberBand.setGeometry(g)
                                 
#          points = arc.asPolyline()
#       
#          if points is not None:
#             self.__rubberBand.setLine(points)
#             if self.__polygonRubberBand is not None: # means it's used to draw a polygon
#                if self.endVertex is not None:
#                   points.insert(0, self.endVertex)
#                   self.__polygonRubberBand.setPolygon(points)

    
   def activate(self):
      QadGetPoint.activate(self)            
      self.__rubberBand.show()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.show()
      
   def deactivate(self):
      try: # necessary because if QGIS is closed this event starts despite the maptool object no longer exists!
         QadGetPoint.deactivate(self)
         self.__rubberBand.hide()
         if self.__polygonRubberBand is not None: self.__polygonRubberBand.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode
      # nothing known, request the first point
      if self.mode == Qad_arc_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_START_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # first point of the arc known, request the second point
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_SECOND_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # first and second point of the arc known, request the third point
      elif self.mode == Qad_arc_maptool_ModeEnum.START_SECOND_PT_KNOWN_ASK_FOR_END_PT:         
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcSecondPt)
      # first point of the arc known, request the center         
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_CENTER_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # first point and center of the arc known, request the end point
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_END_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcCenterPt)
      # first point and center of the arc known, request the inscribed angle
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_ANGLE:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcCenterPt)
      # first point and center of the arc known, request the chord length
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_CHORD:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # start point of the arc known, request the end point
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_END_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # start point and end point of the arc known, request the center
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_CENTER:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # start point and end point of the arc known, request the inscribed angle
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_ANGLE:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # start point and end point of the arc known, request the tangent direction
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_TAN:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # start point and end point of the arc known, request the radius
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_RADIUS:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)                  
         self.setStartPoint(self.arcEndPt)
      # nothing known, request the center
      elif self.mode == Qad_arc_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # center of the arc known, request the start point
      elif self.mode == Qad_arc_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_START_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)                  
         self.setStartPoint(self.arcCenterPt)
      # start point and tangent at start point known, request the end point
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_TAN_KNOWN_ASK_FOR_END_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)                  
         self.setStartPoint(self.arcStartPt)
      # start point of the arc known, request the inscribed angle
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_ANGLE:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # start point and inscribed angle of the arc known, request the end point
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_END_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # start point and inscribed angle of the arc known, request the center
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_CENTER_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # start point and inscribed angle of the arc known, request the radius
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_RADIUS:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # start point and inscribed angle of the arc known, request the second point to measure the radius
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_SECONDPTRADIUS:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPtForRadius)
      # start point, inscribed angle and radius of the arc known, request the chord direction
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # start point and radius of the arc known, request the end point
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_RADIUS_KNOWN_ASK_FOR_END_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
         


# ===============================================================================
# Qad_scale_maptool_ModeEnum class.
# ===============================================================================
class Qad_gripChangeArcRadius_maptool_ModeEnum():
   # request the base point
   ASK_FOR_BASE_PT = 1     
   # base point known, request the second point for the radius
   BASE_PT_KNOWN_ASK_FOR_RADIUS_PT = 2


# ===============================================================================
# Qad_gripChangeArcRadius_maptool class
# ===============================================================================
class Qad_gripChangeArcRadius_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)
                        
      self.basePt = None
      self.entity = None
      self.arc = None 
      self.coordTransform = None
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

   def setEntity(self, entity):
      self.entity = QadEntity(entity)
      self.arc = self.entity.getQadGeom() # arc in map coordinate
      self.basePt = self.arc.center
      self.coordTransform = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), \
                                                   entity.layer.crs(), \
                                                   QgsProject.instance())


   # ============================================================================
   # stretch
   # ============================================================================
   def changeRadius(self, radius):
      self.__highlight.reset()
      # radius = new radius of the arc
      # tolerance2ApproxCurve = tolerance to recreate the curves
      self.arc.radius = radius
      points = self.arc.asPolyline()
      if points is None:
         return False
      
      g = QgsGeometry.fromPolylineXY(points)
      # transform the geometry to the layer's CRS
      g.transform(self.coordTransform)      
      self.__highlight.addGeometry(g, self.entity.layer)
            
      
   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      # base point known, request the second point for the radius
      if self.mode == Qad_gripChangeArcRadius_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_RADIUS_PT:
         radius = qad_utils.getDistance(self.basePt, self.tmpPoint)
         self.changeRadius(radius)                           
         
    
   def activate(self):
      QadGetPoint.activate(self)            
      self.__highlight.show()

   def deactivate(self):
      try: # necessary because if QGIS is closed this event starts despite the maptool object no longer exists!
         QadGetPoint.deactivate(self)
         self.__highlight.hide()
      except:
         pass
      
      
   def setMode(self, mode):
      self.mode = mode
      # nothing known, request the base point
      if self.mode == Qad_gripChangeArcRadius_maptool_ModeEnum.ASK_FOR_BASE_PT:
         self.clear()
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.__highlight.reset()
      # base point known, request the second point for the radius
      elif self.mode == Qad_gripChangeArcRadius_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_RADIUS_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.basePt)
