# -*- coding: utf-8 -*-

# Change history
# 2024-12-15 v.01
# First version!
# 2024-12-29 v0.2
# New feature: Extract line profile from an image. 
#  - The line width can be defined.
#  - Customize the plot apperance, e.g., color, xlim, ylim.
#  - Measure the line profile both horizontally and vertically with mouse drag
# Improved FFT measurement to be more robust and accurate
# Added "Cancel" button to the crop function
# Added export metadata to json and pkl
# Added angle measurement for distance measurement
# 2025-01-10 v0.3
# Fixed filter parameters cannot be set
# Added two low-pass filters: Butterworth and Gaussian
# Remove filter menu on FFT images
# Added operations on image stacks, including cropping, rotating, alignment (cross correlation and optical flow), and integration
# Improved font and color for the frame slider for image stacks
# 2025-01-15 v0.4
# New feature: Live FFT with resizable window
# Added axes viewer to view image size, scale, etc.
# Hold shift key to crop a square
# Import image formats like tif, png, jpg, etc, both rgb and grayscale
# 2025-01-22 v0.5
# The line in measuurement and lineprofile modes can be dragged and resized interactively.
# Added scalebar customization: turn on/off, color, location, etc.
# Copy image directly to the clipboard and paste in Power Point, etc.
# 2025-01-27   v0.6
# Fixed crop and crop stack have the same effect in stack images
# Improved speed for interactive measurement and line profile
# Improved measurement results displaying
# Improved units convertion between image and FFT. Now can compute FFT from uncalibrated images and diffraction patterns.
# Added shortcuts for most of the functions
# Added mask and ifft filtering
# Improved image setting dialog
# Added manual input for cropping

# 2025-01-31  v1.0
# Significant update with redesigned UI. Now it is separated from the old EMD-converter.
# Batch converter function calls the old Emd-converter and runs batch conversion.
# Added flip image and stack
# Added custom color map for colors to transition from black at 0 intensity
# Send to windows and mac bundles

# 2025-02-10 v1.1
# New Features: Geometric phase analysis
# New function: resampling (both up and down)
# Improved mode switching between measure, line profile, etc.
# Manual input vmin vmax together with the slider bar
# Fixed some tif images cannot be imported with missing modules

# 2025-02-16 v1.2
# New feature: Measure diffraction pattern
# New feature: Simple math of add, subtract, multiply, divide, inverse on two images or stacks
# New feature: Calculate iDPC and dDPC from 4 or 2 images or stacks with a given angle. The rotation angle can be guessed by either min curl or max contrast.
# Bug fix: units in some data are not recogonized due to extra space, such as '1 / nm'.
# Added save as type: 32-bit float TIFF

# 2025-02-24 v1.2.1
# Support drag and drop file(s) into the main UI or the batch converter
# Figure keeps the aspect ratio upon resizing (for the most of the cases)
# A mini colorbar can be added to the top right corner 

# 2025-03-06 v1.2.2
# Add right click menu
# Add save as 8-bit tiff and color tiff
# Stack can also be exported as 8-bit tiff and color tiff, png, and jpg
# Added check for the image sizes when computing DPC to prevent crashing
# Fixed letter /mu in micrometer scale bar cannot display correctly.

# 2025-03-11 v1.2.3
# Fixed an incorrect definition of high pass filter in DPC reconstruction that 
# caused the UI to crash on non-square images.
# Fixed dDPC output was set to 'int16' instead of 'float32'.
# Add support for *.mrc file (image stack only). If the metadata txt file exists, it will be loaded as well.
# New feature: import image series of the same type in one folder
# New feature: "Sort stack" function to reorder and delete frames in a stack
# Change copy image shortcut to ctrl+alt+c or cmd+option+c and release ctrl+c/cmd+c to system copy shortcut

# 2025-03-19 v1.2.4
# Fixed incorrect data type handling in stack operations that causes app crash
# Add save metadata option for batch conversion

# 2025-03-31 v1.2.5
# Improved interactive measuring and line profile by using blitting

# 2025-05-01  v1.2.6
# Fixed app crash when measuring on live FFT
# Fixed windowed FFT not working on non calibrated images
# Automatic window positioning with functions
# Add selecting reference area for GPA
# Add adaptive GPA with wfr algorithm
# Improved memory consumption.

# 2025-09-06  v1.3.0dev
# Restructured codes with DPC and GPA codes separately
# Use a separate thread for time-consuming tasks while keeping the GUI responsive
# Added progress bar for long-running tasks
# Bug fix for close event to delete all child widgets
# Set output to float32 for stack alignment
# Added save stack as gif animation
# Added reslice stack from a line
# Live FFT on a stack
# Apply filters to each frame of image stack
# Redesigned the slider for image stack navigation
# "Space" to Play/Pause, "," to Rewind, "." to Forward on stack images.
# Added gamma correction for image adjustment
# Rewrite some of the filter functions
# Added radial integration from a selected center
# Added using arrow keys to move the crop region, live FFT region, and masks on FFT
# iFFT filtered image is automatically updated if a mask is present

# 2025-10-20 v1.3
# Redesigned the main UI with pyqtgraph
# Optimized operation workflow with pyqtgraph functions
# Modified filteres to take non-square images
# Live iFFT also takes non-square images


from operator import pos
from PyQt5 import QtCore, QtWidgets

from PyQt5.QtWidgets import (QApplication, QMainWindow, QListView, QVBoxLayout, 
                             QWidget, QPushButton, QMessageBox, QFileDialog, 
                             QDialog, QAction, QHBoxLayout, QLineEdit, QLabel, 
                             QComboBox, QInputDialog, QCheckBox, QGroupBox, 
                             QFormLayout, QDialogButtonBox,  QTreeWidget, QTreeWidgetItem,
                             QSlider, QStatusBar, QMenu, QTextEdit, QSizePolicy, QRadioButton,
                             QListWidget, QListWidgetItem, QButtonGroup, QProgressBar, QToolBar,
                             QTextBrowser
                             )
from PyQt5.QtCore import Qt, QStringListModel, QObject, pyqtSignal, QThread, QRectF, QSize
from PyQt5.QtGui import QImage, QPixmap, QIcon, QDropEvent, QDragEnterEvent, QFont


import sys
import os
import io

import numpy as np
import copy


import pickle
import json
from collections import OrderedDict

from PIL import Image, ImageDraw, ImageFont

import pyqtgraph as pg
import pyqtgraph.exporters

from scipy.fft import fft2, fftshift, ifft2, ifftshift
from skimage.filters import window
from skimage.measure import profile_line
from scipy.ndimage import rotate, shift
from skimage.registration import phase_cross_correlation, optical_flow_ilk
from skimage.transform import warp, rescale, resize


ver = '1.3'
rdate = '2025-10-25'

#===================Import internal modules==========================================
from GPA import GPA, norm_img, create_mask, refine_center
from DPC import reconstruct_iDPC, reconstruct_dDPC, find_rotation_ang_max_contrast, find_rotation_ang_min_curl
import filters

if getattr(sys, 'frozen', False):
    wkdir = sys._MEIPASS
elif __file__:
    wkdir = os.path.dirname(__file__)
# app.setWindowIcon(QIcon(os.path.join(wkdir, "Icon.ico")))

# Global colormap storage
with open(os.path.join(wkdir, 'colormaps.pkl'), 'rb') as f:
    custom_cmap = pickle.load(f)

#===================Redirect output to the main window===============================
# Custom stream class to capture output
class EmittingStream(QObject):
    text_written = pyqtSignal(str)  # Signal to emit text

    def write(self, text):
        self.text_written.emit(str(text))  # Emit the text

    def flush(self):
        pass  # Required for compatibility with sys.stdout

class TeeStream:
    """Write to both the original stream and the EmittingStream."""
    def __init__(self, emitter: EmittingStream, orig):
        self.emitter = emitter
        self.orig = orig

    def write(self, text):
        try:
            self.orig.write(text)
        except Exception:
            pass
        try:
            self.emitter.write(text)
        except Exception:
            pass

    def flush(self):
        try:
            self.orig.flush()
        except Exception:
            pass
        

#===================QThread for background processing================================
class Worker(QThread):
    result = pyqtSignal(object)
    finished = pyqtSignal()
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        # Perform long-running task defined by func
        result = self.func(*self.args, **self.kwargs)
        self.finished.emit()
        self.result.emit(result)


        
#=====================Main Window UI ===============================================


class UI_TemCompanion(QWidget):
    def __init__(self):
        super().__init__()
        self.setupUi()
        self.file = None
        self.converter = None
        # Create the custom stream and connect it to the QTextEdit
        self.stream = EmittingStream()
        self.stream.text_written.connect(self.append_text)
   
        # Redirect sys.stdout and sys.stderr to the custom stream
        sys.stdout = self.stream
        sys.stderr = self.stream

        # Tee stdout/stderr to both console and UI
        self.stdout_tee = TeeStream(self.stream, sys.__stdout__)
        self.stderr_tee = TeeStream(self.stream, sys.__stderr__)
        sys.stdout = self.stdout_tee
        sys.stderr = self.stderr_tee
        
        # Drag and drop file function
        self.setAcceptDrops(True)
        
        self.print_info()
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        file = event.mimeData().urls()[0].toLocalFile()
        if file:
            self.file = file
            ext = getFileType(file)
            if ext == 'emd':
                self.file_type = 'Velox emd Files (*.emd)'
            elif ext in ['dm3', 'dm4']:
                self.file_type = 'DigitalMicrograph Files (*.dm3 *.dm4)'
            elif ext == 'ser':
                self.file_type = 'TIA ser Files (*.ser)'
            elif ext in ['tif', 'tiff']:
                self.file_type = 'Tiff Files (*.tif *.tiff)'
            elif ext == 'mrc':
                self.file_type = 'MRC Files (*.mrc)'
            elif ext in ['jpg', 'jpeg', 'png', 'bmp']:
                self.file_type = 'Image Formats (*.tif *.tiff *.jpg *.jpeg *.png *.bmp)'
            elif ext == 'pkl':
                self.file_type = 'Pickle Dictionary Files (*.pkl)'
            else:
                QMessageBox.warning(self, 'Open File', 'Unsupported file formats!')
                return
            self.preview()
            event.acceptProposedAction()
    def append_text(self, text):
        # Append text to the QTextEdit
        self.outputBox.moveCursor(self.outputBox.textCursor().End)  # Move cursor to the end
        self.outputBox.insertPlainText(text)  # Insert the text
        
    #=============== Redefine the close window behavior============================
    def closeEvent(self, event):
        # Close all window
        if self.preview_dict:
            plots = list(self.preview_dict.keys())
            for plot in plots:
                try:
                    self.preview_dict[plot].close()
                except:
                    pass

        if self.converter is not None and self.converter.isVisible():
            self.converter.close()
        

        
    # Define filter parameters as class variables        
    apply_wf, apply_absf, apply_nl, apply_bw, apply_gaussian = False, False, False, False, False
    filter_parameters_default = {"WF Delta": "10", "WF Bw-order": "4", "WF Bw-cutoff": "0.3",
                                 "ABSF Delta": "10", "ABSF Bw-order": "4", "ABSF Bw-cutoff": "0.3",
                                 "NL Cycles": "10", "NL Delta": "10", "NL Bw-order": "4", "NL Bw-cutoff": "0.3",
                                 "Bw-order": "4", "Bw-cutoff": "0.3",
                                 "GS-cutoff": "0.3"}

    filter_parameters = filter_parameters_default.copy()
    
    #Preview dict as class variable
    preview_dict = {}


    def setupUi(self):
        
        self.setObjectName("TemCompanion")
        self.setWindowTitle(f"TemCompanion Ver {ver}")
        self.resize(400, 400)
        
        buttonlayout = QHBoxLayout()
        
        self.openfileButton = QPushButton(self)
        #self.openfileButton.setGeometry(QtCore.QRect(30, 20, 80, 60))
        self.openfileButton.resize(80, 60)
        self.openfileButton.setObjectName("OpenFile")
        self.openfileButton.setText('Open \nImages')
        
        
        
        self.convertButton = QPushButton(self)
        #self.convertButton.setGeometry(QtCore.QRect(100, 20, 80, 60))
        self.convertButton.resize(80, 60)
        self.convertButton.setObjectName("BatchConvert")
        self.convertButton.setText("Batch \nConvert")
        
        
        
        
        self.aboutButton = QPushButton(self)
        #self.aboutButton.setGeometry(QtCore.QRect(170, 20, 80, 60))
        self.aboutButton.resize(80, 60)
        self.aboutButton.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred)

        self.aboutButton.setObjectName("aboutButton")
        self.aboutButton.setText("About")
        
        self.contactButton = QPushButton(self)
        #self.contactButton.setGeometry(QtCore.QRect(240, 20, 80, 60))
        self.contactButton.resize(80, 60)
        self.contactButton.setObjectName("contactButton")
        self.contactButton.setText("Contact")
        self.contactButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        self.donateButton = QPushButton(self)
        #self.donateButton.setGeometry(QtCore.QRect(310, 20, 80, 60))
        self.donateButton.resize(80, 60)
        self.donateButton.setObjectName("donateButton")
        self.donateButton.setText("Buy me\n a LUNCH!")
        self.donateButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        buttonlayout.addWidget(self.openfileButton)
        buttonlayout.addWidget(self.convertButton)
        buttonlayout.addWidget(self.aboutButton)
        buttonlayout.addWidget(self.contactButton)
        buttonlayout.addWidget(self.donateButton)
        
        layout = QVBoxLayout()
        layout.addLayout(buttonlayout)
        
        self.authorlabel = QLabel(self)
        #self.authorlabel.setGeometry(QtCore.QRect(30, 320, 350, 16))
        self.authorlabel.setObjectName("authorlabel")
        self.authorlabel.setText(f'TemCompanion by Dr. Tao Ma   {rdate}')
        
        
        # self.outputBox = QTextEdit(self, readOnly=True)
        # #self.outputBox.setGeometry(35, 90, 350, 210)
        # self.outputBox.resize(350, 240)
        # layout.addWidget(self.outputBox)   
        

        self.outputBox = QTextBrowser(self)
        self.outputBox.setOpenExternalLinks(True)  # open http(s) links in default browser
        self.outputBox.setOpenLinks(True)          # allow internal anchors (if any)
        self.outputBox.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.outputBox.resize(350, 220)
        layout.addWidget(self.outputBox)

        layout.addWidget(self.authorlabel)
        
        self.setLayout(layout)

        
#====================================================================
# Connect all functions
        self.openfileButton.clicked.connect(self.openfile)
        
        self.convertButton.clicked.connect(self.batch_convert)
        self.aboutButton.clicked.connect(self.show_about)
        self.contactButton.clicked.connect(self.show_contact)
        self.donateButton.clicked.connect(self.donate)
        

        
        
    def print_info(self):
        html_text = '''
        <div style="font-family: Arial, sans-serif;">
            <h3 style="color: #2196F3; text-align: center;">TemCompanion</h3>
            <p style="text-align: center; font-size: 12px;">
                <b>A comprehensive package for TEM image processing and analysis</b>
            </p>
            <p style="text-align: center; font-style: italic;">
                Designed by Dr. Tao Ma
            </p>
            <p style="font-size: 12px;">
                If TemCompanion helped your TEM image analysis in a publication, please cite:
            </p>
            <p style="font-size: 11px; margin-left: 20px; color: #555;">
                Tao Ma, <i>TemCompanion: An open-source multi-platform GUI program for TEM image processing and analysis</i>, 
                <b>SoftwareX</b>, 2025, <b>31</b>, 102212. 
                <a href="https://doi.org/10.1016/j.softx.2025.102212">doi:10.1016/j.softx.2025.102212</a>
            </p>
            <p style="font-size: 12px;">
                Address your questions and suggestions to 
                <a href="mailto:matao1984@gmail.com">matao1984@gmail.com</a>
            </p>
            <p style="font-size: 12px;">
                See the <b>About</b> for more details. Buy me a lunch if you like it!
            </p>
            <p style="text-align: left; font-size: 12px; color: #666;">
                Version: <b>{ver}</b> | Released: <b>{rdate}</b>
            </p>
        </div>
        '''.format(ver=ver, rdate=rdate)
        
        self.outputBox.append(html_text)
        self.outputBox.append("")

        
#===================================================================
# Open file button connected to OpenFile

    def openfile(self):
        self.file, self.file_type = QFileDialog.getOpenFileName(self,"Select a TEM image file:", "",
                                                     "Velox emd Files (*.emd);;TIA ser Files (*.ser);;DigitalMicrograph Files (*.dm3 *.dm4);;Tiff Files (*.tif *.tiff);;MRC Files (*.mrc);;Image Formats (*.tif *.tiff *.jpg *.jpeg *.png *.bmp);;Pickle Dictionary Files (*.pkl);;Image Series (*.*)")
        if self.file:
            self.preview()
           
        else: 
            self.file = None # Canceled, set back to None
                


#======================================================================
    def batch_convert(self):
        # Open a new window for batch conversion
        self.converter = BatchConverter()
        self.converter.show()
            
        
#=====================================================================        
    @classmethod
    def show_about(cls):
        msg = QMessageBox()
#        msg.setIcon(QMessageBox.Information)
        msg.setText("TemCompanion: a tool to view, edit, filter, and convert TEM image files to tiff, png, and jpg."\
                    "<br>"\
                    "This app was designed by Dr. Tao Ma"\
                    "<br>"\
                    "Version: {}  Released: {}"\
                    "<br>"\
                    "Hope you get good results and publications from it!"\
                    "<br>"\
                    "Get more information and source code from <a href=\"https://github.com/matao1984/temcompanion\">here</a>.".format(ver, rdate))
        msg.setWindowTitle(ver + ": About")

        msg.exec()
        

#=====================================================================        
    def show_contact(self):
        msg = QMessageBox()
        msg.setText("Ask questions and report bugs to:"\
                    "<br>"
                    "<a href=\"mailto:matao1984@gmail.com\">matao1984@gmail.com</a>")
        msg.setWindowTitle(ver + ": Contact")

        msg.exec()
        
#====================================================================
        
    def donate(self):
        msg = QMessageBox()
        msg.setText("I will make this app freely available for the society.<br>"\
                    "If you like this app, show your appreciation and <a href=\"https://paypal.me/matao1984?country.x=US&locale.x=en_US\">buy me a lunch!</a>"\
                    "<br>"\
                    "Your support is my motivation!")
        msg.setWindowTitle(ver + ": Buy me a LUNCH!")

        msg.exec()




            
            
            
#================ Define filter settings function ============================
    @classmethod
    def filter_settings(cls):
     
        filtersettingdialog = FilterSettingDialogue(cls.apply_wf, cls.apply_absf, cls.apply_nl, 
                                                    cls.apply_bw, cls.apply_gaussian, cls.filter_parameters)
        result = filtersettingdialog.exec_()
        if result == QDialog.Accepted:
            cls.filter_parameters = filtersettingdialog.parameters
            cls.apply_wf = filtersettingdialog.apply_wf
            cls.apply_absf = filtersettingdialog.apply_absf
            cls.apply_nl = filtersettingdialog.apply_nl
            cls.apply_bw = filtersettingdialog.apply_bw
            cls.apply_gaussian = filtersettingdialog.apply_gaussian
        
# ====================== Open file for preview ===============================
    def preview(self):
        
        try:
            f = load_file(self.file, self.file_type)
            f_name = getFileName(self.file)
            
            if f == None:
                return
        
            for i in range(len(f)):
                img = f[i]
                try:
                    title = img['metadata']['General']['title']
                except:
                    title = '' 
                try:
                    preview_name = f_name + ": " + title
                    preview_im = PlotCanvas(img, parent=self)
                        
                    
                    preview_im.setWindowTitle(preview_name)
                    preview_im.canvas.canvas_name = preview_name
                    self.preview_dict[preview_name] = preview_im
                    
                    self.preview_dict[preview_name].show() 
                    self.preview_dict[preview_name].position_window('center')
                    
                    print(f'Opened successfully: {f_name + ": " + title}.')
                except Exception as e:
                    print(f'Opened unsuccessful: {f_name + ": " + title}. Error: {e}')
        except Exception as e:
            print(f'Cannot open {self.file}, make sure it is not in use or corrupted! Error: {e}')
            return

        
        finally:    
            f = None


#=========== Scale bar class used with pyqtgraph ==============================================
class CustomScaleBar(pg.ScaleBar):
    def __init__(self, dx, units, parent):
        super().__init__(dx, suffix=units)
        self.setParentItem(parent)

    def set_properties(self, font_size, color, location):
        font = QFont()
        font.setPointSize(font_size)
        text_label = self.text
        text_label.setFont(font)
        text_label.setColor(color)
        self.bar.setBrush(pg.mkBrush(color))

        if location == 'lower left':
            loc = (0, 1), (0.2, 0.95)
        elif location == 'lower right':
            loc = (1, 1), (0.95, 0.95)
        elif location == 'upper right':
            loc = (1, 0), (0.95, 0.08)
        elif location == 'upper left':
            loc = (0, 0), (0.2, 0.08)
        self.anchor(loc[0], loc[1])

#=========== Main frame widget to take the image item and maintain the aspect ratio ===========
class MainFrameCanvas(QWidget):
    """A widget that maintains a specified aspect ratio."""
    def __init__(self, data, parent=None):
        # Image canvas that keeps the aspect ratio
        # data is the image dictionary
        super().__init__(parent)
        self.data = data
        self.img_size = self.data['data'].shape
        if len(self.img_size) == 2:
            self.data_type = 'Image'
        elif len(self.img_size) == 3:
            self.data_type = 'Image Stack'
        else:
            QMessageBox.warning(self, 'Open File', 'Data dimension not supported!')
            return
        
        self.ratio = self.img_size[-1] / self.img_size[-2]       
        self.img_data = self.data['data']
        self.center = self.img_size[-1]//2, self.img_size[-2]//2
        self.offset_x = 0
        self.offset_y = 0
        
        # ROI
        self.selector = []
        self.active_selector = None
     
        self.image_item = None
        self.idx = None
        self.slider = None
        self.colorbar = None
        self.cb_width = 0

        # Playback control for stack images
        self.isPlaying = False
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.next_frame)

        self.plot = pg.PlotWidget()
        self.plot.setBackground('white')
        self.plot.plotItem.showAxis('left', False)
        self.plot.plotItem.showAxis('bottom', False)
        self.plot.plotItem.setContentsMargins(0, 0, 0, 0)
        self.plot.plotItem.setMenuEnabled(False, enableViewBoxMenu=True)
        self.plot.disableAutoRange()
        self.plot.hideButtons()
        

        self.viewbox = self.plot.getViewBox()
        self.viewbox.setDefaultPadding(0)
        self.viewbox.enableAutoRange(enable=False)
  
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)   

        if self.data_type == 'Image Stack':
            self.stack_size = self.img_data.shape[0]
            self.idx = 0
            self.current_img = self.img_data[self.idx]    

            # Slider bar
            self.sh = 34 # Slider height
            self.slider = QSlider(Qt.Horizontal)
            self.slider.setFixedHeight(self.sh)
            self.slider.setRange(0,self.stack_size - 1)
            slider_layout = QHBoxLayout()
            slider_layout.addWidget(self.slider)
            self.frame = QLabel()
            self.frame.setText(f'{self.idx + 1}')
            slider_layout.addWidget(self.frame)
            slider_layout.setContentsMargins(0, 0, 0, 0)
            slider_layout.setSpacing(0)

            self.layout.addLayout(slider_layout)
            self.slider.valueChanged.connect(self.update_frame)
            
        
        else:
            self.current_img = self.img_data
            self.sh = 0

        self.setLayout(self.layout)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self._resize_event(self.size())    
        
        # Some default settings
        sb_color = pg.mkColor('yellow')
        self.attribute = {'cmap': 'gray',
                          'vmin': None,
                          'vmax': None,
                          'gamma': 1.0,
                          'scalebar': True,
                          'color': sb_color,
                          'location': 'lower left',
                          'dimension': 'si-length',
                          'colorbar': False}

        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and self.data_type == 'Image Stack':
            self.toggle_play()
        if event.key() == Qt.Key_Comma and self.data_type == 'Image Stack':
            if self.slider.value() > 1:
                self.slider.setValue(self.slider.value() - 1)
            else:
                self.slider.setValue(self.slider.maximum())
        if event.key() == Qt.Key_Period and self.data_type == 'Image Stack':
            if self.slider.value() < self.slider.maximum():
                self.slider.setValue(self.slider.value() + 1)
            else:
                self.slider.setValue(0)

        # Key events for moving the selector ROI
        if event.key() == Qt.Key_Up:
            if self.active_selector is not None: 
                selector_box = self.active_selector.parentBounds()
                x0 = selector_box.x()
                y0 = selector_box.y()
                x1 = x0 + selector_box.width() 
                y1 = y0 + selector_box.height()
                step = 1 * self.parent().scale
                if y0 >= step:
                    self.active_selector.setPos([x0, y0 - step])
        
        elif event.key() == Qt.Key_Down:
            if self.active_selector is not None: 
                selector_box = self.active_selector.parentBounds()
                x0 = selector_box.x()
                y0 = selector_box.y()
                x1 = x0 + selector_box.width() 
                y1 = y0 + selector_box.height()
                step = 1 * self.parent().scale
                if y1 <= (self.img_size[0] * self.parent().scale - step):
                    self.active_selector.setPos([x0, y0 + step])
        
        elif event.key() == Qt.Key_Left:
            if self.active_selector is not None: 
                selector_box = self.active_selector.parentBounds()
                x0 = selector_box.x()
                y0 = selector_box.y()
                x1 = x0 + selector_box.width() 
                y1 = y0 + selector_box.height()
                step = 1 * self.parent().scale
                if x0 >= step:
                    self.active_selector.setPos([x0 - step, y0])
        
        elif event.key() == Qt.Key_Right:
            if self.active_selector is not None: 
                selector_box = self.active_selector.parentBounds()
                x0 = selector_box.x()
                y0 = selector_box.y()
                x1 = x0 + selector_box.width() 
                y1 = y0 + selector_box.height()
                step = 1 * self.parent().scale
                if x1 <= (self.img_size[1] * self.parent().scale - step):
                    self.active_selector.setPos([x0 + step, y0])

        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            if self.active_selector is not None and self.parent().mode_control['lineprofile']:
                size = self.active_selector.size()
                l, w = size.x(), size.y()
                step = 1 * self.parent().scale
                w += step
                self.active_selector.setSize([l, w])

        elif event.key() == Qt.Key_Minus or event.key() == Qt.Key_Underscore:
            if self.active_selector is not None and self.parent().mode_control['lineprofile']:
                size = self.active_selector.size()
                l, w = size.x(), size.y()
                step = 1 * self.parent().scale
                if w > step:
                    w -= step
                    self.active_selector.setSize([l, w])

    def toggle_play(self, t=100):
        self.isPlaying = not self.isPlaying       
        if self.isPlaying:
            self.timer.start(t) 
        else:
            self.timer.stop()

    def next_frame(self):
        if self.slider.value() < self.slider.maximum():
            self.slider.setValue(self.slider.value() + 1)
        else:
            self.slider.setValue(0)

    def create_img(self, cmap='gray', pvmin=0.1, pvmax=99.9, gamma=1.0):
        scale = self.parent().scale if hasattr(self.parent(), 'scale') else 1
        self.center = self.img_size[-1]//2, self.img_size[-2]//2
        self.offset_x = self.data['axes'][-1]['offset'] if len(self.data['axes']) > 1 and 'offset' in self.data['axes'][-1].keys() else 0
        self.offset_y = self.data['axes'][-2]['offset'] if len(self.data['axes']) > 1 and 'offset' in self.data['axes'][-2].keys() else 0
        
        # Calculate vmin and vmax with percentile
        self.attribute['vmin'] = np.percentile(self.current_img, pvmin)
        self.attribute['vmax'] = np.percentile(self.current_img, pvmax)

        # Clear previous image item if exists
        if self.image_item is not None:
            self.viewbox.removeItem(self.image_item)
            self.image_item = None

        # Create image item       
        self.image_item = pg.ImageItem(self.current_img, axisOrder='row-major', 
                                       autoLevels=False,
                                       levels=(self.attribute['vmin'], self.attribute['vmax']))
        
        lut = custom_cmap[cmap]
        lut = gamma_correct_lut(lut, gamma)
        self.image_item.setLookupTable(lut)
        self.image_item.setScale(scale)
        self.viewbox.addItem(self.image_item)
        self.viewbox.invertY(True)  # To match the image coordinate system
        self.viewbox.setAspectLocked(True)
        # self.viewbox.setLimits(xMin=0, xMax=self.img_size[-1]*scale, yMin=0, yMax=self.img_size[-2]*scale)
        # Redefined autorange button
        self.custom_auto_range()


    def toggle_colorbar(self, show):
        self.attribute['colorbar'] = show
        # Create a colorbar on the right side of the image
        if show:
            if self.colorbar is None:
                if self.image_item is not None:
                    cb_width = 25
                    lut = custom_cmap[self.attribute['cmap']]
                    lut = gamma_correct_lut(lut, self.attribute['gamma'])
                    cm = pg.ColorMap(pos=np.linspace(0, 1, 256), color=lut)
                    self.colorbar = pg.ColorBarItem(values=(self.attribute['vmin'], self.attribute['vmax']),
                                                    width=cb_width, colorMap=cm, interactive=False)
                    self.colorbar.setImageItem(self.image_item, insert_in=self.plot.plotItem)

                    # Set the colorbar text color
                    axis = self.colorbar.axis
                    axis.setTextPen(pg.mkPen('black')) 
                    axis.setPen(pg.mkPen('black'))

                    layout = self.plot.plotItem.layout
                    layout.setColumnFixedWidth(5, cb_width + 40)
                    self.cb_width = 77
                    self._resize_event(self.size())
        else:
            if self.colorbar is not None:
                self.plot.plotItem.layout.removeItem(self.colorbar)
                self.colorbar = None
                self.cb_width = 0
                self._resize_event(self.size())

    def update_img(self, img, pvmin=0.1, pvmax=99.9):
        # Update the image display with new image data 
        # img must match the original image data dimension
        if self.image_item is not None:
            self.current_img = img
            scale = self.parent().scale if hasattr(self.parent(), 'scale') else 1
            self.attribute['vmin'] = np.percentile(img, pvmin)
            self.attribute['vmax'] = np.percentile(img, pvmax)
            self.image_item.setImage(img, axisOrder='row-major', 
                                     autoLevels=False,
                                     levels=(self.attribute['vmin'], self.attribute['vmax']))
            self.image_item.setScale(scale)
            self.custom_auto_range()

    def resizeEvent(self, event):
        self._resize_event(event.size())

    def _resize_event(self, size):
        w, h = size.width(), size.height()

        current_ratio = (w - self.cb_width) / (h - self.sh)
        # Horizontal space for colorbar
        
        
        if current_ratio > self.ratio:
            # Container is too wide, adjust width
            target_w = np.ceil((h-self.sh) * self.ratio) + self.cb_width
            h_margin = (w - target_w) / 2
            h_margin0 = int(h_margin)
            h_margin1 = int(w - target_w - h_margin0)
            self.layout.setContentsMargins(h_margin0, 0, h_margin1, 0)
        else:
            # Container is too tall, adjust height
            target_h = np.ceil((w - self.cb_width) / self.ratio + self.sh)
            v_margin = (h - target_h) / 2
            v_margin0 = int(v_margin)
            v_margin1 = int(h - target_h - v_margin0)
            self.layout.setContentsMargins(0, v_margin0, 0, v_margin1)
        
        # Ensure the contained widget is added last
        if self.layout.itemAt(1) is None:
            self.layout.addWidget(self.plot)

    def custom_auto_range(self):
        img = self.image_item.image
        scale = self.parent().scale if hasattr(self.parent(), 'scale') else 1
        
        if img is not None:
            vb = self.plot.getPlotItem().getViewBox()
            vb.setRange(
                xRange=(0, img.shape[-1] * scale), 
                yRange=(0, img.shape[-2] * scale), 
                padding=0, 
                update=True
            )


    def update_frame(self):
        # For 3D image stacks, change to the frame specified
        if self.slider is not None:
            self.idx = self.slider.value()
            self.frame.setText(f'{self.idx + 1}')
            self.current_img = self.img_data[self.idx]
            self.image_item.setImage(self.current_img, axisOrder='row-major')

            # Update live FFT if in live FFT mode
            if self.parent().mode_control['Live_FFT']:
                self.parent().update_live_fft()

            
#=========== New plot canvas with pyqtgraph ==================================================== 
class PlotCanvas(QMainWindow):
    def __init__(self, img, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(600, 650)
        self.img_size = img['data'].shape
 
        self.scalebar = None
        self.colorbar = None
        
        self.scale = img['axes'][1]['scale'] if 'axes' in img and len(img['axes']) > 1 else 1

        try:
            self.units = img['axes'][1]['units'] if 'axes' in img and len(img['axes']) > 1 else 'px'
            self.units = ''.join(self.units.split(' '))
        except Exception as e:
            print(f"Error reading units: {e} Set to pixel scale")
            self.units = 'px'
            self.scale = 1
                      
        # Create Image with canvas
        self.canvas = MainFrameCanvas(img, parent=self)
        self.setCentralWidget(self.canvas)

        # Update scale bar with zoom
        self.canvas.viewbox.sigRangeChanged.connect(self.create_scalebar)

        # Measurement mode control all in a dictionary
        self.mode_control = {'measurement': False,
                             'crop': False,
                             'lineprofile': False,
                             'measure_fft': False,
                             'mask': False,
                             'Live_FFT': False,
                             'GPA': False,
                             'define_center': False,
                             'radial_integration': False
                            }

        # Some dialogs
        self.radial_integration_dialog = None
        self.dpc_dialog = None

        # All the push buttons
        self.buttons = {'ok': None,
                        'cancel': None,
                        'crop_hand': None,
                        'define_center': None,
                        'define_center2': None,
                        'add': None,
                        'remove': None,
                        'settings': None
                        }
        
        # Some variants for measuring functions initialized as None or 0
        self.start_point = None
        self.end_point = None
        self.crosshair = None
        self.temp_center = []     
        
        # Process history
        if 'process' in img['metadata']:
            self.process = copy.deepcopy(img['metadata']['process'])
        else:
            # Make a new process history
            self.process = {'software': f'TemCompanion v{ver}', 'process': []}
            img['metadata']['process'] = self.process
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Progress bar
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 0)
        self.progressBar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progressBar)
        self.statusBar.showMessage("Ready")

        # Pixel label on the status bar
        self.pixel_label = QLabel(f"--- {self.units} | ---, --- {self.units} | ---,")
        self.value_label = QLabel("---")

        self.statusBar.addPermanentWidget(self.pixel_label)
        self.statusBar.addPermanentWidget(self.value_label)

        # # Connect mouse event
        self.canvas.plot.scene().sigMouseMoved.connect(self.on_mouse_move)
        self.canvas.plot.scene().sigMouseHover.connect(self.on_mouse_hover)

        # Parse and convert the units
        self.set_scalebar_units()

        # Make image
        self.canvas.create_img()

        # Tool bar
        self.create_toolbar()

        # Create menu bar
        self.create_menubar()

    def closeEvent(self, event):
        UI_TemCompanion.preview_dict.pop(self.canvas.canvas_name, None)

    def _make_active_selector(self, selector):
        # Set the active selector to receive key events
        if self.canvas.active_selector is not selector:
            self.canvas.active_selector = selector

    def update_img(self, img, img_size=None, pvmin=0.1, pvmax=99.9):
        # Update the image with a new image dictionary
        # Only used for 2D image case
        if img_size is not None:
            self.img_size = img_size
        else:
            self.img_size = img['data'].shape
        self.scale = img['axes'][1]['scale'] if 'axes' in img and len(img['axes']) > 1 else 1
        try:
            self.units = img['axes'][1]['units'] if 'axes' in img and len(img['axes']) > 1 else 'px'
            self.units = ''.join(self.units.split(' '))
        except Exception as e:
            print(f"Error reading units: {e} Set to pixel scale")
            self.units = 'px'
            self.scale = 1

        self.canvas.update_img(img['data'], pvmin=pvmin, pvmax=pvmax)

    def create_scalebar(self):
        # Remove previous scalebar
        if self.scalebar is not None:
            try:
                self.canvas.viewbox.removeItem(self.scalebar)
            except:
                pass # Always has a mysterious error
            self.scalebar = None

        if self.canvas.attribute['scalebar']:
            # Get current view range instead of using image size
            view_range = self.canvas.viewbox.viewRange()
            x_range = view_range[0][1] - view_range[0][0]
        
            # Set scale bar to 15% of current x-range
            scale_dx_float = x_range * 0.15
            units = self.units
            
            # Set the length to 1, 2, 5, 10, 20, 50, 100, 200, 500.
            scale_dx_list = [1, 2, 5, 10, 20, 50, 100, 200, 500]
            scale_dx = min(scale_dx_list, key=lambda x: abs(x - scale_dx_float))

            self.scalebar = CustomScaleBar(scale_dx, units, parent=self.canvas.viewbox)
            font = 20
            color = self.canvas.attribute['color']
            location = self.canvas.attribute['location']
            self.scalebar.set_properties(font, color, location)
        
    def set_scalebar_units(self):
        # Handle 'um' and '1/um' cases:
        if self.units == 'um':
            self.units = 'µm'
        elif self.units == '1/um':
            self.units = '1/µm'

        # Handle Angstrom cases:
        if self.units in ['A', 'Å', 'ang', 'Ang', 'Angstrom', 'Ångstrom']:
            self.units = 'nm'
            self.scale *= 0.1
        elif self.units in ['1/A', '1/Å', '1/ang', '1/Ang', '1/Angstrom', '1/Ångstrom']:
            self.units = '1/nm'
            self.scale /= 0.1

        # Reformat the units for scale bar so that the scalebar shows a value between 1 and 1000
        units = self.units
        scale = self.scale
        fov = self.img_size[1] * scale  # in original units
        scalebar = fov * 0.15 # 15% of the field of view

        # Handle the realspace cases
        real_units_list = ['pm', 'nm', 'µm', 'mm', 'm', 'km']
        reciprocal_units_list = ['1/pm', '1/nm', '1/µm', '1/mm', '1/m', '1/km'] 
        if units in real_units_list:
            dimension = 'si-length'
            while scalebar < 1 or scalebar >= 1000:
                unit_index = real_units_list.index(units)
                if scalebar < 1 and unit_index > 0:
                    scale *= 1000
                    units = real_units_list[unit_index - 1]
                    scalebar = scale * self.img_size[1] * 0.15

                elif scalebar >= 1000 and unit_index < 5:
                    scale /= 1000
                    units = real_units_list[unit_index + 1]
                    scalebar = scale * self.img_size[1] * 0.15

        # Handle the reciprocal space cases
        elif units in reciprocal_units_list:
            dimension = 'si-length-reciprocal'
            while scalebar < 1 or scalebar >= 1000:
                unit_index = reciprocal_units_list.index(units)
                if scalebar < 1 and unit_index < 5:
                    scale *= 1000
                    units = reciprocal_units_list[unit_index + 1]
                    scalebar = scale * self.img_size[1] * 0.15
                elif scalebar >= 1000 and unit_index > 0:
                    scale /= 1000
                    units = reciprocal_units_list[unit_index - 1]
                    scalebar = scale * self.img_size[1] * 0.15

        else:
            # Unknown units, set to pixel scale
            dimension = 'pixel-length'
            units = 'px'
            scale = 1
        
        self.units = units
        # Set real space units for reciprocal space images
        if dimension == 'si-length-reciprocal' and self.units in reciprocal_units_list:
            self.real_units = real_units_list[reciprocal_units_list.index(self.units)]
        else:
            self.real_units = self.units
        self.scale = scale
        self.canvas.attribute['dimension'] = dimension

        # Update the image dictionary
        self.canvas.data['axes'][0]['scale'] = scale
        self.canvas.data['axes'][1]['scale'] = scale
        self.canvas.data['axes'][0]['units'] = units
        self.canvas.data['axes'][1]['units'] = units

    def create_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(16,16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolbar.layout().setSpacing(0)  # Sets spacing between items
        self.addToolBar(self.toolbar)

        # Add actions to the toolbar
        home_icon = os.path.join(wkdir, 'icons/home.png')
        home_action = QAction(QIcon(home_icon), "Home", self)
        home_action.setStatusTip("Auto scale to fit the window")
        home_action.triggered.connect(self.canvas.custom_auto_range)
        self.toolbar.addAction(home_action)

        self.toolbar.addSeparator()

        save_icon = os.path.join(wkdir, 'icons/save.png')
        save_action = QAction(QIcon(save_icon), "Save", self)
        save_action.setStatusTip("Save the current image")
        save_action.triggered.connect(self.save_figure)
        self.toolbar.addAction(save_action)

        copy_icon = os.path.join(wkdir, 'icons/copy.png')
        copy_action = QAction(QIcon(copy_icon), "Copy", self)
        copy_action.setStatusTip("Copy the current image")
        copy_action.triggered.connect(self.copy_img)
        self.toolbar.addAction(copy_action)

        setting_icon = os.path.join(wkdir, 'icons/settings.png')
        setting_action = QAction(QIcon(setting_icon), "Settings", self)
        setting_action.setStatusTip("Open settings")
        setting_action.triggered.connect(self.image_settings)
        self.toolbar.addAction(setting_action)

        self.toolbar.addSeparator()

        crop_icon = os.path.join(wkdir, 'icons/crop.png')
        crop_action = QAction(QIcon(crop_icon), "Crop", self)
        crop_action.setStatusTip("Crop the image")
        crop_action.triggered.connect(self.crop)
        self.toolbar.addAction(crop_action)

        measure_icon = os.path.join(wkdir, 'icons/measure.png')
        measure_action = QAction(QIcon(measure_icon), "Measure", self)
        measure_action.setStatusTip("Measure distance and angle")
        measure_action.triggered.connect(self.measure)
        self.toolbar.addAction(measure_action)

        measurefft_icon = os.path.join(wkdir, 'icons/measure_fft.png')
        measurefft_action = QAction(QIcon(measurefft_icon), 'Measure FFT', self)
        measurefft_action.setStatusTip('Measure distance and angle in Diffraction/FFT')
        measurefft_action.triggered.connect(self.measure_fft)
        self.toolbar.addAction(measurefft_action)

        lineprofile_icon = os.path.join(wkdir, 'icons/lineprofile.png')
        lineprofile_action = QAction(QIcon(lineprofile_icon), "Line Profile", self)
        lineprofile_action.setStatusTip("Extract line profile")
        lineprofile_action.triggered.connect(self.lineprofile)
        self.toolbar.addAction(lineprofile_action)

        self.toolbar.addSeparator()

        fft_icon = os.path.join(wkdir, "icons/fft.png")
        fft_action = QAction(QIcon(fft_icon), "FFT", self)
        fft_action.setStatusTip("Compute FFT of the image")
        fft_action.triggered.connect(self.fft)
        self.toolbar.addAction(fft_action)

        livefft_icon = os.path.join(wkdir, "icons/live-fft.png")
        livefft_action = QAction(QIcon(livefft_icon), "Live FFT", self)
        livefft_action.setStatusTip("Compute live FFT of the image")
        livefft_action.triggered.connect(self.live_fft)
        self.toolbar.addAction(livefft_action)

        self.toolbar.addSeparator()

        wf_icon = os.path.join(wkdir, "icons/WF.png")
        wf_action = QAction(QIcon(wf_icon), "Wiener Filter", self)
        wf_action.setStatusTip("Apply Wiener filter to the image")
        wf_action.triggered.connect(self.wiener_filter)
        self.toolbar.addAction(wf_action)

        absf_icon = os.path.join(wkdir, "icons/ABSF.png")
        absf_action = QAction(QIcon(absf_icon), "ABS Filter", self)
        absf_action.setStatusTip("Apply ABSF to the image")
        absf_action.triggered.connect(self.absf_filter)
        self.toolbar.addAction(absf_action)

        nl_icon = os.path.join(wkdir, "icons/NL.png")
        nl_action = QAction(QIcon(nl_icon), "Non-linear Filter", self)
        nl_action.setStatusTip("Apply Non-linear filter to the image")
        nl_action.triggered.connect(self.non_linear_filter)
        self.toolbar.addAction(nl_action)

        gaussian_icon = os.path.join(wkdir, "icons/GS.png")
        gaussian_action = QAction(QIcon(gaussian_icon), "Gaussian Filter", self)
        gaussian_action.setStatusTip("Apply Gaussian filter to the image")
        gaussian_action.triggered.connect(self.gaussian_filter)
        self.toolbar.addAction(gaussian_action)

        self.toolbar.addSeparator()

        info_icon = os.path.join(wkdir, "icons/info.png")
        info_action = QAction(QIcon(info_icon), "Info", self)
        info_action.setStatusTip("Show image info")
        info_action.triggered.connect(self.show_info)
        self.toolbar.addAction(info_action)



    def setscale(self):
        # Open a dialog to take the scale
        dialog = SetScaleDialog(self.scale, self.units)
        if dialog.exec_() == QDialog.Accepted:
            scale = dialog.scale
            units = dialog.units
            try:
                scale = float(scale)
                units = str(units)
            except ValueError:
                QMessageBox.critical(self, 'Input Error', 'Please enter a valid scale or unit.')
                return
        
            # Update the new scale to the image dict
            self.scale = scale
            self.units = units

            self.set_scalebar_units()
            self.canvas.image_item.setScale(self.scale)
            self.canvas.viewbox.setRange(xRange=(0, self.img_size[-1]*self.scale), yRange=(0, self.img_size[-2]*self.scale), padding=0)
            
            # Recreate the scalebar with the new scale
            self.create_scalebar()
            
            print(f'Scale updated to {scale} {units}')
            
            # Keep the history
            self.update_metadata(f'Scale updated to {scale} {units}')


    

    def on_mouse_move(self, pos):
        if self.canvas.image_item:
            mouse_point = self.canvas.plot.plotItem.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()
            
            img_x = x / self.scale
            img_y = y / self.scale
            img_size = self.canvas.data['data'].shape

            if 0 <= img_x < img_size[-1] and 0 <= img_y < img_size[-2]:
                value = self.canvas.current_img[int(img_y), int(img_x)]
                
                # Update all labels with offsets
                self.pixel_label.setText(f"{x + self.canvas.offset_x:.2f} {self.units} | {img_x:.1f} px, {y + self.canvas.offset_y:.2f} {self.units} | {img_y:.1f} px")
                self.value_label.setText(f"{value:.2f}")
                
            else:
                self.pixel_label.setText(f"--- {self.units} | ---, --- {self.units} | ---,")
                self.value_label.setText("---")
                # self.statusBar.showMessage("Ready")

    def on_mouse_hover(self, event):
        if not event:
            self.pixel_label.setText(f"--- {self.units} | ---, --- {self.units} | ---,")
            self.value_label.setText("---")

    def position_window(self, pos='center'):
        # Set the window pop up position
        # Possible positions are:
        # 'center': screen center
        # 'center left': left side with the right edge on the screen center
        # 'center right': right side with the left edge on the screen
        # 'next to parent': the left edge next to its parent window
        # tuple (x, y): specific position of screen fraction (0-1)
        
        # Get screen resolution
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        width = screen_geometry.width()
        height = screen_geometry.height()
        frame_size = self.frameGeometry()
        
        if pos == 'center':
            x = (width - frame_size.width()) // 2
            y = (height - frame_size.height()) // 2

        elif pos == 'center left':
            x = width // 2 - frame_size.width()
            y = (height - frame_size.height()) // 2
        
        elif pos == 'center right':
            x = width // 2
            y = (height - frame_size.height()) // 2

        elif pos == 'next to parent':
            if self.parent() is not None:
                parent = self.parent()
                parent_geometry = parent.frameGeometry()
                x = parent_geometry.x() + parent_geometry.width()
                y = parent_geometry.y()
        
        else:
            # Handle tuple case
            if isinstance(pos, tuple) and len(pos) == 2:
                x = int(width * pos[0])
                y = int(height * pos[1])        
                
        self.move(x, y)

    def get_current_img_from_canvas(self):
        # Return the copy of the current image data only
        current_img = self.canvas.current_img.copy()
        return current_img
        
    def get_img_dict_from_canvas(self):
        # Return the current image together with the full dictionary
        current_img = self.get_current_img_from_canvas()
        img_dict = copy.deepcopy(self.canvas.data)
        img_dict['data'] = current_img
        if self.canvas.data_type == 'Image Stack':
            # Update axes
            img_dict['axes'].pop(0)
            img_dict['axes'][0]['index_in_array'] = 0
            img_dict['axes'][1]['index_in_array'] = 1
        return img_dict
    
    def get_original_img_dict(self):
        # Return the original image data together with the full dictionary
        img_dict = copy.deepcopy(self.canvas.data)
        return img_dict
    
    def plot_new_image(self, img_dict, canvas_name, parent=None, metadata=None):
        # Plot a new image in a new window
        # parent: the parent widget for the new image canvas
        # metadata: optional metadata to add in the image dictionary
        # position: the position of the new image canvas
        data = img_dict['data']
        UI_TemCompanion.preview_dict[canvas_name] = PlotCanvas(img_dict, parent=self.parent())
        if metadata is not None:
            UI_TemCompanion.preview_dict[canvas_name].update_metadata(metadata)
        UI_TemCompanion.preview_dict[canvas_name].setWindowTitle(canvas_name)
        UI_TemCompanion.preview_dict[canvas_name].canvas.canvas_name = canvas_name
        UI_TemCompanion.preview_dict[canvas_name].show()
        


    def update_metadata(self, metadata):
        # Update the metadata of the current canvas
        self.process['process'].append(metadata)
        self.canvas.data['metadata']['process'] = copy.deepcopy(self.process)

    def toggle_progress_bar(self, status='ON'):
        if status == 'ON':
            self.progressBar.setVisible(True)
            self.statusBar.showMessage("Processing...")
        else:
            self.progressBar.setVisible(False)
            self.statusBar.showMessage("Ready")
        
        
        
    def create_menubar(self):
        menubar = self.menuBar()

        # File menu and actions
        file_menu = menubar.addMenu('&File')
        save_action = QAction('&Save as', self)
        save_action.setShortcut('ctrl+s')
        save_action.triggered.connect(self.save_figure)
        file_menu.addAction(save_action)
        copy_action = QAction('&Copy Image to Clipboard', self)
        copy_action.setShortcut('ctrl+alt+c')
        copy_action.triggered.connect(self.copy_img)
        file_menu.addAction(copy_action)
        imagesetting_action = QAction('&Image Settings',self)
        imagesetting_action.setShortcut('ctrl+o')
        imagesetting_action.triggered.connect(self.image_settings)
        file_menu.addAction(imagesetting_action)
        close_action = QAction('&Close', self)
        close_action.setShortcut('ctrl+x')
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)
        close_all_action = QAction('&Close all', self)
        close_all_action.setShortcut('ctrl+shift+x')
        close_all_action.triggered.connect(self.close_all)
        file_menu.addAction(close_all_action)

        # Edit menu and actions
        edit_menu = menubar.addMenu('&Process')
        crop_action = QAction('&Crop', self)
        crop_action.setShortcut('ctrl+shift+c')
        crop_action.triggered.connect(self.crop)
        edit_menu.addAction(crop_action)
        rotate_action = QAction('&Rotate', self)
        rotate_action.setShortcut('ctrl+shift+r')
        rotate_action.triggered.connect(self.rotate)
        edit_menu.addAction(rotate_action)
        fliplr_action = QAction('Flip horizontal', self)
        fliplr_action.triggered.connect(self.flip_horizontal)
        edit_menu.addAction(fliplr_action)
        flipud_action = QAction('Flip vertical',self)
        flipud_action.triggered.connect(self.flip_vertical)
        edit_menu.addAction(flipud_action)
        resampling_action = QAction('Resampling', self)
        resampling_action.triggered.connect(self.resampling)
        edit_menu.addAction(resampling_action)
        simplemath_action = QAction('Simple math', self)
        simplemath_action.triggered.connect(self.simplemath)
        edit_menu.addAction(simplemath_action)

        
        # Analyze menu and actions
        analyze_menu = menubar.addMenu('&Analyze')
        setscale_action = QAction('Set Scale', self)
        setscale_action.triggered.connect(self.setscale)
        analyze_menu.addAction(setscale_action)
        measure_action = QAction('Measure', self)
        measure_action.triggered.connect(self.measure)
        analyze_menu.addAction(measure_action)
        measure_fft_action = QAction('Measure Diffraction/FFT', self)
        measure_fft_action.triggered.connect(self.measure_fft)        
        analyze_menu.addAction(measure_fft_action)        
        lineprofile_action = QAction('Line Profile', self)
        lineprofile_action.triggered.connect(self.lineprofile)
        analyze_menu.addAction(lineprofile_action)
        radial_integration_action = QAction('Radial Integration', self)
        radial_integration_action.triggered.connect(self.radial_integration)
        analyze_menu.addAction(radial_integration_action)
        gpa_action = QAction('Geometric Phase Analysis', self)
        gpa_action.triggered.connect(self.gpa)
        analyze_menu.addAction(gpa_action)
        dpc_action = QAction('Reconstruct DPC', self)
        dpc_action.triggered.connect(self.dpc)
        analyze_menu.addAction(dpc_action)

        # FFT menu
        fft_menu = menubar.addMenu('&FFT')
        fft_action = QAction('&FFT', self)
        fft_action.setShortcut('ctrl+f')
        fft_action.triggered.connect(self.fft)
        fft_menu.addAction(fft_action)
        windowedfft_action = QAction('Windowed FFT', self)
        windowedfft_action.triggered.connect(self.windowedfft)
        fft_menu.addAction(windowedfft_action)
        livefft_action = QAction('&Live FFT', self)
        livefft_action.setShortcut('ctrl+shift+f')
        livefft_action.triggered.connect(self.live_fft)
        fft_menu.addAction(livefft_action)
        

        # Filter menu and actions
        filter_menu = menubar.addMenu('&Filter')
        filtersetting_action = QAction('&Filter Settings', self)
        filtersetting_action.triggered.connect(UI_TemCompanion.filter_settings)
        filter_menu.addAction(filtersetting_action)
        
        wiener_action = QAction('&Apply Wiener', self)
        wiener_action.setShortcut('ctrl+shift+w')
        wiener_action.triggered.connect(self.wiener_filter)
        filter_menu.addAction(wiener_action)
        absf_action = QAction('&Apply ABSF', self)
        absf_action.setShortcut('ctrl+shift+a')
        absf_action.triggered.connect(self.absf_filter)
        filter_menu.addAction(absf_action)
        non_linear_action = QAction('&Apply Non-Linear', self)
        non_linear_action.setShortcut('ctrl+shift+n')
        non_linear_action.triggered.connect(self.non_linear_filter)
        filter_menu.addAction(non_linear_action)
        bw_action = QAction('&Apply Butterworth low pass', self)
        bw_action.setShortcut('ctrl+shift+b')
        bw_action.triggered.connect(self.bw_filter)
        filter_menu.addAction(bw_action)
        gaussian_action = QAction('&Apply Gaussian low pass', self)
        gaussian_action.setShortcut('ctrl+shift+g')
        gaussian_action.triggered.connect(self.gaussian_filter)
        filter_menu.addAction(gaussian_action)

        # Stack menu
        if self.canvas.data_type == 'Image Stack':
            stack_menu = menubar.addMenu('&Stack')
            crop_stack = QAction('Crop stack', self)
            crop_stack.triggered.connect(self.crop_stack)
            stack_menu.addAction(crop_stack)
            rotate_stack = QAction('Rotate stack', self)
            rotate_stack.triggered.connect(self.rotate_stack)
            stack_menu.addAction(rotate_stack)
            fliplr_stack = QAction('Flip horizontal', self)
            fliplr_stack.triggered.connect(self.flip_stack_horizontal)
            stack_menu.addAction(fliplr_stack)
            flipud_stack = QAction('Flip vertical', self)
            flipud_stack.triggered.connect(self.flip_stack_vertical)
            stack_menu.addAction(flipud_stack)
            resampling_stack = QAction('Resampling stack', self)
            resampling_stack.triggered.connect(self.resampling_stack)
            stack_menu.addAction(resampling_stack)
            reslice_stack = QAction('Reslice stack', self)
            reslice_stack.triggered.connect(self.reslice_stack)
            stack_menu.addAction(reslice_stack)
            sort_stack = QAction('Sort stack', self)
            sort_stack.triggered.connect(self.sort_stack)
            stack_menu.addAction(sort_stack)
            align_stack_cc = QAction('Align stack with Cross-Correlation', self)
            align_stack_cc.triggered.connect(self.align_stack_cc)
            stack_menu.addAction(align_stack_cc)
            align_stack_of = QAction('Align stack with Optical Flow', self)
            align_stack_of.triggered.connect(self.align_stack_of)
            stack_menu.addAction(align_stack_of)
            integrate_stack = QAction('Integrate stack', self)
            integrate_stack.triggered.connect(self.integrate_stack)  
            stack_menu.addAction(integrate_stack)
            export_stack = QAction('Export as tiff stack', self)
            export_stack.triggered.connect(self.export_stack)
            stack_menu.addAction(export_stack)
            export_stack_gif = QAction('Export as GIF animation', self)
            export_stack_gif.triggered.connect(self.export_stack_gif)
            stack_menu.addAction(export_stack_gif)
            export_series = QAction('Save as series', self)
            export_series.triggered.connect(self.export_series)
            stack_menu.addAction(export_series)

        # Info menu
        info_menu = menubar.addMenu('&Info')
        # axes_action = QAction('Image Axes', self)
        # axes_action.triggered.connect(self.show_axes)
        # info_menu.addAction(axes_action)
        info_action = QAction('&Image Info', self)
        info_action.setShortcut('ctrl+i')
        info_action.triggered.connect(self.show_info)
        info_menu.addAction(info_action)
        about_action = QAction('About', self)
        about_action.triggered.connect(UI_TemCompanion.show_about)
        info_menu.addAction(about_action)

        self.menubar = menubar
        

    def image_settings(self):
        dialog = CustomSettingsDialog(self.canvas.image_item, parent=self)
        dialog.show()


    def save_figure(self):
        options = QFileDialog.Options()
        self.file_path, self.selected_type = QFileDialog.getSaveFileName(self.parent(), 
                                                   "Save Figure", 
                                                   "", 
                                                   "16-bit TIFF Files (*.tiff);;32-bit TIFF Files (*.tiff);;8-bit Grayscale TIFF Files (*.tiff);;Grayscale PNG Files (*.png);;Grayscale JPEG Files (*.jpg);;Color TIFF Files (*.tiff);;Color PNG Files (*.png);;Color JPEG Files (*.jpg);;Pickle Dictionary Files (*.pkl)", 
                                                   options=options)
        if self.file_path:
            # Implement custom save logic here
           
            # Extract the chosen file format            
            self.file_type = getFileType(self.file_path)
            self.f_name = getFileName(self.file_path)
            self.output_dir = getDirectory(self.file_path,s='/')
            print(f"Save figure to {self.file_path} with format {self.file_type}")
            img_to_save = {}
            if self.selected_type == 'Pickle Dictionary Files (*.pkl)':               
                img_dict = self.get_img_dict_from_canvas()
                for key in ['data', 'axes', 'metadata', 'original_metadata']:
                    if key in img_dict.keys():
                        img_to_save[key] = img_dict[key]
                with open(self.file_path, 'wb') as f:
                    pickle.dump(img_to_save, f)
            else:                            
                # Save the current data only
                current_img = self.get_img_dict_from_canvas()
                for key in ['data', 'axes', 'metadata', 'original_metadata']:
                    if key in current_img.keys():
                        img_to_save[key] = current_img[key]
                
                if self.selected_type == '16-bit TIFF Files (*.tiff)':
                    
                    save_as_tif16(img_to_save, self.f_name, self.output_dir)
                elif self.selected_type == '32-bit TIFF Files (*.tiff)':
                    save_as_tif16(img_to_save, self.f_name, self.output_dir, dtype='float32')
                    
                elif self.selected_type in ['8-bit Grayscale TIFF Files (*.tiff)','Grayscale PNG Files (*.png)', 'Grayscale JPEG Files (*.jpg)']:
                    save_with_pil(img_to_save, self.f_name, self.output_dir, self.file_type, scalebar=self.scalebar_settings['scalebar']) 
                else:
                    # Save with pyqtgraph export function
                    exporter = pg.exporters.ImageExporter(self.canvas.viewbox)
                    exporter.parameters()['width'] = self.img_size[1]  # Set export width to original image width
                    # exporter.parameters()['height'] = self.img_size[0]  # Set export height to original image height
                    exporter.export(self.file_path)

    def close_all(self):
        plots = list(UI_TemCompanion.preview_dict.keys())
        for plot in plots:
            try:
                UI_TemCompanion.preview_dict[plot].close()
            except Exception as e:
                print(f"Error closing plot {plot}: {e}, ignored.")

    def copy_img(self):
        # Grab the ViewBox as a QPixmap.
        # Because a ViewBox is a QGraphicsItem, not a QWidget, we must grab its parent GraphicsView.
        # The `PlotWidget` is a `GraphicsView` that contains the `ViewBox`.
        pixmap = self.canvas.viewbox.scene().views()[0].grab(self.canvas.viewbox.sceneBoundingRect().toRect())

        # Set the pixmap to the clipboard
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(pixmap)
        self.statusBar.showMessage("The current image has been copied to the clipboard!")

    def rotate(self):
        # Open a dialog to take the rotation angle
        dialog = RotateImageDialog()
        # Display a message in the status bar
        if dialog.exec_() == QDialog.Accepted:
            ang = dialog.rotate_ang
            try:
                ang = float(ang)
            except ValueError:
                QMessageBox.critical(self, 'Input Error', 'Please enter a valid angle.')
                return
        
            # Process the rotation
            img = self.get_img_dict_from_canvas()
            img_to_rotate = img['data']
            rotated_array = rotate(img_to_rotate,ang)
            img['data'] = rotated_array
            
            # Update axes size
            img['axes'][0]['size'] = img['data'].shape[0]
            img['axes'][1]['size'] = img['data'].shape[1]
            
            # Create a new PlotCanvs to display        
            title = self.windowTitle()
            preview_name = self.canvas.canvas_name + '_R{}'.format(ang)
            UI_TemCompanion.preview_dict[preview_name] = PlotCanvas(img, parent=self.parent())
            UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
            UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
            UI_TemCompanion.preview_dict[preview_name].show()
            print(f'Rotated {title} by {ang} degrees counterclockwise.')
            
            # Positioning
            self.position_window('center left')
            UI_TemCompanion.preview_dict[preview_name].position_window('center right')
            
            # Keep the history
            self.update_metadata(f'Rotated by {ang} degrees from the original image')
    
            
    
    def flip_horizontal(self):
        img = self.get_img_dict_from_canvas()
        img_to_flip = img['data']
        flipped_array = np.fliplr(img_to_flip)
        img['data'] = flipped_array
        
        # Create a new PlotCanvs to display        
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_Flipped_LR'
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvas(img, parent=self.parent())
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].show()
        
        print(f'Flipped {title} horizontally.')
        
        # Positioning
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
        # Keep the history
        self.update_metadata('Flipped horizontally')
        
        
    def flip_vertical(self):
        img = self.get_img_dict_from_canvas()
        img_to_flip = img['data']
        flipped_array = np.flipud(img_to_flip)
        img['data'] = flipped_array
        
        # Create a new PlotCanvs to display        
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_Flipped_UD'
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvas(img, parent=self.parent())
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].show()
        
        print(f'Flipped {title} vertically.')
        
        # Positioning
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
        # Keep the history
        self.update_metadata('Flipped vertically')
        

    def resampling(self):
        # Open a dialog to take the scale factor. Reuse the rotate angle dialog
        dialog = RotateImageDialog()
        dialog.setWindowTitle("Resampling image")
        dialog.angle_input.setPlaceholderText('Enter rescaling factor')
        # Display a message in the status bar
        if dialog.exec_() == QDialog.Accepted:
            rescale_factor = dialog.rotate_ang
            try:
                rescale_factor = float(rescale_factor)
            except ValueError:
                QMessageBox.critical(self, 'Input Error', 'Please enter a valid rescale factor.')
                return
            
            
            img = self.get_img_dict_from_canvas()
            img_to_rebin = img['data']
            rebinned_array = rescale(img_to_rebin, rescale_factor)
            img['data'] = rebinned_array
            
            # Update axes
            new_scale = self.scale / rescale_factor
            new_y, new_x = rebinned_array.shape
            img['axes'][0]['scale'] = new_scale
            img['axes'][0]['size'] = new_y
            img['axes'][1]['scale'] = new_scale
            img['axes'][1]['size'] = new_x
            
            # Create a new PlotCanvs to display        
            title = self.windowTitle()
            preview_name = self.canvas.canvas_name + '_Resampled'
            self.plot_new_image(img, preview_name, parent=self.parent(),metadata=f'Resampled {title} by a factor of {rescale_factor}.')
            
            # Positioning
            self.position_window('center left')
            UI_TemCompanion.preview_dict[preview_name].position_window('center right')

    def simplemath(self):
        dialog = SimpleMathDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            signal1 = dialog.signal1
            signal2 = dialog.signal2
            operation = dialog.operation
            try:
                img1 = copy.deepcopy(find_img_by_title(signal1).canvas.data)
            except Exception as e:
                QMessageBox.warning(self, 'Simple Math', f'Operation not possible on image 1: {e}')
                return
            try:
                img2 = copy.deepcopy(find_img_by_title(signal2).canvas.data)
            except Exception as e:
                QMessageBox.warning(self, 'Simple Math', f'Operation not possible on image 2: {e}')
                return
            
            if operation == 'Add':
                try:
                    img1['data'] = img1['data'] + img2['data']
                except Exception as e:
                    QMessageBox.warning(self, 'Simple Math', f'Operation not possible: {e}')
                    return
            if operation == 'Subtract':
                try:
                    img1['data'] = img1['data'] - img2['data']
                except Exception as e:
                    QMessageBox.warning(self, 'Simple Math', f'Operation not possible: {e}')
                    return
            if operation == 'Multiply':
                try:
                    img1['data'] = img1['data'] * img2['data']
                except Exception as e:    
                    QMessageBox.warning(self, 'Simple Math', f'Operation not possible: {e}')
                    return
            if operation == 'Divide':
                try:
                    img1['data'] = img1['data'] / img2['data']
                except Exception as e:
                    QMessageBox.warning(self, 'Simple Math', f'Operation not possible: {e}')
                    return
            if operation == 'Inverse':
                try:
                    img1['data'] = -img1['data']
                except Exception as e:
                    QMessageBox.warning(self, 'Simple Math', f'Operation not possible: {e}')
                    return

                
            # Plot the new image
            preview_name = signal1 + '_processed'

            if operation == 'Inverse':
                metadata = f'Inversed signal of {signal1}'
            else:
                metadata = f'Processed by {signal1} {operation} {signal2}'

            self.plot_new_image(img1, canvas_name=preview_name, parent=self.parent(), metadata=metadata)
            # Positioning
            UI_TemCompanion.preview_dict[preview_name].position_window('center')
            
    def dpc(self):
        self.dpc_dialog = DPCDialog(parent=self)
        self.dpc_dialog.show()

    def wiener_filter(self):        
        filter_parameters = UI_TemCompanion.filter_parameters        
        delta_wf = int(filter_parameters['WF Delta'])
        order_wf = int(filter_parameters['WF Bw-order'])
        cutoff_wf = float(filter_parameters['WF Bw-cutoff'])
        img_wf = self.get_original_img_dict()
        title = self.windowTitle()
        data = img_wf['data']
        apply_to = None
        if self.canvas.data_type == 'Image Stack':
            dialog = ApplyFilterDialog(parent=self)
            if dialog.exec_() == QDialog.Accepted:
                apply_to = dialog.apply_to
                if apply_to == 'current':
                    img_wf = self.get_img_dict_from_canvas()
                    data = img_wf['data']
            else:
                return
        elif self.canvas.data_type == 'Image':
            apply_to = 'current'
        if apply_to is not None:
            preview_name = self.canvas.canvas_name + '_' + apply_to +'_Wiener Filtered'
            metadata = f'Wiener filter applied with delta = {delta_wf}, Bw-order = {order_wf}, Bw-cutoff = {cutoff_wf}'

            # Positioning
            self.position_window('center left')

            # Apply the filter in a separate thread
            print(f'Applying Wiener filter to {title} with delta = {delta_wf}, Bw-order = {order_wf}, Bw-cutoff = {cutoff_wf}...')
            self.thread = QThread()
            self.worker = Worker(apply_filter_on_img_dict, img_wf, 'Wiener', delta=delta_wf, lowpass_order=order_wf, lowpass_cutoff=cutoff_wf)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(lambda: self.toggle_progress_bar('ON'))
            self.thread.started.connect(self.worker.run)            
            self.thread.finished.connect(lambda: self.toggle_progress_bar('OFF'))
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)           
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.finished.connect(lambda: print(f'Applied Wiener filter to {title} with delta = {delta_wf}, Bw-order = {order_wf}, Bw-cutoff = {cutoff_wf}.'))
            self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata))
            self.worker.result.connect(lambda: UI_TemCompanion.preview_dict[preview_name].position_window('center right'))
            self.thread.start()        
        

    def absf_filter(self):
        filter_parameters = UI_TemCompanion.filter_parameters        
        delta_absf = int(filter_parameters['ABSF Delta'])
        order_absf = int(filter_parameters['ABSF Bw-order'])
        cutoff_absf = float(filter_parameters['ABSF Bw-cutoff'])
        img_absf = self.get_original_img_dict()
        title = self.windowTitle()
        apply_to = None
        data = img_absf['data']
        if self.canvas.data_type == 'Image Stack':
            dialog = ApplyFilterDialog(parent=self)
            if dialog.exec_() == QDialog.Accepted:
                apply_to = dialog.apply_to
                if apply_to == 'current':
                    img_absf = self.get_img_dict_from_canvas()
                    data = img_absf['data']
            else:
                return
        elif self.canvas.data_type == 'Image':
            apply_to = 'current'
        if apply_to is not None:
            preview_name = self.canvas.canvas_name + '_' + apply_to +'_ABS Filtered'
            metadata = f'ABS filter applied with delta = {delta_absf}, Bw-order = {order_absf}, Bw-cutoff = {cutoff_absf}'

            # Positioning
            self.position_window('center left')
            # Apply the filter in a separate thread
            print(f'Applying ABS filter to {title} with delta = {delta_absf}, Bw-order = {order_absf}, Bw-cutoff = {cutoff_absf}...')
            self.thread = QThread()
            self.worker = Worker(apply_filter_on_img_dict, img_absf, 'ABS', delta=delta_absf, lowpass_order=order_absf, lowpass_cutoff=cutoff_absf)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(lambda: self.toggle_progress_bar('ON'))
            self.thread.started.connect(self.worker.run)            
            self.thread.finished.connect(lambda: self.toggle_progress_bar('OFF'))
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)           
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.finished.connect(lambda: print(f'Applied ABS filter to {title} with delta = {delta_absf}, Bw-order = {order_absf}, Bw-cutoff = {cutoff_absf}.'))
            self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata))
            self.worker.result.connect(lambda: UI_TemCompanion.preview_dict[preview_name].position_window('center right'))
            self.thread.start()        

    
    def non_linear_filter(self):
        filter_parameters = UI_TemCompanion.filter_parameters        
        delta_nl = int(filter_parameters['NL Delta'])
        order_nl = int(filter_parameters['NL Bw-order'])
        cutoff_nl = float(filter_parameters['NL Bw-cutoff'])
        N = int(filter_parameters['NL Cycles'])
        img_nl = self.get_original_img_dict()
        title = self.windowTitle()
        data = img_nl['data']
        apply_to = None
        if self.canvas.data_type == 'Image Stack':
            dialog = ApplyFilterDialog(parent=self)
            if dialog.exec_() == QDialog.Accepted:
                apply_to = dialog.apply_to
                if apply_to == 'current':
                    img_nl = self.get_img_dict_from_canvas()
                    data = img_nl['data']
            else:
                return
        elif self.canvas.data_type == 'Image':
            apply_to = 'current'
        if apply_to is not None:
            preview_name = self.canvas.canvas_name + '_' + apply_to + '_NL Filtered'
            metadata = f'Non-Linear filter applied with N = {N}, delta = {delta_nl}, Bw-order = {order_nl}, Bw-cutoff = {cutoff_nl}'
                # Position the current image
            self.position_window('center left')

            # Apply the filter in a separate thread
            print(f'Applying Non-Linear filter to {title} with N = {N}, delta = {delta_nl}, Bw-order = {order_nl}, Bw-cutoff = {cutoff_nl}...')
            self.thread = QThread()
            self.worker = Worker(apply_filter_on_img_dict, img_nl, 'NL', N=N, delta=delta_nl, lowpass_order=order_nl, lowpass_cutoff=cutoff_nl)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(lambda: self.toggle_progress_bar('ON'))
            self.thread.started.connect(self.worker.run)            
            self.thread.finished.connect(lambda: self.toggle_progress_bar('OFF'))
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)           
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.finished.connect(lambda: print(f'Applied Non-Linear filter to {title} with N = {N}, delta = {delta_nl}, Bw-order = {order_nl}, Bw-cutoff = {cutoff_nl}.'))
            self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata))
            self.worker.result.connect(lambda: UI_TemCompanion.preview_dict[preview_name].position_window('center right'))
            self.thread.start()

    def bw_filter(self):
        filter_parameters = UI_TemCompanion.filter_parameters        
        order_bw = int(filter_parameters['Bw-order'])
        cutoff_bw = float(filter_parameters['Bw-cutoff'])
        img_bw = self.get_original_img_dict()
        title = self.windowTitle()
        data = img_bw['data']
        apply_to = None
        if self.canvas.data_type == 'Image Stack':
            dialog = ApplyFilterDialog(parent=self)
            if dialog.exec_() == QDialog.Accepted:
                apply_to = dialog.apply_to
                if apply_to == 'current':
                    img_bw = self.get_img_dict_from_canvas()
                    data = img_bw['data']
            else:
                return
        elif self.canvas.data_type == 'Image':
            apply_to = 'current'
        if apply_to is not None:
            preview_name = self.canvas.canvas_name + '_' + apply_to + '_Bw Filtered'
            metadata = f'Butterworth filter applied with Bw-order = {order_bw}, Bw-cutoff = {cutoff_bw}'

            # Position the current image
            self.position_window('center left')

            # Apply the filter in a separate thread
            print(f'Applying Butterworth filter to {title} with Bw-order = {order_bw}, Bw-cutoff = {cutoff_bw}...')
            self.thread = QThread()
            self.worker = Worker(apply_filter_on_img_dict, img_bw, 'BW', order=order_bw, cutoff_ratio=cutoff_bw)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(lambda: self.toggle_progress_bar('ON'))
            self.thread.started.connect(self.worker.run)            
            self.thread.finished.connect(lambda: self.toggle_progress_bar('OFF'))
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)           
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.finished.connect(lambda: print(f'Applied Butterworth filter to {title} with Bw-order = {order_bw}, Bw-cutoff = {cutoff_bw}.'))
            self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata))
            self.worker.result.connect(lambda: UI_TemCompanion.preview_dict[preview_name].position_window('center right'))
            self.thread.start()


        

    def gaussian_filter(self):
        filter_parameters = UI_TemCompanion.filter_parameters        
        cutoff_gaussian = float(filter_parameters['GS-cutoff'])
        img_gaussian = self.get_original_img_dict()
        title = self.windowTitle()
        data = img_gaussian['data']
        apply_to = None
        if self.canvas.data_type == 'Image Stack':
            dialog = ApplyFilterDialog(parent=self)
            if dialog.exec_() == QDialog.Accepted:
                apply_to = dialog.apply_to
                if apply_to == 'current':
                    img_gaussian = self.get_img_dict_from_canvas()
                    data = img_gaussian['data']
            else:
                return
        elif self.canvas.data_type == 'Image':
            apply_to = 'current'
        if apply_to is not None:
            preview_name = self.canvas.canvas_name + '_' + apply_to + '_Gaussian Filtered'
            metadata = f'Gaussian filter applied with cutoff = {cutoff_gaussian}'
            
            # Position the current image
            self.position_window('center left')

            # Apply the filter in a separate thread
            print(f'Applying Gaussian filter to {title} with cutoff = {cutoff_gaussian}...')
            self.thread = QThread()
            self.worker = Worker(apply_filter_on_img_dict, img_gaussian, 'Gaussian', cutoff_ratio=cutoff_gaussian)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(lambda: self.toggle_progress_bar('ON'))
            self.thread.started.connect(self.worker.run)            
            self.thread.finished.connect(lambda: self.toggle_progress_bar('OFF'))
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)           
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.finished.connect(lambda: print(f'Applied Gaussian filter to {title} with cutoff = {cutoff_gaussian}.'))
            self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata))
            self.worker.result.connect(lambda: UI_TemCompanion.preview_dict[preview_name].position_window('center right'))
            self.thread.start()


    def show_info(self):
        # Show image infomation including metadata
        img_dict = self.get_img_dict_from_canvas()
        metadata = img_dict['metadata']
        
        try: 
            extra_metadata = img_dict['original_metadata']
            metadata.update(extra_metadata)
        except Exception as e:
            pass
        
        img_info = OrderedDict()
        img_info['File Name'] = self.parent().file
        img_info['Data Type'] = self.canvas.data_type
        img_info['Image Size (pixels)'] = f"{img_dict['data'].shape}"
        img_info['Calibrated Image Size'] = f"{self.canvas.img_size[-1] * self.scale:.4g} x {self.canvas.img_size[-2] * self.scale:.4g} {self.units}"
        img_info['Pixel Calibration'] = f"{self.scale:.4g} {self.units}"
        # Add axes info to metadata
        axes = img_dict['axes']
        axes_dict = {}
        for ax in axes:
            axes_dict[ax['name']] = ax
        img_info['Axes'] = axes_dict
        img_info['Processing History'] = metadata.pop('process')

        img_info['Metadata'] = metadata

        self.metadata_viewer = MetadataViewer(img_info, parent=self)
        self.metadata_viewer.show()

    def fft(self):
        img_dict = self.get_img_dict_from_canvas()
        # FFT calculation is handled in the PlotCanvasFFT class

        title = self.canvas.canvas_name
        
        preview_name = title + '_FFT'
        
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvasFFT(img_dict, parent=self)
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].update_metadata(f'FFT of {title}.')
        UI_TemCompanion.preview_dict[preview_name].show()
        
        # Positioning
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('next to parent')
        
        
        
    
    def windowedfft(self):
        img_dict = self.get_img_dict_from_canvas()
        # Crop to a square if not
        data = img_dict['data']
        if data.shape[0] != data.shape[1]:
            # Image will be cropped to square for FFT
            data = filters.crop_to_square(data)
            new_size = data.shape[0]
            for ax in img_dict['axes']:
                ax['size'] = new_size

        w = window('hann', data.shape)
        img_dict['data'] = data * w
        # FFT calculation is handled in the PlotCanvasFFT class

        title = self.canvas.canvas_name
        
        preview_name = title + '_Windowed_FFT'
        
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvasFFT(img_dict, parent=self)
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].update_metadata(f'Windowed FFT of {title}.')
        UI_TemCompanion.preview_dict[preview_name].show()
        
        # Positioning
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('next to parent')

    def live_fft(self, fullsize=False, windowed=False, resize_fft=False):
        self.clean_up(selector=True, buttons=True, modes=True, cid=True, status_bar=True)  # Clean up any existing modes or selectors
        # Activate live FFT mode
        self.mode_control['Live_FFT'] = True
        self.statusBar.showMessage("Drag the square to display FFT.")
        # Add a square selector
        # Initial rectangle position
        x_range = self.img_size[-1] * self.scale
        y_range = self.img_size[-2] * self.scale
        x0 = x_range * 0.25
        y0 = y_range * 0.25
        size = 0.5 * min(x_range, y_range)
        aspect_lock = True
        if fullsize:
            x0 = 0
            y0 = 0
            size = (x_range, y_range)
            # Remove aspect lock for full size used for GPA
            aspect_lock = False
        
        selector = pg.RectROI([x0, y0], size, 
                                    pen=pg.mkPen('r', width=5), 
                                    movable=True, 
                                    resizable=True, 
                                    sideScalers=True,
                                    rotatable=False,
                                    aspectLocked=aspect_lock,
                                    maxBounds=QRectF(0, 0, x_range, y_range))
        self.canvas.selector.append(selector)
        self._make_active_selector(selector)

        self.canvas.viewbox.addItem(selector)

        # Create a new PlotCanvasFFT to display the live FFT
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_Live FFT'
        self.live_img = self.get_img_dict_from_canvas()
        # Crop the selected area
        x0, y0 = int(selector.pos().x() / self.scale), int(selector.pos().y() / self.scale)
        span_x = int(selector.size()[0] / self.scale)
        span_y = int(selector.size()[1] / self.scale)
        x1 = x0 + span_x
        y1 = y0 + span_y
        live_cropped_img = self.live_img['data'][y0:y1, x0:x1]
        if windowed:
            w = window('hann', live_cropped_img.shape)
            live_cropped_img = live_cropped_img * w
        self.live_img['data'] = live_cropped_img
        self.live_img['axes'][0]['size'] = self.live_img['data'].shape[0]
        self.live_img['axes'][1]['size'] = self.live_img['data'].shape[1]
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvasFFT(self.live_img, parent=self)
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].show()
        UI_TemCompanion.preview_dict[preview_name].update_metadata(f'Live FFT of {title}.')
        print(f'Displaying live FFT of {title} from {x0},{y0},{x1},{y1}.')
        # Positioning
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')

        # Connect the selector's sigRegionChanged signal to update the FFT
        selector.sigRegionChanged.connect(lambda: self.update_live_fft(windowed=windowed, resize_fft=resize_fft))

        self.canvas.setFocus()  # Ensure the canvas has focus to receive key events

    def update_live_fft(self, windowed=False, resize_fft=False):
        if self.canvas.selector and self.mode_control['Live_FFT']:
            selector = self.canvas.selector[0]
            x0, y0 = int(selector.pos().x() / self.scale), int(selector.pos().y() / self.scale)
            span_x = int(selector.size()[0] / self.scale)
            span_y = int(selector.size()[1] / self.scale)
            x1 = x0 + span_x
            y1 = y0 + span_y
            self.live_img = self.get_img_dict_from_canvas()
            live_cropped_img = self.live_img['data'][y0:y1, x0:x1]
            
            if windowed:
                w = window('hann', live_cropped_img.shape)
                live_cropped_img = live_cropped_img * w
            self.live_img['data'] = live_cropped_img
            self.live_img['axes'][0]['size'] = self.live_img['data'].shape[0]
            self.live_img['axes'][1]['size'] = self.live_img['data'].shape[1]

            preview_name = self.canvas.canvas_name + '_Live FFT'
            if preview_name in UI_TemCompanion.preview_dict:
                fft_canvas = UI_TemCompanion.preview_dict[preview_name]
                fft_canvas.update_fft_with_img(self.live_img, resize_fft=resize_fft)
                print(f'Displaying live FFT of {self.canvas.canvas_name} from {x0},{y0},{x1},{y1}.')

    def stop_live_fft(self):
        self.clean_up(selector=True, modes=True, status_bar=True)  # Clean up any existing modes or selectors

            
    def crop(self):
        self.clean_up(selector=True, buttons=True, modes=True, cid=True, status_bar=True)  # Clean up any existing modes or selectors

        # Display a message in the status bar
        self.statusBar.showMessage("Drag the rectangle to crop.")

        # Initial rectangle position %37.5 from the left and top, 25% of the width, square
        x_range = self.img_size[-1] * self.scale
        y_range = self.img_size[-2] * self.scale
        x0 = x_range * 0.375 
        y0 = y_range * 0.375 
        selector = pg.RectROI([x0, y0], [x_range * 0.25, x_range * 0.25], 
                                pen=pg.mkPen('r', width=5), 
                                movable=True, 
                                resizable=True, 
                                sideScalers=True,
                                rotatable=False,
                                maxBounds=QRectF(0, 0, x_range, y_range))

        self.canvas.selector.append(selector)
        self._make_active_selector(selector)
        self.canvas.viewbox.addItem(selector)

        # Add buttons for confirm, cancel, and manual input
        OK_icon = os.path.join(wkdir, 'icons/OK.png')
        self.buttons['ok'] = QAction(QIcon(OK_icon), 'Confirm Crop', parent=self)
        self.buttons['ok'].setShortcut('Return')
        self.buttons['ok'].setStatusTip('Confirm Crop (Enter)')
        self.buttons['ok'].triggered.connect(self.confirm_crop)
        self.toolbar.addAction(self.buttons['ok'])
        cancel_icon = os.path.join(wkdir, 'icons/cancel.png')
        self.buttons['cancel'] = QAction(QIcon(cancel_icon), 'Cancel Crop', parent=self)
        self.buttons['cancel'].setShortcut('Esc')
        self.buttons['cancel'].setStatusTip('Cancel Crop (Esc)')
        self.buttons['cancel'].triggered.connect(self.cancel_crop)
        self.toolbar.addAction(self.buttons['cancel'])

        hand_icon = os.path.join(wkdir, 'icons/hand.png')
        self.buttons['crop_hand'] = QAction(QIcon(hand_icon), 'Manual Input', parent=self)
        self.buttons['crop_hand'].setStatusTip('Manual Input of Crop Coordinates')
        self.buttons['crop_hand'].triggered.connect(self.manual_crop)
        self.toolbar.addAction(self.buttons['crop_hand'])

        self.canvas.setFocus()  # Ensure the canvas has focus to receive key events

    
            

    def manual_crop(self):
        if self.canvas.selector:
            dialog = ManualCropDialog(parent=self)
           
            if dialog.exec_() == QDialog.Accepted:
                x0, x1 = dialog.x_range
                y0, y1 = dialog.y_range
                x0, x1, y0, y1 = x0 * self.scale, x1 * self.scale, y0 * self.scale, y1 * self.scale
                selector = self.canvas.selector[0]
                selector.setPos([x0, y0])
                selector.setSize([x1 - x0, y1 - y0])


    def confirm_crop(self, stack=False):
        if self.canvas.selector:
            selector = self.canvas.selector[0]
            x0, y0 = selector.pos()
            x1 = x0 + selector.size()[0]
            y1 = y0 + selector.size()[1]
            x0, x1, y0, y1 = int(x0 / self.scale), int(x1 / self.scale), int(y0 / self.scale), int(y1 / self.scale)
            if abs(x1 - x0) > 5 and abs(y1 - y0) > 5: 
                # Valid area is selected 
                if stack:
                    img = self.get_original_img_dict()
                    cropped_img = img['data'][:, int(y0):int(y1), int(x0):int(x1)]   
                else:          
                    img = self.get_img_dict_from_canvas()
                    cropped_img = img['data'][int(y0):int(y1), int(x0):int(x1)]   

                img['data'] = cropped_img
                
                # Update axes size
                img['axes'][-2]['size'] = img['data'].shape[-2]
                img['axes'][-1]['size'] = img['data'].shape[-1]


                # Create a new PlotCanvas to display
                title = self.windowTitle()
                preview_name = self.canvas.canvas_name + '_cropped'
                metadata = f'Cropped by {x0}:{x1}, {y0}:{y1} from the original image.'
                self.plot_new_image(img, preview_name, parent=self.parent(), metadata=metadata)

                # Positioning
                self.position_window('center left')
                UI_TemCompanion.preview_dict[preview_name].position_window('center right')
                
                print(metadata)
                
                # Remove the selector and buttons
                self.cancel_crop()
            
    
    def cancel_crop(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)
        

    def measure(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)  # Clean up any existing modes or selectors
        # Activate measure mode
        self.mode_control['measurement'] = True
        self.statusBar.showMessage("Drag the line to measure distance and angle.")
        
        # Buttons for finish
        OK_icon = os.path.join(wkdir, 'icons/OK.png')
        self.buttons['ok'] = QAction(QIcon(OK_icon), 'OK', parent=self)
        self.buttons['ok'].setStatusTip('Finish Measurement')
        self.buttons['ok'].setShortcut('Esc')
        self.buttons['ok'].triggered.connect(self.stop_distance_measurement)
        self.toolbar.addAction(self.buttons['ok'])

        # Add a line selector
        x_range = self.img_size[-1] * self.scale
        y_range = self.img_size[-2] * self.scale
        start_point = 0.375 * x_range, 0.5 * y_range
        end_point = 0.625 * x_range, 0.5 * y_range

        selector = pg.LineSegmentROI([start_point, end_point],
                                        pen=pg.mkPen('y', width=3),
                                        movable=True,
                                        rotatable=True,
                                        resizable=True
                                        )
        self.canvas.selector.append(selector)
        self._make_active_selector(selector)
        self.canvas.viewbox.addItem(selector)

        # Connect signals for line change
        selector.sigRegionChanged.connect(self.display_distance)
        self.canvas.setFocus()  # Ensure the canvas has focus to receive key events
        
    def display_distance(self):
        if self.canvas.selector and self.mode_control['measurement']:
            selector = self.canvas.selector[0]
            start_point, end_point = selector.getHandles()[0].pos(), selector.getHandles()[1].pos()
            x0, y0 = start_point.x(), start_point.y()
            x1, y1 = end_point.x(), end_point.y()
            distance = np.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
            angle = calculate_angle_to_horizontal((x0, y0), (x1, y1))
            # Display the distance in the status bar
            self.statusBar.showMessage(f"Measurement: {distance:.3f} {self.units}, {angle:.2f}°")

    def stop_distance_measurement(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)

    def lineprofile(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)  # Clean up any existing modes or selectors
        # Activate line profile mode
        self.mode_control['lineprofile'] = True
        self.statusBar.showMessage("Drag the line to display line profile.")

        # Buttons for finish
        OK_icon = os.path.join(wkdir, 'icons/OK.png')
        self.buttons['ok'] = QAction(QIcon(OK_icon), 'Finish', parent=self)
        self.buttons['ok'].setStatusTip('Finish Line Profile')
        self.buttons['ok'].setShortcut('Esc')
        self.buttons['ok'].triggered.connect(self.stop_line_profile)
        self.toolbar.addAction(self.buttons['ok'])

        # Add a line selector
        x_range = self.img_size[-1] * self.scale
        y_range = self.img_size[-2] * self.scale
        start_point = 0.375 * x_range, 0.5 * y_range
        end_point = 0.625 * x_range, 0.5 * y_range
        selector = pg.LineROI(start_point, end_point, width=self.scale,
                                        pen=pg.mkPen('r', width=1),
                                        movable=True,
                                        rotatable=True,
                                        resizable=True
                                        )
        self.canvas.selector.append(selector)
        self._make_active_selector(selector)
        self.canvas.viewbox.addItem(selector)

        line_x, line_profile = self.extract_line_profile()
        x_label = f'Distance ({self.units})'
        y_label = 'Intensity (a.u.)'
        title = self.canvas.canvas_name + '_Line Profile'

        # Plot the line profile in a new window
        line_profile_window = PlotCanvasSpectrum(line_x, line_profile, parent=self)
        line_profile_window.create_plot(xlabel=x_label, ylabel=y_label, title=title)
        line_profile_window.canvas.canvas_name = title
        UI_TemCompanion.preview_dict[title] = line_profile_window
        UI_TemCompanion.preview_dict[title].setWindowTitle(title)
        line_profile_window.show()
        # Positioning
        self.position_window('center left')
        UI_TemCompanion.preview_dict[title].position_window('center right')

        # Connect signals for line change
        selector.sigRegionChanged.connect(self.update_line_profile)
        self.canvas.setFocus()  # Ensure the canvas has focus to receive key events

    def extract_line_profile(self):
        if self.canvas.selector and self.mode_control['lineprofile']:
            selector = self.canvas.selector[0]
            start_point_roi, end_point_roi = selector.getHandles()[0].pos(), selector.getHandles()[1].pos()
            start_point = selector.mapToParent(start_point_roi)
            end_point = selector.mapToParent(end_point_roi)
            width = int(selector.size().y() / self.scale)  # in pixels
            x0, y0 = int(start_point.x() / self.scale), int(start_point.y() / self.scale)
            x1, y1 = int(end_point.x() / self.scale), int(end_point.y() / self.scale)
            data = self.get_current_img_from_canvas()
            # Calculate the line profile using skimage.measure.profile_line
            line_profile = profile_line(data, (y0, x0), (y1, x1), linewidth=width, reduce_func=np.mean)
            line_x = np.linspace(0, len(line_profile)-1, len(line_profile)) * self.scale
            return line_x, line_profile


    def update_line_profile(self):
        if self.canvas.selector and self.mode_control['lineprofile']:
            title = self.canvas.canvas_name + '_Line Profile'
            line_x, line_profile = self.extract_line_profile()
            UI_TemCompanion.preview_dict[title].update_plot(line_x, line_profile)


    def stop_line_profile(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)


    def radial_integration(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)  # Clean up any existing modes or selectors
        self.mode_control['radial_integration'] = True
        self.statusBar.showMessage("Drag the circle to define center for radial integration.")
        # Perform radial integration on the current image
        self.radial_integration_dialog = RadialIntegrationDialog(parent=self)
        self.radial_integration_dialog.show()

        # Add a circle selector to indicate the center
        x_range = self.img_size[-1] * self.scale
        y_range = self.img_size[-2] * self.scale
        window_size = min(x_range, y_range) * 0.01
        x0 = x_range * 0.5 - window_size
        y0 = y_range * 0.5 - window_size
        selector = pg.CircleROI([x0, y0], radius=window_size,
                                    pen=pg.mkPen('y', width=2),
                                    movable=True,
                                    rotatable=False,
                                    resizable=False,
                                    maxBounds=QRectF(0, 0, x_range, y_range)
                                    )
        self.canvas.selector.append(selector)
        self._make_active_selector(selector)
        self.canvas.viewbox.addItem(selector)
        # Connect signals for circle change
        selector.sigRegionChangeFinished.connect(self.update_radial_integration_center)
        self.canvas.setFocus()  # Ensure the canvas has focus to receive key events

    def update_radial_integration_center(self):
        if self.canvas.selector and self.mode_control['radial_integration']:
            selector = self.canvas.selector[0]
            x, y = selector.pos().x(), selector.pos().y()
            radius = selector.size()[0] / 2
            center_x, center_y = x + radius, y + radius
            px_center_x, px_center_y = int(center_x / self.scale), int(center_y / self.scale)
            # Run CoM to get more accurate center
            image_data = self.canvas.current_img
            window_size = int(radius / self.scale)  # in pixels
            cx_pix, cy_pix = refine_center(image_data, (px_center_x, px_center_y), window_size)
            cx_pix = int(cx_pix)
            cy_pix = int(cy_pix)
            # Update radial integration dialog
            self.radial_integration_dialog.update_center((cx_pix, cy_pix))
            cx, cy = cx_pix * self.scale, cy_pix * self.scale
            x, y = cx - radius, cy - radius
            # Update selector position
            selector.sigRegionChangeFinished.disconnect(self.update_radial_integration_center)
            selector.setPos([x, y])
            selector.sigRegionChangeFinished.connect(self.update_radial_integration_center)


    def measure_fft(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)  # Clean up any existing modes or selectors
        # Activate measure mode
        self.mode_control['measure_fft'] = True
        self.statusBar.showMessage("Drag the circle over spots to measure. Define center as needed.")

        # Buttons for finish and center
        OK_icon = os.path.join(wkdir, 'icons/OK.png')
        self.buttons['ok'] = QAction(QIcon(OK_icon), 'Finish', parent=self)
        self.buttons['ok'].setStatusTip('Finish Measurement')
        self.buttons['ok'].setShortcut('Esc')
        self.buttons['ok'].triggered.connect(self.stop_fft_measurement)
        self.toolbar.addAction(self.buttons['ok'])
        center_icon = os.path.join(wkdir, 'icons/dp_center.png')
        self.buttons['define_center'] = QAction(QIcon(center_icon), 'Define Center', parent=self)
        self.buttons['define_center'].setStatusTip('Define the center of FFT')
        self.buttons['define_center'].triggered.connect(lambda: self.define_center_dp(method='center'))
        self.toolbar.addAction(self.buttons['define_center'])
        center2_icon = os.path.join(wkdir, 'icons/dp_center2.png')
        self.buttons['define_center2'] = QAction(QIcon(center2_icon), 'Define Center 2', parent=self)
        self.buttons['define_center2'].setStatusTip('Define the FFT center by two symmetric points')
        self.buttons['define_center2'].triggered.connect(lambda: self.define_center_dp(method='two-point'))
        self.toolbar.addAction(self.buttons['define_center2'])

        self.show_crosshair()


        # Add a circle selector for FFT measurement
        x_range = self.img_size[-1] * self.scale
        y_range = self.img_size[-2] * self.scale
        x0 = x_range * 0.625
        y0 = y_range * 0.375
        window_size = min(x_range, y_range) * 0.01
        selector = pg.CircleROI([x0, y0], radius=window_size,
                                    pen=pg.mkPen('y', width=3),
                                    movable=True,
                                    rotatable=False,
                                    resizable=False,
                                    maxBounds=QRectF(0, 0, x_range, y_range)
                                    )

        self.canvas.selector.append(selector)
        self._make_active_selector(selector)
        self.canvas.viewbox.addItem(selector)
        # Connect signals for circle change
        selector.sigRegionChangeFinished.connect(self.calculate_fft_distance)
        self.canvas.setFocus()  # Ensure the canvas has focus to receive key events
        
    def calculate_fft_distance(self):
        if self.canvas.selector and self.mode_control['measure_fft']:
            selector = self.canvas.selector[0]
            x, y = selector.pos().x(), selector.pos().y()
            center_x, center_y = self.canvas.center[0] * self.scale, self.canvas.center[1] * self.scale
            # Run CoM to get more accurate center
            image_data = self.canvas.current_img
            radius = selector.size()[0] / 2
            window_size = int(radius / self.scale)  # in pixels
            x0 = int((x + radius) / self.scale)
            y0 = int((y + radius) / self.scale)
            cx_pix, cy_pix = refine_center(image_data, (x0, y0), window_size)
            cx = cx_pix * self.scale
            cy = cy_pix * self.scale
            reciprocal_distance = ((cx - center_x) ** 2 + (cy - center_y) ** 2) ** 0.5
            if reciprocal_distance < 1e-6:
                reciprocal_distance = 1e-6  # Prevent division by zero
            x, y = cx - radius, cy - radius
            distance = 1 / reciprocal_distance
            angle = calculate_angle_to_horizontal((center_x, center_y), (cx, cy))
            self.statusBar.showMessage(f"FFT Measurement: {distance:.3f} {self.real_units}, {angle:.2f}°")

            # Update selector position
            selector.sigRegionChangeFinished.disconnect(self.calculate_fft_distance)
            selector.setPos([x, y])
            selector.sigRegionChangeFinished.connect(self.calculate_fft_distance)

    def stop_fft_measurement(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)
        self.canvas.plot.removeItem(self.crosshair[0])
        self.canvas.plot.removeItem(self.crosshair[1])
        self.crosshair = None

    def define_center_dp(self, method='center'):
        # method: 'center' or 'two-point'
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)  # Clean up any existing modes or selectors
        # Add buttons for confirm and cancel
        OK_icon = os.path.join(wkdir, 'icons/OK.png')
        self.buttons['ok'] = QAction(QIcon(OK_icon), 'Confirm', parent=self)
        self.buttons['ok'].setStatusTip('Confirm Center Definition')
        self.buttons['ok'].setShortcut('Return')
        self.buttons['ok'].triggered.connect(self.accept_define_center)
        self.toolbar.addAction(self.buttons['ok'])
        cancel_icon = os.path.join(wkdir, 'icons/cancel.png')
        self.buttons['cancel'] = QAction(QIcon(cancel_icon), 'Cancel', parent=self)
        self.buttons['cancel'].setStatusTip('Cancel Center Definition')
        self.buttons['cancel'].setShortcut('Esc')
        self.buttons['cancel'].triggered.connect(self.cancel_define_center)
        self.toolbar.addAction(self.buttons['cancel'])

        x_range = self.img_size[-1] * self.scale
        y_range = self.img_size[-2] * self.scale
        
        if method == 'center':
            self.statusBar.showMessage("Drag the circle over the center spot.")
            # Add a circle selector for center definition
            x0 = x_range * 0.5 
            y0 = y_range * 0.5 
            window_size = min(x_range, y_range) * 0.01
            selector = pg.CircleROI([x0 - window_size, y0 - window_size], radius=window_size,
                                    pen=pg.mkPen('r', width=3),
                                    movable=True,
                                    rotatable=False,
                                    resizable=False,
                                    maxBounds=QRectF(0, 0, x_range, y_range)
                                    )
            self.canvas.selector.append(selector)
            self.canvas.viewbox.addItem(selector)
            # Connect signals for circle change
            selector.sigRegionChangeFinished.connect(self.dp_center)
        elif method == 'two-point':
            self.statusBar.showMessage("Drag the circles over two symmetric spots.")
            # Add two circle selectors for two-point center definition
            x0_1 = x_range * 0.375 
            y0_1 = y_range * 0.5 
            x0_2 = x_range * 0.625 
            y0_2 = y_range * 0.5 
            window_size = min(x_range, y_range) * 0.01
            selector1 = pg.CircleROI([x0_1, y0_1], radius=window_size,
                                                pen=pg.mkPen('r', width=3),
                                                movable=True,
                                                rotatable=False,
                                                resizable=False,
                                                maxBounds=QRectF(0, 0, x_range, y_range)
                                                )
            selector2 = pg.CircleROI([x0_2, y0_2], radius=window_size,
                                                pen=pg.mkPen('r', width=3),
                                                movable=True,
                                                rotatable=False,
                                                resizable=False,
                                                maxBounds=QRectF(0, 0, x_range, y_range)
                                                )
            selector1.sigRegionChangeFinished.connect(self.dp_center)
            selector2.sigRegionChangeFinished.connect(self.dp_center)
            self.canvas.viewbox.addItem(selector1)
            self.canvas.viewbox.addItem(selector2)
            self.canvas.selector.append(selector1)
            self.canvas.selector.append(selector2)
            # Implement later

    def accept_define_center(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)
        if self.temp_center:
            if len(self.temp_center) == 1:
                # Define center with 1 spot
                self.canvas.center = self.temp_center[0]
            elif len(self.temp_center) == 2:
                # Define center with 2 spots
                self.canvas.center = ((self.temp_center[0][0] + self.temp_center[1][0]) / 2,
                                      (self.temp_center[0][1] + self.temp_center[1][1]) / 2)
            self.temp_center = []
            self.show_crosshair()
        self.measure_fft()

    def cancel_define_center(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)
        self.temp_center = []

    def dp_center(self):
        self.temp_center = []
        for selector in self.canvas.selector:
            x, y = selector.pos().x(), selector.pos().y()
            # Run CoM to get more accurate center
            image_data = self.canvas.current_img
            radius = selector.size()[0] / 2 
            window_size = int(radius / self.scale)  # in pixels
            x0 = int((x + radius) / self.scale)
            y0 = int((y + radius) / self.scale)
            cx_pix, cy_pix = refine_center(image_data, (x0, y0), window_size)
            cx, cy = cx_pix * self.scale, cy_pix * self.scale
            x, y = cx - radius, cy - radius

            # Update selector position
            selector.sigRegionChangeFinished.disconnect(self.dp_center)
            selector.setPos([x, y])
            selector.sigRegionChangeFinished.connect(self.dp_center)

            self.temp_center.append((cx_pix, cy_pix))




    def show_crosshair(self):
        cx_pix, cy_pix = self.canvas.center
        cx = cx_pix * self.scale 
        cy = cy_pix * self.scale 


        if self.crosshair is not None:
            self.canvas.plot.removeItem(self.crosshair[0])
            self.canvas.plot.removeItem(self.crosshair[1])
            self.crosshair = None

        line_length = self.img_size[-1] / 50 * self.scale  # 2% of the image width
        hLine = self.canvas.plot.plot([cx - line_length, cx + line_length], [cy, cy], pen=pg.mkPen('g', width=3))
        vLine = self.canvas.plot.plot([cx, cx], [cy - line_length, cy + line_length], pen=pg.mkPen('g', width=3))
        self.crosshair = (hLine, vLine)


         

    def clean_up(self, selector=False, buttons=False, modes=False, cid=False, status_bar=False):
        # Remove selectors and buttons if any
        if selector and self.canvas.selector:
            for sel in self.canvas.selector:
                self.canvas.viewbox.removeItem(sel)
            self.canvas.selector = []
            if self.canvas.active_selector is not None:
                self.canvas.active_selector = None

        if buttons:
            for button in self.buttons.keys():
                if self.buttons[button] is not None:
                    self.toolbar.removeAction(self.buttons[button])
                    self.buttons[button] = None

        # Turn off any active modes
        if modes:
            for mode in self.mode_control.values():
                if mode:
                    mode = False

        if cid:
            pass

        # Reset status bar
        if status_bar:
            self.statusBar.showMessage("Ready")

# ============== Geometric phase analysis functions ==============================
    def gpa(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)  # Clean up any existing modes or selectors
        self.live_fft(fullsize=True, windowed=True, resize_fft=True)
         # Resize the selector to be the whole image
        self.canvas.selector[0].setPos((0, 0))
        self.canvas.selector[0].setSize((self.img_size[-1] * self.scale, self.img_size[-2] * self.scale))
        preview_name = self.canvas.canvas_name + '_Live FFT'
        preview_fft = UI_TemCompanion.preview_dict[preview_name]
        fft_shape = preview_fft.canvas.data['data'].shape
        x_range = fft_shape[-1] * preview_fft.scale
        y_range = fft_shape[-2] * preview_fft.scale
        x0, y0 = x_range * 0.625, y_range * 0.5
       

        # Add two masks on the FFT
        # Some default values
        self.r = 10
        self.edgesmooth = 0.3
        self.stepsize = 4
        self.sigma = 10
        self.vmin = -0.1
        self.vmax = 0.1
        self.algorithm = 'standard'
        preview_fft = UI_TemCompanion.preview_dict[preview_name]

        preview_fft.add_mask(pairs=False)
        preview_fft.canvas.selector[0].setPos((x0, y0))       
        preview_fft.add_mask(pairs=False)

        preview_fft.statusBar.showMessage('Drag the masks on noncolinear strong spots.')

        # Buttons
        ok_icon = os.path.join(wkdir, 'icons/OK.png')
        preview_fft.buttons['ok'] = QAction(QIcon(ok_icon), 'Run GPA', parent=preview_fft)
        preview_fft.buttons['ok'].setStatusTip('Run GPA')
        preview_fft.toolbar.addAction(preview_fft.buttons['ok'])
        preview_fft.buttons['ok'].triggered.connect(self.run_gpa)
        cancel_icon = os.path.join(wkdir, 'icons/cancel.png')
        preview_fft.buttons['cancel'] = QAction(QIcon(cancel_icon), 'Close', parent=preview_fft)
        preview_fft.buttons['cancel'].setStatusTip('Close'),
        preview_fft.toolbar.addAction(preview_fft.buttons['cancel'])
        preview_fft.buttons['cancel'].triggered.connect(self.stop_gpa)
        settings_icon = os.path.join(wkdir, 'icons/settings.png')
        preview_fft.buttons['settings'] = QAction(QIcon(settings_icon), 'GPA Settings', parent=preview_fft)
        preview_fft.buttons['settings'].setStatusTip('GPA Settings')
        preview_fft.toolbar.addAction(preview_fft.buttons['settings'])
        preview_fft.buttons['settings'].triggered.connect(self.gpa_settings)
        add_icon = os.path.join(wkdir, 'icons/plus.png')
        preview_fft.buttons['add_mask'] = QAction(QIcon(add_icon), 'Add Mask', parent=preview_fft)
        preview_fft.buttons['add_mask'].setStatusTip('Add Mask')
        preview_fft.toolbar.addAction(preview_fft.buttons['add_mask'])
        preview_fft.buttons['add_mask'].triggered.connect(lambda: preview_fft.add_mask(pairs=False))
        remove_icon = os.path.join(wkdir, 'icons/minus.png')
        preview_fft.buttons['remove_mask'] = QAction(QIcon(remove_icon), 'Remove Mask', parent=preview_fft)
        preview_fft.buttons['remove_mask'].setStatusTip('Remove Mask')
        preview_fft.toolbar.addAction(preview_fft.buttons['remove_mask'])
        preview_fft.buttons['remove_mask'].triggered.connect(preview_fft.remove_mask)
        refine_icon = os.path.join(wkdir, 'icons/measure_fft.png')
        preview_fft.buttons['refine_center'] = QAction(QIcon(refine_icon), 'Refine Center', parent=preview_fft)
        preview_fft.buttons['refine_center'].setStatusTip('Refine the mask positions using CoM.')
        preview_fft.toolbar.addAction(preview_fft.buttons['refine_center'])
        preview_fft.buttons['refine_center'].triggered.connect(self.refine_mask)

        

    def stop_gpa(self):
        preview_name = self.canvas.canvas_name + "_Live FFT"
        UI_TemCompanion.preview_dict[preview_name].clean_up(selector=True, buttons=True, modes=True, status_bar=True)
        self.clean_up(selector=True, modes=True, status_bar=True)

    def run_gpa(self):
        img = self.get_img_dict_from_canvas()
        data = img['data']
        if data.shape[0] != data.shape[1]:
            data = filters.pad_to_square(data)
            # new_size = data.shape[0]
            # for ax in img['axes']:
            #     ax['size'] = new_size
        
        # Get the center and radius of the masks
        preview_name_fft = self.canvas.canvas_name + "_Live FFT"
        preivew_fft = UI_TemCompanion.preview_dict[preview_name_fft]
        scale = preivew_fft.scale
        g = []
        r_list = []
        for mask in preivew_fft.canvas.selector:
            x, y = mask.pos().x(), mask.pos().y()
            r = mask.size()[0] / 2
            cx, cy = x + r, y + r
            cx_pix, cy_pix = int(cx / scale), int(cy / scale)
            g.append((cx_pix, cy_pix))
            r_list.append(int(r / scale))
        if len(g) < 2:
            QMessageBox.warning(self, 'Run GPA', 'At least 2 g vectors are needed!')
            return

        r = max(r_list)

        print(f'Running GPA with g vectors: {g} and mask radius: {r} pixels.')
        
        title = self.canvas.canvas_name
        # Run GPA in a separate thread
        self.thread = QThread()
        self.worker = Worker(GPA, data, g, algorithm=self.algorithm, r=r, edge_blur=self.edgesmooth, sigma=self.sigma, window_size=r, step=self.stepsize)
        # exx, eyy, exy, oxy = GPA(data, g, algorithm=self.algorithm, r=r, edge_blur=self.edgesmooth, sigma=self.sigma, window_size=r, step=self.stepsize)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(lambda: self.toggle_progress_bar('ON'))
        self.thread.started.connect(lambda: print(f'Running GPA on {title} with {self.algorithm} GPA...'))
        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(lambda: self.toggle_progress_bar('OFF')) 
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(lambda: print(f'Finished running GPA on {title} with {self.algorithm} GPA.'))
        self.worker.result.connect(self.display_gpa_result)
        self.thread.start()

    def display_gpa_result(self, result):
        # Display the GPA result
        exx, eyy, exy, oxy = result
        im_y, im_x = self.img_size[-2], self.img_size[-1]
        exx = exx[:im_y, :im_x]
        eyy = eyy[:im_y, :im_x]
        exy = exy[:im_y, :im_x]
        oxy = oxy[:im_y, :im_x]
        img = self.get_img_dict_from_canvas()
        cm = custom_cmap['seismic']
        

        # Display the strain tensors
        exx_dict = copy.deepcopy(img)
        exx_dict['data'] = exx
        preview_name_exx = self.canvas.canvas_name + "_exx"
        self.plot_new_image(exx_dict, preview_name_exx)
        UI_TemCompanion.preview_dict[preview_name_exx].setWindowTitle('Epsilon xx')
        UI_TemCompanion.preview_dict[preview_name_exx].canvas.image_item.setLevels((self.vmin, self.vmax))
        UI_TemCompanion.preview_dict[preview_name_exx].canvas.attribute['vmin'] = self.vmin
        UI_TemCompanion.preview_dict[preview_name_exx].canvas.attribute['vmax'] = self.vmax
        UI_TemCompanion.preview_dict[preview_name_exx].canvas.image_item.setLookupTable(cm)
        UI_TemCompanion.preview_dict[preview_name_exx].canvas.attribute['cmap'] = 'seismic'
        UI_TemCompanion.preview_dict[preview_name_exx].canvas.toggle_colorbar(show=True)
        
        eyy_dict = copy.deepcopy(img)
        eyy_dict['data'] = eyy
        preview_name_eyy = self.canvas.canvas_name + "_eyy"
        self.plot_new_image(eyy_dict, preview_name_eyy)
        UI_TemCompanion.preview_dict[preview_name_eyy].setWindowTitle('Epsilon yy')
        UI_TemCompanion.preview_dict[preview_name_eyy].canvas.image_item.setLevels((self.vmin, self.vmax))
        UI_TemCompanion.preview_dict[preview_name_eyy].canvas.attribute['vmin'] = self.vmin
        UI_TemCompanion.preview_dict[preview_name_eyy].canvas.attribute['vmax'] = self.vmax
        UI_TemCompanion.preview_dict[preview_name_eyy].canvas.image_item.setLookupTable(cm)
        UI_TemCompanion.preview_dict[preview_name_eyy].canvas.attribute['cmap'] = 'seismic'
        UI_TemCompanion.preview_dict[preview_name_eyy].canvas.toggle_colorbar(show=True)
        
        exy_dict = copy.deepcopy(img)
        exy_dict['data'] = exy
        preview_name_exy = self.canvas.canvas_name + "_exy"
        self.plot_new_image(exy_dict, preview_name_exy)
        UI_TemCompanion.preview_dict[preview_name_exy].setWindowTitle('Epsilon xy')
        UI_TemCompanion.preview_dict[preview_name_exy].canvas.image_item.setLevels((self.vmin, self.vmax))
        UI_TemCompanion.preview_dict[preview_name_exy].canvas.attribute['vmin'] = self.vmin
        UI_TemCompanion.preview_dict[preview_name_exy].canvas.attribute['vmax'] = self.vmax
        UI_TemCompanion.preview_dict[preview_name_exy].canvas.image_item.setLookupTable(cm)
        UI_TemCompanion.preview_dict[preview_name_exy].canvas.attribute['cmap'] = 'seismic'
        UI_TemCompanion.preview_dict[preview_name_exy].canvas.toggle_colorbar(show=True)
        
        oxy_dict = copy.deepcopy(img)
        oxy_dict['data'] = oxy
        preview_name_oxy = self.canvas.canvas_name + "_oxy"
        self.plot_new_image(oxy_dict, preview_name_oxy)
        UI_TemCompanion.preview_dict[preview_name_oxy].setWindowTitle('Omega')
        UI_TemCompanion.preview_dict[preview_name_oxy].canvas.image_item.setLevels((self.vmin, self.vmax))
        UI_TemCompanion.preview_dict[preview_name_oxy].canvas.attribute['vmin'] = self.vmin
        UI_TemCompanion.preview_dict[preview_name_oxy].canvas.attribute['vmax'] = self.vmax
        UI_TemCompanion.preview_dict[preview_name_oxy].canvas.image_item.setLookupTable(cm)
        UI_TemCompanion.preview_dict[preview_name_oxy].canvas.attribute['cmap'] = 'seismic'
        UI_TemCompanion.preview_dict[preview_name_oxy].canvas.toggle_colorbar(show=True)
    
    def gpa_settings(self):
        # Open a dialog to take settings
        preview_name = self.canvas.canvas_name + '_Live FFT'
        r = max([mask.size()[0] / 2 for mask in UI_TemCompanion.preview_dict[preview_name].canvas.selector])
        r_pix = int(r / UI_TemCompanion.preview_dict[preview_name].scale)
        step = max(r*2//5, 2)
        dialog = gpaSettings(int(r_pix), self.edgesmooth, step, self.sigma, self.algorithm, vmin=self.vmin, vmax=self.vmax, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.r = dialog.masksize
            self.edgesmooth = dialog.edgesmooth
            self.stepsize = dialog.stepsize
            self.sigma = dialog.sigma
            self.vmin = dialog.vmin
            self.vmax = dialog.vmax
            self.algorithm = dialog.gpa
            
            
        # Update masks 
        for mask in UI_TemCompanion.preview_dict[preview_name].canvas.selector:
            mask.setSize(self.r * 2 * UI_TemCompanion.preview_dict[preview_name].scale)
        
                
    def refine_mask(self):
        preview_name = self.canvas.canvas_name + '_Live FFT'
        preview_fft = UI_TemCompanion.preview_dict[preview_name]
        img = preview_fft.get_current_img_from_canvas()
        #r = max([mask.radius for mask in UI_TemCompanion.preview_dict['GPA_FFT'].mask_list])
        for mask in preview_fft.canvas.selector:
            radius = mask.size()[0] / 2 
            x0 = (mask.pos().x() + radius) / preview_fft.scale
            y0 = (mask.pos().y() + radius) / preview_fft.scale
            g = x0, y0
            window_size = int(radius / preview_fft.scale)  # in pixels
            g_refined = refine_center(img, g, window_size)

            # Update mask position
            cx, cy = g_refined[0] * preview_fft.scale - radius, g_refined[1] * preview_fft.scale - radius
            mask.setPos([cx, cy])
            


# =============== Stack functions ============================================
    def rotate_stack(self):
        # Open a dialog to take the rotation angle
        dialog = RotateImageDialog(parent=self)
        # Display a message in the status bar
        if dialog.exec_() == QDialog.Accepted:
            ang = dialog.rotate_ang
            try:
                ang = float(ang)
            except ValueError:
                QMessageBox.critical(self, 'Input Error', 'Please enter a valid angle.')
                return
        
            # Process the rotation
            img = copy.deepcopy(self.canvas.data)
            img_to_rotate = img['data']
            rotated_array = rotate(img_to_rotate,ang,(2,1))
            img['data'] = rotated_array
            
            # Update axes
            img['axes'][1]['size'] = img['data'].shape[1]
            img['axes'][2]['size'] = img['data'].shape[2]
            
            # Create a new PlotCanvs to display        
            title = self.windowTitle()
            preview_name = self.canvas.canvas_name + '_R{}'.format(ang)

            self.plot_new_image(img, preview_name, parent=self.parent(), metadata=f'Rotated the entire stack of {title} by {ang} degrees counterclockwise.')
            
            print(f'Rotated the entire stack of {title} by {ang} degrees counterclockwise.')
            self.position_window('center left')
            UI_TemCompanion.preview_dict[preview_name].position_window('center right')


    def crop_stack(self):
        self.crop()
        self.buttons['ok'].triggered.disconnect(self.confirm_crop)
        self.buttons['ok'].triggered.connect(self.confirm_crop_stack)

    def confirm_crop_stack(self):
        self.confirm_crop(stack=True)
            
    def flip_stack_horizontal(self):
        img = copy.deepcopy(self.canvas.data)
        img_to_flip = img['data']
        flipped_array = img_to_flip[:,:,::-1]
        img['data'] = flipped_array
        
        # Create a new PlotCanvs to display        
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_Flipped_LR'
        metadata = f'Flipped the entire stack of {title} horizontally.'
        self.plot_new_image(img, preview_name, parent=self.parent(), metadata=metadata)
        
        print(f'Flipped the entire stack of {title} horizontally.')
        
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
    def flip_stack_vertical(self):
        img = copy.deepcopy(self.canvas.data)
        img_to_flip = img['data']
        flipped_array = img_to_flip[:,::-1,:]
        img['data'] = flipped_array
        
        # Create a new PlotCanvs to display        
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_Flipped_UD'
        metadata = f'Flipped the entire stack of {title} vertically.'
        # Create a new PlotCanvs to display 
        self.plot_new_image(img, preview_name, parent=self.parent(), metadata=metadata)
        
        print(f'Flipped the entire stack of {title} vertically.')
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')

    def resampling_stack(self):
        # Open a dialog to take the scale factor. Reuse the rotate angle dialog
        dialog = RotateImageDialog()
        dialog.setWindowTitle("Resampling stack")
        dialog.angle_input.setPlaceholderText('Enter rescaling factor')
        # Display a message in the status bar
        if dialog.exec_() == QDialog.Accepted:
            rescale_factor = dialog.rotate_ang
            try:
                rescale_factor = float(rescale_factor)
            except ValueError:
                QMessageBox.critical(self, 'Input Error', 'Please enter a valid rescale factor.')
                return
            
            
            img = copy.deepcopy(self.canvas.data)
            img_to_rebin = img['data']
            rebinned_array = rescale(img_to_rebin, (1,rescale_factor, rescale_factor))
            img['data'] = rebinned_array
            
            # Update axes
            new_scale = self.scale / rescale_factor
            _, new_y, new_x = rebinned_array.shape
            img['axes'][1]['scale'] = new_scale
            img['axes'][1]['size'] = new_y
            img['axes'][2]['scale'] = new_scale
            img['axes'][2]['size'] = new_x
            
            # Create a new PlotCanvs to display        
            title = self.windowTitle()
            preview_name = self.canvas.canvas_name + '_Resampled'
            metadata = f'Resampled the entire stack of {title} by a factor of {rescale_factor}.'
            self.plot_new_image(img, preview_name, parent=self.parent(), metadata=metadata)
            
            print(f'Resampled {title} by a factor of {rescale_factor}.')
            self.position_window('center left')
            UI_TemCompanion.preview_dict[preview_name].position_window('center right')

    def reslice_stack(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)  # Clean up any existing modes or selectors
        self.statusBar.showMessage("Drag the line to reslice.")
        
        # Buttons for finish
        OK_icon = os.path.join(wkdir, 'icons/OK.png')
        self.buttons['ok'] = QAction(QIcon(OK_icon), 'OK', parent=self)
        self.buttons['ok'].setStatusTip('Reslice from the line')
        self.buttons['ok'].setShortcut('Esc')
        self.buttons['ok'].triggered.connect(self.reslice_from_line)
        self.toolbar.addAction(self.buttons['ok'])

        cancel_icon = os.path.join(wkdir, 'icons/cancel.png')
        self.buttons['cancel'] = QAction(QIcon(cancel_icon), 'Cancel', parent=self)
        self.buttons['cancel'].setStatusTip('Cancel Reslice')
        self.buttons['cancel'].setShortcut('Esc')
        self.buttons['cancel'].triggered.connect(self.cancel_crop)
        self.toolbar.addAction(self.buttons['cancel'])

        # Add a line selector
        x_range = self.img_size[-1] * self.scale
        y_range = self.img_size[-2] * self.scale
        start_point = 0.375 * x_range, 0.5 * y_range
        end_point = 0.625 * x_range, 0.5 * y_range

        selector = pg.LineSegmentROI([start_point, end_point],
                                        pen=pg.mkPen('y', width=3),
                                        movable=True,
                                        rotatable=True,
                                        resizable=True
                                        )
        self.canvas.selector.append(selector)
        self._make_active_selector(selector)
        self.canvas.viewbox.addItem(selector)

    def cancel_reslice(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)

    def reslice_from_line(self):
        if self.canvas.selector:
            selector = self.canvas.selector[0]
            start_point, end_point = selector.getHandles()[0].pos(), selector.getHandles()[1].pos()

            p1 = (start_point.x() / self.scale, start_point.y() / self.scale)
            p2 = (end_point.x() / self.scale, end_point.y() / self.scale)
            
            img = self.get_original_img_dict()
            resliced = []
            for frame in img['data']:
                line = profile_line(frame,(p1[1],p1[0]), (p2[1],p2[0]), linewidth=1)
                resliced.append(line)
            
            resliced_array = np.array(resliced)
            # update image and axes
            img['data'] = resliced_array
            resliced_size = resliced_array.shape
            axes = img['axes']
            
            # z axis will be the new y
            axes[0]['size'] = resliced_size[0]
            axes[0]['navigate'] = False
            axes[1]['size'] = resliced_size[1]
                        
            # plot   
            title = self.canvas.canvas_name         
            preview_name = self.canvas.canvas_name + f'_Resliced from {p1}, {p2}'
            metadata = f'Resliced {title} from {p1} to {p2}.'
            self.plot_new_image(img, preview_name, parent=self.parent(), metadata=metadata)
            self.position_window('center left')
            UI_TemCompanion.preview_dict[preview_name].position_window('center right')

            # Clean up
            self.clean_up(buttons=True, selector=True, status_bar=True)


    def sort_stack(self):
        sorted_img = copy.deepcopy(self.canvas.data)
        img = sorted_img['data']
        img_n, img_y, img_x = img.shape
        stack = [f'Frame {n:03d}' for n in range(img_n)]
        dialog = ListReorderDialog(stack)
        if dialog.exec_() == QDialog.Accepted:
            sorted_order = dialog.ordered_items_idx
            img_n = len(sorted_order)
            sorted_data = np.zeros((img_n, img_y, img_x))
            for i in range(img_n):
                sorted_data[i] = img[sorted_order[i]]
            sorted_img['data'] = sorted_data
            sorted_img['axes'][0]['size'] = img_n    
        else:
            return
        
        # Create a new PlotCanvs to display        
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_sorted'
        metadata = f'Sorted the entire stack of {title} by the order of {sorted_order}.'
        self.plot_new_image(sorted_img, preview_name, parent=self.parent(), metadata=metadata)

        print(f'{title} has been sorted.')
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
    def align_stack_cc(self):                
        # Open a dialog to take parameters
        dialog = AlignStackDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            apply_window = dialog.apply_window
            crop_img = dialog.crop_img
            crop_to_square = dialog.crop_to_square
            img = self.get_original_img_dict()

            preview_name = self.canvas.canvas_name + '_aligned by cc'
            metadata = 'Aligned by Phase Cross-Correlation'

            self.position_window('center left')

            # Run alignment in a separate thread
            self.thread = QThread()
            self.worker = Worker(self.run_alignment_cc, img, apply_window, crop_img, crop_to_square)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(lambda: self.toggle_progress_bar('ON'))
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(lambda: self.toggle_progress_bar('OFF'))
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata))
            self.worker.result.connect(lambda: UI_TemCompanion.preview_dict[preview_name].position_window('center right'))
            self.thread.start()

           

    def run_alignment_cc(self, img_dict, apply_window=True, crop_img=True, crop_to_square=False):
        aligned_img = copy.deepcopy(img_dict)
        img = img_dict['data']

        # Perform phase cross-correlation alignment on an image stack
        # img: 3D numpy array (n, x, y)
        img_n, img_x, img_y = img.shape
        drift_stack = []
        
        
        # Calculate the drift with sub pixel precision
        upsampling = 100
        print('Stack alignment using phase cross-correlation.')
        for n in range(img_n -1):            
            fixed = img[n]
            moving = img[n+1]
            # Apply a Hann window to suppress periodic features
            if apply_window:
                w = window('hann', fixed.shape)
                fixed = fixed * w
                moving = moving * w

            
            drift, _, _ = phase_cross_correlation(fixed, moving, upsample_factor = upsampling, normalization=None)
            drift_stack.append(drift)
        # Shift the images to align the stack
        drift = np.array([0,0])
        drift_all = []
        for n in range(img_n-1):
            drift = drift + drift_stack[n]
            img_to_shift = img[n+1]
            
            img[n+1,:,:] = shift(img_to_shift,drift)
            print(f'Shifted slice {n+1} by {drift}')
            drift_all.append(drift)
            
        if crop_img:
            # Crop the stack to the biggest common region
            drift_x = [i[0] for i in drift_all]
            drift_y = [i[1] for i in drift_all]
            drift_x_min, drift_x_max = min(drift_x), max(drift_x)
            drift_y_min, drift_y_max = min(drift_y), max(drift_y)
            x_min = max(int(drift_x_max) + 1, 0)
            x_max = min(img_x, int(img_x + drift_x_min) - 1)
            y_min = max(int(drift_y_max) + 1,0)
            y_max = min(img_y, int(img_y + drift_y_min) - 1)
            
            img_crop = img[:,x_min:x_max,y_min:y_max]
            print(f'Cropped images to {y_min}:{y_max}, {x_min}:{x_max}.')
            
            if crop_to_square:
                x, y = img_crop[0].shape
                if x > y:
                    new_start = int((x - y) / 2)
                    new_end = new_start + y 
                    img_crop = img_crop[:,new_start:new_end,:]
                else:
                    new_start = int((y - x) / 2)
                    new_end = new_start + x 
                    img_crop = img_crop[:,:,new_start:new_end]
                print(f'Further cropped to square from {new_start}:{new_end}.')
                
            aligned_img['data'] = img_crop
            aligned_img['data'] = aligned_img['data']
            # Update axes size
            aligned_img['axes'][0]['size'] = aligned_img['data'].shape[1]
            aligned_img['axes'][1]['size'] = aligned_img['data'].shape[2]
        print('Stack alignment finished!')
        return aligned_img

    def align_stack_of(self):
        print('Stack alignment using Optical Flow iLK.')
        preview_name = self.canvas.canvas_name + '_aligned by OF'
        metadata = 'Aligned by Optical Flow iLK.'
        self.position_window('center left')
        img = self.get_original_img_dict()
        # Run alignment in a separate thread
        self.thread = QThread()
        self.worker = Worker(self.run_alignment_of, img)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(lambda: self.toggle_progress_bar('ON'))
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(lambda: self.toggle_progress_bar('OFF'))
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata))
        self.worker.result.connect(lambda: UI_TemCompanion.preview_dict[preview_name].position_window('center right'))
        self.thread.start()

            
    def run_alignment_of(self, img_dict):
        aligned_img = copy.deepcopy(img_dict)
        img = aligned_img['data']
        # Normalize
        for f in range(img.shape[0]):
            img[f] = norm_img(img[f])
            
        
        img_n, nr, nc = img.shape
        drift_stack = []
        for n in range(img_n -1):            
            fixed = img[n]
            moving = img[n+1]
            
            print(f'Calculate the drift of slice {n+1} using Optical Flow iLK...')
            
            u, v = optical_flow_ilk(fixed, moving)
            drift_stack.append((u, v))
        
        # Apply the correction
        print('Applying drift correction...')
        row_coords, col_coords = np.meshgrid(np.arange(nr), np.arange(nc), indexing='ij')
        drift = np.array([np.zeros((nr,nc)),np.zeros((nr,nc))])
        for n in range(img_n-1):
            drift = drift + np.array(drift_stack[n])
            vector_field = np.array([row_coords + drift[0], col_coords + drift[1]])
            img_to_shift = img[n+1]
            
            img[n+1,:,:] = warp(img_to_shift, vector_field, mode='constant') 
        
            aligned_img['data'] = img
        print('Stack alignment finished!')
        return aligned_img

    def integrate_stack(self):
        data = np.mean(self.canvas.data['data'], axis=0)
        integrated_img = {'data': data, 'axes': self.canvas.data['axes'], 'metadata': self.canvas.data['metadata'],
                          'original_metadata': self.canvas.data['original_metadata']}
        # Create a new PlotCanvs to display     
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_integrated'
        metadata = f'Stack of {title} has been integrated by averaging all frames.'
        self.plot_new_image(integrated_img, preview_name, parent=self.parent(), metadata=metadata)
        
        print(f'Stack of {title} has been integrated.')
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
    def export_stack(self):
        data = self.get_original_img_dict()
        img_data = data['data']
        
        data_to_export = {'data': img_data, 'metadata': data['metadata'], 'axes': data['axes']}
        options = QFileDialog.Options()
        file_path, selection = QFileDialog.getSaveFileName(self.parent(), 
                                                   "Save as tiff stack", 
                                                   "", 
                                                   "TIFF Files (*.tiff)", 
                                                   options=options)
        if file_path:
            tif_writer(file_path, data_to_export) 
            
            print(f'{file_path} has been exported.')
            
    
    def export_stack_gif(self):
        data = self.get_original_img_dict()
        img_data = data['data']
        # Normalize data
        for f in range(img_data.shape[0]):
            img_data[f] = norm_img(img_data[f]) * 255
        
        data_to_export = {'data': img_data, 'metadata': data['metadata'], 'axes': data['axes']}
        options = QFileDialog.Options()
        file_path, selection = QFileDialog.getSaveFileName(self.parent(), 
                                                   "Save as GIF animation", 
                                                   "", 
                                                   "GIF Files (*.gif)", 
                                                   options=options)
        if file_path:
            im_writer(file_path, data_to_export, duration=500, loop=0) 
            
            print(f'{file_path} has been exported.')

        
    
    def export_series(self):
        data = self.get_img_dict_from_canvas()
        # Image data is the 3D data array
        data['data'] = self.canvas.data['data']
        # Open a file dialog to choose the file path and format
        options = QFileDialog.Options()
        file_path, selected_type = QFileDialog.getSaveFileName(self.parent(), 
                                                   "Save Figure", 
                                                   "", 
                                                   "16-bit TIFF Files (*.tiff);;32-bit TIFF Files (*.tiff);;8-bit TIFF Files (*.tiff);;Grayscale PNG Files (*.png);;Grayscale JPEG Files (*.jpg);;Color TIFF Files (*.tiff);;Color PNG Files (*.png);;Color JPEG Files (*.jpg)", 
                                                   options=options)
        if file_path:
            # Implement custom save logic here
           
            # Extract the chosen file format            
            file_type = getFileType(file_path)
            f_name = getFileName(file_path)
            output_dir = getDirectory(file_path,s='/')
            #output_dir = output_dir + f_name + '/'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            img_to_save = {}
            for key in ['data', 'axes', 'metadata']:
                if key in data.keys():
                    img_to_save[key] = data[key]
                else:
                    print('Invalid image data')
                    return
                
            if selected_type == "16-bit TIFF Files (*.tiff)":
                for i in range(img_to_save['data'].shape[0]):
                    img = {'data': img_to_save['data'][i], 'axes': img_to_save['axes'], 'metadata': img_to_save['metadata']}
                    save_as_tif16(img, f_name + f'_{i:03d}', output_dir, dtype='int16')
                    print(f'Exported to {output_dir}/{f_name}_{i:03d}.')
                    
            elif selected_type == "32-bit TIFF Files (*.tiff)":
                for i in range(img_to_save['data'].shape[0]):
                    img = {'data': img_to_save['data'][i], 'axes': img_to_save['axes'], 'metadata': img_to_save['metadata']}
                    save_as_tif16(img, f_name + f'_{i:03d}', output_dir, dtype='float32')
                    print(f'Exported to {output_dir}/{f_name}_{i:03d}.')
                    
            elif selected_type in ['8-bit TIFF Files (*.tiff)', 'Grayscale PNG Files (*.png)', 'Grayscale JPEG Files (*.jpg)']:
                for i in range(img_to_save['data'].shape[0]):
                    img = {'data': img_to_save['data'][i], 'axes': img_to_save['axes'], 'metadata': img_to_save['metadata']}
                    save_with_pil(img, f_name + f'_{i:03d}', output_dir, file_type, scalebar=self.scalebar_settings['scalebar']) 
                    print(f'Exported to {output_dir}/{f_name}_{i:03d}.')
                    
            else: # Save with pyqtgraph for color images
                for i in range(img_to_save['data'].shape[0]):
                    self.canvas.slider.setValue(i)
                    exporter = pg.exporters.ImageExporter(self.canvas.viewbox)
                    exporter.parameters()['width'] = self.img_size[1]  # Set export width to original image width
                    # exporter.parameters()['height'] = self.img_size[0]  # Set export height to original image height
                    exporter.export(output_dir + f_name + f'_{i:03d}' +'.' + file_type)
                    print(f'Exported to {output_dir}/{f_name}_{i:03d}.')
        


#========== PlotCanvas for FFT ================================================
class PlotCanvasFFT(PlotCanvas):
    def __init__(self, img, parent=None):
        # img is the image dictionary, NOT FFT. FFT will be calculated in create_img()
        super().__init__(img, parent)

        fft_menu = self.menubar.children()[3]
        mask_action = QAction('Mask and iFFT', self)
        mask_action.triggered.connect(self.mask)
        fft_menu.addAction(mask_action)
        
        # Remove GPA
        analyze_menu = self.menubar.children()[4]
        actions = analyze_menu.actions()
        for action in actions:
            if action.iconText() == 'Geometric Phase Analysis':
                gpa_action = action
                analyze_menu.removeAction(gpa_action)
                break
        
        
        
        
        
        # Remove the filter menu
        filter_menu = self.menubar.children()[5]
        self.menubar.removeAction(filter_menu.menuAction())

        # Remove some toolbar buttons
        toolbar = self.toolbar
        for action in toolbar.actions():
            if action.iconText() in ['FFT', 'Live FFT', 'Wiener Filter', 'ABS Filter', 'Gaussian Filter', 'Non-linear Filter']:
                toolbar.removeAction(action)    

        # Add mask button
        mask_icon = os.path.join(wkdir, 'icons/masks.png')
        mask_action = QAction(QIcon(mask_icon), 'Mask and iFFT', self)
        mask_action.setStatusTip('Add masks to FFT spots and perform inverse FFT.')
        mask_action.triggered.connect(self.mask)
        self.toolbar.insertAction(toolbar.actions()[11], mask_action)

        # Store the original image scale in real space
        self.real_scale = self.scale
        
        self.calculate_fft()
        self.set_scalebar_units()
        self.canvas.attribute['cmap'] = 'inferno'

        self.canvas.create_img(cmap=self.canvas.attribute['cmap'], pvmin=30, pvmax=99.9)

    def closeEvent(self, event):       
        if self.parent().mode_control['Live_FFT']:
            self.parent().stop_live_fft()
        UI_TemCompanion.preview_dict.pop(self.canvas.canvas_name, None)

    def calculate_fft(self):
        img_dict = self.canvas.data  
        data = img_dict['data']
    
        max_dim = max(data.shape)
        fft_shape = (max_dim, max_dim)
        
        fft_data = fftshift(fft2(data, s=fft_shape))
        fft_mag = np.abs(fft_data)
        
        # Update image data to fft
        self.canvas.current_img = fft_mag
        self.canvas.data['fft'] = fft_data
        self.canvas.data['data'] = fft_mag
        self.canvas.data['axes'][0]['size'] = fft_shape[0]
        self.canvas.data['axes'][1]['size'] = fft_shape[1]
        
        self.set_fft_scale_units()


    def set_fft_scale_units(self):
        img_dict = self.canvas.data 
        self.real_scale = img_dict['axes'][1]['scale']
        # Update image size
        fft_size = img_dict['data'].shape
        fft_scale = 1 / self.real_scale / fft_size[0]
        self.real_units = img_dict['axes'][0]['units']
        
            
        if self.real_units in ['um', 'µm', 'nm', 'm', 'mm', 'cm', 'pm']:
            fft_units = f'1/{self.real_units}'
        elif self.real_units in ['1/m', '1/cm', '1/mm', '1/um', '1/µm', '1/nm', '1/pm']:
            fft_units = self.real_units.split('/')[-1]
        else: # Cannot parse the unit correctly, reset to pixel scale
            fft_units = 'px'
            fft_scale = 1
            
        
        
        # Update the data associated with this canvas object
        self.units = fft_units 
        self.scale = fft_scale
        self.canvas.scale = fft_scale
        
        # Update image dictionary
        img_dict['axes'][0]['size'] = fft_size[0]
        img_dict['axes'][1]['size'] = fft_size[1]
        img_dict['axes'][0]['scale'] = fft_scale
        img_dict['axes'][1]['scale'] = fft_scale
        img_dict['axes'][0]['units'] = fft_units
        img_dict['axes'][1]['units'] = fft_units

        fft_center = (self.img_size[0]//2, self.img_size[1]//2)
        self.canvas.data['axes'][0]['offset'] = -fft_center[0] * self.scale
        self.canvas.data['axes'][1]['offset'] = -fft_center[1] * self.scale


    def update_fft_with_img(self, img, resize_fft=False):
        self.canvas.data = img
        self.calculate_fft()
        self.set_scalebar_units()
        if resize_fft:
            # Resize the FFT to be the original FFT size
            img_size = self.img_size
            fft_resize = max(img_size)
            resized_fft = resize(self.canvas.data['data'], (fft_resize, fft_resize))
            self.canvas.data['data'] = resized_fft

            # Update size and scale
            self.canvas.data['axes'][0]['size'] = fft_resize
            self.canvas.data['axes'][1]['size'] = fft_resize
            if self.units != 'px':
                fft_scale = 1 / self.real_scale / fft_resize
            else:
                fft_scale = 1
            self.canvas.data['axes'][0]['scale'] = fft_scale
            self.canvas.data['axes'][1]['scale'] = fft_scale
        else:
            img_size = None

        new_img = self.canvas.data
        
        self.update_img(new_img, img_size=img_size, pvmin=30, pvmax=99.9)

    def mask(self):
        # Add symmetric circular mask to the FFT and perform inverse FFT
        self.clean_up(buttons=True, selector=True, modes=True, status_bar=True)
        self.mode_control['mask'] = True
         # Display a message in the status bar
        self.statusBar.showMessage("Drag masks on FFT spots. Add more if needed.")

        # Add buttons
        ok_icon = os.path.join(wkdir, 'icons/ok.png')
        self.buttons['ok'] = QAction(QIcon(ok_icon), 'Finish', self)
        self.buttons['ok'].setShortcut('Esc')
        self.buttons['ok'].setStatusTip('Finish iFFT filtering.')
        self.buttons['ok'].triggered.connect(self.stop_mask_ifft)
        self.toolbar.addAction(self.buttons['ok'])

        add_icon = os.path.join(wkdir, 'icons/plus.png')
        self.buttons['add'] = QAction(QIcon(add_icon), 'Add Mask', self)
        self.buttons['add'].setStatusTip('Add new masks.')
        self.buttons['add'].triggered.connect(lambda: self.add_mask())
        self.toolbar.addAction(self.buttons['add'])   

        remove_icon = os.path.join(wkdir, 'icons/minus.png')
        self.buttons['remove'] = QAction(QIcon(remove_icon), 'Remove Mask', self)
        self.buttons['remove'].setStatusTip('Remove masks.')
        self.buttons['remove'].triggered.connect(self.remove_mask)
        self.toolbar.addAction(self.buttons['remove'])

        self.add_mask()

        # Create a new plot to show live ifft
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_iFFT'
        live_ifft = self.get_img_dict_from_canvas()
        live_ifft_data = self.ifft_with_masks(live_ifft['data'], self.img_size)
        live_ifft['data'] = live_ifft_data

        # Update scale and units
        # Calculate scale and update
        if self.units != 'px':
            img_scale = 1 / self.scale / live_ifft['data'].shape[0]
            img_units = self.real_units
            
        else:
            img_scale = 1
            img_units = 'px'
        
        for axes in live_ifft['axes']:
            axes['units'] = img_units
            axes['scale'] = img_scale
            axes['offset'] = 0


        metadata = f'iFFT with masks from {title}'
        self.plot_new_image(live_ifft, preview_name, parent=self, metadata=metadata)
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')

    def add_mask(self, pairs=True):
        # Add circular mask with an option to add symmetric pairs
        x_range = self.canvas.data['data'].shape[-1] * self.scale
        y_range = self.canvas.data['data'].shape[-2] * self.scale
        x0 = 0.375 * x_range
        y0 = 0.5 * y_range
        radius = 0.01 * min(x_range, y_range)

        mask0 = pg.CircleROI([x0, y0], radius=radius, pen=pg.mkPen('r', width=3), 
                                movable=True, 
                                rotatable=False, 
                                resizable=True,
                                maxBounds=pg.QtCore.QRectF(0,0,x_range,y_range)
                                )
        mask0_id = id(mask0)
        mask0.id = mask0_id

        self.canvas.selector.append(mask0)
        self.canvas.viewbox.addItem(mask0)
        mask0.sigHoverEvent.connect(self._make_active_selector)
        

        if pairs:
            x1, y1 = x_range - x0, y_range - y0
            mask1 = pg.CircleROI([x1, y1], radius=radius, pen=pg.mkPen('r', width=2), 
                                    movable=True, 
                                    rotatable=False, 
                                    resizable=True,
                                    maxBounds=pg.QtCore.QRectF(0,0,x_range,y_range)
                                    )
            
            # Link mask1 to mask0
            mask1.id = mask0_id

            self.canvas.selector.append(mask1)
            self.canvas.viewbox.addItem(mask1)
            mask1.sigHoverEvent.connect(self._make_active_selector)  

            # Connect the signals for synchronized movement and live ifft update
            mask0.sigRegionChanged.connect(self.update_mask_ifft)       
            mask1.sigRegionChanged.connect(self.update_mask_ifft)

            


    def update_mask_ifft(self, mask):
        mask_id = mask.id
        # Find the paired mask
        paired_mask = None
        for m in self.canvas.selector:
            if m.id == mask_id and m is not mask:
                paired_mask = m
                break
        if paired_mask is None:
            return  
        # Update the paired mask position and size
        x0, y0 = mask.pos().x(), mask.pos().y()
        d0 = mask.size()[0]
        x_range = self.canvas.data['data'].shape[-1] * self.scale
        y_range = self.canvas.data['data'].shape[-2] * self.scale
        x1 = x_range - x0 - d0
        y1 = y_range - y0 - d0
        paired_mask.sigRegionChanged.disconnect(self.update_mask_ifft)
        paired_mask.setPos([x1, y1], update=False, finish=False)
        paired_mask.setSize(d0)
        paired_mask.sigRegionChanged.connect(self.update_mask_ifft)

        # Update the live ifft image
        live_ifft_name = self.canvas.canvas_name + '_iFFT'
        live_ifft_data = self.ifft_with_masks(self.canvas.data['fft'], self.img_size)
        if live_ifft_name in UI_TemCompanion.preview_dict:
            live_ifft_canvas = UI_TemCompanion.preview_dict[live_ifft_name]
            live_ifft_canvas.canvas.update_img(live_ifft_data, pvmin=0.1, pvmax=99.9)


    def remove_mask(self):
        if self.canvas.active_selector is not None:
            mask_id = self.canvas.active_selector.id
            masks_to_remove = []
            for m in self.canvas.selector:
                if m.id == mask_id:
                    masks_to_remove.append(m)
            for m in masks_to_remove:
                self.canvas.viewbox.removeItem(m)
                self.canvas.selector.remove(m)
            self.canvas.active_selector = None

    def ifft_with_masks(self, fft_data, img_size):
        # Get the centers and radii of all masks
        center = []
        radius = []
        for m in self.canvas.selector:
            m_center = (m.pos().x() + m.size()[0]/2)/self.scale, (m.pos().y() + m.size()[1]/2)/self.scale
            m_radius = m.size()[0]/2/self.scale
            if m_radius < 1:
                m_radius = 1 # Smallest mask radius is 1 pixel
            center.append(m_center)
            radius.append(m_radius)
        mask = create_mask(fft_data.shape, center, radius)              
        masked_fft = fft_data * mask
        filtered_img_padded = ifft2(ifftshift(masked_fft)).real
        filtered_img = filtered_img_padded[:self.img_size[0], :self.img_size[1]]
        return filtered_img
        

    def stop_mask_ifft(self):
        self.clean_up(buttons=True, selector=True, modes=True, status_bar=True)

                    
        

#========= General spectrum plot canvas ======================================
class PlotCanvasSpectrum(QMainWindow):
    def __init__(self, x, y, parent=None):
        # data is a 2D array with x and y values, x in the first row, y in the second row
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.resize(600, 400)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.x = x
        self.y = y
        self.title = None
        self.xlabel = None
        self.ylabel = None
        self.canvas = QWidget()
        self.plot = pg.PlotWidget(parent=self.canvas)
        self.plot.setBackground('black')
        self.plot.getPlotItem().hideButtons()
        self.plot.getPlotItem().setContentsMargins(0,0,0,0)
        layout = QVBoxLayout()
        layout.addWidget(self.plot)
        self.canvas.setLayout(layout)
        self.setCentralWidget(self.canvas)

        self.selector = None
        self.buttons = {'ok': None, 
                        'cancel': None}

        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Pixel label on the status bar
        self.data_label = QLabel("x = ---, y = ---")

        self.statusBar.addPermanentWidget(self.data_label)

        # # Connect mouse event
        self.plot.scene().sigMouseMoved.connect(self.on_mouse_move)
        self.plot.scene().sigMouseHover.connect(self.on_mouse_hover)

        self.create_plot()
        self.create_menubar()
        self.create_toolbar()
        self.custom_auto_range()

    def exitEvent(self, event):
        UI_TemCompanion.preview_dict.pop(self.canvas.canvas_name, None)

    def create_menubar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu('&File')
        save_action = QAction('&Save as', self)
        save_action.setShortcut('ctrl+s')
        save_action.triggered.connect(self.save_plot)
        file_menu.addAction(save_action)
        copy_action = QAction('&Copy Plot to Clipboard', self)
        copy_action.setShortcut('ctrl+alt+c')
        copy_action.triggered.connect(self.copy_plot)
        file_menu.addAction(copy_action)
        plotsettings_action = QAction('Plot Settings', self)
        plotsettings_action.triggered.connect(self.plotsetting)
        file_menu.addAction(plotsettings_action)
        close_action = QAction('&Close', self)
        close_action.setShortcut('ctrl+x')
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)
        close_all_action = QAction('&Close All', self)
        close_all_action.setShortcut('ctrl+shift+x')
        close_all_action.triggered.connect(self.close_all)
        file_menu.addAction(close_all_action)
        
        measure_menu = menubar.addMenu('Measure')

        measure_horizontal = QAction('Measure horizontal', self)   
        measure_horizontal.triggered.connect(lambda: self.measure('vertical'))
        measure_menu.addAction(measure_horizontal)

        measure_vertical = QAction('Measure vertical', self)      
        measure_vertical.triggered.connect(lambda: self.measure('horizontal'))
        measure_menu.addAction(measure_vertical)
        
        
        self.menubar = menubar

    def create_toolbar(self):
        self.toolbar = QToolBar("Toolbar", self)
        self.toolbar.setIconSize(QtCore.QSize(16,16))
        self.addToolBar(self.toolbar)

        home_icon = os.path.join(wkdir, 'icons/home.png')
        home_action = QAction(QIcon(home_icon), "Home", self)
        home_action.setStatusTip("Reset to original view")
        home_action.triggered.connect(self.custom_auto_range)
        self.toolbar.addAction(home_action)

        save_icon = os.path.join(wkdir, 'icons/save.png')
        save_action = QAction(QIcon(save_icon), "Save", self)
        save_action.setStatusTip("Save plot as image or CSV")
        save_action.triggered.connect(self.save_plot)
        self.toolbar.addAction(save_action)

        copy_icon = os.path.join(wkdir, 'icons/copy.png')
        copy_action = QAction(QIcon(copy_icon), "Copy", self)
        copy_action.setStatusTip("Copy plot to clipboard")
        copy_action.triggered.connect(self.copy_plot)
        self.toolbar.addAction(copy_action)

        settings_icon = os.path.join(wkdir, 'icons/settings.png')
        settings_action = QAction(QIcon(settings_icon), "Settings", self)
        settings_action.setStatusTip("Plot settings")
        settings_action.triggered.connect(self.plotsetting)
        self.toolbar.addAction(settings_action)

        self.toolbar.addSeparator()

        h_measure_icon = os.path.join(wkdir, 'icons/h_measure.png')
        h_measure_action = QAction(QIcon(h_measure_icon), "Measure horizontal", self)
        h_measure_action.triggered.connect(lambda: self.measure('vertical'))
        self.toolbar.addAction(h_measure_action)

        v_measure_icon = os.path.join(wkdir, 'icons/v_measure.png')
        v_measure_action = QAction(QIcon(v_measure_icon), "Measure vertical", self)
        v_measure_action.triggered.connect(lambda: self.measure('horizontal'))
        self.toolbar.addAction(v_measure_action)

    def create_plot(self, title=None, xlabel=None, ylabel=None):
        self.plot_data_item = self.plot.plot(self.x, self.y, pen=pg.mkPen('blue', width=2))
        plot_item = self.plot.getPlotItem()
        ax_color = pg.mkColor('gray')
        x_axis = plot_item.getAxis('bottom')
        y_axis = plot_item.getAxis('left')
        x_axis.setPen(ax_color)
        x_axis.setTextPen(ax_color)
        y_axis.setPen(ax_color)
        y_axis.setTextPen(ax_color)

        if title is not None:
            self.title = title
            self.plot.setTitle(title)
        if xlabel is not None:
            self.xlabel = xlabel
            self.plot.setLabel('bottom', xlabel)
        if ylabel is not None:
            self.ylabel = ylabel
            self.plot.setLabel('left', ylabel)

    def update_plot(self, x, y):
        self.x = x
        self.y = y
        self.plot.clear()
        self.create_plot()

    def closeEvent(self, event):
        if self.parent().mode_control['lineprofile']:
            self.parent().stop_line_profile()
        UI_TemCompanion.preview_dict.pop(self.canvas.canvas_name, None)

    def on_mouse_move(self, pos):
        if self.plot:
            mouse_point = self.plot.plotItem.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()

            self.data_label.setText(f"x = {x:.2f}, y = {y:.2f}")
                

    def on_mouse_hover(self, event):
        if not event:
            self.data_label.setText("x = ---, y = ---")

    def position_window(self, pos='center'):
        # Set the window pop up position
        # Possible positions are:
        # 'center': screen center
        # 'center left': left side with the right edge on the screen center
        # 'center right': right side with the left edge on the screen
        # 'next to parent': the left edge next to its parent window
        
        # Get screen resolution
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        frame_size = self.frameGeometry()
        
        if pos == 'center':
            x = (screen_geometry.width() - frame_size.width()) // 2
            y = (screen_geometry.height() - frame_size.height()) // 2
            
        if pos == 'center left':
            x = screen_geometry.width() // 2 - frame_size.width()
            y = (screen_geometry.height() - frame_size.height()) // 2
        
        if pos == 'center right':
            x = screen_geometry.width() // 2 
            y = (screen_geometry.height() - frame_size.height()) // 2
        if pos == 'next to parent':
            if self.parent() is not None:
                parent = self.parent()
                parent_geometry = parent.frameGeometry()
                x = parent_geometry.x() + parent_geometry.width()
                y = parent_geometry.y()
                
        self.move(x, y)

    def custom_auto_range(self):
        x = self.x
        y = self.y
        x_min = min(x)
        x_max = max(x)
        y_span = max(y) - min(y)
        y_min = min(y) - y_span * 0.1
        y_max = max(y) + y_span * 0.1
        # Set the range
        viewbox = self.plot.getViewBox()
        viewbox.setRange(xRange=(x_min, x_max), yRange=(y_min, y_max), padding=0)
        

    def save_plot(self):
        options = QFileDialog.Options()
        self.file_path, self.selected_type = QFileDialog.getSaveFileName(self.parent(), 
                                                   "Export Figure", 
                                                   "", 
                                                   "Vector SVG Files (*.svg);;Color PNG Files (*.png);;Color JPEG Files (*.jpg);;Color TIFF Files (*.tiff);;Comma Separated Values (*.csv)", 
                                                   options=options)
        if self.file_path:
            self.file_type = getFileType(self.file_path)
            if self.selected_type in ['Color PNG Files (*.png)', 'Color JPEG Files (*.jpg)', 'Color TIFF Files (*.tiff)']:
                print(f'Saving plot to {self.file_path}')
                # scene = self.plot.scene()
                # size = scene.sceneRect().size()
                # save_size = int(size.width()), int(size.height())
                # exporter = pg.exporters.ImageExporter(scene)
                # exporter.parameters()['width'] = save_size[0]  # Set export width to current view width
                # exporter.parameters()['height'] = save_size[1]  # Set export height to current view height
                # exporter.export(self.file_path)
                self.plot.plotItem.writeImage(self.file_path)

            elif self.selected_type == 'Vector SVG Files (*.svg)':
                print(f'Saving plot to {self.file_path}')
                self.plot.plotItem.writeSvg(self.file_path)
                

                
                
                
            elif self.selected_type == 'Comma Separated Values (*.csv)':
                x_label = self.xlabel if self.xlabel is not None else 'X'
                y_label = self.ylabel if self.ylabel is not None else 'Y'
                line_x, line_y = self.x, self.y
                print(f'Exporting plot to {self.file_path}')
                with open(self.file_path, 'w') as f:
                    f.write(f'{x_label}, {y_label}\n')
                    for i in range(len(line_x)):
                        f.write(f'{line_x[i]}, {line_y[i]}\n')

    def copy_plot(self):
        # Copy the current plot to clipboard as an image
        scene = self.plot.scene()
        pixmap = scene.views()[0].grab(scene.itemsBoundingRect().toRect())

        # Set the pixmap to the clipboard
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(pixmap)
        self.statusBar.showMessage("The current image has been copied to the clipboard!")

    def close_all(self):
        plots = list(UI_TemCompanion.preview_dict.keys())
        for plot in plots:
            try:
                UI_TemCompanion.preview_dict[plot].close()
            except:
                pass

    def measure(self, orientation='horizontal'):
        # orientation: 'horizontal' or 'vertical'
        self.cleanup()
        # Finish button
        ok_icon = os.path.join(wkdir, 'icons/ok.png')
        self.buttons['ok'] = QAction(QIcon(ok_icon), "OK", self)
        self.buttons['ok'].setStatusTip("Finish measurement")
        self.buttons['ok'].setShortcut('Esc')
        self.buttons['ok'].triggered.connect(self.cleanup)
        self.toolbar.addAction(self.buttons['ok'])
        
        self.selector = pg.LinearRegionItem(orientation=orientation, movable=True, swapMode='block')
        if orientation == 'horizontal':
            # Set 40% to 60% of y range
            measuring_data = self.y
        else:
            # Set 40% to 60% of x range
            measuring_data = self.x
        x_span = max(measuring_data) - min(measuring_data)
        x_min = min(measuring_data) + x_span * 0.4
        x_max = min(measuring_data) + x_span * 0.6
        self.selector.setRegion([x_min, x_max])
        self.plot.addItem(self.selector)
        self.selector.sigRegionChanged.connect(self.update_measurement)
        self.update_measurement()
        self.statusBar.showMessage('Drag the edges to adjust the measurement region.')

    def update_measurement(self):
        if self.selector is not None:
            min_val, max_val = self.selector.getRegion()
            span = max_val - min_val
            self.statusBar.showMessage(f'Min: {min_val:.3f} | Max: {max_val:.3f} | Span: {span:.3f}')



    def cleanup(self):
        if self.selector is not None:
            self.plot.removeItem(self.selector)
            self.selector = None

        for key, value in self.buttons.items():
            if value is not None:
                self.toolbar.removeAction(self.buttons[key])
                self.buttons[key] = None

        self.statusBar.clearMessage()

    def plotsetting(self):
        dialog = PlotSettingDialog(parent=self)
        dialog.show()


#========= SimpleLevelsWidget ================================================
class SimpleLevelsWidget(QtWidgets.QWidget):
    """Minimal histogram + level control for an ImageItem."""
    sigLevelsChanged = pyqtSignal(object)
    sigLevelChangeFinished = pyqtSignal(object)

    def __init__(self, image_item, orientation='horizontal', bins=512, parent=None):
        super().__init__(parent)
        self.item = self  # for compatibility with previous self.lut.item usage
        self.image_item = image_item
        self.orientation = orientation
        self.bins = bins

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot = pg.PlotWidget(parent=self)
        self.plot.setBackground('k')
        self.plot_item = self.plot.getPlotItem()
        self.plot_item.hideButtons()
        self.plot_item.setContentsMargins(0, 0, 0, 0)
        self.plot_item.vb.setMenuEnabled(False)
        self.plot_item.showAxis('top', True)
        self.plot_item.hideAxis('bottom')
        self.plot_item.hideAxis('left')
        self.plot.setMouseEnabled(x=True, y=False)

        self.curve = self.plot.plot(pen=pg.mkPen((200, 200, 200, 100), width=1))
        layout.addWidget(self.plot)

        # LinearRegionItem along X to select min/max levels
        region_orientation = 'vertical'  # x-axis range selection
        self.region = pg.LinearRegionItem(orientation=region_orientation, movable=True, swapMode='block')
        self.plot.addItem(self.region)

        # Connect signals
        self.region.sigRegionChanged.connect(self._region_changing)
        self.region.sigRegionChangeFinished.connect(self._region_changed)

        # Track image changes to refresh histogram
        if hasattr(self.image_item, 'sigImageChanged'):
            self.image_item.sigImageChanged.connect(self.update_histogram)

        # Init histogram and region range
        self.update_histogram()
        levels = self.image_item.getLevels()
        if levels[0] is not None and levels[1] is not None:
            self.region.setRegion(levels)
        else:
            # fall back to data bounds
            mn, mx = self._data_min_max()
            self.region.setRegion([mn, mx])

        # Disable any context menu on the widget itself
        self.setContextMenuPolicy(Qt.NoContextMenu)

    # API compatibility with HistogramLUTItem
    def getLevels(self):
        return tuple(self.region.getRegion())

    def setLevels(self, min=None, max=None, rgba=None):
        if min is None or max is None:
            if rgba is not None and rgba[0] is not None:
                min, max = rgba[0]
            else:
                raise ValueError("Must specify min and max levels")
        self.region.setRegion((min, max))
        # Immediately push to image
        if self.image_item is not None:
            self.image_item.setLevels((min, max))
        self.sigLevelChangeFinished.emit(self)

    # Internal slots
    def _region_changing(self):
        if self.image_item is not None:
            self.image_item.setLevels(self.getLevels())
        self.sigLevelsChanged.emit(self)

    def _region_changed(self):
        if self.image_item is not None:
            self.image_item.setLevels(self.getLevels())
        self.sigLevelChangeFinished.emit(self)

    # Helpers
    def _data_min_max(self):
        img = getattr(self.image_item, 'image', None)
        if img is None:
            return (0.0, 1.0)
        arr = np.asarray(img)
        if arr.size == 0:
            return (0.0, 1.0)
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            return (0.0, 1.0)
        return (float(arr.min()), float(arr.max()))

    def update_histogram(self):
        h = self.image_item.getHistogram()
        self.curve.setData(*h)
        # Fill the curve
        self.curve.setFillLevel(0)
        self.curve.setBrush(pg.mkBrush(100, 100, 200))



#========= Redefined window for image edit button =============================
class CustomSettingsDialog(QDialog):
    def __init__(self, image_item, parent):
        # parent should be the PlotCanvas object
        super().__init__(parent) 
        self.image_item = image_item
        self.img_data = self.parent().canvas.img_data 

        self.setWindowTitle("Image Settings")        
        self.attribute = self.parent().canvas.attribute

        
        
        self.colorbar = QCheckBox('Colorbar', self)
        if self.attribute['colorbar']:
            self.colorbar.setChecked(True)
        else:
            self.colorbar.setChecked(False)
        self.colorbar.stateChanged.connect(self.set_colorbar)
        
        self.original_settings = copy.copy(self.attribute)
        
        # Create the layout
        layout = QVBoxLayout()

        display_group = QGroupBox("Display Adjustment", self)
        display_layout = QVBoxLayout()

        # Insert a LUT adjustment
        levels = self.image_item.getLevels()
        vmin, vmax = levels[0], levels[1]
        self.original_settings['vmin'] = vmin
        self.original_settings['vmax'] = vmax

        self.lut = SimpleLevelsWidget(self.image_item, orientation='horizontal', bins=512, parent=self)
        self.lut.item.setLevels(vmin, vmax)
        self.lut.setMinimumHeight(100)

        
        self.lut.item.sigLevelsChanged.connect(self.update_colorbar_levels)
        self.lut.item.sigLevelsChanged.connect(self.update_level_labels)
        display_layout.addWidget(self.lut)
        
        # for comparison
        # self.pglut = pg.HistogramLUTWidget(parent=self, image=self.image_item, orientation='horizontal')
        # self.pglut.item.setLevels(vmin, vmax)
        # display_layout.addWidget(self.pglut)

        # vmin and vmax inputs
        h_layout_vmin = QHBoxLayout()
        vmin_label = QLabel("Vmin:")
        self.vmin_input = QLineEdit()
        self.vmin_set = QPushButton("Set")
        h_layout_vmin.addWidget(vmin_label)
        h_layout_vmin.addWidget(self.vmin_input)
        h_layout_vmin.addWidget(self.vmin_set)
        display_layout.addLayout(h_layout_vmin)

        h_layout_vmax = QHBoxLayout()
        vmax_label = QLabel("Vmax:")
        self.vmax_input = QLineEdit()
        self.vmax_set = QPushButton("Set")
        h_layout_vmax.addWidget(vmax_label)
        h_layout_vmax.addWidget(self.vmax_input)
        h_layout_vmax.addWidget(self.vmax_set)
        display_layout.addLayout(h_layout_vmax)

        

        self.vmin_set.clicked.connect(self.set_levels)
        self.vmax_set.clicked.connect(self.set_levels)

        # Set initial vmin and vmax
        self.vmin_input.setText(f"{vmin:.4g}")
        self.vmax_input.setText(f"{vmax:.4g}")

        # Gamma correction
        h_layout_gamma = QHBoxLayout()
        gamma_label = QLabel("Gamma:")
        self.gamma_slider = QSlider(Qt.Horizontal)
        self.gamma_slider.setMinimum(1)
        self.gamma_slider.setMaximum(20)
        self.gamma_slider.setValue(int(self.attribute['gamma'] * 10))
        self.gamma_value_label = QLabel(f"{self.attribute['gamma']:.1f}")
        h_layout_gamma.addWidget(gamma_label)
        h_layout_gamma.addWidget(self.gamma_slider)
        h_layout_gamma.addWidget(self.gamma_value_label)
        display_layout.addLayout(h_layout_gamma)
        self.gamma_slider.valueChanged.connect(self.update_gamma)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # Colormap dropdown
        h_layout_cmap = QHBoxLayout()
        self.cmap_label = QLabel("Preset Maps:")
        self.cmap_combobox = QComboBox()
        self.cmap_combobox.setIconSize(QSize(80, 20))
        colormaps = ['viridis', 'plasma', 'inferno', 'magma', 'cividis',
                     'gray', 'spring', 'summer', 'autumn', 'winter', 'cool',
                      'Wistia', 'hot',
                     'Red', 'Orange', 'Yellow', 'Green', 'Cyan', 'Lime', 'Purple',
                     'Magenta', 'Pink', 'Blue', 'Maize',
                     'jet', 'rainbow', 'turbo', 'hsv', 'seismic'
                     ]
        for cmap_name in colormaps:
            icon = self.create_colormap_icon(cmap_name)
            self.cmap_combobox.addItem(icon, cmap_name)
        #  self.cmap_combobox.addItems(colormaps)
        h_layout_cmap.addWidget(self.cmap_label)
        h_layout_cmap.addWidget(self.cmap_combobox)
        h_layout_cmap.addWidget(self.colorbar)

        cmap_group = QGroupBox("Colormap", self)
        cmap_group.setLayout(h_layout_cmap)
        layout.addWidget(cmap_group)

        # Set current colormap
        cmap = self.attribute['cmap']
        self.cmap_combobox.setCurrentText(cmap)
            
        # Scalebar customization

        scalebar_group = QGroupBox("Scalebar Customization", self)
        scalebar_layout = QVBoxLayout()

        self.scalebar_check = QCheckBox("Add scalebar to image")
        self.scalebar_check.setChecked(self.attribute['scalebar'])
        scalebar_layout.addWidget(self.scalebar_check)

        h_layout_scalebar = QHBoxLayout()
        self.sbcolor_label = QLabel('Scalebar color')
        self.sbcolor_combobox = pg.ColorButton()
        self.sbcolor_combobox.setColor(pg.mkColor(self.attribute['color']))
        
        
        
        h_layout_scalebar.addWidget(self.sbcolor_label)
        h_layout_scalebar.addWidget(self.sbcolor_combobox)
        scalebar_layout.addLayout(h_layout_scalebar)

        h_layout_loc = QHBoxLayout()
        self.sbloc_label = QLabel('Scalebar location')
        self.sblocation_combox = QComboBox()
        sbloc = ['lower left', 'lower right', 'upper left', 'upper right']
        self.sblocation_combox.addItems(sbloc)
        self.sblocation_combox.setCurrentText(self.attribute['location'])
        h_layout_loc.addWidget(self.sbloc_label)
        h_layout_loc.addWidget(self.sblocation_combox)
        scalebar_layout.addLayout(h_layout_loc)

        scalebar_group.setLayout(scalebar_layout)
        layout.addWidget(scalebar_group)

        # Connect all functions
        self.cmap_combobox.currentTextChanged.connect(self.update_colormap)
        self.sbcolor_combobox.sigColorChanged.connect(self.update_scalebar)
        self.scalebar_check.stateChanged.connect(self.update_scalebar)     
        # self.sbcolor_combobox.currentTextChanged.connect(self.update_scalebar)
        self.sblocation_combox.currentTextChanged.connect(self.update_scalebar)

        

        # Apply button
        buttons = QDialogButtonBox(QDialogButtonBox.Reset | QDialogButtonBox.Ok)
        self.reset_button = buttons.button(QDialogButtonBox.Reset)
        self.reset_button.clicked.connect(self.reset_settings)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.ok_button.clicked.connect(self.accept)     
        layout.addWidget(buttons)
        

        self.setLayout(layout)

    def create_colormap_icon(self, cmap_name):
        lut = custom_cmap[cmap_name]
        width = 40
        strip = np.repeat(lut[None, :, :], width, axis=0)
        qimg = QImage(strip, 256, width, 256*4, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimg)
        icon = QIcon(pixmap)
        return icon

    def update_level_labels(self):
        levels = self.lut.item.getLevels()
        vmin, vmax = levels[0], levels[1]
        self.vmin_input.setText(f"{vmin:.4g}")
        self.vmax_input.setText(f"{vmax:.4g}")

    def set_levels(self):
        try:
            vmin = float(self.vmin_input.text())
            vmax = float(self.vmax_input.text())
            if vmin >= vmax:
                QMessageBox.warning(self, "Invalid Input", 
                                        "Vmin must be less than Vmax.")
                return
            self.lut.item.setLevels(min=vmin, max=vmax)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Invalid input for vmin/vmax: {e}")

    def update_gamma(self):
        gamma_value = self.gamma_slider.value() / 10.0
        self.gamma_value_label.setText(f"{gamma_value:.1f}")
        self.parent().canvas.attribute['gamma'] = gamma_value
        # Apply gamma to LUT 
        self.update_colormap()

        

    def set_colorbar(self):
        if self.colorbar.isChecked():
            self.parent().canvas.toggle_colorbar(True)
        else:
            self.parent().canvas.toggle_colorbar(False)

    def update_colorbar_levels(self):
        if self.parent().canvas.colorbar is not None:
            self.parent().canvas.colorbar.setLevels(self.lut.item.getLevels())


    def update_colormap(self):
        # Apply colormap
        self.cmap_name = self.cmap_combobox.currentText()
        lut = custom_cmap[self.cmap_name]
        # Apply gamma correction
        g = self.gamma_slider.value() / 10.0
        lut = gamma_correct_lut(lut, g)

        self.parent().canvas.image_item.setLookupTable(lut)
        self.parent().canvas.attribute['cmap'] = self.cmap_name
        # Update the LUT widget
        # cmap = pg.ColorMap(pos=np.linspace(0, 1, 256), color=lut)
        # self.lut.item.gradient.setColorMap(cmap)
        # Update the colorbar if exists
        if self.parent().canvas.colorbar is not None:
            cmap = pg.ColorMap(pos=np.linspace(0, 1, 256), color=lut)
            self.parent().canvas.colorbar.setColorMap(cmap)

    def update_scalebar(self):
        # Apply scalebar styles
        self.parent().canvas.attribute['scalebar'] = self.scalebar_check.isChecked()
        self.parent().canvas.attribute['color'] = self.sbcolor_combobox.color()
        self.parent().canvas.attribute['location'] = self.sblocation_combox.currentText()
        
        self.parent().create_scalebar()
        
    
    def reset_settings(self):
        # Reset scalebar
        self.scalebar_check.setChecked(self.original_settings['scalebar'])
        self.colorbar.setChecked(self.original_settings['colorbar'])
        self.sbcolor_combobox.setColor(pg.mkColor(self.original_settings['color']))      
        self.sblocation_combox.setCurrentText(self.original_settings['location'])
        
        # Reset vmin vmax
        self.lut.item.setLevels(min=self.original_settings['vmin'], max=self.original_settings['vmax'])
        # Reset colormap
        self.gamma_slider.setValue(int(self.original_settings['gamma'] * 10))
        cmap = self.original_settings['cmap']
        self.cmap_combobox.setCurrentText(cmap)

            

#============ Define a dialogue for filter settings ===========================
class FilterSettingDialogue(QDialog):
    def __init__(self, apply_wf, apply_absf, apply_nl, apply_bw, apply_gaussian, parameters):
        super().__init__()
        self.setWindowTitle("Filter Settings")        
        layout = QVBoxLayout()
        
        default_values = parameters
        self.parameters = {}

        # Wiener Filter Section
        self.wiener_check = QCheckBox("Apply Wiener Filter (for batch conversion)")
        self.wiener_check.setChecked(apply_wf)
        
        self.wiener_group = QGroupBox()
        form_layout = QFormLayout()
        self.delta_wf = QLabel('WF Delta')
        self.delta_wf.setToolTip('Threashold for diffraction spots removal. Smaller delta gives smoothier averaging background but takes more time.') 
        self.delta_wf_input = QLineEdit()
        self.delta_wf_input.setText(default_values['WF Delta'])
        form_layout.addRow(self.delta_wf, self.delta_wf_input)
        self.order_wf = QLabel('WF Bw-order')
        self.order_wf.setToolTip('The order of the lowpass Butterworth filter. Bigger number gives a steeper cutoff.') 
        self.order_wf_input = QLineEdit()
        self.order_wf_input.setText(default_values['WF Bw-order'])
        form_layout.addRow(self.order_wf, self.order_wf_input)
        self.cutoff_wf = QLabel('WF Bw-cutoff')
        self.cutoff_wf.setToolTip('Fraction of radius in reciprocal space from where the taper of the lowpass starts.')
        self.cutoff_wf_input = QLineEdit()
        self.cutoff_wf_input.setText(default_values['WF Bw-cutoff'])
        form_layout.addRow(self.cutoff_wf, self.cutoff_wf_input)
        self.wiener_group.setLayout(form_layout)
        self.wiener_group.setEnabled(True)
        layout.addWidget(self.wiener_check)
        layout.addWidget(self.wiener_group)

        # ABS Filter Section
        self.absf_check = QCheckBox("Apply ABS Filter (for batch conversion)")
        self.absf_check.setChecked(apply_absf)
        self.absf_group = QGroupBox()
        form_layout = QFormLayout()
        self.delta_absf = QLabel('ABSF Delta')
        self.delta_absf.setToolTip('Threashold for diffraction spots removal. Smaller delta gives smoothier averaging background but takes more time.') 
        self.delta_absf_input = QLineEdit()
        self.delta_absf_input.setText(default_values['ABSF Delta'])
        form_layout.addRow(self.delta_absf, self.delta_absf_input)
        self.order_absf = QLabel('ABSF Bw-order')
        self.order_absf.setToolTip('The order of the lowpass Butterworth filter. Bigger number gives a steeper cutoff.') 
        self.order_absf_input = QLineEdit()
        self.order_absf_input.setText(default_values['ABSF Bw-order'])
        form_layout.addRow(self.order_absf, self.order_absf_input)
        self.cutoff_absf = QLabel('ABSF Bw-cutoff')
        self.cutoff_absf.setToolTip('Fraction of radius in reciprocal space from where the taper of the lowpass starts.')
        self.cutoff_absf_input = QLineEdit()
        self.cutoff_absf_input.setText(default_values['ABSF Bw-cutoff'])
        form_layout.addRow(self.cutoff_absf, self.cutoff_absf_input)
        self.absf_group.setLayout(form_layout)
        #self.absf_group.setLayout(self.create_form_layout(["ABSF Delta", "ABSF Bw-order", "ABSF Bw-cutoff"], default_values, self.parameters))
        self.absf_group.setEnabled(True)
        #self.absf_check.stateChanged.connect(lambda: self.absf_group.setEnabled(self.absf_check.isChecked()))
        layout.addWidget(self.absf_check)
        layout.addWidget(self.absf_group)

        # Non-Linear Filter Section
        self.nl_check = QCheckBox("Apply Non-Linear Filter (for batch conversion)")
        self.nl_check.setChecked(apply_nl)
        self.nl_group = QGroupBox()
        form_layout = QFormLayout()
        self.N = QLabel('NL Cycles')
        self.N.setToolTip('Repetition of Wiener-Lowpass filter cycles. More repetition gives stronger filtering effect but takes more time.')
        self.N_input = QLineEdit()
        self.N_input.setText(default_values['NL Cycles'])
        form_layout.addRow(self.N, self.N_input)
        self.delta_nl = QLabel('NL Delta')
        self.delta_nl.setToolTip('Threashold for diffraction spots removal. Smaller delta gives smoothier averaging background but taks more time.') 
        self.delta_nl_input = QLineEdit()
        self.delta_nl_input.setText(default_values['NL Delta'])
        form_layout.addRow(self.delta_nl, self.delta_nl_input)
        self.order_nl = QLabel('NL Bw-order')
        self.order_nl.setToolTip('The order of the lowpass Butterworth filter. Bigger number gives a steeper cutoff.') 
        self.order_nl_input = QLineEdit()
        self.order_nl_input.setText(default_values['NL Bw-order'])
        form_layout.addRow(self.order_nl, self.order_nl_input)
        self.cutoff_nl = QLabel('NL Bw-cutoff')
        self.cutoff_nl.setToolTip('Fraction of radius in reciprocal space from where the taper of the lowpass starts.')
        self.cutoff_nl_input = QLineEdit()
        self.cutoff_nl_input.setText(default_values['NL Bw-cutoff'])
        form_layout.addRow(self.cutoff_nl, self.cutoff_nl_input)
        self.nl_group.setLayout(form_layout)
        #self.nl_group.setLayout(self.create_form_layout(["NL Cycles", "NL Delta", "NL Bw-order", "NL Bw-cutoff"], default_values, self.parameters))
        self.nl_group.setEnabled(True)
        #self.nl_check.stateChanged.connect(lambda: self.nl_group.setEnabled(self.nl_check.isChecked()))
        layout.addWidget(self.nl_check)
        layout.addWidget(self.nl_group)
        
        # Butterworth filter 
        self.bw_check = QCheckBox("Apply Buttwrworth Filter (for batch conversion)")
        self.bw_check.setChecked(apply_bw)
        self.bw_group = QGroupBox()
        form_layout = QFormLayout()
        self.order_bw = QLabel('Bw-order')
        self.order_bw.setToolTip('The order of the lowpass Butterworth filter. Bigger number gives a steeper cutoff.') 
        self.order_bw_input = QLineEdit()
        self.order_bw_input.setText(default_values['Bw-order'])
        form_layout.addRow(self.order_bw, self.order_bw_input)
        self.cutoff_bw = QLabel('Bw-cutoff')
        self.cutoff_bw.setToolTip('Fraction of radius in reciprocal space from where the taper of the lowpass starts.')
        self.cutoff_bw_input = QLineEdit()
        self.cutoff_bw_input.setText(default_values['Bw-cutoff'])
        form_layout.addRow(self.cutoff_bw, self.cutoff_bw_input)
        self.bw_group.setLayout(form_layout)
        self.bw_group.setEnabled(True)
        layout.addWidget(self.bw_check)
        layout.addWidget(self.bw_group)
        
        # Gaussian filter 
        self.gaussian_check = QCheckBox("Apply Gaussian Filter (for batch conversion)")
        self.gaussian_check.setChecked(apply_gaussian)
        self.gaussian_group = QGroupBox()
        form_layout = QFormLayout()
        self.cutoff_gaussian = QLabel('Gaussian cutoff')
        self.cutoff_gaussian.setToolTip('Fraction of radius in reciprocal space from where the taper of the lowpass starts.')
        self.cutoff_gaussian_input = QLineEdit()
        self.cutoff_gaussian_input.setText(default_values['GS-cutoff'])
        form_layout.addRow(self.cutoff_gaussian, self.cutoff_gaussian_input)
        self.gaussian_group.setLayout(form_layout)
        self.gaussian_group.setEnabled(True)
        layout.addWidget(self.gaussian_check)
        layout.addWidget(self.gaussian_group)

        # Dialog Buttons (OK and Cancel)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.handle_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
    
    def handle_ok(self):
        parameters = {}

        self.apply_wf = self.wiener_check.isChecked()
        self.apply_absf = self.absf_check.isChecked()
        self.apply_nl = self.nl_check.isChecked()
        self.apply_bw = self.bw_check.isChecked()
        self.apply_gaussian = self.gaussian_check.isChecked()
        parameters = {'WF Delta': self.delta_wf_input.text(),
                      'WF Bw-order': self.order_wf_input.text(),
                      'WF Bw-cutoff': self.cutoff_wf_input.text(),
                      'ABSF Delta': self.delta_absf_input.text(),
                      'ABSF Bw-order': self.order_absf_input.text(),
                      'ABSF Bw-cutoff': self.cutoff_absf_input.text(),
                      'NL Cycles': self.N_input.text(),
                      'NL Delta': self.delta_nl_input.text(),
                      'NL Bw-order': self.order_nl_input.text(),
                      'NL Bw-cutoff': self.cutoff_nl_input.text(),
                      'Bw-order': self.order_bw_input.text(),
                      'Bw-cutoff': self.cutoff_bw_input.text(),
                      'GS-cutoff': self.cutoff_gaussian_input.text()
            }
        
        self.parameters = parameters        
        
        self.accept()

#=========== Apply filter dialogue ==================================
class ApplyFilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apply Filter")
        layout = QVBoxLayout()
        label1 = QLabel("Apply filter to:")
        layout.addWidget(label1)
        layout2 = QHBoxLayout()
        self.apply_current = QPushButton("Current frame")
        self.apply_current.clicked.connect(self.apply_current_clicked)
        self.apply_stack = QPushButton("Entire stack")
        self.apply_stack.clicked.connect(self.apply_stack_clicked)
        layout2.addWidget(self.apply_current)
        layout2.addWidget(self.apply_stack)
        layout.addLayout(layout2)
        self.setLayout(layout)

    def apply_current_clicked(self):
            self.apply_to = 'current'
            self.accept()

    def apply_stack_clicked(self):
            self.apply_to = 'stack'
            self.accept()

        

#=========== Rotate image dialogue ==================================
class RotateImageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rotate image")        
        layout = QVBoxLayout()
        self.rotate_ang = None
        self.angle_input = QLineEdit(self)
        self.angle_input.setPlaceholderText('Enter angle in degrees')
        layout.addWidget(self.angle_input)
        
        # Dialog Buttons (OK and Cancel)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.handle_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
    def handle_ok(self):
        self.rotate_ang = self.angle_input.text()
        self.accept()
        
#============== Manual crop dialog ================================
class ManualCropDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Input crop range")
        self.x_range = None
        self.y_range = None
        layout = QVBoxLayout()
        x_layout = QHBoxLayout()
        x_label = QLabel('x range')
        self.x_min = QLineEdit()
        self.x_min.setPlaceholderText('xmin')
        x_label2 = QLabel(':')
        self.x_max = QLineEdit()
        self.x_max.setPlaceholderText('xmax')
        x_layout.addWidget(x_label)
        x_layout.addWidget(self.x_min)
        x_layout.addWidget(x_label2)
        x_layout.addWidget(self.x_max)
        y_layout = QHBoxLayout()
        y_label = QLabel('y range')
        self.y_min = QLineEdit()
        self.y_min.setPlaceholderText('ymin')
        y_label2 = QLabel(':')
        self.y_max = QLineEdit()
        self.y_max.setPlaceholderText('ymax')
        y_layout.addWidget(y_label)
        y_layout.addWidget(self.y_min)
        y_layout.addWidget(y_label2)
        y_layout.addWidget(self.y_max)
        
        layout.addLayout(x_layout)
        layout.addLayout(y_layout)
        
        # Dialog Buttons (OK and Cancel)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.handle_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
    def handle_ok(self):
        # Validate the inputs
        try:
            xmin = int(self.x_min.text())
            xmax = int(self.x_max.text())
            ymin = int(self.y_min.text())
            ymax = int(self.y_max.text())
        except:
            QMessageBox.warning(self, 'Manual Input', 'Invalid crop range. Index must be integers!')
            return
            
        img_size = self.parent().img_size
        if xmin < 0 or xmax < 0 or ymin < 0 or ymax < 0:
            QMessageBox.warning(self, 'Manual Input', 'Invalid crop range. Index must be positive!')
            return
        
        elif xmax > img_size[0] or ymax > img_size[1]:
            QMessageBox.warning(self, 'Manual Input', 'Invalid crop range. Index must be smaller than the image size!')
            return
        
        elif xmin > xmax or ymin > ymax:
            QMessageBox.warning(self, 'Manual Input', 'Invalid crop range. Min must be greater than max!')
            return
        
        elif xmax - xmin < 5 or ymax - ymin < 5:
            QMessageBox.warning(self, 'Manual Input', 'Invalid crop range. Crop range must be at least 5 pixels!')
            return
        
        else:
            self.x_range = xmin, xmax
            self.y_range = ymin, ymax
        self.accept()
        
        

#============ Set scale dialogue ==================================
class SetScaleDialog(QDialog):
    def __init__(self, scale, units, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Set pixel scale")        
        layout = QVBoxLayout()
        self.scale_input = QLineEdit(self)
        self.scale_input.setText(str(scale))
        self.unit_input = QLineEdit(self)
        self.unit_input.setText(str(units))
        layout.addWidget(self.scale_input)
        layout.addWidget(self.unit_input)
        
        # Dialog Buttons (OK and Cancel)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.handle_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
    def handle_ok(self):
        self.scale = self.scale_input.text()
        self.units = self.unit_input.text()
        self.accept()
        

#================= Align Stack dialogue =====================================
class AlignStackDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle('Align stack parameters')
        layout = QVBoxLayout()
  
        self.apply_window_check = QCheckBox('Apply a Hann window filter')
        self.apply_window_check.setChecked(True)
        self.crop_img_check = QCheckBox('Crop to common area')
        self.crop_img_check.setChecked(True)
        self.crop_to_square_check = QCheckBox('Crop to the biggest square')
        self.crop_to_square_check.setEnabled(True)
        self.crop_img_check.stateChanged.connect(self.crop_to_square_change)
        self.crop_to_square_check.setChecked(False)
        layout.addWidget(self.apply_window_check)
        layout.addWidget(self.crop_img_check)
        layout.addWidget(self.crop_to_square_check)
        
        # Dialog Buttons (OK and Cancel)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.handle_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
    def crop_to_square_change(self):
        enable = not self.crop_to_square_check.isEnabled()
        self.crop_to_square_check.setEnabled(enable)
        if not enable:
            self.crop_to_square_check.setChecked(False)
            
 
        
    def handle_ok(self):
        #self.get_algorithm()
        self.crop_to_square = False
        self.apply_window = self.apply_window_check.isChecked()
        self.crop_img = self.crop_img_check.isChecked()
        if self.crop_img:
            self.crop_to_square = self.crop_to_square_check.isChecked()
            
        self.accept()
        

                


#=============== Display metadata window ===========================
class MetadataViewer(QMainWindow):
    def __init__(self, metadata, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Metadata Viewer')
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.metadata = metadata
        self.create_menubar()

        # Create DataTreeWidget and set the data
        self.data_tree_widget = pg.DataTreeWidget()
        self.data_tree_widget.setData(metadata)
        self.data_tree_widget.setColumnHidden(1, True)  # Hide the 'Type' column
        layout.addWidget(self.data_tree_widget)
        
    def create_menubar(self):        
        menubar = self.menuBar()  # Create a menu bar

        # File menu and actions
        file_menu = menubar.addMenu('File')
        save_action = QAction('Export', self)
        save_action.triggered.connect(self.export)
        file_menu.addAction(save_action)
        close_action = QAction('Close', self)
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)

            
    def export(self):
        options = QFileDialog.Options()
        self.file_path, self.selected_type = QFileDialog.getSaveFileName(self.parent(), 
                                                   "Export Metadata", 
                                                   "", 
                                                   "JSON Files (*.json);;Pickle Dictionary Files (*.pkl)", 
                                                   options=options)
        if self.file_path:
            # Implement custom save logic here
            if self.selected_type == 'JSON Files (*.json)':
                with open(self.file_path,'w') as f:
                    json.dump(self.metadata, f, indent=4)
                    
            if self.selected_type == 'Pickle Dictionary Files (*.pkl)':
                with open(self.file_path, 'wb') as f:
                    pickle.dump(self.metadata, f)
                    
                    
# ================== Axes Viewer =================================
class DictionaryTreeWidget(QMainWindow):
    def __init__(self, axes_dict, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Axes Information')
        self.setGeometry(100, 100, 400, 350)

        # Create a QTreeWidget
        self.tree = QTreeWidget(self)
        self.setCentralWidget(self.tree)

        # Set Up Columns
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(['Item', 'Value'])
        
        # Set default column widths
        self.tree.setColumnWidth(0, 150)  # Width for the 'Key' column
        self.tree.setColumnWidth(1, 250)  # Width for the 'Value' column


        # Fill the tree with dictionary data
        self.populate_tree(axes_dict)
        
        # Expand all items by default
        self.tree.expandAll()


    def populate_tree(self, dictionary, parent_item=None):
        for key, value in dictionary.items():
            # Create a QTreeWidgetItem for this key-value pair
            if parent_item is None:
                item = QTreeWidgetItem(self.tree)
            else:
                item = QTreeWidgetItem(parent_item)

            item.setText(0, str(key))

            if isinstance(value, dict):
                item.setText(1, '')
                # Recursive call to populate children
                self.populate_tree(value, item)
            else:
                item.setText(1, str(value))

# ================= Spectrum plot settings dialog ===================
class PlotSettingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot Settings")

        layout = QVBoxLayout()

        # Plot title input
        h_layout_title = QHBoxLayout()
        title_label = QLabel("Title:")
        self.title_input = QLineEdit()
        h_layout_title.addWidget(title_label)
        h_layout_title.addWidget(self.title_input)
        layout.addLayout(h_layout_title)

        # Set current title
        current_title = self.parent().plot.getPlotItem().titleLabel.text
        self.title_input.setText(current_title)

        # X label input
        h_layout_xlabel = QHBoxLayout()
        xlabel_label = QLabel("X Label:")
        self.xlabel_input = QLineEdit()
        h_layout_xlabel.addWidget(xlabel_label)
        h_layout_xlabel.addWidget(self.xlabel_input)
        layout.addLayout(h_layout_xlabel)

        # Set current x label
        current_xlabel = self.parent().plot.getPlotItem().getAxis('bottom').labelText
        self.xlabel_input.setText(current_xlabel)

        # X axis range inputs
        h_layout_xmin = QHBoxLayout()
        xmin_label = QLabel("Xmin:")
        self.xmin_input = QLineEdit()
        h_layout_xmin.addWidget(xmin_label)
        h_layout_xmin.addWidget(self.xmin_input)
        layout.addLayout(h_layout_xmin)

        h_layout_xmax = QHBoxLayout()
        xmax_label = QLabel("Xmax:")
        self.xmax_input = QLineEdit()
        h_layout_xmax.addWidget(xmax_label)
        h_layout_xmax.addWidget(self.xmax_input)
        layout.addLayout(h_layout_xmax)

        # Y axis label input
        h_layout_ylabel = QHBoxLayout()
        ylabel_label = QLabel("Y Label:")
        self.ylabel_input = QLineEdit()
        h_layout_ylabel.addWidget(ylabel_label)
        h_layout_ylabel.addWidget(self.ylabel_input)
        layout.addLayout(h_layout_ylabel)

        # Set current y label
        current_ylabel = self.parent().plot.getPlotItem().getAxis('left').labelText
        self.ylabel_input.setText(current_ylabel)

        # Y axis range inputs
        
        h_layout_ymin = QHBoxLayout()
        ymin_label = QLabel("Ymin:")
        self.ymin_input = QLineEdit()
        h_layout_ymin.addWidget(ymin_label)
        h_layout_ymin.addWidget(self.ymin_input)
        layout.addLayout(h_layout_ymin)

        h_layout_ymax = QHBoxLayout()
        ymax_label = QLabel("Ymax:")
        self.ymax_input = QLineEdit()
        h_layout_ymax.addWidget(ymax_label)
        h_layout_ymax.addWidget(self.ymax_input)
        layout.addLayout(h_layout_ymax)
        
        

        # Set current range
        viewbox = self.parent().plot.getViewBox()
        view_range = viewbox.viewRange()
        xmin, xmax = view_range[0]
        ymin, ymax = view_range[1]
        self.xmin_input.setText(f'{xmin:.2f}')
        self.xmax_input.setText(f'{xmax:.2f}')
        self.ymin_input.setText(f'{ymin:.2f}')
        self.ymax_input.setText(f'{ymax:.2f}')
        

        # Line color dropdown
        h_layout_color = QHBoxLayout()
        color_label = QLabel("Line Color:")
        self.color_combobox = pg.ColorButton(parent=self)
        # colors = ['black', 'white', 'gray', 'brown', 'red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'purple']
        # self.color_combobox.addItems(colors)
        h_layout_color.addWidget(color_label)
        h_layout_color.addWidget(self.color_combobox)
        layout.addLayout(h_layout_color)

        # Set current color
        line = self.parent().plot_data_item
        line_color = line.opts['pen'].color()
        self.color_combobox.setColor(line_color)

        # Line width input
        h_layout_linewidth = QHBoxLayout()
        linewidth_label = QLabel("Line Width:")
        self.linewidth_input = QLineEdit()
        h_layout_linewidth.addWidget(linewidth_label)
        h_layout_linewidth.addWidget(self.linewidth_input)
        layout.addLayout(h_layout_linewidth)

        # Set current line width
        line_width = line.opts['pen'].width()
        self.linewidth_input.setText(str(line_width))

        # Background color dropdown
        h_layout_bgcolor = QHBoxLayout()
        bgcolor_label = QLabel("Background Color:")
        self.bgcolor_combobox = pg.ColorButton(parent=self)
        h_layout_bgcolor.addWidget(bgcolor_label)
        h_layout_bgcolor.addWidget(self.bgcolor_combobox)
        layout.addLayout(h_layout_bgcolor)

        # Set current background color
        bg_color = self.parent().plot._background
        self.bgcolor_combobox.setColor(pg.mkColor(bg_color))


        # Axis color dropdown
        h_layout_axcolor = QHBoxLayout()
        axcolor_label = QLabel("Axis Color:")
        self.axcolor_combobox = pg.ColorButton(parent=self)
        h_layout_axcolor.addWidget(axcolor_label)
        h_layout_axcolor.addWidget(self.axcolor_combobox)
        layout.addLayout(h_layout_axcolor)

        # Set current axis color
        ax_color = self.parent().plot.getPlotItem().getAxis('bottom').pen().color()
        self.axcolor_combobox.setColor(ax_color)


        # Turn on/off grid
        self.grid_on = self.parent().plot.getPlotItem().getAxis('bottom').grid
        self.grid_check = QCheckBox("Show Grid")
        self.grid_check.setChecked(self.grid_on)
        layout.addWidget(self.grid_check)

            

        # Apply button
        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Ok)
        self.apply_button = buttons.button(QDialogButtonBox.Apply)
        self.apply_button.clicked.connect(self.apply_settings)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.ok_button.clicked.connect(self.handle_ok)
        
        layout.addWidget(buttons)
        

        self.setLayout(layout)

    def apply_settings(self):
        plot = self.parent().plot
        line = self.parent().plot_data_item

        # Apply title
        title = self.title_input.text()
        plot.setTitle(title)

        # Apply axis labels
        xlabel = self.xlabel_input.text()
        ylabel = self.ylabel_input.text()
        plot.setLabel('bottom', xlabel)
        plot.setLabel('left', ylabel)

        # Apply axes ranges
        try:
            xmin = float(self.xmin_input.text())
            xmax = float(self.xmax_input.text())
            ymin = float(self.ymin_input.text())
            ymax = float(self.ymax_input.text())

        except ValueError:
            QMessageBox.warning(self, 'Plot settings', 'Invalid min or max values!')
            return
            
       
        viewbox = self.parent().plot.getViewBox()
        viewbox.setRange(xRange=(xmin, xmax), yRange=(ymin, ymax), padding=0)
            

        # Apply color and width
        line_color = self.color_combobox.color()
        linewidth = int(self.linewidth_input.text())
        pen = pg.mkPen(color=line_color, width=linewidth)
        line.setPen(pen)

        # Apply background color
        bg_color = self.bgcolor_combobox.color()
        # if bg_color == 'None':
        #     bg_color = None
        plot.setBackground(bg_color)

        # Apply axis color
        ax_color = self.axcolor_combobox.color()
        x_axis = plot.getPlotItem().getAxis('bottom')
        y_axis = plot.getPlotItem().getAxis('left')
        x_axis.setPen(ax_color)
        y_axis.setPen(ax_color)
        x_axis.setTextPen(ax_color)
        y_axis.setTextPen(ax_color)


        # Apply grid
        self.grid_on = self.grid_check.isChecked()
        plot.showGrid(x=self.grid_on, y=self.grid_on)
    
    def handle_ok(self):
        self.apply_settings()
        self.accept()

    
        


#==============Radial Integration Dialog===================================
class RadialIntegrationDialog(QDialog):
    def __init__(self, parent):
        # Parent must be the image window
        super().__init__(parent)
        self.setWindowTitle("Radial Integration")
        self.center = self.parent().canvas.center
        self.img_dict = self.parent().get_img_dict_from_canvas()

        layout = QVBoxLayout()
        label = QLabel("Select the center for radial integration:")
        self.center_label = QLabel(f"Center: {self.center}")
        layout.addWidget(label)
        layout.addWidget(self.center_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.cancel_button = buttons.button(QDialogButtonBox.Cancel)
        self.cancel_button.clicked.connect(self.handle_cancel)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.ok_button.clicked.connect(self.handle_ok)
        layout.addWidget(buttons)

        self.setLayout(layout)


    def handle_ok(self):
        # Handle the OK button press
        self.calculate_radial_integration(self.center)
        self.accept()

    def handle_cancel(self):
        self.parent().clean_up(selector=True, modes=True, status_bar=True)
        self.reject()

    def update_center(self, center):
        self.center = center
        self.center_label.setText(f"Center: {self.center}")

    def calculate_radial_integration(self, center):
        # Perform radial integration calculation
        img = copy.deepcopy(self.img_dict['data'])
        original_center = img.shape[1]//2, img.shape[0]//2
        # Shift image to center
        if center != original_center:
            offset = (int(center[0] - original_center[0]), int(center[1] - original_center[1]))
            x_span = int(min(center[0], img.shape[1]-center[0]))
            new_x_start = center[0] - x_span
            new_x_end = new_x_start + 2 * x_span
            y_span = int(min(center[1], img.shape[0]-center[1]))
            new_y_start = center[1] - y_span
            new_y_end = new_y_start + 2 * y_span
            img = img[new_y_start:new_y_end, new_x_start:new_x_end]
            if img.shape[0] != img.shape[1]:
                img = filters.crop_to_square(img)
            print(f'Original center: {original_center}')
            print(f'New center: {center}')
            print(f"Cropping image to {new_y_start}:{new_y_end}, {new_x_start}:{new_x_end}")
            print(f'New image shape: {img.shape}')

        radial_x, radial_y = filters.radial_integration(img)
        scale = self.img_dict['axes'][1]['scale']
        unit = self.img_dict['axes'][1]['units']
        calibrated_x = radial_x * scale

        # Plot the radial profile
        preview_name = self.parent().windowTitle() + f'_radial_profile from {self.center}'
        x_label = f'Radial Distance ({unit})'
        y_label = 'Integrated Intensity (Counts)'
        plot = PlotCanvasSpectrum(calibrated_x, radial_y, parent=self.parent())
        plot.create_plot(xlabel=x_label, ylabel=y_label, title=preview_name)
        plot.canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name] = plot
        UI_TemCompanion.preview_dict[preview_name].show()

        print(f'Performed radial integration on {self.parent().windowTitle()} from the center: {self.center}.')

        self.handle_cancel()


#==============GPA setting dialog===================================
class gpaSettings(QDialog):
    def __init__(self, masksize, edgesmooth, step, sigma, algorithm, vmin=-0.1, vmax=0.1, parent=None):
        super().__init__(parent)
        self.setWindowTitle('GPA Settings')
        self.masksize = masksize
        self.edgesmooth = edgesmooth
        self.stepsize = step
        self.sigma = sigma
        self.vmin = vmin
        self.vmax = vmax
        self.gpa = algorithm
        
        layout = QVBoxLayout()
        self.standard_radio = QRadioButton("Standard GPA")
        self.standard_radio.toggled.connect(self.enable_settings)
        
        self.adaptive_radio = QRadioButton("Adaptive GPA (SLOW)")
        
        layout.addWidget(self.standard_radio)
        layout.addWidget(self.adaptive_radio)
        
        #self.standardGroup = QGroupBox('Standard GPA Parameters')
        masksize_layout = QHBoxLayout()
        masksize_label = QLabel("Mask radius (px):")
        self.masksize_input = QLineEdit()
        self.masksize_input.setText(str(self.masksize))
        self.masksize_input.setToolTip("The extent around the k vectors used to calculate strains. Smaller mask gives smoothier stain maps but loses spatial resolution and vice versa.")
        self.masksize_input.setFixedSize(50, 20)
        self.masksize_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        masksize_layout.addWidget(masksize_label)
        masksize_layout.addWidget(self.masksize_input)
        layout.addLayout(masksize_layout)
        
        edgesmooth_layout = QHBoxLayout()
        edgesmooth_label = QLabel("Edge smooth (0-1):")
        self.edgesmooth_input = QLineEdit()
        self.edgesmooth_input.setText(str(self.edgesmooth))
        self.edgesmooth_input.setToolTip("The ratio of the outside edge that is smoothed with a cosine function. This is to reduce the edge effect.")
        self.edgesmooth_input.setFixedSize(50, 20)
        self.edgesmooth_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        edgesmooth_layout.addWidget(edgesmooth_label)
        edgesmooth_layout.addWidget(self.edgesmooth_input)
        layout.addLayout(edgesmooth_layout)
        
        layout.addWidget(self.adaptive_radio)
        windowsize_layout = QHBoxLayout()
        windowsize_lable = QLabel("Window size (px):")
        self.windowsize_input = QLineEdit()
        self.windowsize_input.setFixedSize(50, 20)
        self.windowsize_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.windowsize_input.setText(str(self.masksize))
        self.windowsize_input.setToolTip('Window size used for the WFR. The algorithm searches the max value of windowed Fourier transform, "ridge", around the selected k vectors.')
        windowsize_layout.addWidget(windowsize_lable)
        windowsize_layout.addWidget(self.windowsize_input)
        layout.addLayout(windowsize_layout)
        
        step_layout = QHBoxLayout()
        step_lable = QLabel("Step size (px):")
        self.step_input = QLineEdit()
        step = max(self.masksize*2//5, 2)
        self.step_input.setText(str(step))
        self.step_input.setFixedSize(50, 20)
        self.step_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.step_input.setToolTip('Step for the ridge search in WFR algorithm. Smaller step size will significantly increase the processing time.')
        step_layout.addWidget(step_lable)
        step_layout.addWidget(self.step_input)
        layout.addLayout(step_layout)
        
        sigma_layout = QHBoxLayout()
        sigma_lable = QLabel("Sigma:")
        self.sigma_input = QLineEdit()
        self.sigma_input.setText(str(self.sigma))
        self.sigma_input.setFixedSize(50, 20)
        self.sigma_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.sigma_input.setToolTip('The sigma for the Gaussian window used for the Windowed Fourier Transform.')
        sigma_layout.addWidget(sigma_lable)
        sigma_layout.addWidget(self.sigma_input)
        layout.addLayout(sigma_layout)
        
        
        range_layout = QVBoxLayout()
        range_label = QLabel("Limit display range:")
        setrang_layout = QHBoxLayout()
        minlabel = QLabel("min:")
        self.min_input = QLineEdit()
        self.min_input.setText(str(self.vmin))
        self.min_input.setFixedSize(50, 20)
        self.min_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        maxlabel = QLabel("max:")
        self.max_input = QLineEdit()
        self.max_input.setText(str(self.vmax))
        self.max_input.setFixedSize(50, 20)
        self.max_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        setrang_layout.addWidget(minlabel)
        setrang_layout.addWidget(self.min_input)
        setrang_layout.addWidget(maxlabel)
        setrang_layout.addWidget(self.max_input)
        range_layout.addWidget(range_label)
        range_layout.addLayout(setrang_layout)
        layout.addLayout(range_layout)
        
        # Apply button
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.cancel_button = buttons.button(QDialogButtonBox.Cancel)
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.ok_button.clicked.connect(self.handle_ok)
        
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
        if self.gpa == 'standard':
            self.standard_radio.setChecked(True)
        else:
            self.adaptive_radio.setChecked(True)
    
    def enable_settings(self):
        standardgroup = [self.masksize_input, self.edgesmooth_input]
        adaptivegroup = [self.windowsize_input, self.step_input, self.sigma_input]
        if self.standard_radio.isChecked():
            for line in standardgroup:
                line.setEnabled(True)
            for line in adaptivegroup:
                line.setEnabled(False)
        else:
            for line in standardgroup:
                line.setEnabled(False)
            for line in adaptivegroup:
                line.setEnabled(True)
            
        
    def handle_ok(self):
        
        try:
            self.vmin = float(self.min_input.text())
            self.vmax = float(self.max_input.text())
        except:
            QMessageBox.warning(self, 'GPA Settings', 'Invalid display range!')
            return
        if self.vmin > self.vmax:
            QMessageBox.warning(self, 'GPA Settings', 'Invalid display range!')
            return
        
        if self.standard_radio.isChecked():
            self.gpa = 'standard'
            try:
                self.masksize = abs(int(self.masksize_input.text()))
            except:
                QMessageBox.warning(self, 'GPA Settings', 'Mask size must be integer!')
                return
            try:
                self.edgesmooth = float(self.edgesmooth_input.text())
            except:
                QMessageBox.warning(self, 'GPA Settings', 'Smooth factor must be between 0-1!')
                return  
            if self.edgesmooth < 0 or self.edgesmooth > 1:
                QMessageBox.warning(self, 'GPA Settings', 'Smooth factor must be between 0-1!')
                return
        
        if self.adaptive_radio.isChecked():
            self.gpa = 'adaptive'
            try:
                self.masksize = abs(int(self.windowsize_input.text()))
            except:
                QMessageBox.warning(self, 'GPA Settings', 'Window size must be integer!')
                return
            try:
                self.stepsize = int(self.step_input.text())
            except:
                QMessageBox.warning(self, 'GPA Settings', 'Step size must be integer!')
                return
            try:
                self.sigma = abs(float(self.sigma_input.text()))
            except:
                QMessageBox.warning(self, 'GPA Settings', 'Sigma must be a possitive number!')
                return 
            
        
        self.accept()
        
         
#=======================Simple math dialog====================================
class SimpleMathDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Simple Math')
        layout = QVBoxLayout()
        layout1 = QHBoxLayout()
        im1_label = QLabel('Signal 1:')
        self.im1_select = QComboBox()
        img_list = [canvas.canvas.canvas_name for canvas in UI_TemCompanion.preview_dict.values()]
        self.im1_select.addItems(img_list)
        layout1.addWidget(im1_label)
        layout1.addWidget(self.im1_select)
        layout.addLayout(layout1)
        
        layout2 = QHBoxLayout()
        operator_lable = QLabel('Operator:')
        self.operator = QComboBox()
        operator_list = ['Add', 'Subtract', 'Multiply', 'Divide', 'Inverse']  
        self.operator.addItems(operator_list)
        layout2.addWidget(operator_lable)
        layout2.addWidget(self.operator)
        layout.addLayout(layout2)
        
        layout3 = QHBoxLayout()
        im2_label = QLabel('Signal 2:')
        self.im2_select = QComboBox()
        self.im2_select.addItems(img_list)
        layout3.addWidget(im2_label)
        layout3.addWidget(self.im2_select)
        layout.addLayout(layout3)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.handle_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
    def handle_ok(self):
        self.signal1 = self.im1_select.currentText()
        self.signal2 = self.im2_select.currentText()
        self.operation = self.operator.currentText()
        
        self.accept()
        
        
#======================DPC Dialog=============================================
class DPCDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('Reconstruct DPC')
        img_list = [canvas.canvas.canvas_name for canvas in UI_TemCompanion.preview_dict.values()]
        layout = QVBoxLayout()
        self.from4_img = QRadioButton('Reconstruct from quadrant signals A, B, C, and D') 
        self.from4_img.setChecked(True)
        self.from4_img.toggled.connect(self.set_combobox_enable)
        layout.addWidget(self.from4_img)
        imA_label = QLabel('Image A:')
        self.imA = QComboBox()
        imB_label = QLabel('Image B:')
        self.imB = QComboBox()
        imC_label = QLabel('Image C:')
        self.imC = QComboBox()
        imD_label = QLabel('Image D:')
        self.imD = QComboBox()
        self.from4group = [self.imA, self.imB, self.imC, self.imD]
        for combobox in self.from4group:
            combobox.addItems(img_list)
        layout1 = QHBoxLayout()
        layout1.addWidget(imA_label)
        layout1.addWidget(self.imA)
        layout2 = QHBoxLayout()
        layout2.addWidget(imB_label)
        layout2.addWidget(self.imB)
        layout3 = QHBoxLayout()
        layout3.addWidget(imC_label)
        layout3.addWidget(self.imC)
        layout4 = QHBoxLayout()
        layout4.addWidget(imD_label)
        layout4.addWidget(self.imD)
        layout.addLayout(layout1)
        layout.addLayout(layout2)
        layout.addLayout(layout3)
        layout.addLayout(layout4)
        
        self.from2_img = QRadioButton('Reconstruct from DPCx and DPCy')
        layout.addWidget(self.from2_img)
        imX_label = QLabel('DPCx:')
        self.imX = QComboBox()
        self.imX.addItems(img_list)
        imY_label = QLabel('DPCy:')
        self.imY = QComboBox() 
        self.imY.addItems(img_list)
        self.from2group = [self.imX, self.imY]
        layout5 = QHBoxLayout()
        layout5.addWidget(imX_label)
        layout5.addWidget(self.imX)
        layout6 = QHBoxLayout()
        layout6.addWidget(imY_label)
        layout6.addWidget(self.imY)
        layout.addLayout(layout5)
        layout.addLayout(layout6)
        
        layout7 = QHBoxLayout()
        rot_label = QLabel("Scan rotation (degrees):")
        self.rot = QLineEdit()
        self.rot.setText('0')
        self.rot.setToolTip('The angle offset between the quadrant detectors and the scan direction.')
        self.guess_rot_curl = QPushButton('Guess with\n min curl', self)
        self.guess_rot_curl.setToolTip('The DPC signals must be a conservative vector field, so the DPCx and DPCy given by\n the right rotation angle should ideally have zero curls, i.e., dDPCy/dx - dDPCx/dy = 0.')
        self.guess_rot_curl.clicked.connect(self.guess_rotation_min_curl)
        self.guess_rot_contrast = QPushButton('Guess with\n max contrast', self)
        self.guess_rot_contrast.setToolTip('Generally the right rotation angle gives the maximum contrast. However, there\n exist two such angles and one gives the inverse contrast. Pick the one that gives\n the correct phase contrast, e.g., atoms are bright.')
        self.guess_rot_contrast.clicked.connect(self.guess_rotation_max_contrast)
        layout7.addWidget(rot_label)
        layout7.addWidget(self.rot)
        layout7.addWidget(self.guess_rot_curl)
        layout7.addWidget(self.guess_rot_contrast)
        layout.addLayout(layout7)
        
        layout8 = QHBoxLayout()
        hp_label = QLabel('High pass cutoff for iDPC:')
        self.hp_cutoff = QLineEdit()
        self.hp_cutoff.setText('0.02')
        self.hp_cutoff.setToolTip('The cutoff for the high pass filter for iDPC, in fraction of reciprocal space. \nGenerally it must be a small number, e.g., 0.02, to filter out the non-uniform \nbackground while maintaining the crystalline information.')
        layout8.addWidget(hp_label)
        layout8.addWidget(self.hp_cutoff)
        layout.addLayout(layout8)
        
        buttons = QHBoxLayout()
        iDPC = QPushButton('Reconstruct iDPC', self)
        iDPC.clicked.connect(self.reconstruct_iDPC)
        dDPC = QPushButton('Reconstruct dDPC', self)
        dDPC.clicked.connect(self.reconstruct_dDPC)
        cancel_button = QPushButton('Close', self)
        cancel_button.clicked.connect(self.reject)
        cancel_button.setDefault(True)
        buttons.addWidget(iDPC)
        buttons.addWidget(dDPC)
        buttons.addWidget(cancel_button)
        
        layout.addLayout(buttons)
        
        
        self.setLayout(layout)
        self.set_combobox_enable()
        
    def set_combobox_enable(self):
        from4 = self.from4_img.isChecked()
        for box in self.from4group:
            box.setEnabled(from4)
        from2 = self.from2_img.isChecked()
        for box in self.from2group:
            box.setEnabled(from2)
            
    def prepare_images(self):
        if self.from4_img.isChecked():
            imA = self.imA.currentText()
            imB = self.imB.currentText()
            imC = self.imC.currentText()
            imD = self.imD.currentText()
            A = copy.deepcopy(find_img_by_title(imA).canvas.data)
            B = copy.deepcopy(find_img_by_title(imB).canvas.data)
            C = copy.deepcopy(find_img_by_title(imC).canvas.data)
            D = copy.deepcopy(find_img_by_title(imD).canvas.data)
            if A['data'].shape == B['data'].shape and B['data'].shape == C['data'].shape and C['data'].shape == D['data'].shape:
                DPCx = A['data'] - C['data']
                DPCy = B['data'] - D['data']
            else:
                QMessageBox.warning(self,'Error in DPC reconstruction!', 'Sizes of the input images do not match!')
                return None, None, None
        else:
            imX = self.imX.currentText()
            imY = self.imY.currentText()
            A = copy.deepcopy(find_img_by_title(imX).canvas.data)
            B = copy.deepcopy(find_img_by_title(imY).canvas.data)
            if A['data'].shape == B['data'].shape:
                DPCx = A['data']
                DPCy = B['data']
            else:
                QMessageBox.warning(self,'Error in DPC reconstruction!', 'Sizes of the input images do not match!')
                return None, None, None
        return A, DPCx, DPCy
    
    def prepare_current_images(self):
        if self.from4_img.isChecked():
            imA = self.imA.currentText()
            imB = self.imB.currentText()
            imC = self.imC.currentText()
            imD = self.imD.currentText()
            A = find_img_by_title(imA).get_img_dict_from_canvas()
            B = find_img_by_title(imB).get_img_dict_from_canvas()
            C = find_img_by_title(imC).get_img_dict_from_canvas()
            D = find_img_by_title(imD).get_img_dict_from_canvas()
            if A['data'].shape == B['data'].shape and B['data'].shape == C['data'].shape and C['data'].shape == D['data'].shape:
                DPCx = A['data'] - C['data']
                DPCy = B['data'] - D['data']
            else:
                QMessageBox.warning(self,'Error in DPC reconstruction!', 'Sizes of the input images do not match!')
                return None, None, None
        else:
            imX = self.imX.currentText()
            imY = self.imY.currentText()
            A = find_img_by_title(imX).get_img_dict_from_canvas()
            B = find_img_by_title(imY).get_img_dict_from_canvas()
            if A['data'].shape == B['data'].shape:
                DPCx = A['data']
                DPCy = B['data']
            else:
                QMessageBox.warning(self,'Error in DPC reconstruction!', 'Sizes of the input images do not match!')
                return None, None, None
        return A, DPCx, DPCy
        
    def guess_rotation_max_contrast(self):
        _, DPCx, DPCy = self.prepare_current_images()
        if DPCx is None:
            return
        ang1, ang2 = find_rotation_ang_max_contrast(DPCx, DPCy)
        text = f'Two possible rotation angles are {ang1} deg and {ang2} deg. Choose the one that gives the correct contrast!'
        QMessageBox.information(self, 'Rotation angle', text)
        
    def guess_rotation_min_curl(self):
        _, DPCx, DPCy = self.prepare_current_images()
        if DPCx is None:
            return
        ang = find_rotation_ang_min_curl(DPCx, DPCy)
        text = f'The possible rotation angle that gives the minimum curl is {ang} deg.'
        QMessageBox.information(self, 'Rotation angle', text)

    def reconstruct_iDPC(self):
        A, DPCx, DPCy = self.prepare_images()
        if DPCx is None:
            return
        
        iDPC_img = copy.deepcopy(A)
        iDPC_img['data'] = reconstruct_iDPC(DPCx, DPCy, rotation=float(self.rot.text()), cutoff=float(self.hp_cutoff.text()))
        preview_name = self.parent().canvas.canvas_name.split(':')[0] + '_iDPC'
        if self.from4_img.isChecked():
            metadata = f'Reconstructed from {self.imA.currentText()}, {self.imB.currentText()}, {self.imC.currentText()}, and {self.imD.currentText()} by a rotation angle of {self.rot.text()} and high pass filter cutoff of {self.hp_cutoff.text()}.'
        else:
            metadata = f'Reconstructed from {self.imX.currentText()} and {self.imY.currentText()} by a rotation angle of {self.rot.text()} and high pass filter cutoff of {self.hp_cutoff.text()}.'
        self.parent().plot_new_image(iDPC_img, preview_name, metadata=metadata)
        UI_TemCompanion.preview_dict[preview_name].position_window('center')
        
    
    def reconstruct_dDPC(self):
        A, DPCx, DPCy = self.prepare_images()
        if DPCx is None:
            return
            
        dDPC_img = copy.deepcopy(A)
        dDPC_img['data'] = reconstruct_dDPC(DPCx, DPCy, rotation=float(self.rot.text()))
        preview_name = self.parent().canvas.canvas_name.split(':')[0] + '_dDPC'
        if self.from4_img.isChecked():
            metadata = f'Reconstructed from {self.imA.currentText()}, {self.imB.currentText()}, {self.imC.currentText()}, and {self.imD.currentText()} by a rotation angle of {self.rot.text()} and high pass filter cutoff of {self.hp_cutoff.text()}.'
        else:
            metadata = f'Reconstructed from {self.imX.currentText()} and {self.imY.currentText()} by a rotation angle of {self.rot.text()} and high pass filter cutoff of {self.hp_cutoff.text()}.'
        self.parent().plot_new_image(dDPC_img, preview_name, metadata=metadata)
        UI_TemCompanion.preview_dict[preview_name].position_window('center')
        
        
#======================== list reorder dialog =========================
class ListReorderDialog(QDialog):
    def __init__(self, items):
        super().__init__()

        self.ordered_items_idx = []
        self.item_to_index = {item: idx for idx, item in enumerate(items)}
        
        self.setWindowTitle('Reorder image stack')
        self.setGeometry(100, 100, 300, 400)

        # Layout
        layout = QVBoxLayout()

        # QListWidget setup
        self.listWidget = QListWidget(self)
        self.listWidget.setDragDropMode(QListWidget.InternalMove)

        # Add items to the QListWidget
        reordered = sorted(items)
        for item in reordered:
            listItem = QListWidgetItem(item)
            self.listWidget.addItem(listItem)

        # Add QListWidget to the layout
        layout.addWidget(self.listWidget)

        # OK button to confirm and close
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.handle_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        

        # Set the layout for the dialog
        self.setLayout(layout)
    
    def contextMenuEvent(self, event):
        # Check if there is an item at the current mouse position
        item = self.listWidget.itemAt(self.listWidget.mapFromGlobal(event.globalPos()))
        if item:
            # Create context menu
            menu = QMenu(self)
            delete_action = QAction('Delete', self)
            delete_action.triggered.connect(lambda: self.deleteItem(item))
            menu.addAction(delete_action)
            
            move_to_top_action = QAction('Move to Top', self)
            move_to_top_action.triggered.connect(lambda: self.moveToTop(item))
            menu.addAction(move_to_top_action)

            move_to_bottom_action = QAction('Move to Bottom', self)
            move_to_bottom_action.triggered.connect(lambda: self.moveToBottom(item))
            menu.addAction(move_to_bottom_action)

            # Show context menu
            menu.exec_(event.globalPos())

    def deleteItem(self, item):
        # Remove the item from the list widget
        self.listWidget.takeItem(self.listWidget.row(item))
        
    def moveToTop(self, item):
        # Get the row of the current item and remove it
        row = self.listWidget.row(item)
        self.listWidget.takeItem(row)
        # Insert it at the top
        self.listWidget.insertItem(0, item)
    
    def moveToBottom(self, item):
        # Get the row of the current item and remove it
        row = self.listWidget.row(item)
        self.listWidget.takeItem(row)
        # Insert it at the bottom
        self.listWidget.addItem(item) 



    def handle_ok(self):
        for index in range(self.listWidget.count()):
            item_text = self.listWidget.item(index).text()
            original_index = self.item_to_index[item_text]
            self.ordered_items_idx.append(original_index)
            self.accept()        
        
        
         
#========================Batch conversion window ===================
class BatchConverter(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setupUi()
        self.scale_bar = True
        self.files = None
        self.output_dir = None 
        self.get_filter_parameters()
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
        layout.addLayout(layout1)
        layout.addLayout(layout2_1_1)
        layout.addLayout(layout2)
        layout.addLayout(layout3)
        layout.addLayout(layout4)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)

        
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
        self.apply_wf = UI_TemCompanion.apply_wf
        self.apply_absf = UI_TemCompanion.apply_absf
        self.apply_nl = UI_TemCompanion.apply_nl
        self.apply_bw = UI_TemCompanion.apply_bw
        self.apply_gaussian = UI_TemCompanion.apply_gaussian
        
        # Read filter parameters from the main window
        self.filter_parameters = UI_TemCompanion.filter_parameters
        
#===================================================================
# Open file button connected to OpenFile

    def openfile(self):
        self.files, self.filetype = QFileDialog.getOpenFileNames(self,"Select files to be converted:", "",
                                                     "Velox emd Files (*.emd);;TIA ser Files (*.ser);;DigitalMicrograph Files (*.dm3 *.dm4);;Tiff Files (*.tif *.tiff);;Image Formats (*.tif *.tiff *.jpg *.jpeg *.png *.bmp);;Pickle Dictionary Files (*.pkl)")
        if self.files:
            self.output_dir = getDirectory(self.files[0],s='/')
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
            self.output_dir = getDirectory(self.files[0],s='/')
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
            self.output_dir = str(output_dir) + '/'
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
            
            save_metadata = self.metadatacheck.isChecked()

            # A separate thread for file conversion
            self.thread = QThread()

            self.worker = BatchConversionWorker(self.files, self.output_dir,self.f_type, save_metadata=save_metadata, scalebar = self.scale_bar,
                                 apply_wf = self.apply_wf, delta_wf = delta_wf, order_wf = order_wf, cutoff_wf = cutoff_wf,
                                 apply_absf = self.apply_absf, delta_absf = delta_absf, order_absf = order_absf, cutoff_absf = cutoff_absf,
                                 apply_nl = self.apply_nl, N = N, delta_nl = delta_nl, order_nl = order_nl, cutoff_nl = cutoff_nl,
                                 apply_bw = self.apply_bw, order_bw = order_bw, cutoff_bw = cutoff_bw,
                                 apply_gaussian = self.apply_gaussian, cutoff_gaussian = cutoff_gaussian)

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
        # Call the main window method
        UI_TemCompanion.filter_settings()
        
        self.get_filter_parameters()
     


                 

#==================================================================
# Helper functions

from rsciio.emd import file_reader as emd_reader
from rsciio.digitalmicrograph import file_reader as dm_reader
from rsciio.tia import file_reader as tia_reader
from rsciio.tiff import file_reader as tif_reader
from rsciio.tiff import file_writer as tif_writer
from rsciio.image import file_reader as im_reader
from rsciio.mrc import file_reader as mrc_reader
from rsciio.image import file_writer as im_writer
import math

def getDirectory(file, s='.'):
    #Make the working directory and return the path.
    for idx in range(-1, -len(file), -1): 
        if file[idx] == s: #find the file extension and remove it. '/' for parent path
            path = file[:idx] + '/'
            return path
        
def getFileName(file):
    full_name = getDirectory(file)
    full_path = getDirectory(file, s='/')
    f_name = full_name[len(full_path):-1]
    return f_name

def getFileType(file):
    full_name = getDirectory(file)
    file_type = file[len(full_name):]
    return file_type





def apply_filter(img, filter_type, **kwargs):
    filter_dict = {'Wiener': filters.wiener_filter,
                   'ABS': filters.abs_filter,
                   'NL': filters.nlfilter,
                   'BW': filters.bw_lowpass,
                   'Gaussian': filters.gaussian_lowpass
                   }
    if img.ndim == 2:
        # Apply the selected filter only on 2D array
        if filter_type in filter_dict.keys():
            # img = filters.crop_to_square(img)
            
            result = filter_dict[filter_type](img, **kwargs)
            if filter_type in ['Wiener', 'ABS', 'NL']:
                return result[0]
            elif filter_type in ['BW', 'Gaussian']:
                return result
    elif img.ndim == 3:
        # Apply to image stacks
        img_shape = img.shape
        result = np.zeros(img_shape)
        for i in range(img_shape[0]):
            result_i = apply_filter(img[i], filter_type, **kwargs)
            result[i] = result_i
        return result
    else:
        raise ValueError("Unsupported image dimensions")

def apply_filter_on_img_dict(img_dict, *args, **kwargs):
    # Take a image dictionary, apply the filter onto the data, and return the modified dictionary
    data = img_dict['data']
    filtered_data = apply_filter(data, *args, **kwargs)
    img_dict['data'] = filtered_data
    return img_dict

def save_as_tif16(input_file, f_name, output_dir, dtype='int16',
                  apply_wf=False, apply_absf=False, apply_nl=False, apply_bw=False, apply_gaussian=False):
    img = copy.deepcopy(input_file)    

    img['data'] = img['data'].astype(dtype)
        

    # Save unfiltered    
    tif_writer(output_dir + f_name + '.tiff', img)
    
    # Save filtered    
    if apply_wf:
        img['data'] = input_file['wf']
        save_as_tif16(img, f_name + '_WF', output_dir, dtype)
        
    if apply_absf:
        img['data'] = input_file['absf']
        save_as_tif16(img,  f_name + '_ABSF', output_dir, dtype)
        
    if apply_nl:
        img['data'] = input_file['nl']
        save_as_tif16(img, f_name + '_NL', output_dir, dtype)
        
    if apply_bw:
        img['data'] = input_file['bw']
        save_as_tif16(img, f_name + '_BW', output_dir, dtype)
        
    if apply_gaussian:
        img['data'] = input_file['gaussian']
        save_as_tif16(img, f_name + '_Gaussian', output_dir, dtype)
        
       
    
    

def save_with_pil(input_file, f_name, output_dir, f_type, scalebar=True, 
                  apply_wf=False, apply_absf=False, apply_nl=False, apply_bw=False, apply_gaussian=False):
    im_data = norm_img(input_file['data']) * 255
    im = Image.fromarray(im_data.astype('int16'))
    im = im.convert('L')
    if im.size[0] < 128:
        scalebar = False #Remove scalebar for very small images to avoid error
    if scalebar:
        #Add a scale bar
        unit = input_file['axes'][1]['units']
        scale = input_file['axes'][1]['scale']        
        add_scalebar_to_pil(im, scale, unit)       
    im.save(output_dir + f_name + '.' + f_type)
    
    if apply_wf:
        wf = {'data': input_file['wf'], 'axes': input_file['axes'], 'metadata': input_file['metadata']}
        save_with_pil(wf, f_name + '_WF', output_dir, f_type, scalebar=scalebar)
        
    if apply_absf:
        absf = {'data': input_file['absf'], 'axes': input_file['axes'], 'metadata': input_file['metadata']}
        save_with_pil(absf, f_name + '_ABSF', output_dir, f_type, scalebar=scalebar)
        
    if apply_nl:
        nl = {'data': input_file['nl'], 'axes': input_file['axes'], 'metadata': input_file['metadata']}
        save_with_pil(nl, f_name + '_NL', output_dir, f_type, scalebar=scalebar)
        
    if apply_bw:
        bw = {'data': input_file['bw'], 'axes': input_file['axes'], 'metadata': input_file['metadata']}
        save_with_pil(bw, f_name + '_BW', output_dir, f_type, scalebar=scalebar)
        
    if apply_gaussian:
        gaussian = {'data': input_file['gaussian'], 'axes': input_file['axes'], 'metadata': input_file['metadata']}
        save_with_pil(gaussian, f_name + '_Gaussian', output_dir, f_type, scalebar=scalebar)
    

def add_scalebar_to_pil(im, scale, unit):
    '''Add a scalebar to a PIL image'''
    # Handle micrometer sign
    if unit in ['µm', 'um']:
        unit = u'\u03bc' + 'm' # Normal \mu letter 
    im_x, im_y = im.size
    fov_x = im_x * scale
    # Find a good integer length for the scalebar 
    sb_len_float = fov_x / 6 #Scalebar length is about 1/6 of FOV
    # A list of allowed lengths for the scalebar
    sb_lst = [0.1,0.2,0.5,1,2,5,10,20,50,100,200,500,1000,2000,5000]
    # Find the closest value in the list
    sb_len = sorted(sb_lst, key=lambda a: abs(a - sb_len_float))[0]
    sb_len_px = sb_len / scale
    sb_start_x, sb_start_y = (im_x / 12, im_y * 11 / 12) #Bottom left corner from 1/12 of FOV
    draw = ImageDraw.Draw(im)
    sb = (sb_start_x, sb_start_y, sb_start_x + sb_len_px, sb_start_y + im_y/ 80)
    outline_width = round(im_y/300)
    if outline_width == 0:
        outline_width = 1
    draw.rectangle(sb, fill = 'white', outline = 'black', width = outline_width)
    # Add text
    if unit == None:
        unit = 'px'
    text = str(sb_len) + ' ' + unit
    fontsize = int(im_x / 20)
    # Choose a good font according to the os
    if default_font:
        font = ImageFont.truetype(default_font, fontsize)
    else:
        font = ImageFont.load_default(fontsize)

    txt_x, txt_y = (sb_start_x * 1.1, sb_start_y - fontsize * 1.1 - im_y/80)
    # Add outline to the text
    dx = im_x / 800
    draw.text((txt_x-dx, txt_y-dx), text, font=font, fill='black')
    draw.text((txt_x+dx, txt_y-dx), text, font=font, fill='black')
    draw.text((txt_x-dx, txt_y+dx), text, font=font, fill='black')
    draw.text((txt_x+dx, txt_y+dx), text, font=font, fill='black')
    draw.text((txt_x, txt_y), text, font=font, fill='white', anchor=None)  
    

    

def save_file_as(input_file, f_name, output_dir, f_type, **kwargs): 
    apply_wf = kwargs['apply_wf']
    delta_wf = kwargs['delta_wf'] 
    order_wf = kwargs['order_wf']
    cutoff_wf = kwargs['cutoff_wf']
    apply_absf = kwargs['apply_absf']
    delta_absf = kwargs['delta_absf']
    order_absf = kwargs['order_absf']
    cutoff_absf = kwargs['cutoff_absf']
    apply_nl = kwargs['apply_nl'] 
    delta_nl = kwargs['delta_nl'] 
    order_nl = kwargs['order_nl']
    cutoff_nl = kwargs['cutoff_nl'] 
    N = kwargs['N']
    apply_bw = kwargs['apply_bw']
    order_bw = kwargs['order_bw']
    cutoff_bw = kwargs['cutoff_bw']
    apply_gaussian = kwargs['apply_gaussian']
    cutoff_gaussian = kwargs['cutoff_gaussian']    
    scale_bar = kwargs['scalebar']
    #Save images
        

    #Check if the output_dir exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    if apply_wf:
        print(f'Applying Wiener filter to {f_name}...')
        input_file['wf'] = apply_filter(input_file['data'], 'Wiener', 
                                delta=delta_wf, lowpass_order=order_wf, lowpass_cutoff=cutoff_wf)
        
    if apply_absf:
        print(f'Applying ABS filter to {f_name}...')
        input_file['absf'] = apply_filter(input_file['data'], 'ABS',
                                          delta=delta_absf, lowpass_order=order_absf, lowpass_cutoff=cutoff_absf)
        
    if apply_nl:
        print(f'Applying Non-Linear filter to {f_name}...')
        input_file['nl'] = apply_filter(input_file['data'], 'NL', 
                                        N=N, delta=delta_nl, lowpass_order=order_nl, lowpass_cutoff=cutoff_nl)
    if apply_bw:
        print(f'Applying Butterworth low-pass filter to {f_name}...')
        input_file['bw'] = apply_filter(input_file['data'], 'BW',
                                        order = order_bw, cutoff_ratio = cutoff_bw)
        
    if apply_gaussian:
        print(f'Applying Gaussian low-pass filter to {f_name}...')
        input_file['gaussian'] = apply_filter(input_file['data'], 'Gaussian',
                                              cutoff_ratio = cutoff_gaussian)
    if f_type == 'tiff':
        # For tiff format, save directly as 16-bit with calibration, no scalebar
        # No manipulation of data but just set to int16
        if all(i.is_integer() for i in input_file['data'].flat):
            dtype = 'int16'
        else:
            dtype = 'float32'
        save_as_tif16(input_file, f_name, output_dir, dtype=dtype, apply_wf=apply_wf, apply_absf=apply_absf, apply_nl=apply_nl, apply_bw=apply_bw, apply_gaussian=apply_gaussian)

    else:
        if f_type == 'tiff + png':
            if all(i.is_integer() for i in input_file['data'].flat):
                dtype = 'int16'
            else:
                dtype = 'float32'
            save_as_tif16(input_file, f_name, output_dir, dtype=dtype, apply_wf=apply_wf, apply_absf=apply_absf, apply_nl=apply_nl, apply_bw=apply_bw, apply_gaussian=apply_gaussian)
            f_type = 'png'
            
        save_with_pil(input_file, f_name, output_dir, f_type, scalebar=scale_bar, apply_wf=apply_wf, apply_absf=apply_absf, apply_nl=apply_nl, apply_bw=apply_bw, apply_gaussian=apply_gaussian)
        
        
        
def load_file(file, file_type):
 
    #Load emd file:
    if file_type == 'Velox emd Files (*.emd)':
        f = emd_reader(file, select_type = 'images')
 
    #Load dm file:
    elif file_type == 'DigitalMicrograph Files (*.dm3 *.dm4)':
        f = dm_reader(file)
 
    #Load TIA file
    elif file_type == 'TIA ser Files (*.ser)':
        f = tia_reader(file)
        
    #Load tif formats
    elif file_type == 'Tiff Files (*.tif *.tiff)':
        f = tif_reader(file)
        
    
                
    
    #Load MRC TIFF stack
    elif file_type == 'MRC Files (*.mrc)':
        f = mrc_reader(file)
        
    #Load image formats
    elif file_type == 'Image Formats (*.tif *.tiff *.jpg *.jpeg *.png *.bmp)':
        f = im_reader(file)
        for img in f:
            # Only for 2d images
            for ax in img['axes']:
                ax['navigate'] = 'False'
        # If RGB or RGBA image, convert to grayscale
            if np.array(img['data'][0,0].item()).size != 1:
                img['data'] = rgb2gray(img['data'])
                
        
        
    #Load pickle dictionary
    elif file_type == 'Pickle Dictionary Files (*.pkl)':
        with open(file, 'rb') as file:
            f = []
            f.append(pickle.load(file))
            
            
    #Load image series from a folder
    #Will load all the tiff files whose size matches the selected one found in the folder and stack them together
    elif file_type == 'Image Series (*.*)':
        tif_dir = getDirectory(file, s='/')
        f = []
        file_list = []
        ext = getFileType(file)
        # set correct file_type
        if ext == 'emd':
            file_type = 'Velox emd Files (*.emd)'
        elif ext in ['dm3', 'dm4']:
            file_type = 'DigitalMicrograph Files (*.dm3 *.dm4)'
        elif ext == 'ser':
            file_type = 'TIA ser Files (*.ser)'
        elif ext in ['tif', 'tiff']:
            file_type = 'Tiff Files (*.tif *.tiff)'
        elif ext in ['jpg', 'jpeg', 'png', 'bmp']:
            file_type = 'Image Formats (*.tif *.tiff *.jpg *.jpeg *.png *.bmp)'
        elif ext == 'pkl':
            file_type = 'Pickle Dictionary Files (*.pkl)'
        else:
            print('Unsupported file formats for image series!')
            return
        
        # Iterate over all files in the specified directory
        for filename in os.listdir(tif_dir):
            # Check if the file matches the pattern
            if filename.endswith(f'.{ext}'):
                # Construct the full file path
                file_path = os.path.join(tif_dir, filename)
                # Ensure it is a file
                if os.path.isfile(file_path):
                    file_list.append(file_path)
                    
        # A dialog to reorder the loaded images
        stack_list = [getFileName(img_file) for img_file in file_list]
        dialog = ListReorderDialog(stack_list)
        if dialog.exec_() == QDialog.Accepted:
            reorder = dialog.ordered_items_idx
            reordered_file = [file_list[idx] for idx in reorder]
        else:
            return
        
        reordered_img = []
        for img_file in reordered_file:
            try:
                img = load_file(img_file, file_type)  
                reordered_img.append(img[0])
            except Exception as e:
                print(f"Error loading {img_file}: {e} Ignored.")
        
        stack_dict = reordered_img[0]
        img_size = stack_dict['data'].shape
        if len(img_size) != 2:
            print('Invalid image size! Images must be 2-dimensional!')
            return
        stack_array = []
        for img_dict in reordered_img:
            if img_dict['data'].shape == img_size:
                stack_array.append(img_dict['data'])
            else:
                print(f"{img_dict['metadata']['General']['original_filename']} has been skipped due to invalid image size!")
        stack = np.stack(stack_array)
        
        stack_dict['data'] = stack
        # reformat the axes
        z_axis = {'size': stack_dict['data'].shape[0],
                  'index_in_array': 0,
                  'name': 'z',
                  'scale': 1,
                  'offset': 0.0,
                  'units': None,
                  'navigate': True
            }
        stack_dict['axes'].insert(0, z_axis)
        stack_dict['axes'][1]['index_in_array'] = 1
        stack_dict['axes'][2]['index_in_array'] = 2
        f = [stack_dict]
            
    # Validate the content of f
    f_valid = []
    for img_dict in f:
        img_valid = {}
        for key in ['data', 'axes', 'metadata']:
            if key in img_dict.keys():
                img_valid[key] = img_dict[key]
                # ['data', 'axes', 'metadata'] are necessary
            else:
                img_valid = {}
                break
            if img_valid:
                try: 
                    img_valid['original_metadata'] = img_dict['original_metadata']
                    # ['original_metadata'] is optional
                except:
                    pass

        if img_valid:
            f_valid.append(img_valid)   
        
    return f_valid

def rgb2gray(im):
    # Convert numpy array "im" with RGB type to gray. A channel is ignored.
    im_x, im_y = im.shape
    gray = np.zeros((im_x, im_y), dtype='int16')
    for i in range(im_x):
        for j in range(im_y):
            r = im[i,j][0]
            g = im[i,j][1]
            b = im[i,j][2]
            intensity = r * 0.2125 + g * 0.7154 + b * 0.0721
            gray[i,j] = intensity.astype('int16')
    return gray


def convert_file(file, filetype, output_dir, f_type, save_metadata=False, **kwargs):
    #f_type: The file type to be saved. e.g., '.tif', '.png', '.jpg' 
    #
    f_name = getFileName(file)
    
    f = load_file(file, filetype)    
    
    if len(f) != 0: #Valid input containing at least one image
        if f[0]['data'].ndim == 3:
            DCFI = True
        else:
            DCFI = False
    
        if not DCFI:
            #Non DCFI, convert directly
            for img in f:
                try:
                    title = img['metadata']['General']['title']
                except:
                    title = ''
                        
                new_name = f_name + '_' + title
                
                save_file_as(img, new_name, output_dir, f_type=f_type, **kwargs)
                
                if save_metadata:
                    metadata = img['metadata']
                    try:
                        extra_metadata = img['original_metadata']
                        metadata.update(extra_metadata)
                    except Exception as e:
                        print(f"Error reading original metadata: {e}")
                    with open(output_dir + new_name + '.json', 'w') as j_file:
                        json.dump(metadata, j_file, indent=4)
                
                
        else:
            #DCFI images, convert into a folder
            new_dir = output_dir + f_name + '/'
            if not os.path.exists(new_dir):
                os.makedirs(new_dir)
            for img in f:
                data = img['data']
                metadata = img['metadata']
                try:
                    title = img['metadata']['General']['title']
                except:
                    title = ''
                stack_num = img['data'].shape[0] #Number of stacks
                
                #Modify the axes
                axes = img['axes']
                if len(axes) == 3:
                    axes.pop(0)
                    axes[0]['index_in_array'] = 0
                    axes[1]['index_in_array'] = 1
                
                if save_metadata:
                    try:
                        metadata_to_save = metadata.copy()
                        extra_metadata = img['original_metadata']
                        metadata_to_save.update(extra_metadata)
                    except Exception as e:
                        print(f"Error reading original metadata: {e}")
                    with open(new_dir + title + '_metadata.json', 'w') as j_file:
                        json.dump(metadata_to_save, j_file, indent=4)
                
                
                for idx in range(stack_num):
                    new_img = {'data': data[idx],
                               'axes': axes,
                               'metadata': metadata
                        }
                    new_name = title + '_{}'.format(idx)
                    
                    save_file_as(new_img, new_name, new_dir, f_type, **kwargs)

def gamma_correct_lut(lut: np.ndarray, gamma: float) -> np.ndarray:
    """Return a gamma-corrected copy of LUT (Nx4 uint8), where input x in [0,1]
    is remapped by x' = x ** (1/gamma) before sampling the base LUT."""
    try:
        g = float(gamma)
    except Exception:
        g = 1.0
    if g <= 0:
        g = 1.0
    if abs(g - 1.0) < 1e-6:
        return lut

    n = lut.shape[0]
    x = np.linspace(0.0, 1.0, n, dtype=np.float32)
    y = np.power(x, g)  # remapped positions
    idx = y * (n - 1)
    i0 = np.floor(idx).astype(np.int32)
    i1 = np.clip(i0 + 1, 0, n - 1)
    t = (idx - i0).astype(np.float32)[:, None]

    lut_f = lut.astype(np.float32)
    out = (1.0 - t) * lut_f[i0] + t * lut_f[i1]
    return out.astype(np.uint8)
                    

#================Batch Conversion Worker Thread====================================
class BatchConversionWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, files, *args, **kwargs):
        super().__init__()
        self.files = files
        self.args = args
        self.kwargs = kwargs

    def run(self):
        for file in self.files:
            # Identify the file types
            msg = f"Converting '{file}'..."
            self.progress.emit(msg)

            ext = getFileType(file)
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
                QMessageBox.warning(self, 'Open File', 'Unsupported file formats!')
                return

            try:
                convert_file(file, filetype, *self.args, **self.kwargs)

                msg = f"'{file}' has been converted"
                self.progress.emit(msg)

            except Exception as e:
                msg = f"'{file}' has been skipped. Error: {e}"
                self.progress.emit(msg)

        self.finished.emit()

def calculate_angle_from_3_points(A, B, C):
    '''
    Calculate the <ABC when their coordinates are given
    '''
    # A, B, C are the coordinates of the points (x, y)
    # Vector AB
    AB = (B[0] - A[0], B[1] - A[1])
    # Vector BC
    BC = (C[0] - B[0], C[1] - B[1])

    # Dot product of AB and BC
    dot_product = AB[0] * BC[0] + AB[1] * BC[1]

    # Magnitude of AB and BC
    magnitude_AB = math.sqrt(AB[0]**2 + AB[1]**2)
    magnitude_BC = math.sqrt(BC[0]**2 + BC[1]**2)

    # Cosine of the angle
    cos_theta = dot_product / (magnitude_AB * magnitude_BC)

    # Angle in radians
    angle_rad = math.acos(cos_theta)

    # Angle in degrees
    angle_deg = math.degrees(angle_rad)

    return angle_deg

def calculate_angle_to_horizontal(A, B):
    '''
    Calculate the angle of A, B and x direction  
    '''
    y = B[1] - A[1]
    x = B[0] - A[0]
    if x == 0:
        if y > 0:
            ang = -90
        else:
            ang = 90
        return ang
    ang_rad = math.atan((B[1]-A[1])/(B[0]-A[0]))
    ang = math.degrees(ang_rad)  
    
    # Reformat the angle to be -180 to 180
    if x >0 and y>0:
        return -1 * ang
    if x>0 and y<0:
        return -1 * ang
    if x<0 and y>0:
        return -180 - ang
    if x<0 and y<0:
        return 180 - ang
    
    
    return ang

def measure_distance(A, B, scale=1):
    x0, y0 = A
    x1, y1 = B
    distance_pixels = np.sqrt((x1 - x0)**2 + (y1 - y0)**2)
    distance_units = distance_pixels * scale
    return distance_units

def closer_point(p0, p1, p2):
    # Calculate the Euclidean distance from p0 to p1
    distance_p1 = measure_distance(p0, p1)
    
    # Calculate the Euclidean distance from p0 to p2
    distance_p2 = measure_distance(p0, p2)
    
    # Determine which point is closer to p0 and return it
    if distance_p1 < distance_p2:
        return p1, p2
    else:
        return p2, p1

def line(p1, p2):
    '''
    Find a line function from two points
    Return k ,b in the form of y = kx + b
    '''
    A = (p2[1] - p1[1])
    B = (p2[0] - p1[0])
    k = A /B   
    return k, -k * p1[0] + p1[1]    




def find_img_by_title(title):
    for canvas in UI_TemCompanion.preview_dict.values():
        if canvas.canvas.canvas_name == title:
            return canvas

def find_system_font():
    if os.name == 'nt': # Windows
        font_path = os.path.join(os.environ['SystemRoot'], 'Fonts', 'segoeui.ttf')
        if os.path.exists(font_path):
            return font_path

    elif os.name == 'posix':
        if 'Darwin' in os.uname().sysname:  # macOS
            font_paths = ['/System/Library/Fonts/SFNS.ttf', '/System/Library/Fonts/SFNSDisplay.ttf']
            for path in font_paths:
                if os.path.exists(path):
                    return path
        else:
            font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSans.ttf']
            
            for path in font_paths:
                if os.path.exists(path):
                    return path
                   
#====Application entry==================================
# Splash screen for windows app
# import pyi_splash

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
default_font = find_system_font()




# Update the text on the splash screen
# pyi_splash.update_text("Loading...")


# Close the splash screen. It does not matter when the call
# to this function is made, the splash screen remains open until
# this function is called or the Python program is terminated.
# pyi_splash.close()

def main():    
    app = QApplication(sys.argv)
    
    # Setup window icon for windows app
    # if getattr(sys, 'frozen', False):
    #     applicationPath = sys._MEIPASS
    # elif __file__:
    #     applicationPath = os.path.dirname(__file__)
    # app.setWindowIcon(QIcon(os.path.join(applicationPath, "Icon.ico")))
    
    
    temcom = UI_TemCompanion()
    temcom.show()
    temcom.raise_()
    temcom.activateWindow()
    sys.exit(app.exec_())
    


if __name__ == "__main__":
    main()
    

    
