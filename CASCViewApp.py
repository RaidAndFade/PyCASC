import sys, os
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem, QGridLayout, QHeaderView, QAbstractItemView, QTextEdit, QHBoxLayout, QMenu, QFileDialog
from PyQt5.QtGui import QIcon, QFont, QDrag, QPixmap, QPainter
from PyQt5.QtCore import pyqtSlot, Qt, QBuffer, QByteArray, QUrl, QMimeData
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5 import QtCore, QtMultimedia
from read import CASCReader
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

class HexViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.rowlen = 0x10

    def showMedia(self,external_viewer=False):
        c=0
        self.tmp_file=f"tmp/{c}.{self.ext}"
        if not os.path.exists("tmp"): os.mkdir("tmp")
        while os.path.exists(self.tmp_file):
            c+=1
            self.tmp_file=f"tmp/{c}.{self.ext}"
        with open(self.tmp_file,"wb+") as f:
            f.write(self.content)
        webbrowser.open(os.path.join(os.getcwd(),self.tmp_file))
        self.close()

    def showText(self):
        self.text_edit.setText(self.content.decode("utf-8"))
        self.text_edit.show()

    def showHexdump(self):
        t = ""

        hexstrlen = self.rowlen*3
        charstrlen = self.rowlen

        for x in range(0,len(self.content)//self.rowlen,self.rowlen):
            section = self.content[x:x+self.rowlen]
            hexstr = " ".join([f"{y:02x}" for y in section])
            charstr = "".join([chr(y) if 0x20 <= y <= 0x7E else "." for y in section])
            t+=f"{x:06x} {hexstr.ljust(hexstrlen)} {charstr.ljust(charstrlen)}\n"

        self.text_edit.setText(t)
        self.text_edit.show()

    def viewFile(self,filename,content,file_type=None):
        self.text_edit.setText("Loading your file... Please wait")
        self.content = content

        self.ext = os.path.splitext(filename)[1][1:]
        if file_type is None:
            excemptedChars = [0xd,0xa,0x9]
            import filetype
            g = filetype.guess(content[:4096])
            if g is not None and g.mime.split("/")[0] in ['video','audio']:
                file_type=g.mime.split("/")[0]
                self.ext=g.extension
            elif (g is None or g.mime.split("/")[0] not in ['application']) and sum([0x20 <= x <= 0x7E or x in excemptedChars for x in content])==len(content):
                file_type="txt"
        self.type = file_type

        if file_type=="txt": # show strings as normal text files
            self.setWindowTitle(f"TextView: Viewing {filename}")
            self.showText()
        elif file_type in ["audio","video","media"]: # play the audio/video externally   
            self.setWindowTitle(f"MediaView: Viewing {filename}")
            self.showMedia()
        else: # show binary data in hexview
            self.setWindowTitle(f"HexView: Viewing {filename}")
            self.showHexdump()
        # else:
        #     raise Exception("Unsupported datatype passed to viewFile")

    def initUI(self):
        self.setWindowTitle("FileView: Empty")
        self.setMinimumWidth(625)
        self.setMinimumHeight(200)
        self.resize(625,300)

        self.text_edit = QTextEdit(self)
        self.text_edit.setText("Close this window if you see this text.")
        self.text_edit.setFont(QFont("Courier New",10))
        self.text_edit.setReadOnly(True)
        self.text_edit.hide()

        self.tmp_file = None

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.text_edit)
        self.setLayout(self.layout)
        self.show()

class SaveFileWidget(QWidget):
    def __init__(self, items, cascviewapp): 
        """
        items is the same format as created in genFileTree, folder:{'folders':{},'files':{}} file:'name'=>result from read.r_idx
        """
        super().__init__()
        self.items = items
        self.cascviewapp = cascviewapp

    def initUI(self):
        self.setWindowTitle("File Exporter")
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)
        self.resize(300,200)
        items_to_save = {} # dest_path - ckey
        if 'folders' in self.items:
            

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
        self.openHexWidgets=[]

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
            path = f[0].split("/")
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
        self.infoTable.insertRow(1) # 
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

    def beautify_filesize(self, i):
        t,c=["","K","M","G","T"],0
        while i>1024:i//=1024;c+=1
        return str(i)+t[c]+"B"

    def on_right_click(self, QPos=None):
        print("!")
        parent=self.sender()
        pPos=parent.mapToGlobal(QtCore.QPoint(0, 0))
        mPos=pPos+QPos
        self.rcMenu=QMenu(self)
        sitems=self.fileTable.selectedItems()
        if len(sitems)>1:
            self.rcMenu.addAction('Save files').triggered.connect(lambda:self.save_items(sitems))
        else:
            item=self.fileTable.itemAt(QPos)
            if item.is_folder:
                self.rcMenu.addAction("Open Folder").triggered.connect(lambda:self.on_dbl_click(item.row(),item.column()))
            else:
                self.rcMenu.addAction('View File (Autodetect)').triggered.connect(lambda:self.show_hexview_for_ckey(item.text(),item.file_data[1]))
                self.rcMenu.addAction('View Hexdump').triggered.connect(lambda:self.show_hexview_for_ckey(item.text(),item.file_data[1],"hex"))
                self.rcMenu.addAction('Save file').triggered.connect(lambda:self.save_items(item))
                self.rcMenu.addAction('Open file outside').triggered.connect(lambda:self.show_hexview_for_ckey(item.text(),item.file_data[1],"media"))
        self.rcMenu.move(mPos)
        self.rcMenu.show()

    def save_items(self,items,dest=None):
        w = SaveFileWidget(items,dest,self)
        self.openWidgets.append(w)

    def save_file_tree(self,folder,dest):
        pass
        
    def on_click(self, row, column):
        item = self.fileTable.item(row,column)
        if not item.is_folder:
            file_info = self.CASCReader.get_file_info_by_ckey(item.file_data[1]) 
            self.infoTable.item(0,0).setText("File: "+item.text())
            self.infoTable.item(1,0).setText(f"Size: {self.beautify_filesize(file_info['size'])}")
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

    def save_by_ckey(self, fname, ckey, dest=None):
        data = self.CASCReader.get_file_by_ckey(ckey)
        name = dest or QFileDialog.getSaveFileName(self, f"Save {fname} as...",os.path.join(os.getcwd(),fname))[0]
        if name == '': 
            return
        with open(name,'wb+') as f:
            f.write(data)

    def show_hexview_for_ckey(self,fname,ckey,force_type=None):
        data = self.CASCReader.get_file_by_ckey(ckey)
        w = HexViewWidget()
        w.viewFile(fname,data,force_type)
        self.openWidgets.append(w)

    def closeEvent(self, e):
        for h in self.openWidgets:
            if isinstance(h, HexViewWidget) and h.tmp_file is not None:
                os.unlink(h.tmp_file)
            h = None
        if os.path.exists("tmp") and len(os.listdir("tmp"))==0:
            os.rmdir("tmp")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CascViewApp()
    ex.load_casc_dir("G:/Misc Games/Warcraft III")
    sys.exit(app.exec_())  