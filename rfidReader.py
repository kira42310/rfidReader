# -*- coding: UTF-8 -*-
#import platform
import ctypes
import time
import os
import wx
import serial.tools.list_ports
import pymysql
import multitimer
from configparser import ConfigParser

class rfid:

    bdev = ctypes.c_ubyte(0xff) # some specific value for connect to rfid device
    nretry = 5

    # Init function, load dll file and close connection device if open before
    def __init__( self ) -> None:
        currentDir = os.getcwd()
        self.objdll = ctypes.windll.LoadLibrary( currentDir+'\\CFComApi.dll' )
        self.objdll.CFCom_CloseDevice()
        self.state = False

    # function for open connection to rfid device
    def openConnect( self ):
        for i in range( 0, self.nretry ): 
            if( self.objdll.CFCom_OpenDevice( "COM3".encode(), 115200 ) == 1 ):
                self.objdll.CFCom_ClearTagBuf()
                self.state = True
                return 1
        return 0

    # function to close connection to device
    def closeConnect( self ):
        self.state = False
        self.objdll.CFCom_CloseDevice()
        return 1
        
    # function for get tag value from tag device need
    def getTagID( self ) -> str:
        if( not self.state ): return 0
        passw = bytes(4)
        mem = ctypes.c_ubyte(0x01)
        startaddr = ctypes.c_ubyte(0x02)
        addrlength = ctypes.c_ubyte(0x06)
        resultTMP = bytes(12)
        result = ''
        for i in range( 0, self.nretry ):
            self.objdll.CFCom_ReadCardG2( self.bdev, passw, mem, startaddr, addrlength, resultTMP )
            result = self.convertBytetoStr( resultTMP )
            if( result != '000000000000' ): break
            time.sleep(1)
        return result

    # function for convert from byte to hex first and convert to string
    def convertBytetoStr( self, resultTMP: bytes ) -> str:
        result = ''
        for i in range( 0, len(resultTMP) ):
            result += str( hex(resultTMP[i]) )[2:]
        return result

class mysqlConnecter:

    charsetdb = 'utf8mb4'

    # init function read config from config.ini file
    def __init__(self) -> None:
        self.config = ConfigParser()
        self.config.optionxform = str
        self.config.read( 'config.ini' )
        self.hostdb = self.config.get( 'db', 'hostdb' )
        self.portdb = int( self.config.get( 'db', 'portdb' ) )
        self.userdb = self.config.get( 'db', 'userdb' )
        self.passdb = self.config.get( 'db', 'passdb' )
        self.dbname = self.config.get( 'db', 'dbname' )

    # insert to database function take sql as argument
    def insertItem( self, sql ):
        db = pymysql.connect( host = self.hostdb, port = self.portdb, user = self.userdb, password = self.passdb, db = self.dbname, charset = self.charsetdb, cursorclass = pymysql.cursors.DictCursor )
        try:
            cur = db.cursor()
            cur.execute( sql )
            db.commit()
        except pymysql.err.MySQLError as e:
            print( e )
        finally:
            db.close()
        return 1

    # get datas from database take sql as argument
    def getItem( self, sql ):
        db = pymysql.connect( host = self.hostdb, port = self.portdb, user = self.userdb, password = self.passdb, db = self.dbname, charset = self.charsetdb, cursorclass = pymysql.cursors.DictCursor )
        try:
            cur = db.cursor()
            cur.execute( sql )
        except pymysql.err.MySQLError as e:
            print( e )
        finally:
            db.close()
        return cur.fetchall()

    # function to create sql and insert to database by call insertItem function
    def insertPallet( self, tagID, lotWarehouseID, lotProductID, quantity ) -> int:
        sql = ( "INSERT INTO pallet "
        "(tagID,lot_warehouse_id,lot_product_id,quantity,state,date) "
        "VALUES ('"+ tagID +"','"+ lotWarehouseID +"','"+ lotProductID +"','"+ quantity +"','transfer',NOW() )" )
        self.insertItem( sql )
        return 1

    def updatePallet( self, palletID ):
        sql = ( "UPDATE pallet SET state = 'out' "
        "WHERE pallet.id = " + palletID )
        self.insertItem( sql )
        return 1

    # function to create sql and get lot warehouse data from database by call getItem function
    def getLotWarehouse( self ):
        sql = "SELECT * FROM lot_warehouse "
        return self.getItem( sql )

    # function to create sql and get lot product data from database by call getItem function
    def getLotProduct( self ):
        sql = "SELECT * FROM lot_product "
        return self.getItem( sql )

    # function to create sql and get cart data from database by call getItem function
    def getCart( self ):
        sql = "SELECT * FROM cart "
        return self.getItem( sql )

    # function for save option to config.ini file ( UI is not complete )
    def saveOption( self, hostdb: str, portdb: int, userdb: str, passdb: str, dbname: str ):
        self.hostdb = hostdb
        self.portdb = portdb
        self.userdb = userdb
        self.passdb = passdb
        self.dbname = dbname
        self.config.set( 'db', 'hostdb', hostdb )
        self.config.set( 'db', 'portdb', str( portdb ) )
        self.config.set( 'db', 'userdb', userdb )
        self.config.set( 'db', 'passdb', passdb )
        self.config.set( 'db', 'dbname', dbname )
        with open( 'config.ini', 'w' ) as configfile:
            self.config.write( configfile )

    # function for replace save option from default to config.ini file ( UI is not complete )
    def defaultOption( self ):
        self.hostdb = self.config.get( 'default', 'hostdb' )
        self.portdb = int( self.config.get( 'default', 'portdb' ) )
        self.userdb = self.config.get( 'default', 'userdb' )
        self.passdb = self.config.get( 'default', 'passdb' )
        self.dbname = self.config.get( 'default', 'dbname' )
        self.config.set( 'db', 'hostdb', self.hostdb )
        self.config.set( 'db', 'portdb', str( self.portdb ) )
        self.config.set( 'db', 'userdb', self.userdb )
        self.config.set( 'db', 'passdb', self.passdb )
        self.config.set( 'db', 'dbname', self.dbname )
        with open( 'config.ini', 'w' ) as configfile:
            self.config.write( configfile )

    def debugtest( self ):
        print( self.hostdb, self.portdb, self.userdb, self.passdb, self.dbname )

class rfidUI( wx.Frame ):

    title = 'RFID UI'
    vborder = 310
    hborder = 320
    uMargin = 5
    txtBoxSize = ( 200, -1 )
    labelBoxSize = ( 80, -1 )
    pdQuantity = '0'
    rfidThread = None
  
    # init of UI class
    def __init__(self) -> None:
        super().__init__( parent = None, title = self.title, size = ( self.hborder, self.vborder ), style = wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER ^ wx.MAXIMIZE_BOX )

        # create rfid object
        self.rfid = rfid()

        # create mysql object
        self.mysql = mysqlConnecter()

        # create wx panel and box sizer
        panel = wx.Panel(self)
        vbox = wx.BoxSizer( wx.VERTICAL )
        connectionBox = wx.BoxSizer( wx.HORIZONTAL )
        tagInfoBox = wx.BoxSizer( wx.VERTICAL )
        btnBox = wx.BoxSizer( wx.HORIZONTAL )
        # testBox = wx.BoxSizer( wx.HORIZONTAL )

        # connection section UI
        labelCom = wx.StaticText( panel, label = 'COM' )
        connectionBox.Add( labelCom, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, self.uMargin )
        comportList = [ port.name for port in serial.tools.list_ports.comports() ]
        comCombo = wx.ComboBox( panel, choices = comportList, value = comportList[0] )
        connectionBox.Add( comCombo, 0, wx.ALL, self.uMargin )
        self.btnOpen = wx.Button( panel, label = 'Open' )
        btnClose = wx.Button( panel, label = 'Close' )
        connectionBox.Add( self.btnOpen, 0, wx.ALL, self.uMargin )
        connectionBox.Add( btnClose, 0, wx.ALL, self.uMargin )
        self.btnOpen.Bind( wx.EVT_BUTTON, self.onOpenConnection )
        btnClose.Bind( wx.EVT_BUTTON, self.onCloseConnection )

        # tag section UI
        tagIDLine = wx.BoxSizer( wx.HORIZONTAL )
        labelTagID = wx.StaticText( panel, label = 'Tag ID', size = self.labelBoxSize )
        self.textTagID = wx.TextCtrl( panel, style = wx.TE_READONLY | wx.TE_CENTER, size = self.txtBoxSize )
        tagIDLine.Add( labelTagID, 0, wx.ALL, self.uMargin )
        tagIDLine.Add( self.textTagID, 0, wx.ALL, self.uMargin )
        tagLotWLine = wx.BoxSizer( wx.HORIZONTAL )
        labelTagLotW = wx.StaticText( panel, label = 'Lot warehouse', size = self.labelBoxSize )
        # textTagRow = wx.TextCtrl( panel, value = self.tagRow, style = wx.TE_READONLY | wx.TE_CENTER, size = self.txtBoxSize )
        # tagRowLine.Add( textTagRow, 0, wx.ALL | wx.CENTER, self.uMargin )
        self.lotWList = self.mysql.getLotWarehouse()
        lotWCList = [ str( lot['id'] )+','+lot['name'] for lot in self.lotWList ]
        self.lotWCombo = wx.ComboBox( panel, choices = lotWCList, value = lotWCList[0], size = self.txtBoxSize )
        tagLotWLine.Add( labelTagLotW, 0, wx.ALL | wx.CENTER, self.uMargin )
        tagLotWLine.Add( self.lotWCombo, 0, wx.ALL, self.uMargin )
        tagLotPLine = wx.BoxSizer( wx.HORIZONTAL )
        labelTagLotP = wx.StaticText( panel, label = 'Lot product', size = self.labelBoxSize )
        self.lotPList = self.mysql.getLotProduct()
        lotPCList = [ str( lot['id'] ) + ',' + lot['name'] for lot in self.lotPList ]
        self.lotPCombo = wx.ComboBox( panel, choices = lotPCList, value = lotPCList[0], size = self.txtBoxSize )
        tagLotPLine.Add( labelTagLotP, 0, wx.ALL | wx.CENTER, self.uMargin )
        tagLotPLine.Add( self.lotPCombo, 0, wx.ALL, self.uMargin )
        tagCartLine = wx.BoxSizer( wx.HORIZONTAL )
        labelTagCart = wx.StaticText( panel, label = 'Cart number', size = self.labelBoxSize )
        cartList = [ str( lot['id'] ) for lot in self.mysql.getCart() ]
        self.cartCombo = wx.ComboBox( panel, choices = cartList, value = cartList[0], size = self.txtBoxSize )
        tagCartLine.Add( labelTagCart, 0, wx.ALL | wx.CENTER, self.uMargin )
        tagCartLine.Add( self.cartCombo, 0, wx.ALL, self.uMargin )
        pdQuantityLine = wx.BoxSizer( wx.HORIZONTAL )
        labelPDQuantity = wx.StaticText( panel, label = 'Quantity', size = self.labelBoxSize )
        self.textPDQuantity = wx.TextCtrl( panel, value = self.pdQuantity, style = wx.TE_CENTER, size = self.txtBoxSize )
        pdQuantityLine.Add( labelPDQuantity, 0, wx.ALL | wx.CENTER, self.uMargin )
        pdQuantityLine.Add( self.textPDQuantity, 0, wx.ALL | wx.CENTER, self.uMargin )
        tagInfoBox.Add( tagIDLine, 0, wx.ALL )
        tagInfoBox.Add( tagLotWLine, 0, wx.ALL )
        tagInfoBox.Add( tagLotPLine, 0, wx.ALL )
        tagInfoBox.Add( tagCartLine, 0, wx.ALL )
        tagInfoBox.Add( pdQuantityLine, 0, wx.ALL )

        # buttons section UI
        # btnGetTagID = wx.Button( panel, label = 'Get Tag ID' )
        btnAddtoDB = wx.Button( panel, label = 'Add' )
        btnDelfromDB = wx.Button( panel, label = 'Delete' )
        # btnBox.Add( btnGetTagID, 0, wx.ALL, self.uMargin )
        btnBox.Add( btnAddtoDB, 0, wx.ALL, self.uMargin )
        btnBox.Add( btnDelfromDB, 0, wx.ALL, self.uMargin )
        # btnGetTagID.Bind( wx.EVT_BUTTON, self.onGetTagID )
        btnAddtoDB.Bind( wx.EVT_BUTTON, self.onAddToDB )

        # # test database button
        # btnSaveDB = wx.Button( panel, label = 'save' )
        # btnprint = wx.Button( panel, label = 'print' )
        # testBox.Add( btnSaveDB, 0, wx.ALL | wx.CENTER, self.uMargin )
        # testBox.Add( btnprint, 0, wx.ALL | wx.CENTER, self.uMargin )
        # btnSaveDB.Bind( wx.EVT_BUTTON, self.savedb )
        # btnprint.Bind( wx.EVT_BUTTON, self.printdb )

        # add components to main component
        vbox.Add( connectionBox, 0, wx.ALL | wx.ALIGN_LEFT )
        vbox.Add( tagInfoBox, 0, wx.ALL | wx.ALIGN_LEFT )
        vbox.Add( btnBox, 0, wx.ALL | wx.ALIGN_LEFT )
        # vbox.Add( testBox, 0, wx.ALL | wx.ALIGN_CENTER )
        panel.SetSizer(vbox)
        self.Show()

        # bind exit event to function exitHandler
        self.Bind(wx.EVT_CLOSE, self.exitHandler )

    # # debug db
    # def savedb( self, event ):
    #     self.mysql.saveOption()
    # def printdb( self, event ):
    #     self.mysql.debugtest()
    
    # action for open connection button and start thread for scan rfid every 2 secs
    def onOpenConnection( self, event ):
        self.btnOpen.Disable()
        self.rfidThread = multitimer.MultiTimer( 2.0, function = self.scanRfid )
        self.rfidThread.start()
        print( self.rfid.openConnect() )

    # action for close connection button
    def onCloseConnection( self, event ):
        self.btnOpen.Enable()
        if( self.rfidThread != None ): self.rfidThread.stop()
        print( self.rfid.closeConnect() )

    # action for get tag id button
    def onGetTagID( self, event ):
        tagID = self.rfid.getTagID()
        self.textTagID.SetValue( tagID )
        print( tagID )

    # action for insert to database button
    def onAddToDB( self, event ):
        print( self.mysql.insertPallet( self.textTagID.GetValue(), self.lotWCombo.GetValue(), self.lotPCombo.GetValue(), self.textPDQuantity.GetValue() ) )

    # function for scan rfid thread
    def scanRfid( self ):
        tagID = self.rfid.getTagID()
        print( tagID )
        if( tagID != '000000000000' ):
            self.textTagID.SetValue( str(tagID) )

    # function for clear connection and thread before application exit
    def exitHandler( self, event ):
        self.rfid.closeConnect()
        if( self.rfidThread != None ): self.rfidThread.stop()
        self.Destroy()

# test = rfid()
# print( test.openConnect() )
# print( test.getTagID() )

if __name__ == '__main__':
    app = wx.App()
    frame = rfidUI()
    app.MainLoop()

# if platform.system() == 'Windows':
# #    Objdll = ctypes.windll.LoadLibrary('E:\\PycharmProjects\\CFComApi.dll')
#     Objdll = ctypes.windll.LoadLibrary('C:\\CFComApi.dll')

# #elif platform.system() == 'Linux':
# #   libc = ctypes.windll.LoadLibrary('libCFComApi.a')
# print(Objdll)

# if Objdll.CFCom_OpenDevice("COM3".encode(), 115200) == 1:   # open device
#     print("OpenSuccess")
# else:
#     print("OpenError")

# Objdll.CFCom_ClearTagBuf()    # start to get data

# from ctypes import *
# import time

# """ while True:
#     arrBuffer = bytes(9182)
#     iTagLength = c_int(0)
#     iTagNumber = c_int(0)
# #    ret = Objdll.CFCom_GetTagBuf(arrBuffer, byref(iTagLength), byref(iTagNumber))
#     ret = Objdll.CFCom_GetDeviceSystemInfo('0xFF',3)
#     time.sleep(1) """
# bdev = ctypes.c_ubyte(0xff)
# #pucsysteminfo = ctypes.c_ubyte(0)
# #print(Objdll.CFCom_GetDeviceSystemInfo(bdev,ctypes.pointer(pucsysteminfo)))
# pucsysteminfo = bytes(9)
# """ print(Objdll.CFCom_GetDeviceSystemInfo(bdev,pucsysteminfo))
# for i in range( 0 , 9 ):
#     print( hex(pucsysteminfo[i]) ) """
# byteParamAddress = ctypes.c_ubyte(0x01)
# byteValue = ctypes.c_ubyte(0)
# print(ctypes.pointer(byteValue))
# print( byteValue.value )
# print(Objdll.CFCom_ReadDeviceOneParam(bdev,byteParamAddress,ctypes.pointer(byteValue)))
# print( byteValue.value )
# passw = bytes(4)
# mem = ctypes.c_ubyte(0x01)
# startaddr = ctypes.c_ubyte(0x02)
# addrlength = ctypes.c_ubyte(0x06)
# result = bytes(12)
# print(Objdll.CFCom_ReadCardG2(bdev,passw,mem,startaddr,addrlength,result))
# print('start')
# print(result)
# for i in range( 0, len(result)):
#     print( hex(result[i]) )
# print('end')
# print(type(str(result[0])))
#arrBuffer = bytes(9182)
#iTagLength = c_int(0)
#iTagNumber = c_int(0)
#print(Objdll.CFCom_GetTagBuf(arrBuffer, byref(iTagLength), byref(iTagNumber)))
#print( hex(arrBuffer) )