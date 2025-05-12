# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Class to manage the map tool in dimension command context
 
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


import math


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_dim import QadDimStyleAlignmentEnum
from ..qad_rubberband import QadRubberBand


# ===============================================================================
# Qad_dim_maptool_ModeEnum class.
# ===============================================================================
class Qad_dim_maptool_ModeEnum():
   # nothing known, request first dimension point
   NONE_KNOWN_ASK_FOR_FIRST_PT = 1     
   # first point known, request second dimension point
   FIRST_PT_KNOWN_ASK_FOR_SECOND_PT = 2     
   # dimension points known, request position of linear dimension line
   FIRST_SECOND_PT_KNOWN_ASK_FOR_LINEAR_DIM_LINE_POS = 3     
   # request dimension text
   ASK_FOR_TEXT = 4
   # dimension points known, request position of aligned dimension line
   FIRST_SECOND_PT_KNOWN_ASK_FOR_ALIGNED_DIM_LINE_POS = 5
   # request a point on the arc for arc dimension
   ASK_FOR_PARTIAL_ARC_PT_FOR_DIM_ARC = 6
   # dimension points known, request position of arc dimension line
   FIRST_SECOND_PT_KNOWN_ASK_FOR_ARC_DIM_LINE_POS = 7
   # object to be dimensioned known (arc or circle), request position of radius dimension line
   OBJ_KNOWN_ASK_FOR_RADIUS_DIM_LINE_POS = 8


# ===============================================================================
# Qad_dim_maptool class
# ===============================================================================
class Qad_dim_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      dimStyle = None
      self.dimPt1 = None
      self.dimPt2 = None
      self.dimCircle = None
      
      self.dimArc = None # for arc dimensioning
      
      self.forcedTextRot = None # rotation of dimension text
      self.measure = None # dimension measurement (if None it will be calculated)
      self.preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL # alignment of dimension line
      self.forcedDimLineAlignment = None # forced alignment of dimension line
      self.forcedDimLineRot = 0.0 # forced rotation of dimension line
      self.leader = False # to draw leader line in arc dimensioning
      
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
            

   def setDimLineAlignment(self, LinePosPt, horizLine1, horizLine2, verticalLine1, verticalLine2):
      # < 0 if to the left of the line
      sxOfHorizLine1 = True if qad_utils.leftOfLine(LinePosPt, horizLine1[0], horizLine1[1]) < 0 else False
      sxOfHorizLine2 = True if qad_utils.leftOfLine(LinePosPt, horizLine2[0], horizLine2[1]) < 0 else False
      
      sxOfVerticalLine1 = True if qad_utils.leftOfLine(LinePosPt, verticalLine1[0], verticalLine1[1]) < 0 else False
      sxOfVerticalLine2 = True if qad_utils.leftOfLine(LinePosPt, verticalLine2[0], verticalLine2[1]) < 0 else False
      
      # if LinePosPt is between horizontal limit lines and not between vertical limit lines      
      if sxOfHorizLine1 != sxOfHorizLine2 and sxOfVerticalLine1 == sxOfVerticalLine2:
         self.preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL
      # if LinePosPt is not between horizontal limit lines and is between vertical limit lines      
      elif sxOfHorizLine1 == sxOfHorizLine2 and sxOfVerticalLine1 != sxOfVerticalLine2:
         self.preferredAlignment = QadDimStyleAlignmentEnum.VERTICAL
      
      return
