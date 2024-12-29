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

from PyQt5 import QtCore, QtWidgets

from PyQt5.QtWidgets import (QApplication, QMainWindow, QListView, QVBoxLayout, 
                             QWidget, QPushButton, QMessageBox, QFileDialog, 
                             QDialog, QAction, QHBoxLayout, QLineEdit, QLabel, 
                             QComboBox, QInputDialog, QCheckBox, QGroupBox, 
                             QFormLayout, QDialogButtonBox,  QTreeWidget, QTreeWidgetItem,
                             QSlider, QStatusBar)
from PyQt5.QtCore import Qt, QStringListModel
import sys
import os
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
from matplotlib.widgets import Slider, RectangleSelector, SpanSelector

from hrtem_filter import filters
from scipy.fft import fft2, fftshift
from skimage.filters import window
from skimage.measure import profile_line



ver = '0.2'
#rdate = date.today().strftime('%Y-%m-%d')
rdate = '2024-12-29'




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
        event.accept()
        

        
    # Define filter parameters as class variables        
    apply_wf, apply_absf, apply_nl = False, False, False
    filter_parameters_default = {"WF Delta": "5", "WF Bw-order": "4", "WF Bw-cutoff": "0.3",
                                 "ABSF Delta": "5", "ABSF Bw-order": "4", "ABSF Bw-cutoff": "0.3",
                                 "NL Cycles": "10", "NL Delta": "10", "NL Bw-order": "4", "NL Bw-cutoff": "0.3"}

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
                                                     "Velox emd Files (*.emd);;TIA ser Files (*.ser);;DigitalMicrograph Files (*.dm3 *.dm4);;Pickle Dictionary Files (*.pkl)")
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
            cutoff_nl = float(self.filter_parameters['NL Bw-cutoff'])
            N = int(self.filter_parameters['NL Cycles'])
            
            
            
            for file in self.files:  
                # convert_file(file,output_dir,f_type)
                msg = "Converting '{}.{}'".format(getFileName(file),getFileType(file))
                self.refresh_output(msg)
                try:                
                    convert_file(file,self.output_dir,self.f_type, scalebar = UI_TemCompanion.scale_bar,
                                 apply_wf = self.apply_wf, delta_wf = delta_wf, order_wf = order_wf, cutoff_wf = cutoff_wf,
                                 apply_absf = self.apply_absf, delta_absf = delta_absf, order_absf = order_absf, cutoff_absf = cutoff_absf,
                                 apply_nl = self.apply_nl, N = N, delta_nl = delta_nl, order_nl = order_nl, cutoff_nl = cutoff_nl,)
                    
                    msg = "'{}.{}' has been converted".format(getFileName(file),getFileType(file))
                    self.refresh_output(msg)
    
    
                except:
                    msg = "'{}.{}' has been skipped".format(getFileName(file),getFileType(file))
                    self.refresh_output(msg)
    
            self.refresh_output("Convertion finished!")       
            
        




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
     
        filtersettingdialog = FilterSettingDialogue(cls.apply_wf, cls.apply_absf, cls.apply_nl, cls.filter_parameters)
        result = filtersettingdialog.exec_()
        if result == QDialog.Accepted:
            cls.filter_parameters = filtersettingdialog.parameters
            cls.apply_wf = filtersettingdialog.apply_wf
            cls.apply_absf = filtersettingdialog.apply_absf
            cls.apply_nl = filtersettingdialog.apply_nl
            
               
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
                    "If you like this app, show your appreciation and <a href=\"https://www.paypal.com/donate/?business=ZCSWE88TR2YHY&no_recurring=0&currency_code=USD\">buy me a lunch!</a>"\
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
        # Attach the image dict to canvas
        self.canvas.data = copy.deepcopy(img)
        self.canvas.img_idx = None  
        self.preview_dict = {}
        self.selector = None
        
        # Variables for the measure function
        self.line = None
        self.start_point = None
        self.end_point = None
        self.measurement_active = False
        self.line_profile_mode = False

        # Connect event handlers
        self.button_press_cid = None
        self.button_release_cid = None
        self.motion_notify_cid = None
        
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
        self.mpl_toolbar = CustomToolbar(self.canvas, self)        
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
    
    def closeEvent(self, event):
        # Close all window
        if self.preview_dict:
            for plot in self.preview_dict.keys():
                self.preview_dict[plot].close()
        event.accept()
        
        
        
    def create_menubar(self):
        menubar = self.menuBar()  # Create a menu bar

        # File menu and actions
        file_menu = menubar.addMenu('File')
        save_action = QAction('Save', self)
        save_action.triggered.connect(self.mpl_toolbar.save_figure)
        file_menu.addAction(save_action)
        close_action = QAction('Close', self)
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)

        # Edit menu and actions
        edit_menu = menubar.addMenu('Process')
        imagesetting_action = QAction('Image Settings',self)
        imagesetting_action.triggered.connect(self.mpl_toolbar.edit_parameters)
        edit_menu.addAction(imagesetting_action)
        crop_action = QAction('Crop', self)
        crop_action.triggered.connect(self.crop)
        edit_menu.addAction(crop_action)
        rotate_action = QAction('Rotate', self)
        rotate_action.triggered.connect(self.rotate)
        edit_menu.addAction(rotate_action)
        fft_action = QAction('FFT', self)
        fft_action.triggered.connect(self.fft)
        edit_menu.addAction(fft_action)
        windowedfft_action = QAction('Windowed FFT', self)
        windowedfft_action.triggered.connect(self.windowedfft)
        edit_menu.addAction(windowedfft_action)
        
        # Analyze menu and actions
        analyze_menu = menubar.addMenu('Analyze')
        setscale_action = QAction('Set Scale', self)
        setscale_action.triggered.connect(self.setscale)
        analyze_menu.addAction(setscale_action)
        measure_action = QAction('Measure', self)
        measure_action.triggered.connect(self.measure)
        analyze_menu.addAction(measure_action)
        # measure_fft_action = QAction('Measure FFT', self)
        # measure_fft_action.triggered.connect(self.measure_fft)        
        # analyze_menu.addAction(measure_fft_action)
        lineprofile_action = QAction('Line Profile', self)
        lineprofile_action.triggered.connect(self.lineprofile)
        analyze_menu.addAction(lineprofile_action)
        

        # Filter menu and actions
        filter_menu = menubar.addMenu('Filter')
        filtersetting_action = QAction('Filter Settings', self)
        filtersetting_action.triggered.connect(UI_TemCompanion.filter_settings)
        filter_menu.addAction(filtersetting_action)
        
        wiener_action = QAction('Apply Wiener', self)
        wiener_action.triggered.connect(self.wiener_filter)
        filter_menu.addAction(wiener_action)
        absf_action = QAction('Apply ABSF', self)
        absf_action.triggered.connect(self.absf_filter)
        filter_menu.addAction(absf_action)
        non_linear_action = QAction('Apply Non-Linear', self)
        non_linear_action.triggered.connect(self.non_linear_filter)
        filter_menu.addAction(non_linear_action)

        # Info menu
        info_menu = menubar.addMenu('Info')
        info_action = QAction('Image Info', self)
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
        self.statusBar.showMessage("Drag a rectangle to crop")

        
        if self.selector is None:
            self.selector = RectangleSelector(ax, onselect=self.on_select, interactive=True, useblit=True,
                                              drag_from_anywhere=True,
                                              button=[1],
                                              )
            
            # Crop button
            self.ok_button = QPushButton('OK', parent=self.canvas)
            self.ok_button.move(30, 30)
            self.ok_button.clicked.connect(self.confirm_crop)
            self.ok_button.hide()
            self.cancel_button = QPushButton('Cancel', parent=self.canvas)
            self.cancel_button.move(110,30)
            self.cancel_button.clicked.connect(self.cancel_crop)
            self.cancel_button.hide()
            
        self.selector.set_active(True)
        self.ok_button.show()
        self.cancel_button.show()
        self.fig.canvas.draw()

    def on_select(self, eclick, erelease):
        pass  # handle the crop in the confirm_crop function
        
        


    def confirm_crop(self):
        if self.selector is not None and self.selector.active:
            x0, x1, y0, y1 = self.selector.extents
            if abs(x1 - x0) > 1 and abs(y1 - y0) >1: 
                # Valid area is selected               
                img = self.get_img_dict_from_canvas()
                cropped_img = img['data'][int(y0):int(y1), int(x0):int(x1)]                
                img['data'] = cropped_img
                
                
                # Create a new PlotCanvas to display
                title = self.windowTitle()
                preview_name = self.canvas.canvas_name + '_cropped'
                self.preview_dict[preview_name] = PlotCanvas(img)
                self.preview_dict[preview_name].setWindowTitle(title + '_cropped')
                self.preview_dict[preview_name].canvas.canvas_name = preview_name
                self.preview_dict[preview_name].show()
                
                # Write process history in the original_metadata
                self.preview_dict[preview_name].process['process'].append('Cropped by {}:{}, {}:{} from the original image'.format(int(y0),int(y1),int(x0),int(x1)))
                self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
                
            self.selector.set_active(False)
            self.selector.set_visible(False)
            self.selector.disconnect_events()  # Disconnect event handling
            self.selector = None            
            self.ok_button.hide()
            self.cancel_button.hide()
            # Display a message in the status bar
            self.statusBar.showMessage("Ready")
            self.fig.canvas.draw_idle()
            
    
    def cancel_crop(self):
        self.selector.set_active(False)
        self.selector.set_visible(False)
        self.selector.disconnect_events()  # Disconnect event handling
        self.selector = None            
        self.ok_button.hide()
        self.cancel_button.hide()
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
            img_to_rotate = Image.fromarray(img['data'])
            img_rotated = img_to_rotate.rotate(ang, expand=True)
            rotated_array = np.array(img_rotated)
            img['data'] = rotated_array
            
            # Create a new PlotCanvs to display        
            title = self.windowTitle()
            preview_name = self.canvas.canvas_name + '_R{}'.format(ang)
            self.preview_dict[preview_name] = PlotCanvas(img)
            self.preview_dict[preview_name].setWindowTitle(title + ' rotated by {} deg'.format(ang))
            self.preview_dict[preview_name].canvas.canvas_name = preview_name
            self.preview_dict[preview_name].show()
            
            # Keep the history
            self.preview_dict[preview_name].process['process'].append('Rotated by {} degrees from the original image'.format(ang))
            self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)


    def wiener_filter(self):
        filter_parameters = UI_TemCompanion.filter_parameters        
        delta_wf = int(filter_parameters['WF Delta'])
        order_wf = int(filter_parameters['WF Bw-order'])
        cutoff_wf = float(filter_parameters['WF Bw-cutoff'])
        img_wf = self.get_img_dict_from_canvas()
        wf = apply_filter(img_wf['data'], 'Wiener', delta=delta_wf, lowpass_order=order_wf, lowpass_cutoff=cutoff_wf)
        img_wf['data'] = wf
        preview_name = self.canvas.canvas_name + '_WF'
        title = self.windowTitle()
        self.preview_dict[preview_name] = PlotCanvas(img_wf)
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
        absf = apply_filter(img_absf['data'], 'ABS', delta=delta_absf, lowpass_order=order_absf, lowpass_cutoff=cutoff_absf)
        img_absf['data'] = absf
        preview_name = self.canvas.canvas_name + '_ABSF'
        title = self.windowTitle()
        self.preview_dict[preview_name] = PlotCanvas(img_absf)
               
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
        nl = apply_filter(img_nl['data'], 'NL', N=N, delta=delta_nl, lowpass_order=order_nl, lowpass_cutoff=cutoff_nl)
        img_nl['data'] = nl
        preview_name = self.canvas.canvas_name + '_NL'
        title = self.windowTitle()
        self.preview_dict[preview_name] = PlotCanvas(img_nl)
        self.preview_dict[preview_name].canvas.canvas_name = preview_name
        
        self.preview_dict[preview_name].setWindowTitle(title + ' NL Filtered')
        self.preview_dict[preview_name].show()
        
        # Keep the history
        self.preview_dict[preview_name].process['process'].append('Nonlinear filter applied with N= {}, delta = {}, Bw-order = {}, Bw-cutoff = {}'.format(N,delta_nl,order_nl,cutoff_nl))
        self.preview_dict[preview_name].canvas.data['metadata']['process'] = copy.deepcopy(self.preview_dict[preview_name].process)
        
    def create_img(self):
        self.im = self.axes.imshow(self.canvas.data['data'],cmap='gray')
        self.axes.set_axis_off()
        # Add scale bar 
        self.scale = self.canvas.data['axes'][1]['scale']
        self.units = self.canvas.data['axes'][1]['units']  
        if self.units in ['um', 'µm', 'nm', 'm', 'mm', 'cm', 'pm']:
            dimension = 'si-length' # Real space image
        elif self.units in ['1/um', '1/µm', '1/nm', '1/pm']:
            dimension = 'si-length-reciprocal' # Diffraction
        else: # Cannot parse the unit correctly, reset to pixel scale
            self.units = ''
            self.scale = 1
            dimension = 'pixel-length'
        self.scalebar = ScaleBar(self.scale, self.units, location="lower left",
                                 dimension=dimension,
                                 scale_loc="top", frameon=False, sep=2, color='yellow')
        self.axes.add_artist(self.scalebar)
        self.fig.tight_layout(pad=0)
        
    
    def show_info(self):
        # Show image infomation function here
        img_dict = self.get_img_dict_from_canvas()
        metadata = img_dict['metadata']
        try: 
            extra_metadata = img_dict['original_metadata']
            metadata.update(extra_metadata)
        except:
            pass
        self.metadata_viewer = MetadataViewer(metadata)
        self.metadata_viewer.show()
        
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
            self.canvas.data['axes'][0]['scale'] = scale
            self.canvas.data['axes'][1]['scale'] = scale
            self.canvas.data['axes'][0]['units'] = units
            self.canvas.data['axes'][1]['units'] = units
            self.scalebar.remove()
            # Recreate the image with the new scale
            self.create_img()
            self.canvas.draw()
            
            # Keep the history
            self.process['process'].append('Scale updated to {} {}'.format(scale, units))
            self.canvas.data['metadata']['process'] = copy.deepcopy(self.process)
    
#=========== Measure functions ================================================
    def start_distance_measurement(self):
        self.button_press_cid = self.fig.canvas.mpl_connect('button_press_event', self.on_button_press)
        self.button_release_cid = self.fig.canvas.mpl_connect('button_release_event', self.on_button_release)
        # Display a message in the status bar
        self.statusBar.showMessage("Draw a line with mouse to measure")
            

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
            self.fig.canvas.draw_idle()
            
    def stop_line_profile(self):
        if self.line_profile_mode:
            self.line_profile_mode = False
            self.cleanup()  # Cleanup any existing measurements
            # self.fig.canvas.mpl_disconnect(self.button_press_cid)
            # self.fig.canvas.mpl_disconnect(self.button_release_cid)
            #self.fig.canvas.mpl_disconnect(self.motion_notify_cid)
            self.button_press_cid = None
            self.button_release_cid = None
            self.motion_notify_cid = None
            # Display a message in the status bar
            self.statusBar.showMessage("Ready")
            self.fig.canvas.draw_idle()
            

    def cleanup(self):
        if self.line:
            self.line.remove()
            self.line = None
        self.start_point = None
        self.end_point = None
        self.fig.canvas.draw_idle()

    def on_button_press(self, event):
        if event.inaxes != self.axes:
            return
        self.cleanup() # Cleanup any existing measurements
        self.motion_notify_cid = self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.start_point = (event.xdata, event.ydata)
        self.line, = self.axes.plot([self.start_point[0], self.start_point[0]], 
                                  [self.start_point[1], self.start_point[1]], 'r-',linewidth=1)
        self.fig.canvas.draw_idle()

    def on_mouse_move(self, event):
        if self.line is None or self.start_point is None:
            return
        if event.inaxes != self.axes:
            return
        x0, y0 = self.start_point
        self.line.set_data([x0, event.xdata], [y0, event.ydata])
        self.fig.canvas.draw_idle()

    def on_button_release(self, event):
        if event.inaxes != self.axes:
            return
        
        self.end_point = (event.xdata, event.ydata)
        
        # Handle measure the distance
        if self.measurement_active and self.start_point is not None and self.end_point is not None:
            distance_units = measure_distance(self.start_point, self.end_point, scale=self.scale)
            angle = calculate_angle_from_3_points(self.end_point, self.start_point, (self.start_point[0] - 100,self.start_point[1]))
            self.measure_dialog.update_measurement(distance_units, angle)
            
        # Handle line profile
        if self.line_profile_mode and self.start_point is not None and self.end_point is not None:
            # Define a line with two points and display the line profile
            p0 = round(self.start_point[0]), round(self.start_point[1])
            p1 = round(self.end_point[0]), round(self.end_point[1])
            self.fig.canvas.mpl_disconnect(self.button_press_cid)
            self.fig.canvas.mpl_disconnect(self.button_release_cid)

            preview_name = self.windowTitle() + ": Line Profile"
            self.preview_dict[preview_name] = PlotCanvasLineProfile(p0, p1, self)
            self.preview_dict[preview_name].plot_name = preview_name            
            self.preview_dict[preview_name].setWindowTitle(preview_name)
            self.preview_dict[preview_name].show()
            
            
        self.fig.canvas.mpl_disconnect(self.motion_notify_cid)
        
    def update_line_width(self, width):
        if self.line:
            self.line.set_linewidth(width)
            self.fig.canvas.draw_idle()
            
        
    
    def measure(self):
        if not self.measurement_active:
            self.measurement_active = True
            self.measure_dialog = MeasurementDialog(0, 0, self.units, self)
            self.measure_dialog.show()
            self.start_distance_measurement()
        
# #======== Measure FFT function ==============================================
#     def start_fft_measurement(self):
#         self.marker = None
#         if not self.measurement_active:
#             self.measurement_active = True
#             self.button_press_cid = self.fig.canvas.mpl_connect('button_press_event', self.on_click)
            
#     def on_click(self, event):
#         if event.inaxes != self.axes:
#             return
#         # Clear previous results
#         self.cleanup_fft()
#         image_data = self.canvas.data['data']
#         image_size = image_data.shape
#         x_click, y_click = int(event.xdata), int(event.ydata)
#         # Define a window size around the clicked point to calculate the center of mass
#         window_size = self.measure_fft_dialog.windowsize
#         x_min = max(x_click - window_size, 0)
#         x_max = min(x_click + window_size, image_size[0])
#         y_min = max(y_click - window_size, 0)
#         y_max = min(y_click + window_size, image_size[1])
        
#         window = image_data[y_min:y_max, x_min:x_max]

#         # Calculate the center of mass within the window
#         cy, cx = center_of_mass(window)
#         cx += x_min
#         cy += y_min
        
#         # Add marker to plot
#         self.marker,  = self.axes.plot(cx, cy, 'r+', markersize=10)
#         self.fig.canvas.draw_idle()
        
#         # Calculate the d-spacing
#         x0 = image_size[0] // 2
#         y0 = image_size[1] // 2
#         distance_px = np.sqrt((cx - x0)**2 + (cy-y0)**2)
#         self.distance_fft = 1/(distance_px * self.scale)
        
#         # Calculate the angle from horizontal
#         self.ang = calculate_angle_from_3_points((cx, cy), (x0,y0), (x0 - 100,y0))
        
#         # display results in the dialog
#         self.measure_fft_dialog.update_measurement(self.distance_fft, self.ang)
        
        
#     def cleanup_fft(self):
#         if self.marker:
#             self.marker.remove()
#             self.marker = None
#         self.fig.canvas.draw_idle()
        
#     def stop_fft_measurement(self):
#         if self.measurement_active:
#             self.measurement_active = False
#             self.cleanup_fft()  # Cleanup any existing measurements
#             self.fig.canvas.mpl_disconnect(self.button_press_cid)
#             self.button_press_cid = None
#             self.fig.canvas.draw_idle()
        
                
    
#     def measure_fft(self):
#         real_units = None
#         if self.units == '1/nm':
#             real_units = 'nm'
#         elif self.units == '1/um':
#             real_units = 'um'
#         if real_units is not None:
#             self.measure_fft_dialog = MeasureFFTDialog(0, 0, real_units, self)
#             self.measure_fft_dialog.show()
#             self.start_fft_measurement()
#         else:
#             QMessageBox.warning(self, 'Measure FFT', 'Only available for FFT!')

#================= FFT ======================================================        
        
    
    def fft(self):
        if self.units not in ['m','cm','mm','um','nm','pm']:
            QMessageBox.warning(self, 'FFT', 'FFT unavailable! Make sure it is a real space image with a valid scale in real space unit!')
        else:
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
            self.preview_dict[preview_name] = PlotCanvasFFT(img_dict)
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
            self.preview_dict[preview_name] = PlotCanvasFFT(img_dict)
            self.preview_dict[preview_name].setWindowTitle('Windowed FFT of ' + title)
            self.preview_dict[preview_name].canvas.canvas_name = preview_name
            self.preview_dict[preview_name].show()
            

#============ Line profile function ==========================================
    def lineprofile(self):
        if not self.line_profile_mode:
            self.line_profile_mode = True
        self.start_distance_measurement()
        
            


        
#======= Canvas to show image stacks==========================================
class PlotCanvas3d(PlotCanvas):
    def __init__(self, img):
        super().__init__(img)
        
    def create_img(self):
        self.canvas.img_idx = 0
        self.im = self.axes.imshow(self.canvas.data['data'][self.canvas.img_idx],cmap='gray')
        self.axes.set_axis_off()
        # Add scale bar 
        self.scale = self.canvas.data['axes'][1]['scale']
        self.units = self.canvas.data['axes'][1]['units']  
        if self.units in ['um', 'µm', 'nm', 'm', 'mm', 'cm', 'pm']:
            dimension = 'si-length' # Real space image
        elif self.units in ['1/um', '1/µm', '1/nm', '1/pm']:
            dimension = 'si-length-reciprocal' # Diffraction
        else: # Cannot parse the unit correctly, reset to pixel scale
            self.units = ''
            self.scale = 1
            dimension = 'pixel-length'
        self.scalebar = ScaleBar(self.scale, self.units, location="lower left", 
                                 dimension=dimension,
                                 scale_loc="top", frameon=False, sep=2, color='yellow')
        self.axes.add_artist(self.scalebar)
        self.fig.tight_layout(pad=0)
        # Create a slider for stacks
        self.slider_ax = self.fig.add_axes([0.2, 0.9, 0.7, 0.03], facecolor='lightgoldenrodyellow')
        self.fontsize = int(self.canvas.data['data'].shape[1] / 100)
        self.slider = Slider(self.slider_ax, 'Frame', 0, self.canvas.data['data'].shape[0] - 1, 
                             valinit=self.canvas.img_idx, valstep=1,handle_style={'size': self.fontsize})
        self.slider_ax.tick_params(labelsize=self.fontsize)  # Smaller font size for ticks
        self.slider.label.set_size(self.fontsize)     # Smaller font size for label
        self.slider.valtext.set_size(self.fontsize)
        self.slider.on_changed(self.update_frame)
        
    # Update function for the slider
    def update_frame(self, val):
        self.canvas.img_idx = int(self.slider.val)
        self.im.set_data(self.canvas.data['data'][self.canvas.img_idx])
        self.canvas.draw_idle()


#========== PlotCanvas for FFT ================================================
class PlotCanvasFFT(PlotCanvas):
    def __init__(self, img):
        # img is the image dictionary, NOT FFT. FFT will be calculated in create_img()
        super().__init__(img)
        
        analyze_menu = self.menubar.children()[3] #Analyze is at #3
        measure_fft_action = QAction('Measure FFT', self)
        measure_fft_action.triggered.connect(self.measure_fft)        
        analyze_menu.addAction(measure_fft_action)
        
        # global menu
        # menu = self.menubar.children()        
        
    def create_img(self):
        img_dict = self.canvas.data  
        data = img_dict['data']
        
        # Display the power spectrum for better visualization
        fft_data = np.abs(fftshift(fft2(data))) 
        # Normalize image data
        #fft_data = norm_img(fft_data) * 100
        # Reformat the axes of the FFT image
        im_x, im_y = data.shape
        img_scale = img_dict['axes'][1]['scale']
        fft_scale = 1 / img_scale / im_x
        
        # Update the image dictionary with the FFT data
        img_dict['data'] = fft_data
        img_dict['axes'][0]['size'] = im_x
        img_dict['axes'][1]['size'] = im_y
        img_dict['axes'][0]['scale'] = fft_scale
        img_dict['axes'][1]['scale'] = fft_scale
        img_dict['axes'][0]['units'] = '1/{}'.format(img_dict['axes'][0]['units'])
        img_dict['axes'][1]['units'] = '1/{}'.format(img_dict['axes'][1]['units'])
        
        # Update the data associated with this canvas object
        self.units = self.canvas.data['axes'][1]['units'] 
        self.scale = self.canvas.data['axes'][1]['scale']

        vmin, vmax = np.percentile(fft_data, (30,99.9))
        
        self.im = self.axes.imshow(self.canvas.data['data'], vmin=vmin, vmax=vmax, cmap='inferno')
        self.axes.set_axis_off()
        #Scale bar with inverse unit        
        self.scalebar = ScaleBar(self.scale, self.units, dimension='si-length-reciprocal', 
                                 location="lower left", scale_loc="top", frameon=False, sep=2, 
                                 color='yellow')
        self.axes.add_artist(self.scalebar)
        self.fig.tight_layout(pad=0)
        
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
        self.ang = calculate_angle_from_3_points((cx, cy), (x0,y0), (x0 - 100,y0))
        
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
        real_units = None
        if self.units == '1/nm':
            real_units = 'nm'
        elif self.units == '1/um':
            real_units = 'um'
        if real_units is not None:
            self.measure_fft_dialog = MeasureFFTDialog(0, 0, real_units, self)
            self.measure_fft_dialog.show()
            self.start_fft_measurement()
        else:
            QMessageBox.warning(self, 'Measure FFT', 'Only available for FFT!')

        
        
#========= Plot canvas for line profile =======================================
class PlotCanvasLineProfile(QMainWindow):
        def __init__(self, p1, p2, parent=None):
            super().__init__(parent)
            
            self.main_frame = QWidget()
            self.fig = Figure(figsize=(5, 3), dpi=150)
            self.axes = self.fig.add_subplot(111)
            self.canvas = FigureCanvas(self.fig)
            self.canvas.setParent(self)
            self.img_data = self.parent().get_current_img_from_canvas()
            self.selector = None
            self.text = None
            
            self.plot_lineprofile(p1, p2)
            
            # Create the navigation toolbar, tied to the canvas
            self.mpl_toolbar = LineProfileToolbar(self.canvas, self)        
            vbox = QVBoxLayout()
            vbox.addWidget(self.mpl_toolbar)
            vbox.addWidget(self.canvas)
            self.main_frame.setLayout(vbox)
            self.setCentralWidget(self.main_frame)
            self.create_menubar()
            
            self.linewidth = 1 # Default line width set to 1
            
        def create_menubar(self):
            menubar = self.menuBar()
            
            file_menu = menubar.addMenu('File')
            save_action = QAction('Export', self)
            save_action.triggered.connect(self.mpl_toolbar.save_figure)
            file_menu.addAction(save_action)
            close_action = QAction('Close', self)
            close_action.triggered.connect(self.close)
            file_menu.addAction(close_action)
            
            measure_menu = menubar.addMenu('Measure')
            measure_horizontal = QAction('Measure horizontal', self)
            measure_horizontal.triggered.connect(self.measure_horizontal)
            measure_menu.addAction(measure_horizontal)
            measure_vertical = QAction('Measure vertical', self)
            measure_vertical.triggered.connect(self.measure_vertical)
            measure_menu.addAction(measure_vertical)
            
            settings_menu = menubar.addMenu('Settings')
            linewidth_setting_action = QAction('Set line width',self)
            linewidth_setting_action.triggered.connect(self.linewidth_setting)
            settings_menu.addAction(linewidth_setting_action)

            plotsettings_action = QAction('Plot Settings', self)
            plotsettings_action.triggered.connect(self.plotsetting)
            settings_menu.addAction(plotsettings_action)
            
            self.menubar = menubar
            

        def plot_lineprofile(self, p1, p2, linewidth=1):   
            self.start_point = p1
            self.stop_point = p2
            lineprofile = profile_line(self.img_data, (p1[1], p1[0]), (p2[1], p2[0]), linewidth=linewidth, reduce_func=np.mean)
            line_x = np.linspace(0, len(lineprofile)-1, len(lineprofile)) * self.parent().scale
            self.axes.plot(line_x, lineprofile, '-', color='red')
            self.axes.tick_params(direction='in')
            self.axes.set_xlabel('Distance ({})'.format(self.parent().units))
            self.axes.set_ylabel('Intensity')
            self.axes.set_xlim(min(line_x), max(line_x))
            self.fig.tight_layout()
            self.canvas.draw()
            
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
            if self.text:
                self.text.remove()
            self.text = self.axes.text(0.05, 0.9, f'{distance:.4f} ({self.parent().units})',
                                       transform=self.axes.transAxes, color='red')
            self.canvas.draw_idle()
            
        def on_select_v(self,ymin,ymax):
            distance = ymax - ymin
            if self.text:
                self.text.remove()
            self.text = self.axes.text(0.05, 0.9, f'{distance:.0f} (Counts)',
                                       transform=self.axes.transAxes, color='red')
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
                self.clear_button.hide()
             
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

        # Create the layout
        layout = QVBoxLayout()


        # vmin and vmax inputs
        h_layout_vmin = QHBoxLayout()
        self.vmin_label = QLabel("vmin (%):")
        self.vmin_input = QLineEdit()
        h_layout_vmin.addWidget(self.vmin_label)
        h_layout_vmin.addWidget(self.vmin_input)
        layout.addLayout(h_layout_vmin)

        h_layout_vmax = QHBoxLayout()
        self.vmax_label = QLabel("vmax (%):")
        self.vmax_input = QLineEdit()
        h_layout_vmax.addWidget(self.vmax_label)
        h_layout_vmax.addWidget(self.vmax_input)
        layout.addLayout(h_layout_vmax)

        # Set current vmin and vmax
        if self.img:
            vmin, vmax = self.img.get_clim()
            # # Calculate vmin and vmax is at what percentile
            vmin_percentile = stats.percentileofscore(self.img._A.data.flat, vmin)
            vmax_percentile = stats.percentileofscore(self.img._A.data.flat, vmax)
            self.vmin_input.setText(f'{vmin_percentile:.2f}')
            self.vmax_input.setText(f'{vmax_percentile:.2f}')
        

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
            self.cmap_combobox.setCurrentText(self.img.get_cmap().name)

        # Apply button
        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Ok)
        self.apply_button = buttons.button(QDialogButtonBox.Apply)
        self.apply_button.clicked.connect(self.apply_settings)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.ok_button.clicked.connect(self.handle_ok)
        
        layout.addWidget(buttons)
        

        self.setLayout(layout)

    def apply_settings(self):
        if not self.img:
            print("No image present in the axes.")
            return
            

        # Apply vmin and vmax
        try:
            vmin_percentile = float(self.vmin_input.text())
            vmax_percentile = float(self.vmax_input.text())
            
        except ValueError:
            QMessageBox.warning(self, 'Image Settings', 'Invalid vmin or vmax value!')
            return
            

        vmin = np.percentile(self.img._A.data, vmin_percentile)        

        vmax = np.percentile(self.img._A.data, vmax_percentile)
        
        if vmin >= vmax:
           QMessageBox.warning(self, 'Image Settings', 'Invalid vmin or vmax value!')
           return
       
        else:
            self.img.set_clim(vmin, vmax)


        # Apply colormap
        self.cmap_name = self.cmap_combobox.currentText()
        self.img.set_cmap(self.cmap_name)

        # Redraw the canvas
        self.ax.figure.canvas.draw_idle()
    
    def handle_ok(self):
        self.apply_settings()
        self.accept()


#============ Define a custom toolbar to handle the save function==============
class CustomToolbar(NavigationToolbar):
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
                    
                    
                    self.canvas.figure.savefig(self.file_path, dpi=dpi, format=self.file_type)
                try:
                    self.canvas.figure.axes[1].set_visible(True)
                except:
                    pass
                
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

            dialog = CustomSettingsDialog(selected_axes, parent=self)
            dialog.exec_()
            
            
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
    def __init__(self, apply_wf, apply_absf, apply_nl, parameters):
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
        delta = QLabel('WF Delta')
        delta.setToolTip('Threashold for diffraction spots removal. Smaller delta gives smoothier averaging background but takes more time.') 
        delta_input = QLineEdit()
        delta_input.setText(default_values['WF Delta'])
        form_layout.addRow(delta, delta_input)
        order = QLabel('WF Bw-order')
        order.setToolTip('The order of the lowpass Butterworth filter. Bigger number gives a steeper cutoff.') 
        order_input = QLineEdit()
        order_input.setText(default_values['WF Bw-order'])
        form_layout.addRow(order, order_input)
        cutoff = QLabel('WF Bw-cutoff')
        cutoff.setToolTip('Fraction of radius in reciprocal space from where the taper of the lowpass starts.')
        cutoff_input = QLineEdit()
        cutoff_input.setText(default_values['WF Bw-cutoff'])
        form_layout.addRow(cutoff, cutoff_input)
        self.wiener_group.setLayout(form_layout)
        
        #self.wiener_group.setLayout(self.create_form_layout(["WF Delta", "WF Bw-order", "WF Bw-cutoff"], default_values, self.parameters))
        self.wiener_group.setEnabled(True)
        #self.wiener_check.stateChanged.connect(lambda: self.wiener_group.setEnabled(self.wiener_check.isChecked()))
        layout.addWidget(self.wiener_check)
        layout.addWidget(self.wiener_group)

        # ABS Filter Section
        self.absf_check = QCheckBox("Apply ABS Filter")
        self.absf_check.setChecked(apply_absf)
        self.absf_group = QGroupBox()
        form_layout = QFormLayout()
        delta = QLabel('ABSF Delta')
        delta.setToolTip('Threashold for diffraction spots removal. Smaller delta gives smoothier averaging background but takes more time.') 
        delta_input = QLineEdit()
        delta_input.setText(default_values['ABSF Delta'])
        form_layout.addRow(delta, delta_input)
        order = QLabel('ABSF Bw-order')
        order.setToolTip('The order of the lowpass Butterworth filter. Bigger number gives a steeper cutoff.') 
        order_input = QLineEdit()
        order_input.setText(default_values['ABSF Bw-order'])
        form_layout.addRow(order, order_input)
        cutoff = QLabel('ABSF Bw-cutoff')
        cutoff.setToolTip('Fraction of radius in reciprocal space from where the taper of the lowpass starts.')
        cutoff_input = QLineEdit()
        cutoff_input.setText(default_values['ABSF Bw-cutoff'])
        form_layout.addRow(cutoff, cutoff_input)
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
        N = QLabel('NL Cycles')
        N.setToolTip('Repetition of Wiener-Lowpass filter cycles. More repetition gives stronger filtering effect but takes more time.')
        N_input = QLineEdit()
        N_input.setText(default_values['NL Cycles'])
        form_layout.addRow(N, N_input)
        delta = QLabel('NL Delta')
        delta.setToolTip('Threashold for diffraction spots removal. Smaller delta gives smoothier averaging background but taks more time.') 
        delta_input = QLineEdit()
        delta_input.setText(default_values['NL Delta'])
        form_layout.addRow(delta, delta_input)
        order = QLabel('NL Bw-order')
        order.setToolTip('The order of the lowpass Butterworth filter. Bigger number gives a steeper cutoff.') 
        order_input = QLineEdit()
        order_input.setText(default_values['NL Bw-order'])
        form_layout.addRow(order, order_input)
        cutoff = QLabel('NL Bw-cutoff')
        cutoff.setToolTip('Fraction of radius in reciprocal space from where the taper of the lowpass starts.')
        cutoff_input = QLineEdit()
        cutoff_input.setText(default_values['NL Bw-cutoff'])
        form_layout.addRow(cutoff, cutoff_input)
        self.nl_group.setLayout(form_layout)
        #self.nl_group.setLayout(self.create_form_layout(["NL Cycles", "NL Delta", "NL Bw-order", "NL Bw-cutoff"], default_values, self.parameters))
        self.nl_group.setEnabled(True)
        #self.nl_check.stateChanged.connect(lambda: self.nl_group.setEnabled(self.nl_check.isChecked()))
        layout.addWidget(self.nl_check)
        layout.addWidget(self.nl_group)

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
        parameters = {label: edit.text() for label, edit in self.parameters.items()}
        
        self.parameters = parameters
        # print(self.parameters)
        
        
        self.accept()

    # def create_form_layout(self, labels, default_values, inputs_dict):
    #     form_layout = QFormLayout()
    #     for label in labels:
    #         line_edit = QLineEdit()
    #         if label in default_values:
    #             line_edit.setText(default_values[label])
    #         form_layout.addRow(QLabel(label), line_edit)
    #         inputs_dict[label] = line_edit
    #     return form_layout
        
    
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


#=============== Display metadata window ===========================
class MetadataViewer(QMainWindow):
    def __init__(self, metadata):
        super().__init__()
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

                 

#==================================================================
# Helper functions

from rsciio.emd import file_reader as emd_reader
from rsciio.digitalmicrograph import file_reader as dm_reader
from rsciio.tia import file_reader as tia_reader
from rsciio.tiff import file_writer as tif_writer
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
                   'NL': filters.nlfilter}
    
    
    if filter_type in filter_dict.keys():
        img = filters.crop_to_square(img)
        img_filtered, _  = filter_dict[filter_type](img, **kwargs)
        return img_filtered


def save_as_tif16(input_file, f_name, output_dir, 
                  apply_wf=False, apply_absf=False, apply_nl=False):
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
        
       
    
    

def save_with_pil(input_file, f_name, output_dir, f_type, scalebar=True, 
                  apply_wf=False, apply_absf=False, apply_nl=False):
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
    try: 
        font = ImageFont.truetype("arial.ttf", fontsize)
    except:
        try: 
            font = ImageFont.truetype("Helvetica.ttc", fontsize)
        except:
            font = ImageFont.load_default()
    txt_x, txt_y = (sb_start_x * 1.1, sb_start_y - fontsize * 1.1 - im_y/80)
    # Add outline to the text
    dx = im_x / 800
    draw.text((txt_x-dx, txt_y-dx), text, font=font, fill='black')
    draw.text((txt_x+dx, txt_y-dx), text, font=font, fill='black')
    draw.text((txt_x-dx, txt_y+dx), text, font=font, fill='black')
    draw.text((txt_x+dx, txt_y+dx), text, font=font, fill='black')
    draw.text((txt_x, txt_y), text, fill='white', font=font, anchor=None)  
    

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
    scale_bar = kwargs['scalebar']
    #Save images

    #Check if the output_dir exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    if apply_wf:
        input_file['wf'] = apply_filter(input_file['data'], 'Wiener', 
                                delta=delta_wf, lowpass_order=order_wf, lowpass_cutoff=cutoff_wf)
        
    if apply_absf:
        input_file['absf'] = apply_filter(input_file['data'], 'ABS',
                                          delta=delta_absf, lowpass_order=order_absf, lowpass_cutoff=cutoff_absf)
        
    if apply_nl:
        input_file['nl'] = apply_filter(input_file['data'], 'NL', 
                                        N=N, delta=delta_nl, lowpass_order=order_nl, lowpass_cutoff=cutoff_nl)
    
    if f_type == 'tiff':
        # For tiff format, save directly as 16-bit with calibration, no scalebar
        # No manipulation of data but just set to int16
        save_as_tif16(input_file, f_name, output_dir, apply_wf=apply_wf, apply_absf=apply_absf, apply_nl=apply_nl)

    else:
        if f_type == 'tiff + png':
            save_as_tif16(input_file, f_name, output_dir, apply_wf=apply_wf, apply_absf=apply_absf, apply_nl=apply_nl)
            f_type = 'png'
            
        save_with_pil(input_file, f_name, output_dir, f_type, scalebar=scale_bar, apply_wf=apply_wf, apply_absf=apply_absf, apply_nl=apply_nl)
        
        
        
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

def measure_distance(A, B, scale=1):
    x0, y0 = A
    x1, y1 = B
    distance_pixels = np.sqrt((x1 - x0)**2 + (y1 - y0)**2)
    distance_units = distance_pixels * scale
    return distance_units

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

def main():
    
   
    app = QApplication(sys.argv)
    
    
    
    temcom = UI_TemCompanion()
    temcom.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    
    
    
    main()
