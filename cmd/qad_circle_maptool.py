# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Class to manage the map tool for requesting a point in the context of the circle command
 
                              -------------------
        last update          : 2025-05-11
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


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum, QadGetPointSelectionModeEnum
from ..qad_circle import QadCircle
from ..qad_circle_fun import *
from ..qad_rubberband import QadRubberBand
from ..qad_snapper import QadSnapTypeEnum


# ===============================================================================
# Qad_circle_maptool_ModeEnum class.
# ===============================================================================
class Qad_circle_maptool_ModeEnum():
   # nothing known, request center
   NONE_KNOWN_ASK_FOR_CENTER_PT = 1     
   # center of circle known, request radius
   CENTER_PT_KNOWN_ASK_FOR_RADIUS = 2     
   # center of circle known, request diameter
   CENTER_PT_KNOWN_ASK_FOR_DIAM = 3     
   # nothing known, request first point
   NONE_KNOWN_ASK_FOR_FIRST_PT = 4
   # first point known, request second point
   FIRST_PT_KNOWN_ASK_FOR_SECOND_PT = 5
   # first and second point known, request third point
   FIRST_SECOND_PT_KNOWN_ASK_FOR_THIRD_PT = 6
   # nothing known, request first diameter endpoint
   NONE_KNOWN_ASK_FOR_FIRST_DIAM_PT = 7
   # first diameter endpoint known, request second diameter endpoint
   FIRST_DIAM_PT_KNOWN_ASK_FOR_SECOND_DIAM_PT = 8
   # nothing known, request first tangent entity
   NONE_KNOWN_ASK_FOR_FIRST_TAN = 9
   # first tangent entity known, request second tangent entity
   FIRST_TAN_KNOWN_ASK_FOR_SECOND_TAN = 10
   # first and second tangent entities known, request radius
   FIRST_SECOND_TAN_KNOWN_ASK_FOR_RADIUS = 11
   # first, second tangent entities and first point for radius known
   # request second point for radius
   FIRST_SECOND_TAN_FIRSTPTRADIUS_KNOWN_ASK_FOR_SECONDPTRADIUS = 12

# ===============================================================================
# Qad_circle_maptool class
# ===============================================================================
class Qad_circle_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)
                        
      self.centerPt = None
      self.radius = None
      self.firstPt = None
      self.secondPt = None
      self.firstDiamPt = None
      self.tan1 = None
      self.tan2 = None
      self.startPtForRadius = None
            
      self.__rubberBand = QadRubberBand(self.canvas, False)
      self.layer = None
      self.mode = None


   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      if rubberBandBorderColor is not None:
         self.__rubberBand.setBorderColor(rubberBandBorderColor)
      if rubberBandFillColor is not None:
         self.__rubberBand.setFillColor(rubberBandFillColor)

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
