# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin OK

 ARC command to draw an arc
 
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


# Import the PyQt and QGIS libraries
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsWkbTypes, QgsGeometry, QgsPointXY
import math


from ..qad_arc import QadArc
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_arc_maptool import Qad_arc_maptool, Qad_arc_maptool_ModeEnum, \
                              Qad_gripChangeArcRadius_maptool, Qad_gripChangeArcRadius_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .. import qad_utils
from .. import qad_layer 
from ..qad_grip import QadGripStatusEnum
from ..qad_dim import QadDimStyles


# Class that manages the ARC command
class QadARCCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadARCCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "ARC")

   def getEnglishName(self):
      return "ARC"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runARCCommand)
   
   def getIcon(self):
      return QIcon(":/plugins/qad/icons/arc.svg")

   def getNote(self):
      # set the explanatory notes of the command      
      return QadMsg.translate("Command_ARC", "Draws an arc by many methods.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.vertices = []

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_arc_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None
         
   def run(self, msgMapTool = False, msg = None):
      self.isValidPreviousInput = True # to manage the command also in macro
           
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command
      
      currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.LineGeometry)
      if currLayer is None:
         self.showErr(errMsg)
         return True # end command

      # =========================================================================
      # REQUEST FIRST POINT or CENTER
      if self.step == 0: # beginning of the command
         # set the map tool
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_START_PT)
         keyWords = QadMsg.translate("Command_ARC", "Center")
         
         prompt = QadMsg.translate("Command_ARC", "Specify the start point of the arc or [{0}]:").format(keyWords)                 
         
         englishKeyWords = "Center"
         keyWords += "_" + englishKeyWords
         # prepares to wait for a point or enter or a keyword         
         # msg, inputType, default, keyWords, no mode check
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NONE)         
         self.step = 1
         
         return False

      # =========================================================================
      # RESPONSE TO REQUEST FIRST POINT or CENTER
      elif self.step == 1: # after waiting for a point or enter or a keyword, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
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

         if type(value) == QgsPointXY: # if the initial point of the arc has been entered           
            self.startPt = value
            self.plugIn.setLastPoint(value)
            
            # set the map tool
            self.getPointMapTool().arcStartPt = self.startPt
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_SECOND_PT)
                                
            keyWords = QadMsg.translate("Command_ARC", "Center") + "/" + \
                       QadMsg.translate("Command_ARC", "End")
            
            prompt = QadMsg.translate("Command_ARC", "Specify second point of the arc or [{0}]:").format(keyWords)                 
            
            englishKeyWords = "Center" + "/" + "End"
            keyWords += "_" + englishKeyWords
            # prepares to wait for a point or a keyword         
            # msg, inputType, default, keyWords
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                         None, \
                         keyWords, QadInputModeEnum.NONE)
            
            self.step = 2
            return False
         else: # you want to enter the center of the arc
            # set the map tool
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT)
            # prepares to wait for a point
            self.waitForPoint(QadMsg.translate("Command_ARC", "Specify the center of the arc: "))
            
            self.step = 13
            return False

      # =========================================================================
      # RESPONSE TO REQUEST SECOND POINT or CENTER or END
      elif self.step == 2: # after waiting for a point or a keyword, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ARC", "Center") or value == "Center":
               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_CENTER_PT)
               # prepares to wait for a point
               self.waitForPoint(QadMsg.translate("Command_ARC", "Specify the center of the arc: "))
               self.step = 4           
            elif value == QadMsg.translate("Command_ARC", "End") or value == "End":
               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_END_PT)
               # prepares to wait for a point
               self.waitForPoint(QadMsg.translate("Command_ARC", "Specify the final point of the arc: "))
               self.step = 8     
         elif type(value) == QgsPointXY: # if the second point of the arc has been entered            
            self.secondPt = value
            # set the map tool
            self.getPointMapTool().arcSecondPt = self.secondPt
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_SECOND_PT_KNOWN_ASK_FOR_END_PT)

            # prepares to wait for a point
            self.waitForPoint(QadMsg.translate("Command_ARC", "Specify the final point of the arc: "))
            self.step = 3
                  
         return False

      # =========================================================================
      # RESPONSE TO REQUEST FINAL POINT OF THE ARC (from step = 2)
      elif self.step == 3: # after waiting for a point, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         self.endPt = value
         
         arc = QadArc()         
         if arc.fromStartSecondEndPts(self.startPt, self.secondPt, self.endPt) == True:
            self.plugIn.setLastPoint(arc.getEndPt())
            geom = arc.asGeom(currLayer.wkbType())
            if geom is not None:
               # if the points are so close to be considered equal
               if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
               else:
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                  
               self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
               
               qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command
      
         # prepares to wait for a point
         self.waitForPoint(QadMsg.translate("Command_ARC", "Specify the final point of the arc: "))
         self.isValidPreviousInput = False # to manage the command also in macro     
         return False
      
      # =========================================================================
      # RESPONSE TO REQUEST CENTER OF THE ARC (from step = 2)
      elif self.step == 4: # after waiting for a point, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False
               
            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         self.centerPt = value
         self.plugIn.setLastPoint(value)
         
         # set the map tool
         self.getPointMapTool().arcCenterPt = self.centerPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_END_PT)
         
         keyWords = QadMsg.translate("Command_ARC", "Angle") + "/" + \
                    QadMsg.translate("Command_ARC", "chord Length")
                             
         prompt = QadMsg.translate("Command_ARC", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)                 
                         
         englishKeyWords = "Angle" + "/" + "chord Length"
         keyWords += "_" + englishKeyWords
         # prepares to wait for a point or a keyword         
         # msg, inputType, default, keyWords, null values not allowed
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NOT_NULL)
         
         self.step = 5
         return False
      
      # =========================================================================
      # RESPONSE TO REQUEST "Specify final point of the arc or [Angle/chord Length]: " (from step = 4)
      elif self.step == 5: # after waiting for a point or a keyword, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the point comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if type(value) == unicode:  
            if value == QadMsg.translate("Command_ARC", "Angle") or value == "Angle":
               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_ANGLE)
               # prepares to wait for a point or a real number         
               # msg, inputType, default, keyWords, null values not allowed
               self.waitFor(QadMsg.translate("Command_ARC", "Specify the included angle (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
               self.step = 6
               return False                              
            elif value == QadMsg.translate("Command_ARC", "chord Length") or value == "chord Length":
               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_CHORD)
               # prepares to wait for a point or a real number         
               # msg, inputType, default, keyWords, positive values
               self.waitFor(QadMsg.translate("Command_ARC", "Specify the chord length (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 7
               return False                              
         elif type(value) == QgsPointXY: # if the end point of the arc has been entered
            self.endPt = value
                     
            arc = QadArc()
            if arc.fromStartCenterEndPts(self.startPt, self.centerPt, self.endPt) == True:
               if ctrlPressed: # invert initial-final angle
                  arc.inverseAngles()
               
               self.plugIn.setLastPoint(arc.getEndPt())

               geom = arc.asGeom(currLayer.wkbType())
               if geom is not None:
                  # if the points are so close to be considered equal
                  if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                     self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
                  else:
                     self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                     
                  self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
                  
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # end command
                           
            keyWords = QadMsg.translate("Command_ARC", "Angle") + "/" + \
                       QadMsg.translate("Command_ARC", "chord Length")
            prompt = QadMsg.translate("Command_ARC", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)

            englishKeyWords = "Angle" + "/" + "chord Length"
            keyWords += "_" + englishKeyWords
            # prepares to wait for a point or a keyword         
            # msg, inputType, default, keyWords, null values not allowed
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                         None, \
                         keyWords, QadInputModeEnum.NOT_NULL)
            self.isValidPreviousInput = False # to manage the command also in macro
            return False
      
      # =========================================================================
      # RESPONSE TO REQUEST "Specify included angle: " (from step = 5)
      elif self.step == 6: # after waiting for a point or a real number, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the point comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.angle = qad_utils.getAngleBy2Pts(self.centerPt, value)             
         else:
            self.angle = value

         arc = QadArc()         
         if arc.fromStartCenterPtsAngle(self.startPt, self.centerPt, self.angle) == True:
            if ctrlPressed: # invert initial-final angle
               arc.inverseAngles()
               
            self.plugIn.setLastPoint(arc.getEndPt())
            geom = arc.asGeom(currLayer.wkbType())
            if geom is not None:
               # if the points are so close to be considered equal
               if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
               else:
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                  
               self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
               
               qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command
            
         # prepares to wait for a point or a real number         
         # msg, inputType, default, keyWords, null values not allowed
         self.waitFor(QadMsg.translate("Command_ARC", "Specify the included angle (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
         self.isValidPreviousInput = False # to manage the command also in macro         
         return False

      
      # =========================================================================
      # RESPONSE TO REQUEST "Specify chord length: " (from step = 5)
      elif self.step == 7: # after waiting for a point or a real number, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the point comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.chord = qad_utils.getDistance(self.startPt, value)             
         else:
            self.chord = value

         arc = QadArc()         
         if arc.fromStartCenterPtsChord(self.startPt, self.centerPt, self.chord) == True:
            if ctrlPressed: # invert initial-final angle
               arc.inverseAngles()

            self.plugIn.setLastPoint(arc.getEndPt())
            geom = arc.asGeom(currLayer.wkbType())
            if geom is not None:
               # if the points are so close to be considered equal
               if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
               else:
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                  
               self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
               
               qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command

         # prepares to wait for a point or a real number         
         # msg, inputType, default, keyWords, positive values allowed
         self.waitFor(QadMsg.translate("Command_ARC", "Specify the chord length (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      None, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
         self.isValidPreviousInput = False # to manage the command also in macro         
         return False
                 
      # =========================================================================
      # RESPONSE TO REQUEST "Specify final point of the arc: " (from step = 1)
      elif self.step == 8: # after waiting for a point, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         self.endPt = value
         self.plugIn.setLastPoint(self.endPt)

         # set the map tool
         self.getPointMapTool().arcEndPt = self.endPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_CENTER)
      
         keyWords = QadMsg.translate("Command_ARC", "Angle") + "/" + \
                    QadMsg.translate("Command_ARC", "Direction") + "/" + \
                    QadMsg.translate("Command_ARC", "Radius")
                    
         prompt = QadMsg.translate("Command_ARC", "Specify the center point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)

         englishKeyWords = "Angle" + "/" + "Direction" + "/" + "Radius"
         keyWords += "_" + englishKeyWords
         # prepares to wait for a point or a keyword         
         # msg, inputType, default, keyWords, null values not allowed
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NOT_NULL)
         
         self.step = 9
         return False
         
      # =========================================================================
      # RESPONSE TO REQUEST "Specify center of the arc or [Angle/Direction/Radius]: " (from step = 8)
      elif self.step == 9: # after waiting for a point or a keyword, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the point comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ARC", "Angle") or value == "Angle":
               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_RADIUS)
               # prepares to wait for a point or a real number         
               # msg, inputType, default, keyWords, isNullable
               self.waitFor(QadMsg.translate("Command_ARC", "Specify the radius of the arc (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 12
               return False                              
         elif type(value) == QgsPointXY: # if the center of the arc has been entered
            self.centerPt = value

            arc = QadArc()         
            if arc.fromStartCenterEndPts(self.startPt, self.centerPt, self.endPt) == True:
               if ctrlPressed: # invert initial-final angle
                  arc.inverseAngles()
                  
               self.plugIn.setLastPoint(arc.getEndPt())
               geom = arc.asGeom(currLayer.wkbType())
               if geom is not None:
                  # if the points are so close to be considered equal
                  if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                     self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
                  else:
                     self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                     
                  self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
                  
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # end command
                           
            keyWords = QadMsg.translate("Command_ARC", "Angle") + "/" + \
                       QadMsg.translate("Command_ARC", "Direction") + "/" + \
                       QadMsg.translate("Command_ARC", "Radius")
                       
            prompt = QadMsg.translate("Command_ARC", "Specify the center point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)
                      
            englishKeyWords = "Angle" + "/" + "Direction" + "/" + "Radius"
            keyWords += "_" + englishKeyWords
            # prepares to wait for a point or a keyword         
            # msg, inputType, default, keyWords, isNullable
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                         None, \
                         keyWords, QadInputModeEnum.NOT_NULL)
            self.isValidPreviousInput = False # to manage the command also in macro                     
            return False
      
      # =========================================================================
      # RESPONSE TO REQUEST "Specify included angle: " (from step = 9)
      elif self.step == 10: # after waiting for a point or a real number, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the point comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.angle = qad_utils.getAngleBy2Pts(self.startPt, value)
         else:
            self.angle = value
            
         arc = QadArc()         
         if arc.fromStartEndPtsAngle(self.startPt, self.endPt, self.angle) == True:
            if ctrlPressed: # invert initial-final angle
               arc.inverseAngles()
               
            self.plugIn.setLastPoint(arc.getEndPt())
            geom = arc.asGeom(currLayer.wkbType())
            if geom is not None:
               # if the points are so close to be considered equal
               if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
               else:
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                  
               self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
               
               qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command

         # prepares to wait for a point or a real number         
         # msg, inputType, default, keyWords, null values not allowed
         self.waitFor(QadMsg.translate("Command_ARC", "Specify the included angle (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
         self.isValidPreviousInput = False # to manage the command also in macro         
         return False
      
      # =========================================================================
      # RESPONSE TO REQUEST "Specify tangent direction for the start point of the arc: " (from step = 9)
      elif self.step == 11: # after waiting for a point or a real number, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the point comes as a parameter of the function
            value = msg
            ctrlPressed = False
            
         if type(value) == QgsPointXY:
            self.angleTan = qad_utils.getAngleBy2Pts(self.startPt, value)             
         else:
            self.angleTan = value

         arc = QadArc()         
         if arc.fromStartEndPtsTan(self.startPt, self.endPt, self.angleTan) == True:
            if ctrlPressed: # invert initial-final angle
               arc.inverseAngles()
               
            self.plugIn.setLastPoint(arc.getEndPt())
            geom = arc.asGeom(currLayer.wkbType())
            if geom is not None:
               # if the points are so close to be considered equal
               if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
               else:
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                  
               self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
               
               qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command

         # prepares to wait for a point or a real number         
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(QadMsg.translate("Command_ARC", "Specify the tangent direction for the start point of the arc (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", QadInputModeEnum.NOT_NULL)
         self.isValidPreviousInput = False # to manage the command also in macro
         return False


      # =========================================================================
      # RESPONSE TO REQUEST "Specify radius of the arc: " (from step = 9)
      elif self.step == 12: # after waiting for a point or a real number, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the point comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.radius = qad_utils.getDistance(self.endPt, value)             
         else:
            self.radius = value

         self.plugIn.setLastRadius(self.radius)
         
         arc = QadArc()
         if arc.fromStartEndPtsRadius(self.startPt, self.endPt, self.radius) == True:
            if ctrlPressed: # invert initial-final angle
               arc.inverseAngles()
               
            self.plugIn.setLastPoint(arc.getEndPt())
            geom = arc.asGeom(currLayer.wkbType())
            if geom is not None:
               # if the points are so close to be considered equal
               if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
               else:
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                  
               self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
               
               qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command

         # prepares to wait for a point or a real number         
         # msg, inputType, default, keyWords, positive values
         self.waitFor(QadMsg.translate("Command_ARC", "Specify the radius of the arc (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      None, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
         self.isValidPreviousInput = False # to manage the command also in macro
         return False


      # ========================================================================
      # RESPONSE TO REQUEST CENTER OF THE ARC (from step = 1)
      elif self.step == 13: # after waiting for a point, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         self.centerPt = value
         self.plugIn.setLastPoint(value)

         # set the map tool
         self.getPointMapTool().arcCenterPt = self.centerPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_START_PT)

         # prepares to wait for a point
         self.waitForPoint(QadMsg.translate("Command_ARC", "Specify the start point of the arc: "))
         self.step = 14
         
         return False


      # =========================================================================
      # RESPONSE TO REQUEST START POINT OF THE ARC (from step = 13)
      elif self.step == 14: # after waiting for a point, the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         self.startPt = value
         self.plugIn.setLastPoint(value)

         # set the map tool
         self.getPointMapTool().arcStartPt = self.startPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_END_PT)
         
         keyWords = QadMsg.translate("Command_ARC", "Angle") + "/" + \
                    QadMsg.translate("Command_ARC", "chord Length")
         
         prompt = QadMsg.translate("Command_ARC", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)
                           
         englishKeyWords = "Angle" + "/" + "chord Length"
         keyWords += "_" + englishKeyWords
         # prepares to wait for a point or a keyword         
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NOT_NULL)
         
         self.step = 5
         return False


# ============================================================================
# Class that manages the command to change the radius of an arc for grips
# ============================================================================
class QadGRIPCHANGEARCRADIUSCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadGRIPCHANGEARCRADIUSCommandClass(self.plugIn)

   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entity = None
      self.skipToNextGripCommand = False
      self.copyEntities = False
      self.basePt = QgsPointXY()
      self.nOperationsToUndo = 0

   
   def __del__(self):
      QadCommandClass.__del__(self)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_gripChangeArcRadius_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None

   
   # ============================================================================
   # setSelectedEntityGripPoints
   # ============================================================================
   def setSelectedEntityGripPoints(self, entitySetGripPoints):
      # list of entityGripPoint with selected grip points
      # sets the first entity with a selected grip
      self.entity = None
      for entityGripPoints in entitySetGripPoints.entityGripPoints:
         for gripPoint in entityGripPoints.gripPoints:
            # selected grip point
            if gripPoint.getStatus() == QadGripStatusEnum.SELECTED:
               # check if the entity belongs to a dimension style
               if QadDimStyles.isDimEntity(entityGripPoints.entity):
                  return False
               if entityGripPoints.entity.getQadGeom().whatIs() != "ARC":
                  return False
               
               self.entity = entityGripPoints.entity
               arc = entityGripPoints.entity.getQadGeom() # arc in map coordinate
               self.basePt.set(arc.center.x(), arc.center.y())
               return True
      return False
   

   # ============================================================================
   # changeRadius
   # ============================================================================
   def changeRadius(self, radius):
      # radius = new radius of the arc
      if radius <= 0:
         return False
      arc = self.entity.getQadGeom()
      arc.radius = radius
      points = arc.asPolyline()
      if points is None:
         return False
      
      g = QgsGeometry.fromPolylineXY(points)
      f = self.entity.getFeature()      
      f.setGeometry(g)
      
      self.plugIn.beginEditCommand("Feature stretched", [self.entity.layer])
      
      if self.copyEntities == False:
         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, self.entity.layer, f, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False
      else:
         # plugIn, layer, features, coordTransform, refresh, check_validity
         if qad_layer.addFeatureToLayer(self.plugIn, self.entity.layer, f, None, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False

      self.plugIn.setLastRadius(radius)
      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1

      return True


   # ============================================================================
   # waitForRadius
   # ============================================================================
   def waitForRadius(self):
      keyWords = QadMsg.translate("Command_GRIP", "Base point") + "/" + \
                 QadMsg.translate("Command_GRIP", "Copy") + "/" + \
                 QadMsg.translate("Command_GRIP", "Undo") + "/" + \
                 QadMsg.translate("Command_GRIP", "eXit")
      prompt = QadMsg.translate("Command_GRIPCHANGEARCRADIUS", "Specify the radius or [{0}]: ").format(keyWords)

      englishKeyWords = "Base point" + "/" + "Copy" + "/" + "Undo" + "/" "eXit"
      keyWords += "_" + englishKeyWords
      # prepares to wait for a point or enter or a keyword
      # msg, inputType, default, keyWords, positive values
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
      self.step = 1
      # set the map tool
      self.getPointMapTool().setEntity(self.entity) # sets basePt in the center of the arc
      self.getPointMapTool().basePt = self.basePt
      self.getPointMapTool().setMode(Qad_gripChangeArcRadius_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_RADIUS_PT)


   # ============================================================================
   # waitForBasePt
   # ============================================================================
   def waitForBasePt(self):
      self.step = 2   
      # set the map tool
      self.getPointMapTool().setMode(Qad_gripChangeArcRadius_maptool_ModeEnum.ASK_FOR_BASE_PT)

      # prepares to wait for a point
      self.waitForPoint(QadMsg.translate("Command_GRIP", "Specify base point: "))


   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command
     
      # =========================================================================
      # OBJECTS SELECTION REQUEST
      if self.step == 0: # beginning of the command
         if self.entity is None: # no objects to stretch
            return True
         self.showMsg(QadMsg.translate("Command_GRIPCHANGEARCRADIUS", "\n** RADIUS **\n"))
         # prepares to wait for radius
         self.waitForRadius()
         return False
      
      # =========================================================================
      # RESPONSE TO THE REQUEST OF THE RADIUS OF FILLET (from step = 1)
      elif self.step == 1:
         ctrlKey = False
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  if self.copyEntities == False:
                     self.skipToNextGripCommand = True
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
            ctrlKey = self.getPointMapTool().ctrlKey
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_GRIP", "Base point") or value == "Base point":
               # prepares to wait for the base point
               self.waitForBasePt()
            elif value == QadMsg.translate("Command_GRIP", "Copy") or value == "Copy":
               # Copy entities leaving the originals unchanged
               self.copyEntities = True                     
               # prepares to wait for radius
               self.waitForRadius()
            elif value == QadMsg.translate("Command_GRIP", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0: 
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))                  
               # prepares to wait for radius
               self.waitForRadius()
            elif value == QadMsg.translate("Command_GRIP", "eXit") or value == "eXit":
               return True # end command
         elif type(value) == QgsPointXY or type(value) == float: # if the radius has been entered
            if type(value) == QgsPointXY: # if the radius has been entered with a point
               if value == self.basePt:
                  self.showMsg(QadMsg.translate("QAD", "\nThe value must be positive and not zero."))
                  # prepares to wait for radius
                  self.waitForRadius()
                  return False
                                      
               radius = qad_utils.getDistance(self.basePt, value)
            else:
               radius = value

            if ctrlKey:
               self.copyEntities = True
   
            self.changeRadius(radius)

            if self.copyEntities == False:
               return True
            # prepares to wait for radius
            self.waitForRadius()
         else:
            if self.copyEntities == False:
               self.skipToNextGripCommand = True
            return True # end command

         return False
              
      # =========================================================================
      # RESPONSE TO THE BASE POINT REQUEST (from step = 1)
      elif self.step == 2: # after waiting for a point
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  pass # default option
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY: # if the base point has been entered
            self.basePt.set(value.x(), value.y())
            # set the map tool
            self.getPointMapTool().basePt = self.basePt
            
         # prepares to wait for radius
         self.waitForRadius()

         return FalseANGLE)
               # prepares to wait for a point or a real number         
               # msg, inputType, default, keyWords, isNullable
               self.waitFor(QadMsg.translate("Command_ARC", "Specify the included angle (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
               self.step = 10
               return False                              
            elif value == QadMsg.translate("Command_ARC", "Direction") or value == "Direction":
               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_TAN)
               # prepares to wait for a point or a real number         
               # msg, inputType, default, keyWords, isNullable
               self.waitFor(QadMsg.translate("Command_ARC", "Specify the tangent direction for the start point of the arc (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", QadInputModeEnum.NOT_NULL)
               self.step = 11
               return False     
