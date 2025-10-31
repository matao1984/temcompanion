from PyQt5 import QtCore, QtWidgets

from PyQt5.QtWidgets import (QApplication, QMainWindow, QListView, QVBoxLayout, 
                             QWidget, QPushButton, QMessageBox, QFileDialog, 
                             QDialog, QAction, QHBoxLayout, QLineEdit, QLabel, 
                             QComboBox, QInputDialog, QCheckBox, QGroupBox, 
                             QFormLayout, QDialogButtonBox,  QTreeWidget, QTreeWidgetItem,
                             QSlider, QStatusBar, QMenu, QTextEdit, QSizePolicy, QRadioButton,
                             QListWidget, QListWidgetItem, QButtonGroup, QProgressBar, QToolBar,
                             QTextBrowser, QDockWidget
                             )
from PyQt5.QtCore import Qt, QStringListModel, QObject, pyqtSignal, QThread, QRect, QRectF, QSize, QTimer
from PyQt5.QtGui import QImage, QPixmap, QIcon, QDropEvent, QDragEnterEvent, QFont

import pyqtgraph as pg
import pyqtgraph.exporters
import numpy as np
import copy
import importlib.resources
import pickle
import json

# Internal modules
from .functions import gamma_correct_lut, find_img_by_title
from . import filters
# from .main import UI_TemCompanion
from TemCompanion.DPC import reconstruct_iDPC, reconstruct_dDPC, find_rotation_ang_max_contrast, find_rotation_ang_min_curl


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
        self.setFocusPolicy(Qt.StrongFocus)
        self.data = data
        self.img_size = self.data['data'].shape

        if len(self.img_size) == 2:
            self.data_type = 'Image'
        elif len(self.img_size) == 3:
            self.data_type = 'Image Stack'
        else:
            QMessageBox.warning(self, 'Open File', 'Data dimension not supported!')
            return
        
        # Load colormap
        with importlib.resources.files('TemCompanion').joinpath('colormaps.pkl').open('rb') as f:
            self.colormap = pickle.load(f)
        
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
        self.timer = QTimer()
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
        
        lut = self.colormap[cmap]
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
                    lut = self.colormap[self.attribute['cmap']]
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



#========= Image settings dialog =============================
class CustomSettingsDialog(QDialog):
    def __init__(self, image_item, parent):
        # parent should be the PlotCanvas object
        super().__init__(parent) 
        self.image_item = image_item
        self.img_data = self.parent().canvas.img_data 

        self.setWindowTitle("Image Settings")        
        self.attribute = self.parent().canvas.attribute
        self.colormap = self.parent().canvas.colormap

        
        
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
        lut = self.colormap[cmap_name]
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
        lut = self.colormap[self.cmap_name]
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

            

#============ Filter settings dialog for plot canvas ===========================
class FilterSettingDialog(QDialog):
    # Same as FilterSettingBatchConvert but without apply to check boxes
    def __init__(self, parameters, parent):
        super().__init__(parent)
        self.setWindowTitle("Filter Settings")        
        layout = QVBoxLayout()
        
        default_values = parameters
        self.parameters = {}

        # Wiener Filter Section      
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
        layout.addWidget(self.wiener_group)

        # ABS Filter Section
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
        layout.addWidget(self.absf_group)

        # Non-Linear Filter Section
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
        layout.addWidget(self.nl_group)
        
        # Butterworth filter Section
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
        layout.addWidget(self.bw_group)
        
        # Gaussian filter Section
        self.gaussian_group = QGroupBox()
        form_layout = QFormLayout()
        self.cutoff_gaussian = QLabel('Gaussian cutoff')
        self.cutoff_gaussian.setToolTip('Fraction of radius in reciprocal space from where the taper of the lowpass starts.')
        self.cutoff_gaussian_input = QLineEdit()
        self.cutoff_gaussian_input.setText(default_values['GS-cutoff'])
        form_layout.addRow(self.cutoff_gaussian, self.cutoff_gaussian_input)
        self.gaussian_group.setLayout(form_layout)
        self.gaussian_group.setEnabled(True)
        layout.addWidget(self.gaussian_group)

        # Dialog Buttons (OK and Cancel)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.handle_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
    
    def handle_ok(self):
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

#============ Define a dialogue for filter settings for batch convert ===========================
class FilterSettingBatchConvert(QDialog):
    def __init__(self, apply_wf, apply_absf, apply_nl, apply_bw, apply_gaussian, parameters, parent=None):
        super().__init__(parent)
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
        self.wiener_group.setEnabled(apply_wf)
        self.wiener_check.stateChanged.connect(lambda: self.wiener_group.setEnabled(self.wiener_check.isChecked()))
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
        self.absf_group.setEnabled(apply_absf)
        self.absf_check.stateChanged.connect(lambda: self.absf_group.setEnabled(self.absf_check.isChecked()))
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
        self.nl_group.setEnabled(apply_nl)
        self.nl_check.stateChanged.connect(lambda: self.nl_group.setEnabled(self.nl_check.isChecked()))
        layout.addWidget(self.nl_check)
        layout.addWidget(self.nl_group)
        
        # Butterworth filter 
        self.bw_check = QCheckBox("Apply Butterworth Filter")
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
        self.bw_group.setEnabled(apply_bw)
        self.bw_check.stateChanged.connect(lambda: self.bw_group.setEnabled(self.bw_check.isChecked()))
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
        self.gaussian_group.setEnabled(apply_gaussian)
        self.gaussian_check.stateChanged.connect(lambda: self.gaussian_group.setEnabled(self.gaussian_check.isChecked()))
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

            print(f'Exported metadata to {self.file_path} as {self.selected_type}.')

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
        # unit = self.img_dict['axes'][1]['units']
        calibrated_x = radial_x * scale
        self.x_data = calibrated_x
        self.y_data = radial_y

        # # Plot the radial profile
        # preview_name = self.parent().windowTitle() + f'_radial_profile from {self.center}'
        # x_label = f'Radial Distance ({unit})'
        # y_label = 'Integrated Intensity (Counts)'
        # plot = PlotCanvasSpectrum(calibrated_x, radial_y, parent=self.parent())
        # plot.create_plot(xlabel=x_label, ylabel=y_label, title=preview_name)
        # plot.canvas.canvas_name = preview_name
        # UI_TemCompanion.preview_dict[preview_name] = plot
        # UI_TemCompanion.preview_dict[preview_name].show()

        # print(f'Performed radial integration on {self.parent().windowTitle()} from the center: {self.center}.')



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
    def __init__(self, img_list,parent=None):
        super().__init__(parent)
        self.setWindowTitle('Simple Math')
        layout = QVBoxLayout()
        layout1 = QHBoxLayout()
        im1_label = QLabel('Signal 1:')
        self.im1_select = QComboBox()
        # img_list = [canvas.canvas.canvas_name for canvas in UI_TemCompanion.preview_dict.values()]
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
    def __init__(self,img_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Reconstruct DPC')
        self.img_list = img_list
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
            combobox.addItems(self.img_list)
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
        self.imX.addItems(self.img_list)
        imY_label = QLabel('DPCy:')
        self.imY = QComboBox() 
        self.imY.addItems(self.img_list)
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
            A = copy.deepcopy(find_img_by_title(self.img_list, imA).canvas.data)
            B = copy.deepcopy(find_img_by_title(self.img_list, imB).canvas.data)
            C = copy.deepcopy(find_img_by_title(self.img_list, imC).canvas.data)
            D = copy.deepcopy(find_img_by_title(self.img_list, imD).canvas.data)
            if A['data'].shape == B['data'].shape and B['data'].shape == C['data'].shape and C['data'].shape == D['data'].shape:
                DPCx = A['data'] - C['data']
                DPCy = B['data'] - D['data']
            else:
                QMessageBox.warning(self,'Error in DPC reconstruction!', 'Sizes of the input images do not match!')
                return None, None, None
        else:
            imX = self.imX.currentText()
            imY = self.imY.currentText()
            A = copy.deepcopy(find_img_by_title(self.img_list, imX).canvas.data)
            B = copy.deepcopy(find_img_by_title(self.img_list, imY).canvas.data)
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
            A = find_img_by_title(self.img_list, imA).get_img_dict_from_canvas()
            B = find_img_by_title(self.img_list, imB).get_img_dict_from_canvas()
            C = find_img_by_title(self.img_list, imC).get_img_dict_from_canvas()
            D = find_img_by_title(self.img_list, imD).get_img_dict_from_canvas()
            if A['data'].shape == B['data'].shape and B['data'].shape == C['data'].shape and C['data'].shape == D['data'].shape:
                DPCx = A['data'] - C['data']
                DPCy = B['data'] - D['data']
            else:
                QMessageBox.warning(self,'Error in DPC reconstruction!', 'Sizes of the input images do not match!')
                return None, None, None
        else:
            imX = self.imX.currentText()
            imY = self.imY.currentText()
            A = find_img_by_title(self.img_list, imX).get_img_dict_from_canvas()
            B = find_img_by_title(self.img_list, imY).get_img_dict_from_canvas()
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
        print(text)
        QMessageBox.information(self, 'Rotation angle', text)
        
    def guess_rotation_min_curl(self):
        _, DPCx, DPCy = self.prepare_current_images()
        if DPCx is None:
            return
        ang = find_rotation_ang_min_curl(DPCx, DPCy)
        text = f'The possible rotation angle that gives the minimum curl is {ang} deg.'
        print(text)
        QMessageBox.information(self, 'Rotation angle', text)

    def reconstruct_iDPC(self):
        A, DPCx, DPCy = self.prepare_images()
        if DPCx is None:
            return
        
        iDPC_img = copy.deepcopy(A)
        iDPC_img['data'] = reconstruct_iDPC(DPCx, DPCy, rotation=float(self.rot.text()), cutoff=float(self.hp_cutoff.text()))
        preview_name = self.parent().canvas.canvas_name.split(':')[0] + '_iDPC'
        if self.from4_img.isChecked():
            metadata = f'Reconstructed iDPC from {self.imA.currentText()}, {self.imB.currentText()}, {self.imC.currentText()}, and {self.imD.currentText()} by a rotation angle of {self.rot.text()} and high pass filter cutoff of {self.hp_cutoff.text()}.'
        else:
            metadata = f'Reconstructed iDPC from {self.imX.currentText()} and {self.imY.currentText()} by a rotation angle of {self.rot.text()} and high pass filter cutoff of {self.hp_cutoff.text()}.'
        self.parent().plot_new_image(iDPC_img, preview_name, metadata=metadata, position='center')
        print(metadata)
        
    
    def reconstruct_dDPC(self):
        A, DPCx, DPCy = self.prepare_images()
        if DPCx is None:
            return
            
        dDPC_img = copy.deepcopy(A)
        dDPC_img['data'] = reconstruct_dDPC(DPCx, DPCy, rotation=float(self.rot.text()))
        preview_name = self.parent().canvas.canvas_name.split(':')[0] + '_dDPC'
        if self.from4_img.isChecked():
            metadata = f'Reconstructed dDPC from {self.imA.currentText()}, {self.imB.currentText()}, {self.imC.currentText()}, and {self.imD.currentText()} by a rotation angle of {self.rot.text()} and high pass filter cutoff of {self.hp_cutoff.text()}.'
        else:
            metadata = f'Reconstructed dDPC from {self.imX.currentText()} and {self.imY.currentText()} by a rotation angle of {self.rot.text()} and high pass filter cutoff of {self.hp_cutoff.text()}.'
        self.parent().plot_new_image(dDPC_img, preview_name, metadata=metadata, position='center')
        print(metadata)
        
        
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