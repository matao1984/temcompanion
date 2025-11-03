from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication,QWidget, QMainWindow, QFileDialog, QSizePolicy, QVBoxLayout, QDialog,
                             QHBoxLayout, QApplication, QMessageBox, QProgressBar, QCheckBox, QSpinBox, QLabel)
from PyQt5.QtGui import QDropEvent, QDragEnterEvent
from concurrent.futures import ThreadPoolExecutor, as_completed
import os


from .functions import getDirectory, getFileNameType, convert_file
from .UI_elements import FilterSettingBatchConvert



#========================Batch conversion window ===================
class BatchConverter(QMainWindow):
    def __init__(self,parent):
        super().__init__(parent)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.setupUi()

        self.scale_bar = True
        self.files = None
        self.output_dir = None 
        self.get_filter_parameters()
        # Default filter settings
        self.apply_wf = False
        self.apply_absf = False
        self.apply_nl = False
        self.apply_bw = False
        self.apply_gaussian = False
        self.apply_gaussian_hp = False

        self.setAcceptDrops(True)

    def setupUi(self):
        self.setWindowTitle("Batch Conversion")
        self.setObjectName("BatchConverter")
        self.resize(400, 300)
        
        self.openfileButton = QtWidgets.QPushButton("Open \nFiles",self)
        self.openfileButton.setFixedSize(80, 60)
        self.openfileButton.setObjectName("OpenFile")
        self.openfileButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        self.openfilebox = QtWidgets.QTextEdit(self,readOnly=True)
        self.openfilebox.resize(240,60)
        self.openfilebox.setObjectName("OpenFileBox")
        self.openfilebox.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        
        self.filterButton = QtWidgets.QPushButton("Also Apply Filters",self)
        self.filterButton.setFixedSize(160, 60)
        self.filterButton.setObjectName("filterButton")
        self.filterButton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.convertlabel = QtWidgets.QLabel('Select the output format: ',self)
        
        self.convertlabel.setObjectName("ConvertTo")
        
        
        self.formatselect = QtWidgets.QComboBox(self)
        
        self.formatselect.addItems(['tiff + png','tiff', 'png', 'jpg'])
        self.formatselect.setObjectName("FormatSelect")
        
        self.setdirButton = QtWidgets.QPushButton("Output \nDirectory",self)
        self.setdirButton.setFixedSize(80, 60)
        self.setdirButton.setObjectName("SetDir")
        self.setdirButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        self.outputdirbox = QtWidgets.QTextEdit(self, readOnly=True)
        self.outputdirbox.resize(240, 40)
        self.outputdirbox.setObjectName("OutPutDirBox")
        self.outputdirbox.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        
        self.checkscalebar = QtWidgets.QCheckBox("Add scale bar to images",self)       
        self.checkscalebar.setChecked(True)
        self.checkscalebar.setObjectName("checkscalebar")
        
        self.metadatacheck = QCheckBox("Export metadata", self)
        self.metadatacheck.setChecked(False)
        self.metadatacheck.setObjectName("metadatacheck")
        
        self.convertButton = QtWidgets.QPushButton("Convert \nAll",self)
        self.convertButton.setFixedSize(80, 60)
        self.convertButton.setObjectName("convertButton")
        self.convertButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        # Thread count control
        self.thread_label = QLabel("Number of threads:", self)
        self.thread_spinbox = QSpinBox(self)
        self.thread_spinbox.setMinimum(1)
        self.thread_spinbox.setMaximum(os.cpu_count() or 8)
        self.thread_spinbox.setValue(min(8, os.cpu_count() or 8))
        self.thread_spinbox.setToolTip(f"Number of parallel threads for batch processing (1-{os.cpu_count() or 8})")
        self.thread_spinbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        
        self.convertbox = QtWidgets.QTextEdit(self, readOnly=True)
        self.convertbox.resize(240,40)
        self.convertbox.setObjectName("convertbox")
        self.convertbox.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        
        layout = QVBoxLayout()
        layout1 = QHBoxLayout()
        layout1.addWidget(self.openfileButton)
        layout1.addWidget(self.openfilebox)
        layout2 = QHBoxLayout()
        layout2_1 = QVBoxLayout()
        layout2_1_1 = QHBoxLayout()
        
        layout2_1_1.addWidget(self.convertlabel)
        layout2_1_1.addWidget(self.formatselect)
        
        
        #layout2_1.addLayout(layout2_1_1)
        layout2_1.addWidget(self.checkscalebar)
        layout2_1.addWidget(self.metadatacheck)
        layout2.addLayout(layout2_1)
        layout2.addWidget(self.filterButton)
        layout2.addStretch(1)
        layout3 = QHBoxLayout()
        layout3.addWidget(self.setdirButton)
        layout3.addWidget(self.outputdirbox)
        layout4 = QHBoxLayout()
        layout4.addWidget(self.convertButton)
        layout4.addWidget(self.convertbox)
        layout5 = QHBoxLayout()
        layout5.addWidget(self.thread_label)
        layout5.addWidget(self.thread_spinbox)
        layout5.addStretch(1)
        layout.addLayout(layout1)
        layout.addLayout(layout2_1_1)
        layout.addLayout(layout2)
        layout.addLayout(layout3)
        layout.addLayout(layout4)
        layout.addLayout(layout5)
        layout.addWidget(self.progress_bar)
        
        self.central_widget.setLayout(layout)

        
#====================================================================
# Connect all functions
        self.openfileButton.clicked.connect(self.openfile)
        self.setdirButton.clicked.connect(self.set_dir)
        
        self.filterButton.clicked.connect(self.filter_settings)
        self.checkscalebar.stateChanged.connect(self.set_scalebar)
        self.convertButton.clicked.connect(self.convert_emd)
        
        
        
    def set_scalebar(self):
        self.scale_bar = self.checkscalebar.isChecked()
        
    def get_filter_parameters(self):        
        # Read default filter parameters from the main window
        self.filter_parameters = self.parent().filter_parameters
        
#===================================================================
# Open file button connected to OpenFile

    def openfile(self):
        self.files, self.filetype = QFileDialog.getOpenFileNames(self,"Select files to be converted:", "",
                                                     "Velox emd Files (*.emd);;TIA ser Files (*.ser);;DigitalMicrograph Files (*.dm3 *.dm4);;Tiff Files (*.tif *.tiff);;Image Formats (*.tif *.tiff *.jpg *.jpeg *.png *.bmp);;Pickle Dictionary Files (*.pkl)")
        if self.files:
            self.output_dir = getDirectory(self.files[0])
            self.outputdirbox.setText(self.output_dir)
            self.openfilebox.setText('')
            for file in self.files:
                self.openfilebox.append(file)
                QApplication.processEvents()
        else: 
            self.files = None # Canceled, set back to None
            
    
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files:
            self.files = files
            self.output_dir = getDirectory(self.files[0])
            self.outputdirbox.setText(self.output_dir)
            self.openfilebox.setText('')
            for file in self.files:
                self.openfilebox.append(file)
                QApplication.processEvents()
            event.acceptProposedAction() 
                


#===================================================================
# Output directory button connected to SetDir

    def set_dir(self):
        output_dir = QFileDialog.getExistingDirectory(self, "Select Directory")
        if output_dir:
            self.output_dir = str(output_dir)
            self.outputdirbox.setText(self.output_dir)
            QApplication.processEvents()
            
#===================================================================
# Let's go button connected to convertButton
    def refresh_output(self, text):
        self.convertbox.append(text)
        QApplication.processEvents()
        
    def convert_emd(self): 
        if self.files == None:
            QMessageBox.warning(self, 'No files loaded', 'Select file(s) to convert!')
            
        else:
            self.refresh_output('Converting, please wait...')
            self.f_type = self.formatselect.currentText()
           
            # Load filter parameters 
            delta_wf = int(self.filter_parameters['WF Delta'])
            order_wf = int(self.filter_parameters['WF Bw-order'])
            cutoff_wf = float(self.filter_parameters['WF Bw-cutoff'])
            delta_absf = int(self.filter_parameters['ABSF Delta'])
            order_absf = int(self.filter_parameters['ABSF Bw-order'])
            cutoff_absf = float(self.filter_parameters['ABSF Bw-cutoff'])
            delta_nl = int(self.filter_parameters['NL Delta'])
            order_nl = int(self.filter_parameters['NL Bw-order'])
            N = int(self.filter_parameters['NL Cycles'])
            cutoff_nl = float(self.filter_parameters['NL Bw-cutoff'])
            order_bw = int(self.filter_parameters['Bw-order'])
            cutoff_bw = float(self.filter_parameters['Bw-cutoff'])
            cutoff_gaussian = float(self.filter_parameters['GS-cutoff'])
            cutoff_gaussian_hp = float(self.filter_parameters['GS-HP-cutoff'])
            
            save_metadata = self.metadatacheck.isChecked()
            
            # Get thread count from spinbox
            num_threads = self.thread_spinbox.value()

            # A separate thread for file conversion
            self.thread = QThread()

            self.worker = BatchConversionWorker(self.files, self.output_dir, self.f_type, save_metadata=save_metadata, scalebar = self.scale_bar,
                                 apply_wf = self.apply_wf, delta_wf = delta_wf, order_wf = order_wf, cutoff_wf = cutoff_wf,
                                 apply_absf = self.apply_absf, delta_absf = delta_absf, order_absf = order_absf, cutoff_absf = cutoff_absf,
                                 apply_nl = self.apply_nl, N = N, delta_nl = delta_nl, order_nl = order_nl, cutoff_nl = cutoff_nl,
                                 apply_bw = self.apply_bw, order_bw = order_bw, cutoff_bw = cutoff_bw,
                                 apply_gaussian = self.apply_gaussian, cutoff_gaussian = cutoff_gaussian,
                                 apply_gaussian_hp = self.apply_gaussian_hp, cutoff_gaussian_hp = cutoff_gaussian_hp,
                                 num_threads = num_threads)

            self.worker.moveToThread(self.thread)

            self.thread.started.connect(lambda: self.progress_bar.setVisible(True))
            self.thread.started.connect(self.worker.run)
            self.worker.progress.connect(self.refresh_output)
            self.worker.finished.connect(lambda: self.progress_bar.setVisible(False))  
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater) 
            self.thread.finished.connect(self.thread.deleteLater)            
            self.worker.finished.connect(lambda: self.refresh_output("Conversion finished!")) 
            self.thread.start()
                         
            
            
#================ Define filter settings function ============================
    
    def filter_settings(self):
        dialog = FilterSettingBatchConvert(self.apply_wf, self.apply_absf, self.apply_nl,
                                      self.apply_bw, self.apply_gaussian, self.apply_gaussian_hp,
                                      self.filter_parameters, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            # Update filter settings based on user input
            self.apply_wf = dialog.apply_wf
            self.apply_absf = dialog.apply_absf
            self.apply_nl = dialog.apply_nl
            self.apply_bw = dialog.apply_bw
            self.apply_gaussian = dialog.apply_gaussian
            self.apply_gaussian_hp = dialog.apply_gaussian_hp
            self.filter_parameters = dialog.parameters
     


                    

#================Batch Conversion Worker Thread====================================
class BatchConversionWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, files, *args, num_threads=None, **kwargs):
        super().__init__()
        self.files = files
        self.args = args
        self.kwargs = kwargs
        # Use provided thread count, or default to 8 (but don't exceed available CPU count)
        if num_threads is not None:
            self.max_workers = num_threads
        else:
            self.max_workers = min(8, os.cpu_count() or 1)

    def process_single_file(self, file):
        """Process a single file - will be called by each thread"""
        try:
            ext = getFileNameType(file)[1].lower()
            if ext == 'emd':
                filetype = 'Velox emd Files (*.emd)'
            elif ext in ['dm3', 'dm4']:
                filetype = 'DigitalMicrograph Files (*.dm3 *.dm4)'
            elif ext == 'ser':
                filetype = 'TIA ser Files (*.ser)'
            elif ext in ['tif', 'tiff']:
                filetype = 'Tiff Files (*.tif *.tiff)'
            elif ext in ['jpg', 'jpeg', 'png', 'bmp']:
                filetype = 'Image Formats (*.tif *.tiff *.jpg *.jpeg *.png *.bmp)'
            elif ext == 'pkl':
                filetype = 'Pickle Dictionary Files (*.pkl)'
            else:
                return (file, False, 'Unsupported file format')

            convert_file(file, filetype, *self.args, **self.kwargs)
            return (file, True, 'Converted successfully')

        except Exception as e:
            return (file, False, str(e))

    def run(self):
        """Run batch conversion with multithreading"""
        total_files = len(self.files)
        completed = 0
        
        msg = f"Starting batch conversion of {total_files} file(s) using {self.max_workers} threads..."
        self.progress.emit(msg)

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all files for processing
            future_to_file = {executor.submit(self.process_single_file, file): file 
                             for file in self.files}
            
            # Process completed tasks as they finish
            for future in as_completed(future_to_file):
                file, success, message = future.result()
                completed += 1
                
                if success:
                    msg = f"[{completed}/{total_files}] '{file}' has been converted"
                else:
                    msg = f"[{completed}/{total_files}] '{file}' has been skipped. Error: {message}"
                
                self.progress.emit(msg)

        self.finished.emit()