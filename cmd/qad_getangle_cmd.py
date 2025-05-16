# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Command to be inserted in other commands for requesting an angle
 
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
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from ..qad_entity import QadEntity
from ..qad_getpoint import QadGetPointDrawModeEnum
from .. import qad_utils


# ===============================================================================
# QadGetAngleClass
# ===============================================================================
class QadGetAngleClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ Instantiates a new command of the same type """
      return QadGetAngleClass(self.plugIn)
      
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entity = QadEntity()
      self.startPt = None            
      self.msg = QadMsg.translate("QAD", "Specify angle: ")
      self.angle = None # in radians
      # Storing last point because the point(s) indicated by this function should not
      # alter lastpoint 
      self.__prevLastPoint = self.plugIn.lastPoint
            
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      # =========================================================================
      # REQUEST POINT or ENTITY
      if self.step == 0: # beginning of the command
         if self.startPt is not None:
            # Set the map tool
            self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
            self.getPointMapTool().setStartPoint(self.startPt)

         # Prepares to wait for a point or a real number         
         # msg, inputType, default, keyWords, non-null values
         self.waitFor(self.msg, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      self.angle, "", \
                      QadInputModeEnum.NOT_NULL)

         self.step = 1
         return False

      # =========================================================================
      # RESPONSE TO POINT REQUEST OR REAL NUMBER
      elif self.step == 1: # after waiting for a point, the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # The following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # so the command was reactivated and returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False
               
            value = self.getPointMapTool().point
         else: # the point or real number arrives as a parameter of the function
            value = msg

         if value is None:
            return True # end command
         
         if type(value) == float:
            self.angle = qad_utils.toRadians(value)
            return True # end command
         elif type(value) == QgsPointXY:
            # The point(s) indicated by this function should not alter lastpoint 
            self.plugIn.setLastPoint(self.__prevLastPoint)
            
            if self.startPt is not None:
               self.angle = qad_utils.getAngleBy2Pts(self.startPt, value)
               return True # end command
            else:            
               self.startPt = value            
               # Set the map tool
               self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
               self.getPointMapTool().setStartPoint(self.startPt)
               prompt = QadMsg.translate("QAD", "Specify second point: ")
               # Prepares to wait for a point
               self.waitForPoint(prompt)
               self.step = 2

         return False
         
      # =========================================================================
      # RESPONSE TO SECOND ANGLE POINT REQUEST (from step = 1)
      elif self.step == 2: # after waiting for a point, the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # The following condition occurs if during the selection of a point
            # another plugin was activated that deactivated Qad
            # so the command was reactivated and returns here without the maptool
            # having selected a point            
            if self.getPointMapTool().point is None: # the maptool was activated without a point
               if self.getPointMapTool().rightButton == True: # if the right mouse button was used
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                  return False

            value = self.getPointMapTool().point
         else: # the point arrives as a parameter of the function
            value = msg

         # The point(s) indicated by this function should not alter lastpoint 
         self.plugIn.setLastPoint(self.__prevLastPoint)
         
         if qad_utils.ptNear(self.startPt, value):
            self.showMsg(QadMsg.translate("QAD", "\nThe points must be different."))
            # Prepares to wait for a point
            self.waitForPoint(QadMsg.translate("QAD", "Specify second point: "))
            return False
         else:
            self.angle = qad_utils.getAngleBy2Pts(self.startPt, value)
            return True # end command
