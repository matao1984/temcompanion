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

# 2025-10-20 v1.3.0
# Reorganized the project structure
# Redesigned the main UI with pyqtgraph
# Optimized operation workflow with pyqtgraph functions
# Modified filteres to take non-square images
# Live iFFT also takes non-square images

from PyQt5.QtWidgets import (QApplication, QMainWindow,  QVBoxLayout, 
                             QWidget, QPushButton, QMessageBox, QFileDialog, 
                             QHBoxLayout, QLabel, QCheckBox, QTextBrowser, QDockWidget
                             )
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QDropEvent, QDragEnterEvent


import sys
import os
import pickle


#===================Import internal modules==========================================

from .functions import load_file, getFileNameType
from .batch_convert import BatchConverter
from .canvas import PlotCanvas

        
#=====================Main Window UI ===============================================


class UI_TemCompanion(QMainWindow):
    # Define filter parameters as class variables        
    filter_parameters = {"WF Delta": "10", "WF Bw-order": "4", "WF Bw-cutoff": "0.3",
                        "ABSF Delta": "10", "ABSF Bw-order": "4", "ABSF Bw-cutoff": "0.3",
                        "NL Cycles": "10", "NL Delta": "10", "NL Bw-order": "4", "NL Bw-cutoff": "0.3",
                        "Bw-order": "4", "Bw-cutoff": "0.3",
                        "GS-cutoff": "0.3",
                        "GS-HP-cutoff": "0.005"
                        }
    
    #Preview dict as class variable
    preview_dict = {}

    def __init__(self, config):
        super().__init__()
        # Environment variables
        self.ver = config.pop('version')
        self.rdate = config.pop('release_date')
        self.wkdir = config.pop('working_directory')
        self.colormap = config.pop('colormap')

        self.attribute = config  # Remaining config items are default image settings

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
            ext = getFileNameType(file)[1].lower()
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
        

        
    


    def setupUi(self):
        # Window size 
        self.size_with_dock = 400, 450
        self.size_without_dock = 400, 100
        self.setObjectName("TemCompanion")
        self.setWindowTitle(f"TemCompanion Ver {self.ver}")
        self.resize(*self.size_with_dock)
        
        
        # Central widget + layout 
        central = QWidget(self)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        buttonlayout = QHBoxLayout()
        
        self.openfileButton = QPushButton(self)
        self.openfileButton.setFixedSize(80, 60)
        self.openfileButton.setObjectName("OpenFile")
        self.openfileButton.setText('Open \nImages')
        
        
        
        self.convertButton = QPushButton(self)
        self.convertButton.setFixedSize(80, 60)
        self.convertButton.setObjectName("BatchConvert")
        self.convertButton.setText("Batch \nConvert")
        
        
        
        
        self.aboutButton = QPushButton(self)
        self.aboutButton.setFixedSize(80, 60)
        self.aboutButton.setObjectName("aboutButton")
        self.aboutButton.setText("About")
        
        self.contactButton = QPushButton(self)
        self.contactButton.setFixedSize(80, 60)
        self.contactButton.setObjectName("contactButton")
        self.contactButton.setText("Contact")

        self.donateButton = QPushButton(self)
        self.donateButton.setFixedSize(80, 60)
        self.donateButton.setObjectName("donateButton")
        self.donateButton.setText("Buy me\n a LUNCH!")

        buttonlayout.addWidget(self.openfileButton)
        buttonlayout.addWidget(self.convertButton)
        buttonlayout.addWidget(self.aboutButton)
        buttonlayout.addWidget(self.contactButton)
        buttonlayout.addWidget(self.donateButton)

        layout.addLayout(buttonlayout)

        # Add a horizontal layout for author label and output dock toggle
        author_layout = QHBoxLayout()
        
        self.authorlabel = QLabel(self)
        self.authorlabel.setObjectName("authorlabel")
        self.authorlabel.setText(f'TemCompanion by Dr. Tao Ma   {self.rdate}')
        author_layout.addWidget(self.authorlabel)
        
        # Add stretch to push the checkbox to the right
        author_layout.addStretch(1)
        
        # Add the output dock toggle checkbox
        self.output_toggle = QCheckBox("Show Output", self)
        self.output_toggle.setChecked(True)
        author_layout.addWidget(self.output_toggle)
        
        layout.addLayout(author_layout)

        layout.addStretch(1)

        central.setLayout(layout)
        self.setCentralWidget(central)
        
        # self.outputBox = QTextEdit(self, readOnly=True)
        # #self.outputBox.setGeometry(35, 90, 350, 210)
        # self.outputBox.resize(350, 240)
        # layout.addWidget(self.outputBox)   
        

        self.outputBox = QTextBrowser(self)
        self.outputBox.setOpenExternalLinks(True)  # open http(s) links in default browser
        self.outputBox.setOpenLinks(True)          # allow internal anchors (if any)
        self.outputBox.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.outputBox.resize(350, 220)
        # layout.addWidget(self.outputBox)

        # Add the dock widget at the bottom (sticky to bottom, detachable)
        self.outputDock = QDockWidget("Output", self)
        self.outputDock.setObjectName("OutputDock")
        self.outputDock.setAllowedAreas(Qt.BottomDockWidgetArea)  # stick to bottom area
        self.outputDock.setFeatures(
            QDockWidget.DockWidgetMovable |
            QDockWidget.DockWidgetFloatable |
            QDockWidget.DockWidgetClosable
        )
        self.outputDock.setWidget(self.outputBox)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.outputDock)
        self.resizeDocks([self.outputDock], [350], Qt.Vertical)
        
        # Connect signal to handle dock detachment
        self.outputDock.topLevelChanged.connect(self._on_dock_toplevel_changed)

        # Connect the checkbox to the dock's toggleViewAction
        # toggle_action = self.outputDock.toggleViewAction()
        self.output_toggle.toggled.connect(self.toggle_dock)
        self.outputDock.visibilityChanged.connect(self._on_dock_visibility_changed)
        # toggle_action.toggled.connect(self.output_toggle.setChecked)


        # Connect all functions
        self.openfileButton.clicked.connect(self.openfile)       
        self.convertButton.clicked.connect(self.batch_convert)
        self.aboutButton.clicked.connect(self.show_about)
        self.contactButton.clicked.connect(self.show_contact)
        self.donateButton.clicked.connect(self.donate) 

        


    def _on_dock_toplevel_changed(self, topLevel):
        """Handle dock widget detach/reattach to maintain main window size"""
        if topLevel:
            # Use QTimer with a direct connection instead of lambda
            QTimer.singleShot(10, lambda: self.resize(*self.size_without_dock))
        else:
            # Dock is being reattached
            # Restore the stored geometry if it exists
            QTimer.singleShot(10, self.restore_dock)

    def _on_dock_visibility_changed(self, visible):
        """Update checkbox state when dock is closed/shown"""
        # Block signals to prevent triggering toggle_dock
        self.output_toggle.blockSignals(True)
        self.output_toggle.setChecked(visible)
        self.output_toggle.blockSignals(False)       
        # Resize main window according to visibility
        if visible:
            QTimer.singleShot(10, self.restore_dock)
        else:
            QTimer.singleShot(10, lambda: self.resize(*self.size_without_dock))

                

    def restore_dock(self):
        """Helper function to reattach the dock if needed"""
        self.resize(*self.size_with_dock)
        self.resizeDocks([self.outputDock], [350], Qt.Vertical)
        
    def toggle_dock(self, checked):
        """Show or hide the output dock based on checkbox state"""
        if checked:
            self.outputDock.blockSignals(True)
            self.outputDock.setFloating(False)  # Reattach if floating
            self.outputDock.setVisible(True)
            self.restore_dock()
            self.outputDock.blockSignals(False)
        else:
            self.outputDock.setVisible(False)
            self.resize(*self.size_without_dock)

     
        
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
            <p style="font-size: 11px; margin-left: 20px">
                Tao Ma, <i>TemCompanion: An open-source multi-platform GUI program for TEM image processing and analysis</i>, 
                <b>SoftwareX</b>, 2025, <b>31</b>, 102212. 
                <a href="https://doi.org/10.1016/j.softx.2025.102212">doi:10.1016/j.softx.2025.102212</a>
            </p>
            <p style="font-size: 12px;">
                Address your questions and suggestions to 
                <a href="mailto:matao1984@gmail.com">matao1984@gmail.com</a>
            </p>
            <p style="font-size: 12px;">
                See the <b>About</b> for more details. <a href="https://paypal.me/matao1984?country.x=US&locale.x=en_US">Buy me a lunch</a> if you like it!
            </p>
            <p style="text-align: left; font-size: 12px">
                Version: <b>{ver}</b> | Released: <b>{rdate}</b>
            </p>
        </div>
        '''.format(ver=self.ver, rdate=self.rdate)
        
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
        self.converter = BatchConverter(parent=self)
        self.converter.show()
            
        
#=====================================================================        
    def show_about(self):
        msg = QMessageBox()
#        msg.setIcon(QMessageBox.Information)
        msg.setText("TemCompanion: a comprehensive package for TEM data processing and analysis."\
                    "<br>"\
                    "This app was designed by Dr. Tao Ma"\
                    "<br>"\
                    "Version: {}  Released: {}"\
                    "<br>"\
                    "If TemCompanion helped your TEM image analysis in a publication, please cite:"\
                    "<br>"
                    "Tao Ma, TemCompanion: An open-source multi-platform GUI program for TEM image processing and analysis, "\
                    "SoftwareX, 2025, 31, 102212. "\
                    "<a href=\"https://doi.org/10.1016/j.softx.2025.102212\">doi:10.1016/j.softx.2025.102212</a>"
                    "<br>"\
                    "Get more information and source code from <a href=\"https://github.com/matao1984/temcompanion\">here</a>.".format(self.ver, self.rdate))
        msg.setWindowTitle(f"{self.ver}: About")

        msg.exec()
        

#=====================================================================        
    def show_contact(self):
        msg = QMessageBox()
        msg.setText("Ask questions and report bugs to:"\
                    "<br>"
                    "<a href=\"mailto:matao1984@gmail.com\">matao1984@gmail.com</a>")
        msg.setWindowTitle(self.ver + ": Contact")

        msg.exec()
        
#====================================================================
        
    def donate(self):
        msg = QMessageBox()
        msg.setText("If you like this app, show your appreciation and <a href=\"https://paypal.me/matao1984?country.x=US&locale.x=en_US\">buy me a lunch!</a>"\
                    "<br>"\
                    "Your support is my motivation!")
        msg.setWindowTitle(self.ver + ": Buy me a LUNCH!")

        msg.exec()



        
# ====================== Open file for preview ===============================
    def preview(self):
        
        try:
            f = load_file(self.file, self.file_type)
            if f == None:
                return
            f_name = getFileNameType(self.file)[0]
            
            
        
            for i in range(len(f)):
                img = f[i]

                if 'title' in img['metadata']['General']:
                    title = img['metadata']['General']['title']
                else:
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
        
        
         



                   
#====Application entry==================================
# Splash screen for windows app
# import pyi_splash







# Update the text on the splash screen
# pyi_splash.update_text("Loading...")


# Close the splash screen. It does not matter when the call
# to this function is made, the splash screen remains open until
# this function is called or the Python program is terminated.
# pyi_splash.close()

def main(config):    
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    wkdir = config['working_directory']
    app.setWindowIcon(QIcon(os.path.join(wkdir, "icons/icon.ico")))

    temcom = UI_TemCompanion(config)
    temcom.show()
    temcom.raise_()
    temcom.activateWindow()
    sys.exit(app.exec_())
    



    

    
