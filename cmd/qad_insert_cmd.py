# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 INSERT command for inserting a symbol
 
                              -------------------
        last update          : 2025-05-17
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
from qgis.core import QgsGeometry, QgsFeature, QgsWkbTypes, QgsPointXY, QgsVectorLayerUtils
from qgis.PyQt.QtGui import QIcon


from .. import qad_utils
from .qad_generic_cmd import QadCommandClass
from .. import qad_layer
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_getdist_cmd import QadGetDistClass
from .qad_getangle_cmd import QadGetAngleClass
from ..qad_textwindow import QadInputModeEnum
from ..qad_msg import QadMsg
from ..qad_point import QadPoint


# Class that manages the INSERT command
class QadINSERTCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadINSERTCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "INSERT")

   def getEnglishName(self):
      return "INSERT"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runINSERTCommand)
   
   def getIcon(self):
      return QIcon(":/plugins/qad/icons/insert.svg")

   def getNote(self):
      # set the explanatory notes for the command
      return QadMsg.translate("Command_INSERT", "Insert a symbol.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.insPt = None
      self.scale = self.plugIn.lastScale
      self.rot = self.plugIn.lastRot
      self.GetDistClass = None
      self.GetAngleClass = None

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.GetDistClass is not None:
         del self.GetDistClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      # when requesting distance (scale)
      if self.step == 2:
         return self.GetDistClass.getPointMapTool()
      # when requesting rotation
      elif self.step == 3:
         return self.GetAngleClass.getPointMapTool()
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      # when requesting distance (scale)
      if self.step == 2:
         return self.GetDistClass.getCurrentContextualMenu()
      # when requesting rotation
      elif self.step == 3:
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu
       def addFeature(self, layer):
     pt = QadPoint(self.insPt)
     g = self.mapToLayerCoordinates(layer, pt.asGeom(layer.wkbType()))
     f = QgsVectorLayerUtils.createFeature(layer, g, {}, layer.createExpressionContext())
     # f = QgsFeature()
     #f.setGeometry(g)
     # Add attribute fields to feature.
     #fields = layer.fields()
     #f.setFields(fields)
     
     # # assign default values
     # provider = layer.dataProvider()
     # for field in fields.toList():
     #    i = fields.indexFromName(field.name())
     #    f[field.name()] = provider.defaultValue(i)
     
     
     # if scale depends on a field
     scaleFldName = qad_layer.get_symbolScaleFieldName(layer)
     if len(scaleFldName) > 0:
        f.setAttribute(scaleFldName, self.scale)
     
     # if rotation depends on a field
     rotFldName = qad_layer.get_symbolRotationFieldName(layer)
     if len(rotFldName) > 0:
        f.setAttribute(rotFldName, qad_utils.toDegrees(self.rot))
     
     return qad_layer.addFeatureToLayer(self.plugIn, layer, f)               
     
     
  def run(self, msgMapTool = False, msg = None):
     if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
        self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
        return True # end command
     
     currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.PointGeometry)
     if currLayer is None:
        self.showErr(errMsg)
        return True # end command

     if qad_layer.isSymbolLayer(currLayer) == False:
        errMsg = QadMsg.translate("QAD", "\nCurrent layer is not a symbol layer.")
        errMsg = errMsg + QadMsg.translate("QAD", "\nA symbol layer is a vector punctual layer without label.\n")
        self.showErr(errMsg)         
        return True # end command

              
     # =========================================================================
     # REQUEST FOR INSERTION POINT
     if self.step == 0: # start of the command
        self.waitForPoint() # prepares to wait for a point
        self.step = self.step + 1
        return False
     
     # =========================================================================
     # RESPONSE TO THE REQUEST FOR INSERTION POINT
     elif self.step == 1: # after waiting for a point, the command restarts
        if msgMapTool == True: # the point comes from a graphic selection
           # the following condition occurs if during the selection of a point
           # another plugin has been activated that has deactivated Qad
           # then reactivated the command that returns here without the maptool
           # having selected a point            
           if self.getPointMapTool().point is None: # the maptool has been activated without a point
              if self.getPointMapTool().rightButton == True: # if right mouse button used
                 return True # end command
              else:
                 self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                 return False

           pt = self.getPointMapTool().point
        else: # the point comes as a parameter of the function
           pt = msg

        self.insPt = QgsPointXY(pt)
        self.plugIn.setLastPoint(self.insPt)
        
        # if scale depends on a field
        scaleFldName = qad_layer.get_symbolScaleFieldName(currLayer)
        if len(scaleFldName) > 0:
           # prepares to wait for the scale                      
           self.GetDistClass = QadGetDistClass(self.plugIn)
           prompt = QadMsg.translate("Command_INSERT", "Specify the symbol scale <{0}>: ")
           self.GetDistClass.msg = prompt.format(str(self.scale))
           self.GetDistClass.dist = self.scale
           self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE | QadInputModeEnum.NOT_ZERO
           self.GetDistClass.startPt = self.insPt
           self.step = 2
           self.GetDistClass.run(msgMapTool, msg)
           return False
        else: 
           # if rotation depends on a field
           rotFldName = qad_layer.get_symbolRotationFieldName(currLayer)
           if len(rotFldName) > 0:
              if self.GetAngleClass is not None:
                 del self.GetAngleClass                  
              # prepares to wait for the rotation angle                     
              self.GetAngleClass = QadGetAngleClass(self.plugIn)
              prompt = QadMsg.translate("Command_INSERT", "Specify the symbol rotation <{0}>: ")
              self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.rot)))
              self.GetAngleClass.angle = self.rot
              self.GetAngleClass.startPt = self.insPt               
              self.step = 3
              self.GetAngleClass.run(msgMapTool, msg)               
              return False
           else:
              self.addFeature(currLayer)

        return True
     
     # =========================================================================
     # RESPONSE TO THE SCALE REQUEST (from step = 1)
     elif self.step == 2:
        if self.GetDistClass.run(msgMapTool, msg) == True:
           if self.GetDistClass.dist is not None:
              self.scale = self.GetDistClass.dist
              self.plugIn.setLastScale(self.scale)
              del self.GetDistClass
              self.GetDistClass = None
               
              # if rotation depends on a field
              rotFldName = qad_layer.get_symbolRotationFieldName(currLayer)
              if len(rotFldName) > 0:
                 if self.GetAngleClass is not None:
                    del self.GetAngleClass                  
                 # prepares to wait for the rotation angle                      
                 self.GetAngleClass = QadGetAngleClass(self.plugIn)
                 prompt = QadMsg.translate("Command_INSERT", "Specify the symbol rotation <{0}>: ")
                 self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.rot)))
                 self.GetAngleClass.angle = self.rot
                 self.GetAngleClass.startPt = self.insPt               
                 self.step = 3
                 self.GetAngleClass.run(msgMapTool, msg)         
                 return False
              else:
                 self.addFeature(currLayer)               
                 return True   
           else:
              return True   
        return False
     
     # =========================================================================
     # RESPONSE TO THE ROTATION REQUEST (from step = 1 or 2)
     elif self.step == 3:
        if self.GetAngleClass.run(msgMapTool, msg) == True:
           if self.GetAngleClass.angle is not None:
              self.rot = self.GetAngleClass.angle
              self.plugIn.setLastRot(self.rot)
              self.addFeature(currLayer)
              return True # end command
           else:
              return True
        return False
