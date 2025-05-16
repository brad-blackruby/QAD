# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 CIRCLE command for drawing a circle
 
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


# Import the PyQt and QGIS libraries
from qgis.core import QgsWkbTypes, QgsPointXY, QgsGeometry
from qgis.PyQt.QtGui import QIcon


from .. import qad_layer
from .. import qad_utils
from .qad_circle_maptool import Qad_circle_maptool, Qad_circle_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputModeEnum, QadInputTypeEnum
from ..qad_geom_relations import *
from ..qad_multi_geom import *
from ..qad_circle_fun import *
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_snapper import QadSnapTypeEnum


# Class that manages the CIRCLE command
class QadCIRCLECommandClass(QadCommandClass):
   
   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadCIRCLECommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "CIRCLE")

   def getEnglishName(self):
      return "CIRCLE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runCIRCLECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/circle.svg")

   def getNote(self):
      # set the explanatory notes for the command
      return QadMsg.translate("Command_CIRCLE", "Draws a circle by many methods.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # if this flag = True the command is used within another command to draw a circle
      # that will not be saved to a layer
      self.virtualCmd = False
      self.rubberBandBorderColor = None
      self.rubberBandFillColor = None
      self.centerPt = None
      self.radius = None
      self.area = 100      

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_circle_maptool(self.plugIn)
            self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)
         return self.PointMapTool
      else:
         return None
   
   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      self.rubberBandBorderColor = rubberBandBorderColor
      self.rubberBandFillColor = rubberBandFillColor
      if self.PointMapTool is not None:
         self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)
         
   def run(self, msgMapTool = False, msg = None):
      self.isValidPreviousInput = True # to handle the command also in macro

      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      currLayer = None
      if self.virtualCmd == False: # if we really want to save the circle in a layer   
         # current layer must be editable and of line or polygon type
         currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry])
         if currLayer is None:
            self.showErr(errMsg)
            return True # end command
         self.getPointMapTool().layer = currLayer

      # =========================================================================
      # REQUEST FIRST POINT or CENTER
      if self.step == 0: # beginning of the command
         # set the map tool
         self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT)
         keyWords = QadMsg.translate("Command_CIRCLE", "3Points") + "/" + \
                    QadMsg.translate("Command_CIRCLE", "2POints") + "/" + \
                    QadMsg.translate("Command_CIRCLE", "Ttr (tangent tangent radius)")
         prompt = QadMsg.translate("Command_CIRCLE", "Specify the center point of the circle or [{0}]: ").format(keyWords)

         englishKeyWords = "3Points" + "/" + "2POints" + "/" + "Ttr (tangent tangent radius)"
         keyWords += "_" + englishKeyWords
         # it prepares to wait for a point or enter or a keyword         
         # msg, inputType, default, keyWords, no check
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NONE)
         
         self.step = 1
         return False

      # =========================================================================
      # RESPONSE TO CENTER REQUEST
      elif self.step == 1: # after waiting for a point or enter or a keyword, the command is restarted
         if msgMapTool == True: # the point comes from a graphical selection
            # the following condition occurs if during the selection of a point
            # another plugin has been activated that has deactivated Qad
            # then the command has been reactivated that returns here without the
            # maptool having selected a point
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if using the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point arrives as a parameter of the function
            value = msg

         if value is None:
            if self.plugIn.lastPoint is not None:
               value = self.plugIn.lastPoint
            else:
               return True # end command

         if type(value) == str:
            if value == QadMsg.translate("Command_CIRCLE", "3Points") or value == "3Points":
               # set the map tool
               self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)
               # it prepares to wait for a point
               self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first point on the circle: "))
               self.step = 4           
            elif value == QadMsg.translate("Command_CIRCLE", "2POints") or value == "2POints":
               # set the map tool
               self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_DIAM_PT)
               # it prepares to wait for a point
               self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first end of the circle diameter: "))
               self.step = 7     
            elif value == QadMsg.translate("Command_CIRCLE", "Ttr (tangent tangent radius)") or \
                 value == "Ttr (tangent tangent radius)":
               # set the map tool
               self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_TAN)
               # it prepares to wait for a point
               self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first tangent element of the circle: "))
               self.step = 9     
         elif type(value) == QgsPointXY: # if the center of the circle has been entered           
            self.centerPt = value
            self.plugIn.setLastPoint(value)
            
            # set the map tool
            self.getPointMapTool().centerPt = self.centerPt
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_RADIUS)                                
           
            keyWords = QadMsg.translate("Command_CIRCLE", "Diameter") + "/" + \
                       QadMsg.translate("Command_CIRCLE", "Area")
            prompt = QadMsg.translate("Command_CIRCLE", "Specify the circle radius or [{0}]: ").format(keyWords)
            
            englishKeyWords = "Diameter" + "/" + "Area"
            keyWords += "_" + englishKeyWords
            # it prepares to wait for a point or a keyword         
            # msg, inputType, default, keyWords, positive values
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                         None, \
                         keyWords, \
                         QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
            
            self.step = 2
         
         return False
