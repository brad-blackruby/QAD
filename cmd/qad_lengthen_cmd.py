# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 LENGTHEN command to extend an object
 
                              -------------------
        begin                : 2015-10-05
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


from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsPointXY, QgsWkbTypes


from .. import qad_utils
from ..qad_variables import QadVariables
from ..qad_msg import QadMsg
from ..qad_entity import QadEntity
from .qad_generic_cmd import QadCommandClass
from .qad_getdist_cmd import QadGetDistClass
from .qad_getangle_cmd import QadGetAngleClass
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_lengthen_maptool import Qad_lengthen_maptool, Qad_lengthen_maptool_ModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .. import qad_layer
from ..qad_arc import QadArc
from ..qad_dim import QadDimStyles
from .. import qad_grip
from ..qad_geom_relations import getQadGeomClosestVertex
from ..qad_multi_geom import fromQadGeomToQgsGeom, getQadGeomAt, setQadGeomAt, isLinearQadGeom


# Class that manages the LENGTHEN command
class QadLENGTHENCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ instantiates a new command of the same type """
      return QadLENGTHENCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "LENGTHEN")

   def getEnglishName(self):
      return "LENGTHEN"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runLENGTHENCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/lengthen.svg")
   
   def getNote(self):
      # set the explanatory notes for the command      
      return QadMsg.translate("Command_LENGTHEN", "Lengthen an object.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.OpMode = plugIn.lastOpMode_lengthen # "DElta" or "Percent" or "Total" or "DYnamic"
      self.OpType = None # "length" or "Angle"
      self.value = None 

      self.startPt = None
      self.GetDistClass = None
      self.GetAngleClass = None
      self.entity = QadEntity()
      self.linearObject = None
      self.atGeom = None
      self.move_startPt = None
      
      self.nOperationsToUndo = 0


   def __del__(self):
      QadCommandClass.__del__(self)
      if self.GetDistClass is not None:
         del self.GetDistClass      
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 3: # when requesting distance
         return self.GetDistClass.getPointMapTool()
      if self.step == 4: # when requesting angle
         return self.GetAngleClass.getPointMapTool()
      elif (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_lengthen_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None


   def getCurrentContextualMenu(self):
      if self.step == 3: # when requesting distance
         return self.GetDistClass.getCurrentContextualMenu()
      if self.step == 4: # when requesting angle
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu

  def setInfo(self, entity, point):
     # sets: self.entity, self.linearObject, self.atGeom and self.move_startPt
     if self.linearObject is not None:
        del self.linearObject
        self.linearObject = None
     
     self.entity.set(entity.layer, entity.featureId)
     qadGeom = self.entity.getQadGeom()

     # the function returns a list with 
     # (<minimum distance>
     # <point of the closest vertex>
     # <index of the closest geometry>
     # <index of the closest sub-geometry>
     # <index of the part of the closest sub-geometry>
     # <index of the closest vertex>
     result = getQadGeomClosestVertex(qadGeom, point)
     self.atGeom = result[2]
     self.linearObject = getQadGeomAt(qadGeom, self.atGeom, 0).copy()
                 
     if qad_utils.getDistance(self.linearObject.getStartPt(), point) <= \
        qad_utils.getDistance(self.linearObject.getEndPt(), point):
        # extending from the start point
        self.move_startPt = True
     else:
        # extending from the end point
        self.move_startPt = False
        
     return True
  

  # ============================================================================
  # lengthen
  # ============================================================================
  def lengthen(self, point):
     layer = self.entity.layer
     f = self.entity.getFeature()
     if f is None: # feature no longer exists
        return False
     qadGeom = self.entity.getQadGeom()
                 
     # returns a tuple (<The squared cartesian distance>,
     #                    <minDistPoint>
     #                    <afterVertex>
     #                    <leftOf>)
     res = False
     newLinearObject = self.linearObject.copy()
     if self.OpMode == "DElta":
        if self.OpType == "length":
           res = newLinearObject.lengthen_delta(self.move_startPt, self.value)
        elif self.OpType == "Angle":
           res = newLinearObject.lengthen_deltaAngle(self.move_startPt, self.value)
     elif self.OpMode == "Percent":
        value = newLinearObject.length() * self.value / 100
        value = value - newLinearObject.length()
        res = newLinearObject.lengthen_delta(self.move_startPt, value)
     elif self.OpMode == "Total":
        if self.OpType == "length":
           value = self.value - newLinearObject.length()
           res = newLinearObject.lengthen_delta(self.move_startPt, value)
        elif self.OpType == "Angle":                     
           if newLinearObject.whatIs() == "ARC":
              value = self.value - newLinearObject.totalAngle()
              res = newLinearObject.lengthen_deltaAngle(self.move_startPt, value)
     elif self.OpMode == "DYnamic":
        if newLinearObject.whatIs() == "POLYLINE":
           if self.move_startPt:
              linearObject = newLinearObject.getLinearObjectAt(0)
           else:
              linearObject = newLinearObject.getLinearObjectAt(-1)
        else:
           linearObject = newLinearObject
           
        gType = linearObject.whatIs()
        if gType == "LINE":
           newPt = qad_utils.getPerpendicularPointOnInfinityLine(linearObject.getStartPt(), linearObject.getEndPt(), point)
           ang = linearObject.getTanDirectionOnStartPt()
              
        elif gType == "ARC":
           newPt = qad_utils.getPolarPointByPtAngle(linearObject.center, \
                                                    qad_utils.getAngleBy2Pts(linearObject.center, point), \
                                                    linearObject.radius)                  
        elif gType == "ELLIPSE_ARC":
           pass

        if self.move_startPt:
           linearObject.setStartPt(newPt)
        else:
           linearObject.setEndPt(newPt)

        if gType == "LINE" and newLinearObject.whatIs() == "POLYLINE" and \
           qad_utils.TanDirectionNear(ang, newLinearObject.getTanDirectionOnStartPt()) == False:
           res = False
        else:
           res = True
           
     if res == False: # lengthening impossible
        return False

     updGeom = setQadGeomAt(qadGeom, newLinearObject, self.atGeom, 0)
     # transform the geometry to the layer's CRS
     f.setGeometry(fromQadGeomToQgsGeom(updGeom, layer))
        
     self.plugIn.beginEditCommand("Feature edited", layer)
     
     # plugIn, layer, feature, refresh, check_validity
     if qad_layer.updateFeatureToLayer(self.plugIn, layer, f, False, False) == False:
        self.plugIn.destroyEditCommand()
        return False

     self.plugIn.endEditCommand()
     self.nOperationsToUndo = self.nOperationsToUndo + 1
     
     return True

  def showLength(self, entity, pt):
     # displays the length of the entity in map units
     qadGeom = entity.getQadGeom()
     if qadGeom is None:         
        errMsg = QadMsg.translate("QAD", "Invalid object.")
        self.showErr("\n" + errMsg)
        return None

     # the function returns a list with 
     # (<minimum distance>
     # <point of the closest vertex>
     # <index of the closest geometry>
     # <index of the closest sub-geometry>
     # <index of the part of the closest sub-geometry>
     # <index of the closest vertex>
     result = getQadGeomClosestVertex(qadGeom, pt)
     atGeom = result[2]
     LinearObjectToMisure = getQadGeomAt(qadGeom, atGeom, 0).copy()

     msg = QadMsg.translate("Command_LENGTHEN", "\nCurrent length: {0}")
     msg = msg.format(str(LinearObjectToMisure.length()))

     if LinearObjectToMisure.whatIs() == "ARC":
        msg = msg + QadMsg.translate("Command_LENGTHEN", ", included angle: {0}")
        msg = msg.format(str(qad_utils.toDegrees(LinearObjectToMisure.totalAngle())))
        
     self.showMsg(msg)


  def waitForObjectSelToMisure(self):
     self.step = 1      
     # set the map tool
     self.getPointMapTool().setMode(Qad_lengthen_maptool_ModeEnum.ASK_FOR_OBJ_TO_MISURE)

     if self.plugIn.lastOpMode_lengthen == "DElta":
        self.defaultValue = QadMsg.translate("Command_LENGTHEN", "DElta")
     elif self.plugIn.lastOpMode_lengthen == "Percent":
        self.defaultValue = QadMsg.translate("Command_LENGTHEN", "Percent")
     elif self.plugIn.lastOpMode_lengthen == "Total":
        self.defaultValue = QadMsg.translate("Command_LENGTHEN", "Total")
     elif self.plugIn.lastOpMode_lengthen == "DYnamic":
        self.defaultValue = QadMsg.translate("Command_LENGTHEN", "DYnamic")
     else:
        self.defaultValue = None
     
     keyWords = QadMsg.translate("Command_LENGTHEN", "DElta") + "/" + \
                QadMsg.translate("Command_LENGTHEN", "Percent") + "/" + \
                QadMsg.translate("Command_LENGTHEN", "Total") + "/" + \
                QadMsg.translate("Command_LENGTHEN", "DYnamic")
     if self.defaultValue is None:
        prompt = QadMsg.translate("Command_LENGTHEN", "Select an object or [{0}] <{1}>: ").format(keyWords, self.defaultValue)
     else:
        prompt = QadMsg.translate("Command_LENGTHEN", "Select an object or [{0}] <{1}>: ").format(keyWords, self.defaultValue)

     englishKeyWords = "DElta" + "/" + "Percent" + "/" + "Total" + "/" + "DYnamic"
     keyWords += "_" + englishKeyWords
     # prepares to wait for a point or enter or a keyword         
     # msg, inputType, default, keyWords, no check
     self.waitFor(prompt, \
                  QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                  self.defaultValue, \
                  keyWords, QadInputModeEnum.NONE)


  def waitForDelta(self):
     self.step = 2
     self.OpMode = "DElta"
     self.plugIn.setLastOpMode_lengthen(self.OpMode)
     # set the map tool
     self.getPointMapTool().setMode(Qad_lengthen_maptool_ModeEnum.ASK_FOR_DELTA)

     keyWords = QadMsg.translate("Command_LENGTHEN", "Angle")
     prompt = QadMsg.translate("Command_LENGTHEN", "Enter delta length or [{0}] <{1}>: ").format(keyWords, str(self.plugIn.lastDelta_lengthen))

     englishKeyWords = "Angle"
     keyWords += "_" + englishKeyWords
     # prepares to wait for a point or enter or a keyword         
     # msg, inputType, default, keyWords, no check
     self.waitFor(prompt, \
                  QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS | QadInputTypeEnum.FLOAT, \
                  self.plugIn.lastDelta_lengthen, \
                  keyWords, QadInputModeEnum.NONE)
     

  def waitForDeltaLength(self, msgMapTool, msg):
     self.step = 3
     self.OpType = "length"

     # prepares to wait for a distance                     
     if self.GetDistClass is not None:
        del self.GetDistClass
     self.GetDistClass = QadGetDistClass(self.plugIn)     
     prompt = QadMsg.translate("Command_LENGTHEN", "Enter delta length <{0}>: ")
     self.GetDistClass.msg = prompt.format(str(self.plugIn.lastDelta_lengthen))
     self.GetDistClass.startPt = self.startPt
     self.GetDistClass.dist = self.plugIn.lastDelta_lengthen
     self.GetDistClass.inputMode = QadInputModeEnum.NONE
     self.GetDistClass.run(msgMapTool, msg)

  def waitForDeltaAngle(self, msgMapTool, msg):
     self.step = 4
     self.OpType = "Angle"

     # prepares to wait for the rotation angle                      
     if self.GetAngleClass is not None:
        del self.GetAngleClass                  
     self.GetAngleClass = QadGetAngleClass(self.plugIn)
     prompt = QadMsg.translate("Command_LENGTHEN", "Enter delta angle <{0}>: ")
     self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.plugIn.lastDeltaAngle_lengthen)))
     self.GetAngleClass.angle = self.plugIn.lastDeltaAngle_lengthen
     self.GetAngleClass.run(msgMapTool, msg)         


  def waitForObjectSel(self):
     self.step = 5
     # set the map tool
     self.getPointMapTool().setMode(Qad_lengthen_maptool_ModeEnum.ASK_FOR_OBJ_TO_LENGTHEN)
     self.getPointMapTool().refreshSnapType() # update snapType which may have been changed by distance or angle maptool
     self.getPointMapTool().OpType = self.OpType 
     self.getPointMapTool().value = self.value

     keyWords = QadMsg.translate("Command_LENGTHEN", "Undo")
     prompt = QadMsg.translate("Command_LENGTHEN", "Select an object to change or [{0}]: ").format(QadMsg.translate("Command_LENGTHEN", "Undo"))

     englishKeyWords = "Undo"
     keyWords += "_" + englishKeyWords
     # prepares to wait for a point or enter or a keyword
     # msg, inputType, default, keyWords, no check
     self.waitFor(prompt, \
                  QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                  None, \
                  keyWords, QadInputModeEnum.NONE)


  def waitForPercent(self):
     self.step = 6
     self.OpMode = "Percent"
     self.plugIn.setLastOpMode_lengthen(self.OpMode)

     # set the map tool
     self.getPointMapTool().setMode(Qad_lengthen_maptool_ModeEnum.ASK_FOR_PERCENT)

     prompt = QadMsg.translate("Command_LENGTHEN", "Enter percentage length <{0}>: ")
     prompt = prompt.format(str(self.plugIn.lastPerc_lengthen))
     # prepares to wait for a real number         
     # msg, inputType, default, keyWords, positive values
     self.waitFor(prompt, QadInputTypeEnum.FLOAT, \
                  self.plugIn.lastPerc_lengthen, "", \
                  QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)


  def waitForTotal(self):
     self.step = 7
     self.OpMode = "Total"
     self.plugIn.setLastOpMode_lengthen(self.OpMode)
     # set the map tool
     self.getPointMapTool().setMode(Qad_lengthen_maptool_ModeEnum.ASK_FOR_TOTAL)

     keyWords = QadMsg.translate("Command_LENGTHEN", "Angle")
     prompt = QadMsg.translate("Command_LENGTHEN", "Specify total length or [{0}] <{1}>: ").format(keyWords, str(self.plugIn.lastTotal_lengthen))

     englishKeyWords = "Angle"
     keyWords += "_" + englishKeyWords
     # prepares to wait for a point or enter or a keyword         
     # msg, inputType, default, keyWords, no check
     self.waitFor(prompt, \
                  QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS | QadInputTypeEnum.FLOAT, \
                  self.plugIn.lastTotal_lengthen, \
                  keyWords, QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
     

  def waitForTotalLength(self, msgMapTool, msg):
     self.step = 8
     self.OpType = "length"

     # prepares to wait for a distance                     
     if self.GetDistClass is not None:
        del self.GetDistClass
     self.GetDistClass = QadGetDistClass(self.plugIn)     
     prompt = QadMsg.translate("Command_LENGTHEN", "Enter total length <{0}>: ")
     self.GetDistClass.msg = prompt.format(str(self.plugIn.lastTotal_lengthen))
     self.GetDistClass.startPt = self.startPt
     self.GetDistClass.dist = self.plugIn.lastTotal_lengthen
     self.GetDistClass.inputMode = QadInputModeEnum.NONE
     self.GetDistClass.run(msgMapTool, msg)

  def waitForTotalAngle(self, msgMapTool, msg):
     self.step = 9
     self.OpType = "Angle"

     # prepares to wait for the rotation angle                      
     if self.GetAngleClass is not None:
        del self.GetAngleClass                  
     self.GetAngleClass = QadGetAngleClass(self.plugIn)
     prompt = QadMsg.translate("Command_LENGTHEN", "Enter total angle <{0}>: ")
     self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.plugIn.lastTotalAngle_lengthen)))
     self.GetAngleClass.angle = self.plugIn.lastTotalAngle_lengthen
     self.GetAngleClass.run(msgMapTool, msg)         


  def waitForDynamicPt(self):
     self.step = 10
     # set the map tool
     self.getPointMapTool().setMode(Qad_lengthen_maptool_ModeEnum.ASK_FOR_DYNAMIC_POINT)

     prompt = QadMsg.translate("Command_LENGTHEN", "Specify new endpoint: ")

     # prepares to wait for a point or enter or a keyword         
     # msg, inputType, default, keyWords, no check
     self.waitFor(prompt, \
                  QadInputTypeEnum.POINT2D, \
                  None, \
                  "", QadInputModeEnum.NONE)


  # ============================================================================
  # run
  # ============================================================================
  def run(self, msgMapTool = False, msg = None):
     if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
        self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
        return True # end command

     # =========================================================================
     # OBJECT SELECTION REQUEST
     if self.step == 0: # command start
        # prepares to wait for the selection of objects to extend/cut
        self.waitForObjectSelToMisure()
        return False

     # =========================================================================
     # RESPONSE TO OBJECTS TO MEASURE SELECTION
     elif self.step == 1:
        if msgMapTool == True: # the point comes from a graphic selection
           # the following condition occurs if during the selection of a point
           # another plugin was activated that deactivated Qad
           # then the command was reactivated which returns here without the maptool
           # having selected a point            
           if self.getPointMapTool().point is None: # the maptool was activated without a point
              if self.getPointMapTool().rightButton == True: # if used the right mouse button
                 value = self.defaultValue
              else:
                 self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                 return False
           else:
              value = self.getPointMapTool().point
        else: # the point comes as a parameter of the function
           value = msg

        if type(value) == unicode:
           if value == QadMsg.translate("Command_LENGTHEN", "DElta") or value == "DElta":
              self.waitForDelta()
              return False
           elif value == QadMsg.translate("Command_LENGTHEN", "Percent") or value == "Percent":
              self.waitForPercent()
              return False
           elif value == QadMsg.translate("Command_LENGTHEN", "Total") or value == "Total":
              self.waitForTotal()
              return False
           elif value == QadMsg.translate("Command_LENGTHEN", "DYnamic") or value == "DYnamic":
              self.OpMode = "DYnamic"
              self.plugIn.setLastOpMode_lengthen(self.OpMode)
              # prepares to wait for the selection of objects to lengthen
              self.waitForObjectSel()
              return False

        elif type(value) == QgsPointXY: # if a point has been selected
           if self.getPointMapTool().entity.isInitialized():
              self.showLength(self.getPointMapTool().entity, value)
           else:
              # looking for entities at the indicated point considering
              # only linear layers that do not belong to dimensions or polygon type 
              layerList = []
              for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All visible vector layers
                 if layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                    if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                       layerList.append(layer)
                                    
              result = qad_utils.getEntSel(self.getPointMapTool().toCanvasCoordinates(value), \
                                           self.getPointMapTool(), \
                                           QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                           layerList)
              if result is not None:
                 feature = result[0]
                 layer = result[1]
                 self.showLength(QadEntity().set(layer, feature.id()), value)
        else:
           return True # end command
        
        # prepares to wait for the selection of objects to measure
        self.waitForObjectSelToMisure()
                                         
        return False

     # =========================================================================
     # RESPONSE TO DELTA REQUEST (from step = 1)
     elif self.step == 2: # after waiting for a point or a real number, restart the command
        if msgMapTool == True: # the point comes from a graphic selection
           # the following condition occurs if during the selection of a point
           # another plugin was activated that deactivated Qad
           # then the command was reactivated which returns here without the maptool
           # having selected a point            
           if self.getPointMapTool().point is None: # the maptool was activated without a point
              if self.getPointMapTool().rightButton == True: # if used the right mouse button
                 value = self.plugIn.lastDelta_lengthen # default option "offset"
              else:
                 self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                 return False
           else:
              value = self.getPointMapTool().point
        else: # the point comes as a parameter of the function
           value = msg

        if type(value) == unicode:
           if value == QadMsg.translate("Command_LENGTHEN", "Angle") or value == "Angle":
              self.waitForDeltaAngle(msgMapTool, msg)
        elif type(value) == QgsPointXY: # if a point has been entered
           self.startPt = value
           self.waitForDeltaLength(msgMapTool, msg)
        elif type(value) == float: # if the delta has been entered
           self.plugIn.setLastDelta_lengthen(value)
           self.OpType = "length"
           self.value = value
           # prepares to wait for the selection of objects to lengthen
           self.waitForObjectSel()

        return False 


     # =========================================================================
     # RESPONSE TO DELTA LENGTH REQUEST (from step = 2)
     elif self.step == 3: # after waiting for a point or a real number, restart the command
        if self.GetDistClass.run(msgMapTool, msg) == True:
           if self.GetDistClass.dist is not None:
              self.plugIn.setLastDelta_lengthen(self.GetDistClass.dist)
              self.value = self.GetDistClass.dist
              # prepares to wait for the selection of objects to lengthen
              self.waitForObjectSel()
              

     # =========================================================================
     # RESPONSE TO DELTA ANGLE REQUEST (from step = 2)
     elif self.step == 4: # after waiting for a point or a real number, restart the command
        if self.GetAngleClass.run(msgMapTool, msg) == True:
           if self.GetAngleClass.angle is not None:
              self.plugIn.setLastDeltaAngle_lengthen(self.GetAngleClass.angle)
              self.value = self.GetAngleClass.angle
              # prepares to wait for the selection of objects to lengthen
              self.waitForObjectSel()


     # =========================================================================
     # RESPONSE TO OBJECTS TO LENGTHEN SELECTION
     elif self.step == 5:
        if msgMapTool == True: # the point comes from a graphic selection
           # the following condition occurs if during the selection of a point
           # another plugin was activated that deactivated Qad
           # then the command was reactivated which returns here without the maptool
           # having selected a point            
           if self.getPointMapTool().point is None: # the maptool was activated without a point
              if self.getPointMapTool().rightButton == True: # if used the right mouse button
                 return True # end command
              else:
                 self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                 return False
           else:
              value = self.getPointMapTool().point
        else: # the point comes as a parameter of the function
           value = msg

        if type(value) == unicode:
           if value == QadMsg.translate("Command_LENGTHEN", "Undo") or value == "Undo":
              if self.nOperationsToUndo > 0: 
                 self.nOperationsToUndo = self.nOperationsToUndo - 1
                 self.plugIn.undoEditCommand()
              else:
                 self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))                  
        elif type(value) == QgsPointXY: # if a point has been selected
           if self.getPointMapTool().entity.isInitialized():
              self.setInfo(self.getPointMapTool().entity, value)
              if self.OpMode != "DYnamic":
                 self.lengthen(value)
              else:
                 self.waitForDynamicPt()
                 return False
           else:
              # looking for entities at the indicated point considering
              # only editable linear layers that do not belong to dimensions
              layerList = []
              for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All visible vector layers
                 if layer.geometryType() == QgsWkbTypes.LineGeometry and layer.isEditable():
                    if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                       layerList.append(layer)
                                    
              result = qad_utils.getEntSel(self.getPointMapTool().toCanvasCoordinates(value), \
                                           self.getPointMapTool(), \
                                           QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                           layerList)
              if result is not None:
                 feature = result[0]
                 layer = result[1]
                 self.setInfo(QadEntity().set(layer, feature.id()), value)

                 if self.OpMode != "DYnamic":
                    self.lengthen(value)
                 else:
                    self.waitForDynamicPt()
                    return False
        else:
           return True # end command

        # prepares to wait for the selection of objects to lengthen
        self.waitForObjectSel()
                          
        return False 

     # =========================================================================
     # RESPONSE TO PERCENTAGE REQUEST (from step = 1)
     elif self.step == 6: # after waiting for a real number, restart the command
        if msgMapTool == True: # the point comes from a graphic selection
           # the following condition occurs if during the selection of a point
           # another plugin was activated that deactivated Qad
           # then the command was reactivated which returns here without the maptool
           # having selected a point            
           if self.getPointMapTool().point is None: # the maptool was activated without a point
              if self.getPointMapTool().rightButton == True: # if used the right mouse button
                 value = self.plugIn.lastPerc_lengthen
              else:
                 self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                 return False
           else:
              return False
        else: # the point comes as a parameter of the function
           value = msg

        if type(value) == float: # percentage has been entered
           self.plugIn.setLastPerc_lengthen(value)
           self.value = value
           # prepares to wait for the selection of objects to lengthen
           self.waitForObjectSel()
           
        return False


     # =========================================================================
     # RESPONSE TO TOTAL REQUEST (from step = 1)
     elif self.step == 7: # after waiting for a point or a real number, restart the command
        if msgMapTool == True: # the point comes from a graphic selection
           # the following condition occurs if during the selection of a point
           # another plugin was activated that deactivated Qad
           # then the command was reactivated which returns here without the maptool
           # having selected a point            
           if self.getPointMapTool().point is None: # the maptool was activated without a point
              if self.getPointMapTool().rightButton == True: # if used the right mouse button
                 value = self.plugIn.lastTotal_lengthen
              else:
                 self.setMapTool(self.getPointMapTool()) # reactivate the maptool
                 return False
           else:
              value = self.getPointMapTool().point
        else: # the point comes as a parameter of the function
           value = msg

        if type(value) == unicode:
           if value == QadMsg.translate("Command_LENGTHEN", "Angle") or value == "Angle":
              self.waitForTotalAngle(msgMapTool, msg)
        elif type(value) == QgsPointXY: # if a point has been entered
           self.startPt = value
           self.waitForTotalLength(msgMapTool, msg)
        elif type(value) == float: # if the delta has been entered
           self.plugIn.setLastTotal_lengthen(value)
           self.OpType = "length"
           self.value = value
           # prepares to wait for the selection of objects to lengthen
           self.waitForObjectSel()

        return False 


     # =========================================================================
     # RESPONSE TO TOTAL LENGTH REQUEST (from step = 7)
     elif self.step == 8: # after waiting for a point or a real number, restart the command
        if self.GetDistClass.run(msgMapTool, msg) == True:
           if self.GetDistClass.dist is not None:
              self.plugIn.setLastTotal_lengthen(self.GetDistClass.dist)
              self.value = self.GetDistClass.dist
              # prepares to wait for the selection of objects to lengthen
              self.waitForObjectSel()
              return False
           

     # =========================================================================
     # RESPONSE TO DELTA ANGLE REQUEST (from step = 7)
     elif self.step == 9: # after waiting for a point or a real number, restart the command
        if self.GetAngleClass.run(msgMapTool, msg) == True:
           if self.GetAngleClass.angle is not None:
              self.plugIn.setLastTotalAngle_lengthen(self.GetAngleClass.angle)
              self.value = self.GetAngleClass.angle
              # prepares to wait for the selection of objects to lengthen
              self.waitForObjectSel()
              return False


     # =========================================================================
     # RESPONSE TO NEW ENDPOINT REQUEST IN DYNAMIC MODE (from step = 5)
     elif self.step == 10: # after waiting for a point
        if msgMapTool == True: # the point comes from a graphic selection
           # the following condition occurs if during the selection of a point
           # another plugin was activated that deactivated Qad
           # then the command was reactivated which returns here without the maptool
           # having selected a point            
           if self.getPointMapTool().point is None: # the maptool was activated without a point
              self.setMapTool(self.getPointMapTool()) # reactivate the maptool
              return False

           value = self.getPointMapTool().point            
        else: # the point comes as a parameter of the function
           value = msg

        if type(value) == QgsPointXY: # if a point has been entered
           self.lengthen(value)
           
        # prepares to wait for the selection of objects to lengthen
        self.waitForObjectSel()
           
        return False

# ============================================================================
# Class that manages the LENGTHEN command for grips
# ============================================================================
class QadGRIPLENGTHENCommandClass(QadCommandClass):

  def instantiateNewCmd(self):
     """ instantiates a new command of the same type """
     return QadGRIPLENGTHENCommandClass(self.plugIn)
  
  def __init__(self, plugIn):
     QadCommandClass.__init__(self, plugIn)
     self.entity = None
     self.skipToNextGripCommand = False
     self.copyEntities = False
     self.basePt = QgsPointXY()
     self.nOperationsToUndo = 0
     
     self.linearObject = None
     self.atGeom = None
     self.move_startPt = None


  def __del__(self):
     QadCommandClass.__del__(self)


  def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):      
     if (self.plugIn is not None):
        if self.PointMapTool is None:
           self.PointMapTool = Qad_lengthen_maptool(self.plugIn)
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
           if gripPoint.getStatus() == qad_grip.QadGripStatusEnum.SELECTED:
              # verify if the entity belongs to a dimension style
              if QadDimStyles.isDimEntity(entityGripPoints.entity):
                 return False
              qadGeom = entityGripPoints.entity.getQadGeom()
              
              # sets: self.entity, self.linearObject, self.atGeom and self.move_startPt
              self.entity = entityGripPoints.entity
              
              if self.linearObject is not None:
                 del self.linearObject
                 self.linearObject = None

              # the function returns a list with 
              # (<minimum distance>
              # <point of the closest vertex>
              # <index of the closest geometry>
              # <index of the closest sub-geometry>
              # <index of the part of the closest sub-geometry>
              # <index of the closest vertex>
              point = gripPoint.getPoint()
              result = getQadGeomClosestVertex(qadGeom, point)
              self.atGeom = result[2]
              linearObject = getQadGeomAt(qadGeom, self.atGeom, 0).copy()

              if not isLinearQadGeom(linearObject):
                 return False

              self.linearObject = getQadGeomAt(qadGeom, self.atGeom, 0).copy()
                          
              if qad_utils.getDistance(self.linearObject.getStartPt(), point) <= \
                 qad_utils.getDistance(self.linearObject.getEndPt(), point):
                 # extending from the start point
                 self.move_startPt = True
              else:
                 # extending from the end point
                 self.move_startPt = False
              
              # set the map tool
              if self.getPointMapTool().setInfo(self.entity, point) == False:
                 return False
              
              return True
     return False


  # ============================================================================
  # lengthen
  # ============================================================================
  def lengthen(self, point):
     layer = self.entity.layer
     f = self.entity.getFeature()
     if f is None: # feature no longer exists
        return False
     qadGeom = self.entity.getQadGeom()
                 
     res = False
     newLinearObject = self.linearObject.copy()

     if newLinearObject.whatIs() == "POLYLINE":
        if self.move_startPt:
           linearObject = newLinearObject.getLinearObjectAt(0)
        else:
           linearObject = newLinearObject.getLinearObjectAt(-1)
     else:
        linearObject = newLinearObject
        
     gType = linearObject.whatIs()
     if gType == "LINE":
        newPt = qad_utils.getPerpendicularPointOnInfinityLine(linearObject.getStartPt(), linearObject.getEndPt(), point)
        ang = linearObject.getTanDirectionOnStartPt()
           
     elif gType == "ARC":
        newPt = qad_utils.getPolarPointByPtAngle(linearObject.center, \
                                                 qad_utils.getAngleBy2Pts(linearObject.center, point), \
                                                 linearObject.radius)                  
     elif gType == "ELLIPSE_ARC":
        pass

     if self.move_startPt:
        linearObject.setStartPt(newPt)
     else:
        linearObject.setEndPt(newPt)
       
     if gType == "LINE" and newLinearObject.whatIs() == "POLYLINE" and \
        qad_utils.TanDirectionNear(ang, linearObject.getTanDirectionOnStartPt()) == False:
        res = False
     else:
        res = True

     if res == False: # lengthening impossible
        return False
     
     updGeom = setQadGeomAt(qadGeom, newLinearObject, self.atGeom, 0)
     # transform the geometry to the layer's CRS
     f.setGeometry(fromQadGeomToQgsGeom(updGeom, layer))
        
     self.plugIn.beginEditCommand("Feature edited", layer)
     
     if self.copyEntities == False:
        # plugIn, layer, feature, refresh, check_validity
        if qad_layer.updateFeatureToLayer(self.plugIn, layer, f, False, False) == False:
           self.plugIn.destroyEditCommand()
           return False
     else:
        # plugIn, layer, features, coordTransform, refresh, check_validity
        if qad_layer.addFeatureToLayer(self.plugIn, layer, f, None, False, False) == False:
           self.plugIn.destroyEditCommand()
           return False
     
     self.plugIn.endEditCommand()
     self.nOperationsToUndo = self.nOperationsToUndo + 1
     
     return True

  def waitForDynamicPt(self):
     keyWords = QadMsg.translate("Command_GRIP", "Copy") + "/" + \
                QadMsg.translate("Command_GRIP", "Undo") + "/" + \
                QadMsg.translate("Command_GRIP", "eXit")
     prompt = QadMsg.translate("Command_GRIPLENGTHEN", "Specify new endpoint or [{0}]: ").format(keyWords)

     englishKeyWords = "Copy" + "/" + "Undo" + "/" "eXit"
     keyWords += "_" + englishKeyWords

     # prepares to wait for a point or enter or a keyword         
     # msg, inputType, default, keyWords, no check
     self.waitFor(prompt, \
                  QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                  None, \
                  keyWords, QadInputModeEnum.NONE)
     self.step = 1
     # set the map tool
     self.getPointMapTool().setMode(Qad_lengthen_maptool_ModeEnum.ASK_FOR_DYNAMIC_POINT)


  # ============================================================================
  # run
  # ============================================================================
  def run(self, msgMapTool = False, msg = None):
     if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
        self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
        return True # end command

     # =========================================================================
     # OBJECT SELECTION REQUEST
     if self.step == 0: # command start
        self.waitForDynamicPt()
        return False

     # =========================================================================
     # RESPONSE TO OBJECTS TO MEASURE SELECTION
     elif self.step == 1:
        ctrlKey = False
        if msgMapTool == True: # the point comes from a graphic selection
           # the following condition occurs if during the selection of a point
           # another plugin was activated that deactivated Qad
           # then the command was reactivated which returns here without the maptool
           # having selected a point            
           if self.getPointMapTool().point is None: # the maptool was activated without a point
              if self.getPointMapTool().rightButton == True: # if used the right mouse button
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
           if value == QadMsg.translate("Command_GRIP", "Copy") or value == "Copy":
              # Copy entities leaving the originals unchanged
              self.copyEntities = True                     

              self.waitForDynamicPt()
           elif value == QadMsg.translate("Command_GRIP", "Undo") or value == "Undo":
              if self.nOperationsToUndo > 0: 
                 self.nOperationsToUndo = self.nOperationsToUndo - 1
                 self.plugIn.undoEditCommand()
              else:
                 self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))                  

              self.waitForDynamicPt()
           elif value == QadMsg.translate("Command_GRIP", "eXit") or value == "eXit":
              return True # end command
        elif type(value) == QgsPointXY: # if a point has been selected
           if ctrlKey:
              self.copyEntities = True
  
           self.lengthen(value)

           if self.copyEntities == False:
              return True

           self.waitForDynamicPt()
        else:
           if self.copyEntities == False:
              self.skipToNextGripCommand = True
           return True # end command
                                         
        return False
