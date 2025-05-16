# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Command to be inserted in other commands for requesting a distance
 
                              -------------------
        begin                : 2025-05-15
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
from qgis.core import QgsPointXY


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputModeEnum, QadInputTypeEnum
from ..qad_getpoint import QadGetPointDrawModeEnum
from .. import qad_utils
from ..qad_entity import QadEntity


# ===============================================================================
# QadGetDistClass
# ===============================================================================
class QadGetDistClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ Instantiates a new command of the same type """
      return QadGetDistClass(self.plugIn)
      
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entity = QadEntity()
      self.startPt = None            
      self.msg = QadMsg.translate("QAD", "Specify the distance: ")
      self.dist = None
      self.inputMode = QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE
      self.ctrlKey = False

      # Store last point because the point(s) indicated by this function should not
      # alter lastpoint 
      self.__prevLastPoint = self.plugIn.lastPoint
            
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      # =========================================================================
      # REQUEST POINT or ENTITY
      if self.step == 0: # beginning of the command
         # prepares to wait for a point or a real number         
         # msg, inputType, default, keyWords, positive values
         self.waitFor(self.msg, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      self.dist, "", \
                      QadInputModeEnum.NOT_NULL | self.inputMode)
         
         if self.startPt is not None:            
            # set the map tool
            self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
            self.getPointMapTool().setStartPoint(self.startPt)

         self.step = 1
         return False

      # =========================================================================
      # RESPONSE TO POINT REQUEST or real number
      elif self.step == 1: # after waiting for a point, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin has been activated that has deactivated Qad
            # then reactivated the command that returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool has been activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False
               
            value = self.getPointMapTool().point
            self.ctrlKey = self.getPointMapTool().ctrlKey
         else: # the point or the real number comes as a parameter of the function
            value = msg

         if value is None:
            return True # end command
         
         if type(value) == float:
            self.dist = value
            return True # end command
         elif type(value) == QgsPointXY:
            # the point(s) indicated by this function should not alter lastpoint 
            self.plugIn.setLastPoint(self.__prevLastPoint)

            if self.startPt is not None:
               self.dist = qad_utils.getDistance(self.startPt, value)
               return True # end command
            else:
               self.startPt = value            
               # set the map tool
               self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
               self.getPointMapTool().setStartPoint(self.startPt)
               
               # prepares to wait for a point
               self.waitForPoint(QadMsg.translate("QAD", "Specify second point: "))
                              
               self.step = 2

         return False
         
      # =========================================================================
      # RESPONSE TO REQUEST FOR SECOND POINT OF DISTANCE (from step = 1)
      elif self.step == 2: # after waiting for a point, restart the command
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if during the selection of a point
            # another plugin has been activated that has deactivated Qad
            # then reactivated the command that returns here without the maptool
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

         # the point(s) indicated by this function should not alter lastpoint 
         self.plugIn.setLastPoint(self.__prevLastPoint)

         self.dist = qad_utils.getDistance(self.startPt, value)
         return True # end command
