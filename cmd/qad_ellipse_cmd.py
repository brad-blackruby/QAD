# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 ELLIPSE command for drawing an ellipse
 
                              -------------------
        last update          : 2025-05-15
        copyright            : Black Ruby
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
from qgis.core import QgsWkbTypes, QgsPointXY
from qgis.PyQt.QtGui import QIcon
import math


from ..qad_ellipse import QadEllipse
from ..qad_ellipse_arc import QadEllipseArc
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_ellipse_maptool import Qad_ellipse_maptool, Qad_ellipse_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputModeEnum, QadInputTypeEnum
from .. import qad_utils
from .. import qad_layer


# ===============================================================================
# QadMELLIPSECommandClassStepEnum class.
# ===============================================================================
class QadELLIPSECommandClassStepEnum():
   ASK_FOR_FIRST_FINAL_AXIS_PT      = 1 # Requests the first endpoint of the axis (0 is the start of the command)
   ASK_FOR_SECOND_FINAL_AXIS_PT     = 2 # Requests the second endpoint of the axis
   ASK_DIST_TO_OTHER_AXIS           = 3 # Requests to specify the distance from the second axis
   ASK_ROTATION_ROUND_MAJOR_AXIS    = 4 # Requests the rotation around the major axis
   ASK_START_ANGLE                  = 5 # Requests the start angle
   ASK_END_ANGLE                    = 6 # Requests the end angle
   ASK_INCLUDED_ANGLE               = 7 # Requests the included angle
   ASK_START_PARAMETER              = 8 # Requests the start parametric angle
   ASK_END_PARAMETER                = 9 # Requests the end parametric angle
   ASK_FOR_CENTER                   = 10 # Requests the center
   ASK_FOR_FIRST_FOCUS              = 11 # Requests the first focus point
   ASK_FOR_SECOND_FOCUS             = 12 # Requests the second focus point
   ASK_FOR_PT_ON_ELLIPSE            = 13 # Requests a point on the ellipse
   ASK_AREA                         = 14 # Requests the area of the ellipse

# Class that manages the ELLIPSE command
class QadELLIPSECommandClass(QadCommandClass):
   
   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadELLIPSECommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "ELLIPSE")

   def getEnglishName(self):
      return "ELLIPSE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runELLIPSECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/ellipse.svg")

   def getNote(self):
      # set the explanatory notes for the command
      return QadMsg.translate("Command_ELLIPSE", "Draws an ellipse by many methods.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # if this flag = True the command is used within another command to draw a circle
      # that will not be saved on a layer
      self.virtualCmd = False
      self.rubberBandBorderColor = None
      self.rubberBandFillColor = None
      
      self.arc = False # flag that determines whether to draw an elliptical arc or a complete ellipse
      self.axis1Pt1 = None # first endpoint of the axis
      self.axis1Pt2 = None # second endpoint of the axis
      self.distToOtherAxis = 0.0 # distance from the other axis
      self.centerPt = None # center point of the ellipse
      self.ellipse = QadEllipse()
      self.ellipseArc = QadEllipseArc()
      self.rot = 0 # rotation around the axis
      self.startAngle = 0.0 # the ellipse can be incomplete (like an arc for a circle)
      self.endAngle = math.pi * 2 # A startAngle of 0 and endAngle of 2pi will produce a closed Ellipse.
      self.includedAngle = 0.0
      self.focus1 = None # first focus point
      self.focus2 = None # second focus point

def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_ellipse_maptool(self.plugIn)
            self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)
         return self.PointMapTool
      else:
         return None


   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      self.rubberBandBorderColor = rubberBandBorderColor
      self.rubberBandFillColor = rubberBandFillColor
      if self.PointMapTool is not None:
         self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)

         
   # ============================================================================
   # waitForFirstFinalAxisPt
   # ============================================================================
   def waitForFirstFinalAxisPt(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_FOR_FIRST_FINAL_AXIS_PT
      # set the map tool
      self.getPointMapTool().setSelectionMode(Qad_ellipse_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_FINAL_AXIS_PT)
      if self.arc == False: # if you want to draw a complete ellipse
         keyWords = QadMsg.translate("Command_ELLIPSE", "Arc") + "/" + \
                    QadMsg.translate("Command_ELLIPSE", "Center") + "/" + \
                    QadMsg.translate("Command_ELLIPSE", "Foci")
         prompt = QadMsg.translate("Command_ELLIPSE", "Specify axis endpoint of ellipse or [{0}]: ").format(keyWords)
         englishKeyWords = "Arc" + "/" + "Center" + "/" + "Foci"
         keyWords += "_" + englishKeyWords
      else: # if you want to draw an elliptical arc
         keyWords = QadMsg.translate("Command_ELLIPSE", "Center") + "/" + \
                    QadMsg.translate("Command_ELLIPSE", "Foci")
         prompt = QadMsg.translate("Command_ELLIPSE", "Specify axis endpoint of elliptical arc or [{0}]: ").format(keyWords)
         englishKeyWords = "Center" + "/" + "Foci"
         keyWords += "_" + englishKeyWords
      
      # prepares to wait for a point or enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)
         
         
   # ============================================================================
   # waitForSecondFinalAxisPt
   # ============================================================================
   def waitForSecondFinalAxisPt(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_FOR_SECOND_FINAL_AXIS_PT
      # set the map tool
      self.getPointMapTool().axis1Pt1 = self.axis1Pt1
      self.getPointMapTool().centerPt = self.centerPt
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.FIRST_FINAL_AXIS_PT_KNOWN_ASK_FOR_SECOND_FINAL_AXIS_PT)                                
      # prepares to wait for a point
      self.waitForPoint(QadMsg.translate("Command_ELLIPSE", "Specify other endpoint of axis: "))

         
   # ============================================================================
   # waitForDistanceToOtherAxis
   # ============================================================================
   def waitForDistanceToOtherAxis(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_DIST_TO_OTHER_AXIS
      # set the map tool
      if self.getPointMapTool().axis1Pt1 is None: # if starting from the center of the ellipse
         self.getPointMapTool().axis1Pt1 = self.axis1Pt1
      else:
         self.getPointMapTool().centerPt = self.centerPt
      self.getPointMapTool().axis1Pt2 = self.axis1Pt2
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_FOR_DIST_TO_OTHER_AXIS)                                
      keyWords = QadMsg.translate("Command_ELLIPSE", "Rotation") + "/" + \
                 QadMsg.translate("Command_ELLIPSE", "Area")
      prompt = QadMsg.translate("Command_ELLIPSE", "Specify distance to other axis or [{0}]: ").format(keyWords)

      englishKeyWords = "Rotation" + "/" + "Area"
      keyWords += "_" + englishKeyWords
      # prepares to wait for a point, a real number or a keyword
      # msg, inputType, default, keyWords, non-null value
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS | QadInputTypeEnum.FLOAT, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)


   # ============================================================================
   # waitForRotationAroundMajorAxis
   # ============================================================================
   def waitForRotationAroundMajorAxis(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_ROTATION_ROUND_MAJOR_AXIS
      # set the map tool
      self.getPointMapTool().axis1Pt2 = self.axis1Pt2
      self.getPointMapTool().centerPt = self.centerPt
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_ROTATION_ROUND_MAJOR_AXIS)                                

      # prepares to wait for a point or an angle
      # msg, inputType, default, keyWords, non-null value
      self.waitFor(QadMsg.translate("Command_ELLIPSE", "Specify rotation around major axis: "), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                   None, \
                   "", QadInputModeEnum.NOT_NULL)


   # ============================================================================
   # waitForArea
   # ============================================================================
   def waitArea(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_AREA
      # set the map tool
      self.getPointMapTool().axis1Pt2 = self.axis1Pt2
      self.getPointMapTool().centerPt = self.centerPt
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_AREA)                                

      # prepares to wait for a value or an angle
      # msg, inputType, default, keyWords, non-null value
      self.waitForFloat(QadMsg.translate("Command_ELLIPSE", "Specify ellipse area: "), \
                        None, \
                        QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)


   # ============================================================================
   # waitForStartAngle
   # ============================================================================
   def waitForStartAngle(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_START_ANGLE
      # set the map tool
      self.getPointMapTool().ellipse = self.ellipse
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_START_ANGLE)                                

      keyWords = QadMsg.translate("Command_ELLIPSE", "Parameter")
      prompt = QadMsg.translate("Command_ELLIPSE", "Specify start angle or [{0}]: ").format(keyWords)

      englishKeyWords = "Parameter"
      keyWords += "_" + englishKeyWords

      # prepares to wait for a point or an angle or a keyword
      # msg, inputType, default, keyWords, non-null value
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS | QadInputTypeEnum.ANGLE, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)


   # ============================================================================
   # waitForEndAngle
   # ============================================================================
   def waitForEndAngle(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_END_ANGLE
      # set the map tool
      self.getPointMapTool().startAngle = self.startAngle
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_END_ANGLE)                                

      keyWords = QadMsg.translate("Command_ELLIPSE", "Parameter") + "/" + \
                 QadMsg.translate("Command_ELLIPSE", "Included angle")
      prompt = QadMsg.translate("Command_ELLIPSE", "Specify end angle or [{0}]: ").format(keyWords)
      englishKeyWords = "Parameter" + "/" + "Included angle"
      keyWords += "_" + englishKeyWords

      # prepares to wait for a point or an angle or a keyword
      # msg, inputType, default, keyWords, non-null value
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS | QadInputTypeEnum.ANGLE, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)

# ============================================================================
   # waitForIncludedAngle
   # ============================================================================
   def waitForIncludedAngle(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_INCLUDED_ANGLE
      # set the map tool
      self.getPointMapTool().startAngle = self.startAngle
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_INCLUDED_ANGLE)                                

      # prepares to wait for a point or an angle
      # msg, inputType, default, keyWords, non-null value
      self.waitFor(QadMsg.translate("Command_ELLIPSE", "Specify included angle for arc: "), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                   None, \
                   "", QadInputModeEnum.NOT_NULL)


   # ============================================================================
   # waitForStartParameter
   # ============================================================================
   def waitForStartParameter(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_START_PARAMETER
      # set the map tool
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_START_PARAMETER)                                

      keyWords = QadMsg.translate("Command_ELLIPSE", "Angle")
      prompt = QadMsg.translate("Command_ELLIPSE", "Specify start parameter [{0}]: ").format(keyWords)
      englishKeyWords = "Angle"
      keyWords += "_" + englishKeyWords

      # prepares to wait for a point or an angle or a keyword
      # msg, inputType, default, keyWords, non-null value
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS | QadInputTypeEnum.ANGLE, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)


   # ============================================================================
   # waitForEndParameter
   # ============================================================================
   def waitForEndParameter(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_END_PARAMETER
      # set the map tool
      self.getPointMapTool().startAngle = self.startAngle
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_END_PARAMETER)                                

      keyWords = QadMsg.translate("Command_ELLIPSE", "Angle") + "/" + \
                 QadMsg.translate("Command_ELLIPSE", "Included angle")
      prompt = QadMsg.translate("Command_ELLIPSE", "Specify end parameter or [{0}]: ").format(keyWords)
      englishKeyWords = "Angle" + "/" + "Included angle"
      keyWords += "_" + englishKeyWords

      # prepares to wait for a point or an angle or a keyword
      # msg, inputType, default, keyWords, non-null value
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS | QadInputTypeEnum.ANGLE, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)


   # ============================================================================
   # waitForCenter
   # ============================================================================
   def waitForCenter(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_FOR_CENTER
      # set the map tool
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_FOR_CENTER)
      # prepares to wait for a point
      self.waitForPoint(QadMsg.translate("Command_ELLIPSE", "Specify center of ellipse: "))


   # ============================================================================
   # waitForFirstFocus
   # ============================================================================
   def waitForFirstFocus(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_FOR_FIRST_FOCUS
      # set the map tool
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_FOR_FIRST_FOCUS)
      # prepares to wait for a point
      self.waitForPoint(QadMsg.translate("Command_ELLIPSE", "Specify first focus point of ellipse: "))


   # ============================================================================
   # waitForSecondFocus
   # ============================================================================
   def waitForSecondFocus(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_FOR_SECOND_FOCUS
      # set the map tool
      self.getPointMapTool().focus1 = self.focus1
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_FOR_SECOND_FOCUS)
      # prepares to wait for a point
      self.waitForPoint(QadMsg.translate("Command_ELLIPSE", "Specify second focus point of ellipse: "))


   # ============================================================================
   # waitForPtOnEllipse
   # ============================================================================
   def waitForPtOnEllipse(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_FOR_PT_ON_ELLIPSE
      # set the map tool
      self.getPointMapTool().focus2 = self.focus2
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_FOR_PT_ON_ELLIPSE)
      # prepares to wait for a point
      self.waitForPoint(QadMsg.translate("Command_ELLIPSE", "Specify a point on ellipse: "))


   def run(self, msgMapTool = False, msg = None):
      self.isValidPreviousInput = True # to manage the command also in macro

      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      currLayer = None
      if self.virtualCmd == False: # if you really want to save the ellipse in a layer
         if self.arc == True:
            # the current layer must be editable and of line type
            currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, [QgsWkbTypes.LineGeometry])
            if currLayer is None:
               self.showErr(errMsg)
               return True # end command
         else:
            # the current layer must be editable and of line or polygon type
            currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry])
            if currLayer is None:
               self.showErr(errMsg)
               return True # end command
         self.getPointMapTool().geomType = QgsWkbTypes.LineGeometry if currLayer.geometryType() == QgsWkbTypes.LineGeometry else QgsWkbTypes.PolygonGeometry
         
      if self.step == 0:     
         self.waitForFirstFinalAxisPt()
         return False # continue

         
      # =========================================================================
      # RESPONSE TO REQUEST FOR FIRST END POINT OF THE AXIS (from step = 0)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_FOR_FIRST_FINAL_AXIS_PT: # after waiting for a point or enter or a keyword, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated QAD
            # then the command was reactivated which returns here without the maptool
            # having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if value is None:
            if self.plugIn.lastPoint is not None:
               value = self.plugIn.lastPoint
            else:
               return True # end command

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ELLIPSE", "Arc") or value == "Arc":
               self.arc = True
               self.waitForFirstFinalAxisPt()
            elif value == QadMsg.translate("Command_ELLIPSE", "Center") or value == "Center":
               self.waitForCenter()
            elif value == QadMsg.translate("Command_ELLIPSE", "Foci") or value == "Foci":
               self.waitForFirstFocus()
         elif type(value) == QgsPointXY: # if the first endpoint of the axis has been entered
            self.axis1Pt1 = value
            self.plugIn.setLastPoint(value)                       
            self.waitForSecondFinalAxisPt()
         
         return False

    # =========================================================================
      # RESPONSE TO REQUEST FOR SECOND END POINT OF THE AXIS (from step = ASK_FOR_FIRST_FINAL_AXIS_PT)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_FOR_SECOND_FINAL_AXIS_PT: # after waiting for a point, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated QAD
            # then the command was reactivated which returns here without the maptool
            # having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY: # if the second endpoint of the axis has been entered
            self.axis1Pt2 = value
            if self.centerPt is None: # the center is not known
               self.centerPt = qad_utils.getMiddlePoint(self.axis1Pt1, self.axis1Pt2)
            else: # the first point of the axis is not known -> self.axis1Pt1
               axis1Len = qad_utils.getDistance(self.centerPt, self.axis1Pt2)
               angle = qad_utils.getAngleBy2Pts(self.axis1Pt2, self.centerPt)
               self.axis1Pt1 = qad_utils.getPolarPointByPtAngle(self.centerPt, angle, axis1Len)
               
            self.plugIn.setLastPoint(value)
            self.waitForDistanceToOtherAxis()
         
         return False


      # =========================================================================
      # RESPONSE TO REQUEST FOR DISTANCE FROM THE OTHER AXIS (from step = ASK_FOR_SECOND_FINAL_AXIS_PT)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_DIST_TO_OTHER_AXIS: # after waiting for a point or enter or a keyword, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated QAD
            # then the command was reactivated which returns here without the maptool
            # having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ELLIPSE", "Rotation") or value == "Rotation":
               self.waitForRotationAroundMajorAxis()
            elif value == QadMsg.translate("Command_ELLIPSE", "Area") or value == "Area":
               self.waitArea()            
         elif type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # if the first endpoint of the axis has been entered
               self.distToOtherAxis = qad_utils.getDistance(self.centerPt, value)
            else: # if a real number has been entered
               self.distToOtherAxis = value

            if self.ellipse.fromAxis1FinalPtsAxis2Len(self.axis1Pt2, self.axis1Pt1, self.distToOtherAxis) is not None:
               if self.arc == False: # if you want to draw a complete ellipse
                  geom = self.ellipse.asGeom(currLayer.wkbType())
                  if geom is not None:
                     if self.virtualCmd == False: # if you really want to save the ellipse in a layer
                        qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                     return True # end command
               else: # if you want to draw an elliptical arc
                  self.waitForStartAngle()
         
         return False


      # =========================================================================
      # RESPONSE TO REQUEST FOR ROTATION AROUND THE MAJOR AXIS (from step = ASK_FOR_SECOND_FINAL_AXIS_PT)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_ROTATION_ROUND_MAJOR_AXIS: # after waiting for a point or an angle, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated QAD
            # then the command was reactivated which returns here without the maptool
            # having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # if a point has been entered
               angle = qad_utils.getAngleBy2Pts(self.centerPt, value)
            else: # if a real number has been entered
               angle = value
            self.distToOtherAxis = math.fabs(qad_utils.getDistance(self.axis1Pt1, self.axis1Pt2) / 2 * math.cos(angle))

            if self.ellipse.fromAxis1FinalPtsAxis2Len(self.axis1Pt2, self.axis1Pt1, self.distToOtherAxis) is not None:
               if self.arc == False: # if you want to draw a complete ellipse
                  geom = self.ellipse.asGeom(currLayer.wkbType())
                  if geom is not None:
                     if self.virtualCmd == False: # if you really want to save the circle in a layer
                        qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                     return True # end command
               else: # if you want to draw an elliptical arc
                  self.waitForStartAngle()
         
         return False


      # =========================================================================
      # RESPONSE TO REQUEST FOR ELLIPSE AREA (from step = ASK_FOR_SECOND_FINAL_AXIS_PT)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_AREA: # after waiting for a number, the command is restarted
         if msgMapTool == True: # the value comes from a graphic selection
            self.setMapTool(self.getPointMapTool()) # reactivate the maptool
            return False
         else: # the point comes as a parameter of the function
            value = msg

         if self.ellipse.fromAxis1FinalPtsArea(self.axis1Pt2, self.axis1Pt1, value) is not None:
            if self.arc == False: # if you want to draw a complete ellipse
               geom = self.ellipse.asGeom(currLayer.wkbType())
               if geom is not None:
                  if self.virtualCmd == False: # if you really want to save the circle in a layer
                     qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # end command
            else: # if you want to draw an elliptical arc
               self.waitForStartAngle()
         
         return False

    # =========================================================================
      # RESPONSE TO REQUEST FOR START ANGLE OF THE ELLIPTICAL ARC
      # (from step = ASK_DIST_TO_OTHER_AXIS or other steps)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_START_ANGLE: # after waiting for a point or an angle, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated QAD
            # then the command was reactivated which returns here without the maptool
            # having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # if the first endpoint of the axis has been entered
               ellipseAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.ellipse.majorAxisFinalPt)
               self.startAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, value) - ellipseAngle
            else: # if a real number has been entered
               self.startAngle = value
           
            self.waitForEndAngle()
         elif type(value) == unicode:
            if value == QadMsg.translate("Command_ELLIPSE", "Parameter") or value == "Parameter":
               self.waitForStartParameter()
         
         return False


      # =========================================================================
      # RESPONSE TO REQUEST FOR END ANGLE OF THE ELLIPTICAL ARC (from step = ASK_START_ANGLE)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_END_ANGLE: # after waiting for a point or an angle, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated QAD
            # then the command was reactivated which returns here without the maptool
            # having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # if the first endpoint of the axis has been entered
               ellipseAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.ellipse.majorAxisFinalPt)
               self.endAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, value) - ellipseAngle
            else: # if a real number has been entered
               self.endAngle = value

            self.ellipseArc.set(self.ellipse.center, self.ellipse.majorAxisFinalPt, self.ellipse.axisRatio, self.startAngle, self.endAngle)
            geom = self.ellipseArc.asGeom(currLayer.wkbType())
            if geom is not None:
               if self.virtualCmd == False: # if you really want to save the circle in a layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command
           
         elif type(value) == unicode:
            if value == QadMsg.translate("Command_ELLIPSE", "Parameter") or value == "Parameter":
               self.waitForEndParameter()
            elif value == QadMsg.translate("Command_ELLIPSE", "Included angle") or value == "Included angle":
               self.waitForIncludedAngle()

         return False


      # =========================================================================
      # RESPONSE TO REQUEST FOR INCLUDED ANGLE (from step = ASK_END_ANGLE)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_INCLUDED_ANGLE: # after waiting for a point or an angle, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated QAD
            # then the command was reactivated which returns here without the maptool
            # having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # if a point has been entered
               self.endAngle = self.startAngle + qad_utils.getAngleBy2Pts(self.ellipse.center, value)
            else: # if a real number has been entered
               self.endAngle = self.startAngle + value
            
            self.ellipseArc.set(self.ellipse.center, self.ellipse.majorAxisFinalPt, self.ellipse.axisRatio, self.startAngle, self.endAngle)
            geom = self.ellipseArc.asGeom(currLayer.wkbType())
            if geom is not None:
               if self.virtualCmd == False: # if you really want to save the circle in a layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command
         
         return False

      # =========================================================================
      # RESPONSE TO REQUEST FOR START PARAMETRIC ANGLE OF THE ELLIPTICAL ARC
      # (from step = ASK_START_ANGLE or other steps)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_START_PARAMETER: # after waiting for a point or an angle, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated QAD
            # then the command was reactivated which returns here without the maptool
            # having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # if the first endpoint of the axis has been entered
               ellipseAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.ellipse.majorAxisFinalPt)
               self.startAngle = self.ellipse.getAngleFromParam(qad_utils.getAngleBy2Pts(self.ellipse.center, value) - ellipseAngle)
            else: # if a real number has been entered
               self.startAngle = self.ellipse.getAngleFromParam(value)
           
            self.waitForEndParameter()
         elif type(value) == unicode:
            if value == QadMsg.translate("Command_ELLIPSE", "Angle") or value == "Angle":
               self.waitForStartAngle()
         
         return False


      # =========================================================================
      # RESPONSE TO REQUEST FOR END PARAMETRIC ANGLE OF THE ELLIPTICAL ARC (from step = ASK_START_PARAMETER)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_END_PARAMETER: # after waiting for a point or an angle, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated QAD
            # then the command was reactivated which returns here without the maptool
            # having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # if the first endpoint of the axis has been entered
               ellipseAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.ellipse.majorAxisFinalPt)
               self.endAngle = self.ellipse.getAngleFromParam(qad_utils.getAngleBy2Pts(self.ellipse.center, value) - ellipseAngle)
            else: # if a real number has been entered
               self.endAngle = self.ellipse.getAngleFromParam(value)

            self.ellipseArc.set(self.ellipse.center, self.ellipse.majorAxisFinalPt, self.ellipse.axisRatio, self.startAngle, self.endAngle)
            geom = self.ellipseArc.asGeom(currLayer.wkbType())
            if geom is not None:
               if self.virtualCmd == False: # if you really want to save the circle in a layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command
           
         elif type(value) == unicode:
            if value == QadMsg.translate("Command_ELLIPSE", "Angle") or value == "Angle":
               self.waitForEndAngle()
            elif value == QadMsg.translate("Command_ELLIPSE", "Included angle") or value == "Included angle":
               self.waitForIncludedAngle()

         return False

    # =========================================================================
      # RESPONSE TO REQUEST FOR CENTER OF THE ELLIPSE (from step = ASK_FOR_FIRST_FINAL_AXIS_PT)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_FOR_CENTER: # after waiting for a point, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated QAD
            # then the command was reactivated which returns here without the maptool
            # having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY: # if the center has been entered
            self.centerPt = value
            self.axis1Pt1 = None
            self.plugIn.setLastPoint(value)
            self.waitForSecondFinalAxisPt()
         
         return False


      # =========================================================================
      # RESPONSE TO REQUEST FOR FIRST FOCUS POINT OF THE ELLIPSE (from step = ASK_FOR_FIRST_FINAL_AXIS_PT)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_FOR_FIRST_FOCUS: # after waiting for a point, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated QAD
            # then the command was reactivated which returns here without the maptool
            # having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY: # if the focus point has been entered
            self.focus1 = value
            self.plugIn.setLastPoint(value)
            self.waitForSecondFocus()
         
         return False


      # =========================================================================
      # RESPONSE TO REQUEST FOR SECOND FOCUS POINT OF THE ELLIPSE (from step = ASK_FOR_FIRST_FOCUS)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_FOR_SECOND_FOCUS: # after waiting for a point, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated QAD
            # then the command was reactivated which returns here without the maptool
            # having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY: # if the focus point has been entered
            self.focus2 = value
            self.plugIn.setLastPoint(value)
            self.waitForPtOnEllipse()
         
         return False


      # =========================================================================
      # RESPONSE TO REQUEST FOR A POINT ON THE ELLIPSE (from step = ASK_FOR_SECOND_FOCUS)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_FOR_PT_ON_ELLIPSE: # after waiting for a point, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated QAD
            # then the command was reactivated which returns here without the maptool
            # having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY: # if the focus point has been entered
            self.plugIn.setLastPoint(value)
            
            if self.ellipse.fromFoci(self.focus1, self.focus2, value) is not None:
               if self.arc == False: # if you want to draw a complete ellipse
                  geom = self.ellipse.asGeom(currLayer.wkbType())
                  if geom is not None:
                     if self.virtualCmd == False: # if you really want to save the circle in a layer
                        qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                     return True # end command                  
               else: # if you want to draw an elliptical arc
                  self.waitForStartAngle()
         
         return False


      return True
