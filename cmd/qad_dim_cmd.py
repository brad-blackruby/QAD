# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 commands for creating dimensions
 
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


# Import the PyQt and QGIS libraries
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsPointXY
import math


from ..qad_snapper import QadSnapTypeEnum
from ..qad_arc import QadArc
from ..qad_dim import QadDimStyleAlignmentEnum, QadDimStyles, QadDimStyle, \
                      QadDimTypeEnum, QadDimStyleTxtRotModeEnum
from .qad_dim_maptool import Qad_dim_maptool, Qad_dim_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_entsel_cmd import QadEntSelClass
from .qad_getangle_cmd import QadGetAngleClass
from ..qad_variables import QadVariables
from .. import qad_utils
from ..qad_multi_geom import getQadGeomAt, getQadGeomPartAt
from ..qad_geom_relations import getQadGeomClosestPart, QadPerpendicularity, QadIntersections

# ============================================================================
# GENERIC FUNCTIONS - BEGIN
# ============================================================================


# ============================================================================
# GENERIC FUNCTIONS - END
# ============================================================================


# Class that manages the DIMLINEAR command
class QadDIMLINEARCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadDIMLINEARCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "DIMLINEAR")

   def getEnglishName(self):
      return "DIMLINEAR"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runDIMLINEARCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/dimLinear.svg")

   def getNote(self):
      # set the explanatory notes for the command
      return QadMsg.translate("Command_DIM", "Creates an horizontal or vertical linear dimension.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entSelClass = None
      self.GetAngleClass = None
            
      self.dimPt1 = QgsPointXY() # first explicit dimensioning point
      self.dimPt2 = QgsPointXY() # second explicit dimensioning point
      self.dimCircle = None    # circle object to be dimensioned
      
      self.measure = None # dimension measurement (if None it is calculated)
      self.preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL # alignment of the dimension line
      # read the current dimension style
      dimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      self.forcedDimLineAlignment = None # forced dimension line alignment
      self.forcedDimLineRot = 0.0 # forced dimension line rotation
      
      _dimStyle = QadDimStyles.findDimStyle(dimStyleName)
      if _dimStyle is not None:
         self.dimStyle = QadDimStyle(_dimStyle) # make a copy because it can be modified by the command
         self.dimStyle.dimType = QadDimTypeEnum.LINEAR
      else:
         self.dimStyle = None
      

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.entSelClass is not None:
         self.entSelClass.entity.deselectOnLayer()
         del self.entSelClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 2: # when in entity selection phase
         return self.entSelClass.getPointMapTool(drawMode)
      # when in rotation request phase
      elif self.step == 6 or self.step == 7:
         return self.GetAngleClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_dim_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 2: # when in entity selection phase
         return self.entSelClass.getCurrentContextualMenu()
      # when in rotation request phase
      elif self.step == 6 or self.step == 7:
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu

   
   # ============================================================================
   # addDimToLayers
   # ============================================================================
   def addDimToLayers(self, linePosPt):
      return self.dimStyle.addLinearDimToLayers(self.plugIn, self.dimPt1, self.dimPt2, \
                                                linePosPt, self.measure, self.preferredAlignment, \
                                                self.forcedDimLineRot)
   
   
   # ============================================================================
   # waitForFirstPt
   # ============================================================================
   def waitForFirstPt(self):
      self.step = 1
      # set the map tool
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)                                

      msg = QadMsg.translate("Command_DIM", "Specify first extension line origin or <select object>: ")
      
      # prepares to wait for a point or enter      
      # msg, inputType, default, keyWords, no control
      self.waitFor(msg, \
                   QadInputTypeEnum.POINT2D, \
                   None, \
                   "", QadInputModeEnum.NONE)

   
   # ============================================================================
   # waitForSecondPt
   # ============================================================================
   def waitForSecondPt(self):
      self.step = 3
      # set the map tool
      self.getPointMapTool().dimPt1 = self.dimPt1
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)                                
      # prepares to wait for a point
      self.waitForPoint(QadMsg.translate("Command_DIM", "Specify second extension line origin: "))

   
   # ============================================================================
   # waitForEntsel
   # ============================================================================
   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = 2         
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_DIM", "Select the object to dimension: ")
      # exclude point selection
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = True
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.getPointMapTool().setSnapType(QadSnapTypeEnum.DISABLE)         
      self.entSelClass.run(msgMapTool, msg)

   
   # ============================================================================
   # waitForDimensionLinePos
   # ============================================================================
   def waitForDimensionLinePos(self):
      self.step = 4
      # set the map tool      
      self.getPointMapTool().dimPt2 = self.dimPt2
      if self.getPointMapTool().dimPt1 is None: # in case of object selection dimPt1 was not initialized
         self.getPointMapTool().dimPt1 = self.dimPt1
         self.getPointMapTool().dimCircle = self.dimCircle
      self.getPointMapTool().preferredAlignment = self.preferredAlignment
      self.getPointMapTool().forcedDimLineAlignment = self.forcedDimLineAlignment
      self.getPointMapTool().forcedDimLineRot = self.forcedDimLineRot      
      self.getPointMapTool().dimStyle = self.dimStyle      
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_LINEAR_DIM_LINE_POS)                                
      
      # prepares to wait for a point or a keyword
      keyWords = QadMsg.translate("Command_DIM", "Text") + "/" + \
                 QadMsg.translate("Command_DIM", "Angle") + "/" + \
                 QadMsg.translate("Command_DIM", "Horizontal") + "/" + \
                 QadMsg.translate("Command_DIM", "Vertical") + "/" + \
                 QadMsg.translate("Command_DIM", "Rotated")      
      prompt = QadMsg.translate("Command_DIM", "Specify dimension line location or [{0}]: ").format(keyWords)
      
      englishKeyWords = "Text" + "/" + "Angle" + "/" + "Horizontal" + "/" + "Vertical" + "/" + "Rotated"
      keyWords += "_" + englishKeyWords
      # msg, inputType, default, keyWords, no control
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, \
                   QadInputModeEnum.NONE)                                      
      

   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      if self.dimStyle is None:
         self.showMsg(QadMsg.translate("QAD", "\nDimension style not valid.\nVerify the value of DIMSTYLE variable.\n"))
         return True # end command
         
      errMsg = self.dimStyle.getInValidErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # end command
      
      errMsg = self.dimStyle.getNotGraphEditableErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # end command

# =========================================================================
      # REQUEST FIRST EXTENSION LINE ORIGIN SELECTION
      if self.step == 0: # start of the command         
         self.waitForFirstPt()
         return False
      
      # =========================================================================
      # RESPONSE TO THE REQUEST FOR FIRST EXTENSION LINE ORIGIN (from step = 0)
      elif self.step == 1:
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  value = None # default option None
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if value is None:
            self.waitForEntsel(msgMapTool, msg)
         else:
            self.dimPt1.set(value.x(), value.y())
            self.waitForSecondPt()

         return False

      # =========================================================================
      # RESPONSE TO THE SELECTION OF AN ENTITY (from step = 1)
      elif self.step == 2:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               g = self.entSelClass.entity.getQadGeom()
               res = getQadGeomClosestPart(g, self.entSelClass.point)
               g = getQadGeomPartAt(g, res[2], res[3], res[4])
               objType = g.whatIs()
               
               if objType == "LINE" or objType == "ARC" or objType == "ELLIPSE_ARC":
                  self.dimPt1 = g.getStartPt()                  
                  self.dimPt2 = g.getEndPt()
               elif objType == "CIRCLE": # if it's a circle
                  self.dimCircle = g.copy()
                  
               self.waitForDimensionLinePos()
               return False
            else:
               if self.entSelClass.canceledByUsr == True: # end command
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)
         return False # continue

         
      # =========================================================================
      # RESPONSE TO THE REQUEST FOR SECOND EXTENSION LINE ORIGIN (from step = 1)
      elif self.step == 3: # after waiting for a point or a real number, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if value is None:
            return True

         if type(value) == QgsPointXY: # if the second point has been entered
            self.dimPt2.set(value.x(), value.y())
            self.waitForDimensionLinePos()
         
         return False 
         
               
      # =========================================================================
      # RESPONSE TO THE REQUEST FOR DIMENSION LINE POSITION (from step = 2 and 3)
      elif self.step == 4: # after waiting for a point or a real number, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # then the command has been reactivated that returns here without the maptool
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
            if value == QadMsg.translate("Command_DIM", "Text") or value == "Text":
               prompt = QadMsg.translate("Command_DIM", "Enter dimension text <{0}>: ")
               dist = qad_utils.getDistance(self.dimPt1, self.dimPt2)
               self.waitForString(prompt.format(str(dist)), dist)
               self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.ASK_FOR_TEXT)
               self.step = 5         
            elif value == QadMsg.translate("Command_DIM", "Angle") or value == "Angle":
               # prepares to wait for the rotation angle of the text
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                                   
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               prompt = QadMsg.translate("Command_DIM", "Specify angle of dimension text <{0}>: ")
               self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.dimStyle.textForcedRot)))
               self.GetAngleClass.angle = self.dimStyle.textForcedRot
               self.step = 6
               self.GetAngleClass.run(msgMapTool, msg)               
            elif value == QadMsg.translate("Command_DIM", "Horizontal") or value == "Horizontal":
               # horizontal alignment of the dimension line
               self.forcedDimLineAlignment = QadDimStyleAlignmentEnum.HORIZONTAL # forced dimension line alignment               
               self.forcedDimLineRot = 0.0             
               self.waitForDimensionLinePos()
            elif value == QadMsg.translate("Command_DIM", "Vertical") or value == "Vertical":
               # vertical alignment of the dimension line               
               self.forcedDimLineAlignment = QadDimStyleAlignmentEnum.VERTICAL # forced dimension line alignment
               self.forcedDimLineRot = 0.0             
               self.waitForDimensionLinePos()
            elif value == QadMsg.translate("Command_DIM", "Rotated") or value == "Rotated":
               # prepares to wait for the rotation angle of the dimension line
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                                   
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               prompt = QadMsg.translate("Command_DIM", "Specify angle of dimension line <{0}>: ")
               self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.forcedDimLineRot)))
               self.GetAngleClass.angle = self.forcedDimLineRot
               self.step = 7
               self.GetAngleClass.run(msgMapTool, msg)               
               pass
         elif type(value) == QgsPointXY: # if the dimension line positioning point has been entered
            self.preferredAlignment = self.getPointMapTool().preferredAlignment
            self.dimPt1 = self.getPointMapTool().dimPt1
            self.dimPt2 = self.getPointMapTool().dimPt2
            self.addDimToLayers(value)
            return True # end command
            
         return False


      # =========================================================================
      # RESPONSE TO THE TEXT REQUEST (from step = 4)
      elif self.step == 5: # after waiting for a string, restart the command
         if type(msg) == unicode:
            text = msg.strip()
            if len(text) > 0:
               self.measure = text
               self.getPointMapTool().measure = self.measure
         self.waitForDimensionLinePos()
            
         return False
      
      
      # =========================================================================
      # RESPONSE TO THE DIMENSION TEXT ROTATION REQUEST (from step = 4)
      elif self.step == 6:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
               self.dimStyle.textForcedRot = self.GetAngleClass.angle 
            self.waitForDimensionLinePos()

         return False
      
      
      # =========================================================================
      # RESPONSE TO THE DIMENSION LINE ROTATION REQUEST (from step = 4)
      elif self.step == 7:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.forcedDimLineRot = self.GetAngleClass.angle 
            self.waitForDimensionLinePos()

         return False

      
# Class that manages the DIMALIGNED command
class QadDIMALIGNEDCommandClass(QadCommandClass):
   
   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadDIMALIGNEDCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "DIMALIGNED")

   def getEnglishName(self):
      return "DIMALIGNED"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runDIMALIGNEDCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/dimAligned.svg")

   def getNote(self):
      # set the explanatory notes for the command
      return QadMsg.translate("Command_DIM", "Creates an aligned linear dimension.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entSelClass = None
      self.GetAngleClass = None
      
      self.dimPt1 = QgsPointXY()
      self.dimPt2 = QgsPointXY()
      self.dimCircle = None    # circle object to be dimensioned
      
      self.measure = None # dimension measurement (if None it is calculated)
      # read the current dimension style
      dimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      _dimStyle = QadDimStyles.findDimStyle(dimStyleName)      
      if _dimStyle is not None:
         self.dimStyle = QadDimStyle(_dimStyle) # make a copy because it can be modified by the command
         self.dimStyle.dimType = QadDimTypeEnum.ALIGNED
      else:
         self.dimStyle = None

 def __del__(self):
      QadCommandClass.__del__(self)
      if self.entSelClass is not None:
         self.entSelClass.entity.deselectOnLayer()
         del self.entSelClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 2: # when in entity selection phase
         return self.entSelClass.getPointMapTool(drawMode)
      # when in rotation request phase
      elif self.step == 6:
         return self.GetAngleClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_dim_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 2: # when in entity selection phase
         return self.entSelClass.getCurrentContextualMenu()
      # when in rotation request phase
      elif self.step == 6:
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu

   
   # ============================================================================
   # addDimToLayers
   # ============================================================================
   def addDimToLayers(self, linePosPt):
      return self.dimStyle.addAlignedDimToLayers(self.plugIn, self.dimPt1, self.dimPt2, \
                                                 linePosPt, self.measure)

      
   # ============================================================================
   # waitForFirstPt
   # ============================================================================
   def waitForFirstPt(self):
      self.step = 1
      # set the map tool
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)                                

      msg = QadMsg.translate("Command_DIM", "Specify first extension line origin or <select object>: ")
      
      # prepares to wait for a point or enter      
      # msg, inputType, default, keyWords, no control
      self.waitFor(msg, \
                   QadInputTypeEnum.POINT2D, \
                   None, \
                   "", QadInputModeEnum.NONE)

   
   # ============================================================================
   # waitForSecondPt
   # ============================================================================
   def waitForSecondPt(self):
      self.step = 3
      # set the map tool
      self.getPointMapTool().dimPt1 = self.dimPt1
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)                                
      # prepares to wait for a point
      self.waitForPoint(QadMsg.translate("Command_DIM", "Specify second extension line origin: "))

   
   # ============================================================================
   # waitForEntsel
   # ============================================================================
   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = 2         
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_DIM", "Select the object to dimension: ")
      # exclude point selection
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = True
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.getPointMapTool().setSnapType(QadSnapTypeEnum.DISABLE)         
      self.entSelClass.run(msgMapTool, msg)

   
   # ============================================================================
   # waitForDimensionLinePos
   # ============================================================================
   def waitForDimensionLinePos(self):
      self.step = 4
      # set the map tool      
      self.getPointMapTool().dimPt2 = self.dimPt2
      if self.getPointMapTool().dimPt1 is None: # in case of object selection dimPt1 was not initialized
         self.getPointMapTool().dimPt1 = self.dimPt1
         self.getPointMapTool().dimCircle = self.dimCircle
      self.getPointMapTool().dimStyle = self.dimStyle      
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_ALIGNED_DIM_LINE_POS)                                
      
      # prepares to wait for a point or a keyword
      keyWords = QadMsg.translate("Command_DIM", "Text") + "/" + \
                 QadMsg.translate("Command_DIM", "Angle")      
      prompt = QadMsg.translate("Command_DIM", "Specify dimension line location or [{0}]: ").format(keyWords)
      englishKeyWords = "Text" + "/" + "Angle"
      keyWords += "_" + englishKeyWords
      
      # msg, inputType, default, keyWords, no control
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, \
                   QadInputModeEnum.NONE)                                      
      

   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      if self.dimStyle is None:
         self.showMsg(QadMsg.translate("QAD", "\nDimension style not valid.\nVerify the value of DIMSTYLE variable.\n"))
         return True # end command
         
      errMsg = self.dimStyle.getInValidErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # end command
      
      errMsg = self.dimStyle.getNotGraphEditableErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # end command


      # =========================================================================
      # REQUEST FIRST EXTENSION LINE ORIGIN SELECTION
      if self.step == 0: # start of the command         
         self.waitForFirstPt()
         return False
      
      # =========================================================================
      # RESPONSE TO THE REQUEST FOR FIRST EXTENSION LINE ORIGIN (from step = 0)
      elif self.step == 1:
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  value = None # default option None
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if value is None:
            self.waitForEntsel(msgMapTool, msg)
         else:
            self.dimPt1.set(value.x(), value.y())
            self.waitForSecondPt()

         return False

      # =========================================================================
      # RESPONSE TO THE SELECTION OF AN ENTITY (from step = 1)
      elif self.step == 2:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               g = self.entSelClass.entity.getQadGeom()
               res = getQadGeomClosestPart(g, self.entSelClass.point)
               g = getQadGeomPartAt(g, res[2], res[3], res[4])
               objType = g.whatIs()
               
               if objType == "LINE" or objType == "ARC" or objType == "ELLIPSE_ARC":
                  self.dimPt1 = g.getStartPt()                  
                  self.dimPt2 = g.getEndPt()
               elif objType == "CIRCLE": # if it's a circle
                  self.dimCircle = g.copy()
                  l = QadLine().set(self.dimCircle.center, self.entSelClass.point)
                  intPts = QadIntersections.infinityLineWithCircle(l, self.dimCircle)
                  if len(intPts) == 2:
                     self.dimPt1 = intPts[0]
                     self.dimPt2 = intPts[1]                     
                  
               self.waitForDimensionLinePos()
               return False
            else:
               if self.entSelClass.canceledByUsr == True: # end command
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)
         return False # continue


      # =========================================================================
      # RESPONSE TO THE REQUEST FOR SECOND EXTENSION LINE ORIGIN (from step = 1)
      elif self.step == 3: # after waiting for a point or a real number, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if value is None:
            return True

         if type(value) == QgsPointXY: # if the second point has been entered
            self.dimPt2.set(value.x(), value.y())
            self.waitForDimensionLinePos()
         
         return False

# =========================================================================
      # RESPONSE TO THE REQUEST FOR DIMENSION LINE POSITION (from step = 2 and 3)
      elif self.step == 4: # after waiting for a point or a real number, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # then the command has been reactivated that returns here without the maptool
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
            if value == QadMsg.translate("Command_DIM", "Text") or value == "Text":
               prompt = QadMsg.translate("Command_DIM", "Enter dimension text <{0}>: ")
               dist = qad_utils.getDistance(self.dimPt1, self.dimPt2)
               self.waitForString(prompt.format(str(dist)), dist)
               self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.ASK_FOR_TEXT)
               self.step = 5         
            elif value == QadMsg.translate("Command_DIM", "Angle") or value == "Angle":
               # prepares to wait for the rotation angle of the text
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                                   
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               prompt = QadMsg.translate("Command_DIM", "Specify angle of dimension text <{0}>: ")
               self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.dimStyle.textForcedRot)))
               self.GetAngleClass.angle = self.dimStyle.textForcedRot
               self.step = 6
               self.GetAngleClass.run(msgMapTool, msg)               
         elif type(value) == QgsPointXY: # if the dimension line positioning point has been entered
            self.dimPt1 = self.getPointMapTool().dimPt1
            self.dimPt2 = self.getPointMapTool().dimPt2
            self.addDimToLayers(value)
            return True # end command
            
         return False


      # =========================================================================
      # RESPONSE TO THE TEXT REQUEST (from step = 4)
      elif self.step == 5: # after waiting for a string, restart the command
         if type(msg) == unicode:
            text = msg.strip()
            if len(text) > 0:
               self.measure = text
               self.getPointMapTool().measure = self.measure
         self.waitForDimensionLinePos()
            
         return False


      # =========================================================================
      # RESPONSE TO THE DIMENSION TEXT ROTATION REQUEST (from step = 4)
      elif self.step == 6:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
               self.dimStyle.textForcedRot = self.GetAngleClass.angle 
            self.waitForDimensionLinePos()

         return False


# QadDIMARCCommandClassStepEnum class.
# ===============================================================================
class QadDIMARCCommandClassStepEnum():
   START                = 0 # must be = 0 because it's the start of the command
   ASK_FOR_ENTSEL       = 1 # requests entity selection
   ASK_FOR_MAIN_OPTIONS = 2 # requests to select an option
   ASK_FOR_TEXT_VALUE   = 3 # requests the value of the dimension text
   ASK_FOR_TEXT_ROT     = 4 # requests the rotation of the dimension text
   ASK_FOR_1PT_ARC      = 5 # requests the first point of the arc
   ASK_FOR_2PT_ARC      = 6 # requests the second point of the arc


# Class that manages the DIMARC command
class QadDIMARCCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadDIMARCCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "DIMARC")

   def getEnglishName(self):
      return "DIMARC"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runDIMARCCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/dimArc.svg")

   def getNote(self):
      # set the explanatory notes for the command
      return QadMsg.translate("Command_DIM", "Creates an arc length dimension.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entSelClass = None
      self.GetAngleClass = None
      self.dimPt1 = QgsPointXY()
      self.dimPt2 = QgsPointXY()
      self.dimArc = None    # arc object to be dimensioned
      self.dimPartialArc = QadArc()
      self.leader = False # option available only for arcs > 90 degrees 
            
      self.measure = None # dimension measurement (if None it is calculated)
      # read the current dimension style
      dimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      self.dimStyle = QadDimStyles.findDimStyle(dimStyleName)
      if self.dimStyle is not None:
         self.dimStyle.dimType = QadDimTypeEnum.ARC_LENTGH
      

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.entSelClass is not None:
         self.entSelClass.entity.deselectOnLayer()
         del self.entSelClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_ENTSEL: # when in entity selection phase
         return self.entSelClass.getPointMapTool(drawMode)
      # when in rotation request phase
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_TEXT_ROT:
         return self.GetAngleClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_dim_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_ENTSEL: # when in entity selection phase
         return self.entSelClass.getCurrentContextualMenu()
      # when in rotation request phase
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_TEXT_ROT:
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   # ============================================================================
   # setArc
   # ============================================================================
   def setArc(self, entity, point):
      """
      Sets self.dimArc that defines the arc to dimension
      """
      qadGeom = entity.getQadGeom()
      """
      the function returns a list with 
      (<minimum distance>
       <closest point>
       <index of the closest geometry>
       <index of the closest sub-geometry>
       <index of the part of the closest sub-geometry>
       <"left of" if the point is to the left of the part with the following values:
       -   < 0 = left (for line, arc or ellipse arc) or inside (for circles, ellipses)
       -   > 0 = right (for line, arc or ellipse arc) or outside (for circles, ellipses)
       )
      """
      dummy = getQadGeomClosestPart(qadGeom, point)
      # returns the sub-geometry
      subGeom = getQadGeomAt(qadGeom, dummy[2], dummy[3])
      
      gType = subGeom.whatIs()
      if gType == "POLYLINE":
         subGeom = subGeom.getLinearObjectAt(dummy[4])
         gType = subGeom.whatIs()
      
      if gType == "ARC":
         self.dimArc = subGeom
         self.dimPartialArc.set(self.dimArc.center, self.dimArc.radius, self.dimArc.startAngle, self.dimArc.endAngle)
         return True
      else:
         return False

    # ============================================================================
   # getPartialPtOnArc
   # ============================================================================
   def getPartialPtOnArc(self, pt):
      """
      Calculates the point on the arc closest to pt which is a point chosen by the user
      """
      
      perpPts = QadPerpendicularity.fromPointToArc(pt, self.dimArc)
      if len(perpPts) == 0: # look for the closest point to pt1 between start and end
         startPt = self.dimArc.getStartPt()
         endPt = self.dimArc.getEndPt()
         if qad_utils.getDistance(startPt, pt) <= qad_utils.getDistance(endPt, pt):
            return startPt
         else:
            return endPt
      elif len(perpPts) == 1:
         return perpPts[0]
      elif len(perpPts) == 2: # look for the closest point to pt1
         if qad_utils.getDistance(perpPts[0], pt) <= qad_utils.getDistance(perpPts[1], pt):
            return perpPts[0]
         else:
            return perpPts[1]

      return None


   # ============================================================================
   # setPartialArc
   # ============================================================================
   def setPartialArc(self):
      """
      Calculates the partial arc of dimArc that has endpoints at dimPt1 and dimPt2
      """
      self.dimPartialArc.setEndAngleByPt(self.dimPt1)
      l1 = self.dimPartialArc.length()
      self.dimPartialArc.setEndAngleByPt(self.dimPt2)
      l2 = self.dimPartialArc.length()
      
      if l1 > l2: # if dimPt1 is further than dimPt2 from the start point of the arc
         self.dimPartialArc.setEndAngleByPt(self.dimPt1)
         self.dimPartialArc.setStartAngleByPt(self.dimPt2)
      else: # if dimPt1 is closer than dimPt2 to the start point of the arc
         self.dimPartialArc.setStartAngleByPt(self.dimPt1)


   # ============================================================================
   # addDimToLayers
   # ============================================================================
   def addDimToLayers(self, linePosPt):
      return self.dimStyle.addArcDimToLayers(self.plugIn, self.dimPartialArc, \
                                             linePosPt, self.measure, self.leader)

   
   # ============================================================================
   # waitForEntsel
   # ============================================================================
   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = QadDIMARCCommandClassStepEnum.ASK_FOR_ENTSEL
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_DIM", "Select arc or polyline arc segment: ")
      # exclude the selection of points and dimensions
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = True
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.checkDimLayers = False
      self.entSelClass.getPointMapTool().setSnapType(QadSnapTypeEnum.DISABLE)
      self.entSelClass.run(msgMapTool, msg)

   
   # ============================================================================
   # waitForDimensionLinePos
   # ============================================================================
   def waitForDimensionLinePos(self):
      self.step = QadDIMARCCommandClassStepEnum.ASK_FOR_MAIN_OPTIONS
      # set the map tool      
      self.getPointMapTool().dimArc = self.dimPartialArc
      self.getPointMapTool().dimStyle = self.dimStyle
      self.getPointMapTool().leader = self.leader
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_ARC_DIM_LINE_POS)
      
      # prepares to wait for a point or a keyword
      keyWords = QadMsg.translate("Command_DIM", "Text") + "/" + \
                 QadMsg.translate("Command_DIM", "Angle") + "/" + \
                 QadMsg.translate("Command_DIM", "Partial")
      englishKeyWords = "Text" + "/" + "Angle" + "/" + "Partial"
      
      # if the arc angle is > 90 degrees, also use the leader option
      if self.dimArc.totalAngle() > math.pi / 2:
         if self.leader == False:
            keyWords = keyWords + "/" + QadMsg.translate("Command_DIM", "Leader")
            englishKeyWords = englishKeyWords + "/" + "Leader"
         else:
            keyWords = keyWords + "/" + QadMsg.translate("Command_DIM", "No leader")
            englishKeyWords = englishKeyWords + "/" + "No leader"
         
      prompt = QadMsg.translate("Command_DIM", "Specify dimension location or [{0}]: ").format(keyWords)
      keyWords += "_" + englishKeyWords

      # msg, inputType, default, keyWords, no control
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, \
                   QadInputModeEnum.NONE)                                      
      

   # ============================================================================
   # waitForFirstPt
   # ============================================================================
   def waitForFirstPt(self):
      self.step = QadDIMARCCommandClassStepEnum.ASK_FOR_1PT_ARC
      # set the map tool
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.ASK_FOR_PARTIAL_ARC_PT_FOR_DIM_ARC)

      msg = QadMsg.translate("Command_DIM", "Specify first point on the arc: ")
      
      # prepares to wait for a point
      self.waitForPoint(msg)
      

   # ============================================================================
   # waitForSecondPt
   # ============================================================================
   def waitForSecondPt(self):
      self.step = QadDIMARCCommandClassStepEnum.ASK_FOR_2PT_ARC
      # set the map tool
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.ASK_FOR_PARTIAL_ARC_PT_FOR_DIM_ARC)

      msg = QadMsg.translate("Command_DIM", "Specify second point on the arc: ")
      
      # prepares to wait for a point
      self.waitForPoint(msg)


   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      if self.dimStyle is None:
         self.showMsg(QadMsg.translate("QAD", "\nDimension style not valid.\nVerify the value of DIMSTYLE variable.\n"))
         return True # end command
         
      errMsg = self.dimStyle.getInValidErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # end command
      
      errMsg = self.dimStyle.getNotGraphEditableErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # end command

      if self.step == QadDIMARCCommandClassStepEnum.START:
         self.waitForEntsel(msgMapTool, msg)
         return False # continue

      # =========================================================================
      # RESPONSE TO THE SELECTION OF AN ENTITY
      if self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_ENTSEL:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               if self.setArc(self.entSelClass.entity, self.entSelClass.point) == True:
                  self.waitForDimensionLinePos()
               else:
                  self.showMsg(QadMsg.translate("Command_DIM", "Select an arc or polyline arc segment."))
            else:               
               if self.entSelClass.canceledByUsr == True: # end command
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)
         return False # continue


      # =========================================================================
      # RESPONSE TO THE REQUEST FOR DIMENSION LINE POSITION
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_MAIN_OPTIONS: # after waiting for a point or an option, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # then the command has been reactivated that returns here without the maptool
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
            if value == QadMsg.translate("Command_DIM", "Text") or value == "Text":
               prompt = QadMsg.translate("Command_DIM", "Enter dimension text <{0}>: ")
               dist = self.dimPartialArc.length()
               self.waitForString(prompt.format(str(dist)), dist)
               self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.ASK_FOR_TEXT)
               self.step = QadDIMARCCommandClassStepEnum.ASK_FOR_TEXT_VALUE
            elif value == QadMsg.translate("Command_DIM", "Angle") or value == "Angle":
               # prepares to wait for the rotation angle of the text
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                                   
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               prompt = QadMsg.translate("Command_DIM", "Specify angle of dimension text <{0}>: ")
               self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.dimStyle.textForcedRot)))
               self.GetAngleClass.angle = self.dimStyle.textForcedRot
               self.step = QadDIMARCCommandClassStepEnum.ASK_FOR_TEXT_ROT
               self.GetAngleClass.run(msgMapTool, msg)
            elif value == QadMsg.translate("Command_DIM", "Partial") or value == "Partial":
               self.waitForFirstPt()
            elif value == QadMsg.translate("Command_DIM", "Leader") or value == "Leader":
               self.leader = True
               self.waitForDimensionLinePos()
            elif value == QadMsg.translate("Command_DIM", "No leader") or value == "No leader":
               self.leader = False
               self.waitForDimensionLinePos()
               
         elif type(value) == QgsPointXY: # if the dimension line positioning point has been entered
            self.addDimToLayers(value)
            return True # end command
            
         return False

    # =========================================================================
      # RESPONSE TO THE TEXT REQUEST (from step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_TEXT_VALUE: # after waiting for a string, restart the command
         if type(msg) == unicode:
            text = msg.strip()
            if len(text) > 0:
               self.measure = text
               self.getPointMapTool().measure = self.measure
         self.waitForDimensionLinePos()
            
         return False
      
      
      # =========================================================================
      # RESPONSE TO THE DIMENSION TEXT ROTATION REQUEST (from step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_TEXT_ROT:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
               self.dimStyle.textForcedRot = self.GetAngleClass.angle 
            self.waitForDimensionLinePos()

         return False
      

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR FIRST POINT ON THE ARC (from step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_1PT_ARC: # after waiting for a point or a real number, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY: # if the second point has been entered
            ptOnArc = self.getPartialPtOnArc(value)
            if ptOnArc is not None:
               self.dimPt1.set(ptOnArc.x(), ptOnArc.y())

         self.waitForSecondPt()
         
         return False 
      

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR FIRST POINT ON THE ARC (from step = ASK_FOR_1PT_ARC)
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_2PT_ARC: # after waiting for a point or a real number, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY: # if the second point has been entered
            ptOnArc = self.getPartialPtOnArc(value)
            if ptOnArc is not None:
               self.dimPt2.set(ptOnArc.x(), ptOnArc.y())
            
            self.setPartialArc()
            self.waitForDimensionLinePos()
         
         return False 


# ===============================================================================
# QadDIMRADIUSCommandClassStepEnum class.
# ===============================================================================
class QadDIMRADIUSCommandClassStepEnum():
   START                = 0 # must be = 0 because it's the start of the command
   ASK_FOR_ENTSEL       = 1 # requests entity selection
   ASK_FOR_MAIN_OPTIONS = 2 # requests to select an option
   ASK_FOR_TEXT_VALUE   = 3 # requests the value of the dimension text
   ASK_FOR_TEXT_ROT     = 4 # requests the rotation of the dimension text


# Class that manages the DIMRADIUS command
class QadDIMRADIUSCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadDIMRADIUSCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "DIMRADIUS")

   def getEnglishName(self):
      return "DIMRADIUS"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runDIMRADIUSCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/dimRadius.svg")

   def getNote(self):
      # set the explanatory notes for the command
      return QadMsg.translate("Command_DIM", "Creates a radius dimension for a circle or an arc.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entSelClass = None
      self.GetAngleClass = None
      self.dimObj = None    # arc or circle object to dimension
            
      self.measure = None # dimension measurement (if None it is calculated)
      # read the current dimension style
      dimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      self.dimStyle = QadDimStyles.findDimStyle(dimStyleName)
      if self.dimStyle is not None:
         self.dimStyle.dimType = QadDimTypeEnum.ARC_LENTGH
      

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.entSelClass is not None:
         self.entSelClass.entity.deselectOnLayer()
         del self.entSelClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_ENTSEL: # when in entity selection phase
         return self.entSelClass.getPointMapTool(drawMode)
      # when in rotation request phase
      elif self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_TEXT_ROT:
         return self.GetAngleClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_dim_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_ENTSEL: # when in entity selection phase
         return self.entSelClass.getCurrentContextualMenu()
      # when in rotation request phase
      elif self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_TEXT_ROT:
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   # ============================================================================
   # setArcOrCircle
   # ============================================================================
   def setArcOrCircle(self, entity, point):
      """
      Sets self.dimObj that defines the arc or circle to dimension
      """
      qadGeom = entity.getQadGeom()
      """
      the function returns a list with 
      (<minimum distance>
       <closest point>
       <index of the closest geometry>
       <index of the closest sub-geometry>
       <index of the part of the closest sub-geometry>
       <"left of" if the point is to the left of the part with the following values:
       -   < 0 = left (for line, arc or ellipse arc) or inside (for circles, ellipses)
       -   > 0 = right (for line, arc or ellipse arc) or outside (for circles, ellipses)
       )
      """
      dummy = getQadGeomClosestPart(qadGeom, point)
      # returns the sub-geometry
      subGeom = getQadGeomAt(qadGeom, dummy[2], dummy[3])
      gType = subGeom.whatIs()
      
      if gType == "ARC" or gType == "CIRCLE":
         self.dimObj = subGeom
         return True
      else:
         return False
      

   # ============================================================================
   # addDimToLayers
   # ============================================================================
   def addDimToLayers(self, linePosPt):
      return self.dimStyle.addRadiusDimToLayers(self.plugIn, self.dimObj, \
                                                linePosPt, self.measure)

   
   # ============================================================================
   # waitForEntsel
   # ============================================================================
   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = QadDIMRADIUSCommandClassStepEnum.ASK_FOR_ENTSEL
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_DIM", "Select arc or circle: ")
      # exclude the selection of points and dimensions
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = True
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.checkDimLayers = False
      self.entSelClass.getPointMapTool().setSnapType(QadSnapTypeEnum.DISABLE)
      self.entSelClass.run(msgMapTool, msg)
      
   
   # ============================================================================
   # waitForDimensionLinePos
   # ============================================================================
   def waitForDimensionLinePos(self):
      self.step = QadDIMRADIUSCommandClassStepEnum.ASK_FOR_MAIN_OPTIONS
      # set the map tool
      if self.dimObj.whatIs() == "ARC":
         self.getPointMapTool().dimArc = self.dimObj
      else:
         self.getPointMapTool().dimCircle = self.dimObj

      self.getPointMapTool().dimStyle = self.dimStyle
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.OBJ_KNOWN_ASK_FOR_RADIUS_DIM_LINE_POS)
      
      # prepares to wait for a point or a keyword
      # prepares to wait for a point or a keyword
      keyWords = QadMsg.translate("Command_DIM", "Text") + "/" + \
                 QadMsg.translate("Command_DIM", "Angle")
      englishKeyWords = "Text" + "/" + "Angle"

      prompt = QadMsg.translate("Command_DIM", "Specify dimension location or [{0}]: ").format(keyWords)
      keyWords += "_" + englishKeyWords

      # msg, inputType, default, keyWords, no control
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, \
                   QadInputModeEnum.NONE)                                      


   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      if self.dimStyle is None:
         self.showMsg(QadMsg.translate("QAD", "\nDimension style not valid.\nVerify the value of DIMSTYLE variable.\n"))
         return True # end command
         
      errMsg = self.dimStyle.getInValidErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # end command
      
      errMsg = self.dimStyle.getNotGraphEditableErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # end command

      if self.step == QadDIMRADIUSCommandClassStepEnum.START:
         self.waitForEntsel(msgMapTool, msg)
         return False # continue

      # =========================================================================
      # RESPONSE TO THE SELECTION OF AN ENTITY
      if self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_ENTSEL:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               if self.setArcOrCircle(self.entSelClass.entity, self.entSelClass.point) == True:
                  self.waitForDimensionLinePos()
               else:
                  self.showMsg(QadMsg.translate("Command_DIM", "Select an arc or polyline arc segment."))
            else:               
               if self.entSelClass.canceledByUsr == True: # end command
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)
         return False # continue


      # =========================================================================
      # RESPONSE TO THE REQUEST FOR DIMENSION LINE POSITION
      elif self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_MAIN_OPTIONS: # after waiting for a point or an option, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # then the command has been reactivated that returns here without the maptool
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
            if value == QadMsg.translate("Command_DIM", "Text") or value == "Text":
               prompt = QadMsg.translate("Command_DIM", "Enter dimension text <{0}>: ")
               dist = self.dimObj.radius
               self.waitForString(prompt.format(str(dist)), dist)
               self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.ASK_FOR_TEXT)
               self.step = QadDIMRADIUSCommandClassStepEnum.ASK_FOR_TEXT_VALUE
            elif value == QadMsg.translate("Command_DIM", "Angle") or value == "Angle":
               # prepares to wait for the rotation angle of the text
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                                   
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               prompt = QadMsg.translate("Command_DIM", "Specify angle of dimension text <{0}>: ")
               self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.dimStyle.textForcedRot)))
               self.GetAngleClass.angle = self.dimStyle.textForcedRot
               self.step = QadDIMRADIUSCommandClassStepEnum.ASK_FOR_TEXT_ROT
               self.GetAngleClass.run(msgMapTool, msg)
               
         elif type(value) == QgsPointXY: # if the dimension line positioning point has been entered
            self.addDimToLayers(value)
            return True # end command
            
         return False


      # =========================================================================
      # RESPONSE TO THE TEXT REQUEST (from step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_TEXT_VALUE: # after waiting for a string, restart the command
         if type(msg) == unicode:
            text = msg.strip()
            if len(text) > 0:
               self.measure = text
               self.getPointMapTool().measure = self.measure
         self.waitForDimensionLinePos()
            
         return False
      
      
      # =========================================================================
      # RESPONSE TO THE DIMENSION TEXT ROTATION REQUEST (from step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_TEXT_ROT:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
               self.dimStyle.textForcedRot = self.GetAngleClass.angle 
            self.waitForDimensionLinePos()

         return False
