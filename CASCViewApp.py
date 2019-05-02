import sys, os
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QProgressBar, QAction, QTableWidget,QTableWidgetItem, QGridLayout, QHeaderView, QAbstractItemView, QTextEdit, QHBoxLayout, QMenu, QFileDialog
from PyQt5.QtGui import QIcon, QFont, QDrag, QPixmap, QPainter
from PyQt5.QtCore import pyqtSlot, Qt, QBuffer, QByteArray, QUrl, QMimeData, pyqtSignal
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5 import QtCore, QtMultimedia
from CASCUtils import beautify_filesize
from read import CASCReader
from widgets.HexViewWidget import HexViewWidget
from widgets.SaveFileWidget import SaveFileWidget
import webbrowser

class TableFolderItem(QTableWidgetItem):
    def __init__(self, text, is_folder=False, is_back_button=False, file_data=None):
        QTableWidgetItem.__init__(self,text)
        self.is_folder = is_folder
        self.is_back_button = is_back_button
        self.file_data = file_data

    def __lt__(self, other):
        if self.is_back_button:
            return True # straight out my ass
        elif other.is_back_button:
            return False
        else:
            return super(TableFolderItem, self).__lt__(other)

class FileTableWidget(QTableWidget):
    pass #a dream that will never happen (drag-drop out)

class CascViewApp(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.title = 'Shitty CASCViewer'
        self.width = 700
        self.height = 500

        self.CASCReader=None
        self.files=[]
        self.filetree=self.genFileTree()
        self.curPath=[]
        self.openWidgets=[]

        self.initUI()

    def load_casc_dir(self, dir):
        self.CASCReader = CASCReader(dir)
        self.files = self.CASCReader.list_files()
        self.filetree = self.genFileTree()
        self.curPath = []
        self.populateTable()

    def genFileTree(self):
        ftree = {'folders':{},'files':{}}
        for f in self.files:
            path = f[0].replace("\\","/").split("/")
            toptree = ftree
            for sp in path[:-1]:
                if sp not in toptree['folders']:
                    toptree['folders'][sp]={'folders':{},'files':{}}
                toptree = toptree['folders'][sp]
            toptree['files'][path[-1]]=f
        return ftree
        
    def initUI(self):
        self.setWindowTitle(self.title)
        self.resize(self.width,self.height)
        
        self.createTables()

        self.main_widget = QWidget(self)

        # Add box layout, add table to box layout and add box layout to widget
        self.layout = QGridLayout(self.main_widget)
        self.layout.addWidget(self.fileTable,0,0) 
        self.layout.addWidget(self.infoTable,0,1) 

        self.main_widget.setLayout(self.layout)
        self.setCentralWidget(self.main_widget)

        # extractAction = QAction("&", self)
        # extractAction.setShortcut("Ctrl+Q")
        # extractAction.setStatusTip('Leave The App')
        # extractAction.triggered.connect(self.close_application)

        self.statusBar()

        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('&File')
        # fileMenu.addAction(extractAction)

        # Show widget
        self.show()
    
    def populateTable(self):
        curDir = self.filetree
        for x in self.curPath:
            curDir = curDir['folders'][x]
    
        for x in range(self.fileTable.rowCount()):
            self.fileTable.removeRow(0)

        if self.curPath != []:
            self.fileTable.insertRow(self.fileTable.rowCount())
            self.fileTable.setItem(self.fileTable.rowCount()-1, 0, TableFolderItem("..",is_folder=True,is_back_button=True))

        for f in curDir['files']:
            self.fileTable.insertRow(self.fileTable.rowCount())
            self.fileTable.setItem(self.fileTable.rowCount()-1, 0, TableFolderItem(f,file_data=curDir['files'][f]))

        for f in curDir['folders']:
            self.fileTable.insertRow(self.fileTable.rowCount())
            self.fileTable.setItem(self.fileTable.rowCount()-1, 0, TableFolderItem("📁"+f,is_folder=True))
            
        self.fileTable.sortByColumn(0,0)
        self.fileTable.scrollToTop()

    def createTables(self):
        # Create tables
        self.fileTable = FileTableWidget()
        self.fileTable.setColumnCount(1)
        self.fileTable.verticalHeader().hide()
        self.fileTable.setEditTriggers(QTableWidget.NoEditTriggers)
        # self.fileTable.setSelectionMode(QAbstractItemView.SingleSelection)
        # self.fileTable.setDragDropMode(QAbstractItemView.DragOnly)
        # self.fileTable.setDragEnabled(True)
        # self.fileTable.setDropIndicatorShown(True)

        header = self.fileTable.horizontalHeader()       
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.hide()

        self.populateTable()        

        self.infoTable = QTableWidget()
        self.infoTable.setColumnCount(1)
        header = self.infoTable.horizontalHeader()       
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.hide()

        self.infoTable.verticalHeader().hide()

        self.infoTable.insertRow(0) # Name
        self.infoTable.setItem(0, 0, QTableWidgetItem(""))
        self.infoTable.insertRow(1) # size
        self.infoTable.setItem(1, 0, QTableWidgetItem(""))
        # self.infoTable.insertRow(2)
        # self.infoTable.setItem(2, 0, QTableWidgetItem(""))

        self.infoTable.setFixedWidth(200)
        self.infoTable.setSelectionMode(QAbstractItemView.NoSelection)
        self.infoTable.setEditTriggers(QTableWidget.NoEditTriggers)

        # table selection change
        self.fileTable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.fileTable.customContextMenuRequested.connect(self.on_right_click)
        self.fileTable.cellClicked.connect(self.on_click)
        self.fileTable.cellDoubleClicked.connect(self.on_dbl_click)

    def on_right_click(self, QPos=None):
        print("!")
        parent=self.sender()
        pPos=parent.mapToGlobal(QtCore.QPoint(0, 0))
        mPos=pPos+QPos
        self.rcMenu=QMenu(self)
        sitems=[x for x in self.fileTable.selectedItems() if not x.is_back_button]
        if len(sitems)>1:
            self.rcMenu.addAction('Export files').triggered.connect(lambda:self.save_items(sitems))
        else:
            item=self.fileTable.itemAt(QPos)
            if item.is_folder:
                self.rcMenu.addAction("Open Folder").triggered.connect(lambda:self.on_dbl_click(item.row(),item.column()))
                self.rcMenu.addAction('Export folder').triggered.connect(lambda:self.save_items([item]))
            else:
                self.rcMenu.addAction('View File (Autodetect)').triggered.connect(lambda:self.show_hexview_for_ckey(item.text(),item.file_data[1]))
                self.rcMenu.addAction('View Hexdump').triggered.connect(lambda:self.show_hexview_for_ckey(item.text(),item.file_data[1],"hex"))
                self.rcMenu.addAction('Export file').triggered.connect(lambda:self.save_items([item]))
                self.rcMenu.addAction('Open file outside').triggered.connect(lambda:self.show_hexview_for_ckey(item.text(),item.file_data[1],"media"))
        self.rcMenu.move(mPos)
        self.rcMenu.show()

    def save_items(self,items,dest=None):
        curDir = self.filetree
        for x in self.curPath:
            curDir = curDir['folders'][x]
        folder={'folders':{},'files':{}}
        for x in items:
            n=x.text()
            if x.is_folder:
                if x.is_back_button: continue
                folder['folders'][n[1:]]=curDir['folders'][n[1:]]
            else:
                folder['files'][n]=curDir['files'][n]
        w = SaveFileWidget(folder,dest,self)
        self.openWidgets.append(w)

    def save_file_tree(self,folder,dest):
        pass
        
    def on_click(self, row, column):
        item = self.fileTable.item(row,column)
        if not item.is_folder:
            file_info = self.CASCReader.get_file_info_by_ckey(item.file_data[1]) 
            self.infoTable.item(0,0).setText("File: "+item.text())
            self.infoTable.item(1,0).setText(f"Size: {beautify_filesize(file_info['size'])}")
            # self.infoTable.item(3,0).setText(item.text())
        else:
            if item.is_back_button: 
                self.infoTable.item(0,0).setText("Parent Directory")
                self.infoTable.item(1,0).setText("")
            else:
                curDir = self.filetree
                for x in self.curPath+[item.text()[1:]]:
                    curDir = curDir['folders'][x]
                self.infoTable.item(0,0).setText("Folder: "+item.text()[1:])
                self.infoTable.item(1,0).setText(f"Items: {len(curDir['files'])+len(curDir['folders'])}")

    def on_dbl_click(self, row, column):
        #enter directory, do nothing if it's a file
        item = self.fileTable.item(row,column)
        if item.is_folder:
            if item.is_back_button:
                self.curPath.pop()
            else:
                self.curPath.append(item.text()[1:])
            self.populateTable()
        else:
            self.show_hexview_for_ckey(item.text(),item.file_data[1])

    def show_hexview_for_ckey(self,fname,ckey,force_type=None):
        data = self.CASCReader.get_file_by_ckey(ckey)
        w = HexViewWidget()
        w.viewFile(fname,data,force_type)
        self.openWidgets.append(w)

    def closeEvent(self, e):
        for h in self.openWidgets:
            if isinstance(h, HexViewWidget) and h.tmp_file is not None:
                os.unlink(h.tmp_file)
            h.closeEvent(None)
        self.openWidgets=None
        if os.path.exists("tmp") and len(os.listdir("tmp"))==0:
            os.rmdir("tmp")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CascViewApp()
    # ex.load_casc_dir("G:/Misc Games/Warcraft III")
    ex.load_casc_dir("G:/Misc Games/Diablo III") 
    sys.exit(app.exec_())   