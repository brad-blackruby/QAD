# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Base class for a command
 
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
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtWidgets import QAction, QMenu
from qgis.core import QgsPointXY, QgsGeometry, QgsCoordinateTransform, QgsProject


from ..qad_msg import QadMsg
from ..qad_utils import pointToStringFmt
from ..qad_variables import QadVariables
from ..qad_textwindow import QadInputModeEnum, QadInputTypeEnum
from ..qad_getpoint import QadGetPointDrawModeEnum, QadGetPoint
from ..qad_dynamicinput import QadDynamicInputContextEnum
from ..qad_dsettings_dlg import QadDSETTINGSDialog, QadDSETTINGSTabIndexEnum
from ..qad_snapper import QadSnapTypeEnum, snapTypeEnum2Str


# Class that manages a generic command
class QadCommandClass(QObject): # derived from QObject to handle the sender() method
   def showMsg(self, msg, displayPromptAfterMsg = False):
      if self.plugIn is not None:
         self.plugIn.showMsg(msg, displayPromptAfterMsg)
         
   def showErr(self, err):
      if self.plugIn is not None:
         self.plugIn.showErr(err)

   def showInputMsg(self, inputMsg, inputType, default = None, keyWords = "", \
                    inputMode = QadInputModeEnum.NONE):
      if self.plugIn is not None:
         self.plugIn.showInputMsg(inputMsg, inputType, default, keyWords, inputMode)

      # initialize the contextual menu
      self.initContextualMenu(inputType, keyWords)


   def initContextualMenu(self, inputType, keyWords):
      if self.plugIn is None:
         return
      
      if self.contextualMenu:
         del self.contextualMenu
         self.contextualMenu = None

#       if keyWords == "":
#          if self.contextualMenu:
#             del self.contextualMenu
#             self.contextualMenu = None
#          return

      self.contextualMenu = QadContextualMenuClass(self.plugIn, inputType, keyWords)


   def enterActionByContextualMenu(self):
      self.plugIn.showEvaluateMsg(None)

   
   def cancelActionByContextualMenu(self):
      self.plugIn.abortCommand()


   def showEvaluateMsgByContextualMenu(self):
      sender = self.sender()
      self.plugIn.showEvaluateMsg(sender.text())


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = QadGetPoint(self.plugIn, drawMode) # for point selection
         return self.PointMapTool
      else:
         return None

      
   def getCurrentContextualMenu(self):
      return self.contextualMenu


   def hidePointMapToolMarkers(self):
      if self.PointMapTool is not None:
         self.PointMapTool.hidePointMapToolMarkers()

   def setMapTool(self, mapTool):
      if self.plugIn is not None:
         # set the maptool for input via graphic window
         self.plugIn.canvas.setMapTool(mapTool)
         self.plugIn.mainAction.setChecked(True)     


   def waitForPoint(self, msg = None, \
                    default = None, inputMode = QadInputModeEnum.NOT_NULL):
      if msg is None:
          msg = QadMsg.translate("QAD", "Specify point: ")
      self.setMapTool(self.getPointMapTool())
      # set input via text window
      self.showInputMsg(msg, QadInputTypeEnum.POINT2D, default, "", inputMode)
      

   def waitForString(self, msg, default = None, inputMode = QadInputModeEnum.NONE):
      self.setMapTool(self.getPointMapTool())
      # set input via text window
      self.showInputMsg(msg, QadInputTypeEnum.STRING, default, "", inputMode)


   def waitForInt(self, msg, default = None, inputMode = QadInputModeEnum.NOT_NULL):
      self.setMapTool(self.getPointMapTool())
      # set input via text window
      self.showInputMsg(msg, QadInputTypeEnum.INT, default, "", inputMode)


   def waitForLong(self, msg, default = None, inputMode = QadInputModeEnum.NOT_NULL):
      self.setMapTool(self.getPointMapTool())
      # set input via text window
      self.showInputMsg(msg, QadInputTypeEnum.LONG, default, "", inputMode)


   def waitForFloat(self, msg, default = None, inputMode = QadInputModeEnum.NOT_NULL):
      self.setMapTool(self.getPointMapTool())
      # set input via text window
      self.showInputMsg(msg, QadInputTypeEnum.FLOAT, default, "", inputMode)


   def waitForBool(self, msg, default = None, inputMode = QadInputModeEnum.NOT_NULL):
      self.setMapTool(self.getPointMapTool())
      # set input via text window
      self.showInputMsg(msg, QadInputTypeEnum.BOOL, default, "", inputMode)


   def waitForSelSet(self, msg = QadMsg.translate("QAD", "Select objects: ")):
      self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_RECTANGLE)
      self.setMapTool(self.getPointMapTool())
      self.getPointMapTool().getDynamicInput().context = QadDynamicInputContextEnum.NONE
      # set input via text window
      self.showInputMsg(msg, QadInputTypeEnum.POINT2D)


   def waitFor(self, msg, inputType, default = None, keyWords = "", \
               inputMode = QadInputModeEnum.NONE):
      self.setMapTool(self.getPointMapTool())
      # set input via text window
      self.showInputMsg(msg, inputType, default, keyWords, inputMode)


   def getCurrMsgFromTxtWindow(self):
      if self.plugIn is not None:
         return self.plugIn.getCurrMsgFromTxtWindow()
      else:
         return None
         
   def showEvaluateMsg(self, msg = None):
      if self.plugIn is not None:
         self.plugIn.showEvaluateMsg(msg)

   def runCommandAbortingTheCurrent(self):
      self.plugIn.runCommandAbortingTheCurrent(self.getName())
      
   def getToolTipText(self):
      text = self.getName()
      if len(self.getNote()) > 0:
         text = text + "\n\n" + self.getNote()
      return text
      
   # ============================================================================
   # functions to be overridden with classes inheriting from this one
   # ============================================================================
   def getName(self):
      """ set the command name in uppercase """
      return ""

   def getEnglishName(self):
      """ set the command name in English uppercase """
      return ""

   def connectQAction(self, action):
      pass     
      #action.triggered.connect(self.plugIn.runPLINECommand) for example

   def getIcon(self):
      # set the command icon (e.g. QIcon(":/plugins/qad/icons/pline.svg"))
      # remember to insert the icon in resources.qrc and recompile the resources
      return None

   def getNote(self):
      """ set the explanatory notes of the command """
      return ""
   
   def __init__(self, plugIn):
      QObject.__init__(self)      
      self.plugIn       = plugIn
      self.PointMapTool = None
      self.step         = 0      
      self.isValidPreviousInput = True # to manage the command also in macro
      self.contextualMenu = None
      
      # initialize all map tools needed for the command
      # example of a command structure that requires
      # 1) a point
      # self.mapTool = QadGetPoint(self.plugIn) # for point selection


   def __del__(self):
      """ destructor """
      self.hidePointMapToolMarkers()
      
      if self.PointMapTool:
         self.PointMapTool.removeItems()
         del self.PointMapTool
         self.PointMapTool = None
         
      if self.contextualMenu:
         #QObject.disconnect(enterAction, SIGNAL("triggered()"), self.enterActionByContextualMenu)

         del self.contextualMenu
         self.contextualMenu = None

       ########## BEGIN SEGMENT 2 ##########     
  def instantiateNewCmd(self):
     """ instantiates a new command of the same type """
     return None
  
  def run(self, msgMapTool = False, msg = None):
     """
     Executes the command.
     - msgMapTool; if True means a value comes from MapTool of the command
                  if False means the value is in the msg parameter
     - msg;        input value to the command (used when msgMapTool = False)
     
     returns True if the command is terminated otherwise False
     """
     # example of a command structure that requires
     # 1) a point
     if self.step == 0: # beginning of the command
        self.waitForPoint() # prepares to wait for a point
        self.step = self.step + 1
        return False
     elif self.step == 1: # after waiting for a point, restart the command
        if msgMapTool == True: # the point comes from a graphic selection
           # the following condition occurs if during the selection of a point
           # another plugin has been activated that has deactivated Qad
           # then the command was reactivated which returns here without the maptool
           # having selected a point            
           if self.getPointMapTool().point is None: # the maptool has been activated without a point
              self.setMapTool(self.getPointMapTool()) # reactivate the maptool
              return False

           pt = self.getPointMapTool().point
        else: # the point comes as a parameter of the function
           pt = msg
           
        return True

  def mapToLayerCoordinates(self, layer, point_geom):
     # transform point or geometry coordinates from output CRS to layer's CRS 
     if self.plugIn is None:
        return None
     if type(point_geom) == QgsPointXY:
        return self.plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point_geom)
     
     fromCrs = self.plugIn.canvas.mapSettings().destinationCrs()
     toCrs = layer.crs()
        
     if type(point_geom) == QgsGeometry:
        if fromCrs == toCrs:
           return QgsGeometry(point_geom)
        
        # transform the geometry in the canvas crs to work with plane xy coordinates
        coordTransform = QgsCoordinateTransform(self.plugIn.canvas.mapSettings().destinationCrs(), \
                                                layer.crs(), \
                                                QgsProject.instance())
        g = QgsGeometry(point_geom)
        g.transform(coordTransform)
        return g
     elif (type(point_geom) == list or type(point_geom) == tuple): # list of points or geometries
        res = []
        if fromCrs == toCrs:
           for pt in point_geom:
              if type(pt) == QgsPointXY:
                 res.append(QgsPointXY(pt))
              elif type(pt) == QgsGeometry:
                 res.append(QgsGeometry(pt))
           return res
           
        coordTransform = QgsCoordinateTransform(self.plugIn.canvas.mapSettings().destinationCrs(), \
                                                layer.crs(), \
                                                QgsProject.instance())
        for pt in point_geom:
           if type(pt) == QgsPointXY:
              res.append(coordTransform.transform(pt))
           elif type(pt) == QgsGeometry:
              g = QgsGeometry(pt)
              g.transform(coordTransform)
              res.append(g)
        return res
     else:
        return None

  def layerToMapCoordinates(self, layer, point_geom):
     # transform point or geometry coordinates from layer's CRS to output CRS 
     if self.plugIn is None:
        return None
     if type(point_geom) == QgsPointXY:
        return self.plugIn.canvas.mapSettings().layerToMapCoordinates(layer, point_geom)
     elif type(point_geom) == QgsGeometry:
        # transform the geometry in the canvas crs to work with plane xy coordinates
        coordTransform = QgsCoordinateTransform(layer.crs(), \
                                                self.plugIn.canvas.mapSettings().destinationCrs(), \
                                                QgsProject.instance())
        g = QgsGeometry(point_geom)
        g.transform(coordTransform)
        return g
     elif (type(point_geom) == list or type(point_geom) == tuple): # list of points or geometries
        coordTransform = QgsCoordinateTransform(self.plugIn.canvas.mapSettings().destinationCrs(), \
                                                layer.crs(), \
                                                QgsProject.instance())
        res = []
        for pt in point_geom:
           if type(pt) == QgsPointXY:
              res.append(coordTransform.transform(pt))
           elif type(point_geom) == QgsGeometry:
              g = QgsGeometry(point_geom)
              g.transform(coordTransform)
              res.append(g)
        return res
     else:
        return None


# Class that manages the contextual menu of Qad commands
class QadContextualMenuClass(QMenu):

  def __init__(self, plugIn, inputType, keyWords):
     self.plugIn = plugIn
     QMenu.__init__(self, self.plugIn.canvas)
     self.connections = []
     self.localEnglishKeyWords = []
     self.localKeyWords = []
     self.initActions(inputType, keyWords)

  def __del__(self):
     """ destructor """
     self.delActions()

  def delActions(self):
     # delete and disconnect all actions for events
     for connection in self.connections:
        action = connection[0]
        slot = connection[1]
        action.triggered.disconnect(slot)
     del self.connections[:]


  def initActions(self, inputType, keyWords):
     self.delActions()
        
     msg = QadMsg.translate("ContextualCmdMenu", "Enter")
     action = QAction(msg, self)
     self.addAction(action)
     self.connections.append([action, self.enterActionByContextualMenu])

     msg = QadMsg.translate("ContextualCmdMenu", "Cancel")
     action = QAction(msg, self)
     self.addAction(action)
     self.connections.append([action, self.cancelActionByContextualMenu])
        
     if inputType & QadInputTypeEnum.POINT2D or inputType & QadInputTypeEnum.POINT3D:
        msg = QadMsg.translate("ContextualCmdMenu", "Recent Input")
        recentPtsMenu = self.addMenu(msg)
        
        ptsHistory = self.plugIn.ptsHistory
        ptsHistoryLen = len(ptsHistory)
        i = ptsHistoryLen - 1
        cmdInputHistoryMax = QadVariables.get(QadMsg.translate("Environment variables", "CMDINPUTHISTORYMAX"))
        # cycle through the history of last used points
        while i >= 0 and (ptsHistoryLen - i) <= cmdInputHistoryMax:
           strPt = pointToStringFmt(ptsHistory[i])
           i = i - 1
           action = QAction(strPt, recentPtsMenu)
           recentPtsMenu.addAction(action)
           self.connections.append([action, self.showEvaluateMsgByContextualMenu])
                   
     # cycle through the current options of the command in use
     if len(keyWords) > 0:
        # initialize the list of keywords contextual to the current command (local language)
        # separator character between keywords in local language and those in English
        self.localEnglishKeyWords = keyWords.split("_")
        self.localKeyWords = self.localEnglishKeyWords[0].split("/") # separator character for keywords

        self.addSeparator()
        for keyWord in self.localKeyWords:
           action = QAction(keyWord, self)
           self.addAction(action)
           self.connections.append([action, self.showEvaluateMsgByContextualMenu])
     else: # there are no options
        del self.localEnglishKeyWords[:] # empty the list
        del self.localKeyWords[:] # empty the list

     if inputType & QadInputTypeEnum.POINT2D or inputType & QadInputTypeEnum.POINT3D:
        self.addSeparator()
        osnapMenu = QadOsnapContextualMenuClass(self.plugIn)
        self.addMenu(osnapMenu)

     # create all connections for events
     for connection in self.connections:
        action = connection[0]
        slot = connection[1]
        action.triggered.connect(slot)


  def enterActionByContextualMenu(self):
     actualCmd = self.plugIn.QadCommands.actualCommand
     if actualCmd is not None:
        pointMapTool = actualCmd.getPointMapTool()
        if pointMapTool is not None:
           dynInput = pointMapTool.getDynamicInput()
           if dynInput is not None:
              if dynInput.anyLockedValueEdit() == True:
                 if dynInput.refreshResult() == True:
                    dynInput.showEvaluateMsg(dynInput.resStr)
                    return
              
     self.plugIn.showEvaluateMsg(None)

  
  def cancelActionByContextualMenu(self):
     self.plugIn.abortCommand()


  def showEvaluateMsgByContextualMenu(self):
     sender = self.sender()
     self.plugIn.showEvaluateMsg(sender.text())


# Class that manages the osnap contextual menu of Qad commands
class QadOsnapContextualMenuClass(QMenu):

  def __init__(self, plugIn):
     self.plugIn = plugIn
     title = QadMsg.translate("ContextualCmdMenu", "Snap Overrides")
     QMenu.__init__(self, title, self.plugIn.canvas)
     self.connections = []
     self.initActions()

  def __del__(self):
     """ destructor """
     self.delActions()


  def delActions(self):
     # delete and disconnect all actions for events
     for connection in self.connections:
        action = connection[0]
        slot = connection[1]
        action.triggered.disconnect(slot)
     del self.connections[:]

  def initActions(self):
     self.delActions()

     msg = QadMsg.translate("Snap", "Midpoint between 2 points")
     icon = QIcon(":/plugins/qad/icons/osnap_mid2p.svg")
     if icon is None:
        M2PAction = QAction(msg, self)
     else:
        M2PAction = QAction(icon, msg, self)
     self.addAction(M2PAction)
     self.connections.append([M2PAction, self.addM2PActionByPopupMenu])
     
     self.addSeparator()

     msg = QadMsg.translate("DSettings_Dialog", "Start / End")
     icon = QIcon(":/plugins/qad/icons/osnap_endLine.svg")
     if icon is None:
        addEndLineSnapTypeAction = QAction(msg, self)
     else:
        addEndLineSnapTypeAction = QAction(icon, msg, self)
     self.addAction(addEndLineSnapTypeAction)
     self.connections.append([addEndLineSnapTypeAction, self.addEndLineSnapTypeByPopupMenu])
     
     msg = QadMsg.translate("DSettings_Dialog", "Segment Start / End")
     icon = QIcon(":/plugins/qad/icons/osnap_end.svg")
     if icon is None:
        addEndSnapTypeAction = QAction(msg, self)
     else:
        addEndSnapTypeAction = QAction(icon, msg, self)        
     self.addAction(addEndSnapTypeAction)
     self.connections.append([addEndSnapTypeAction, self.addEndSnapTypeByPopupMenu])
     
     msg = QadMsg.translate("DSettings_Dialog", "Middle point")
     icon = QIcon(":/plugins/qad/icons/osnap_mid.svg")
     if icon is None:
        addMidSnapTypeAction = QAction(msg, self)
     else:
        addMidSnapTypeAction = QAction(icon, msg, self)        
     self.addAction(addMidSnapTypeAction)
     self.connections.append([addMidSnapTypeAction, self.addMidSnapTypeByPopupMenu])
     
     msg = QadMsg.translate("DSettings_Dialog", "Intersection")
     icon = QIcon(":/plugins/qad/icons/osnap_int.svg")
     if icon is None:
        addIntSnapTypeAction = QAction(msg, self)
     else:
        addIntSnapTypeAction = QAction(icon, msg, self)        
     self.addAction(addIntSnapTypeAction)
     self.connections.append([addIntSnapTypeAction, self.addIntSnapTypeByPopupMenu])
     
     msg = QadMsg.translate("DSettings_Dialog", "Intersection on extension")
     icon = QIcon(":/plugins/qad/icons/osnap_extInt.svg")
     if icon is None:
        addExtIntSnapTypeAction = QAction(msg, self)
     else:
        addExtIntSnapTypeAction = QAction(icon, msg, self)        
     self.addAction(addExtIntSnapTypeAction)
     self.connections.append([addExtIntSnapTypeAction, self.addExtIntSnapTypeByPopupMenu])
     
     msg = QadMsg.translate("DSettings_Dialog", "Extend")
     icon = QIcon(":/plugins/qad/icons/osnap_ext.svg")
     if icon is None:
        addExtSnapTypeAction = QAction(msg, self)
     else:
        addExtSnapTypeAction = QAction(icon, msg, self)        
     self.addAction(addExtSnapTypeAction)
     self.connections.append([addExtSnapTypeAction, self.addExtSnapTypeByPopupMenu])

     self.addSeparator()
    
     msg = QadMsg.translate("DSettings_Dialog", "Center")
     icon = QIcon(":/plugins/qad/icons/osnap_cen.svg")
     if icon is None:
        addCenSnapTypeAction = QAction(msg, self)
     else:
        addCenSnapTypeAction = QAction(icon, msg, self)        
     self.addAction(addCenSnapTypeAction)
     self.connections.append([addCenSnapTypeAction, self.addCenSnapTypeByPopupMenu])
    
     msg = QadMsg.translate("DSettings_Dialog", "Quadrant")
     icon = QIcon(":/plugins/qad/icons/osnap_qua.svg")
     if icon is None:
        addQuaSnapTypeAction = QAction(msg, self)
     else:
        addQuaSnapTypeAction = QAction(icon, msg, self)        
     self.addAction(addQuaSnapTypeAction)
     self.connections.append([addQuaSnapTypeAction, self.addQuaSnapTypeByPopupMenu])
    
     msg = QadMsg.translate("DSettings_Dialog", "Tangent")
     icon = QIcon(":/plugins/qad/icons/osnap_tan.svg")
     if icon is None:
        addTanSnapTypeAction = QAction(msg, self)
     else:
        addTanSnapTypeAction = QAction(icon, msg, self)        
     self.addAction(addTanSnapTypeAction)
     self.connections.append([addTanSnapTypeAction, self.addTanSnapTypeByPopupMenu])

     self.addSeparator()

     msg = QadMsg.translate("DSettings_Dialog", "Perpendicular")
     icon = QIcon(":/plugins/qad/icons/osnap_per.svg")
     if icon is None:
        addPerSnapTypeAction = QAction(msg, self)
     else:
        addPerSnapTypeAction = QAction(icon, msg, self)        
     self.addAction(addPerSnapTypeAction)     
     self.connections.append([addPerSnapTypeAction, self.addPerSnapTypeByPopupMenu])

     msg = QadMsg.translate("DSettings_Dialog", "Parallel")
     icon = QIcon(":/plugins/qad/icons/osnap_par.svg")
     if icon is None:
        addParSnapTypeAction = QAction(msg, self)
     else:
        addParSnapTypeAction = QAction(icon, msg, self)        
     self.addAction(addParSnapTypeAction)     
     self.connections.append([addParSnapTypeAction, self.addParSnapTypeByPopupMenu])

     msg = QadMsg.translate("DSettings_Dialog", "Node")
     icon = QIcon(":/plugins/qad/icons/osnap_nod.svg")
     if icon is None:
        addNodSnapTypeAction = QAction(msg, self)
     else:
        addNodSnapTypeAction = QAction(icon, msg, self)        
     self.addAction(addNodSnapTypeAction)     
     self.connections.append([addNodSnapTypeAction, self.addNodSnapTypeByPopupMenu])

     msg = QadMsg.translate("DSettings_Dialog", "Near")
     icon = QIcon(":/plugins/qad/icons/osnap_nea.svg")
     if icon is None:
        addNeaSnapTypeAction = QAction(msg, self)
     else:
        addNeaSnapTypeAction = QAction(icon, msg, self)        
     self.addAction(addNeaSnapTypeAction)     
     self.connections.append([addNeaSnapTypeAction, self.addNeaSnapTypeByPopupMenu])

     msg = QadMsg.translate("DSettings_Dialog", "Progressive")
     icon = QIcon(":/plugins/qad/icons/osnap_pr.svg")
     if icon is None:
        addPrSnapTypeAction = QAction(msg, self)
     else:
        addPrSnapTypeAction = QAction(icon, msg, self)        
     self.addAction(addPrSnapTypeAction)     
     self.connections.append([addPrSnapTypeAction, self.addPrSnapTypeByPopupMenu])

     msg = QadMsg.translate("DSettings_Dialog", "None")
     icon = QIcon(":/plugins/qad/icons/osnap_disable.svg")
     if icon is None:
        setSnapTypeToDisableAction = QAction(msg, self)
     else:
        setSnapTypeToDisableAction = QAction(icon, msg, self)        
     self.addAction(setSnapTypeToDisableAction)     
     self.connections.append([setSnapTypeToDisableAction, self.setSnapTypeToDisableByPopupMenu])

     self.addSeparator()

     msg = QadMsg.translate("DSettings_Dialog", "Object snap settings...")
     icon = QIcon(":/plugins/qad/icons/dsettings.svg")
     if icon is None:
        DSettingsAction = QAction(msg, self)
     else:
        DSettingsAction = QAction(icon, msg, self)        
     self.addAction(DSettingsAction)     
     self.connections.append([DSettingsAction, self.showDSettingsByPopUpMenu])

     # create all connections for events
     for connection in self.connections:
        action = connection[0]
        slot = connection[1]
        action.triggered.connect(slot)


  # ============================================================================
  # addSnapTypeByPopupMenu
  # ============================================================================
  def addSnapTypeByPopupMenu(self, _snapType):
     # the function must set the object snap only temporarily
     str = snapTypeEnum2Str(_snapType)
     self.plugIn.showEvaluateMsg(str)
     return
#       value = QadVariables.get(QadMsg.translate("Environment variables", "OSMODE"))
#       if value & QadSnapTypeEnum.DISABLE:
#          value =  value - QadSnapTypeEnum.DISABLE      
#       QadVariables.set(QadMsg.translate("Environment variables", "OSMODE"), value | _snapType)
#       QadVariables.save()
#       self.plugIn.refreshCommandMapToolSnapType()
        
  def addM2PActionByPopupMenu(self):
     self.plugIn.showEvaluateMsg("_M2P")      
  def addEndLineSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.END_PLINE)
  def addEndSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.END)
  def addMidSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.MID)
  def addIntSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.INT)      
  def addExtIntSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.EXT_INT)
  def addExtSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.EXT)   
  def addCenSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.CEN)      
  def addQuaSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.QUA)
  def addTanSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.TAN)
  def addPerSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PER)
  def addParSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PAR)
  def addNodSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.NOD)
  def addNeaSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.NEA)
  def addPrSnapTypeByPopupMenu(self):
     self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PR)

  def setSnapTypeToDisableByPopupMenu(self):
     value = QadVariables.get(QadMsg.translate("Environment variables", "OSMODE"))
     QadVariables.set(QadMsg.translate("Environment variables", "OSMODE"), value | QadSnapTypeEnum.DISABLE)
     QadVariables.save()      
     self.plugIn.refreshCommandMapToolSnapType()

  def showDSettingsByPopUpMenu(self):
     d = QadDSETTINGSDialog(self.plugIn)
     d.exec_()
     self.plugIn.refreshCommandMapToolSnapType()
     self.plugIn.refreshCommandMapToolAutoSnap()
     self.plugIn.refreshCommandMapToolDynamicInput()
