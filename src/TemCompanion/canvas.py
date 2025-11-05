from PyQt5 import QtCore

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox, 
                             QFileDialog, QDialog, QAction, QLabel, QStatusBar, 
                             QProgressBar, QToolBar
                             )
from PyQt5.QtCore import Qt,  QThread, QRectF, QSize, pyqtSignal
from PyQt5.QtGui import QIcon

import os
import numpy as np
import copy


import pickle
from collections import OrderedDict

import pyqtgraph as pg
import pyqtgraph.exporters

from scipy.fft import fft2, fftshift, ifft2, ifftshift
from skimage.filters import window
from skimage.measure import profile_line
from scipy.ndimage import rotate, shift
from skimage.registration import phase_cross_correlation, optical_flow_ilk
from skimage.transform import warp, rescale, resize

from rsciio.tiff import file_writer as tif_writer
from rsciio.image import file_writer as im_writer

# Internal imports
from .UI_elements import (FilterSettingDialog, MainFrameCanvas, CustomScaleBar, 
                          SetScaleDialog, CustomSettingsDialog, RotateImageDialog,
                          SimpleMathDialog, DPCDialog, RadialIntegrationDialog, 
                          ManualCropDialog, ApplyFilterDialog, ListReorderDialog,
                          AlignStackDialog, MetadataViewer, PlotSettingDialog, 
                          gpaSettings
                        )

from .functions import (getDirectory, getFileNameType, save_as_tif16, save_with_pil,
                        find_img_by_title, apply_filter_on_img_dict, calculate_angle_to_horizontal
                        )

from . import filters
from .GPA import GPA, norm_img, create_mask, refine_center


class PlotCanvas(QMainWindow):
    def __init__(self, img, parent):
        # parent must be the main UI_TemCompanion window
        super().__init__(parent)
        self.ver = self.parent().ver
        self.wkdir = self.parent().wkdir
        self.colormap = self.parent().colormap
        self.attribute = copy.deepcopy(self.parent().attribute)  # Default image settings

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setFocusPolicy(Qt.StrongFocus)
        self.img_size = img['data'].shape

        # Load default filter parameters from the main window class
        self.filter_parameters = self.parent().filter_parameters
 
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
        if 'TemCompanion' in img['metadata']:
            self.process = copy.deepcopy(img['metadata']['TemCompanion'])
            # Update some info
            self.process['Image Size (pixels)'] = f"{self.canvas.img_size[-1]} x {self.canvas.img_size[-2]}"
            self.process['Calibrated Image Size'] = f"{self.canvas.img_size[-1] * self.scale:.4g} x {self.canvas.img_size[-2] * self.scale:.4g} {self.units}"
            self.process['Pixel Calibration'] = f"{self.scale:.4g} {self.units}"
        else:
            # Make a new process history
            self.process = {'Version': f'TemCompanion v{self.ver}', 
                            'Data Type': f'{self.canvas.data_type}',
                            'File Name': self.parent().file,
                            'Image Size (pixels)': f"{self.canvas.img_size[-1]} x {self.canvas.img_size[-2]}",
                            'Calibrated Image Size': f"{self.canvas.img_size[-1] * self.scale:.4g} x {self.canvas.img_size[-2] * self.scale:.4g} {self.units}", 
                            'Pixel Calibration': f"{self.scale:.4g} {self.units}",
                            'process': []}
            img['metadata']['TemCompanion'] = self.process
        
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
        self.canvas.create_img(cmap=self.attribute['cmap'],
                               pvmin=self.attribute['pvmin'],
                               pvmax=self.attribute['pvmax'],
                               gamma=self.attribute['gamma']
                               )

        # Tool bar
        self.create_toolbar()

        # Create menu bar
        self.create_menubar()

        self.resize(600, 650)

    def closeEvent(self, event):
        self.parent().preview_dict.pop(self.canvas.canvas_name, None)

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
        home_icon = os.path.join(self.wkdir, 'icons/home.png')
        home_action = QAction(QIcon(home_icon), "Home", self)
        home_action.setStatusTip("Auto scale to fit the window")
        home_action.triggered.connect(self.canvas.custom_auto_range)
        self.toolbar.addAction(home_action)

        self.toolbar.addSeparator()

        save_icon = os.path.join(self.wkdir, 'icons/save.png')
        save_action = QAction(QIcon(save_icon), "Save", self)
        save_action.setStatusTip("Save the current image")
        save_action.triggered.connect(self.save_figure)
        self.toolbar.addAction(save_action)

        copy_icon = os.path.join(self.wkdir, 'icons/copy.png')
        copy_action = QAction(QIcon(copy_icon), "Copy", self)
        copy_action.setStatusTip("Copy the current image")
        copy_action.triggered.connect(self.copy_img)
        self.toolbar.addAction(copy_action)

        setting_icon = os.path.join(self.wkdir, 'icons/settings.png')
        setting_action = QAction(QIcon(setting_icon), "Settings", self)
        setting_action.setStatusTip("Open settings")
        setting_action.triggered.connect(self.image_settings)
        self.toolbar.addAction(setting_action)

        self.toolbar.addSeparator()

        crop_icon = os.path.join(self.wkdir, 'icons/crop.png')
        crop_action = QAction(QIcon(crop_icon), "Crop", self)
        crop_action.setStatusTip("Crop the image")
        crop_action.triggered.connect(self.crop)
        self.toolbar.addAction(crop_action)

        measure_icon = os.path.join(self.wkdir, 'icons/measure.png')
        measure_action = QAction(QIcon(measure_icon), "Measure", self)
        measure_action.setStatusTip("Measure distance and angle")
        measure_action.triggered.connect(self.measure)
        self.toolbar.addAction(measure_action)

        measurefft_icon = os.path.join(self.wkdir, 'icons/measure_fft.png')
        measurefft_action = QAction(QIcon(measurefft_icon), 'Measure FFT', self)
        measurefft_action.setStatusTip('Measure distance and angle in Diffraction/FFT')
        measurefft_action.triggered.connect(self.measure_fft)
        self.toolbar.addAction(measurefft_action)

        lineprofile_icon = os.path.join(self.wkdir, 'icons/lineprofile.png')
        lineprofile_action = QAction(QIcon(lineprofile_icon), "Line Profile", self)
        lineprofile_action.setStatusTip("Extract line profile")
        lineprofile_action.triggered.connect(self.lineprofile)
        self.toolbar.addAction(lineprofile_action)

        self.toolbar.addSeparator()

        fft_icon = os.path.join(self.wkdir, "icons/fft.png")
        fft_action = QAction(QIcon(fft_icon), "FFT", self)
        fft_action.setStatusTip("Compute FFT of the image")
        fft_action.triggered.connect(self.fft)
        self.toolbar.addAction(fft_action)

        livefft_icon = os.path.join(self.wkdir, "icons/live-fft.png")
        livefft_action = QAction(QIcon(livefft_icon), "Live FFT", self)
        livefft_action.setStatusTip("Compute live FFT of the image")
        livefft_action.triggered.connect(self.live_fft)
        self.toolbar.addAction(livefft_action)

        self.toolbar.addSeparator()

        wf_icon = os.path.join(self.wkdir, "icons/WF.png")
        wf_action = QAction(QIcon(wf_icon), "Wiener Filter", self)
        wf_action.setStatusTip("Apply Wiener filter to the image")
        wf_action.triggered.connect(self.wiener_filter)
        self.toolbar.addAction(wf_action)

        absf_icon = os.path.join(self.wkdir, "icons/ABSF.png")
        absf_action = QAction(QIcon(absf_icon), "ABS Filter", self)
        absf_action.setStatusTip("Apply ABSF to the image")
        absf_action.triggered.connect(self.absf_filter)
        self.toolbar.addAction(absf_action)

        nl_icon = os.path.join(self.wkdir, "icons/NL.png")
        nl_action = QAction(QIcon(nl_icon), "Non-linear Filter", self)
        nl_action.setStatusTip("Apply Non-linear filter to the image")
        nl_action.triggered.connect(self.non_linear_filter)
        self.toolbar.addAction(nl_action)

        gaussian_icon = os.path.join(self.wkdir, "icons/GS.png")
        gaussian_action = QAction(QIcon(gaussian_icon), "Gaussian Filter", self)
        gaussian_action.setStatusTip("Apply Gaussian filter to the image")
        gaussian_action.triggered.connect(self.gaussian_filter)
        self.toolbar.addAction(gaussian_action)

        self.toolbar.addSeparator()

        info_icon = os.path.join(self.wkdir, "icons/info.png")
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
        screen_top = screen_geometry.top()
        screen_left = screen_geometry.left()
        frame_size = self.frameGeometry()
        
        if pos == 'center':
            x = screen_left + (width - frame_size.width()) // 2
            y = screen_top + (height - frame_size.height()) // 2

        elif pos == 'center left':
            x = screen_left + (width // 2 - frame_size.width())
            y = screen_top + (height - frame_size.height()) // 2

        elif pos == 'center right':
            x = screen_left + (width // 2)
            y = screen_top + (height - frame_size.height()) // 2

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

        # Clamp coordinates to screen bounds (including top screen offset)
        
        x = max(screen_left, min(x, screen_left + width - frame_size.width()))
        y = max(screen_top, min(y, screen_top + height - frame_size.height()))   
                
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
    
    def plot_new_image(self, img_dict, canvas_name, parent=None, metadata=None, position=None):
        # Plot a new image in a new window
        # parent: the parent widget for the new image canvas
        # metadata: optional metadata to add in the image dictionary
        # position: the position of the new image canvas
        # Returns the new canvas object
        main_window = self.parent()
        plot = PlotCanvas(img_dict, parent=self.parent())
        plot.setWindowTitle(canvas_name)
        plot.canvas.canvas_name = canvas_name
        main_window.preview_dict[canvas_name] = plot

        if metadata is not None:
            plot.update_metadata(metadata)

        if position is not None:
            plot.position_window(position)
        plot.show()

        return plot



    def update_metadata(self, metadata):
        # Update the metadata of the current canvas
        self.process['process'].append(metadata)
        self.canvas.data['metadata']['TemCompanion'] = copy.deepcopy(self.process)

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
        filtersetting_action.triggered.connect(self.filter_settings)
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
        about_action.triggered.connect(self.parent().show_about)
        info_menu.addAction(about_action)

        self.menubar = menubar
        

    def image_settings(self):
        dialog = CustomSettingsDialog(self.canvas.image_item, parent=self)
        dialog.show()
        # Move the dialog next to the main window
        dialog.position_window('next to parent')


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
            self.f_name, self.file_type = getFileNameType(self.file_path)          
            self.output_dir = getDirectory(self.file_path)
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
        plots = list(self.parent().preview_dict.keys())
        for plot in plots:
            try:
                self.parent().preview_dict[plot].close()
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
            metadata = f'Rotated {title} by {ang} degrees counterclockwise.'
            self.plot_new_image(img, preview_name, parent=self.parent(), metadata=metadata, position='center right')
            print(f'Rotated {title} by {ang} degrees counterclockwise.')
            
            # Positioning
            self.position_window('center left')            
            
    
            
    
    def flip_horizontal(self):
        img = self.get_img_dict_from_canvas()
        img_to_flip = img['data']
        flipped_array = np.fliplr(img_to_flip)
        img['data'] = flipped_array
        
        # Create a new PlotCanvs to display        
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_Flipped_LR'
        metadata = f'Flipped {title} horizontally.'
        self.plot_new_image(img, preview_name, parent=self.parent(), metadata=metadata, position='center right')

        print(f'Flipped {title} horizontally.')
        
        # Positioning
        self.position_window('center left')
        
        
    def flip_vertical(self):
        img = self.get_img_dict_from_canvas()
        img_to_flip = img['data']
        flipped_array = np.flipud(img_to_flip)
        img['data'] = flipped_array
        
        # Create a new PlotCanvs to display        
        title = self.windowTitle()
        preview_name = self.canvas.canvas_name + '_Flipped_UD'
        metadata = f'Flipped {title} vertically.'
        self.plot_new_image(img, preview_name, parent=self.parent(), metadata=metadata, position='center right')

        
        print(f'Flipped {title} vertically.')
        
        # Positioning
        self.position_window('center left')

        

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
            self.plot_new_image(img, preview_name, parent=self.parent(),metadata=f'Resampled {title} by a factor of {rescale_factor}.', position='center right')
            print(f'Resampled {title} by a factor of {rescale_factor}.')
            
            # Positioning
            self.position_window('center left')


    def simplemath(self):
        img_list = self.parent().preview_dict
        dialog = SimpleMathDialog(img_list, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            signal1 = dialog.signal1
            signal2 = dialog.signal2
            operation = dialog.operation
            try:
                img1 = copy.deepcopy(find_img_by_title(img_list, signal1).canvas.data)
            except Exception as e:
                QMessageBox.warning(self, 'Simple Math', f'Operation not possible on image 1: {e}')
                return
            try:
                img2 = copy.deepcopy(find_img_by_title(img_list, signal2).canvas.data)
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
                print(f'Inversed signal of {signal1}.')
            else:
                metadata = f'Processed by {signal1} {operation} {signal2}'
                print(f'Processed {signal1} {operation} {signal2}.')

            self.plot_new_image(img1, canvas_name=preview_name, parent=self.parent(), metadata=metadata, position='center')

            
    def dpc(self):
        img_list = self.parent().preview_dict
        self.dpc_dialog = DPCDialog(img_list, parent=self)
        self.dpc_dialog.show()

    def filter_settings(self):
        dialog = FilterSettingDialog(self.filter_parameters, parent=self)
        dialog.show()
        if dialog.exec_() == QDialog.Accepted:
            self.filter_parameters = dialog.parameters

    def wiener_filter(self):        
        filter_parameters = self.filter_parameters
        try:
            delta_wf = int(filter_parameters['WF Delta'])
            order_wf = int(filter_parameters['WF Bw-order'])
            cutoff_wf = float(filter_parameters['WF Bw-cutoff'])
        except ValueError:
            QMessageBox.warning(self, 'Invalid Parameters', 'Please enter valid numbers for the filter parameters.')
            return
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
            self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata, position='center right'))
            self.thread.start()        
        

    def absf_filter(self):
        filter_parameters = self.filter_parameters
        try: 
            delta_absf = int(filter_parameters['ABSF Delta'])
            order_absf = int(filter_parameters['ABSF Bw-order'])
            cutoff_absf = float(filter_parameters['ABSF Bw-cutoff'])
        except ValueError:
            QMessageBox.warning(self, 'Invalid Parameters', 'Please enter valid numbers for the filter parameters.')
            return
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
            self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata, position='center right'))
            self.thread.start()


    
    def non_linear_filter(self):
        filter_parameters = self.filter_parameters  
        try: 
            delta_nl = int(filter_parameters['NL Delta'])
            order_nl = int(filter_parameters['NL Bw-order'])
            cutoff_nl = float(filter_parameters['NL Bw-cutoff'])
            N = int(filter_parameters['NL Cycles'])
        except ValueError:
            QMessageBox.warning(self, 'Invalid Parameters', 'Please enter valid numbers for the filter parameters.')
            return      
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
            self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata, position='center right'))
            self.thread.start()

    def bw_filter(self):
        filter_parameters = self.filter_parameters
        try: 
            order_bw = int(filter_parameters['Bw-order'])
            cutoff_bw = float(filter_parameters['Bw-cutoff'])
        except ValueError:
            QMessageBox.warning(self, 'Invalid Parameters', 'Please enter valid numbers for the filter parameters.')
            return
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
            self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata, position='center right'))
            self.thread.start()


        

    def gaussian_filter(self):
        filter_parameters = self.filter_parameters
        try: 
            cutoff_gaussian = float(filter_parameters['GS-cutoff'])
            hp_cutoff_gaussian = float(filter_parameters['GS-hp-cutoff'])
        except ValueError:
            QMessageBox.warning(self, 'Invalid Parameters', 'Please enter valid numbers for the filter parameters.')
            return
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
            # Tailor metadata based on high-pass cutoff
            if hp_cutoff_gaussian <= 0 or hp_cutoff_gaussian >=1: # No high-pass filter
                metadata = f'Gaussian low-pass filter applied with cutoff = {cutoff_gaussian}'
            elif cutoff_gaussian <= 0 or cutoff_gaussian >=1: # No low-pass filter
                metadata = f'Gaussian high-pass filter applied with cutoff = {hp_cutoff_gaussian}'
            else:
                # Both filters applied, this is a band pass filter
                metadata = f'Gaussian band-pass filter applied with low cutoff = {hp_cutoff_gaussian} and high cutoff = {cutoff_gaussian}'
            
            # Position the current image
            self.position_window('center left')

            # Apply the filter in a separate thread
            print(f'Applying {metadata} to {title}...')
            self.thread = QThread()
            self.worker = Worker(apply_filter_on_img_dict, img_gaussian, 'Gaussian', cutoff_ratio=cutoff_gaussian, hp_cutoff_ratio=hp_cutoff_gaussian)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(lambda: self.toggle_progress_bar('ON'))
            self.thread.started.connect(self.worker.run)            
            self.thread.finished.connect(lambda: self.toggle_progress_bar('OFF'))
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)           
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.finished.connect(lambda: print(f'Applied {metadata}.'))
            self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata, position='center right'))
            self.thread.start()


    def show_info(self):
        # Show image infomation including metadata
        img_dict = self.get_original_img_dict()
        metadata = img_dict['metadata']
        
        try: 
            extra_metadata = img_dict['original_metadata']
            metadata.update(extra_metadata)
        except Exception as e:
            pass
        
        img_info = OrderedDict()
        img_info['TemCompanion'] = metadata.pop('TemCompanion')
        
        # Add axes info to metadata
        axes = img_dict['axes']
        axes_dict = {}
        for ax in axes:
            axes_dict[ax['name']] = ax
        img_info['Axes'] = axes_dict
        

        img_info['Metadata'] = metadata

        self.metadata_viewer = MetadataViewer(img_info, parent=self)
        self.metadata_viewer.show()

    def fft(self):
        img_dict = self.get_img_dict_from_canvas()
        # FFT calculation is handled in the PlotCanvasFFT class

        title = self.canvas.canvas_name
        
        preview_name = title + '_FFT'
        
        fft_plot = PlotCanvasFFT(img_dict, title, parent=self.parent())
        fft_plot.setWindowTitle(preview_name)
        fft_plot.canvas.canvas_name = preview_name
        fft_plot.update_metadata(f'FFT of {title}.')
        self.parent().preview_dict[preview_name] = fft_plot
        fft_plot.show()
        print(f'Performed FFT on {title}.')
        
        # Positioning
        self.position_window('center left')
        fft_plot.position_window('center right')
        
        
        
    
    def windowedfft(self):
        img_dict = self.get_img_dict_from_canvas()
        # Crop to a square if not
        data = img_dict['data']
        # if data.shape[0] != data.shape[1]:
        #     # Image will be cropped to square for FFT
        #     data = filters.crop_to_square(data)
        #     new_size = data.shape[0]
        #     for ax in img_dict['axes']:
        #         ax['size'] = new_size

        w = window('hann', data.shape)
        img_dict['data'] = data * w
        # FFT calculation is handled in the PlotCanvasFFT class

        title = self.canvas.canvas_name
        
        preview_name = title + '_Windowed_FFT'

        fft_plot = PlotCanvasFFT(img_dict, title, parent=self.parent())
        fft_plot.setWindowTitle(preview_name)
        fft_plot.canvas.canvas_name = preview_name
        fft_plot.update_metadata(f'Windowed FFT of {title}.')
        self.parent().preview_dict[preview_name] = fft_plot
        fft_plot.show()
        print(f'Performed FFT on {title} with a Hann window.')
        
        # Positioning
        self.position_window('center left')
        fft_plot.position_window('center right')

    def live_fft(self, fullsize=False, windowed=False, resize_fft=False):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)  # Clean up any existing modes or selectors
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
        title = self.canvas.canvas_name
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
        fft_plot = PlotCanvasFFT(self.live_img, title, parent=self.parent())
        fft_plot.setWindowTitle(preview_name)
        fft_plot.canvas.canvas_name = preview_name
        self.parent().preview_dict[preview_name] = fft_plot
        fft_plot.show()
        fft_plot.update_metadata(f'Live FFT of {title}.')
        print(f'Displaying live FFT of {title} from {x0},{y0},{x1},{y1}.')
        # Positioning
        self.position_window('center left')
        fft_plot.position_window('center right')

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
            if preview_name in self.parent().preview_dict:
                fft_canvas = self.parent().preview_dict[preview_name]
                fft_canvas.update_fft_with_img(self.live_img, resize_fft=resize_fft)
                print(f'Displaying live FFT of {self.canvas.canvas_name} from {x0},{y0},{x1},{y1}.')

    def stop_live_fft(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)  # Clean up any existing modes or selectors

            
    def crop(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)  # Clean up any existing modes or selectors

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
        OK_icon = os.path.join(self.wkdir, 'icons/OK.png')
        self.buttons['ok'] = QAction(QIcon(OK_icon), 'Confirm Crop', parent=self)
        self.buttons['ok'].setShortcut('Return')
        self.buttons['ok'].setStatusTip('Confirm Crop (Enter)')
        self.buttons['ok'].triggered.connect(self.confirm_crop)
        self.toolbar.addAction(self.buttons['ok'])
        cancel_icon = os.path.join(self.wkdir, 'icons/cancel.png')
        self.buttons['cancel'] = QAction(QIcon(cancel_icon), 'Cancel Crop', parent=self)
        self.buttons['cancel'].setShortcut('Esc')
        self.buttons['cancel'].setStatusTip('Cancel Crop (Esc)')
        self.buttons['cancel'].triggered.connect(self.cancel_crop)
        self.toolbar.addAction(self.buttons['cancel'])

        hand_icon = os.path.join(self.wkdir, 'icons/hand.png')
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
            x0, x1, y0, y1 = round(x0 / self.scale), round(x1 / self.scale), round(y0 / self.scale), round(y1 / self.scale)
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
                self.plot_new_image(img, preview_name, parent=self.parent(), metadata=metadata, position='center right')

                # Positioning
                self.position_window('center left')
                
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
        OK_icon = os.path.join(self.wkdir, 'icons/OK.png')
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
        # self._make_active_selector(selector)
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
        OK_icon = os.path.join(self.wkdir, 'icons/OK.png')
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
        self.canvas.viewbox.addItem(selector)
        self._make_active_selector(selector)
        

        line_x, line_profile = self.extract_line_profile()
        x_label = f'Distance ({self.units})'
        y_label = 'Intensity (a.u.)'
        title = self.canvas.canvas_name + '_Line Profile'

        # Plot the line profile in a new window
        line_profile_window = PlotCanvasSpectrum(line_x, line_profile, self.canvas.canvas_name, parent=self.parent())
        line_profile_window.create_plot(xlabel=x_label, ylabel=y_label, title=title)
        line_profile_window.canvas.canvas_name = title
        self.parent().preview_dict[title] = line_profile_window
        self.parent().preview_dict[title].setWindowTitle(title)
        line_profile_window.show()
        # Positioning
        self.position_window('center left')
        self.parent().preview_dict[title].position_window('center right')

        # Connect signals for line change
        selector.sigRegionChanged.connect(self.update_line_profile)
        self.setFocus()  # Ensure the canvas has focus to receive key events

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
            preview_name = self.canvas.canvas_name + '_Line Profile'
            line_x, line_profile = self.extract_line_profile()
            self.parent().preview_dict[preview_name].update_plot(line_x, line_profile)


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

        # Handle plot once dialog is accepted
        if self.radial_integration_dialog.exec_() == QDialog.Accepted:
            self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)  # Clean up any existing modes or selectors
            # Plot the radial profile
            center = self.radial_integration_dialog.center
            preview_name = self.windowTitle() + f'_radial_profile from {center}'
            x_data = self.radial_integration_dialog.x_data
            y_data = self.radial_integration_dialog.y_data
            x_label = f'Radial Distance ({self.units})'
            y_label = 'Integrated Intensity (Counts)'
            plot = PlotCanvasSpectrum(x_data, y_data, parent=self.parent())
            plot.create_plot(xlabel=x_label, ylabel=y_label, title=preview_name)
            plot.canvas.canvas_name = preview_name
            self.parent().preview_dict[preview_name] = plot
            self.parent().preview_dict[preview_name].show()

            print(f'Performed radial integration on {self.windowTitle()} from the center: {center}.')

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
        OK_icon = os.path.join(self.wkdir, 'icons/OK.png')
        self.buttons['ok'] = QAction(QIcon(OK_icon), 'Finish', parent=self)
        self.buttons['ok'].setStatusTip('Finish Measurement')
        self.buttons['ok'].setShortcut('Esc')
        self.buttons['ok'].triggered.connect(self.stop_fft_measurement)
        self.toolbar.addAction(self.buttons['ok'])
        center_icon = os.path.join(self.wkdir, 'icons/dp_center.png')
        self.buttons['define_center'] = QAction(QIcon(center_icon), 'Define Center', parent=self)
        self.buttons['define_center'].setStatusTip('Define the center of FFT')
        self.buttons['define_center'].triggered.connect(lambda: self.define_center_dp(method='center'))
        self.toolbar.addAction(self.buttons['define_center'])
        center2_icon = os.path.join(self.wkdir, 'icons/dp_center2.png')
        self.buttons['define_center2'] = QAction(QIcon(center2_icon), 'Define Center with Two Points', parent=self)
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
                                    # resizable=False,
                                    maxBounds=QRectF(0, 0, x_range, y_range)
                                    )
        selector.addTranslateHandle([0.5, 0.5])  # Add a handle at the center for easier dragging

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
        OK_icon = os.path.join(self.wkdir, 'icons/OK.png')
        self.buttons['ok'] = QAction(QIcon(OK_icon), 'Confirm', parent=self)
        self.buttons['ok'].setStatusTip('Confirm Center Definition')
        self.buttons['ok'].setShortcut('Return')
        self.buttons['ok'].triggered.connect(self.accept_define_center)
        self.toolbar.addAction(self.buttons['ok'])
        cancel_icon = os.path.join(self.wkdir, 'icons/cancel.png')
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
                                    # resizable=False,
                                    maxBounds=QRectF(0, 0, x_range, y_range)
                                    )
            selector.addTranslateHandle([0.5, 0.5])  # Add a handle at the center for easier dragging
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
            selector1.addTranslateHandle([0.5, 0.5])  # Add a handle at the center for easier dragging
            selector2 = pg.CircleROI([x0_2, y0_2], radius=window_size,
                                                pen=pg.mkPen('r', width=3),
                                                movable=True,
                                                rotatable=False,
                                                resizable=False,
                                                maxBounds=QRectF(0, 0, x_range, y_range)
                                                )
            selector2.addTranslateHandle([0.5, 0.5])  # Add a handle at the center for easier dragging
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


         

    def clean_up(self, selector=False, buttons=False, modes=False, status_bar=False):
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
            for mode in self.mode_control.keys():
                if self.mode_control[mode]:
                    self.mode_control[mode] = False

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
        preview_fft = self.parent().preview_dict[preview_name]
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
        preview_fft = self.parent().preview_dict[preview_name]

        preview_fft.add_mask(pairs=False)
        preview_fft.canvas.selector[0].setPos((x0, y0))       
        preview_fft.add_mask(pairs=False)

        preview_fft.statusBar.showMessage('Drag the masks on noncolinear strong spots.')

        # Buttons
        ok_icon = os.path.join(self.wkdir, 'icons/OK.png')
        preview_fft.buttons['ok'] = QAction(QIcon(ok_icon), 'Run GPA', parent=preview_fft)
        preview_fft.buttons['ok'].setStatusTip('Run GPA')
        preview_fft.toolbar.addAction(preview_fft.buttons['ok'])
        preview_fft.buttons['ok'].triggered.connect(self.run_gpa)
        cancel_icon = os.path.join(self.wkdir, 'icons/cancel.png')
        preview_fft.buttons['cancel'] = QAction(QIcon(cancel_icon), 'Close', parent=preview_fft)
        preview_fft.buttons['cancel'].setStatusTip('Close'),
        preview_fft.toolbar.addAction(preview_fft.buttons['cancel'])
        preview_fft.buttons['cancel'].triggered.connect(self.stop_gpa)
        settings_icon = os.path.join(self.wkdir, 'icons/settings.png')
        preview_fft.buttons['settings'] = QAction(QIcon(settings_icon), 'GPA Settings', parent=preview_fft)
        preview_fft.buttons['settings'].setStatusTip('GPA Settings')
        preview_fft.toolbar.addAction(preview_fft.buttons['settings'])
        preview_fft.buttons['settings'].triggered.connect(self.gpa_settings)
        add_icon = os.path.join(self.wkdir, 'icons/plus.png')
        preview_fft.buttons['add_mask'] = QAction(QIcon(add_icon), 'Add Mask', parent=preview_fft)
        preview_fft.buttons['add_mask'].setStatusTip('Add Mask')
        preview_fft.toolbar.addAction(preview_fft.buttons['add_mask'])
        preview_fft.buttons['add_mask'].triggered.connect(lambda: preview_fft.add_mask(pairs=False))
        remove_icon = os.path.join(self.wkdir, 'icons/minus.png')
        preview_fft.buttons['remove_mask'] = QAction(QIcon(remove_icon), 'Remove Mask', parent=preview_fft)
        preview_fft.buttons['remove_mask'].setStatusTip('Remove Mask')
        preview_fft.toolbar.addAction(preview_fft.buttons['remove_mask'])
        preview_fft.buttons['remove_mask'].triggered.connect(preview_fft.remove_mask)
        refine_icon = os.path.join(self.wkdir, 'icons/measure_fft.png')
        preview_fft.buttons['refine_center'] = QAction(QIcon(refine_icon), 'Refine Center', parent=preview_fft)
        preview_fft.buttons['refine_center'].setStatusTip('Refine the mask positions using CoM.')
        preview_fft.toolbar.addAction(preview_fft.buttons['refine_center'])
        preview_fft.buttons['refine_center'].triggered.connect(self.refine_mask)

        

    def stop_gpa(self):
        preview_name = self.canvas.canvas_name + "_Live FFT"
        self.parent().preview_dict[preview_name].clean_up(selector=True, buttons=True, modes=True, status_bar=True)
        self.clean_up(selector=True, modes=True, status_bar=True)

    def run_gpa(self):
        img = self.get_img_dict_from_canvas()
        data = img['data']
        if data.shape[0] != data.shape[1]:
            data = filters.pad_to_square(data)
        
        # Get the center and radius of the masks
        preview_name_fft = self.canvas.canvas_name + "_Live FFT"
        preview_fft = self.parent().preview_dict[preview_name_fft]
        scale = preview_fft.scale
        g = []
        r_list = []
        for mask in preview_fft.canvas.selector:
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
        main_window = self.parent()
        # Display the GPA result
        exx, eyy, exy, oxy = result
        im_y, im_x = self.img_size[-2], self.img_size[-1]
        exx = exx[:im_y, :im_x]
        eyy = eyy[:im_y, :im_x]
        exy = exy[:im_y, :im_x]
        oxy = oxy[:im_y, :im_x]
        img = self.get_img_dict_from_canvas()
        cm = self.canvas.colormap['seismic']
        

        # Display the strain tensors
        exx_dict = copy.deepcopy(img)
        exx_dict['data'] = exx
        preview_name_exx = self.canvas.canvas_name + "_exx"
        self.plot_new_image(exx_dict, preview_name_exx)
        main_window.preview_dict[preview_name_exx].setWindowTitle('Epsilon xx')
        main_window.preview_dict[preview_name_exx].canvas.image_item.setLevels((self.vmin, self.vmax))
        main_window.preview_dict[preview_name_exx].canvas.attribute['vmin'] = self.vmin
        main_window.preview_dict[preview_name_exx].canvas.attribute['vmax'] = self.vmax
        main_window.preview_dict[preview_name_exx].canvas.image_item.setLookupTable(cm)
        main_window.preview_dict[preview_name_exx].canvas.attribute['cmap'] = 'seismic'
        main_window.preview_dict[preview_name_exx].canvas.toggle_colorbar(show=True)

        eyy_dict = copy.deepcopy(img)
        eyy_dict['data'] = eyy
        preview_name_eyy = self.canvas.canvas_name + "_eyy"
        self.plot_new_image(eyy_dict, preview_name_eyy)
        main_window.preview_dict[preview_name_eyy].setWindowTitle('Epsilon yy')
        main_window.preview_dict[preview_name_eyy].canvas.image_item.setLevels((self.vmin, self.vmax))
        main_window.preview_dict[preview_name_eyy].canvas.attribute['vmin'] = self.vmin
        main_window.preview_dict[preview_name_eyy].canvas.attribute['vmax'] = self.vmax
        main_window.preview_dict[preview_name_eyy].canvas.image_item.setLookupTable(cm)
        main_window.preview_dict[preview_name_eyy].canvas.attribute['cmap'] = 'seismic'
        main_window.preview_dict[preview_name_eyy].canvas.toggle_colorbar(show=True)

        exy_dict = copy.deepcopy(img)
        exy_dict['data'] = exy
        preview_name_exy = self.canvas.canvas_name + "_exy"
        self.plot_new_image(exy_dict, preview_name_exy)
        main_window.preview_dict[preview_name_exy].setWindowTitle('Epsilon xy')
        main_window.preview_dict[preview_name_exy].canvas.image_item.setLevels((self.vmin, self.vmax))
        main_window.preview_dict[preview_name_exy].canvas.attribute['vmin'] = self.vmin
        main_window.preview_dict[preview_name_exy].canvas.attribute['vmax'] = self.vmax
        main_window.preview_dict[preview_name_exy].canvas.image_item.setLookupTable(cm)
        main_window.preview_dict[preview_name_exy].canvas.attribute['cmap'] = 'seismic'
        main_window.preview_dict[preview_name_exy].canvas.toggle_colorbar(show=True)

        oxy_dict = copy.deepcopy(img)
        oxy_dict['data'] = oxy
        preview_name_oxy = self.canvas.canvas_name + "_oxy"
        self.plot_new_image(oxy_dict, preview_name_oxy)
        main_window.preview_dict[preview_name_oxy].setWindowTitle('Omega')
        main_window.preview_dict[preview_name_oxy].canvas.image_item.setLevels((self.vmin, self.vmax))
        main_window.preview_dict[preview_name_oxy].canvas.attribute['vmin'] = self.vmin
        main_window.preview_dict[preview_name_oxy].canvas.attribute['vmax'] = self.vmax
        main_window.preview_dict[preview_name_oxy].canvas.image_item.setLookupTable(cm)
        main_window.preview_dict[preview_name_oxy].canvas.attribute['cmap'] = 'seismic'
        main_window.preview_dict[preview_name_oxy].canvas.toggle_colorbar(show=True)

    def gpa_settings(self):
        # Open a dialog to take settings
        preview_name = self.canvas.canvas_name + '_Live FFT'
        r = max([mask.size()[0] / 2 for mask in self.parent().preview_dict[preview_name].canvas.selector])
        r_pix = int(r / self.parent().preview_dict[preview_name].scale)
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
        for mask in self.parent().preview_dict[preview_name].canvas.selector:
            mask.setSize(self.r * 2 * self.parent().preview_dict[preview_name].scale)


    def refine_mask(self):
        preview_name = self.canvas.canvas_name + '_Live FFT'
        preview_fft = self.parent().preview_dict[preview_name]
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

            self.plot_new_image(img, preview_name, parent=self.parent(), metadata=f'Rotated the entire stack of {title} by {ang} degrees counterclockwise.', position='center right')
            
            print(f'Rotated the entire stack of {title} by {ang} degrees counterclockwise.')
            self.position_window('center left')


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
        self.plot_new_image(img, preview_name, parent=self.parent(), metadata=metadata, position='center right')
        
        print(f'Flipped the entire stack of {title} horizontally.')
        
        self.position_window('center left')
        
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
        self.plot_new_image(img, preview_name, parent=self.parent(), metadata=metadata, position='center right')
        
        print(f'Flipped the entire stack of {title} vertically.')
        self.position_window('center left')

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
            self.plot_new_image(img, preview_name, parent=self.parent(), metadata=metadata, position='center right')
            
            print(f'Resampled {title} by a factor of {rescale_factor}.')
            self.position_window('center left')

    def reslice_stack(self):
        self.clean_up(selector=True, buttons=True, modes=True, status_bar=True)  # Clean up any existing modes or selectors
        self.statusBar.showMessage("Drag the line to reslice.")
        
        # Buttons for finish
        OK_icon = os.path.join(self.wkdir, 'icons/OK.png')
        self.buttons['ok'] = QAction(QIcon(OK_icon), 'OK', parent=self)
        self.buttons['ok'].setStatusTip('Reslice from the line')
        self.buttons['ok'].setShortcut('Esc')
        self.buttons['ok'].triggered.connect(self.reslice_from_line)
        self.toolbar.addAction(self.buttons['ok'])

        cancel_icon = os.path.join(self.wkdir, 'icons/cancel.png')
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
            self.plot_new_image(img, preview_name, parent=self.parent(), metadata=metadata, position='center right')
            self.position_window('center left')
            print(metadata)

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
        self.plot_new_image(sorted_img, preview_name, parent=self.parent(), metadata=metadata, position='center right')

        print(metadata)
        self.position_window('center left')
        
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
            self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata, position='center right'))
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
        self.worker.result.connect(lambda result: self.plot_new_image(result, preview_name, parent=self.parent(), metadata=metadata), position='center right')
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
        self.plot_new_image(integrated_img, preview_name, parent=self.parent(), metadata=metadata, position='center right')
        
        print(f'Stack of {title} has been integrated.')
        self.position_window('center left')
        
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
            f_name, file_type = getFileNameType(file_path)
            output_dir = getDirectory(file_path)
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
    def __init__(self, img, source_img, parent=None):
        # img is the image dictionary, NOT FFT. FFT will be calculated in create_img()
        super().__init__(img, parent)
        self.canvas.data_type = 'FFT'
        self.source_img = source_img  # Store the original canvas name


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
        mask_icon = os.path.join(self.wkdir, 'icons/masks.png')
        mask_action = QAction(QIcon(mask_icon), 'Mask and iFFT', self)
        mask_action.setStatusTip('Add masks to FFT spots and perform inverse FFT.')
        mask_action.triggered.connect(self.mask)
        self.toolbar.insertAction(toolbar.actions()[11], mask_action)

        # Store the original image scale in real space
        self.real_scale = self.scale
        
        self.calculate_fft()
        self.set_scalebar_units()
        
        # Update the colormap in attribute
        self.canvas.attribute['cmap'] = self.canvas.attribute['fft_cmap']
        self.canvas.create_img(cmap=self.canvas.attribute['cmap'], 
                               pvmin=self.attribute['fft_pvmin'], 
                               pvmax=self.attribute['fft_pvmax'])

        # Update data type in the image dictionary
        self.canvas.data['metadata']['TemCompanion']['Data Type'] = 'FFT'
        self.canvas.data['metadata']['TemCompanion']['Image Size (pixels)'] = f"{self.canvas.img_size[-1]} x {self.canvas.img_size[-2]}"
        self.canvas.data['metadata']['TemCompanion']['Calibrated Image Size'] = f"{self.canvas.img_size[-1] * self.scale:.4g} x {self.canvas.img_size[-2] * self.scale:.4g} {self.units}"
        self.canvas.data['metadata']['TemCompanion']['Pixel Calibration'] = f"{self.scale:.4g} {self.units}"
        self.process = copy.deepcopy(img['metadata']['TemCompanion'])

    def closeEvent(self, event):  
        source_canvas = find_img_by_title(self.parent().preview_dict, self.source_img)     
        if source_canvas is not None and source_canvas.mode_control['Live_FFT']:
            source_canvas.stop_live_fft()
        self.parent().preview_dict.pop(self.canvas.canvas_name, None)

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
        ok_icon = os.path.join(self.wkdir, 'icons/ok.png')
        self.buttons['ok'] = QAction(QIcon(ok_icon), 'Finish', self)
        self.buttons['ok'].setShortcut('Esc')
        self.buttons['ok'].setStatusTip('Finish iFFT filtering.')
        self.buttons['ok'].triggered.connect(self.stop_mask_ifft)
        self.toolbar.addAction(self.buttons['ok'])

        add_icon = os.path.join(self.wkdir, 'icons/plus.png')
        self.buttons['add'] = QAction(QIcon(add_icon), 'Add Mask', self)
        self.buttons['add'].setStatusTip('Add new masks.')
        self.buttons['add'].triggered.connect(lambda: self.add_mask())
        self.toolbar.addAction(self.buttons['add'])   

        remove_icon = os.path.join(self.wkdir, 'icons/minus.png')
        self.buttons['remove'] = QAction(QIcon(remove_icon), 'Remove Mask', self)
        self.buttons['remove'].setStatusTip('Remove masks.')
        self.buttons['remove'].triggered.connect(self.remove_mask)
        self.toolbar.addAction(self.buttons['remove'])

        self.add_mask()

        # Create a new plot to show live ifft
        title = self.canvas.canvas_name
        preview_name = self.canvas.canvas_name + '_iFFT'
        live_ifft = self.get_img_dict_from_canvas()
        live_ifft['metadata']['TemCompanion']['Data Type'] = 'Image'
        live_ifft_data = self.ifft_with_masks(live_ifft['data'])
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
        live_ifft['metadata']['TemCompanion']['Pixel Calibration'] = f"{img_scale:.4g} {img_units}"
        live_ifft['metadata']['TemCompanion']['Image Size (pixels)'] = f"{live_ifft['data'].shape[1]} x {live_ifft['data'].shape[0]}"
        live_ifft['metadata']['TemCompanion']['Calibrated Image Size'] = f"{live_ifft['data'].shape[1] * img_scale:.4g} x {live_ifft['data'].shape[0] * img_scale:.4g} {img_units}"
        


        metadata = f'iFFT with masks from {title}'
        self.plot_new_image(live_ifft, preview_name, parent=self.parent(), metadata=metadata, position='center right')
        self.position_window('center left')

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
        mask0.addTranslateHandle([0.5, 0.5])  # Add a handle at the center for easier movement
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
            mask1.addTranslateHandle([0.5, 0.5])  # Add a handle at the center for easier movement
            # Link mask1 to mask0
            mask1.id = mask0_id

            self.canvas.selector.append(mask1)
            self.canvas.viewbox.addItem(mask1)
            mask1.sigHoverEvent.connect(self._make_active_selector)  

            # Connect the signals for synchronized movement and live ifft update
            mask0.sigRegionChangeFinished.connect(self.update_mask_ifft)    
            mask0.sigRegionChanged.connect(self.update_paired_mask)   
            mask1.sigRegionChangeFinished.connect(self.update_mask_ifft)
            mask1.sigRegionChanged.connect(self.update_paired_mask)

    def update_paired_mask(self, mask):
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
        paired_mask.sigRegionChanged.disconnect(self.update_paired_mask)
        paired_mask.sigRegionChangeFinished.disconnect(self.update_mask_ifft)
        paired_mask.setPos([x1, y1], update=False, finish=False)
        paired_mask.setSize(d0)
        paired_mask.sigRegionChanged.connect(self.update_paired_mask)
        paired_mask.sigRegionChangeFinished.connect(self.update_mask_ifft)

    def update_mask_ifft(self):
        # Update the live ifft image
        live_ifft_name = self.canvas.canvas_name + '_iFFT'
        live_ifft_data = self.ifft_with_masks(self.canvas.data['fft'])
        if live_ifft_name in self.parent().preview_dict:
            live_ifft_canvas = self.parent().preview_dict[live_ifft_name]
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

    def ifft_with_masks(self, fft_data):
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
    def __init__(self, x, y, source_img=None, parent=None):
        # data is a 2D array with x and y values, x in the first row, y in the second row
        # source_img is the original image canvas name
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.resize(600, 400)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.wkdir = self.parent().wkdir
        self.x = x
        self.y = y
        self.source_img = source_img
        self.title = None
        self.xlabel = None
        self.ylabel = None
        self.canvas = QWidget()
        self.canvas.data_type = 'Spectrum' # For future use
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

        home_icon = os.path.join(self.wkdir, 'icons/home.png')
        home_action = QAction(QIcon(home_icon), "Home", self)
        home_action.setStatusTip("Reset to original view")
        home_action.triggered.connect(self.custom_auto_range)
        self.toolbar.addAction(home_action)

        save_icon = os.path.join(self.wkdir, 'icons/save.png')
        save_action = QAction(QIcon(save_icon), "Save", self)
        save_action.setStatusTip("Save plot as image or CSV")
        save_action.triggered.connect(self.save_plot)
        self.toolbar.addAction(save_action)

        copy_icon = os.path.join(self.wkdir, 'icons/copy.png')
        copy_action = QAction(QIcon(copy_icon), "Copy", self)
        copy_action.setStatusTip("Copy plot to clipboard")
        copy_action.triggered.connect(self.copy_plot)
        self.toolbar.addAction(copy_action)

        settings_icon = os.path.join(self.wkdir, 'icons/settings.png')
        settings_action = QAction(QIcon(settings_icon), "Settings", self)
        settings_action.setStatusTip("Plot settings")
        settings_action.triggered.connect(self.plotsetting)
        self.toolbar.addAction(settings_action)

        self.toolbar.addSeparator()

        h_measure_icon = os.path.join(self.wkdir, 'icons/h_measure.png')
        h_measure_action = QAction(QIcon(h_measure_icon), "Measure horizontal", self)
        h_measure_action.setStatusTip("Measure horizontal distance")
        h_measure_action.triggered.connect(lambda: self.measure('vertical'))
        self.toolbar.addAction(h_measure_action)

        v_measure_icon = os.path.join(self.wkdir, 'icons/v_measure.png')
        v_measure_action = QAction(QIcon(v_measure_icon), "Measure vertical", self)
        v_measure_action.setStatusTip("Measure vertical distance")
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
        if self.source_img is not None:
            source_canvas = find_img_by_title(self.parent().preview_dict, self.source_img)     
            if source_canvas is not None and source_canvas.mode_control['lineprofile']:
                source_canvas.stop_line_profile()
        
        self.parent().preview_dict.pop(self.canvas.canvas_name, None)

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
            self.file_type = getFileNameType(self.file_path)[1]
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
        plots = list(self.parent().preview_dict.keys())
        for plot in plots:
            try:
                self.parent().preview_dict[plot].close()
            except:
                pass

    def measure(self, orientation='horizontal'):
        # orientation: 'horizontal' or 'vertical'
        self.cleanup()
        # Finish button
        ok_icon = os.path.join(self.wkdir, 'icons/ok.png')
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
        dialog.position_window('next to parent')



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