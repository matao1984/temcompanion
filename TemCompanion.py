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

from PyQt5 import QtCore, QtWidgets

from PyQt5.QtWidgets import (QApplication, QMainWindow, QListView, QVBoxLayout, 
                             QWidget, QPushButton, QMessageBox, QFileDialog, 
                             QDialog, QAction, QHBoxLayout, QLineEdit, QLabel, 
                             QComboBox, QInputDialog, QCheckBox, QGroupBox, 
                             QFormLayout, QDialogButtonBox,  QTreeWidget, QTreeWidgetItem,
                             QSlider, QStatusBar, QMenu, QTextEdit, QSizePolicy, QRadioButton,
                             QListWidget, QListWidgetItem, QButtonGroup
                             )
from PyQt5.QtCore import Qt, QStringListModel, QObject, pyqtSignal
from PyQt5.QtGui import QImage, QIcon, QDropEvent, QDragEnterEvent
from superqt import QDoubleRangeSlider

import sys
import os
import io

import numpy as np
import copy

from scipy.ndimage import center_of_mass

import pickle
import json

from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from matplotlib.figure import Figure
from matplotlib_scalebar.scalebar import ScaleBar
from matplotlib.widgets import Slider, RectangleSelector, SpanSelector
from matplotlib.patches import Circle
from matplotlib.colors import LinearSegmentedColormap

from hrtem_filter import filters
from scipy.fft import fft2, fftshift, ifft2, ifftshift, fftfreq
from skimage.filters import window
from skimage.measure import profile_line
from scipy.ndimage import rotate, shift, fourier_gaussian
from skimage.registration import phase_cross_correlation, optical_flow_ilk
from skimage.transform import warp, rescale, resize


ver = '1.2.6'
rdate = '2025-05-01'

#===================Redirect output to the main window===============================
# Custom stream class to capture output
class EmittingStream(QObject):
    text_written = pyqtSignal(str)  # Signal to emit text

    def write(self, text):
        self.text_written.emit(str(text))  # Emit the text

    def flush(self):
        pass  # Required for compatibility with sys.stdout
        

        
   
        

        
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
                self.preview_dict[plot].close()
        
        if self.converter is not None and self.converter.isVisible():
            self.converter.close()
        

        
    # Define filter parameters as class variables        
    apply_wf, apply_absf, apply_nl, apply_bw, apply_gaussian = False, False, False, False, False
    filter_parameters_default = {"WF Delta": "5", "WF Bw-order": "4", "WF Bw-cutoff": "0.3",
                                 "ABSF Delta": "5", "ABSF Bw-order": "4", "ABSF Bw-cutoff": "0.3",
                                 "NL Cycles": "10", "NL Delta": "10", "NL Bw-order": "4", "NL Bw-cutoff": "0.3",
                                 "Bw-order": "4", "Bw-cutoff": "0.3",
                                 "GS-cutoff": "0.3"}

    filter_parameters = filter_parameters_default.copy()
    
    #Preview dict as class variable
    preview_dict = {}


    def setupUi(self):
        
        self.setObjectName("TemCompanion")
        self.setWindowTitle(f"TemCompanion Ver {ver}")
        self.resize(400, 300)
        
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
        
        
        self.outputBox = QTextEdit(self, readOnly=True)
        #self.outputBox.setGeometry(35, 90, 350, 210)
        self.outputBox.resize(350, 210)
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
        print('='*42)
        print('''
        TemCompanion 
--- a convenient tool to view, edit, filter, and convert TEM image files to tiff, png, and jpg.     
Address your questions and suggestions to matao1984@gmail.com.
See the "About" for more details. Buy me a lunch if you like it!
              ''')
                    
        print('          Version: ' + ver + ' Released: ' + rdate)
        print('='*42)

        
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
        
                        
                    if img['data'].ndim == 2:  
                        
                        preview_im = PlotCanvas(img, parent=self)
                        
                        
        
                    elif img['data'].ndim == 3:
                        # Modify the axes to be aligned with the save functions
                        # Backup the original axes
                        if 'original_axes' not in img.keys():
                            img['original_axes'] = copy.deepcopy(img['axes'])
                            img['axes'].pop(0)
                            img['axes'][0]['index_in_array'] = 0
                            img['axes'][1]['index_in_array'] = 1
                        
                        preview_im = PlotCanvas3d(img, parent=self)
                    else:
                        QMessageBox.warning(self,'Load file error','Cannot preview the file(s). Currently, only 2D and 3D data are supported!')
                        return
                        
                    
                    preview_im.setWindowTitle(preview_name)
                    preview_im.canvas.canvas_name = preview_name
                    self.preview_dict[preview_name] = preview_im
                    
                    self.preview_dict[preview_name].show() 
                    self.preview_dict[preview_name].position_window('center')
                    
                    print(f'Opened successfully: {f_name + ": " + title}.')
                except:
                    print(f'Opened unsuccessful: {f_name + ": " + title}.')
        except:
            print(f'Cannot open {self.file}, make sure it is not in use or corrupted!')
            return  
        
        
        finally:    
            f = None
            
            
#=========== Define figure canvas for preview ===================================================
class PlotCanvas(QMainWindow):
    def __init__(self, img, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        
        
        
        self.img_size = img['data'].shape
              
        # Create main frame for image
        self.main_frame = QWidget()
        self.aspect_ratio = self.img_size[-2]/self.img_size[-1]
        fig_x = 4
        fig_y = fig_x * self.aspect_ratio
        self.fig = Figure((fig_x, fig_y),dpi=150) 
        self.axes = self.fig.add_subplot(111)
        self.axes.set_title('Image')
        self.axes.title.set_visible(False)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.main_frame)
        sizepolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        self.canvas.setSizePolicy(sizepolicy)
        # Attach the image dict to canvas
        self.canvas.data = img
        
               
        
        # Set the click to focus to receive key press event
        self.canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
        self.canvas.setFocus()
        

        
        
        
        # Default settings for scale bar
        self.scalebar_settings = {'scalebar': True,
                                  'color': 'yellow',
                                  'location': 'lower left',
                                  'scale_loc': 'top',
                                  'sep': 2}
        self.scalebar = None
        self.colorbar = None
        
        # Variables for the measure function
        self.line = None
        self.start_point = None
        self.end_point = None
        self.active_point = None
        self.inactive_point = None
        self.background = None
        
        # Connect zoom/pan events
        self.zoom_cid = self.fig.canvas.mpl_connect('draw_event', self.update_background)
        
        self.canvas.img_idx = None  # For 3d slicing
        self.selector = None # For cropping
        
        self.text = None # Measurement result text
        
        self.linewidth = 1 # Default linewidth for line profile
        self.marker = None 
        self.center_marker = None # Center marker for diffraction pattern
        self.center = self.img_size[1] // 2, self.img_size[0] // 2
        
        self.mask_list = []
        self.sym_mask_list = []
        
        # Measurement mode control all in a dictionary
        self.mode_control = {'measurement': False,
                             'lineprofile': False,
                             'measure_fft': False,
                             'mask': False,
                             'Live_FFT': False,
                             'GPA': False
            }

        # Connect event handlers
        self.button_press_cid = None
        self.button_release_cid = None
        self.motion_notify_cid = None
        self.scroll_event_cid = None
        
        # All the push buttons
        self.buttons = {'crop_ok': None,
                        'crop_cancel': None,
                        'distance_finish': None}
        
        self.distance_fft = 0
        self.ang = 0
        
        
        try:
            self.process = copy.deepcopy(self.canvas.data['metadata']['process'])
        except:
            self.process = {'software': 'TemCompanion v{}'.format(ver),
                            'process': []}
            # Keep history in the metadata
            self.canvas.data['metadata']['process'] = self.process
        
        
        # Create the navigation toolbar, tied to the canvas
        self.mpl_toolbar = CustomToolbar(self.canvas, parent=self)        
        vbox = QVBoxLayout()
        vbox.addWidget(self.mpl_toolbar)
        vbox.addWidget(self.canvas)
        self.main_frame.setLayout(vbox)
        self.setCentralWidget(self.main_frame)
        
        # Create figure and menubar
        self.create_img()
        self.update_background()
        self.create_menubar()
        
        # Create a status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Display a message in the status bar
        self.statusBar.showMessage("Ready")
        
        # Right click menu
        self.main_frame.setContextMenuPolicy(Qt.CustomContextMenu)
        self.main_frame.customContextMenuRequested.connect(self.show_context_menu)
        

        
    def closeEvent(self, event):
        self.canvas.data = None
        UI_TemCompanion.preview_dict.pop(self.canvas.canvas_name, None)
    
    def resizeEvent(self, event):
        # width = event.size().width()
        # height = event.size().height()
        width = self.canvas.size().width()
        height = self.canvas.size().height()

        # Calculate new sizes preserving aspect ratio
        if width * self.aspect_ratio > height:
            # Height is the limiting factor
            fig_height = height
            fig_width = int(height / self.aspect_ratio)
        else:
            # Width is the limiting factor
            fig_width = width
            fig_height = int(width * self.aspect_ratio)

        self.canvas.resize(fig_width, fig_height)
        
    
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
            
        
    
        

       
    def create_menubar(self):
        menubar = self.menuBar()  # Create a menu bar

        # File menu and actions
        file_menu = menubar.addMenu('&File')
        save_action = QAction('&Save as', self)
        save_action.setShortcut('ctrl+s')
        save_action.triggered.connect(self.mpl_toolbar.save_figure)
        file_menu.addAction(save_action)
        copy_action = QAction('&Copy Image to Clipboard', self)
        copy_action.setShortcut('ctrl+alt+c')
        copy_action.triggered.connect(self.copy_img)
        file_menu.addAction(copy_action)
        imagesetting_action = QAction('&Image Settings',self)
        imagesetting_action.setShortcut('ctrl+o')
        imagesetting_action.triggered.connect(self.mpl_toolbar.edit_parameters)
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
        
        
        # Analyze menu and actions
        analyze_menu = menubar.addMenu('&Analyze')
        setscale_action = QAction('Set Scale', self)
        setscale_action.triggered.connect(self.setscale)
        analyze_menu.addAction(setscale_action)
        measure_action = QAction('&Measure', self)
        measure_action.setShortcut('ctrl+m')
        measure_action.triggered.connect(self.measure)
        analyze_menu.addAction(measure_action)
        measure_fft_action = QAction('&Measure Diffraction/FFT', self)
        measure_fft_action.setShortcut('ctrl+shift+m')
        measure_fft_action.triggered.connect(self.measure_fft)        
        analyze_menu.addAction(measure_fft_action)        
        lineprofile_action = QAction('&Line Profile', self)
        lineprofile_action.setShortcut('ctrl+l')
        lineprofile_action.triggered.connect(self.lineprofile)
        analyze_menu.addAction(lineprofile_action)
        gpa_action = QAction('Geometric Phase Analysis', self)
        gpa_action.triggered.connect(self.gpa)
        analyze_menu.addAction(gpa_action)
        dpc_action = QAction('Reconstruct DPC', self)
        dpc_action.triggered.connect(self.dpc)
        analyze_menu.addAction(dpc_action)
        

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
        gaussian_action.triggered.connect(self.gaussion_filter)
        filter_menu.addAction(gaussian_action)

        # Info menu
        info_menu = menubar.addMenu('&Info')
        axes_action = QAction('Image Axes', self)
        axes_action.triggered.connect(self.show_axes)
        info_menu.addAction(axes_action)
        info_action = QAction('&View Metadata', self)
        info_action.setShortcut('ctrl+i')
        info_action.triggered.connect(self.show_info)
        info_menu.addAction(info_action)
        about_action = QAction('About', self)
        about_action.triggered.connect(UI_TemCompanion.show_about)
        info_menu.addAction(about_action)
        
        self.menubar = menubar
        
    def show_context_menu(self, pos):
        context_menu = QtWidgets.QMenu(self)
        
        # File menu
        file_menu = context_menu.addMenu('File')
        save_action = QAction('Save as')
        save_action.triggered.connect(self.mpl_toolbar.save_figure)
        file_menu.addAction(save_action)
        copy_action = QAction('Copy Image to Clipboard')
        copy_action.triggered.connect(self.copy_img)
        file_menu.addAction(copy_action)
        imagesetting_action = QAction('Image Settings')
        imagesetting_action.triggered.connect(self.mpl_toolbar.edit_parameters)
        file_menu.addAction(imagesetting_action)
        close_action = QAction('Close')
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)
        
        # Edit menu and actions
        edit_menu = context_menu.addMenu('Process')
        crop_action = QAction('Crop')
        crop_action.triggered.connect(self.crop)
        edit_menu.addAction(crop_action)
        rotate_action = QAction('Rotate')
        rotate_action.triggered.connect(self.rotate)
        edit_menu.addAction(rotate_action)
        fliplr_action = QAction('Flip horizontal')
        fliplr_action.triggered.connect(self.flip_horizontal)
        edit_menu.addAction(fliplr_action)
        flipud_action = QAction('Flip vertical',self)
        flipud_action.triggered.connect(self.flip_vertical)
        edit_menu.addAction(flipud_action)
        resampling_action = QAction('Resampling')
        resampling_action.triggered.connect(self.resampling)
        edit_menu.addAction(resampling_action)
        simplemath_action = QAction('Simple math', self)
        simplemath_action.triggered.connect(self.simplemath)
        edit_menu.addAction(simplemath_action)
        
        # FFT menu
        fft_menu = context_menu.addMenu('FFT')
        fft_action = QAction('FFT')
        fft_action.triggered.connect(self.fft)
        fft_menu.addAction(fft_action)
        windowedfft_action = QAction('Windowed FFT')
        windowedfft_action.triggered.connect(self.windowedfft)
        fft_menu.addAction(windowedfft_action)
        livefft_action = QAction('Live FFT')
        livefft_action.triggered.connect(self.live_fft)
        fft_menu.addAction(livefft_action)
        
        
        # Analyze menu and actions
        analyze_menu = context_menu.addMenu('Analyze')
        setscale_action = QAction('Set Scale')
        setscale_action.triggered.connect(self.setscale)
        analyze_menu.addAction(setscale_action)
        measure_action = QAction('Measure')
        measure_action.triggered.connect(self.measure)
        analyze_menu.addAction(measure_action)
        measure_fft_action = QAction('Measure Diffraction/FFT')
        measure_fft_action.triggered.connect(self.measure_fft)        
        analyze_menu.addAction(measure_fft_action)        
        lineprofile_action = QAction('Line Profile')
        lineprofile_action.triggered.connect(self.lineprofile)
        analyze_menu.addAction(lineprofile_action)
        gpa_action = QAction('Geometric Phase Analysis')
        gpa_action.triggered.connect(self.gpa)
        analyze_menu.addAction(gpa_action)
        
        

        # Filter menu and actions
        filter_menu = context_menu.addMenu('Filter')
        filtersetting_action = QAction('Filter Settings')
        filtersetting_action.triggered.connect(UI_TemCompanion.filter_settings)
        filter_menu.addAction(filtersetting_action)
        
        wiener_action = QAction('Apply Wiener')
        wiener_action.triggered.connect(self.wiener_filter)
        filter_menu.addAction(wiener_action)
        absf_action = QAction('Apply ABSF')
        absf_action.triggered.connect(self.absf_filter)
        filter_menu.addAction(absf_action)
        non_linear_action = QAction('Apply Non-Linear')
        non_linear_action.triggered.connect(self.non_linear_filter)
        filter_menu.addAction(non_linear_action)
        bw_action = QAction('Apply Butterworth low pass')
        bw_action.triggered.connect(self.bw_filter)
        filter_menu.addAction(bw_action)
        gaussian_action = QAction('Apply Gaussian low pass')
        gaussian_action.triggered.connect(self.gaussion_filter)
        filter_menu.addAction(gaussian_action)

        # Info menu
        info_menu = context_menu.addMenu('Info')
        axes_action = QAction('Image Axes')
        axes_action.triggered.connect(self.show_axes)
        info_menu.addAction(axes_action)
        info_action = QAction('View Metadata')
        info_action.triggered.connect(self.show_info)
        info_menu.addAction(info_action)
        

        context_menu.exec_(self.mapToGlobal(pos))
        
        
        
    def get_current_img_from_canvas(self):
        current_ax = self.canvas.figure.get_axes()[0]
        current_img = current_ax.get_images()[0]._A
        return current_img
        
    def get_img_dict_from_canvas(self):
        # Return the current image together with the full dictionary
        current_img = self.get_current_img_from_canvas()
        img_dict = copy.deepcopy(self.canvas.data)
        img_dict['data'] = current_img
        return img_dict
    
    def close_all(self):
        plots = list(UI_TemCompanion.preview_dict.keys())
        for plot in plots:
            UI_TemCompanion.preview_dict[plot].close()
        
    
    def crop(self):
        ax = self.canvas.figure.get_axes()[0]
        # Display a message in the status bar
        self.statusBar.showMessage("Drag a rectangle to crop. Hold Shift to draw a square.")
        

        
        if self.selector is None:
            self.selector = RectangleSelector(ax, onselect=self.on_select, interactive=True, useblit=True,
                                              drag_from_anywhere=True, use_data_coordinates=True,
                                              minspanx=5, minspany=5,
                                              button=[1]
                                              )
            
            # Crop button
            self.buttons['crop_ok'] = QPushButton('OK', parent=self.canvas)
            self.buttons['crop_ok'].move(30, 30)
            self.buttons['crop_ok'].clicked.connect(self.confirm_crop)
           
            self.buttons['crop_cancel'] = QPushButton('Cancel', parent=self.canvas)
            self.buttons['crop_cancel'].move(100,30)
            self.buttons['crop_cancel'].clicked.connect(self.cancel_crop)
            
            self.buttons['crop_input'] = QPushButton(('Manual input'), parent=self.canvas)
            self.buttons['crop_input'].move(170,30)
            self.buttons['crop_input'].clicked.connect(self.manual_crop)
            
            
            self.selector.set_active(True)
            # Show buttons
            for value in self.buttons.values():
                if value is not None:
                    value.show()
            
            self.fig.canvas.draw_idle()

    def on_select(self, eclick, erelease):
        pass  # handle the crop in the confirm_crop function

    def manual_crop(self):
        if self.selector is not None:
            dialog = ManualCropDialog(parent=self)
           
            if dialog.exec_() == QDialog.Accepted:
                x0, x1 = dialog.x_range
                y0, y1 = dialog.y_range
                self.selector.extents = x0, x1, y0, y1


    def confirm_crop(self):
        if self.selector is not None and self.selector.active:
            x0, x1, y0, y1 = self.selector.extents
            if abs(x1 - x0) > 5 and abs(y1 - y0) > 5: 
                # Valid area is selected               
                img = self.get_img_dict_from_canvas()
                cropped_img = img['data'][int(y0):int(y1), int(x0):int(x1)]                
                img['data'] = cropped_img
                
                # Update axes size
                img['axes'][0]['size'] = img['data'].shape[0]
                img['axes'][1]['size'] = img['data'].shape[1]
                
                
                # Create a new PlotCanvas to display
                title = self.windowTitle()
                preview_name = self.canvas.canvas_name + '_cropped'
                UI_TemCompanion.preview_dict[preview_name] = PlotCanvas(img, parent=self.parent())
                UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
                UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
                UI_TemCompanion.preview_dict[preview_name].show()
                
                # Positioning
                self.position_window('center left')
                UI_TemCompanion.preview_dict[preview_name].position_window('center right')
                
                print('Cropped {} by {}:{}, {}:{}'.format(title, int(x0), int(x1),int(y0), int(y1)))
                
                # Write process history in the original_metadata
                UI_TemCompanion.preview_dict[preview_name].process['process'].append('Cropped by {}:{}, {}:{} from the original image'.format(int(x0),int(x1),int(y0),int(y1)))
                UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
                
            self.selector.set_active(False)
            self.selector.set_visible(False)
            self.selector.disconnect_events()  # Disconnect event handling
            self.selector = None  
            # Reset buttons
            for value in self.buttons.values():
                if value is not None:
                    value.hide()
                    value = None
            
            # Display a message in the status bar
            self.statusBar.showMessage("Ready")
            self.fig.canvas.draw_idle()
            
    
    def cancel_crop(self):
        if self.selector is not None:
            self.selector.set_active(False)
            self.selector.set_visible(False)
            self.selector.disconnect_events()  # Disconnect event handling
            self.selector = None  
            
        for value in self.buttons.values():
            if value is not None:
                value.hide()
                value = None
        
        # Display a message in the status bar
        self.statusBar.showMessage("Ready")
        self.fig.canvas.draw_idle()
    





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
            UI_TemCompanion.preview_dict[preview_name].process['process'].append('Rotated by {} degrees from the original image'.format(ang))
            UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
    
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
        UI_TemCompanion.preview_dict[preview_name].process['process'].append('Flipped horizontally')
        UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
        
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
        UI_TemCompanion.preview_dict[preview_name].process['process'].append('Flipped vertically')
        UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)


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
            UI_TemCompanion.preview_dict[preview_name] = PlotCanvas(img, parent=self.parent())
            UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
            UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
            UI_TemCompanion.preview_dict[preview_name].show()
            
            print(f'Resampled {title} by a factor of {rescale_factor}.')
            
            # Positioning
            self.position_window('center left')
            UI_TemCompanion.preview_dict[preview_name].position_window('center right')
            
            # Keep the history
            UI_TemCompanion.preview_dict[preview_name].process['process'].append(f'Resampled by a factor of {rescale_factor}.')
            UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)



            
    def copy_img(self):
        buf = io.BytesIO()
        figsize = self.canvas.figure.get_size_inches()
        img_size = self.get_current_img_from_canvas().shape
        dpi = float(sorted(img_size/figsize, reverse=True)[0])
        # Hide other elements
        if len(self.canvas.figure.axes) != 1:
            self.canvas.figure.axes[1].set_visible(False)
        
        self.canvas.figure.savefig(buf, dpi=dpi)
        
        
        self.clipboard = QApplication.clipboard().setImage(QImage.fromData(buf.getvalue()))
        buf.close()
        if len(self.canvas.figure.axes) != 1:
            self.canvas.figure.axes[1].set_visible(True)
        
        
        self.statusBar.showMessage("The current image has been copied to the clipboard!")
        self.fig.canvas.draw_idle()

    def wiener_filter(self):
        
        filter_parameters = UI_TemCompanion.filter_parameters        
        delta_wf = int(filter_parameters['WF Delta'])
        order_wf = int(filter_parameters['WF Bw-order'])
        cutoff_wf = float(filter_parameters['WF Bw-cutoff'])
        img_wf = self.get_img_dict_from_canvas()
        title = self.windowTitle()
        wf = apply_filter(img_wf['data'], 'Wiener', delta=delta_wf, lowpass_order=order_wf, lowpass_cutoff=cutoff_wf)
        img_wf['data'] = wf
        preview_name = self.canvas.canvas_name + '_Wiener Filtered'
        
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvas(img_wf, parent=self.parent())
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].show()
        
        print(f'Applied Wiener filter to {title} with delta = {delta_wf}, Bw-order = {order_wf}, Bw-cutoff = {cutoff_wf}.')
        # Positioning
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
        # Keep the history
        UI_TemCompanion.preview_dict[preview_name].process['process'].append('Wiener filter applied with delta = {}, Bw-order = {}, Bw-cutoff = {}'.format(delta_wf,order_wf,cutoff_wf))
        UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
        

    def absf_filter(self):
        filter_parameters = UI_TemCompanion.filter_parameters        
        delta_absf = int(filter_parameters['ABSF Delta'])
        order_absf = int(filter_parameters['ABSF Bw-order'])
        cutoff_absf = float(filter_parameters['ABSF Bw-cutoff'])
        img_absf = self.get_img_dict_from_canvas()
        title = self.windowTitle()
        absf = apply_filter(img_absf['data'], 'ABS', delta=delta_absf, lowpass_order=order_absf, lowpass_cutoff=cutoff_absf)
        img_absf['data'] = absf
        preview_name = self.canvas.canvas_name + '_ABS Filtered'
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvas(img_absf, parent=self.parent())
               
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].show()
        
        # Print results output
        msg = f'ABS filter to {title} with delta = {delta_absf}, Bw-order = {order_absf}, Bw-cutoff = {cutoff_absf}.'
        print(msg)
        
        # Positioning
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
        # Keep the history
        UI_TemCompanion.preview_dict[preview_name].process['process'].append('ABS filter applied with delta = {}, Bw-order = {}, Bw-cutoff = {}'.format(delta_absf,order_absf,cutoff_absf))
        UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
        

    
    def non_linear_filter(self):
        filter_parameters = UI_TemCompanion.filter_parameters        
        delta_nl = int(filter_parameters['NL Delta'])
        order_nl = int(filter_parameters['NL Bw-order'])
        cutoff_nl = float(filter_parameters['NL Bw-cutoff'])
        N = int(filter_parameters['NL Cycles'])
        img_nl = self.get_img_dict_from_canvas()
        title = self.windowTitle()
        nl = apply_filter(img_nl['data'], 'NL', N=N, delta=delta_nl, lowpass_order=order_nl, lowpass_cutoff=cutoff_nl)
        img_nl['data'] = nl
        preview_name = self.canvas.canvas_name + '_NL Filtered'
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvas(img_nl, parent=self.parent())
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].show()
        
        # Print results output
        msg = f'Applied Non-Linear filter to {title} with N = {N}, delta = {delta_nl}, Bw-order = {order_nl}, Bw-cutoff = {cutoff_nl}.'
        print(msg)
        
        # Positioning
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')

        
        # Keep the history
        UI_TemCompanion.preview_dict[preview_name].process['process'].append('Nonlinear filter applied with N= {}, delta = {}, Bw-order = {}, Bw-cutoff = {}'.format(N,delta_nl,order_nl,cutoff_nl))
        UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
        
    def bw_filter(self):
        filter_parameters = UI_TemCompanion.filter_parameters        
        order_bw = int(filter_parameters['Bw-order'])
        cutoff_bw = float(filter_parameters['Bw-cutoff'])
        img_bw = self.get_img_dict_from_canvas()
        title = self.windowTitle()
        bw = apply_filter(img_bw['data'], 'BW', order=order_bw, cutoff_ratio=cutoff_bw)
        img_bw['data'] = bw
        preview_name = self.canvas.canvas_name + '_Bw Filtered'
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvas(img_bw, parent=self.parent())
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].show()
        
        print(f'Applied Butterworth filter to {title} with Bw-order = {order_bw}, Bw-cutoff = {cutoff_bw}.')
        
        # Positioning
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
        # Keep the history
        UI_TemCompanion.preview_dict[preview_name].process['process'].append('Butterworth filter applied with Bw-order = {}, Bw-cutoff = {}'.format(order_bw,cutoff_bw))
        UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
    
    def gaussion_filter(self):
        filter_parameters = UI_TemCompanion.filter_parameters        
        cutoff_gaussian = float(filter_parameters['GS-cutoff'])
        img_gaussian = self.get_img_dict_from_canvas()
        title = self.windowTitle()
        gaussian = apply_filter(img_gaussian['data'], 'Gaussian', cutoff_ratio=cutoff_gaussian)
        img_gaussian['data'] = gaussian
        preview_name = self.canvas.canvas_name + '_Gaussian Filtered'
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvas(img_gaussian,parent=self.parent())
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].show()
        
        print(f'Applied Gaussian filter to {title} with cutoff = {cutoff_gaussian}.')
        # Positioning
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
        
        # Keep the history
        UI_TemCompanion.preview_dict[preview_name].process['process'].append('Gaussian filter applied with cutoff = {}'.format(cutoff_gaussian))
        UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
    
    
    def create_img(self):
        
        self.im = self.axes.imshow(self.canvas.data['data'], cmap='gray')
        self.axes.set_axis_off()
        # Add scale bar 
        self.scale = self.canvas.data['axes'][1]['scale']
        self.units = self.canvas.data['axes'][1]['units'] 
        
        if self.scalebar_settings['scalebar']:
            self.create_scalebar()
            
        if self.scalebar_settings['dimension'] == 'si-length-reciprocal':
            vmin = np.percentile(self.canvas.data['data'], 30)
            vmax = np.percentile(self.canvas.data['data'], 99.5)
        else:
            vmin = np.percentile(self.canvas.data['data'], 0.01)
            vmax = np.percentile(self.canvas.data['data'], 99.9)
            
        # Update vmin/vmax
        self.im.set_clim(vmin, vmax)    
        self.fig.tight_layout(pad=0)
        
        self.fig.canvas.draw()
        
        
    def update_background(self, event=None):
        self.background = self.fig.canvas.copy_from_bbox(self.axes.bbox)
        
    def create_scalebar(self):
        if self.scalebar is not None:
            self.scalebar.remove()
            
        # Strip spaces in some cases
        try:
            self.units = ''.join(self.units.split(' '))
        except:
            pass
        
        if self.units in ['um', 'µm', 'nm', 'm', 'mm', 'cm', 'pm']:
            self.scalebar_settings['dimension'] = 'si-length' # Real space image
            if self.units == 'um':
                self.units = 'µm' 
        elif self.units in ['1/m', '1/cm', '1/mm', '1/um', '1/µm', '1/nm', '1/pm']:
            self.scalebar_settings['dimension']  = 'si-length-reciprocal' # Diffraction
            if self.units == '1/um':
                self.units = '1/µm'
        else: # Cannot parse the unit correctly, reset to pixel scale
            self.units = 'px'
            self.scale = 1
            self.scalebar_settings['dimension']  = 'pixel-length'
        
    
        self.scalebar = ScaleBar(self.scale, self.units, location=self.scalebar_settings['location'],
                             dimension=self.scalebar_settings['dimension'],
                             scale_loc=self.scalebar_settings['scale_loc'], 
                             frameon=False, sep=self.scalebar_settings['sep'], 
                             color=self.scalebar_settings['color'])
        self.axes.add_artist(self.scalebar)
        
    def create_colorbar(self):
        self.remove_colorbar()
        img = self.axes.get_images()[0]
        cax = self.axes.inset_axes([0.95,0.8,0.03,0.16])
        vmin, vmax = img.get_clim()
        ticks = [vmin, vmax]
        self.colorbar = self.fig.colorbar(self.im, cax=cax, ticks=ticks, orientation='vertical', ticklocation='left')
        self.colorbar.ax.tick_params(size=0)
        self.canvas.draw_idle()
        
    def remove_colorbar(self):
        if self.colorbar is not None:
            self.colorbar.remove()
            self.colorbar = None
            self.canvas.draw_idle()

            
    
    def show_info(self):
        # Show image infomation function here
        img_dict = self.get_img_dict_from_canvas()
        metadata = img_dict['metadata']
        
        try: 
            extra_metadata = img_dict['original_metadata']
            metadata.update(extra_metadata)
        except:
            pass
        self.metadata_viewer = MetadataViewer(metadata, parent=self)
        self.metadata_viewer.show()
        
    def show_axes(self):
        # Show image axes including size, scale, etc.
        axes = self.get_img_dict_from_canvas()['axes']
        axes_dict = {}
        for ax in axes:
            axes_dict[ax['name']] = ax
            
        self.axes_viewer = DictionaryTreeWidget(axes_dict, parent=self)
        self.axes_viewer.show()
        
        
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
                QMessageBox.critical(self, 'Input Error', 'Please enter a valid scale.')
                return
        
            # Update the new scale to the image dict
            self.scale = scale
            self.units = units
            self.canvas.data['axes'][0]['scale'] = scale
            self.canvas.data['axes'][1]['scale'] = scale
            self.canvas.data['axes'][0]['units'] = units
            self.canvas.data['axes'][1]['units'] = units
            
            # Recreate the scalebar the new scale
            self.create_scalebar()
            self.canvas.draw()
            
            print(f'Scale updated to {scale} {units}')
            
            # Keep the history
            self.process['process'].append('Scale updated to {} {}'.format(scale, units))
            self.canvas.data['metadata']['process'] = copy.deepcopy(self.process)
            
    def simplemath(self):
        dialog = SimpleMathDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            signal1 = dialog.signal1
            signal2 = dialog.signal2
            operation = dialog.operation
            try:
                img1 = copy.deepcopy(find_img_by_title(signal1).canvas.data)
            except:
                QMessageBox.warning(self, 'Simple Math', 'Operation not possible. Make sure the signal 1 is a valid image!')
                return
            try:
                img2 = copy.deepcopy(find_img_by_title(signal2).canvas.data)
            except:
                QMessageBox.warning(self, 'Simple Math', 'Operation not possible. Make sure the signal 2 is a valid image!')
                return
            
            if operation == 'Add':
                try:
                    img1['data'] = img1['data'] + img2['data']
                except:
                    QMessageBox.warning(self, 'Simple Math', 'Operation not possible. Make sure the images are in the same size!')
                    return
            if operation == 'Subtract':
                try:
                    img1['data'] = img1['data'] - img2['data']
                except:
                    QMessageBox.warning(self, 'Simple Math', 'Operation not possible. Make sure the images are in the same size!')
                    return
            if operation == 'Multiply':
                try:
                    img1['data'] = img1['data'] * img2['data']
                except:    
                    QMessageBox.warning(self, 'Simple Math', 'Operation not possible. Make sure the images are in the same size!')
                    return
            if operation == 'Divide':
                try:
                    img1['data'] = img1['data'] / img2['data']
                except:
                    QMessageBox.warning(self, 'Simple Math', 'Operation not possible. Make sure the images are in the same size!')
                    return
            if operation == 'Inverse':
                try:
                    img1['data'] = -img1['data']
                except:
                    QMessageBox.warning(self, 'Simple Math', 'Operation not possible. Make sure the signal 1 is a valid image!')
                    return

                
            # Plot the new image
            if img1['data'].ndim == 2:
                plot = PlotCanvas(img1, self.parent())
            elif img1['data'].ndim == 3:
                plot = PlotCanvas3d(img1, self.parent())
            preview_name = signal1 + '_processed'
            plot.canvas.canvas_name = preview_name
            UI_TemCompanion.preview_dict[preview_name] = plot
            UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
            UI_TemCompanion.preview_dict[preview_name].show()
            UI_TemCompanion.preview_dict[preview_name].position_window('center')
            # Keep the history
            if operation == 'Inverse':
                UI_TemCompanion.preview_dict[preview_name].process['process'].append(f'Inversed signal of {signal1}')
            else:
                UI_TemCompanion.preview_dict[preview_name].process['process'].append(f'Processed by {signal1} {operation} {signal2}')
            UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)    
            
        
    
#=========== Measure functions ================================================
    def clear_cid(self):
        cid_list = [self.button_press_cid, self.button_release_cid, self.motion_notify_cid, self.scroll_event_cid]
        for i, cid in enumerate(cid_list):
            if cid is not None:
                self.fig.canvas.mpl_disconnect(cid)
                cid_list[i] = None
                
    def clear_buttons(self):
        for key, value in self.buttons.items():
            if value is not None:
                self.buttons[key].hide()
                self.buttons[key] = None
    
    def measure(self):
        # Turn off all active modes   
        self.cleanup()
        self.clear_cid()
        self.clear_buttons()
        
        
        for key, value in self.mode_control.items():
            if value:
                self.mode_control[key] = False
        # Turn on measurement mode
        self.mode_control['measurement'] = True
        
        self.start_distance_measurement()
        

    def start_distance_measurement(self):
        self.button_press_cid = self.fig.canvas.mpl_connect('button_press_event', self.on_button_press)
        self.button_release_cid = self.fig.canvas.mpl_connect('button_release_event', self.on_button_release)
        # Display a message in the status bar
        self.statusBar.showMessage("Draw a line with mouse to measure. Drag with mouse if needed.")
        
        if self.buttons['distance_finish'] is None and self.mode_control['measurement']:
            self.buttons['distance_finish'] = QPushButton('Finish', parent=self.canvas)
            self.buttons['distance_finish'].move(30, 30)
            self.buttons['distance_finish'].clicked.connect(self.stop_distance_measurement)
            self.buttons['distance_finish'].show()
        
        # For line profile mode
        if self.mode_control['lineprofile']:
            preview_name = self.windowTitle() + "_Line Profile"
            
            UI_TemCompanion.preview_dict[preview_name] = PlotCanvasLineProfile(parent=self)
            UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name            
            UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
            UI_TemCompanion.preview_dict[preview_name].show()
            
            # Positioning
            self.position_window('center left')
            UI_TemCompanion.preview_dict[preview_name].position_window('next to parent')
            

    def stop_distance_measurement(self):
        if self.mode_control['measurement']:
            self.mode_control['measurement'] = False
            
            # Display a message in the status bar
            self.statusBar.showMessage("Ready")
            
            
            self.cleanup()  # Cleanup any existing measurements
            self.clear_cid() # Disconnect all the cid and set them to None
            self.clear_buttons()         
            self.fig.canvas.draw_idle()
            
    def stop_line_profile(self):
        if self.mode_control['lineprofile']:
            self.mode_control['lineprofile'] = False
           
            self.cleanup()  # Cleanup any existing measurements
            self.clear_cid() # Disconnect all the cid and set them to None
            
            # Display a message in the status bar
            self.statusBar.showMessage("Ready")
            self.fig.canvas.draw_idle()
            

    def cleanup(self):
        if self.line is not None:
            self.line.remove()
            self.line = None
            self.start_point = None
            self.end_point = None
        
        if self.text is not None:
            self.text.remove()
            self.text = None
            
        if self.marker is not None:
            self.marker.remove()
            self.marker = None
            
        if self.center_marker is not None:
            self.center_marker.remove()
            self.center_marker = None
        
        if self.mode_control['mask']:
            self.cleanup_mask()
        
            
        self.canvas.draw_idle()

    def on_button_press(self, event):
        threshold_x = self.img_size[0] / 50
        threshold_y = self.img_size[1] / 50
        threshold = min (threshold_x, threshold_y)
        if event.inaxes != self.axes:
            return
        if (self.start_point is None and self.end_point is None) or (measure_distance((event.xdata, event.ydata), self.start_point) > threshold and measure_distance((event.xdata, event.ydata), self.end_point) > threshold):
            # First click
            self.cleanup() # Cleanup any existing measurements
            self.motion_notify_cid = self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
            self.start_point = (event.xdata, event.ydata)
            self.inactive_point = self.start_point
            self.line, = self.axes.plot([self.start_point[0], self.start_point[0]], 
                                      [self.start_point[1], self.start_point[1]], 'r-',linewidth=self.linewidth)
            
        else:    
        # if self.start_point is not None and self.end_point is not None:
            # Drag on existing points to resize
            self.active_point, self.inactive_point = closer_point((event.xdata, event.ydata), self.start_point, self.end_point)
            self.motion_notify_cid = self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
            
        #self.fig.canvas.draw_idle()

    def on_mouse_move(self, event):
        if self.line is None or self.start_point is None or self.inactive_point is None:
            return
        if event.inaxes != self.axes:
            return
        x0, y0 = self.inactive_point
        x1, y1 = event.xdata, event.ydata
        
        # Only update and redraw if the mouse movement is significant
        if abs(x1 - x0) > self.img_size[1] * 0.01 or abs(y1 - y0) > self.img_size[0] * 0.01:  # Example threshold
            self.line.set_data([x0, x1], [y0, y1])
            
            #self.fig.canvas.draw_idle()
            self.fig.canvas.restore_region(self.background)
            self.axes.draw_artist(self.line)
            self.fig.canvas.blit(self.axes.bbox)
        

    def on_button_release(self, event):
        if event.inaxes != self.axes:
            return
        if self.end_point is None:
            self.end_point = (event.xdata, event.ydata)
        elif self.inactive_point == self.start_point:
            self.end_point = (event.xdata, event.ydata)
        else:
            self.start_point = (event.xdata, event.ydata)
            
        
        # Handle measure the distance
        if self.mode_control['measurement'] and self.start_point is not None and self.end_point is not None:
            distance_units = measure_distance(self.start_point, self.end_point, scale=self.scale)
            #angle = calculate_angle_from_3_points(self.end_point, self.start_point, (self.start_point[0] - 100,self.start_point[1]))
            angle = calculate_angle_to_horizontal(self.start_point, self.end_point)
            if self.text is not None:
                self.text.remove()
            
            text_x = self.start_point[0] 
            text_y = self.start_point[1] - self.img_size[1] * 0.05
            self.text = self.axes.text(text_x, text_y, f'{distance_units:.3f} {self.units}; {angle:.2f} degrees',
                           color='yellow', rotation=angle)
            self.text.set_rotation_mode('anchor')
            self.axes.draw_artist(self.text)
            self.fig.canvas.blit(self.axes.bbox)
            
            
        # Handle line profile
        if self.mode_control['lineprofile'] and self.start_point is not None and self.end_point is not None:
            # Define a line with two points and display the line profile
            p0 = round(self.start_point[0]), round(self.start_point[1])
            p1 = round(self.end_point[0]), round(self.end_point[1])
            preview_name = self.windowTitle() + "_Line Profile"
            UI_TemCompanion.preview_dict[preview_name].plot_lineprofile(p0, p1,self.linewidth)
            
            
            
        self.fig.canvas.mpl_disconnect(self.motion_notify_cid)
        
    def update_line_width(self, width):
        if self.line:
            self.linewidth = width
            self.line.set_linewidth(width)
            self.fig.canvas.draw_idle()
            
        
    
    
    
#============ Line profile function ==========================================
    def lineprofile(self):
        
                
        self.cleanup()
        self.clear_cid()
        self.clear_buttons()
        
        for key, value in self.mode_control.items():
            if value:
                self.mode_control[key] = False
        # Turn on measurement mode
        
        
        self.mode_control['lineprofile'] = True
        self.linewidth = 1
        self.start_distance_measurement()
         
        

#================= FFT ======================================================        
        
    
    def fft(self):
        # if self.units not in ['m','cm','mm','um','nm','pm']:
        #     QMessageBox.warning(self, 'FFT', 'FFT unavailable! Make sure it is a real space image with a valid scale in real space unit!')
        # else:
        img_dict = self.get_img_dict_from_canvas()
        # Crop to a square if not
        data = img_dict['data']
        if data.shape[0] != data.shape[1]:
            # Image will be cropped to square for FFT
            data = filters.crop_to_square(data)
            new_size = data.shape[0]
            for ax in img_dict['axes']:
                ax['size'] = new_size
            img_dict['data'] = data
        # FFT calculation is handled in the PlotCanvasFFT class
        
        preview_name = self.canvas.canvas_name + '_FFT'
        
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvasFFT(img_dict, parent=self)
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].show()
        
        # Positioning
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('next to parent')
        
        
        
    
    def windowedfft(self):
        # if self.units not in ['m','cm','mm','um','nm','pm']:
        #     QMessageBox.warning(self, 'FFT', 'FFT unavailable! Make sure it is a real space image with a valid scale in real space unit!')
        # else:
        img_dict = self.get_img_dict_from_canvas()
        # Crop to a square if not
        data = img_dict['data']
        if data.shape[0] != data.shape[1]:
            data = filters.crop_to_square(data)
            new_size = data.shape[0]
            for ax in img_dict['axes']:
                ax['size'] = new_size
        w = window('hann', data.shape)
        img_dict['data'] = data * w
        # FFT calculation is handled in the PlotCanvasFFT class
        
        preview_name = self.canvas.canvas_name + '_Windowed FFT'
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvasFFT(img_dict, parent=self)
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].show()
        
        # Positioning
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('next to parent')
            
    def live_fft(self):
        self.mode_control['Live_FFT'] = True
        ax = self.canvas.figure.get_axes()[0]
        # Display a message in the status bar
        self.statusBar.showMessage("Drag the square on ROI to compute FFT. Resize if needed.")
        

        
        if self.selector is None:
            self.selector = RectangleSelector(ax, onselect=self.fft_select, interactive=True, useblit=True,
                                              drag_from_anywhere=True, use_data_coordinates=True,
                                              button=[1],ignore_event_outside=True
                                              )
            self.current_data = self.get_current_img_from_canvas()
            im_x, im_y = self.current_data.shape
            fft_size = min(int(im_x/2), int(im_y/2))
            x_min = int(im_y/4)
            x_max = x_min + fft_size
            y_min = int(im_x/4)
            y_max = y_min + fft_size
            
            self.selector.extents = (x_min, x_max, y_min, y_max)
            
            self.selector.set_active(True)
            self.fig.canvas.draw_idle()
            
            preview_name = self.canvas.canvas_name + '_Live FFT'
            self.live_img = copy.deepcopy(self.canvas.data)
            self.live_img['data'] = self.current_data[y_min:y_max, x_min:x_max]
            UI_TemCompanion.preview_dict[preview_name] = PlotCanvasFFT(self.live_img, parent=self)
            UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
            UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
            UI_TemCompanion.preview_dict[preview_name].show()
            
            # Positioning
            self.position_window('center left')
            UI_TemCompanion.preview_dict[preview_name].position_window('next to parent')
        
    def fft_select(self, eclick, erelease):
        # Keep the box square
        x_min, x_max, y_min, y_max = eclick.xdata, erelease.xdata, eclick.ydata, erelease.ydata
        x_min = int(x_min)
        x_max = int(x_max)
        y_min = int(y_min)
        y_max = int(y_max)
        dx = x_max - x_min
        dy = y_max - y_min
        if dx != dy:
            d = min(dx, dy)
            x_max = x_min + d
            y_max = y_min + d
            self.selector.extents = (x_min, x_max, y_min, y_max)
        self.live_img['data'] = self.current_data[y_min:y_max,x_min:x_max]
        # fft_size = self.live_img['data'].shape[0]
        # fft_scale = 1 / self.scale / fft_size
        # Update the FFT 
        preview_name = self.canvas.canvas_name + '_Live FFT'
        UI_TemCompanion.preview_dict[preview_name].update_img(self.live_img['data'])
        
        print(f"Displaying FFT from {x_min}:{x_max}, {y_min}:{y_max}")
    
    def stop_live_fft(self):
        if self.selector is not None:
            self.selector.set_active(False)
            self.selector.set_visible(False)
            self.selector = None
            self.mode_control['Live_FFT'] = False
            # Display a message in the status bar
            self.statusBar.showMessage("Ready")
            self.canvas.draw_idle()
            
#======== Measure FFT function ==============================================
    def start_fft_measurement(self):
                
        if self.scalebar_settings['dimension'] == 'si-length-reciprocal':
            real_units = self.units.split('/')[-1]
            self.measure_fft_dialog = MeasureFFTDialog(0, 0, real_units, self)
            self.measure_fft_dialog.setWindowFlags(self.measure_fft_dialog.windowFlags() | Qt.WindowStaysOnTopHint)
            self.measure_fft_dialog.show()
            
            # Positioning
            #self.position_window('center left')
            self.measure_fft_dialog.position_window('next to parent')
            
            
            self.button_press_cid = self.fig.canvas.mpl_connect('button_press_event', self.on_click)
            # Display a message in the status bar
            self.statusBar.showMessage("Click on a spot to measure")
            
            # Display center marker            
            self.center_marker, = self.axes.plot(self.center[0], self.center[1], 'yx', markersize=10)
            
            # Add define center button
            self.buttons['define_center'] = QPushButton('Define Center', self)
            self.buttons['define_center'].clicked.connect(self.define_center_dp)
            self.buttons['define_center'].setGeometry(30,100,120,30)
            self.buttons['define_center'].show()
            
            
            
    def define_center_dp(self):
        # Measured soots list for defineing center
        self.measured_spots = [None, None]
        # Reconnect the button press event cid
        self.fig.canvas.mpl_disconnect(self.button_press_cid)
        self.button_press_cid = self.fig.canvas.mpl_connect('button_press_event', self.on_click_define_center)
        self.buttons['define_center'].hide()
        # Add two new buttons
        self.buttons['define_center_ok'] = QPushButton('OK', self)
        self.buttons['define_center_ok'].clicked.connect(self.set_center_dp)
        self.buttons['define_center_ok'].setGeometry(30,100,80,30)
        self.buttons['define_center_ok'].show()
        
        self.buttons['define_center_cancel'] = QPushButton('Cancel', self)
        self.buttons['define_center_cancel'].clicked.connect(self.quit_set_center)
        self.buttons['define_center_cancel'].setGeometry(110,100,80,30)
        self.buttons['define_center_cancel'].show()
        # Display message in the status bar
        self.statusBar.showMessage('To define the center, click on the center spot or two symmetric spots.')
        self.canvas.draw_idle()
    
    def quit_set_center(self):
        self.buttons['define_center_ok'].hide()
        self.buttons['define_center_cancel'].hide()
        self.buttons['define_center'].show()
        # Display a message in the status bar
        self.statusBar.showMessage("Click on a spot to measure")
        self.fig.canvas.mpl_disconnect(self.button_press_cid)
        self.button_press_cid = self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.cleanup()
        self.center_marker, = self.axes.plot(self.center[0], self.center[1], 'yx', markersize=10)

        self.canvas.draw_idle()
        
    def set_center_dp(self):
        if self.measured_spots[0] is not None and self.measured_spots[1] is not None:
            # Two spots are collected
            p1, p2 = self.measured_spots[0], self.measured_spots[1]
            self.center = int(p1[0] + (p2[0] - p1[0]) / 2), int(p1[1] + (p2[1] - p1[1]) / 2)
        elif self.measured_spots[1] is not None:
            # One spot
            p1 = self.measured_spots[1]
            self.center = int(p1[0]), int(p1[1])
        
        self.quit_set_center()
        
        
        
    def on_click_define_center(self, event):
        # Handle clicking event when defining the center
        if event.inaxes != self.axes:
            return
        # Clear previous results
        self.cleanup()
        image_data = self.canvas.data['data']
        
        x_click, y_click = int(event.xdata), int(event.ydata)
        # Define a window size around the clicked point to calculate the center of mass
        window_size = self.measure_fft_dialog.windowsize
        
        cx, cy = refine_center(image_data, (x_click, y_click), window_size)
        
        
        # Add refined position to the list
        self.measured_spots.pop(0)
        self.measured_spots.append((cx, cy))
        
        # Add marker to plot
        plots_x = []
        plots_y = []
        for spot in self.measured_spots:
            if spot is not None:
                plots_x.append(spot[0])
                plots_y.append(spot[1])
        self.marker,  = self.axes.plot(plots_x, plots_y, 'y+', markersize=10)
        self.fig.canvas.draw_idle()
        
        
        
    
    def on_click(self, event):
        if event.inaxes != self.axes:
            return
        # Clear previous results
        self.cleanup()
        image_data = self.canvas.data['data']
        
        x_click, y_click = int(event.xdata), int(event.ydata)
        # Define a window size around the clicked point to calculate the center of mass
        window_size = self.measure_fft_dialog.windowsize
        
        cx, cy = refine_center(image_data, (x_click, y_click), window_size)
        
        
        # Add marker to plot
        self.marker,  = self.axes.plot(cx, cy, 'r+', markersize=10)
        self.center_marker, = self.axes.plot(self.center[0], self.center[1], 'yx', markersize=10)
        
        self.axes.draw_artist(self.marker)
        self.fig.canvas.blit(self.axes.bbox)
        #self.fig.canvas.draw_idle()
        
        # Calculate the d-spacing
        self.distance_fft = 1 / measure_distance((cx,cy), self.center, scale=self.scale)
        
        # Calculate the angle from horizontal
        self.ang = calculate_angle_to_horizontal(self.center, (cx,cy))
        # display results in the dialog
        self.measure_fft_dialog.update_measurement(self.distance_fft, self.ang)
        
        
    
        
    def stop_fft_measurement(self):
        if self.mode_control['measure_fft']:
            self.mode_control['measure_fft'] = False
            self.cleanup()  # Cleanup any existing measurements
            self.clear_cid()
            self.clear_buttons()
            
            # Display a message in the status bar
            self.statusBar.showMessage("Ready")
            self.fig.canvas.draw_idle()
            
                    
        
    def measure_fft(self):
        if self.scalebar_settings['dimension'] != 'si-length-reciprocal':
            QMessageBox.warning(self,'Measure Diffraction/FFT','Measure diffraction/FFT only available in reciprocal space. Make sure the scale and unit are calibrated correctly!')
        else:
            self.marker = None
            for key, value in self.mode_control.items():
                if value:
                    self.mode_control[key] = False
                    
            self.cleanup()
            self.clear_cid()
            self.clear_buttons()
            self.mode_control['measure_fft'] = True
            self.start_fft_measurement()
        
        
        
#============== Put cleanup mask function here===============================
    def cleanup_mask(self):
        if self.mask_list or self.sym_mask_list:
            all_mask_list = self.mask_list + self.sym_mask_list
            for mask in all_mask_list:
                mask.remove()
        
                
            self.mask_list = []
            self.sym_mask_list = []
            
            self.clear_buttons()
        
            self.active_mask = None
            self.active_idx = None
            self.clear_cid()
            self.mode_control['mask'] = False        
            
            self.canvas.draw_idle()



#============= Geometric Phase Analysis ======================================
    def gpa(self):
        img = self.get_img_dict_from_canvas()
        data = img['data']
        
        # Take a windowed FFT. The image is cropped to square
        
        if data.shape[0] != data.shape[1]:
            data = filters.crop_to_square(data)
            new_size = data.shape[0]
            for ax in img['axes']:
                ax['size'] = new_size
        w = window('hann', data.shape)
        img['data'] = data * w
        # FFT calculation is handled in the PlotCanvasFFT class
        
        self.mode_control['Live_FFT'] = True
        ax = self.canvas.figure.get_axes()[0]
        # Display a message in the status bar
        self.statusBar.showMessage("Drag the square on the reference region. Resize if needed.")
        
        
        self.selector = RectangleSelector(ax, onselect=self.gpa_select, interactive=True, useblit=True,
                                          drag_from_anywhere=True, use_data_coordinates=True,
                                          button=[1],ignore_event_outside=True
                                          )
        self.current_data = self.get_current_img_from_canvas()
        self.live_img = copy.deepcopy(img)
        im_x, im_y = img['data'].shape
        fft_size = im_x
        x_min = 0
        x_max = x_min + fft_size
        y_min = 0
        y_max = y_min + fft_size
        
        self.selector.extents = (x_min, x_max, y_min, y_max)
        
        self.selector.set_active(True)
        self.fig.canvas.draw_idle()
        
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + "_GPA_FFT"
        preview_fft = PlotCanvasFFT(self.live_img, parent=self)
        
        UI_TemCompanion.preview_dict[preview_name] = preview_fft
        
        preview_fft.canvas.canvas_name = preview_name
        preview_fft.setWindowTitle('Windowed FFT of ' + title)
        preview_fft.show()
        self.position_window('center left')
        preview_fft.position_window('next to parent')
        
        # Add two masks on the FFT
        # Some default values
        self.r = 10
        self.edgesmooth = 0.3
        self.stepsize = 4
        self.sigma = 10
        self.vmin = -0.1
        self.vmax = 0.1
        self.algorithm = 'standard'
        
        
        preview_fft.mask()
        
        preview_fft.add_mask()
        
        preview_fft.statusBar.showMessage('Drag the masks on two noncolinear strong spots. Scroll to resize')
        m1 = preview_fft.mask_list[0]
        m1.center = self.img_size[1]*0.75, self.img_size[0]*0.25
        
        m2 = preview_fft.mask_list[1]
        m2.center = self.img_size[1]*0.75, self.img_size[0]*0.75
        
        # Remove the circles on the symmetric side
        for circle in preview_fft.sym_mask_list:
            circle.remove()
        preview_fft.sym_mask_list = []
        preview_fft.mode_control['GPA'] = True
        
        # Redefine buttons
        preview_fft.clear_buttons()
        preview_fft.buttons['GPA'] = QPushButton('Run GPA', preview_fft)
        preview_fft.buttons['GPA'].setGeometry(30, 80, 80, 30)
        preview_fft.buttons['GPA'].clicked.connect(self.run_gpa)
        preview_fft.buttons['GPA'].show()
        preview_fft.buttons['GPA_settings'] = QPushButton('Settings', preview_fft)
        preview_fft.buttons['GPA_settings'].setGeometry(100, 80, 80, 30)
        preview_fft.buttons['GPA_settings'].clicked.connect(self.gpa_settings)
        preview_fft.buttons['GPA_settings'].show()
        preview_fft.buttons['GPA_refine'] = QPushButton('Refine mask position', preview_fft)
        preview_fft.buttons['GPA_refine'].setGeometry(170, 80, 150, 30)
        preview_fft.buttons['GPA_refine'].clicked.connect(self.refine_mask)
        preview_fft.buttons['GPA_refine'].show()
        preview_fft.buttons['Add_mask'] = QPushButton('Add mask', preview_fft)
        preview_fft.buttons['Add_mask'].setGeometry(310, 80, 100, 30)
        preview_fft.buttons['Add_mask'].clicked.connect(preview_fft.add_mask)
        preview_fft.buttons['Add_mask'].show()
        preview_fft.buttons['Remove_mask'] = QPushButton('Remove mask', preview_fft)
        preview_fft.buttons['Remove_mask'].setGeometry(400, 80, 110, 30)
        preview_fft.buttons['Remove_mask'].clicked.connect(preview_fft.remove_mask)
        preview_fft.buttons['Remove_mask'].show()
        preview_fft.canvas.draw_idle()
        
    def gpa_select(self, eclick, erelease):
        # Keep the box square
        x_min, x_max, y_min, y_max = eclick.xdata, erelease.xdata, eclick.ydata, erelease.ydata
        x_min = int(x_min)
        x_max = int(x_max)
        y_min = int(y_min)
        y_max = int(y_max)
        dx = x_max - x_min
        dy = y_max - y_min
        if dx != dy:
            d = min(dx, dy)
            x_max = x_min + d
            y_max = y_min + d
            self.selector.extents = (x_min, x_max, y_min, y_max)
        self.live_img['data'] = self.current_data[y_min:y_max,x_min:x_max]
        # Update the FFT
        preview_name = self.canvas.canvas_name + "_GPA_FFT"
        UI_TemCompanion.preview_dict[preview_name].update_img(self.live_img['data'], gpa=True, windowed=True)
        
    def run_gpa(self):
        img = self.get_img_dict_from_canvas()
        data = img['data']
        if data.shape[0] != data.shape[1]:
            data = filters.crop_to_square(data)
            new_size = data.shape[0]
            for ax in img['axes']:
                ax['size'] = new_size
        
        # Get the center and radius of the masks
        preview_name_fft = self.canvas.canvas_name + "_GPA_FFT"
        g = [m.center for m in UI_TemCompanion.preview_dict[preview_name_fft].mask_list]
        if len(g) < 2:
            QMessageBox.warning(self, 'Run GPA', 'At least 2 g vectors are needed!')
            return
        
        # g1 = UI_TemCompanion.preview_dict[preview_name_fft].mask_list[0].center
        # g2 = UI_TemCompanion.preview_dict[preview_name_fft].mask_list[1].center
        r = max(UI_TemCompanion.preview_dict[preview_name_fft].mask_list[0].radius, UI_TemCompanion.preview_dict[preview_name_fft].mask_list[1].radius)
        
        exx, eyy, exy, oxy = GPA(data, g, algorithm=self.algorithm, r=r, edge_blur=self.edgesmooth, sigma=self.sigma, window_size=r, step=self.stepsize)
        # if self.algorithm == 'standard':
        #     exx, eyy, exy, oxy = simpleGPA(data, g1, g2, r, edge_blur=self.edgesmooth)
        # elif self.algorithm == 'adaptive':
        #     exx, eyy, exy, oxy = adaptiveGPA(data, g1, g2, sigma=r, window_size=r, step=int(r/5))
        
        # Display the strain tensors
        exx_dict = copy.deepcopy(img)
        exx_dict['data'] = exx
        preview_name_exx = self.canvas.canvas_name + "_exx"
        UI_TemCompanion.preview_dict[preview_name_exx] = PlotCanvas(exx_dict, parent=self)
        UI_TemCompanion.preview_dict[preview_name_exx].setWindowTitle('Epsilon xx')
        UI_TemCompanion.preview_dict[preview_name_exx].canvas.canvas_name = preview_name_exx
        UI_TemCompanion.preview_dict[preview_name_exx].im.set_clim(self.vmin, self.vmax)
        UI_TemCompanion.preview_dict[preview_name_exx].im.set_cmap('seismic')
        UI_TemCompanion.preview_dict[preview_name_exx].create_colorbar()
        UI_TemCompanion.preview_dict[preview_name_exx].show()
        
        eyy_dict = copy.deepcopy(img)
        eyy_dict['data'] = eyy
        preview_name_eyy = self.canvas.canvas_name + "_eyy"
        UI_TemCompanion.preview_dict[preview_name_eyy] = PlotCanvas(eyy_dict, parent=self)
        UI_TemCompanion.preview_dict[preview_name_eyy].setWindowTitle('Epsilon yy')
        UI_TemCompanion.preview_dict[preview_name_eyy].canvas.canvas_name = preview_name_eyy
        UI_TemCompanion.preview_dict[preview_name_eyy].im.set_clim(self.vmin, self.vmax)
        UI_TemCompanion.preview_dict[preview_name_eyy].im.set_cmap('seismic')
        UI_TemCompanion.preview_dict[preview_name_eyy].create_colorbar()
        UI_TemCompanion.preview_dict[preview_name_eyy].show()
        
        exy_dict = copy.deepcopy(img)
        exy_dict['data'] = exy
        preview_name_exy = self.canvas.canvas_name + "_exy"
        UI_TemCompanion.preview_dict[preview_name_exy] = PlotCanvas(exy_dict, parent=self)
        UI_TemCompanion.preview_dict[preview_name_exy].setWindowTitle('Epsilon xy')
        UI_TemCompanion.preview_dict[preview_name_exy].canvas.canvas_name = preview_name_exy
        UI_TemCompanion.preview_dict[preview_name_exy].im.set_clim(self.vmin, self.vmax)
        UI_TemCompanion.preview_dict[preview_name_exy].im.set_cmap('seismic')
        UI_TemCompanion.preview_dict[preview_name_exy].create_colorbar()
        UI_TemCompanion.preview_dict[preview_name_exy].show()
        
        oxy_dict = copy.deepcopy(img)
        oxy_dict['data'] = oxy
        preview_name_oxy = self.canvas.canvas_name + "_oxy"
        UI_TemCompanion.preview_dict[preview_name_oxy] = PlotCanvas(oxy_dict, parent=self)
        UI_TemCompanion.preview_dict[preview_name_oxy].setWindowTitle('Omega')
        UI_TemCompanion.preview_dict[preview_name_oxy].canvas.canvas_name = preview_name_oxy
        UI_TemCompanion.preview_dict[preview_name_oxy].im.set_clim(self.vmin, self.vmax)
        UI_TemCompanion.preview_dict[preview_name_oxy].im.set_cmap('seismic')
        UI_TemCompanion.preview_dict[preview_name_oxy].create_colorbar()
        UI_TemCompanion.preview_dict[preview_name_oxy].show()
    
    def gpa_settings(self):
        # Open a dialog to take settings
        preview_name = self.canvas.canvas_name + '_GPA_FFT'
        r = max(UI_TemCompanion.preview_dict[preview_name].mask_list[0].radius, UI_TemCompanion.preview_dict[preview_name].mask_list[1].radius)
        step = max(r*2//5, 2)
        dialog = gpaSettings(int(r), self.edgesmooth, step, self.sigma, self.algorithm, vmin=self.vmin, vmax=self.vmax, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.r = dialog.masksize
            self.edgesmooth = dialog.edgesmooth
            self.stepsize = dialog.stepsize
            self.sigma = dialog.sigma
            self.vmin = dialog.vmin
            self.vmax = dialog.vmax
            self.algorithm = dialog.gpa
            
            
        # Update masks 
        for mask in UI_TemCompanion.preview_dict[preview_name].mask_list:
            mask.set_radius(self.r)
        
        UI_TemCompanion.preview_dict[preview_name].canvas.draw_idle()
                
    def refine_mask(self):
        preview_name = self.canvas.canvas_name + '_GPA_FFT'
        window_size = 5
        img = UI_TemCompanion.preview_dict[preview_name].get_current_img_from_canvas()
        #r = max([mask.radius for mask in UI_TemCompanion.preview_dict['GPA_FFT'].mask_list])
        for mask in UI_TemCompanion.preview_dict[preview_name].mask_list:
            g = mask.center
            g_refined = refine_center(img, g, window_size)
            mask.center = g_refined
            #mask.radius = r
        UI_TemCompanion.preview_dict[preview_name].canvas.draw_idle()
        
        
#================Differential Phase Contrast===================================
    def dpc(self):
        self.dpc_reconstruct = DPCDialog(parent=self)
        self.dpc_reconstruct.show()
        
        

        
#======= Canvas to show image stacks==========================================
class PlotCanvas3d(PlotCanvas):
    def __init__(self, img, parent=None):
        super().__init__(img, parent)        
        # Redefine image size 
        self.img_size = img['data'].shape[1], img['data'].shape[2]
        
        # Add extra buttons
        self.buttons['crop_stack_ok'] = None
        self.buttons['crop_stack_cancel'] = None
        
        # Add Stack menu
        stack_menu = QMenu('Stack', self) 
        self.menubar.insertMenu(self.menubar.children()[6].children()[0],stack_menu)
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
        export_series = QAction('Save as series', self)
        export_series.triggered.connect(self.export_series)
        stack_menu.addAction(export_series)
        
        
    def create_img(self):
        self.canvas.img_idx = 0
        self.im = self.axes.imshow(self.canvas.data['data'][self.canvas.img_idx],cmap='gray')
        self.axes.set_axis_off()
        # Add scale bar 
        self.scale = self.canvas.data['axes'][1]['scale']
        self.units = self.canvas.data['axes'][1]['units'] 
        if self.scalebar_settings['scalebar']:
            self.create_scalebar()
        self.fig.tight_layout(pad=0)
        # Create a slider for stacks
        self.slider_ax = self.fig.add_axes([0.2, 0.9, 0.7, 0.03], facecolor='lightgoldenrodyellow')
        self.fontsize = 10
        self.slider = Slider(self.slider_ax, 'Frame', 0, self.canvas.data['data'].shape[0] - 1, 
                             valinit=self.canvas.img_idx, valstep=1,handle_style={'size': self.fontsize})
        self.slider_ax.tick_params(labelsize=self.fontsize)  # Smaller font size for ticks
        self.slider.label.set_size(self.fontsize)     # Smaller font size for label
        self.slider.label.set_color('yellow')
        self.slider.valtext.set_size(self.fontsize)
        self.slider.valtext.set_color('yellow')
        self.slider.on_changed(self.update_frame)
        
    # Update function for the slider
    def update_frame(self, val):
        self.canvas.img_idx = int(self.slider.val)
        self.im.set_data(self.canvas.data['data'][self.canvas.img_idx])
        self.canvas.draw_idle()
        
        
    def flip_stack_horizontal(self):
        img = copy.deepcopy(self.canvas.data)
        img_to_flip = img['data']
        flipped_array = img_to_flip[:,:,::-1]
        img['data'] = flipped_array
        
        # Create a new PlotCanvs to display        
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_Flipped_LR'
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvas3d(img, parent=self.parent())
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].show()
        
        print(f'Flipped the entire stack of {title} horizontally.')
        
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
        # Keep the history
        UI_TemCompanion.preview_dict[preview_name].process['process'].append('Flipped horizontally')
        UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
   
    def flip_stack_vertical(self):
        img = copy.deepcopy(self.canvas.data)
        img_to_flip = img['data']
        flipped_array = img_to_flip[:,::-1,:]
        img['data'] = flipped_array
        
        # Create a new PlotCanvs to display        
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_Flipped_UD'
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvas3d(img, parent=self.parent())
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].show()
        
        print(f'Flipped the entire stack of {title} vertically.')
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
        # Keep the history
        UI_TemCompanion.preview_dict[preview_name].process['process'].append('Flipped vertically')
        UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
    
    def crop_stack(self):
        ax = self.canvas.figure.get_axes()[0]
        # Display a message in the status bar
        self.statusBar.showMessage("Drag a rectangle to crop. Hold Shift to draw a square.")
        

        
        if self.selector is None:
            self.selector = RectangleSelector(ax, onselect=self.on_select, interactive=True, useblit=True,
                                              drag_from_anywhere=True, use_data_coordinates=True,
                                              minspanx=5, minspany=5,
                                              button=[1]
                                              )
            
            # Crop button
            self.buttons['crop_stack_ok'] = QPushButton('OK', parent=self.canvas)
            self.buttons['crop_stack_ok'].move(30, 30)
            self.buttons['crop_stack_ok'].clicked.connect(self.confirm_crop_stack)

            self.buttons['crop_stack_cancel'] = QPushButton('Cancel', parent=self.canvas)
            self.buttons['crop_stack_cancel'].move(100,30)
            self.buttons['crop_stack_cancel'].clicked.connect(self.cancel_crop)
            
            self.buttons['crop_stack_input'] = QPushButton('Manual input', parent=self.canvas)
            self.buttons['crop_stack_input'].move(170,30)
            self.buttons['crop_stack_input'].clicked.connect(self.manual_crop)
            
            self.selector.set_active(True)
            for value in self.buttons.values():
                if value is not None:
                    value.show()
            
            self.fig.canvas.draw_idle()
        
    def confirm_crop_stack(self):
        if self.selector is not None and self.selector.active:
            x0, x1, y0, y1 = self.selector.extents
            if abs(x1 - x0) > 5 and abs(y1 - y0) >5: 
                # Valid area is selected               
                img = copy.deepcopy(self.canvas.data)
                cropped_img = img['data'][:,int(y0):int(y1), int(x0):int(x1)]                
                img['data'] = cropped_img
                # Update axes size
                img['axes'][0]['size'] = img['data'].shape[1]
                img['axes'][1]['size'] = img['data'].shape[2]
                
                
                # Create a new PlotCanvas to display
                title = self.windowTitle()
                preview_name = self.canvas.canvas_name + '_cropped'
                UI_TemCompanion.preview_dict[preview_name] = PlotCanvas3d(img, parent=self.parent())
                UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
                UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
                UI_TemCompanion.preview_dict[preview_name].show()
                
                print(f'Cropped the entire stack of {title} by {int(x0)}:{int(x1)}, {int(y0)}:{int(y1)}.')
                self.position_window('center left')
                UI_TemCompanion.preview_dict[preview_name].position_window('center right')
                
                # Write process history in the original_metadata
                UI_TemCompanion.preview_dict[preview_name].process['process'].append('Cropped by {}:{}, {}:{} from the original image'.format(int(x0),int(x1),int(y0),int(y1)))
                UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
                
            self.selector.set_active(False)
            self.selector.set_visible(False)
            self.selector.disconnect_events()  # Disconnect event handling
            self.selector = None    
            for value in self.buttons.values():
                if value is not None:
                    value.hide()
                    value = None
            
            self.statusBar.showMessage("Ready")
            self.fig.canvas.draw_idle()
            

    
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
            img['axes'][0]['size'] = img['data'].shape[0]
            img['axes'][1]['size'] = img['data'].shape[1]
            
            # Create a new PlotCanvs to display        
            title = self.windowTitle()
            preview_name = self.canvas.canvas_name + '_R{}'.format(ang)
            UI_TemCompanion.preview_dict[preview_name] = PlotCanvas3d(img, parent=self.parent())
            UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
            UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
            UI_TemCompanion.preview_dict[preview_name].show()
            
            print(f'Rotated the entire stack of {title} by {ang} degrees counterclockwise.')
            self.position_window('center left')
            UI_TemCompanion.preview_dict[preview_name].position_window('center right')
            
            # Keep the history
            UI_TemCompanion.preview_dict[preview_name].process['process'].append('Rotated by {} degrees from the original image'.format(ang))
            UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
    
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
            img['axes'][0]['scale'] = new_scale
            img['axes'][0]['size'] = new_y
            img['axes'][1]['scale'] = new_scale
            img['axes'][1]['size'] = new_x
            
            # Create a new PlotCanvs to display        
            title = self.windowTitle()
            preview_name = self.canvas.canvas_name + '_Resampled'
            UI_TemCompanion.preview_dict[preview_name] = PlotCanvas3d(img, parent=self.parent())
            UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
            UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
            UI_TemCompanion.preview_dict[preview_name].show()
            
            print(f'Resampled {title} by a factor of {rescale_factor}.')
            self.position_window('center left')
            UI_TemCompanion.preview_dict[preview_name].position_window('center right')
            
            # Keep the history
            UI_TemCompanion.preview_dict[preview_name].process['process'].append(f'Resampled by a factor of {rescale_factor}.')
            UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)


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
            sorted_img['original_axes'][0]['size'] = img_n    
        else:
            return
        
        # Create a new PlotCanvs to display        
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_sorted'
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvas3d(sorted_img, parent=self.parent())
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].show()
        
        print(f'{title} has been sorted.')
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
        # Keep the history
        UI_TemCompanion.preview_dict[preview_name].process['process'].append(f'Sorted by the order of {sorted_order}.')
        UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
    
    def align_stack_cc(self):        
        aligned_img = copy.deepcopy(self.canvas.data)
        img = aligned_img['data']
        
        # Open a dialog to take parameters
        dialog = AlignStackDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            apply_window = dialog.apply_window
            crop_img = dialog.crop_img
            crop_to_square = dialog.crop_to_square
                        
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
                
                img[n+1,:,:] = shift(img_to_shift,drift, output='int16')
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
                    
            # Create a new PlotCanvas to display
            preview_name = self.canvas.canvas_name + '_aligned by cc'
            UI_TemCompanion.preview_dict[preview_name] = PlotCanvas3d(aligned_img, parent=self.parent())
            UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
            UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
            UI_TemCompanion.preview_dict[preview_name].show()
            
            self.position_window('center left')
            UI_TemCompanion.preview_dict[preview_name].position_window('center right')
            
            # Write process history in the original_metadata
            UI_TemCompanion.preview_dict[preview_name].process['process'].append('Aligned by Phase Cross-Correlation')
            UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
    

    def align_stack_of(self):
        aligned_img = copy.deepcopy(self.canvas.data)
        img = aligned_img['data']
        # Open a dialog to take parameters
        # dialog = AlignStackOFDialog(parent=self)
        # if dialog.exec_() == QDialog.Accepted:
        #     algorithm = dialog.algorithm
        #     apply_window = dialog.apply_window
            
        print('Stack alignment using Optical Flow iLK.')
        img_n, nr, nc = img.shape
        drift_stack = []
        for n in range(img_n -1):            
            fixed = img[n]
            moving = img[n+1]
            
            #print(f'Calculate the drift of slice {n+1} using Optical Flow iLK...')
            
            u, v = optical_flow_ilk(fixed, moving)
            drift_stack.append((u, v))
        
        # Apply the correction
        #print('Applying drift correction...')
        row_coords, col_coords = np.meshgrid(np.arange(nr), np.arange(nc), indexing='ij')
        drift = np.array([np.zeros((nr,nc)),np.zeros((nr,nc))])
        for n in range(img_n-1):
            drift = drift + np.array(drift_stack[n])
            vector_field = np.array([row_coords + drift[0], col_coords + drift[1]])
            img_to_shift = img[n+1]
            
            img[n+1,:,:] = warp(img_to_shift, vector_field, mode='constant') 
        
            aligned_img['data'] = img
        print('Stack alignment finished!')
                
        # Create a new PlotCanvas to display
        preview_name = self.canvas.canvas_name + '_aligned by OF'
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvas3d(aligned_img, parent=self.parent())
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].show()
        
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
        # Write process history in the original_metadata
        UI_TemCompanion.preview_dict[preview_name].process['process'].append('Aligned by Optical Flow iLK')
        UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
            
    
    def integrate_stack(self):
        data = np.mean(self.canvas.data['data'], axis=0)
        integrated_img = {'data': data, 'axes': self.canvas.data['axes'], 'metadata': self.canvas.data['metadata'],
                          'original_metadata': self.canvas.data['original_metadata']}
        # Create a new PlotCanvs to display     
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_integrated'
        UI_TemCompanion.preview_dict[preview_name] = PlotCanvas(integrated_img, parent=self.parent())
        UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
        UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name].show()
        
        print(f'Stack of {title} has been integrated.')
        self.position_window('center left')
        UI_TemCompanion.preview_dict[preview_name].position_window('center right')
        
        # Keep the history
        # UI_TemCompanion.preview_dict[preview_name].process['process'].append('Rotated by {} degrees from the original image'.format(ang))
        # UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
    
    def export_stack(self):
        data = self.canvas.data
        img_data = data['data'].astype('float32')
        # Update the axes in case they have been changed, e.g., scale, size...
        data['original_axes'][1]['size'] = data['axes'][0]['size']
        data['original_axes'][2]['size'] = data['axes'][1]['size']
        data['original_axes'][1]['scale'] = data['axes'][0]['scale']
        data['original_axes'][2]['scale'] = data['axes'][1]['scale']
        data['original_axes'][1]['units'] = data['axes'][0]['units']
        data['original_axes'][2]['units'] = data['axes'][1]['units']
        
        data_to_export = {'data': img_data, 'metadata': data['metadata'], 'axes': data['original_axes']}
        options = QFileDialog.Options()
        file_path, selection = QFileDialog.getSaveFileName(self.parent(), 
                                                   "Save as tiff stack", 
                                                   "", 
                                                   "TIFF Files (*.tiff)", 
                                                   options=options)
        if file_path:
            tif_writer(file_path, data_to_export) 
            
            print(f'{file_path} has been exported.')

        
    
    def export_series(self):
        data = self.canvas.data
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
                    
            else: # Save with matplotlib
                figsize = self.canvas.figure.get_size_inches()
                img_size = img_to_save['data'][0].shape
                dpi = float(sorted(img_size/figsize, reverse=True)[0])  
                
                # Hide the slider
                self.canvas.figure.axes[1].set_visible(False)
                for i in range(img_to_save['data'].shape[0]):
                    self.slider.set_val(i)
                    self.canvas.figure.savefig(output_dir + f_name + f'_{i:03d}' +'.' + file_type, dpi=dpi, format=file_type)
                    print(f'Exported to {output_dir}/{f_name}_{i:03d}.')
                self.canvas.figure.axes[1].set_visible(True)
                    
            

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
                break
        analyze_menu.removeAction(gpa_action)
        
        
        
        
        # Remove the filter menu
        filter_menu = self.menubar.children()[5]
        self.menubar.removeAction(filter_menu.menuAction())
        
        
        
        
        self.active_mask = None
        self.active_idx = None
        
        
        
        
        # Add extra buttons
        self.buttons['mask_add'] = None
        self.buttons['mask_remove'] = None
        self.buttons['mask_ifft'] = None
        self.buttons['mask_cancel'] = None
    
    def closeEvent(self, event):       
        if self.parent().mode_control['Live_FFT']:
            self.parent().stop_live_fft()
        UI_TemCompanion.preview_dict.pop(self.canvas.canvas_name, None)
        
        
    def set_scale_units(self):
        img_dict = self.canvas.data 
        self.real_scale = img_dict['axes'][1]['scale']
        # Update image size
        self.img_size = img_dict['data'].shape
        fft_scale = 1 / self.real_scale / self.img_size[0]
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
        
        # Update image dictionary
        img_dict['axes'][0]['size'] = self.img_size[0]
        img_dict['axes'][1]['size'] = self.img_size[1]
        img_dict['axes'][0]['scale'] = fft_scale
        img_dict['axes'][1]['scale'] = fft_scale
        img_dict['axes'][0]['units'] = fft_units
        img_dict['axes'][1]['units'] = fft_units
        
        
    def create_img(self):
        img_dict = self.canvas.data  
        data = img_dict['data']
        
        fft_data = fftshift(fft2(data))
        fft_mag = np.abs(fft_data)
        # Normalize image data
        #fft_data = norm_img(fft_data) * 100
        # Reformat the axes of the FFT image
        
        # Update image data to fft
        self.canvas.data['fft'] = fft_data
        self.canvas.data['data'] = fft_mag
        self.set_scale_units()
        

        vmin, vmax = np.percentile(fft_mag, (30,99.9))
        
        self.im = self.axes.imshow(self.canvas.data['data'], vmin=vmin, vmax=vmax, cmap='inferno')
        self.axes.set_axis_off()
        #Scale bar with inverse unit  
        if self.scalebar_settings['scalebar']:
            self.create_scalebar()
        self.fig.tight_layout(pad=0)
        
    def update_img(self, real_data, gpa=False, windowed=False):
        # Compute fft from real_data and update the display and scale
        if windowed:
            w = window('hann', real_data.shape)
            real_data = real_data * w
        fft_data = fftshift(fft2(real_data))        
        fft_mag = np.abs(fft_data)
        self.canvas.data['data'] = fft_mag
        self.canvas.data['fft'] = fft_data
        
        # For GPA use, resize the FFT to the original
        if gpa:
            fft_mag = resize(fft_mag, self.img_size)
            self.im._A = fft_mag
            vmin, vmax = np.percentile(fft_mag, (30,99.9))
            self.im.set_clim(vmin, vmax)
        
        else:
            # Update the units
            self.canvas.data['axes'][0]['units'] = self.real_units
            self.canvas.data['axes'][1]['units'] = self.real_units
            self.canvas.data['axes'][0]['scale'] = self.real_scale
            self.canvas.data['axes'][1]['scale'] = self.real_scale
            # Update the units and scale
            self.set_scale_units()
            # Update the center
            self.center = fft_mag.shape[1]//2, fft_mag.shape[0]//2
            
            # Clear the image canvas
        
            self.axes.clear()
            self.marker = None
            self.center_marker = None
            self.scalebar = None
            self.line = None
            self.text = None
        
        # # Reset the measurement marker if exists
        # if self.marker is not None:
        #     self.marker = None
        
            vmin, vmax = np.percentile(fft_mag, (30,99.9))
            
            self.im = self.axes.imshow(self.canvas.data['data'], vmin=vmin, vmax=vmax, cmap='inferno')
            self.axes.set_axis_off()
            #Scale bar with inverse unit        
            if self.scalebar_settings['scalebar']:
                self.create_scalebar()
            self.fig.tight_layout(pad=0)
        
        self.update_background()
        self.canvas.draw_idle()
        
    
# Redefine right click menu
    def show_context_menu(self, pos):
        context_menu = QtWidgets.QMenu(self)
        
        # File menu
        file_menu = context_menu.addMenu('File')
        save_action = QAction('Save as')
        save_action.triggered.connect(self.mpl_toolbar.save_figure)
        file_menu.addAction(save_action)
        copy_action = QAction('Copy Image to Clipboard')
        copy_action.triggered.connect(self.copy_img)
        file_menu.addAction(copy_action)
        imagesetting_action = QAction('Image Settings')
        imagesetting_action.triggered.connect(self.mpl_toolbar.edit_parameters)
        file_menu.addAction(imagesetting_action)
        close_action = QAction('Close')
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)
        
        # Edit menu and actions
        edit_menu = context_menu.addMenu('Process')
        crop_action = QAction('Crop')
        crop_action.triggered.connect(self.crop)
        edit_menu.addAction(crop_action)
        rotate_action = QAction('Rotate')
        rotate_action.triggered.connect(self.rotate)
        edit_menu.addAction(rotate_action)
        fliplr_action = QAction('Flip horizontal')
        fliplr_action.triggered.connect(self.flip_horizontal)
        edit_menu.addAction(fliplr_action)
        flipud_action = QAction('Flip vertical',self)
        flipud_action.triggered.connect(self.flip_vertical)
        edit_menu.addAction(flipud_action)
        resampling_action = QAction('Resampling')
        resampling_action.triggered.connect(self.resampling)
        edit_menu.addAction(resampling_action)
        simplemath_action = QAction('Simple math', self)
        simplemath_action.triggered.connect(self.simplemath)
        edit_menu.addAction(simplemath_action)
        
        # FFT menu
        fft_menu = context_menu.addMenu('FFT')
        fft_action = QAction('FFT')
        fft_action.triggered.connect(self.fft)
        fft_menu.addAction(fft_action)
        windowedfft_action = QAction('Windowed FFT')
        windowedfft_action.triggered.connect(self.windowedfft)
        fft_menu.addAction(windowedfft_action)
        livefft_action = QAction('Live FFT')
        livefft_action.triggered.connect(self.live_fft)
        fft_menu.addAction(livefft_action)
        mask_action = QAction('Mask and iFFT')
        mask_action.triggered.connect(self.mask)
        fft_menu.addAction(mask_action)
        
        
        # Analyze menu and actions
        analyze_menu = context_menu.addMenu('Analyze')
        setscale_action = QAction('Set Scale')
        setscale_action.triggered.connect(self.setscale)
        analyze_menu.addAction(setscale_action)
        measure_action = QAction('Measure')
        measure_action.triggered.connect(self.measure)
        analyze_menu.addAction(measure_action)
        measure_fft_action = QAction('Measure Diffraction/FFT')
        measure_fft_action.triggered.connect(self.measure_fft)        
        analyze_menu.addAction(measure_fft_action)        
        lineprofile_action = QAction('Line Profile')
        lineprofile_action.triggered.connect(self.lineprofile)
        analyze_menu.addAction(lineprofile_action)
        
    
        # Info menu
        info_menu = context_menu.addMenu('Info')
        axes_action = QAction('Image Axes')
        axes_action.triggered.connect(self.show_axes)
        info_menu.addAction(axes_action)
        info_action = QAction('View Metadata')
        info_action.triggered.connect(self.show_info)
        info_menu.addAction(info_action)
        
    
        context_menu.exec_(self.mapToGlobal(pos))
        
        

         
    
    def mask(self):
        self.cleanup()
        self.clear_cid()        
        self.clear_buttons()
        for key, value in self.mode_control.items():
            if value:
                self.mode_control[key] = False
                
        self.mode_control['mask'] = True
        self.mask_list = []
        self.sym_mask_list = []
       
        self.button_press_cid = self.fig.canvas.mpl_connect('button_press_event', self.fft_on_press)
        self.button_release_cid = self.fig.canvas.mpl_connect('button_release_event', self.fft_on_release)

        
        # Buttons for add, remove, cancel
        self.buttons['mask_add'] = QPushButton('Add', parent=self.canvas)
        self.buttons['mask_add'].setGeometry(30, 30, 80, 30)
        self.buttons['mask_add'].clicked.connect(self.add_mask)
        self.buttons['mask_remove'] = QPushButton('Remove', parent=self.canvas)
        self.buttons['mask_remove'] .setGeometry(100, 30, 80, 30)
        self.buttons['mask_remove'] .clicked.connect(self.remove_mask)
        self.buttons['mask_cancel']  = QPushButton('Cancel', parent=self.canvas)
        self.buttons['mask_cancel'].setGeometry(170, 30, 80, 30)
        self.buttons['mask_cancel'].clicked.connect(self.cleanup_mask)
        self.buttons['mask_ifft'] = QPushButton('iFFT', parent=self.canvas)
        self.buttons['mask_ifft'].setGeometry(240, 30, 80, 30)
        self.buttons['mask_ifft'].clicked.connect(self.ifft_filter)
        
        for key, value in self.buttons.items():
            if value is not None:
                self.buttons[key].show()
        
        self.add_mask()
        
        self.statusBar.showMessage('Drag on the red circle to position. Scroll to resize. Add more as needed.')
        self.canvas.draw_idle()
        
    
    
    def add_mask(self):       
        # Default size and position
        x0, y0 = self.img_size[0]/4, self.img_size[1]/4
        r0 = int(self.img_size[0]/100 /0.7)
        mask = Circle((x0,y0),radius=r0, color='red', fill=False)
        self.axes.add_artist(mask)
        self.mask_list.append(mask)
        
        # Set color to inactive mask
        if self.active_mask is not None:
            self.active_mask.set_color('orange')
        
        # Add another circle at symmetric position
        if self.mode_control['GPA'] is not True:
            sym_mask = Circle((self.img_size[0]-x0,self.img_size[1]-y0), radius=r0, color='yellow', fill=False)
            self.sym_mask_list.append(sym_mask)
            self.axes.add_artist(sym_mask)
            self.active_mask = mask
            
            self.active_idx = self.mask_list.index(mask)
        self.canvas.draw_idle()

        
    def remove_mask(self):
        if self.active_mask is not None:
            self.mask_list.remove(self.active_mask)
            if self.sym_mask_list:
                self.sym_mask_list[self.active_idx].remove()
                self.sym_mask_list.pop(self.active_idx)
            self.active_mask.remove()
            
            self.active_mask = None
            self.active_idx = None
            self.canvas.draw_idle()
        
    def fft_on_press(self,event):
        
        if event.inaxes != self.axes:
            return
        
        if self.active_mask is not None:
            self.active_mask.set_color('orange')
        x, y = event.xdata, event.ydata
        # Find the closest circle in the mask list
        for i, mask in enumerate(self.mask_list):
            cx, cy = mask.center
            d = measure_distance((x,y), (cx,cy))
            if d < mask.radius * 1.5:
                self.active_mask = mask
                self.active_idx = i
                break
            else:
                self.active_mask = None
                self.active_idx = None
        # Set red color to the active circle
        if self.active_mask is not None:
            self.active_mask.set_color('red')        
            self.motion_notify_cid = self.fig.canvas.mpl_connect('motion_notify_event', self.fft_on_move)
            self.scroll_event_cid = self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.draw_idle()
        
    def fft_on_move(self, event):
        if event.inaxes != self.axes:
            return
        x, y = event.xdata, event.ydata
        x0, y0 = self.active_mask.center
        
        self.active_mask.center = x, y
        if self.sym_mask_list:
            self.sym_mask_list[self.active_idx].center = (self.img_size[0]-x, self.img_size[1]-y)
        self.canvas.draw_idle()
        # if abs(x0-x) > self.img_size[0] /100 or abs(y0-y) > self.img_size[1] / 100:
        #     self.fig.canvas.draw()
            
     
    def fft_on_release(self, event):
        if event.inaxes != self.axes:
            return
        
        
        self.fig.canvas.mpl_disconnect(self.motion_notify_cid)
        self.canvas.draw_idle()
                
    def on_scroll(self, event):
        if self.active_mask is None:
            return

        if event.button == 'up':
            new_radius = self.active_mask.radius + 1
        elif event.button == 'down':
            new_radius = max(self.active_mask.radius - 1, 1)
            
        else:
            return
        
        all_mask_list = self.mask_list + self.sym_mask_list
        for mask in all_mask_list:
            mask.set_radius(new_radius)
        # self.active_mask.set_radius(new_radius)
        # if self.sym_mask_list:
        #     self.sym_mask_list[self.active_idx].set_radius(new_radius)

        self.fig.canvas.draw_idle() 
        
            
        
     
    def ifft_filter(self):
        if self.mask_list and self.sym_mask_list:
            mask_list = self.mask_list + self.sym_mask_list
            center = [m.center for m in mask_list]
            radius = [m.radius for m in mask_list]
            mask = create_mask(self.img_size, center, radius)               
            
            fft_data = self.canvas.data['fft']
            masked_fft = fft_data * mask
            filtered_img = ifft2(ifftshift(masked_fft)).real
            filtered_img_dict = self.get_img_dict_from_canvas()
            filtered_img_dict['data'] = filtered_img
            
            # Calculate scale and update
            if self.units != 'px':
                img_scale = 1 / self.scale /self.img_size[0]
                img_units = self.units.split('/')[-1]
                
            else:
                img_scale = 1
                img_units = 'px'
            
            for axes in filtered_img_dict['axes']:
                axes['units'] = img_units
                axes['scale'] = img_scale
                
                
            # Create a new plot canvas and display
            mask_center = [(int(circle.center[0]), int(circle.center[1])) for circle in self.mask_list]
            preview_name = self.canvas.canvas_name + f'_iFFT_{mask_center}'
            UI_TemCompanion.preview_dict[preview_name] = PlotCanvas(filtered_img_dict,parent=self.parent())
            UI_TemCompanion.preview_dict[preview_name].canvas.canvas_name = preview_name
            
            UI_TemCompanion.preview_dict[preview_name].setWindowTitle(preview_name)
            UI_TemCompanion.preview_dict[preview_name].show()
            
            self.position_window('center left')
            UI_TemCompanion.preview_dict[preview_name].position_window('center right')
            
            # Keep the history
            UI_TemCompanion.preview_dict[preview_name].process['process'].append(f'IFFT from {mask_center}')
            UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
        else:
            QMessageBox.warning(self, 'Mask and iFFT', 'Add mask(s) first!') 
    
            
            
        
#========= Plot canvas for line profile =======================================
class PlotCanvasLineProfile(QMainWindow):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            
            self.main_frame = QWidget()
            self.fig = Figure(figsize=(5, 3), dpi=150)
            self.axes = self.fig.add_subplot(111)
            self.canvas = FigureCanvas(self.fig)
            self.canvas.setParent(self)
            
            self.selector = None
            self.text = None
            self.clear_button = None
            
            #self.plot_lineprofile(p1, p2)
            
            # Create the navigation toolbar, tied to the canvas
            self.mpl_toolbar = LineProfileToolbar(self.canvas, self)        
            vbox = QVBoxLayout()
            vbox.addWidget(self.mpl_toolbar)
            vbox.addWidget(self.canvas)
            self.main_frame.setLayout(vbox)
            self.setCentralWidget(self.main_frame)
            self.create_menubar()
            
            # Right click menu
            self.main_frame.setContextMenuPolicy(Qt.CustomContextMenu)
            self.main_frame.customContextMenuRequested.connect(self.show_context_menu)
            
            # Buttons
            self.buttons = {'measure_clear': None}
            
            self.linewidth = 1
        
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
            
        def create_menubar(self):
            menubar = self.menuBar()
            
            file_menu = menubar.addMenu('&File')
            save_action = QAction('&Save as', self)
            save_action.setShortcut('ctrl+s')
            save_action.triggered.connect(self.mpl_toolbar.save_figure)
            file_menu.addAction(save_action)
            copy_action = QAction('&Copy Plot to Clipboard', self)
            copy_action.setShortcut('ctrl+c')
            copy_action.triggered.connect(self.copy_plot)
            file_menu.addAction(copy_action)
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
            
            measure_horizontal.triggered.connect(self.measure_horizontal)
            measure_menu.addAction(measure_horizontal)
            measure_vertical = QAction('Measure vertical', self)
            
            measure_vertical.triggered.connect(self.measure_vertical)
            measure_menu.addAction(measure_vertical)
            
            settings_menu = menubar.addMenu('&Settings')
            linewidth_setting_action = QAction('&Set line width',self)
            linewidth_setting_action.setShortcut('ctrl+w')
            linewidth_setting_action.triggered.connect(self.linewidth_setting)
            settings_menu.addAction(linewidth_setting_action)

            plotsettings_action = QAction('&Plot Settings', self)
            plotsettings_action.setShortcut('ctrl+o')
            plotsettings_action.triggered.connect(self.plotsetting)
            settings_menu.addAction(plotsettings_action)
            
            self.menubar = menubar
            
        def show_context_menu(self,pos):
            context_menu = QtWidgets.QMenu(self)
            
            file_menu = context_menu.addMenu('File')
            save_action = QAction('Save as')
            save_action.triggered.connect(self.mpl_toolbar.save_figure)
            file_menu.addAction(save_action)
            copy_action = QAction('Copy Plot to Clipboard')
            copy_action.triggered.connect(self.copy_plot)
            file_menu.addAction(copy_action)
            close_action = QAction('Close')
            close_action.triggered.connect(self.close)
            file_menu.addAction(close_action)
            
            
            measure_menu = context_menu.addMenu('Measure')
            measure_horizontal = QAction('Measure horizontal', self)            
            measure_horizontal.triggered.connect(self.measure_horizontal)
            measure_menu.addAction(measure_horizontal)
            measure_vertical = QAction('Measure vertical', self)            
            measure_vertical.triggered.connect(self.measure_vertical)
            measure_menu.addAction(measure_vertical)
            
            settings_menu = context_menu.addMenu('Settings')
            linewidth_setting_action = QAction('&Set line width')
            linewidth_setting_action.triggered.connect(self.linewidth_setting)
            settings_menu.addAction(linewidth_setting_action)
            plotsettings_action = QAction('Plot Settings')
            plotsettings_action.triggered.connect(self.plotsetting)
            settings_menu.addAction(plotsettings_action)
            
            context_menu.exec_(self.mapToGlobal(pos))

        
        def close_all(self):
            plots = list(UI_TemCompanion.preview_dict.keys())
            for plot in plots:
                UI_TemCompanion.preview_dict[plot].close()
            
        def copy_plot(self):
            buf = io.BytesIO()
            
            dpi = 150
            
            self.canvas.figure.savefig(buf, dpi=dpi)
            
            
            self.clipboard = QApplication.clipboard().setImage(QImage.fromData(buf.getvalue()))
            buf.close()
            
            self.fig.canvas.draw_idle()
            

        def plot_lineprofile(self, p1, p2, linewidth=1):  
            self.img_data = self.parent().get_current_img_from_canvas()
            if self.text is not None:
                self.text = None
            self.axes.clear()
            
            self.start_point = p1
            self.stop_point = p2
            lineprofile = profile_line(self.img_data, (p1[1], p1[0]), (p2[1], p2[0]), linewidth=linewidth, reduce_func=np.mean)
            line_x = np.linspace(0, len(lineprofile)-1, len(lineprofile)) * self.parent().scale
            self.axes.plot(line_x, lineprofile, '-', color='red')
            self.axes.tick_params(direction='in')
            self.axes.set_xlabel('Distance ({})'.format(self.parent().units))
            self.axes.set_ylabel('Intensity')
            self.axes.set_xlim(min(line_x), max(line_x))
            y_span = max(lineprofile) - min(lineprofile)
            y_max = max(lineprofile) + y_span * 0.1
            y_min = min(lineprofile) - y_span * 0.1
            self.axes.set_ylim(y_min, y_max)
            self.fig.tight_layout()
            self.canvas.draw_idle()
            
        def update_lineprofile(self, linewidth):
            self.linewidth = linewidth
            # Remove the previous plot
            line = self.axes.get_lines()[0]
            line.remove()
            self.plot_lineprofile(self.start_point, self.stop_point, linewidth=self.linewidth)
            self.parent().update_line_width(linewidth)
            
            
        def closeEvent(self, event):
            if self.parent().mode_control['lineprofile']:
                self.parent().stop_line_profile()
            UI_TemCompanion.preview_dict.pop(self.canvas.canvas_name, None)
            
        def plotsetting(self):
            self.mpl_toolbar.edit_parameters()
            
        def linewidth_setting(self):
            dialog = LineWidthSettingDialog(self.linewidth, parent=self)
            dialog.show()
            


        def on_select_h(self, xmin, xmax):
            distance = xmax - xmin
            if self.text is not None:
                self.text.remove()
                
            ylim = self.axes.get_ylim()
            text_x = distance * 0.1 + xmin
            text_y = ylim[1] - (ylim[1] - ylim[0]) * 0.1
            
            self.text = self.axes.text(text_x, text_y, f'{distance:.4f} ({self.parent().units})',
                                       color='black')
            self.canvas.draw_idle()
            
        def on_select_v(self,ymin,ymax):
            distance = ymax - ymin
            if self.text is not None:
                self.text.remove()
                
            xlim = self.axes.get_xlim()
            text_x = xlim[1] - (xlim[1] - xlim[0]) * 0.3
            text_y = ymax - distance * 0.1
            self.text = self.axes.text(text_x, text_y, f'{distance:.0f} (Counts)',
                                       color='black')
            self.canvas.draw_idle()
            
        def cleanup(self):
            if self.selector is not None:
                self.selector.set_active(False)
                self.selector.set_visible(False)
                self.selector = None   
            if self.text is not None:
                self.text.remove()
                self.text = None
            
            if self.clear_button is not None:
                self.clear_button.hide()
                self.clear_button = None
            
            self.fig.canvas.draw_idle()
            
        def measure_horizontal(self):            
            self.measure_span('horizontal')
                
            
        def measure_vertical(self):
            self.measure_span('vertical')
            
        def measure_span(self, direction):
            if direction == 'horizontal':
                onselect = self.on_select_h
            elif direction == 'vertical':
                onselect = self.on_select_v
            if self.selector is None:
                self.selector = SpanSelector(self.axes, onselect=onselect, interactive=True, useblit=True,
                                             direction=direction,
                                             drag_from_anywhere=True,
                                             button=[1],
                                             )
                 # Clear button
                self.clear_button = QPushButton('Clear', parent=self.canvas)
                self.clear_button.move(10, 10)
                self.clear_button.clicked.connect(self.cleanup)
             
                self.selector.set_active(True)
                self.clear_button.show()
                self.fig.canvas.draw_idle()   
            


#========= Redefined window for image edit button =============================
class CustomSettingsDialog(QDialog):
    def __init__(self, ax, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Image Settings")
        self.ax = ax
        #self.img = ax.get_images()[0] if ax.get_images() else None
        self.img = self.parent().plotcanvas.im
        self.scalebar_settings = self.parent().plotcanvas.scalebar_settings
        
        self.colorbar = QCheckBox('Colorbar', self)
        if self.parent().plotcanvas.colorbar is not None:
            self.colorbar.setChecked(True)
        else:
            self.colorbar.setChecked(False)
        
        self.original_settings = {}
        self.original_settings['scalebar'] = copy.copy(self.scalebar_settings)
        # Create the layout
        layout = QVBoxLayout()
        
        # vmin and vmax slider
        vminmax_label = QLabel('vmin/max')
        self.doubleslider = QDoubleRangeSlider(Qt.Orientation.Horizontal)
        self.doubleslider.valueChanged.connect(self.update_clim)
        self.colorbar.stateChanged.connect(self.set_colorbar)
        
        h_box = QHBoxLayout()
        h_box.addWidget(vminmax_label)
        h_box.addWidget(self.doubleslider)
        layout.addLayout(h_box)

        
        h_layout_vmin = QHBoxLayout()
        self.vmin_label = QLabel("vmin:")
        self.vmin_input = QLineEdit()
        self.vmin_input.resize(40, 10)
        self.vmin_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.vmin_button = QPushButton('Set', self)
        self.vmin_button.clicked.connect(self.set_vminmax)
        h_layout_vmin.addWidget(self.vmin_label)
        h_layout_vmin.addWidget(self.vmin_input)
        h_layout_vmin.addWidget(self.vmin_button)
        layout.addLayout(h_layout_vmin)

        h_layout_vmax = QHBoxLayout()
        self.vmax_label = QLabel("vmax:")
        self.vmax_input = QLineEdit()
        self.vmax_input.resize(40, 10)
        self.vmax_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.vmax_button = QPushButton('Set', self)
        self.vmax_button.clicked.connect(self.set_vminmax)
        h_layout_vmax.addWidget(self.vmax_label)
        h_layout_vmax.addWidget(self.vmax_input)
        h_layout_vmax.addWidget(self.vmax_button)
        layout.addLayout(h_layout_vmax)
        
        
        
        
        
        # Set current vmin and vmax
        if self.img:
            vmin, vmax = self.img.get_clim()
            dmin = np.percentile(self.img._A, 0.01)            
            dmax = np.percentile(self.img._A, 99.9)
            self.doubleslider.setRange(dmin, dmax)
            self.doubleslider.setValue((vmin, vmax))
            self.vmin_input.setText(f'{vmin:.2f}')
            self.vmax_input.setText(f'{vmax:.2f}')
            
            self.original_settings['vmin/max'] = (vmin, vmax)
            self.original_settings['dmin/max'] = (dmin, dmax)
        

        

        # Colormap dropdown
        h_layout_cmap = QHBoxLayout()
        self.cmap_label = QLabel("Colormap:")
        self.cmap_combobox = QComboBox()
        colormaps = ['viridis', 'plasma', 'inferno', 'magma', 'cividis',
                     'gray', 'spring', 'summer', 'autumn', 'winter', 'cool',
                      'Wistia', 'hot',
                     'Red', 'Orange', 'Yellow', 'Green', 'Cyan', 'Lime', 'Purple',
                     'Magenta', 'Pink', 'Blue', 'Maize',
                     'jet', 'rainbow', 'turbo', 'hsv', 'seismic'
                     ]
        self.cmap_combobox.addItems(colormaps)
        h_layout_cmap.addWidget(self.cmap_label)
        h_layout_cmap.addWidget(self.cmap_combobox)
        h_layout_cmap.addWidget(self.colorbar)
        layout.addLayout(h_layout_cmap)

        # Set current colormap
        if self.img:
            cmap = self.img.get_cmap().name
            self.cmap_combobox.setCurrentText(cmap)
            self.original_settings['cmap'] = cmap
            
        # Update colormap if changed
        self.cmap_combobox.currentTextChanged.connect(self.update_colormap)
        

        
            
        # Scalebar customization
        
        self.scalebar_check = QCheckBox("Add scalebar to image")
        self.scalebar_check.setChecked(self.scalebar_settings['scalebar'])
        self.scalebar_check.stateChanged.connect(self.update_scalebar)
        
        layout.addWidget(self.scalebar_check)
        h_layout_scalebar = QHBoxLayout()
        self.sbcolor_label = QLabel('Scalebar color')
        self.sbcolor_combobox = QComboBox()
        sbcolor = ['black', 'white', 'red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'purple']
        self.sbcolor_combobox.addItems(sbcolor)
        self.sbcolor_combobox.setCurrentText(self.scalebar_settings['color'])
        self.sbcolor_combobox.currentTextChanged.connect(self.update_scalebar)
        
        
        h_layout_scalebar.addWidget(self.sbcolor_label)
        h_layout_scalebar.addWidget(self.sbcolor_combobox)
        
        h_layout_loc = QHBoxLayout()
        self.sbloc_label = QLabel('Scalebar location')
        self.sblocation_combox = QComboBox()
        sbloc = ['lower left', 'lower right', 'lower center', 'upper left', 'upper right', 'upper center']
        self.sblocation_combox.addItems(sbloc)
        self.sblocation_combox.setCurrentText(self.scalebar_settings['location'])
        self.sblocation_combox.currentTextChanged.connect(self.update_scalebar)
        h_layout_loc.addWidget(self.sbloc_label)
        h_layout_loc.addWidget(self.sblocation_combox)
        
        h_layout_scaleloc = QHBoxLayout()
        self.scaleloc_label = QLabel('Text location')
        self.scaleloc = QComboBox()
        scaleloc = ['top', 'bottom', 'left', 'right', 'none'] 
        self.scaleloc.addItems(scaleloc)
        self.scaleloc.setCurrentText(self.scalebar_settings['scale_loc'])
        self.scaleloc.currentTextChanged.connect(self.update_scalebar)
        h_layout_scaleloc.addWidget(self.scaleloc_label)
        h_layout_scaleloc.addWidget(self.scaleloc)
        layout.addLayout(h_layout_scalebar)
        layout.addLayout(h_layout_loc)
        layout.addLayout(h_layout_scaleloc)

        # Apply button
        buttons = QDialogButtonBox(QDialogButtonBox.Reset | QDialogButtonBox.Ok)
        self.reset_button = buttons.button(QDialogButtonBox.Reset)
        self.reset_button.clicked.connect(self.reset_settings)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.ok_button.clicked.connect(self.accept)
        
        layout.addWidget(buttons)
        

        self.setLayout(layout)
        
    def update_clim(self):
        # Apply vmin and vmax
        vmin, vmax = self.doubleslider.value()
        self.vmin_input.setText(f'{vmin:.2f}')
        self.vmax_input.setText(f'{vmax:.2f}')
        self.img.set_clim(vmin,vmax)
        if self.colorbar.isChecked():
            self.parent().plotcanvas.colorbar.set_ticks([vmin,vmax])
        self.ax.figure.canvas.draw_idle()
    
    def set_colorbar(self):
        if self.colorbar.isChecked():
            self.parent().plotcanvas.create_colorbar()
        else:
            self.parent().plotcanvas.remove_colorbar()
    
    
    def set_vminmax(self):
        try:
            vmin = float(self.vmin_input.text())
            
        except:
            QMessageBox.warning(self, 'Invalid vmin', 'vmin must be a number!')
            return
        
        try:
            vmax = float(self.vmax_input.text())
        except:
            QMessageBox.warning(self, 'Invalid vmax', 'vmax must be a number!')
            return
        
        if vmin < self.doubleslider.minimum():
            self.doubleslider.setMinimum(vmin)
        if vmax > self.doubleslider.maximum():
            self.doubleslider.setMaximum(vmax)
        self.doubleslider.setValue((vmin, vmax))
        
        
        
        
    def update_colormap(self):
        # Apply colormap
        self.cmap_name = self.cmap_combobox.currentText()
        if self.cmap_name in custom_cmap.keys():
            self.cmap_name = custom_cmap[self.cmap_name]
        self.img.set_cmap(self.cmap_name)
        self.ax.figure.canvas.draw_idle()
    
    def update_scalebar(self):
        # Apply scalebar styles
        self.scalebar_settings['scalebar'] = self.scalebar_check.isChecked()
        self.scalebar_settings['color'] = self.sbcolor_combobox.currentText()
        self.scalebar_settings['location'] = self.sblocation_combox.currentText()
        self.scalebar_settings['scale_loc'] = self.scaleloc.currentText()
        
        self.parent().apply_scalebar()
        self.ax.figure.canvas.draw_idle()
        
    
    def reset_settings(self):
        # Reset scalebar
        self.scalebar_check.setChecked(self.original_settings['scalebar']['scalebar'])
        self.sbcolor_combobox.setCurrentText(self.original_settings['scalebar']['color'])
        self.sblocation_combox.setCurrentText(self.original_settings['scalebar']['location'])
        self.scaleloc.setCurrentText(self.original_settings['scalebar']['scale_loc'])
        self.update_scalebar()
        
        # Reset vmin vmax
        self.doubleslider.setRange(*self.original_settings['dmin/max'])
        self.doubleslider.setValue(self.original_settings['vmin/max'])
        self.update_clim()
        
        # Reset colormap
        self.cmap_combobox.setCurrentText(self.original_settings['cmap'])
        self.update_colormap()

#============ Redefined custom color maps transitioning from black ============
# Redefine color maps for pure colors to transition from black
custom_cmap = {}
n_bins = 255  # Number of discrete colors to use in the colormap
base_colors = {'Red': (1,0,0),
               'Orange': (1,69/255,0),
               'Yellow': (1,1,0),
               'Green': (0,1,0),
               'Cyan': (0,1,1),
               'Lime': (0,0,1),
               'Purple': (128/255, 0, 128/255),
               'Magenta': (1,0,1),
               'Pink': (1,192/255,203/255),
               'Blue': (0, 39/255, 76/255),
               'Maize': (1, 203/255, 5/255)
                }
# Generate colors from the base color dictionary
for key, value in base_colors.items():
    colors = [(0,0,0), value] # Black to the color    
    # Create a colormap
    cmap_name = key
    cm = LinearSegmentedColormap.from_list(cmap_name, colors, N=n_bins)
    custom_cmap[key] = cm

#============ Define a custom toolbar to handle the save function==============
class CustomToolbar(NavigationToolbar):
    def __init__(self, canvas, parent=None):
        super().__init__(canvas, parent)
        
        self.imgsetting_dialog = None
        self.plotcanvas = parent
        self.scalebar_settings = self.plotcanvas.scalebar_settings
        self.remove_button('Subplots')
        
        

    def remove_button(self,text):
        # The button we want to remove is 'Subplots' (usually the seventh item in the toolbar)
        # We can remove by finding its index and removing it
        for action in self.actions():
            if action.text() == text:
                self.removeAction(action)
                break
        
    def save_figure(self, *args):       
        # Replace the save figure to use PIL and tif_writer
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
            for key in ['data', 'axes', 'original_axes', 'metadata', 'original_metadata']:
                if key in self.canvas.data.keys():
                    img_to_save[key] = self.canvas.data[key]
            if self.selected_type == 'Pickle Dictionary Files (*.pkl)':
                with open(self.file_path, 'wb') as f:
                    pickle.dump(img_to_save, f)
            else:                            
                # Check if the image is 3D
                if isinstance(self.canvas.img_idx, int):
                    img_to_save['data'] = img_to_save['data'][self.canvas.img_idx] 
                    # Hide the slider bar for savefig
                    self.canvas.figure.axes[1].set_visible(False)
                    
                if self.selected_type == '16-bit TIFF Files (*.tiff)':
                    
                    save_as_tif16(img_to_save, self.f_name, self.output_dir)
                elif self.selected_type == '32-bit TIFF Files (*.tiff)':
                    save_as_tif16(img_to_save, self.f_name, self.output_dir, dtype='float32')
                    
                elif self.selected_type in ['8-bit Grayscale TIFF Files (*.tiff)','Grayscale PNG Files (*.png)', 'Grayscale JPEG Files (*.jpg)']:
                    save_with_pil(img_to_save, self.f_name, self.output_dir, self.file_type, scalebar=self.plotcanvas.scalebar_settings['scalebar']) 
                else:
                    # Save with matplotlib. Need to calculate the dpi to keep the original size
                    figsize = self.canvas.figure.get_size_inches()
                    img_size = img_to_save['data'].shape
                    dpi = float(sorted(img_size/figsize, reverse=True)[0])                                        
                    self.canvas.figure.savefig(self.file_path, dpi=dpi, format=self.file_type)
                    
                if isinstance(self.canvas.img_idx, int):
                    self.canvas.figure.axes[1].set_visible(True)
                
                
    # Redefine the edit axis button
    def edit_parameters(self):
        """Override the default edit_parameters to use a custom dialog."""
        #if self.canvas.figure:
        axes = self.canvas.figure.get_axes()
        if not axes:
            return
            
        # Always select the image axis which is the first
        selected_axes = axes[0]

        self.imgsetting_dialog = CustomSettingsDialog(selected_axes, parent=self)
        self.imgsetting_dialog.exec_()
        
    def apply_scalebar(self):
        if self.imgsetting_dialog is not None:
            self.plotcanvas.scalebar_settings = self.imgsetting_dialog.scalebar_settings
            
            # Remove the original scalebar
            if  self.plotcanvas.scalebar is not None:
                self.plotcanvas.scalebar.remove()
                self.plotcanvas.scalebar = None
            
            # Apply the new style
            if self.plotcanvas.scalebar_settings['scalebar']:
                self.plotcanvas.create_scalebar()
            
            
            
#============ Toolbar for the lineprofile ======================================
class LineProfileToolbar(NavigationToolbar):
    def __init__(self, canvas, parent=None):
        super().__init__(canvas, parent)
        
        self.remove_button('Subplots')

    def remove_button(self,text):
        # The button we want to remove is 'Subplots' (usually the seventh item in the toolbar)
        # We can remove by finding its index and removing it
        for action in self.actions():
            if action.text() == text:
                self.removeAction(action)
                break
            
    # Redefine the save button to handle export
    def save_figure(self, *args):
        # Replace the save figure to use PIL and tif_writer
        options = QFileDialog.Options()
        self.file_path, self.selected_type = QFileDialog.getSaveFileName(self.parent(), 
                                                   "Export Figure", 
                                                   "", 
                                                   "Color PNG Files (*.png);;Color JPEG Files (*.jpg);;Comma Separated Values (*.csv)", 
                                                   options=options)
        if self.file_path:
            self.file_type = getFileType(self.file_path)
            if self.selected_type in ['Color PNG Files (*.png)', 'Color JPEG Files (*.jpg)']:
                self.canvas.figure.savefig(self.file_path, dpi=150, format=self.file_type)
            elif self.selected_type == 'Comma Separated Values (*.csv)':
                ax = self.canvas.figure.get_axes()[0]
                x_label = ax.get_xlabel()
                lineprof = ax.get_lines()[0]
                line_x, line_y = lineprof.get_data()
                with open(self.file_path, 'w') as f:
                    f.write(f'{x_label}, Intensity\n')
                    for i in range(len(line_x)):
                        f.write(f'{line_x[i]}, {line_y[i]}\n')
                        
                        
    # Redefine the edit axis button
    def edit_parameters(self):
        """Override the default edit_parameters to use a custom dialog."""
        if self.canvas.figure:
            axes = self.canvas.figure.get_axes()
            if not axes:
                return
            if len(axes) > 1:
                selected_axes, ok = QInputDialog.getItem(
                    self, "Edit Plot",
                    "Select the axes to edit",
                    [ax.get_title() or f"Axes {i + 1}" for i, ax in enumerate(axes)],
                    current=0,
                    editable=False
                )
                if not ok:
                    return
                selected_axes = axes[
                    [ax.get_title() or f"Axes {i + 1}" for i, ax in enumerate(axes)]
                    .index(selected_axes)
                ]
            else:
                selected_axes = axes[0]

            dialog = LineProfileSettingDialog(selected_axes, parent=self)
            dialog.exec_()
                                
                
    
            
            

#=========== Define file selection window for preview ===================================================        
class select_img_for_preview(QDialog):
    def __init__(self):
        super().__init__()
        
        self.selected_file = None  # Initialize the selected_file variable

        # Set up the dialog
        self.setWindowTitle('Select a file to preview')
        self.setGeometry(100, 100, 300, 200)

        # Create a QListView widget
        self.list_view = QListView()

        # Create a model and set it to the QListView
        self.model = QStringListModel()
        self.list_view.setModel(self.model)

        # Create an OK button
        self.ok_button = QPushButton('Preview')
        self.ok_button.clicked.connect(self.handle_ok)

        # Create a layout and add the list view and OK button to it
        layout = QVBoxLayout()
        layout.addWidget(self.list_view)
        layout.addWidget(self.ok_button)

        # Set the layout to the dialog
        self.setLayout(layout)

    def set_items(self, items):
        """Set the items in the list view."""
        self.model.setStringList(items)

    def handle_ok(self):
        """Handle the OK button click and return the selected item."""
        indexes = self.list_view.selectedIndexes()
        if indexes:
            # Get the selected item from the model
            self.selected_file = self.model.data(indexes[0], 0)
            self.accept()  # Close the dialog and return from exec_()
        else:
            QMessageBox.warning(self, 'No Selection', 'Select one file to preview!')
            

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

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Metadata'])
        self.setCentralWidget(self.tree)
        self.metadata = metadata
        self.create_menubar()

        self.populate_tree(metadata)
        
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

    def populate_tree(self, data, parent=None):
        if parent is None:
            parent = self.tree.invisibleRootItem()

        if isinstance(data, dict):
            for key, value in data.items():
                item = QTreeWidgetItem([key])
                parent.addChild(item)
                self.populate_tree(value, item)
        elif isinstance(data, list):
            for index, value in enumerate(data):
                item = QTreeWidgetItem([f"[{index}]"])
                parent.addChild(item)
                self.populate_tree(value, item)
        else:
            item = QTreeWidgetItem([str(data)])
            parent.addChild(item)
            
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

# ================== Line Width setting dialog ===================
class LineProfileSettingDialog(QDialog):
    def __init__(self, ax, parent=None):
        super().__init__(parent)
        self.ax = ax
        self.line = ax.get_lines()[0] if ax.get_lines() else None

        self.setWindowTitle("Line Width Settings")
        self.linewidth = 1
        
        # Create the layout
        layout = QVBoxLayout()
        
        


        # Axes range inputs
        h_layout_xmin = QHBoxLayout()
        self.xmin_label = QLabel("Xmin:")
        self.xmin_input = QLineEdit()
        h_layout_xmin.addWidget(self.xmin_label)
        h_layout_xmin.addWidget(self.xmin_input)
        layout.addLayout(h_layout_xmin)

        h_layout_xmax = QHBoxLayout()
        self.xmax_label = QLabel("Xmax:")
        self.xmax_input = QLineEdit()
        h_layout_xmax.addWidget(self.xmax_label)
        h_layout_xmax.addWidget(self.xmax_input)
        layout.addLayout(h_layout_xmax)
        
        h_layout_ymin = QHBoxLayout()
        self.ymin_label = QLabel("Ymin:")
        self.ymin_input = QLineEdit()
        h_layout_ymin.addWidget(self.ymin_label)
        h_layout_ymin.addWidget(self.ymin_input)
        layout.addLayout(h_layout_ymin)

        h_layout_ymax = QHBoxLayout()
        self.ymax_label = QLabel("Ymax:")
        self.ymax_input = QLineEdit()
        h_layout_ymax.addWidget(self.ymax_label)
        h_layout_ymax.addWidget(self.ymax_input)
        layout.addLayout(h_layout_ymax)
        
        

        # Set current range
        if self.ax:
            xmin, xmax = self.ax.get_xlim()
            ymin, ymax = self.ax.get_ylim()

            self.xmin_input.setText(f'{xmin:.2f}')
            self.xmax_input.setText(f'{xmax:.2f}')            
            self.ymin_input.setText(f'{ymin:.2f}')
            self.ymax_input.setText(f'{ymax:.2f}')
        

        # Line color dropdown
        h_layout_color = QHBoxLayout()
        self.color_label = QLabel("Line Color:")
        self.color_combobox = QComboBox()
        colors = ['black', 'gray', 'brown', 'red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'purple']
        self.color_combobox.addItems(colors)
        h_layout_color.addWidget(self.color_label)
        h_layout_color.addWidget(self.color_combobox)
        layout.addLayout(h_layout_color)

        # Set current color
        if self.line:
            current_color = self.line.get_color()
            self.color_combobox.setCurrentText(current_color)
            

        # Apply button
        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Ok)
        self.apply_button = buttons.button(QDialogButtonBox.Apply)
        self.apply_button.clicked.connect(self.apply_settings)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.ok_button.clicked.connect(self.handle_ok)
        
        layout.addWidget(buttons)
        

        self.setLayout(layout)

    def apply_settings(self):
        if not self.line:
            print("No line profile present in the axes.")
            return
          
        # Apply axes ranges
        try:
            xmin = float(self.xmin_input.text())
            xmax = float(self.xmax_input.text())
            ymin = float(self.ymin_input.text())
            ymax = float(self.ymax_input.text())

        except ValueError:
            QMessageBox.warning(self, 'Line profile settings', 'Invalid min or max values!')
            return
            
        
        # if xmin >= xmax or ymin >= ymax:
        #    QMessageBox.warning(self, 'Line profile settings', 'Invalid min or max value!')
        #    return
       
        else:
            self.ax.set_xlim(xmin, xmax)
            self.ax.set_ylim(ymin, ymax)


        # Apply color
        self.color_name = self.color_combobox.currentText()
        self.line.set_color(self.color_name)
        # Redraw the canvas
        self.ax.figure.canvas.draw_idle()
    
    def handle_ok(self):
        self.apply_settings()
        self.accept()
        
# ================== Line width setting dialog =============================
class LineWidthSettingDialog(QDialog):
    def __init__(self, linewidth, parent=None):
        super().__init__(parent)
        self.linewidth = linewidth
        
        
        # Line width 
        self.layout = QVBoxLayout()
        self.linewidth_label = QLabel("Line width:")
        self.linewidth_input = QLineEdit()
        self.linewidth_input.setText(f'{self.linewidth}')
        self.layout.addWidget(self.linewidth_label)
        self.layout.addWidget(self.linewidth_input)
        
        
        # Apply button
        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Ok)
        self.apply_button = buttons.button(QDialogButtonBox.Apply)
        self.apply_button.clicked.connect(self.apply_settings)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.ok_button.clicked.connect(self.handle_ok)
        
        self.layout.addWidget(buttons)
        self.setLayout(self.layout)
        
    def apply_settings(self):
        try:
            self.linewidth = int(self.linewidth_input.text())
        except:
            QMessageBox.warning(self, 'Line Width Setting', 'Line width must be integer!')
        self.parent().update_lineprofile(self.linewidth)
        
    def handle_ok(self):
        self.apply_settings()
        self.accept()
        
        
        
        
            
# ================== Measure results window =======================
class MeasurementDialog(QDialog):
    def __init__(self, distance, ang, units, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Measurement")
        self.units = units

        QBtn = QDialogButtonBox.Ok
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.ok_pressed)

        self.layout = QVBoxLayout()
        self.message = QLabel(f"Distance: {distance:.2f} {self.units}")
        self.layout.addWidget(self.message)
        self.message2 = QLabel(f"Angle: {ang:.2f} degrees")
        self.layout.addWidget(self.message2)
        
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
    
    def update_measurement(self, distance, angle):
        self.message.setText(f"Distance: {distance:.2f} {self.units}")
        self.message2.setText(f"Angle: {angle:.2f} degrees")
        
    def ok_pressed(self):
        self.parent().stop_distance_measurement()
        self.accept()
    
    def closeEvent(self, event):
        self.parent().stop_distance_measurement()
        
        

# #==================== Measure FFT results window ===================
class MeasureFFTDialog(QDialog):
    def __init__(self, distance, ang, units, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Measurement")
        self.units = units
        self.windowsize = 10
        
        QBtn = QDialogButtonBox.Ok
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.ok_pressed)

        self.layout = QVBoxLayout()
        self.message = QLabel(f"d-spacing: {distance:.3f} {self.units}")
        self.layout.addWidget(self.message)
        self.message2 = QLabel(f"Angle: {ang:.2f} degrees")
        self.layout.addWidget(self.message2)
        
        
        self.window_slider = QSlider(QtCore.Qt.Horizontal)
        self.window_slider.setRange(1, 50)
        self.window_slider.setValue(10)        
        self.slider_label = QLabel(f'Window size: {self.windowsize}')
        self.layout.addWidget(self.slider_label)
        self.layout.addWidget(self.window_slider)
        
       
        
        self.layout.addWidget(self.buttonBox)
        
        self.setLayout(self.layout)
        
        self.window_slider.valueChanged.connect(self.update_window_size)
        
    def update_window_size(self):
        self.windowsize = self.window_slider.value()
        self.slider_label.setText(f'Window size: {self.windowsize}')
        
    def update_measurement(self, distance, angle):
        self.message.setText(f"d-spacing: {distance:.3f} {self.units}")
        self.message2.setText(f"Angle: {angle:.2f} degrees")
        
    def ok_pressed(self):
        self.parent().stop_fft_measurement()
        self.accept()
        
    def closeEvent(self, event):
         self.parent().stop_fft_measurement()
         
    def position_window(self, pos='center'):
        # Set the window pop up position
        # Possible positions are:
        # 'center': screen center
        # 'center left': left side with the right edge on the screen center
        # 'center right': right side with the left edge on the screen
        # 'next to parent': the left edge next to its parent window
        
        # Get screen resolution
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        frame_size = self.geometry()
        
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
        
        # solver_layout = QHBoxLayout()
        # solver_label = QLabel("Number of g vectors:")
        # self.solver_2g = QRadioButton("2")
        # self.solver_2g.setChecked(True)
        # self.solver_3g = QRadioButton("3")
        # solver_group = QButtonGroup(self)
        # solver_group.addButton(self.solver_2g)
        # solver_group.addButton(self.solver_3g)
        # solver_layout.addWidget(solver_label)
        # solver_layout.addWidget(self.solver_2g)
        # solver_layout.addWidget(self.solver_3g)
        # layout.addLayout(solver_layout)
        
        
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
            
        # if self.solver_2g.isChecked():
        #     self.n_masks = 2
        # if self.solver_3g.isChecked():
        #     self.n_masks = 3
        
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
        if iDPC_img['data'].ndim == 2:
            plot = PlotCanvas(iDPC_img, parent=self.parent())
        elif iDPC_img['data'].ndim == 3:
            plot = PlotCanvas3d(iDPC_img, parent=self.parent())
        preview_name = self.parent().canvas.canvas_name.split(':')[0] + '_iDPC'
        plot.setWindowTitle(preview_name)
        plot.canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name] = plot
        UI_TemCompanion.preview_dict[preview_name].show()
        UI_TemCompanion.preview_dict[preview_name].position_window('center')
        
        # Keep the history
        if self.from4_img.isChecked():
            UI_TemCompanion.preview_dict[preview_name].process['process'].append(f'Reconstructed from {self.imA.currentText()}, {self.imB.currentText()}, {self.imC.currentText()}, and {self.imD.currentText()} by a rotation angle of {self.rot.text()}.')
        else:
            UI_TemCompanion.preview_dict[preview_name].process['process'].append(f'Reconstructed from {self.imX.currentText()} and {self.imY.currentText()} by a rotation angle of {self.rot.text()}.')
        UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
    
    def reconstruct_dDPC(self):
        A, DPCx, DPCy = self.prepare_images()
        if DPCx is None:
            return
            
        dDPC_img = copy.deepcopy(A)
        dDPC_img['data'] = reconstruct_dDPC(DPCx, DPCy, rotation=float(self.rot.text()))
        if dDPC_img['data'].ndim == 2:
            plot = PlotCanvas(dDPC_img, parent=self.parent())
        elif dDPC_img['data'].ndim == 3:
            plot = PlotCanvas3d(dDPC_img, parent=self.parent())
        preview_name = self.parent().canvas.canvas_name.split(':')[0] + '_dDPC'
        plot.setWindowTitle(preview_name)
        plot.canvas.canvas_name = preview_name
        UI_TemCompanion.preview_dict[preview_name] = plot
        UI_TemCompanion.preview_dict[preview_name].show()
        UI_TemCompanion.preview_dict[preview_name].position_window('center')
        
        # Keep the history
        if self.from4_img.isChecked():
            UI_TemCompanion.preview_dict[preview_name].process['process'].append(f'Reconstructed from {self.imA.currentText()}, {self.imB.currentText()}, {self.imC.currentText()}, and {self.imD.currentText()} by a rotation angle of {self.rot.text()}.')
        else:
            UI_TemCompanion.preview_dict[preview_name].process['process'].append(f'Reconstructed from {self.imX.currentText()} and {self.imY.currentText()} by a rotation angle of {self.rot.text()}.')
        UI_TemCompanion.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(UI_TemCompanion.preview_dict[preview_name].process)
        
        
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
            
            
            for file in self.files:  
                # convert_file(file,output_dir,f_type)
                msg = "Converting '{}.{}'".format(getFileName(file),getFileType(file))
                self.refresh_output(msg)
                
                ext = getFileType(file)
                if ext == 'emd':
                    self.filetype = 'Velox emd Files (*.emd)'
                elif ext in ['dm3', 'dm4']:
                    self.filetype = 'DigitalMicrograph Files (*.dm3 *.dm4)'
                elif ext == 'ser':
                    self.filetype = 'TIA ser Files (*.ser)'
                elif ext in ['tif', 'tiff']:
                    self.filetype = 'Tiff Files (*.tif *.tiff)'
                elif ext in ['jpg', 'jpeg', 'png', 'bmp']:
                    self.filetype = 'Image Formats (*.tif *.tiff *.jpg *.jpeg *.png *.bmp)'
                elif ext == 'pkl':
                    self.filetype = 'Pickle Dictionary Files (*.pkl)'
                else:
                    QMessageBox.warning(self, 'Open File', 'Unsupported file formats!')
                    return
                
                try:                
                    convert_file(file,self.filetype, self.output_dir,self.f_type, save_metadata=save_metadata, scalebar = self.scale_bar,
                                 apply_wf = self.apply_wf, delta_wf = delta_wf, order_wf = order_wf, cutoff_wf = cutoff_wf,
                                 apply_absf = self.apply_absf, delta_absf = delta_absf, order_absf = order_absf, cutoff_absf = cutoff_absf,
                                 apply_nl = self.apply_nl, N = N, delta_nl = delta_nl, order_nl = order_nl, cutoff_nl = cutoff_nl,
                                 apply_bw = self.apply_bw, order_bw = order_bw, cutoff_bw = cutoff_bw,
                                 apply_gaussian = self.apply_gaussian, cutoff_gaussian = cutoff_gaussian
                                 )
                    
                    msg = "'{}.{}' has been converted".format(getFileName(file),getFileType(file))
                    self.refresh_output(msg)
    
    
                except:
                    msg = "'{}.{}' has been skipped".format(getFileName(file),getFileType(file))
                    self.refresh_output(msg)
    
            self.refresh_output("Conversion finished!") 
            
        





            
            
            
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
#from rsciio.image import file_writer as im_writer
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


def norm_img(data):
    #Normalize a data array
    data = data.astype('float32') #Int32 for calculation
    norm = (data - data.min())/(data.max()-data.min())
    return norm

#@run_in_executor
def apply_filter(img, filter_type, **kwargs):
    filter_dict = {'Wiener': filters.wiener_filter,
                   'ABS': filters.abs_filter,
                   'NL': filters.nlfilter,
                   'BW': filters.bw_lowpass,
                   'Gaussian': filters.gaussian_lowpass
                   }
    
    
    if filter_type in filter_dict.keys():
        img = filters.crop_to_square(img)
        
        result = filter_dict[filter_type](img, **kwargs)
        if filter_type in ['Wiener', 'ABS', 'NL']:
            return result[0]
        elif filter_type in ['BW', 'Gaussian']:
            return result


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
            except:
                pass
        
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
                    img_valid['original_axes'] = img_dict['original_axes']
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
                    except:
                        pass
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
                    except:
                        pass
                    with open(new_dir + title + '_metadata.json', 'w') as j_file:
                        json.dump(metadata_to_save, j_file, indent=4)
                
                
                for idx in range(stack_num):
                    new_img = {'data': data[idx],
                               'axes': axes,
                               'metadata': metadata
                        }
                    new_name = title + '_{}'.format(idx)
                    
                    save_file_as(new_img, new_name, new_dir, f_type, **kwargs)
                    
                    
                    
                           
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



#===== GPA functions ==================================
# Conventional GPA
def get_phase_fft(img, k, r, edge_blur=0.3):
    '''Calculate phase from masked iFFT image
    Bansed on Hÿtch 1998
    r : int
        Size of the circular mask to place over the reflection
    edge_blur : float, optional
        Fraction of pixels at the edge that will be smoothed by a cosine function.
    '''
    im_y, im_x = img.shape
    cx, cy = im_x // 2, im_y // 2
    x = np.arange(im_x)
    y = np.arange(im_y)
    X, Y = np.meshgrid(x, y)
    
    # calculate the fft and mask only on one side
    fft = fftshift(fft2(img)) 
    kx, ky = k
    # need to calculate the coordinates for mask
    x = int(kx * im_x + cx)
    y = int(ky * im_y + cy)
    m = create_mask((im_y, im_x), [(x, y)], [r], edge_blur)
    fft_m = fft * m
    # calculate complex valued ifft
    ifft_m = ifft2(ifftshift(fft_m))
    # raw phase 
    phifft_m = np.angle(ifft_m)
    # corrected phase  
    P = phifft_m - 2*np.pi*(kx*X+ky*Y)
    return P
    
    
def calc_strains(P, ks):
    """
    Calculate strain with two g vectors and phases
    P : numpy array of phase image (2,m,n)
    ks: k vectors (2, 2)
    Returns
    -------
    im_exx : numpy array
        The epsilon_xx strain component 
    im_eyy : numpy array
        The epsilon_yy strain component 
    im_exy : numpy array
        Epsilon_yx = (epsilon_yx), the shear strain
    im_oxy : numpy array
        omega_xy = -omega_yx, the rotation component
    """
    # Calculate the phase derivatives

    dP1dy = calc_derivative(P[0,:,:], 0) 
    dP1dx = calc_derivative(P[0,:,:], 1)
    dP2dy = calc_derivative(P[1,:,:], 0)
    dP2dx = calc_derivative(P[1,:,:], 1)
    
    # calculate lattice points a1 and a2    
    [a1x, a2x], [a1y, a2y] = np.linalg.inv(ks)
    
    # the strain components
    exx = -1/(2*np.pi)*(a1x*dP1dx+a2x*dP2dx)
    exy = -1/(2*np.pi)*(a1x*dP1dy+a2x*dP2dy)
    eyx = -1/(2*np.pi)*(a1y*dP1dx+a2y*dP2dx)
    eyy = -1/(2*np.pi)*(a1y*dP1dy+a2y*dP2dy)
    
    Exy = (exy + eyx) / 2
    oxy = (exy - eyx) / 2

    return exx, eyy, Exy, oxy



def create_mask(img_size, center, radius, edge_blur=0.3):
    '''
    Generate a circle mask from a given point and radius
    img_size: tuple of original (FFT) image size
    center: list of tuple of the mask center
    radius: lisf of float of the radius in pixel, length must be equal to center
    edge_width: fload of the smoothed edge in pixel
    '''      
    # Create a grid of coordinates
    Y, X = np.ogrid[:img_size[0], :img_size[1]]
    mask = np.zeros(img_size, dtype=float) 
    
    for i in range(len(center)):
        x_center, y_center = center[i]
        r = radius[i]
        # Calculate the Euclidean distance from each grid point to the circle's center
        distance = np.sqrt((X - x_center)**2 + (Y - y_center)**2)
        
        edge_width = int(r * edge_blur)
    
        # Create the base circle mask: inside the circle is 1, outside is 0
        inside_circle = (distance <= r - edge_width)
        outside_circle = (distance >= r)
    
        # Transition zone
        transition_zone = ~inside_circle & ~outside_circle
        
        # Smooth edge with a cosine function
        transition_distance = (distance - r) / edge_width
        transition_mask = 0.5 * (1 + np.cos(np.pi * transition_distance))
    
        # Combine masks
        mask[inside_circle] = 1
        mask[transition_zone] = transition_mask[transition_zone]

    return mask


def refine_center(img, g, r):
    '''
    Refine the g vector center with center of mass
    g: tuple of (x, y)
    r: radius for window size
    '''
    window_size = r
    x = int(g[0])
    y = int(g[1])
    x_min = max(x - window_size, 0)
    x_max = min(x + window_size, img.shape[1])
    y_min = max(y - window_size, 0)
    y_max = min(y + window_size, img.shape[0])

    window = img[y_min:y_max, x_min:x_max]

    # Convert the window to binary with a threshold to make CoM more accurate
    threshold = np.mean(window) + 1.5 * np.std(window)
    binary_image = window > threshold

    # Calculate the center of mass within the window
    cy, cx = center_of_mass(binary_image)
    cx += x_min
    cy += y_min
    return cx, cy

def calc_derivative(arr, axis):
    """
    Calculate the derivative of a phase image.
    """
    s1 = np.exp(-1j*arr)
    s2 = np.exp(1j*arr)
    d1 = np.gradient(s2, axis=axis) 
    #nd = np.min(d1.shape)
    dP1x = s1 * d1
    return dP1x.imag



# Least square fit to solve the strain tensors with at least two g vectors
def extract_strain_lstsqr(g, dPdx, dPdy):
    '''g: n x 2 array of g vectors, n >= 2
    dPdx, dPdy: n x m x m array of corresponding phase derivatives
    solve exx, exy, eyx, oxy with least square
    '''
    n = g.shape[0]
    m = dPdx.shape[1]
    
    # Initialize solutions
    Exx = np.zeros((m,m))
    Exy = np.zeros((m,m))
    Eyx = np.zeros((m,m))
    Eyy = np.zeros((m,m))
    
    # Solve elemental wise
    for i in range(m):
        for j in range(m):
            # Construct linear equations
            A = np.zeros((2 * n, 4))  # 4 unknowns: Exx_ij, Exy_ij, Eyx_ij, Oxy_ij
            b = np.zeros(2 * n)
            
            for k in range(n):
                gx, gy = g[k]

                # First equation: gx * Exx_ij + gy * Exy_ij = -1/(2pi) * dP_dx[k, i, j]
                A[2 * k, 0] = gx  # coefficient for Exx_ij
                A[2 * k, 1] = gy   # coefficient for Exy_ij
                b[2 * k] = -1 / (2 * np.pi) * dPdx[k, i, j]

                # Second equation: gx * Eyx_ij + gy * Oxy_ij = -1/(2pi) * dP_dy[k, i, j]
                A[2 * k + 1, 2] = gx  # coefficient for Eyx_ij
                A[2 * k + 1, 3] = gy  # coefficient for Eyy_ij
                b[2 * k + 1] = -1 / (2 * np.pi) * dPdy[k, i, j]
        
            # Solve least squares for this (i,j) element
            x, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
            Exx[i, j], Exy[i, j], Eyx[i, j], Eyy[i, j] = x
    
    exy = (Exy + Eyx) / 2
    Oxy = (Eyx - Exy) /2
            
    return Exx, Eyy, exy, Oxy

# Adaptive GPA with Windowed Fourier Ridge phase retrieval
def get_phase_wfr(img, g, sigma, window_size, step):
    '''
    Calculate the phase from HRTEM image with a given g vector
    using the Windowed Fourier ridge technique.
    Algorithm explained in K Qian, Optics and Lasers in Engineering 45.2 (2007): 304-317.
    https://doi.org/10.1016/j.optlaseng.2005.10.012
    Codes adopted from pyGPA originated from:
    T.A. de Jong et al. Nat Commun 13, 70 (2022)
    https://doi.org/10.1038/s41467-021-27646-1
    Parameters:
    img: image array
    g: g vector coordinates in its FFT
    sigma: for Gaussian filter
    window_size: window size for wfr algorithm, in pixel
    step: step size in pixel for wfr
    Returns: phase as numpy array with the same size of img'''
    
    # Compute k vectors
    im_y, im_x = img.shape
    kx, ky = g
    xx, yy = np.meshgrid(np.arange(im_x), np.arange(im_y))
    
    # Compute window size and step
    kw = window_size * 1 / im_x
    kstep = step * 1 / im_x
    
    g = {'phase': np.zeros_like(img),
         'r': np.zeros_like(img),
         }
    for wx in np.arange(kx-kw, kx+kw, kstep):
        for wy in np.arange(ky-kw, ky+kw, kstep):
            multiplier = np.exp(np.pi*2j * (xx*wx + yy*wy))
            X = fft2(img * multiplier)
            sf = ifft2(fourier_gaussian(X, sigma=sigma))           
            sf *= np.exp(-2j*np.pi*((wx-kx)*xx+(wy-ky)*yy))
            t = np.abs(sf) > g['r']
            g['r'][t] = np.abs(sf)[t]
            g['phase'][t] = np.angle(sf)[t]
    phase = -g['phase']# Mysterious minus sign
    return phase

# Put together one function overall
def GPA(img, g, algorithm='standard', r=20, edge_blur=0.3, sigma=10, window_size=10, step=4):
    '''Top level GPA function
    img: np array of square shape m x m
    g: list of reference g coordinates n x 2
        when n = 2, use standard GPA to calculate strain tensors
        when n > 2, use least square fit to solve the stain tensors
    algorithm: 
        'standard': perform standard GPA by retrieving phases from masked iFFT 
        Ref: M. Hÿtch, E. Snoeck, R. Kilaas, Ultramicroscopy 74 (1998) 131–146.
        'adaptive': perform adaptive GPA by retrieving phase using WFR
        Ref: 
        K Qian, Optics and Lasers in Engineering 45.2 (2007): 304-317.
        T.A. de Jong et al. Nat Commun 13, 70 (2022)
    r: int, mask radius used for standard GPA
    edge_blur: float between 0-1, Fraction of pixels at the edge that will be smoothed by a cosine function. 
    sigma: float, sigma of the Gaussian window for WFT
    window_size: int, window size for WFR
    step: int, step for WFR
    Return: strain tensors with the same size of img
    '''
    # Normalize the input image
    img = norm_img(img)
    im_y, im_x = img.shape
    n = len(g)
    # FFT center coordinates
    cx, cy = im_x // 2, im_y // 2 
    
    P = np.zeros((n, im_y, im_x))
    dPdx = np.zeros((n, im_y, im_x))
    dPdy = np.zeros((n, im_y, im_x))
    ks = np.zeros((n,2))
    
    # Calculate the phase from the g vector list
    for i in range(n):
        x, y = g[i]
        ks[i] = (x-cx)/im_x, (y-cy)/im_y
        
        if algorithm == 'standard':
            P[i,:,:] = get_phase_fft(img, ks[i], r, edge_blur)
        else:
            P[i,:,:] = get_phase_wfr(img, ks[i], sigma, window_size, step)
        
        #Calculate the phase derivative
        dPdx[i,:,:] = calc_derivative(P[i,:,:], axis=1)
        dPdy[i,:,:] = calc_derivative(P[i,:,:], axis=0)
    
    # Calculate the strain tensors
    if n > 2:
        # use least square fit
        exx, eyy, exy, oxy = extract_strain_lstsqr(ks, dPdx, dPdy)
    else:
        # use standard method
        exx, eyy, exy, oxy = calc_strains(P, ks)
    return exx, eyy, exy, oxy


def renormalize_phase(P):
    r = (P+np.pi) % (2*np.pi) - np.pi
    return r
    

def rotate_vector(X, Y, ang):
    '''
    X, Y: array; components of vector along x and y
    ang: rotation angle in radian
    '''
    new_X = X * np.cos(ang) - Y * np.sin(ang)
    new_Y = X * np.sin(ang) + Y * np.cos(ang)
    return new_X, new_Y

# Integrate DPC function
def reconstruct_iDPC(DPCx, DPCy, rotation=0, cutoff=0.02):
    '''
    Reconstruct iDPC image from DPCx and DPCy images
    DPCx, DPCy: arrays of the same size
    rotation: float, scan rotation offset for the setup in degrees
    cutoff: float, cutoff for the high pass filter
    ref: Ivan Lazić, et al. Ultramicroscopy 160 (2016) 265–280. 
    '''
    if DPCx.ndim == 2:
        im_y, im_x = DPCx.shape
        # Rotate the DPC vector images
        if rotation != 0:
            ang = rotation * np.pi / 180 # Convert to radian
            DPCx, DPCy = rotate_vector(DPCx, DPCy, ang)
        # Make the k grid
        qx, qy = fftfreq(im_x), fftfreq(im_y)
        kx, ky = np.meshgrid(qx, qy)
        d1 = kx * fft2(DPCx) + ky * fft2(DPCy)
        k2 = kx**2 + ky**2
        d2 = 2 * np.pi * k2 * 1j
        d2[0,0] = np.inf
        iDPC_fft = d1 / d2
        # Apply a Gaussian high pass filter
        g = gaussian_high_pass((im_y, im_x), cutoff)
        iDPC_fft = iDPC_fft * g
        iDPC = np.real(ifft2(iDPC_fft))
        #iDPC -= np.min(iDPC)
    elif DPCx.ndim == 3:
        # Calculate on an image stack
        im_z = DPCx.shape[0]
        iDPC = np.zeros(DPCx.shape)
        for i in range(im_z):
            iDPC[i,:,:] = reconstruct_iDPC(DPCx[i], DPCy[i], rotation, cutoff)
    #iDPC_int16 = iDPC.astype('int16')
    return iDPC
    
def gaussian_high_pass(shape, cutoff=0.02):
    # Return a Gaussian high pass filter
    im_y, im_x = shape
    cx, cy = im_x // 2, im_y // 2
    X, Y = np.meshgrid(np.arange(im_x), np.arange(im_y))
    X -= cx
    Y -= cy
    sigma = im_x * cutoff
    gaussian = np.exp(-(X**2 + Y**2) / (2 * sigma ** 2))
    return ifftshift(1 - gaussian)

# Calculate the divergence
def reconstruct_dDPC(DPCx, DPCy, rotation, inverse = False):
    if DPCx.ndim == 2:
        # Rotate the DPC vector images
        if rotation != 0:
            ang = rotation * np.pi / 180 # Convert to radian
            DPCx, DPCy = rotate_vector(DPCx, DPCy, ang)
        dDPCx = np.gradient(DPCx, axis=1)
        dDPCy = np.gradient(DPCy, axis=0)
        dDPC = dDPCx + dDPCy
        if inverse:
            dDPC = -dDPC
        #dDPC -= np.min(dDPC)
    elif DPCx.ndim == 3:
        im_z = DPCx.shape[0]
        dDPC = np.zeros(DPCx.shape)
        for i in range(im_z):
            dDPC[i,:,:] = reconstruct_dDPC(DPCx[i], DPCy[i], rotation, inverse)
    #dDPC_int16 = dDPC.astype('int16')
    return dDPC

def find_rotation_ang_max_contrast(DPCx, DPCy, step=1):
    '''Try to find the scan rotation offset of DPC signals by maximizing the contrast
    DPCx, DPCy: 2d array of the same size
    step: invertal of degrees when evaluating the contrast in 0-360 degrees 
    Return: angle'''
    im_size = 256
    if DPCx.shape[0] > im_size and DPCx.shape[1] > im_size:
        # crop the input signals to save time
        x0 = (DPCx.shape[1] - im_size) // 2
        y0 = (DPCx.shape[0] - im_size) // 2
        DPCx = DPCx[y0:y0+im_size,x0:x0+im_size]
        DPCy = DPCy[y0:y0+im_size,x0:x0+im_size]
    angles1 = np.arange(0, 180, step)
    angles2 = np.arange(-180,0, step)
    contrast = []
    for ang in angles1:
        iDPC = reconstruct_iDPC(DPCx, DPCy, ang)
        contrast.append(np.std(iDPC))
    
    i_max1 = contrast.index(max(contrast))
    contrast = []
    for ang in angles2:
        iDPC = reconstruct_iDPC(DPCx, DPCy, ang)
        contrast.append(np.std(iDPC))
    i_max2 = contrast.index(max(contrast))
    return angles1[i_max1], angles2[i_max2]

def find_rotation_ang_min_curl(DPCx, DPCy, step=1):
    '''Try to find the scan rotation offset of DPC signals by minimizing the curl
    DPCx, DPCy: 2d array of the same size
    step: invertal of degrees when evaluating the curl in 0-360 degrees 
    Return: angle
    '''
    angles = np.arange(0, 360, step)
    curls = []
    for ang in angles:
        Dx, Dy = rotate_vector(DPCx, DPCy, ang*np.pi/180)
        C = curl_2d(Dx, Dy)
        curls.append(C)
        
    cost = [np.sum(c**2) for c in curls]
    i_min = cost.index(min(cost))
    return angles[i_min]    
    
def curl_2d(Fx, Fy):
    return np.gradient(Fy, axis=1) - np.gradient(Fx, axis=0)

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
    

    
