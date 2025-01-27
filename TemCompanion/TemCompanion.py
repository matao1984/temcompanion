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
# 2025-01-   v0.6
# Fixed crop and crop stack have the same effect in stack images
# Improved speed for interactive measurement and line profile
# Improved measurement results displaying
# Improved units convertion between image and FFT. Now can compute FFT from uncalibrated images and diffraction patterns.
# Added shortcuts for most of the functions
# Added mask and ifft filtering
# Improved image setting dialog

from PyQt5 import QtCore, QtWidgets

from PyQt5.QtWidgets import (QApplication, QMainWindow, QListView, QVBoxLayout, 
                             QWidget, QPushButton, QMessageBox, QFileDialog, 
                             QDialog, QAction, QHBoxLayout, QLineEdit, QLabel, 
                             QComboBox, QInputDialog, QCheckBox, QGroupBox, 
                             QFormLayout, QDialogButtonBox,  QTreeWidget, QTreeWidgetItem,
                             QSlider, QStatusBar, QMenu, QRadioButton)
from PyQt5.QtCore import Qt, QStringListModel
from PyQt5.QtGui import QImage
from superqt import QDoubleRangeSlider

import sys
import os
import io
from datetime import date

import numpy as np
import copy
from scipy import stats
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
from matplotlib.widgets import Slider, RectangleSelector, SpanSelector, EllipseSelector
from matplotlib.patches import Circle

from hrtem_filter import filters
from scipy.fft import fft2, fftshift, ifft2, ifftshift
from skimage.filters import window
from skimage.measure import profile_line
from scipy.ndimage import rotate, shift
from skimage.registration import phase_cross_correlation, optical_flow_ilk
from skimage.transform import warp



ver = '0.6'
#rdate = date.today().strftime('%Y-%m-%d')
rdate = '2025-01-27'




class UI_TemCompanion(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.retranslateUi(self)
        self.set_scalebar()
        self.files = None
        self.output_dir = None
        self.preview_dict = {}
        
    #=============== Redefine the close window behavior============================
    def closeEvent(self, event):
        # Close all window
        if self.preview_dict:
            for plot in self.preview_dict.keys():
                self.preview_dict[plot].close()
        

        
    # Define filter parameters as class variables        
    apply_wf, apply_absf, apply_nl, apply_bw, apply_gaussian = False, False, False, False, False
    filter_parameters_default = {"WF Delta": "5", "WF Bw-order": "4", "WF Bw-cutoff": "0.3",
                                 "ABSF Delta": "5", "ABSF Bw-order": "4", "ABSF Bw-cutoff": "0.3",
                                 "NL Cycles": "10", "NL Delta": "10", "NL Bw-order": "4", "NL Bw-cutoff": "0.3",
                                 "Bw-order": "4", "Bw-cutoff": "0.3",
                                 "GS-cutoff": "0.3"}

    filter_parameters = filter_parameters_default.copy()
    scale_bar = False
    
    @classmethod
    def set_scalebar(cls):
        cls.scale_bar = not cls.scale_bar

        


    def setupUi(self, TemCompanion):
        TemCompanion.setObjectName("TemCompanion")
        TemCompanion.resize(465, 370)
        self.openfileButton = QtWidgets.QPushButton(TemCompanion)
        self.openfileButton.setGeometry(QtCore.QRect(30, 20, 91, 61))
        self.openfileButton.setObjectName("OpenFile")
        
        self.openfilebox = QtWidgets.QTextEdit(TemCompanion,readOnly=True)
        self.openfilebox.setGeometry(QtCore.QRect(130, 20, 301, 61))
        self.openfilebox.setObjectName("OpenFileBox")
        
        self.previewButton = QtWidgets.QPushButton(TemCompanion)
        self.previewButton.setGeometry(QtCore.QRect(30, 90, 91, 61))
        self.previewButton.setObjectName("Preview")
        
        self.filterButton = QtWidgets.QPushButton(TemCompanion)
        self.filterButton.setGeometry(QtCore.QRect(130, 90, 91, 61))
        self.filterButton.setObjectName("filterButton")
        
        self.convertlabel = QtWidgets.QLabel(TemCompanion)
        self.convertlabel.setGeometry(QtCore.QRect(260, 100, 91, 16))
        self.convertlabel.setObjectName("ConvertTo")
        
        self.formatselect = QtWidgets.QComboBox(TemCompanion)
        self.formatselect.setGeometry(QtCore.QRect(330, 100, 95, 22))
        self.formatselect.addItems(['tiff + png','tiff', 'png', 'jpg'])
        self.formatselect.setObjectName("FormatSelect")
        
        self.setdirButton = QtWidgets.QPushButton(TemCompanion)
        self.setdirButton.setGeometry(QtCore.QRect(30, 160, 91, 61))
        self.setdirButton.setObjectName("SetDir")
        
        self.outputdirbox = QtWidgets.QTextEdit(TemCompanion)
        self.outputdirbox.setGeometry(QtCore.QRect(130, 160, 301, 61))
        self.outputdirbox.setObjectName("OutPutDirBox")
        
        self.checkscalebar = QtWidgets.QCheckBox(TemCompanion)
        self.checkscalebar.setGeometry(QtCore.QRect(250, 130, 170, 20))
        self.checkscalebar.setChecked(True)
        self.checkscalebar.setObjectName("checkscalebar")
        
        self.convertButton = QtWidgets.QPushButton(TemCompanion)
        self.convertButton.setGeometry(QtCore.QRect(30, 230, 91, 61))
        self.convertButton.setObjectName("convertButton")
        
        self.convertbox = QtWidgets.QTextEdit(TemCompanion)
        self.convertbox.setGeometry(QtCore.QRect(130, 230, 301, 61))
        self.convertbox.setObjectName("convertbox")
        
        self.authorlabel = QtWidgets.QLabel(TemCompanion)
        self.authorlabel.setGeometry(QtCore.QRect(30, 340, 351, 16))
        self.authorlabel.setObjectName("authorlabel")
        
        self.aboutButton = QtWidgets.QPushButton(TemCompanion)
        self.aboutButton.setGeometry(QtCore.QRect(30, 300, 90, 30))
        self.aboutButton.setObjectName("aboutButton")
        
        self.contactButton = QtWidgets.QPushButton(TemCompanion)
        self.contactButton.setGeometry(QtCore.QRect(150, 300, 90, 30))
        self.contactButton.setObjectName("contactButton")
        
        self.donateButton = QtWidgets.QPushButton(TemCompanion)
        self.donateButton.setGeometry(QtCore.QRect(270, 300, 130, 30))
        self.donateButton.setObjectName("donateButton")

        self.retranslateUi(TemCompanion)
        QtCore.QMetaObject.connectSlotsByName(TemCompanion)
        
#====================================================================
# Connect all functions
        self.openfileButton.clicked.connect(self.openfile)
        self.setdirButton.clicked.connect(self.set_dir)
        self.convertButton.clicked.connect(self.convert_emd)
        self.aboutButton.clicked.connect(self.show_about)
        self.contactButton.clicked.connect(self.show_contact)
        self.donateButton.clicked.connect(self.donate)
        self.previewButton.clicked.connect(self.preview)
        self.filterButton.clicked.connect(self.filter_settings)
        self.checkscalebar.stateChanged.connect(UI_TemCompanion.set_scalebar)

        

    def retranslateUi(self, TemCompanion):
        _translate = QtCore.QCoreApplication.translate
        TemCompanion.setWindowTitle(_translate("TemCompanion", "TemCompanion Ver {}".format(ver)))
        self.openfileButton.setText(_translate("TemCompanion", "Open files"))
        self.convertlabel.setText(_translate("TemCompanion", "Covnert to"))
        self.previewButton.setText(_translate("TemCompanion","Preview"))
        self.filterButton.setText(_translate("TemCompanion","Filters"))
        self.setdirButton.setText(_translate("TemCompanion", "Output \n"
"directory"))
        self.checkscalebar.setText(_translate("TemCompanion", "Add scale bar to images"))
        self.convertButton.setText(_translate("TemCompanion", "Convert All"))
        self.authorlabel.setText(_translate("TemCompanion", "TemCompanion by Dr. Tao Ma   {}".format(rdate)))
        
        self.aboutButton.setText(_translate("TemCompanion", "About"))
        self.contactButton.setText(_translate("TemCompanion", "Contact"))
        self.donateButton.setText(_translate("TemCompanion", "Buy me a LUNCH!"))
        
        

        
#===================================================================
# Open file button connected to OpenFile

    def openfile(self):
        self.files, _ = QFileDialog.getOpenFileNames(self,"Select files to be converted:", "",
                                                     "Velox emd Files (*.emd);;TIA ser Files (*.ser);;DigitalMicrograph Files (*.dm3 *.dm4);;Image Formats (*.tif *.tiff *.jpg *.jpeg *.png *.bmp);;Pickle Dictionary Files (*.pkl)")
        if self.files:
            self.output_dir = getDirectory(self.files[0],s='/')
            self.outputdirbox.setText(self.output_dir)
            self.openfilebox.setText('')
            for file in self.files:
                self.openfilebox.append(file)
                QApplication.processEvents()
        else: 
            self.files = None # Canceled, set back to None
                


#===================================================================
# Output directory button connected to SetDir

    def set_dir(self):
        self.output_dir = str(QFileDialog.getExistingDirectory(self, "Select Directory") + '/')
        if self.output_dir:
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
            
            
            
            
            for file in self.files:  
                # convert_file(file,output_dir,f_type)
                msg = "Converting '{}.{}'".format(getFileName(file),getFileType(file))
                print(msg)
                self.refresh_output(msg)
                try:                
                    convert_file(file,self.output_dir,self.f_type, scalebar = UI_TemCompanion.scale_bar,
                                 apply_wf = self.apply_wf, delta_wf = delta_wf, order_wf = order_wf, cutoff_wf = cutoff_wf,
                                 apply_absf = self.apply_absf, delta_absf = delta_absf, order_absf = order_absf, cutoff_absf = cutoff_absf,
                                 apply_nl = self.apply_nl, N = N, delta_nl = delta_nl, order_nl = order_nl, cutoff_nl = cutoff_nl,
                                 apply_bw = self.apply_bw, order_bw = order_bw, cutoff_bw = cutoff_bw,
                                 apply_gaussian = self.apply_gaussian, cutoff_gaussian = cutoff_gaussian
                                 )
                    
                    msg = "'{}.{}' has been converted".format(getFileName(file),getFileType(file))
                    print(msg)
                    self.refresh_output(msg)
    
    
                except:
                    msg = "'{}.{}' has been skipped".format(getFileName(file),getFileType(file))
                    print(msg)
                    self.refresh_output(msg)
    
            self.refresh_output("Convertion finished!") 
            print('Convertion finished!')
            
        




#=====================================================================
#Preview button function
    def preview(self):
        # Preview function set to view only 1 file for simplicity
        if self.files == None:
            QMessageBox.warning(self, 'No files loaded', 'Select file(s) to preview!')
        else:
            # Single file case:
            if len(self.files) == 1:
                f = load_file(self.files[0])
                f_name = getFileName(self.files[0])
            
            #Multiple file case, open a select file window
            else:
                # Create an instance of the ListSelector     
                select_img_window = select_img_for_preview()
    
                # Set the list of items to select from
                select_img_window.set_items(self.files)
    
                # Show the window
                result = select_img_window.exec_()
    
                # Check if the dialog was accepted and print the selected file
                if result == QDialog.Accepted and select_img_window.selected_file:
                    preview_file = select_img_window.selected_file
                    f = load_file(preview_file)
                    f_name = getFileName(preview_file)
                                    
            
            
    
            for i in range(len(f)):
                img = f[i]
                try:
                    title = img['metadata']['General']['title']
                except:
                    title = ''   
                preview_name = 'preview_{}'.format(i)    
    
                    
                if img['data'].ndim == 2:                
                    preview_im = PlotCanvas(img)
                    
    
                elif img['data'].ndim == 3:
                    # Modify the axes to be aligned with the save functions
                    # Backup the original axes
                    img['original_axes'] = copy.deepcopy(img['axes'])
                    img['axes'].pop(0)
                    img['axes'][0]['index_in_array'] = 0
                    img['axes'][1]['index_in_array'] = 1
                    preview_im = PlotCanvas3d(img)
                    
                
                preview_im.setWindowTitle(f_name + ": " + title)
                preview_im.canvas.canvas_name = preview_name
                self.preview_dict[preview_name] = preview_im
                self.preview_dict[preview_name].show() 
            
            
            
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

#=========== Define figure canvas for preview ===================================================
class PlotCanvas(QMainWindow):
    def __init__(self, img, parent=None):
        super().__init__(parent)
              
        # Create main frame for image
        self.main_frame = QWidget()
        self.fig = Figure((4,4),dpi=150) 
        self.axes = self.fig.add_subplot(111)
        self.axes.set_title('Image')
        self.axes.title.set_visible(False)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.main_frame)
        
        
        # Set the click to focus to receive key press event
        self.canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
        self.canvas.setFocus()

        # Attach the image dict to canvas
        self.canvas.data = img
        self.img_size = img['data'].shape
        self.canvas.img_idx = None  
        self.preview_dict = {}
        self.selector = None
        
        # Default settings for scale bar
        self.scalebar_settings = {'scalebar': True,
                                  'color': 'yellow',
                                  'location': 'lower left',
                                  'scale_loc': 'top',
                                  'sep': 2}
        self.scalebar = None
        
        
        # Variables for the measure function
        self.line = None
        self.start_point = None
        self.end_point = None
        self.active_point = None
        self.inactive_point = None
        self.measurement_active = False
        self.text = None # Measurement result text
        self.line_profile_mode = False
        self.linewidth = 1 # Default linewidth for line profile

        # Connect event handlers
        self.button_press_cid = None
        self.button_release_cid = None
        self.motion_notify_cid = None
        
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
        self.create_menubar()
        
        # Create a status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Display a message in the status bar
        self.statusBar.showMessage("Ready")
        
        
    
    # def closeEvent(self, event):
    #     if self.measurement_active:
    #         self.stop_distance_measurement()
    #     if self.line_profile_mode:
    #         self.stop_line_profile()
        
        
        
        
    def create_menubar(self):
        menubar = self.menuBar()  # Create a menu bar

        # File menu and actions
        file_menu = menubar.addMenu('&File')
        save_action = QAction('&Save as', self)
        save_action.setShortcut('ctrl+s')
        save_action.triggered.connect(self.mpl_toolbar.save_figure)
        file_menu.addAction(save_action)
        copy_action = QAction('&Copy Image to Clipboard', self)
        copy_action.setShortcut('ctrl+c')
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
        fft_action = QAction('&FFT', self)
        fft_action.setShortcut('ctrl+f')
        fft_action.triggered.connect(self.fft)
        edit_menu.addAction(fft_action)
        windowedfft_action = QAction('Windowed FFT', self)
        windowedfft_action.triggered.connect(self.windowedfft)
        edit_menu.addAction(windowedfft_action)
        livefft_action = QAction('&Live FFT', self)
        livefft_action.setShortcut('ctrl+shift+f')
        livefft_action.triggered.connect(self.live_fft)
        edit_menu.addAction(livefft_action)
        
        
        # Analyze menu and actions
        analyze_menu = menubar.addMenu('&Analyze')
        setscale_action = QAction('Set Scale', self)
        setscale_action.triggered.connect(self.setscale)
        analyze_menu.addAction(setscale_action)
        measure_action = QAction('&Measure', self)
        measure_action.setShortcut('ctrl+m')
        measure_action.triggered.connect(self.measure)
        analyze_menu.addAction(measure_action)
        lineprofile_action = QAction('&Line Profile', self)
        lineprofile_action.setShortcut('ctrl+l')
        lineprofile_action.triggered.connect(self.lineprofile)
        analyze_menu.addAction(lineprofile_action)
        

        # Filter menu and actions
        filter_menu = menubar.addMenu('&Filter')
        filtersetting_action = QAction('&Filter Settings', self)
        filtersetting_action.setShortcut('ctrl+shift+f')
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
                
                
                # Create a new PlotCanvas to display
                title = self.windowTitle()
                preview_name = self.canvas.canvas_name + '_cropped'
                self.preview_dict[preview_name] = PlotCanvas(img, parent=self)
                self.preview_dict[preview_name].setWindowTitle(title + '_cropped')
                self.preview_dict[preview_name].canvas.canvas_name = preview_name
                self.preview_dict[preview_name].show()
                
                # Write process history in the original_metadata
                self.preview_dict[preview_name].process['process'].append('Cropped by {}:{}, {}:{} from the original image'.format(int(x0),int(x1),int(y0),int(y1)))
                self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
                
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
            
            # Create a new PlotCanvs to display        
            title = self.windowTitle()
            preview_name = self.canvas.canvas_name + '_R{}'.format(ang)
            self.preview_dict[preview_name] = PlotCanvas(img, parent=self)
            self.preview_dict[preview_name].setWindowTitle(title + ' rotated by {} deg'.format(ang))
            self.preview_dict[preview_name].canvas.canvas_name = preview_name
            self.preview_dict[preview_name].show()
            
            # Keep the history
            self.preview_dict[preview_name].process['process'].append('Rotated by {} degrees from the original image'.format(ang))
            self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
            
            
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
        print(f'Applying Wiener filter to {title} with delta = {delta_wf}, Bw-order = {order_wf}, Bw-cutoff = {cutoff_wf}...')
        wf = apply_filter(img_wf['data'], 'Wiener', delta=delta_wf, lowpass_order=order_wf, lowpass_cutoff=cutoff_wf)
        img_wf['data'] = wf
        preview_name = self.canvas.canvas_name + '_WF'
        
        self.preview_dict[preview_name] = PlotCanvas(img_wf, parent=self)
        self.preview_dict[preview_name].setWindowTitle(title + ' Wiener Filtered')
        self.preview_dict[preview_name].canvas.canvas_name = preview_name
        self.preview_dict[preview_name].show()
        
        # Keep the history
        self.preview_dict[preview_name].process['process'].append('Wiener filter applied with delta = {}, Bw-order = {}, Bw-cutoff = {}'.format(delta_wf,order_wf,cutoff_wf))
        self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
        

    def absf_filter(self):
        filter_parameters = UI_TemCompanion.filter_parameters        
        delta_absf = int(filter_parameters['ABSF Delta'])
        order_absf = int(filter_parameters['ABSF Bw-order'])
        cutoff_absf = float(filter_parameters['ABSF Bw-cutoff'])
        img_absf = self.get_img_dict_from_canvas()
        title = self.windowTitle()
        print(f'Applying ABS filter to {title} with delta = {delta_absf}, Bw-order = {order_absf}, Bw-cutoff = {cutoff_absf}...')
        absf = apply_filter(img_absf['data'], 'ABS', delta=delta_absf, lowpass_order=order_absf, lowpass_cutoff=cutoff_absf)
        img_absf['data'] = absf
        preview_name = self.canvas.canvas_name + '_ABSF'
        self.preview_dict[preview_name] = PlotCanvas(img_absf, parent=self)
               
        self.preview_dict[preview_name].setWindowTitle(title + ' ABS Filtered')
        self.preview_dict[preview_name].canvas.canvas_name = preview_name
        self.preview_dict[preview_name].show()
        
        # Keep the history
        self.preview_dict[preview_name].process['process'].append('ABS filter applied with delta = {}, Bw-order = {}, Bw-cutoff = {}'.format(delta_absf,order_absf,cutoff_absf))
        self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
        

    def non_linear_filter(self):
        filter_parameters = UI_TemCompanion.filter_parameters        
        delta_nl = int(filter_parameters['NL Delta'])
        order_nl = int(filter_parameters['NL Bw-order'])
        cutoff_nl = float(filter_parameters['NL Bw-cutoff'])
        N = int(filter_parameters['NL Cycles'])
        img_nl = self.get_img_dict_from_canvas()
        title = self.windowTitle()
        print(f'Applying Non-Linear filter to {title} with delta = {delta_nl}, Bw-order = {order_nl}, Bw-cutoff = {cutoff_nl}...')
        nl = apply_filter(img_nl['data'], 'NL', N=N, delta=delta_nl, lowpass_order=order_nl, lowpass_cutoff=cutoff_nl)
        img_nl['data'] = nl
        preview_name = self.canvas.canvas_name + '_NL'
        self.preview_dict[preview_name] = PlotCanvas(img_nl, parent=self)
        self.preview_dict[preview_name].canvas.canvas_name = preview_name
        
        self.preview_dict[preview_name].setWindowTitle(title + ' NL Filtered')
        self.preview_dict[preview_name].show()
        
        # Keep the history
        self.preview_dict[preview_name].process['process'].append('Nonlinear filter applied with N= {}, delta = {}, Bw-order = {}, Bw-cutoff = {}'.format(N,delta_nl,order_nl,cutoff_nl))
        self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
    
        
    def bw_filter(self):
        filter_parameters = UI_TemCompanion.filter_parameters        
        order_bw = int(filter_parameters['Bw-order'])
        cutoff_bw = float(filter_parameters['Bw-cutoff'])
        img_bw = self.get_img_dict_from_canvas()
        title = self.windowTitle()
        print(f'Applying Butterworth filter to {title} with Bw-order = {order_bw}, Bw-cutoff = {cutoff_bw}...')
        bw = apply_filter(img_bw['data'], 'BW', order=order_bw, cutoff_ratio=cutoff_bw)
        img_bw['data'] = bw
        preview_name = self.canvas.canvas_name + '_Bw'
        self.preview_dict[preview_name] = PlotCanvas(img_bw, parent=self)
        self.preview_dict[preview_name].canvas.canvas_name = preview_name
        
        self.preview_dict[preview_name].setWindowTitle(title + ' Butterworth Filtered')
        self.preview_dict[preview_name].show()
        
        # Keep the history
        self.preview_dict[preview_name].process['process'].append('Butterworth filter applied with Bw-order = {}, Bw-cutoff = {}'.format(order_bw,cutoff_bw))
        self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
    
    def gaussion_filter(self):
        filter_parameters = UI_TemCompanion.filter_parameters        
        cutoff_gaussian = float(filter_parameters['GS-cutoff'])
        img_gaussian = self.get_img_dict_from_canvas()
        title = self.windowTitle()
        print(f'Applying Gaussian filter to {title} with cutoff = {cutoff_gaussian}...')
        gaussian = apply_filter(img_gaussian['data'], 'Gaussian', cutoff_ratio=cutoff_gaussian)
        img_gaussian['data'] = gaussian
        preview_name = self.canvas.canvas_name + '_GS'
        self.preview_dict[preview_name] = PlotCanvas(img_gaussian,parent=self)
        self.preview_dict[preview_name].canvas.canvas_name = preview_name
        
        self.preview_dict[preview_name].setWindowTitle(title + ' Gaussian Filtered')
        self.preview_dict[preview_name].show()
        
        # Keep the history
        self.preview_dict[preview_name].process['process'].append('Gaussian filter applied with cutoff = {}'.format(cutoff_gaussian))
        self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
    
    
    def create_img(self):
        self.im = self.axes.imshow(self.canvas.data['data'],cmap='gray')
        self.axes.set_axis_off()
        # Add scale bar 
        self.scale = self.canvas.data['axes'][1]['scale']
        self.units = self.canvas.data['axes'][1]['units'] 
        
        if self.scalebar_settings['scalebar']:
            self.create_scalebar()
            
        self.fig.tight_layout(pad=0)
        self.fig.canvas.draw()
        
    def create_scalebar(self):
        if self.scalebar is not None:
            self.scalebar.remove()
        
        if self.units in ['um', 'µm', 'nm', 'm', 'mm', 'cm', 'pm']:
            self.scalebar_settings['dimension'] = 'si-length' # Real space image
        elif self.units in ['1/m', '1/cm', '1/mm', '1/um', '1/µm', '1/nm', '1/pm']:
            self.scalebar_settings['dimension']  = 'si-length-reciprocal' # Diffraction
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
            
            # Keep the history
            self.process['process'].append('Scale updated to {} {}'.format(scale, units))
            self.canvas.data['metadata']['process'] = copy.deepcopy(self.process)
    
#=========== Measure functions ================================================
    def start_distance_measurement(self):
        self.button_press_cid = self.fig.canvas.mpl_connect('button_press_event', self.on_button_press)
        self.button_release_cid = self.fig.canvas.mpl_connect('button_release_event', self.on_button_release)
        # Display a message in the status bar
        self.statusBar.showMessage("Draw a line with mouse to measure. Drag with mouse if needed.")
        if self.buttons['distance_finish'] is None and self.measurement_active:
            self.buttons['distance_finish'] = QPushButton('Finish', parent=self.canvas)
            self.buttons['distance_finish'].move(30, 30)
            self.buttons['distance_finish'].clicked.connect(self.stop_distance_measurement)
            self.buttons['distance_finish'].show()
        
        # For line profile mode
        if self.line_profile_mode:
            preview_name = "Line Profile"
            
            self.preview_dict[preview_name] = PlotCanvasLineProfile(parent=self)
            self.preview_dict[preview_name].plot_name = preview_name            
            self.preview_dict[preview_name].setWindowTitle(preview_name)
            self.preview_dict[preview_name].show()
            

    def stop_distance_measurement(self):
        if self.measurement_active:
            self.measurement_active = False
            
            # Display a message in the status bar
            self.statusBar.showMessage("Ready")
            
            self.cleanup()  # Cleanup any existing measurements
            self.fig.canvas.mpl_disconnect(self.button_press_cid)
            self.fig.canvas.mpl_disconnect(self.button_release_cid)
            #self.fig.canvas.mpl_disconnect(self.motion_notify_cid)
            self.button_press_cid = None
            self.button_release_cid = None
            self.motion_notify_cid = None
                
        if self.buttons['distance_finish'] is not None:
            self.buttons['distance_finish'].hide()
            self.buttons['distance_finish'] = None
            
        self.fig.canvas.draw_idle()
            
    def stop_line_profile(self):
        if self.line_profile_mode:
            self.line_profile_mode = False
            self.cleanup()  # Cleanup any existing measurements
            self.fig.canvas.mpl_disconnect(self.button_press_cid)
            self.fig.canvas.mpl_disconnect(self.button_release_cid)
            #self.fig.canvas.mpl_disconnect(self.motion_notify_cid)
            self.button_press_cid = None
            self.button_release_cid = None
            self.motion_notify_cid = None
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
        
            
        self.fig.canvas.draw_idle()

    def on_button_press(self, event):
        threshold_x = self.img_size[0] / 10
        threshold_y = self.img_size[1] / 10
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
            
        self.fig.canvas.draw_idle()

    def on_mouse_move(self, event):
        if self.line is None or self.start_point is None or self.inactive_point is None:
            return
        if event.inaxes != self.axes:
            return
        x0, y0 = self.inactive_point
        x1, y1 = event.xdata, event.ydata
        
        # Only update and redraw if the mouse movement is significant
        if abs(x1 - x0) > self.img_size[0] * 0.01 or abs(y1 - y0) > self.img_size[1] * 0.01:  # Example threshold
            self.line.set_data([x0, x1], [y0, y1])
            self.fig.canvas.draw_idle()
        

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
        if self.measurement_active and self.start_point is not None and self.end_point is not None:
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
            self.canvas.draw_idle()
            #self.measure_dialog.update_measurement(distance_units, angle)
            
        # Handle line profile
        if self.line_profile_mode and self.start_point is not None and self.end_point is not None:
            # Define a line with two points and display the line profile
            p0 = round(self.start_point[0]), round(self.start_point[1])
            p1 = round(self.end_point[0]), round(self.end_point[1])
            self.preview_dict['Line Profile'].plot_lineprofile(p0, p1,self.linewidth)
            # self.fig.canvas.mpl_disconnect(self.button_press_cid)
            # self.fig.canvas.mpl_disconnect(self.button_release_cid)

            # preview_name = self.windowTitle() + ": Line Profile"
            # self.preview_dict[preview_name] = PlotCanvasLineProfile(p0, p1, self)
            # self.preview_dict[preview_name].plot_name = preview_name            
            # self.preview_dict[preview_name].setWindowTitle(preview_name)
            # self.preview_dict[preview_name].show()
            
            
        self.fig.canvas.mpl_disconnect(self.motion_notify_cid)
        
    def update_line_width(self, width):
        if self.line:
            self.linewidth = width
            self.line.set_linewidth(width)
            self.fig.canvas.draw_idle()
            
        
    
    def measure(self):
        if not self.measurement_active:
            self.measurement_active = True
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
            img_dict['data'] = data
        # FFT calculation is handled in the PlotCanvasFFT class
        
        preview_name = self.canvas.canvas_name + '_FFT'
        
        title = self.windowTitle()
        self.preview_dict[preview_name] = PlotCanvasFFT(img_dict, parent=self)
        self.preview_dict[preview_name].setWindowTitle('FFT of ' + title)
        self.preview_dict[preview_name].canvas.canvas_name = preview_name
        self.preview_dict[preview_name].show()
        
    
    def windowedfft(self):
        if self.units not in ['m','cm','mm','um','nm','pm']:
            QMessageBox.warning(self, 'FFT', 'FFT unavailable! Make sure it is a real space image with a valid scale in real space unit!')
        else:
            img_dict = self.get_img_dict_from_canvas()
            # Crop to a square if not
            data = img_dict['data']
            if data.shape[0] != data.shape[1]:
                data = filters.crop_to_square(data)
            w = window('hann', data.shape)
            img_dict['data'] = data * w
            # FFT calculation is handled in the PlotCanvasFFT class
            
            preview_name = self.canvas.canvas_name + '_Windowed FFT'
            title = self.windowTitle()
            self.preview_dict[preview_name] = PlotCanvasFFT(img_dict, parent=self)
            self.preview_dict[preview_name].setWindowTitle('Windowed FFT of ' + title)
            self.preview_dict[preview_name].canvas.canvas_name = preview_name
            self.preview_dict[preview_name].show()
            
    def live_fft(self):
        ax = self.canvas.figure.get_axes()[0]
        # Display a message in the status bar
        self.statusBar.showMessage("Drag the square to ROI compute FFT. Resize if needed.")
        

        
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
            
            preview_name = 'Live FFT'
            title = self.windowTitle()
            self.live_img = copy.deepcopy(self.canvas.data)
            self.live_img['data'] = self.current_data[y_min:y_max, x_min:x_max]
            self.preview_dict[preview_name] = PlotCanvasFFT(self.live_img, parent=self)
            self.preview_dict[preview_name].setWindowTitle('Live FFT of ' + title)
            self.preview_dict[preview_name].canvas.canvas_name = preview_name
            self.preview_dict[preview_name].show()
        
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
        self.preview_dict['Live FFT'].update_img(self.live_img['data'])
        
        print(f"Displaying FFT from {y_min}:{y_max}, {x_min}:{x_max}")
    
    def stop_live_fft(self):
        if self.selector is not None:
            self.selector.set_active(False)
            self.selector.set_visible(False)
            self.selector = None
            # Display a message in the status bar
            self.statusBar.showMessage("Ready")
            self.canvas.draw_idle()
        
        
            

#============ Line profile function ==========================================
    def lineprofile(self):
        if not self.line_profile_mode:
            self.line_profile_mode = True
            self.linewidth = 1
        self.start_distance_measurement()
        
            


        
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
        self.menubar.insertMenu(self.menubar.children()[5].children()[0],stack_menu)
        crop_stack = QAction('Crop Stack', self)
        crop_stack.triggered.connect(self.crop_stack)
        stack_menu.addAction(crop_stack)
        rotate_stack = QAction('Rotate Stack', self)
        rotate_stack.triggered.connect(self.rotate_stack)
        stack_menu.addAction(rotate_stack)
        align_stack_cc = QAction('Align Stack with Cross-Correlation', self)
        align_stack_cc.triggered.connect(self.align_stack_cc)
        stack_menu.addAction(align_stack_cc)
        align_stack_of = QAction('Align Stack with Optical Flow', self)
        align_stack_of.triggered.connect(self.align_stack_of)
        stack_menu.addAction(align_stack_of)
        integrate_stack = QAction('Integrate Stack', self)
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
                img['data'] = cropped_img.astype('int16')
                
                
                # Create a new PlotCanvas to display
                title = self.windowTitle()
                preview_name = self.canvas.canvas_name + '_cropped'
                self.preview_dict[preview_name] = PlotCanvas3d(img, parent=self)
                self.preview_dict[preview_name].setWindowTitle(title + '_cropped')
                self.preview_dict[preview_name].canvas.canvas_name = preview_name
                self.preview_dict[preview_name].show()
                
                # Write process history in the original_metadata
                self.preview_dict[preview_name].process['process'].append('Cropped by {}:{}, {}:{} from the original image'.format(int(x0),int(x1),int(y0),int(y1)))
                self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
                
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
            img['data'] = rotated_array.astype('int16')
            
            # Create a new PlotCanvs to display        
            title = self.windowTitle()
            preview_name = self.canvas.canvas_name + '_R{}'.format(ang)
            self.preview_dict[preview_name] = PlotCanvas3d(img, parent=self)
            self.preview_dict[preview_name].setWindowTitle(title + ' rotated by {} deg'.format(ang))
            self.preview_dict[preview_name].canvas.canvas_name = preview_name
            self.preview_dict[preview_name].show()
            
            # Keep the history
            self.preview_dict[preview_name].process['process'].append('Rotated by {} degrees from the original image'.format(ang))
            self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
    
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
            print('Calculate drifts using phase cross-correlation...')
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
                print(f'Shifting slice {n+1} by {drift}')
                img[n+1,:,:] = shift(img_to_shift,drift)
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
                    
                aligned_img['data'] = img_crop
                aligned_img['data'] = aligned_img['data'].astype('int16')
            print('Stack alignment finished!')
                    
            # Create a new PlotCanvas to display
            title = self.windowTitle()
            preview_name = self.canvas.canvas_name + '_aligned'
            self.preview_dict[preview_name] = PlotCanvas3d(aligned_img, parent=self)
            self.preview_dict[preview_name].setWindowTitle(title + '_aligned by Cross Correlation')
            self.preview_dict[preview_name].canvas.canvas_name = preview_name
            self.preview_dict[preview_name].show()
            
            # Write process history in the original_metadata
            self.preview_dict[preview_name].process['process'].append('Aligned by Phase Cross-Correlation')
            self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
    

    def align_stack_of(self):
        aligned_img = copy.deepcopy(self.canvas.data)
        img = aligned_img['data']
        # Open a dialog to take parameters
        # dialog = AlignStackOFDialog(parent=self)
        # if dialog.exec_() == QDialog.Accepted:
        #     algorithm = dialog.algorithm
        #     apply_window = dialog.apply_window
            
        print('Calculate drifts using Optical Flow iLK...')
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
        
            aligned_img['data'] = img.astype('int16')
        print('Stack alignment finished!')
                
        # Create a new PlotCanvas to display
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_aligned'
        self.preview_dict[preview_name] = PlotCanvas3d(aligned_img, parent=self)
        self.preview_dict[preview_name].setWindowTitle(title + '_aligned by Optical Flow')
        self.preview_dict[preview_name].canvas.canvas_name = preview_name
        self.preview_dict[preview_name].show()
        
        # Write process history in the original_metadata
        self.preview_dict[preview_name].process['process'].append('Aligned by Optical Flow iLK')
        self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
            
    
    def integrate_stack(self):
        data = np.mean(self.canvas.data['data'], axis=0)
        integrated_img = {'data': data.astype('int16'), 'axes': self.canvas.data['axes'], 'metadata': self.canvas.data['metadata'],
                          'original_metadata': self.canvas.data['original_metadata']}
        # Create a new PlotCanvs to display        
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_integrated'
        self.preview_dict[preview_name] = PlotCanvas(integrated_img, parent=self)
        self.preview_dict[preview_name].setWindowTitle(title + ' integrated')
        self.preview_dict[preview_name].canvas.canvas_name = preview_name
        self.preview_dict[preview_name].show()
        
        # Keep the history
        # self.preview_dict[preview_name].process['process'].append('Rotated by {} degrees from the original image'.format(ang))
        # self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
    
    def export_stack(self):
        data = self.canvas.data
        img_data = data['data'].astype('int16')

        data_to_export = {'data': img_data, 'metadata': data['metadata'], 'axes': data['original_axes']}
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self.parent(), 
                                                   "Save as tiff stack", 
                                                   "", 
                                                   "TIFF Files (*.tiff)", 
                                                   options=options)
        if file_path:
           tif_writer(file_path, data_to_export) 

        
    
    def export_series(self):
        data = self.canvas.data
        options = QFileDialog.Options()
        file_path, selected_type = QFileDialog.getSaveFileName(self.parent(), 
                                                   "Save Figure", 
                                                   "", 
                                                   "TIFF Files (*.tiff);;Grayscale PNG Files (*.png);;Grayscale JPEG Files (*.jpg)", 
                                                   options=options)
        if file_path:
            # Implement custom save logic here
           
            # Extract the chosen file format            
            file_type = getFileType(file_path)
            f_name = getFileName(file_path)
            output_dir = getDirectory(file_path,s='/')
            output_dir = output_dir + f_name + '/'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            img_to_save = {}
            for key in ['data', 'axes', 'metadata']:
                if key in data.keys():
                    img_to_save[key] = data[key]
                else:
                    print('Invalid image data')
                    return
            if file_type == 'tiff':
                for i in range(img_to_save['data'].shape[0]):
                    img = {'data': img_to_save['data'][i].astype('int16'), 'axes': img_to_save['axes'], 'metadata': img_to_save['metadata']}
                    save_as_tif16(img, f_name + f'_{i}', output_dir)
                    
            elif selected_type in ['Grayscale PNG Files (*.png)', 'Grayscale JPEG Files (*.jpg)']:
                for i in range(img_to_save['data'].shape[0]):
                    img = {'data': img_to_save['data'][i], 'axes': img_to_save['axes'], 'metadata': img_to_save['metadata']}
                    save_with_pil(img, f_name + f'_{i}', output_dir, file_type, scalebar=UI_TemCompanion.scale_bar) 


#========== PlotCanvas for FFT ================================================
class PlotCanvasFFT(PlotCanvas):
    def __init__(self, img, parent=None):
        # img is the image dictionary, NOT FFT. FFT will be calculated in create_img()
        super().__init__(img, parent)
        
        edit_menu = self.menubar.children()[2]
        mask_action = QAction('Mask and iFFT', self)
        mask_action.triggered.connect(self.mask)
        edit_menu.addAction(mask_action)
        
        
        analyze_menu = self.menubar.children()[3] #Analyze is at #3
        measure_fft_action = QAction('&Measure FFT', self)
        measure_fft_action.setShortcut('ctrl+shift+m')
        measure_fft_action.triggered.connect(self.measure_fft)        
        analyze_menu.addAction(measure_fft_action)
        
        # Remove the filter menu
        filter_menu = self.menubar.children()[4]
        self.menubar.removeAction(filter_menu.menuAction())
        
        self.marker = None  
        
        self.n_mask = 0
        self.active_mask = None
        self.active_idx = None
        
        # Add extra buttons
        self.buttons['mask_add'] = None
        self.buttons['mask_remove'] = None
        self.buttons['mask_ifft'] = None
        self.buttons['mask_cancel'] = None
        
        self.fft_button_press_cid = None
        self.fft_button_release_cid = None
        self.fft_motion_notify_cid = None
        self.fft_scroll_event_cid = None
        
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
        
    def update_img(self, real_data):
        # Compute fft from real_data and update the display and scale
        fft_data = fftshift(fft2(real_data))
        fft_mag = np.abs(fft_data)
        self.canvas.data['fft'] = fft_data
        self.canvas.data['data'] = fft_mag
        # Update the units
        self.canvas.data['axes'][0]['units'] = self.real_units
        self.canvas.data['axes'][1]['units'] = self.real_units
        self.canvas.data['axes'][0]['scale'] = self.real_scale
        self.canvas.data['axes'][1]['scale'] = self.real_scale
        # Update the units and scale
        self.set_scale_units()
        
        # Clear the image canvas
        self.axes.clear()
        
        # Reset the measurement marker if exists
        if self.marker is not None:
            self.marker = None
        
        vmin, vmax = np.percentile(fft_mag, (30,99.9))
        
        self.im = self.axes.imshow(self.canvas.data['data'], vmin=vmin, vmax=vmax, cmap='inferno')
        self.axes.set_axis_off()
        #Scale bar with inverse unit        
        if self.scalebar_settings['scalebar']:
            self.create_scalebar()
        self.fig.tight_layout(pad=0)
        
       
        self.canvas.draw_idle()
        
    def closeEvent(self, event):
        self.parent().stop_live_fft()
        
        
        
#======== Measure FFT function ==============================================
    def start_fft_measurement(self):
        self.marker = None
        if not self.measurement_active:
            self.measurement_active = True
            self.button_press_cid = self.fig.canvas.mpl_connect('button_press_event', self.on_click)
            # Display a message in the status bar
            self.statusBar.showMessage("Click on a spot to measure")
            
    def on_click(self, event):
        if event.inaxes != self.axes:
            return
        # Clear previous results
        self.cleanup_fft()
        image_data = self.canvas.data['data']
        image_size = image_data.shape
        x_click, y_click = int(event.xdata), int(event.ydata)
        # Define a window size around the clicked point to calculate the center of mass
        window_size = self.measure_fft_dialog.windowsize
        x_min = max(x_click - window_size, 0)
        x_max = min(x_click + window_size, image_size[0])
        y_min = max(y_click - window_size, 0)
        y_max = min(y_click + window_size, image_size[1])
        
        window = image_data[y_min:y_max, x_min:x_max]
        
        # Convert the window to binary with a threshold to make CoM more accurate
        threshold = np.mean(window) + 2*np.std(window)
        binary_image = window > threshold

        # Calculate the center of mass within the window
        cy, cx = center_of_mass(binary_image)
        cx += x_min
        cy += y_min
        
        # Add marker to plot
        self.marker,  = self.axes.plot(cx, cy, 'r+', markersize=10)
        self.fig.canvas.draw_idle()
        
        # Calculate the d-spacing
        x0 = image_size[0] // 2
        y0 = image_size[1] // 2
        distance_px = np.sqrt((cx - x0)**2 + (cy-y0)**2)
        self.distance_fft = 1/(distance_px * self.scale)
        
        # Calculate the angle from horizontal
        #self.ang = calculate_angle_from_3_points((cx, cy), (x0,y0), (x0 - 100,y0))
        self.ang = calculate_angle_to_horizontal((x0,y0), (cx,cy))
        # display results in the dialog
        self.measure_fft_dialog.update_measurement(self.distance_fft, self.ang)
        
        
    def cleanup_fft(self):
        if self.marker:
            self.marker.remove()
            self.marker = None
        self.fig.canvas.draw_idle()
        
    def stop_fft_measurement(self):
        if self.measurement_active:
            self.measurement_active = False
            self.cleanup_fft()  # Cleanup any existing measurements
            self.fig.canvas.mpl_disconnect(self.button_press_cid)
            self.button_press_cid = None
            # Display a message in the status bar
            self.statusBar.showMessage("Ready")
            self.fig.canvas.draw_idle()
            
                    
        
    def measure_fft(self):
        if self.scalebar_settings['dimension'] == 'si-length-reciprocal':
            real_units = self.units.split('/')[-1]
            self.measure_fft_dialog = MeasureFFTDialog(0, 0, real_units, self)
            self.measure_fft_dialog.show()
            self.start_fft_measurement()
            
        else:
            QMessageBox.warning(self, 'Measure FFT', 'Invalid calibration in FFT! Please calibrate the image and try again.')
         
    
    def mask(self):
        self.mask_list = []
        self.sym_mask_list = []
        
        self.fft_button_press_cid = self.fig.canvas.mpl_connect('button_press_event', self.fft_on_press)
        self.fft_button_release_cid = self.fig.canvas.mpl_connect('button_release_event', self.fft_on_release)

        
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
        
        for value in self.buttons.values():
            if value is not None:
                value.show()
        
        self.add_mask()
        
        self.statusBar.showMessage('Drag on the red circle to position. Scroll to resize. Add more as needed.')
        self.canvas.draw_idle()
        
    
    
    def add_mask(self):       
        # Default size and position
        x0, y0 = self.img_size[0]/4, self.img_size[1]/4
        r0 = int(self.img_size[0]/100)
        mask = Circle((x0,y0),radius=r0, color='red', fill=False)
        self.axes.add_artist(mask)
        self.mask_list.append(mask)
        
        # Set color to inactive mask
        if self.active_mask is not None:
            self.active_mask.set_color('orange')
        
        # Add another circle at symmetric position
        
        sym_mask = Circle((self.img_size[0]-x0,self.img_size[1]-y0), radius=r0, color='yellow', fill=False)
        self.sym_mask_list.append(sym_mask)
        self.axes.add_artist(sym_mask)
        self.active_mask = mask
        self.active_idx = self.mask_list.index(mask)
        self.canvas.draw_idle()
        
    def remove_mask(self):
        if self.active_mask is not None:
            self.mask_list.remove(self.active_mask)
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
        #min_dist = float('inf')
        for i, mask in enumerate(self.mask_list):
            cx, cy = mask.center
            d = measure_distance((x,y), (cx,cy))
            if d < mask.radius * 1.5:
                self.active_mask = mask
                self.active_idx = i
                break
        # Set red color to the active circle
        self.active_mask.set_color('red')        
        self.fft_motion_notify_cid = self.fig.canvas.mpl_connect('motion_notify_event', self.fft_on_move)
        self.fft_scroll_event_cid = self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.draw_idle()
        
    def fft_on_move(self, event):
        if event.inaxes != self.axes:
            return
        x, y = event.xdata, event.ydata
        x0, y0 = self.active_mask.center
        
        self.active_mask.center = x, y
        self.sym_mask_list[self.active_idx].center = (self.img_size[0]-x, self.img_size[1]-y)
        self.canvas.draw_idle()
        # if abs(x0-x) > self.img_size[0] /100 or abs(y0-y) > self.img_size[1] / 100:
        #     self.fig.canvas.draw()
            
     
    def fft_on_release(self, event):
        if event.inaxes != self.axes:
            return
        
        
        self.fig.canvas.mpl_disconnect(self.fft_motion_notify_cid)
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
        
        self.active_mask.set_radius(new_radius)
        self.sym_mask_list[self.active_idx].set_radius(new_radius)

        self.fig.canvas.draw_idle() 
        
            

    
    def cleanup_mask(self):
        for i in range(len(self.mask_list)):
            self.mask_list[i].remove()
            self.sym_mask_list[i].remove()
        self.mask_list = []
        self.sym_mask_list = []
        
        for value in self.buttons.values():
            if value is not None:
                value.hide()
                value = None

        self.active_mask = None
        self.active_idx = None
        #self.fig.canvas.mpl_disconnect(self.fft_motion_notify_cid)
        self.fig.canvas.mpl_disconnect(self.fft_button_press_cid)
        self.fig.canvas.mpl_disconnect(self.fft_button_release_cid)
        self.fig.canvas.mpl_disconnect(self.fft_scroll_event_cid)
        
        self.canvas.draw_idle()
        
    def create_mask(self, edge_width=5):
        
        mask = np.zeros(self.img_size, dtype=float)
        mask_lst = self.mask_list + self.sym_mask_list
        for circle in mask_lst:
            x_center, y_center = circle.center
            radius = circle.get_radius()
            # Create a grid of coordinates
            Y, X = np.ogrid[:self.img_size[0], :self.img_size[1]]
            
            # Calculate the Euclidean distance from each grid point to the circle's center
            distance = np.sqrt((X - x_center)**2 + (Y - y_center)**2)
            
            # Create the base circle mask: inside the circle is 1, outside is 0
            inside_circle = (distance <= radius)
            outside_circle = (distance >= radius + edge_width)
            
            # Transition zone
            transition_zone = ~inside_circle & ~outside_circle
            transition_mask = np.clip((radius + edge_width - distance) / edge_width, 0, 1)
    
            # Combine masks
            mask[inside_circle] = 1
            mask[transition_zone] = transition_mask[transition_zone]
            
        return mask
     
    def ifft_filter(self):
        if self.mask_list and self.sym_mask_list:
            mask = self.create_mask()
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
            title = self.windowTitle()
            preview_name = self.canvas.canvas_name + f'_iFFT_{mask_center}'
            self.preview_dict[preview_name] = PlotCanvas(filtered_img_dict,parent=self)
            self.preview_dict[preview_name].canvas.canvas_name = preview_name
            
            self.preview_dict[preview_name].setWindowTitle('iFFT of ' + title)
            self.preview_dict[preview_name].show()
            
            # Keep the history
            self.preview_dict[preview_name].process['process'].append(f'IFFT from {mask_center}')
            self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
        else:
            QMessageBox.warning(self, 'Mask and iFFT', 'Add mask(s) first!') 
    
            
            
        
#========= Plot canvas for line profile =======================================
class PlotCanvasLineProfile(QMainWindow):
        def __init__(self, parent=None):
            super().__init__(parent)
            
            self.main_frame = QWidget()
            self.fig = Figure(figsize=(5, 3), dpi=150)
            self.axes = self.fig.add_subplot(111)
            self.canvas = FigureCanvas(self.fig)
            self.canvas.setParent(self)
            
            self.selector = None
            self.text = None
            
            #self.plot_lineprofile(p1, p2)
            
            # Create the navigation toolbar, tied to the canvas
            self.mpl_toolbar = LineProfileToolbar(self.canvas, self)        
            vbox = QVBoxLayout()
            vbox.addWidget(self.mpl_toolbar)
            vbox.addWidget(self.canvas)
            self.main_frame.setLayout(vbox)
            self.setCentralWidget(self.main_frame)
            self.create_menubar()
            
            # Buttons
            self.buttons = {'measure_clear': None}
            
            self.linewidth = 1
            
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
            self.parent().stop_line_profile()
            event.accept()
            
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
            self.selector.set_active(False)
            self.selector.set_visible(False)
            self.selector = None            
            self.clear_button.hide()
            self.text.remove()
            self.text = None
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
        self.img = ax.get_images()[0] if ax.get_images() else None
        self.scalebar_settings = self.parent().plotcanvas.scalebar_settings
        
        self.original_settings = {}
        self.original_settings['scalebar'] = copy.copy(self.scalebar_settings)
        # Create the layout
        layout = QVBoxLayout()
        
        # vmin and vmax slider
        vminmax_label = QLabel('vmin/max')
        self.doubleslider = QDoubleRangeSlider(Qt.Orientation.Horizontal)
        self.doubleslider.valueChanged.connect(self.update_clim)
        
        h_box = QHBoxLayout()
        h_box.addWidget(vminmax_label)
        h_box.addWidget(self.doubleslider)
        
        
        
        # Set current vmin and vmax
        if self.img:
            vmin, vmax = self.img.get_clim()
            dmin = int(np.min(self.img._A))
            dmax = round(np.max(self.img._A))
            self.doubleslider.setRange(dmin, dmax)
            self.doubleslider.setValue((vmin, vmax))
            
            self.original_settings['vmin/max'] = (vmin, vmax)
        
        layout.addLayout(h_box)
            
            
        
        # # vmin and vmax inputs
        # h_layout_vmin = QHBoxLayout()
        # self.vmin_label = QLabel("vmin (%):")
        # self.vmin_input = QLineEdit()
        # h_layout_vmin.addWidget(self.vmin_label)
        # h_layout_vmin.addWidget(self.vmin_input)
        # layout.addLayout(h_layout_vmin)

        # h_layout_vmax = QHBoxLayout()
        # self.vmax_label = QLabel("vmax (%):")
        # self.vmax_input = QLineEdit()
        # h_layout_vmax.addWidget(self.vmax_label)
        # h_layout_vmax.addWidget(self.vmax_input)
        # layout.addLayout(h_layout_vmax)

        # Set current vmin and vmax
        # if self.img:
        #     vmin, vmax = self.img.get_clim()
        #     # # Calculate vmin and vmax is at what percentile
        #     vmin_percentile = stats.percentileofscore(self.img._A.data.flat, vmin)
        #     vmax_percentile = stats.percentileofscore(self.img._A.data.flat, vmax)
        #     self.vmin_input.setText(f'{vmin_percentile:.2f}')
        #     self.vmax_input.setText(f'{vmax_percentile:.2f}')
        

        # Colormap dropdown
        h_layout_cmap = QHBoxLayout()
        self.cmap_label = QLabel("Colormap:")
        self.cmap_combobox = QComboBox()
        colormaps = ['viridis', 'plasma', 'inferno', 'magma', 'cividis',
                     'Greys', 'Greys_r', 'Purples', 'Purples_r', 'Blues', 'Blues_r', 
                     'Greens', 'Greens_r', 'Oranges', 'Oranges_r', 'Reds', 'Reds_r',
                     'gray', 'spring', 'summer', 'autumn', 'winter', 'cool',
                      'Wistia', 'hot']
        self.cmap_combobox.addItems(colormaps)
        h_layout_cmap.addWidget(self.cmap_label)
        h_layout_cmap.addWidget(self.cmap_combobox)
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
        self.img.set_clim(vmin,vmax)
        self.ax.figure.canvas.draw_idle()
        
    def update_colormap(self):
        # Apply colormap
        self.cmap_name = self.cmap_combobox.currentText()
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
        self.doubleslider.setValue(self.original_settings['vmin/max'])
        self.update_clim()
        
        # Reset colormap
        self.cmap_combobox.setCurrentText(self.original_settings['cmap'])
        self.update_colormap()


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
                                                   "TIFF Files (*.tiff);;Grayscale PNG Files (*.png);;Grayscale JPEG Files (*.jpg);;Color PNG Files (*.png);;Color JPEG Files (*.jpg);;Pickle Dictionary Files (*.pkl)", 
                                                   options=options)
        if self.file_path:
            # Implement custom save logic here
           
            # Extract the chosen file format            
            self.file_type = getFileType(self.file_path)
            self.f_name = getFileName(self.file_path)
            self.output_dir = getDirectory(self.file_path,s='/')
            print(f"Saving figure to {self.file_path} with format {self.file_type}")
            img_to_save = {}
            for key in ['data', 'axes', 'metadata', 'original_metadata']:
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
                    
                if self.file_type == 'tiff':
                    save_as_tif16(img_to_save, self.f_name, self.output_dir)
                elif self.selected_type in ['Grayscale PNG Files (*.png)', 'Grayscale JPEG Files (*.jpg)']:
                    save_with_pil(img_to_save, self.f_name, self.output_dir, self.file_type, scalebar=UI_TemCompanion.scale_bar) 
                else:
                    # Save with matplotlib. Need to calculate the dpi to keep the original size
                    figsize = self.canvas.figure.get_size_inches()
                    img_size = img_to_save['data'].shape
                    dpi = float(sorted(img_size/figsize, reverse=True)[0])
                    
                    # Hide all the buttons if active
                    # for key, value in self.plotcanvas.buttons.items():
                    #     if value is not None:
                    #         self.plotcanvas.buttons[key].hide()
                    
                    
                    self.canvas.figure.savefig(self.file_path, dpi=dpi, format=self.file_type)
                    
                    # Bring back the hiden buttons
                    # for key, value in self.plotcanvas.buttons.items():
                    #     if value is not None:
                    #         self.plotcanvas.buttons[key].show()
                if isinstance(self.canvas.img_idx, int):
                    self.canvas.figure.axes[1].set_visible(True)
                
                
    # Redefine the edit axis button
    def edit_parameters(self):
        """Override the default edit_parameters to use a custom dialog."""
        #if self.canvas.figure:
        axes = self.canvas.figure.get_axes()
        if not axes:
            return
            # if len(axes) > 1:
            #     selected_axes, ok = QInputDialog.getItem(
            #         self, "Edit Plot",
            #         "Select the axes to edit",
            #         [ax.get_title() or f"Axes {i + 1}" for i, ax in enumerate(axes)],
            #         current=0,
            #         editable=False
            #     )
            #     if not ok:
            #         return
            #     selected_axes = axes[
            #         [ax.get_title() or f"Axes {i + 1}" for i, ax in enumerate(axes)]
            #         .index(selected_axes)
            #     ]
            # else:
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
        self.wiener_check = QCheckBox("Apply Wiener Filter")
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
        self.absf_check = QCheckBox("Apply ABS Filter")
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
        self.nl_check = QCheckBox("Apply Non-Linear Filter")
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
        self.bw_check = QCheckBox("Apply Buttwrworth Filter")
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
        self.gaussian_check = QCheckBox("Apply Gaussian Filter")
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
        # algorithm = QLabel('Alignment algorithm')
        # self.cc = QRadioButton('Phase Cross-Correlation')
        # self.cc.setChecked(True)
        # self.of_ilk = QRadioButton('Optical Flow (iterative Lucas-Kanade)')
        # self.of_tvl1 = QRadioButton('Optical Flow (TV-L1)')
        # layout.addWidget(algorithm)
        # layout.addWidget(self.cc)
        # layout.addWidget(self.of_ilk)
        # layout.addWidget(self.of_tvl1)
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
            
    # def get_algorithm(self):
    #     if self.cc.isChecked():
    #         self.algorithm = "Phase Cross-Correlation"
    #     elif self.of_ilk.isChecked():
    #         self.algorithm = "Optical Flow iLK"
    #     elif self.of_tvl1.isChecked():
    #         self.algorithm = "Optical Flow TV-L1"
        
    def handle_ok(self):
        #self.get_algorithm()
        self.crop_to_square = False
        self.apply_window = self.apply_window_check.isChecked()
        self.crop_img = self.crop_img_check.isChecked()
        if self.crop_img:
            self.crop_to_square = self.crop_to_square_check.isChecked()
            
        self.accept()
        
        
#================= Align Stack with Optical Flow dialogue =====================================
# class AlignStackOFDialog(QDialog):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.algorithm = None
#         self.setWindowTitle('Align stack parameters')
#         layout = QVBoxLayout()
#         algorithm = QLabel('Alignment algorithm')
#         self.of_ilk = QRadioButton('Optical Flow (iterative Lucas-Kanade)')
#         self.of_ilk.setChecked(True)
#         self.of_tvl1 = QRadioButton('Optical Flow (TV-L1)')
#         layout.addWidget(algorithm)
#         layout.addWidget(self.of_ilk)
#         layout.addWidget(self.of_tvl1)
#         self.apply_window_check = QCheckBox('Apply a Hann window filter')
#         self.apply_window_check.setChecked(False)
#         layout.addWidget(self.apply_window_check)
        
        
#         # Dialog Buttons (OK and Cancel)
#         buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
#         buttons.accepted.connect(self.handle_ok)
#         buttons.rejected.connect(self.reject)
#         layout.addWidget(buttons)
        
#         self.setLayout(layout)
        
        
#     def handle_ok(self):
#         if self.of_ilk.isChecked():
#             self.algorithm = "Optical Flow iLK"
#         elif self.of_tvl1.isChecked():
#             self.algorithm = "Optical Flow TV-L1"
        
#         self.apply_window = self.apply_window_check.isChecked()
            
#         self.accept()
                


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
                    json.dump(self.metadata, f)
                    
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

                 

#==================================================================
# Helper functions

from rsciio.emd import file_reader as emd_reader
from rsciio.digitalmicrograph import file_reader as dm_reader
from rsciio.tia import file_reader as tia_reader
from rsciio.tiff import file_reader as tif_reader
from rsciio.tiff import file_writer as tif_writer
from rsciio.image import file_reader as im_reader
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


def save_as_tif16(input_file, f_name, output_dir, 
                  apply_wf=False, apply_absf=False, apply_nl=False, apply_bw=False, apply_gaussian=False):
    img = copy.deepcopy(input_file)
    # Check if the image data is compatible with 16-bit int
    if all(i.is_integer() for i in img['data'].flat):
        img['data'] = img['data'].astype('int16')
        
    else:
        img['data'] = img['data'].astype('float32')
        

    # Save unfiltered    
    tif_writer(output_dir + f_name + '.tiff', img)
    
    # Save filtered    
    if apply_wf:
        img['data'] = input_file['wf']
        save_as_tif16(img, f_name + '_WF', output_dir)
        
    if apply_absf:
        img['data'] = input_file['absf']
        save_as_tif16(img,  f_name + '_ABSF', output_dir)
        
    if apply_nl:
        img['data'] = input_file['nl']
        save_as_tif16(img, f_name + '_NL', output_dir)
        
    if apply_bw:
        img['data'] = input_file['bw']
        save_as_tif16(img, f_name + '_BW', output_dir)
        
    if apply_gaussian:
        img['data'] = input_file['gaussian']
        save_as_tif16(img, f_name + '_Gaussian', output_dir)
        
       
    
    

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
    text = str(sb_len) + ' ' + unit
    fontsize = int(im_x / 20)
    font = ImageFont.load_default(fontsize)
    # try: 
    #     font = ImageFont.truetype("arial.ttf", fontsize)
    # except:
    #     try: 
    #         font = ImageFont.truetype("Helvetica.ttc", fontsize)
    #     except:
    #         font = ImageFont.load_default()
    txt_x, txt_y = (sb_start_x * 1.1, sb_start_y - fontsize * 1.1 - im_y/80)
    # Add outline to the text
    dx = im_x / 800
    draw.text((txt_x-dx, txt_y-dx), text, font=font, fill='black')
    draw.text((txt_x+dx, txt_y-dx), text, font=font, fill='black')
    draw.text((txt_x-dx, txt_y+dx), text, font=font, fill='black')
    draw.text((txt_x+dx, txt_y+dx), text, font=font, fill='black')
    draw.text((txt_x, txt_y), text, font=font, fill='white', anchor=None)  
    

# def scale_bar_to_fig(imgshape,scale,unit,facecolor="white",edgecolor="black"):
#     # Add a scalebar to the preview image handled by matplotlib
#     im_x, im_y = imgshape
#     fov_x = im_x * scale
#     sb_len_float = fov_x / 6
#     sb_lst = [0.1,0.2,0.5,1,2,5,10,20,50,100,200,500,1000,2000,5000]
#     sb_len = sorted(sb_lst, key=lambda a: abs(a - sb_len_float))[0]
#     sb_len_px = sb_len / scale
#     sb_start_x, sb_start_y = (im_x / 12, im_y *11 / 12)
#     fontsize = int(im_y / 25)
    
#     lw = im_y/80
#     sb = patches.Rectangle((sb_start_x,sb_start_y),sb_len_px,im_y/80,fc=facecolor,ec=edgecolor,lw=lw)
#     text = str(sb_len) + ' ' + unit

#     txt_x, txt_y = (sb_start_x + sb_len * 0.1, sb_start_y - im_y/80)
#     return sb, text, txt_x, txt_y, fontsize
    

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
        save_as_tif16(input_file, f_name, output_dir, apply_wf=apply_wf, apply_absf=apply_absf, apply_nl=apply_nl, apply_bw=apply_bw, apply_gaussian=apply_gaussian)

    else:
        if f_type == 'tiff + png':
            save_as_tif16(input_file, f_name, output_dir, apply_wf=apply_wf, apply_absf=apply_absf, apply_nl=apply_nl, apply_bw=apply_bw, apply_gaussian=apply_gaussian)
            f_type = 'png'
            
        save_with_pil(input_file, f_name, output_dir, f_type, scalebar=scale_bar, apply_wf=apply_wf, apply_absf=apply_absf, apply_nl=apply_nl, apply_bw=apply_bw, apply_gaussian=apply_gaussian)
        
        
        
def load_file(file):
    input_type = getFileType(file)
 
    #Load emd file:
    if input_type == 'emd':
        f = emd_reader(file, select_type = 'images')
 
    #Load dm file:
    elif input_type in ['dm3', 'dm4']:
        f = dm_reader(file)
 
    #Load TIA file
    elif input_type == 'ser':
        f = tia_reader(file)
        
    #Load tif formats
    elif input_type in ['tif', 'tiff']:
        f = tif_reader(file)
        
    #Load image formats
    elif input_type in ['png', 'jpg', 'jpeg', 'bmp']:
        f = im_reader(file)
        for img in f:
            # Only for 2d images
            for ax in img['axes']:
                ax['navigate'] = 'False'
        # If RGB or RGBA image, convert to grayscale
            if np.array(img['data'][0,0].item()).size != 1:
                img['data'] = rgb2gray(img['data'])
                
        
        
    #Load pickle dictionary
    elif input_type == 'pkl':
        with open(file, 'rb') as file:
            f = []
            f.append(pickle.load(file))
            
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


def convert_file(file, output_dir, f_type, **kwargs):
    #f_type: The file type to be saved. e.g., '.tif', '.png', '.jpg' 
    #
    f_name = getFileName(file)
    
    f = load_file(file)    
    
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
                try:
                    save_file_as(img, new_name, output_dir, f_type=f_type, **kwargs)
                except:
                    pass
                
        else:
            #DCFI images, convert into a folder
            new_dir = output_dir + f_name + '/'
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
                axes.pop(0)
                axes[0]['index_in_array'] = 0
                axes[1]['index_in_array'] = 1
                
                
                for idx in range(stack_num):
                    new_img = {'data': data[idx],
                               'axes': axes,
                               'metadata': metadata
                        }
                    new_name = title + '_{}'.format(idx)
                    try: 
                       save_file_as(new_img, new_name, new_dir, f_type, **kwargs)
                    except: 
                       pass
                           
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
                


#====Application entry==================================
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
print('='*50)
print('''
      TemCompanion 
      --- a convenient tool to view, edit, filter, and convert TEM image files to tiff, png, and jpg.
          
      This app was designed by Dr. Tao Ma. 
      Address your questions and suggestions to matao1984@gmail.com.
      Please see the "About" before use!
      Hope you get good results and publications from it!
      ''')
            
print('          Version: ' + ver + ' Released: ' + rdate)
print('='*50)
    

def main():
    
   
    app = QApplication(sys.argv)
    
    
    
    temcom = UI_TemCompanion()
    temcom.show()
    sys.exit(app.exec_())


if __name__ == "__main__":

    
    main()
