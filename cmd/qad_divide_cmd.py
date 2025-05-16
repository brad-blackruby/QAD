# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 DIVIDE command to create point objects at equal distances along the perimeter or length of an object
 
                              -------------------
        last update          : 2025-05-15
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
from qgis.core import QgsGeometry, QgsFeature, QgsWkbTypes, QgsVectorLayerUtils
from qgis.PyQt.QtGui import QIcon


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from .qad_entsel_cmd import QadEntSelClass
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .. import qad_utils
from .. import qad_layer
from ..qad_dim import QadDimStyles
from ..qad_multi_geom import getQadGeomAt
from ..qad_geom_relations import getQadGeomClosestPart


# ===============================================================================
# QadDIVIDECommandClassStepEnum class.
# ===============================================================================
class QadDIVIDECommandClassStepEnum():
   ASK_FOR_ENT        = 1 # requests the selection of an object (0 is the start of the command)
   ASK_FOR_ALIGNMENT  = 2 # requests alignment
   ASK_SEGMENT_NUMBER = 3 # requests the number of segments
   

# Class that manages the DIVIDE command
class QadDIVIDECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadDIVIDECommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "DIVIDE")

   def getEnglishName(self):
      return "DIVIDE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runDIVIDECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/divide.svg")

   def getNote(self):
      # set explanatory notes for the command
      return QadMsg.translate("Command_DIVIDE", "Creates evenly spaced punctual objects along the length or perimeter of an object.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entSelClass = None
      self.objectAlignment = True
      self.nSegments = 1

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.entSelClass is not None:
         self.entSelClass.entity.deselectOnLayer()
         del self.entSelClass
      

   # ============================================================================
   # waitForEntsel
   # ============================================================================
   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = QadDIVIDECommandClassStepEnum.ASK_FOR_ENT
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_DIVIDE", "Select object to divide: ")
      # discard point selection
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = True
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.checkDimLayers = False
      self.entSelClass.onlyEditableLayers = False

      self.entSelClass.run(msgMapTool, msg)


   # ============================================================================
   # waitForAlignmentObjs
   # ============================================================================
   def waitForAlignmentObjs(self):
      self.step = QadDIVIDECommandClassStepEnum.ASK_FOR_ALIGNMENT

      keyWords = QadMsg.translate("QAD", "Yes") + "/" + QadMsg.translate("QAD", "No")
      self.defaultValue = QadMsg.translate("QAD", "Yes")
      prompt = QadMsg.translate("Command_DIVIDE", "Align with object ? [{0}] <{1}>: ").format(keyWords, self.defaultValue)
      
      englishKeyWords = "Yes" + "/" + "No"
      keyWords += "_" + englishKeyWords

      # msg, inputType, default, keyWords, no validation
      self.waitFor(prompt, \
                   QadInputTypeEnum.KEYWORDS, \
                   self.defaultValue, \
                   keyWords, QadInputModeEnum.NONE)

   
   # ============================================================================
   # waitForSegmentNumber
   # ============================================================================
   def waitForSegmentNumber(self):
      self.step = QadDIVIDECommandClassStepEnum.ASK_SEGMENT_NUMBER

      # prepares to wait for an integer number
      msg = QadMsg.translate("Command_DIVIDE", "Enter the number of segments: ")
      # msg, inputType, default, keyWords, positive values
      self.waitFor(msg, \
                   QadInputTypeEnum.INT, \
                   None, \
                   "", \
                   QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)


   # ============================================================================
   # addFeature
   # ============================================================================
   def addFeature(self, layer, insPt, rot, openForm = True):
      transformedPoint = self.mapToLayerCoordinates(layer, insPt)
      g = QgsGeometry.fromPointXY(transformedPoint)
      f = QgsVectorLayerUtils.createFeature(layer, g, {}, layer.createExpressionContext())
      
      # if scale depends on a field
      scaleFldName = qad_layer.get_symbolScaleFieldName(layer)
      if len(scaleFldName) > 0:
         f.setAttribute(scaleFldName, 1.0)
      
      # if rotation depends on a field
      rotFldName = qad_layer.get_symbolRotationFieldName(layer)
      if len(rotFldName) > 0:
         f.setAttribute(rotFldName, qad_utils.toDegrees(rot))
      
      return qad_layer.addFeatureToLayer(self.plugIn, layer, f, None, True, False, openForm)               


   # ============================================================================
   # doDivide
   # ============================================================================
   def doDivide(self, dstLayer):
      f = self.entSelClass.entity.getFeature()
      if f is None:
         return
      
      layer = self.entSelClass.entity.layer
      
      qadGeom = self.entSelClass.entity.getQadGeom()
      # the function returns a list with
      # (<minimum distance>
      # <closest point>
      # <index of closest geometry>
      # <index of the closest sub-geometry>
      # if closed geometry is polyline type, the list also contains
      # <index of the part of the closest sub-geometry>
      # <"left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
      dummy = getQadGeomClosestPart(qadGeom, self.entSelClass.point)
      # returns the sub-geometry
      pathPolyline = getQadGeomAt(qadGeom, dummy[2], dummy[3])
      distance = pathPolyline.length() / self.nSegments
      
      self.plugIn.beginEditCommand("Feature divided", dstLayer)
      
      i = 1
      distanceFromStart = distance
      openForm = True if self.nSegments == 2 else False
      while i < self.nSegments:
         pt, rot = pathPolyline.getPointFromStart(distanceFromStart)
         if self.addFeature(dstLayer, pt, rot if self.objectAlignment else 0, openForm) == False:
            self.plugIn.destroyEditCommand()
            return False
         i = i + 1
         distanceFromStart = distanceFromStart + distance 

      self.plugIn.endEditCommand()
      return True
      

   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command
      
      currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.PointGeometry)
      if currLayer is None:
         self.showErr(errMsg)
         return True # end command

      if qad_layer.isSymbolLayer(currLayer) == False :
         errMsg = QadMsg.translate("QAD", "\nCurrent layer is not a symbol layer.")
         errMsg = errMsg + QadMsg.translate("QAD", "\nA symbol layer is a vector punctual layer without label.\n")
         self.showErr(errMsg)
         return True # end command
      
      if  len(QadDimStyles.getDimListByLayer(currLayer)) > 0:
         errMsg = QadMsg.translate("QAD", "\nThe current layer belongs to a dimension style.\n")
         self.showErr(errMsg)
         return True # end command

      if self.step == 0:     
         self.waitForEntsel(msgMapTool, msg)
         return False # continue


      # =========================================================================
      # RESPONSE TO ENTITY SELECTION (from step = 0)
      elif self.step == QadDIVIDECommandClassStepEnum.ASK_FOR_ENT:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               # if the destination layer is a symbol type
               if qad_layer.isSymbolLayer(currLayer) == True:
                  # if the symbol can be rotated
                  if len(qad_layer.get_symbolRotationFieldName(currLayer)) >0:
                     self.waitForAlignmentObjs()
                  else:
                     self.waitForSegmentNumber()
               return False
            else:
               if self.entSelClass.canceledByUsr == True: # end command
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)
         return False # continue
      

      # =========================================================================
      # RESPONSE TO ALIGN OBJECTS REQUEST (from step = ASK_FOR_ENT)
      elif self.step == QadDIVIDECommandClassStepEnum.ASK_FOR_ALIGNMENT: # after waiting for a keyword the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            if self.getPointMapTool().rightButton == True: # if right mouse button is used
               value = self.defaultValue 
            else:
               self.setMapTool(self.getPointMapTool()) # reactivate the maptool
               return False
         else:
            # the keyword comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("QAD", "Yes") or value == "Yes":
               self.objectAlignment = True
            else:
               self.objectAlignment = False

            self.waitForSegmentNumber()
         
         return False 


      # =========================================================================
      # RESPONSE TO SEGMENT NUMBER REQUEST (from step = ASK_FOR_ALIGNMENT)
      # =========================================================================
      elif self.step == QadDIVIDECommandClassStepEnum.ASK_SEGMENT_NUMBER: # after waiting for an integer the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            if self.getPointMapTool().rightButton == True: # if right mouse button is used
               return False
            else:
               self.setMapTool(self.getPointMapTool()) # reactivate the maptool
               return False
         else:
            # the number of segments comes as a parameter of the function
            self.nSegments = msg
            self.doDivide(currLayer)
            return True # end command
         return False
