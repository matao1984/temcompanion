from PyQt5.QtWidgets import QAction, QToolBar, QFileDialog
from PyQt5.QtCore import Qt, QRectF, QSize, QPointF, pyqtSignal
from PyQt5.QtGui import QIcon

import pyqtgraph as pg

import numpy as np
import os
import pickle
from rsciio.usid import file_writer as usid_writer

from .canvas import PlotCanvas, Worker
from .GPA import create_mask
from .DPC import reconstruct_iDPC, reconstruct_dDPC
from .functions import getDirectory, getFileNameType, save_as_tif16, save_with_pil


class DiffractionCanvas(PlotCanvas):
    def __init__(self, img4d, master_handle, parent=None):
        self.img4d = img4d  # Store the image dict with 4D data
        # Reformat the 4D image dict to fit the PlotCanvas class
        self.R_size = img4d["data"].shape[0], img4d["data"].shape[1]
        self.Q_size = img4d["data"].shape[2], img4d["data"].shape[3]
        q_img_data = img4d["data"][self.R_size[0] // 2, self.R_size[1] // 2, :, :]
        q_img = {
            "data": q_img_data,
            "metadata": img4d["metadata"],
            "axes": [img4d["axes"][2], img4d["axes"][3]],
        }
        if "original_metadata" in img4d.keys():
            q_img["original_metadata"] = img4d["original_metadata"]
        super().__init__(q_img, parent=parent)
        self.pvmin = self.attribute.get("4dstem_pvmin", 0.1)
        self.pvmax = self.attribute.get("4dstem_pvmax", 99)
        self.canvas.update_img(
            q_img_data, pvmin=self.pvmin, pvmax=self.pvmax
        )  # Update the image with the specified pvmin and pvmax for 4D-STEM diffraction
        # Store the PlotCanvas4D object as the master handle to allow communication between the diffraction canvas and the virtual image canvas
        self.master_handle = master_handle
        self.setWindowTitle("Diffraction")

    def closeEvent(self, event):
        self.parent().preview_dict.pop(self.canvas.canvas_name, None)
        R_canvas_name = self.master_handle.R_canvas.canvas.canvas_name
        if R_canvas_name in self.parent().preview_dict:
            self.parent().preview_dict[
                R_canvas_name
            ].close()  # Close the virtual image canvas if it's still open
            self.parent().preview_dict.pop(R_canvas_name, None)
        self.master_handle = None  # Remove reference to master handle to allow garbage collection of the virtual image canvas if it's still open

    def create_menubar(self):
        menubar = self.menuBar()
        # menubar.clear()  # Clear existing menu items if any

        # File menu and actions
        file_menu = menubar.addMenu("&File")
        save_action = QAction("&Save as", self)
        save_action.setShortcut("ctrl+s")
        save_action.triggered.connect(self.save_figure)
        file_menu.addAction(save_action)
        copy_action = QAction("&Copy Image to Clipboard", self)
        copy_action.setShortcut("ctrl+alt+c")
        copy_action.triggered.connect(self.copy_img)
        file_menu.addAction(copy_action)
        copy_img_action = QAction("&New Image from Display", self)
        copy_img_action.triggered.connect(self.new_img_from_display)
        file_menu.addAction(copy_img_action)
        imagesetting_action = QAction("&Image Settings", self)
        imagesetting_action.setShortcut("ctrl+o")
        imagesetting_action.triggered.connect(self.image_settings)
        file_menu.addAction(imagesetting_action)
        close_action = QAction("&Close", self)
        close_action.setShortcut("ctrl+x")
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)
        close_all_action = QAction("&Close all", self)
        close_all_action.setShortcut("ctrl+shift+x")
        close_all_action.triggered.connect(self.close_all)
        file_menu.addAction(close_all_action)

        # Edit menu and actions
        edit_menu = menubar.addMenu("&Process")
        crop_action = QAction("&Crop", self)
        crop_action.setShortcut("ctrl+shift+c")
        crop_action.triggered.connect(self.crop)
        edit_menu.addAction(crop_action)

        fliplr_action = QAction("Flip horizontal", self)
        fliplr_action.triggered.connect(self.flip_horizontal)
        edit_menu.addAction(fliplr_action)
        flipud_action = QAction("Flip vertical", self)
        flipud_action.triggered.connect(self.flip_vertical)
        edit_menu.addAction(flipud_action)

        # Analyze menu and actions
        analyze_menu = menubar.addMenu("&Analyze")
        setscale_action = QAction("Set Scale", self)
        setscale_action.triggered.connect(self.setscale)
        analyze_menu.addAction(setscale_action)
        measure_action = QAction("Measure", self)
        measure_action.triggered.connect(self.measure)
        analyze_menu.addAction(measure_action)
        measure_angle_action = QAction("Measure Angle", self)
        measure_angle_action.triggered.connect(self.measure_angle)
        analyze_menu.addAction(measure_angle_action)
        measure_fft_action = QAction("Measure Diffraction/FFT", self)
        measure_fft_action.triggered.connect(self.measure_fft)
        analyze_menu.addAction(measure_fft_action)
        lineprofile_action = QAction("Line Profile", self)
        lineprofile_action.triggered.connect(self.lineprofile)
        analyze_menu.addAction(lineprofile_action)
        radial_integration_action = QAction("Radial Integration", self)
        radial_integration_action.triggered.connect(self.radial_integration)
        analyze_menu.addAction(radial_integration_action)

        # Detector menu and actions
        detector_menu = menubar.addMenu("&Detector")
        point_action = QAction("Point", self)
        point_action.setShortcut("ctrl+shift+p")
        point_action.triggered.connect(self.point_detector)
        detector_menu.addAction(point_action)

        circle_action = QAction("Circle", self)
        circle_action.setShortcut("ctrl+shift+o")
        circle_action.triggered.connect(self.circle_detector)
        detector_menu.addAction(circle_action)

        annular_action = QAction("Annular", self)
        annular_action.setShortcut("ctrl+shift+a")
        annular_action.triggered.connect(self.annular_detector)
        detector_menu.addAction(annular_action)

        dpc_menu = detector_menu.addMenu("DPC")
        dpc_action = QAction("DPC", self)
        dpc_action.triggered.connect(self.dpc)
        dpc_menu.addAction(dpc_action)
        idpc_action = QAction("iDPC", self)
        idpc_action.triggered.connect(self.idpc)
        dpc_menu.addAction(idpc_action)
        ddpc_action = QAction("dDPC", self)
        ddpc_action.triggered.connect(self.ddpc)
        dpc_menu.addAction(ddpc_action)

        com_menu = detector_menu.addMenu("CoM")
        com_action = QAction("CoM", self)
        com_action.triggered.connect(self.com)
        com_menu.addAction(com_action)
        icom_action = QAction("iCoM", self)
        icom_action.triggered.connect(self.icom)
        com_menu.addAction(icom_action)
        dcom_action = QAction("dCoM", self)
        dcom_action.triggered.connect(self.dcom)
        com_menu.addAction(dcom_action)

        # Info menu
        info_menu = menubar.addMenu("&Info")
        info_action = QAction("&Image Info", self)
        info_action.setShortcut("ctrl+i")
        info_action.triggered.connect(self.show_info)
        info_menu.addAction(info_action)
        about_action = QAction("About", self)
        about_action.triggered.connect(self.parent().show_about)
        info_menu.addAction(about_action)

        self.menubar = menubar

    def create_toolbar(self):
        # self.toolbar.clear()  # Close existing toolbar if any

        self.toolbar = QToolBar("Diffraction Toolbar")
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolbar.layout().setSpacing(0)  # Sets spacing between items
        self.addToolBar(self.toolbar)

        # Add actions to the toolbar
        home_icon = os.path.join(self.wkdir, "icons/home.png")
        home_action = QAction(QIcon(home_icon), "Home", self)
        home_action.setStatusTip("Auto scale to fit the window")
        home_action.triggered.connect(self.canvas.custom_auto_range)
        self.toolbar.addAction(home_action)

        self.toolbar.addSeparator()

        save_icon = os.path.join(self.wkdir, "icons/save.png")
        save_action = QAction(QIcon(save_icon), "Save", self)
        save_action.setStatusTip("Save the current image")
        save_action.triggered.connect(self.save_figure)
        self.toolbar.addAction(save_action)

        copy_icon = os.path.join(self.wkdir, "icons/copy.png")
        copy_action = QAction(QIcon(copy_icon), "Copy", self)
        copy_action.setStatusTip("Copy the current image")
        copy_action.triggered.connect(self.copy_img)
        self.toolbar.addAction(copy_action)

        setting_icon = os.path.join(self.wkdir, "icons/settings.png")
        setting_action = QAction(QIcon(setting_icon), "Settings", self)
        setting_action.setStatusTip("Open settings")
        setting_action.triggered.connect(self.image_settings)
        self.toolbar.addAction(setting_action)

        self.toolbar.addSeparator()

        crop_icon = os.path.join(self.wkdir, "icons/crop.png")
        crop_action = QAction(QIcon(crop_icon), "Crop", self)
        crop_action.setStatusTip("Crop the diffraction patterns")
        crop_action.triggered.connect(self.crop)
        self.toolbar.addAction(crop_action)

        measure_icon = os.path.join(self.wkdir, "icons/measure.png")
        measure_action = QAction(QIcon(measure_icon), "Measure", self)
        measure_action.setStatusTip("Measure distance and angle")
        measure_action.triggered.connect(self.measure)
        self.toolbar.addAction(measure_action)

        measure_angle_icon = os.path.join(self.wkdir, "icons/angle.png")
        measure_angle_action = QAction(QIcon(measure_angle_icon), "Measure Angle", self)
        measure_angle_action.setStatusTip("Measure angle from three points")
        measure_angle_action.triggered.connect(self.measure_angle)
        self.toolbar.addAction(measure_angle_action)

        measurefft_icon = os.path.join(self.wkdir, "icons/measure_fft.png")
        measurefft_action = QAction(QIcon(measurefft_icon), "Measure FFT", self)
        measurefft_action.setStatusTip("Measure distance and angle in Diffraction/FFT")
        measurefft_action.triggered.connect(self.measure_fft)
        self.toolbar.addAction(measurefft_action)

        lineprofile_icon = os.path.join(self.wkdir, "icons/lineprofile.png")
        lineprofile_action = QAction(QIcon(lineprofile_icon), "Line Profile", self)
        lineprofile_action.setStatusTip("Extract line profile")
        lineprofile_action.triggered.connect(self.lineprofile)
        self.toolbar.addAction(lineprofile_action)

        self.toolbar.addSeparator()

        point_detector_icon = os.path.join(self.wkdir, "icons/point_detector.png")
        point_detector_action = QAction(
            QIcon(point_detector_icon), "Point Detector", self
        )
        point_detector_action.setStatusTip("Add a point detector for the virtual image")
        point_detector_action.triggered.connect(self.point_detector)
        self.toolbar.addAction(point_detector_action)

        circle_detector_icon = os.path.join(self.wkdir, "icons/circle_detector.png")
        circle_detector_action = QAction(
            QIcon(circle_detector_icon), "Circle Detector", self
        )
        circle_detector_action.setStatusTip(
            "Add a circle detector for the virtual image"
        )
        circle_detector_action.triggered.connect(self.circle_detector)
        self.toolbar.addAction(circle_detector_action)

        annular_detector_icon = os.path.join(self.wkdir, "icons/annular_detector.png")
        annular_detector_action = QAction(
            QIcon(annular_detector_icon), "Annular Detector", self
        )
        annular_detector_action.setStatusTip(
            "Add an annular detector for the virtual image"
        )
        annular_detector_action.triggered.connect(self.annular_detector)
        self.toolbar.addAction(annular_detector_action)

        self.toolbar.addSeparator()

        info_icon = os.path.join(self.wkdir, "icons/info.png")
        info_action = QAction(QIcon(info_icon), "Info", self)
        info_action.setStatusTip("Show image info")
        info_action.triggered.connect(self.show_info)
        self.toolbar.addAction(info_action)

    def save_figure(self):
        options = QFileDialog.Options()
        # Remember and reuse last selected save filter (session only)
        last_save_filter = None
        try:
            last_save_filter = self.parent().settings.get(
                "lastSaveFilter", "16-bit TIFF Files (*.tiff)"
            )
        except Exception:
            last_save_filter = "16-bit TIFF Files (*.tiff)"
        save_filters = (
            "16-bit TIFF Files (*.tiff);;"
            "32-bit TIFF Files (*.tiff);;"
            "8-bit Grayscale TIFF Files (*.tiff);;"
            "Grayscale PNG Files (*.png);;"
            "Grayscale JPEG Files (*.jpg);;"
            "Color TIFF Files (*.tiff);;"
            "Color PNG Files (*.png);;"
            "Color JPEG Files (*.jpg);;"
            "USID (*.hdf5);;"
            "Pickle Dictionary Files (*.pkl)"
        )
        self.file_path, self.selected_type = QFileDialog.getSaveFileName(
            self.parent(),
            "Save Figure",
            "",
            save_filters,
            last_save_filter,
            options=options,
        )
        if self.file_path:
            # Update session-only selected filter for next time
            if self.selected_type:
                try:
                    self.parent().settings["lastSaveFilter"] = self.selected_type
                except Exception:
                    pass
            # Implement custom save logic here

            # Extract the chosen file format
            self.f_name, self.file_type = getFileNameType(self.file_path)
            self.output_dir = getDirectory(self.file_path)
            print(f"Save figure to {self.file_path} with format {self.file_type}")
            img_to_save = {}
            if self.selected_type == "Pickle Dictionary Files (*.pkl)":
                img_dict = self.img4d
                for key in ["data", "axes", "metadata", "original_metadata"]:
                    if key in img_dict.keys():
                        img_to_save[key] = img_dict[key]
                with open(self.file_path, "wb") as f:
                    pickle.dump(img_to_save, f)
            elif self.selected_type == "USID (*.hdf5)":
                img_dict = self.img4d
                for key in ["data", "axes", "metadata", "original_metadata"]:
                    if key in img_dict.keys():
                        img_to_save[key] = img_dict[key]
                usid_writer(self.file_path, img_to_save)
            else:
                # Save the current data only
                current_img = self.get_img_dict_from_canvas()
                for key in ["data", "axes", "metadata", "original_metadata"]:
                    if key in current_img.keys():
                        img_to_save[key] = current_img[key]

                if self.selected_type == "16-bit TIFF Files (*.tiff)":
                    save_as_tif16(img_to_save, self.f_name, self.output_dir)
                elif self.selected_type == "32-bit TIFF Files (*.tiff)":
                    save_as_tif16(
                        img_to_save, self.f_name, self.output_dir, dtype="float32"
                    )

                elif self.selected_type in [
                    "8-bit Grayscale TIFF Files (*.tiff)",
                    "Grayscale PNG Files (*.png)",
                    "Grayscale JPEG Files (*.jpg)",
                ]:
                    save_with_pil(
                        img_to_save,
                        self.f_name,
                        self.output_dir,
                        self.file_type,
                        scalebar=self.attribute["scalebar"],
                    )
                else:
                    # Save with pyqtgraph export function
                    exporter = pg.exporters.ImageExporter(self.canvas.viewbox)
                    exporter.parameters()["width"] = self.img_size[
                        1
                    ]  # Set export width to original image width
                    # exporter.parameters()['height'] = self.img_size[0]  # Set export height to original image height
                    exporter.export(self.file_path)

    def point_detector(self):
        self.clean_up(
            selector=True, buttons=True
        )  # Clean up existing selectors before adding a new one
        # Add a circle ROI to the diffraction canvas at the center of the Q space
        self.master_handle.point_detector_diffraction()  # Call the method to add the point detector to the diffraction canvas

    def circle_detector(self):
        self.clean_up(
            selector=True, buttons=True
        )  # Clean up existing selectors before adding a new one
        self.master_handle.circle_detector_diffraction(
            function=self.master_handle.update_detector_diffraction
        )  # Call the method to add the circle detector to the diffraction canvas

    def annular_detector(self):
        self.clean_up(
            selector=True, buttons=True
        )  # Clean up existing selectors before adding a new one
        self.master_handle.annular_detector_diffraction(
            function=self.master_handle.update_annular_detector_diffraction
        )  # Call the method to add the annular detector to the diffraction canvas

    def dpc(self):
        self.clean_up(
            selector=True, buttons=True
        )  # Clean up existing selectors before adding a new one
        self.master_handle.dpc()  # Call the method to perform DPC reconstruction from 4D-STEM data

    def idpc(self):
        self.clean_up(
            selector=True, buttons=True
        )  # Clean up existing selectors before adding a new one
        self.master_handle.idpc()  # Call the method to perform iDPC reconstruction from 4D-STEM data

    def ddpc(self):
        self.clean_up(
            selector=True, buttons=True
        )  # Clean up existing selectors before adding a new one
        self.master_handle.ddpc()  # Call the method to perform dDPC reconstruction from 4D-STEM data

    def com(self):
        self.clean_up(
            selector=True, buttons=True
        )  # Clean up existing selectors before adding a new one
        self.master_handle.com()  # Call the method to perform CoM reconstruction from 4D-STEM data

    def icom(self):
        self.clean_up(
            selector=True, buttons=True
        )  # Clean up existing selectors before adding a new one
        self.master_handle.icom()  # Call the method to perform iCoM reconstruction from 4D-STEM data

    def dcom(self):
        self.clean_up(
            selector=True, buttons=True
        )  # Clean up existing selectors before adding a new one
        self.master_handle.dcom()  # Call the method to perform dCoM reconstruction from 4D-STEM data

    def crop(self):
        self.clean_up(
            selector=True, buttons=True, modes=True, status_bar=True
        )  # Clean up any existing modes or selectors

        # Display a message in the status bar
        self.statusBar.showMessage("Drag the rectangle to crop.")

        # Initial rectangle position %37.5 from the left and top, 25% of the width, square
        x_range = self.img_size[-1] * self.scale
        y_range = self.img_size[-2] * self.scale
        x0 = x_range * 0.375
        y0 = y_range * 0.375
        selector = pg.RectROI(
            [x0, y0],
            [x_range * 0.25, x_range * 0.25],
            pen=pg.mkPen("r", width=5),
            movable=True,
            resizable=True,
            sideScalers=True,
            rotatable=False,
            maxBounds=QRectF(0, 0, x_range, y_range),
        )

        self.canvas.selector.append(selector)
        self._make_active_selector(selector)
        self.canvas.viewbox.addItem(selector)

        # Add buttons for confirm, cancel, and manual input
        OK_icon = os.path.join(self.wkdir, "icons/OK.png")
        self.buttons["ok"] = QAction(QIcon(OK_icon), "Confirm Crop", parent=self)
        self.buttons["ok"].setShortcut("Return")
        self.buttons["ok"].setStatusTip("Confirm Crop (Enter)")
        self.buttons["ok"].triggered.connect(self.master_handle.crop_Q)
        self.toolbar.addAction(self.buttons["ok"])
        cancel_icon = os.path.join(self.wkdir, "icons/cancel.png")
        self.buttons["cancel"] = QAction(QIcon(cancel_icon), "Cancel Crop", parent=self)
        self.buttons["cancel"].setShortcut("Esc")
        self.buttons["cancel"].setStatusTip("Cancel Crop (Esc)")
        self.buttons["cancel"].triggered.connect(self.cancel_crop)
        self.toolbar.addAction(self.buttons["cancel"])

        hand_icon = os.path.join(self.wkdir, "icons/hand.png")
        self.buttons["hand"] = QAction(QIcon(hand_icon), "Manual Input", parent=self)
        self.buttons["hand"].setStatusTip("Manual Input of Crop Coordinates")
        self.buttons["hand"].triggered.connect(self.manual_crop)
        self.toolbar.addAction(self.buttons["hand"])

        self.canvas.setFocus()  # Ensure the canvas has focus to receive key events

    def flip_horizontal(self):
        self.master_handle.flip_horizontal_Q()  # Call the method to flip the diffraction image horizontally

    def flip_vertical(self):
        self.master_handle.flip_vertical_Q()  # Call the method to flip the diffraction image vertically


class VirtualImageCanvas(PlotCanvas):
    def __init__(self, img4d, master_handle, parent=None):
        self.img4d = img4d  # Store the image dict with 4D data
        # Reformat the 4D image dict to fit the PlotCanvas class
        self.R_size = img4d["data"].shape[0], img4d["data"].shape[1]
        self.Q_size = img4d["data"].shape[2], img4d["data"].shape[3]
        v_img_data = img4d["data"][:, :, self.Q_size[0] // 2, self.Q_size[1] // 2]
        v_img = {
            "data": v_img_data,
            "metadata": img4d["metadata"],
            "axes": [img4d["axes"][0], img4d["axes"][1]],
        }
        if "original_metadata" in img4d.keys():
            v_img["original_metadata"] = img4d["original_metadata"]
        super().__init__(v_img, parent=parent)
        self.master_handle = master_handle
        self.setWindowTitle("Virtual Image")

    def closeEvent(self, event):
        self.parent().preview_dict.pop(self.canvas.canvas_name, None)
        Q_canvas_name = self.master_handle.Q_canvas.canvas.canvas_name
        if Q_canvas_name in self.parent().preview_dict:
            self.parent().preview_dict[
                Q_canvas_name
            ].close()  # Close the diffraction canvas if it's still open
            self.parent().preview_dict.pop(Q_canvas_name, None)
        self.master_handle = None  # Remove reference to master handle to allow garbage collection of the diffraction canvas if it's still open

    def create_menubar(self):
        menubar = self.menuBar()
        # menubar.clear()  # Clear existing menu items if any

        # File menu and actions
        file_menu = menubar.addMenu("&File")
        save_action = QAction("&Save as", self)
        save_action.setShortcut("ctrl+s")
        save_action.triggered.connect(self.save_figure)
        file_menu.addAction(save_action)
        copy_action = QAction("&Copy Image to Clipboard", self)
        copy_action.setShortcut("ctrl+alt+c")
        copy_action.triggered.connect(self.copy_img)
        file_menu.addAction(copy_action)
        copy_img_action = QAction("&New Image from Display", self)
        copy_img_action.triggered.connect(self.new_img_from_display)
        file_menu.addAction(copy_img_action)
        imagesetting_action = QAction("&Image Settings", self)
        imagesetting_action.setShortcut("ctrl+o")
        imagesetting_action.triggered.connect(self.image_settings)
        file_menu.addAction(imagesetting_action)
        close_action = QAction("&Close", self)
        close_action.setShortcut("ctrl+x")
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)
        close_all_action = QAction("&Close all", self)
        close_all_action.setShortcut("ctrl+shift+x")
        close_all_action.triggered.connect(self.close_all)
        file_menu.addAction(close_all_action)

        # Edit menu and actions
        edit_menu = menubar.addMenu("&Process")
        crop_action = QAction("&Crop", self)
        crop_action.setShortcut("ctrl+shift+c")
        crop_action.triggered.connect(self.crop)
        edit_menu.addAction(crop_action)

        fliplr_action = QAction("Flip horizontal", self)
        fliplr_action.triggered.connect(self.flip_horizontal)
        edit_menu.addAction(fliplr_action)
        flipud_action = QAction("Flip vertical", self)
        flipud_action.triggered.connect(self.flip_vertical)
        edit_menu.addAction(flipud_action)

        # Analyze menu and actions
        analyze_menu = menubar.addMenu("&Analyze")
        setscale_action = QAction("Set Scale", self)
        setscale_action.triggered.connect(self.setscale)
        analyze_menu.addAction(setscale_action)
        measure_action = QAction("Measure", self)
        measure_action.triggered.connect(self.measure)
        analyze_menu.addAction(measure_action)
        measure_angle_action = QAction("Measure Angle", self)
        measure_angle_action.triggered.connect(self.measure_angle)
        analyze_menu.addAction(measure_angle_action)

        lineprofile_action = QAction("Line Profile", self)
        lineprofile_action.triggered.connect(self.lineprofile)
        analyze_menu.addAction(lineprofile_action)

        # Detector menu and actions
        detector_menu = menubar.addMenu("&Detector")
        point_action = QAction("Point", self)
        point_action.setShortcut("ctrl+shift+p")
        point_action.triggered.connect(self.point_detector)
        detector_menu.addAction(point_action)

        rectangle_action = QAction("Rectangle", self)
        rectangle_action.setShortcut("ctrl+shift+r")
        rectangle_action.triggered.connect(self.rectangle_detector)
        detector_menu.addAction(rectangle_action)

        # FFT menu
        fft_menu = menubar.addMenu("&FFT")
        fft_action = QAction("&FFT", self)
        fft_action.setShortcut("ctrl+f")
        fft_action.triggered.connect(self.fft)
        fft_menu.addAction(fft_action)
        windowedfft_action = QAction("Windowed FFT", self)
        windowedfft_action.triggered.connect(self.windowedfft)
        fft_menu.addAction(windowedfft_action)
        livefft_action = QAction("&Live FFT", self)
        livefft_action.setShortcut("ctrl+shift+f")
        livefft_action.triggered.connect(self.live_fft)
        fft_menu.addAction(livefft_action)

        # Info menu
        info_menu = menubar.addMenu("&Info")
        # axes_action = QAction('Image Axes', self)
        # axes_action.triggered.connect(self.show_axes)
        # info_menu.addAction(axes_action)
        info_action = QAction("&Image Info", self)
        info_action.setShortcut("ctrl+i")
        info_action.triggered.connect(self.show_info)
        info_menu.addAction(info_action)
        about_action = QAction("About", self)
        about_action.triggered.connect(self.parent().show_about)
        info_menu.addAction(about_action)

        self.menubar = menubar

    def create_toolbar(self):
        self.toolbar = QToolBar("Virtual Image Toolbar")
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.addToolBar(self.toolbar)

        # Add actions to the toolbar
        home_icon = os.path.join(self.wkdir, "icons/home.png")
        home_action = QAction(QIcon(home_icon), "Home", self)
        home_action.setStatusTip("Auto scale to fit the window")
        home_action.triggered.connect(self.canvas.custom_auto_range)
        self.toolbar.addAction(home_action)

        save_icon = os.path.join(self.wkdir, "icons/save.png")
        save_action = QAction(QIcon(save_icon), "Save", self)
        save_action.setStatusTip("Save the current image")
        save_action.triggered.connect(self.save_figure)
        self.toolbar.addAction(save_action)

        copy_icon = os.path.join(self.wkdir, "icons/copy.png")
        copy_action = QAction(QIcon(copy_icon), "Copy", self)
        copy_action.setStatusTip("Copy the current image")
        copy_action.triggered.connect(self.copy_img)
        self.toolbar.addAction(copy_action)

        setting_icon = os.path.join(self.wkdir, "icons/settings.png")
        setting_action = QAction(QIcon(setting_icon), "Settings", self)
        setting_action.setStatusTip("Open settings")
        setting_action.triggered.connect(self.image_settings)
        self.toolbar.addAction(setting_action)

        self.toolbar.addSeparator()
        crop_icon = os.path.join(self.wkdir, "icons/crop.png")
        crop_action = QAction(QIcon(crop_icon), "Crop", self)
        crop_action.setStatusTip("Crop the real space")
        crop_action.triggered.connect(self.crop)
        self.toolbar.addAction(crop_action)

        measure_icon = os.path.join(self.wkdir, "icons/measure.png")
        measure_action = QAction(QIcon(measure_icon), "Measure", self)
        measure_action.setStatusTip("Measure distance and angle")
        measure_action.triggered.connect(self.measure)
        self.toolbar.addAction(measure_action)

        measure_angle_icon = os.path.join(self.wkdir, "icons/angle.png")
        measure_angle_action = QAction(QIcon(measure_angle_icon), "Measure Angle", self)
        measure_angle_action.setStatusTip("Measure angle from three points")
        measure_angle_action.triggered.connect(self.measure_angle)
        self.toolbar.addAction(measure_angle_action)

        lineprofile_icon = os.path.join(self.wkdir, "icons/lineprofile.png")
        lineprofile_action = QAction(QIcon(lineprofile_icon), "Line Profile", self)
        lineprofile_action.setStatusTip("Extract line profile")
        lineprofile_action.triggered.connect(self.lineprofile)
        self.toolbar.addAction(lineprofile_action)

        self.toolbar.addSeparator()

        point_detector_icon = os.path.join(self.wkdir, "icons/point_detector.png")
        point_detector_action = QAction(
            QIcon(point_detector_icon), "Point Detector", self
        )
        point_detector_action.setStatusTip("Add a point detector for diffraction")
        point_detector_action.triggered.connect(self.point_detector)
        self.toolbar.addAction(point_detector_action)

        rectangle_detector_icon = os.path.join(
            self.wkdir, "icons/rectangle_detector.png"
        )
        rectangle_detector_action = QAction(
            QIcon(rectangle_detector_icon), "Rectangle Detector", self
        )
        rectangle_detector_action.setStatusTip(
            "Add a rectangle detector for mean diffraction"
        )
        rectangle_detector_action.triggered.connect(self.rectangle_detector)
        self.toolbar.addAction(rectangle_detector_action)

        self.toolbar.addSeparator()

        info_icon = os.path.join(self.wkdir, "icons/info.png")
        info_action = QAction(QIcon(info_icon), "Info", self)
        info_action.setStatusTip("Show image info")
        info_action.triggered.connect(self.show_info)
        self.toolbar.addAction(info_action)

    def save_figure(self):
        options = QFileDialog.Options()
        # Remember and reuse last selected save filter (session only)
        last_save_filter = None
        try:
            last_save_filter = self.parent().settings.get(
                "lastSaveFilter", "16-bit TIFF Files (*.tiff)"
            )
        except Exception:
            last_save_filter = "16-bit TIFF Files (*.tiff)"
        save_filters = (
            "16-bit TIFF Files (*.tiff);;"
            "32-bit TIFF Files (*.tiff);;"
            "8-bit Grayscale TIFF Files (*.tiff);;"
            "Grayscale PNG Files (*.png);;"
            "Grayscale JPEG Files (*.jpg);;"
            "Color TIFF Files (*.tiff);;"
            "Color PNG Files (*.png);;"
            "Color JPEG Files (*.jpg);;"
            "USID (*.hdf5);;"
            "Pickle Dictionary Files (*.pkl)"
        )
        self.file_path, self.selected_type = QFileDialog.getSaveFileName(
            self.parent(),
            "Save Figure",
            "",
            save_filters,
            last_save_filter,
            options=options,
        )
        if self.file_path:
            # Update session-only selected filter for next time
            if self.selected_type:
                try:
                    self.parent().settings["lastSaveFilter"] = self.selected_type
                except Exception:
                    pass
            # Implement custom save logic here

            # Extract the chosen file format
            self.f_name, self.file_type = getFileNameType(self.file_path)
            self.output_dir = getDirectory(self.file_path)
            print(f"Save figure to {self.file_path} with format {self.file_type}")
            img_to_save = {}
            if self.selected_type == "Pickle Dictionary Files (*.pkl)":
                img_dict = self.img4d
                for key in ["data", "axes", "metadata", "original_metadata"]:
                    if key in img_dict.keys():
                        img_to_save[key] = img_dict[key]
                with open(self.file_path, "wb") as f:
                    pickle.dump(img_to_save, f)
            elif self.selected_type == "USID (*.hdf5)":
                img_dict = self.img4d
                for key in ["data", "axes", "metadata", "original_metadata"]:
                    if key in img_dict.keys():
                        img_to_save[key] = img_dict[key]
                usid_writer(self.file_path, img_to_save)
            else:
                # Save the current data only
                current_img = self.get_img_dict_from_canvas()
                for key in ["data", "axes", "metadata", "original_metadata"]:
                    if key in current_img.keys():
                        img_to_save[key] = current_img[key]

                if self.selected_type == "16-bit TIFF Files (*.tiff)":
                    save_as_tif16(img_to_save, self.f_name, self.output_dir)
                elif self.selected_type == "32-bit TIFF Files (*.tiff)":
                    save_as_tif16(
                        img_to_save, self.f_name, self.output_dir, dtype="float32"
                    )

                elif self.selected_type in [
                    "8-bit Grayscale TIFF Files (*.tiff)",
                    "Grayscale PNG Files (*.png)",
                    "Grayscale JPEG Files (*.jpg)",
                ]:
                    save_with_pil(
                        img_to_save,
                        self.f_name,
                        self.output_dir,
                        self.file_type,
                        scalebar=self.attribute["scalebar"],
                    )
                else:
                    # Save with pyqtgraph export function
                    exporter = pg.exporters.ImageExporter(self.canvas.viewbox)
                    exporter.parameters()["width"] = self.img_size[
                        1
                    ]  # Set export width to original image width
                    # exporter.parameters()['height'] = self.img_size[0]  # Set export height to original image height
                    exporter.export(self.file_path)

    def point_detector(self):
        self.clean_up(
            selector=True
        )  # Clean up existing selectors before adding a new one
        # Add a circle ROI to the diffraction canvas at the center of the Q space
        self.master_handle.point_detector_virtualimg()  # Call the method to add the point detector to the virtual image canvas

    def rectangle_detector(self):
        self.clean_up(
            selector=True
        )  # Clean up existing selectors before adding a new one
        self.master_handle.rectangle_detector_virtualimg()  # Call the method to add the rectangle detector to

    def crop(self):
        self.clean_up(
            selector=True, buttons=True, modes=True, status_bar=True
        )  # Clean up any existing modes or selectors

        # Display a message in the status bar
        self.statusBar.showMessage("Drag the rectangle to crop.")

        # Initial rectangle position %37.5 from the left and top, 25% of the width, square
        x_range = self.img_size[-1] * self.scale
        y_range = self.img_size[-2] * self.scale
        x0 = x_range * 0.375
        y0 = y_range * 0.375
        selector = pg.RectROI(
            [x0, y0],
            [x_range * 0.25, x_range * 0.25],
            pen=pg.mkPen("r", width=5),
            movable=True,
            resizable=True,
            sideScalers=True,
            rotatable=False,
            maxBounds=QRectF(0, 0, x_range, y_range),
        )

        self.canvas.selector.append(selector)
        self._make_active_selector(selector)
        self.canvas.viewbox.addItem(selector)

        # Add buttons for confirm, cancel, and manual input
        OK_icon = os.path.join(self.wkdir, "icons/OK.png")
        self.buttons["ok"] = QAction(QIcon(OK_icon), "Confirm Crop", parent=self)
        self.buttons["ok"].setShortcut("Return")
        self.buttons["ok"].setStatusTip("Confirm Crop (Enter)")
        self.buttons["ok"].triggered.connect(self.master_handle.crop_R)
        self.toolbar.addAction(self.buttons["ok"])
        cancel_icon = os.path.join(self.wkdir, "icons/cancel.png")
        self.buttons["cancel"] = QAction(QIcon(cancel_icon), "Cancel Crop", parent=self)
        self.buttons["cancel"].setShortcut("Esc")
        self.buttons["cancel"].setStatusTip("Cancel Crop (Esc)")
        self.buttons["cancel"].triggered.connect(self.cancel_crop)
        self.toolbar.addAction(self.buttons["cancel"])

        hand_icon = os.path.join(self.wkdir, "icons/hand.png")
        self.buttons["hand"] = QAction(QIcon(hand_icon), "Manual Input", parent=self)
        self.buttons["hand"].setStatusTip("Manual Input of Crop Coordinates")
        self.buttons["hand"].triggered.connect(self.manual_crop)
        self.toolbar.addAction(self.buttons["hand"])

        self.canvas.setFocus()  # Ensure the canvas has focus to receive key events

    def flip_horizontal(self):
        self.master_handle.flip_horizontal_R()  # Call the method to flip the virtual image horizontally

    def flip_vertical(self):
        self.master_handle.flip_vertical_R()  # Call the method to flip the virtual image vertically


class PlotCanvas4D:
    def __init__(self, img, parent=None):
        self.img4d = img  # Store the original 4D image dict
        self.img_data = img["data"]
        if self.img_data.ndim != 4:
            print("Error: The image data must be 4D.")
            return
        self.data_type = "4D-STEM"
        self.R_size = img["data"].shape[0], img["data"].shape[1]
        self.Q_size = img["data"].shape[2], img["data"].shape[3]
        self.R_center = self.R_size[0] // 2, self.R_size[1] // 2
        self.Q_center = self.Q_size[0] // 2, self.Q_size[1] // 2
        self.R_canvas = VirtualImageCanvas(
            self.img4d, master_handle=self, parent=parent
        )
        self.Q_canvas = DiffractionCanvas(self.img4d, master_handle=self, parent=parent)

        self.point_detector_diffraction()  # Initialize the point detector on the diffraction canvas
        self.point_detector_virtualimg()  # Initialize the point detector on the virtual image canvas

    def show(self):
        self.R_canvas.show()
        self.R_canvas.position_window("center left")
        self.Q_canvas.show()
        self.Q_canvas.position_window("center right")

    def remove_roi_Q(self, roi):
        if roi in self.Q_canvas.canvas.selector:
            self.Q_canvas.canvas.selector.remove(roi)
            self.Q_canvas.canvas.active_selector = None
            self.Q_canvas.canvas.viewbox.removeItem(roi)

        if len(self.Q_canvas.canvas.selector) == 0:
            self.Q_canvas.clean_up(
                buttons=True
            )  # Clean up any buttons related to the selector

    def remove_roi_R(self, roi):
        if roi in self.R_canvas.canvas.selector:
            self.R_canvas.canvas.selector.remove(roi)
            self.R_canvas.canvas.active_selector = None
            self.R_canvas.canvas.viewbox.removeItem(roi)

    def point_detector_diffraction(self):
        # Add a circle ROI to the diffraction canvas at the center of the Q space
        x_range = self.Q_canvas.img_size[-1] * self.Q_canvas.scale
        y_range = self.Q_canvas.img_size[-2] * self.Q_canvas.scale
        x0 = self.Q_center[1] * self.Q_canvas.scale
        y0 = self.Q_center[0] * self.Q_canvas.scale
        selector = pg.CircleROI(
            [x0, y0],
            radius=1 * self.Q_canvas.scale,
            pen=pg.mkPen("red", width=5),
            movable=True,
            rotatable=False,
            resizable=False,
            removable=True,
            maxBounds=QRectF(0, 0, x_range, y_range),
        )

        self.Q_canvas.canvas.selector.append(selector)
        self.Q_canvas._make_active_selector(selector)
        self.Q_canvas.canvas.viewbox.addItem(selector)
        h0 = selector.getHandles()[0]  # remove default scale handle
        selector.removeHandle(h0)
        selector.addTranslateHandle([0.5, 0.5])
        selector.sigRegionChanged.connect(self.update_point_detector_diffraction)
        selector.sigRemoveRequested.connect(lambda roi: self.remove_roi_Q(roi))

    def update_point_detector_diffraction(self):
        selector = self.Q_canvas.canvas.selector[
            0
        ]  # Assuming only one selector for point detector
        pos = (
            selector.pos() + selector.size() * 0.5
        )  # Get the center position of the circle ROI
        qx = pos.x() / self.Q_canvas.scale
        qy = pos.y() / self.Q_canvas.scale
        # Update the virtual image based on the new position in Q space
        v_img_data = self.img_data[:, :, int(qy), int(qx)]
        self.R_canvas.canvas.update_img(v_img_data)

    def point_detector_virtualimg(self):
        # Add a circle ROI to the diffraction canvas at the center of the Q space
        x_range = self.R_canvas.img_size[-1] * self.R_canvas.scale
        y_range = self.R_canvas.img_size[-2] * self.R_canvas.scale
        x0 = self.R_center[1] * self.R_canvas.scale
        y0 = self.R_center[0] * self.R_canvas.scale
        selector = pg.CircleROI(
            [x0, y0],
            radius=1 * self.R_canvas.scale,
            pen=pg.mkPen("red", width=5),
            movable=True,
            rotatable=False,
            resizable=False,
            removable=True,
            maxBounds=QRectF(0, 0, x_range, y_range),
        )

        self.R_canvas.canvas.selector.append(selector)
        self.R_canvas._make_active_selector(selector)
        self.R_canvas.canvas.viewbox.addItem(selector)
        h0 = selector.getHandles()[0]  # remove default scale handle
        selector.removeHandle(h0)
        selector.addTranslateHandle([0.5, 0.5])
        selector.sigRegionChanged.connect(self.update_point_detector_virtualimg)
        selector.sigRemoveRequested.connect(lambda roi: self.remove_roi_R(roi))

    def update_point_detector_virtualimg(self):
        selector = self.R_canvas.canvas.selector[
            0
        ]  # Assuming only one selector for point detector
        pos = (
            selector.pos() + selector.size() * 0.5
        )  # Get the center position of the circle ROI
        x = pos.x() / self.R_canvas.scale
        y = pos.y() / self.R_canvas.scale
        # Update the diffraction image based on the new position in R space
        q_img_data = self.img_data[int(y), int(x), :, :]
        pvmin = self.Q_canvas.pvmin
        pvmax = self.Q_canvas.pvmax
        self.Q_canvas.canvas.update_img(q_img_data, pvmin=pvmin, pvmax=pvmax)

    def rectangle_detector_virtualimg(self):
        # Add a rectangle ROI to the virtual image canvas at the center of the R space
        x_range = self.R_canvas.img_size[-1] * self.R_canvas.scale
        y_range = self.R_canvas.img_size[-2] * self.R_canvas.scale
        x0 = self.R_center[1] * self.R_canvas.scale
        y0 = self.R_center[0] * self.R_canvas.scale
        width = 0.2 * x_range  # Default width as 20% of the x_range
        height = 0.2 * y_range  # Default height as 20% of the y_range
        selector = pg.RectROI(
            [x0 - width / 2, y0 - height / 2],
            [width, height],
            pen=pg.mkPen("yellow", width=5),
            movable=True,
            rotatable=False,
            resizable=True,
            removable=True,
            maxBounds=QRectF(0, 0, x_range, y_range),
        )
        self.R_canvas.canvas.selector.append(selector)
        self.R_canvas._make_active_selector(selector)
        self.R_canvas.canvas.viewbox.addItem(selector)

        selector.sigRegionChangeFinished.connect(
            self.update_rectangle_detector_virtualimg
        )
        selector.sigRemoveRequested.connect(lambda roi: self.remove_roi_R(roi))

    def update_rectangle_detector_virtualimg(self):
        selector = self.R_canvas.canvas.selector[
            0
        ]  # Assuming only one selector for rectangle detector
        pos = selector.pos()  # Get the top-left position of the rectangle ROI
        size = selector.size()  # Get the size of the rectangle ROI
        x_start = int(pos.x() / self.R_canvas.scale)
        y_start = int(pos.y() / self.R_canvas.scale)
        x_end = int((pos.x() + size.x()) / self.R_canvas.scale)
        y_end = int((pos.y() + size.y()) / self.R_canvas.scale)
        # Update the diffraction image to be the mean of the selected region in R space
        q_img_data = np.mean(
            self.img_data[y_start:y_end, x_start:x_end, :, :], axis=(0, 1)
        )
        pvmin = self.Q_canvas.pvmin
        pvmax = self.Q_canvas.pvmax
        self.Q_canvas.canvas.update_img(q_img_data, pvmin=pvmin, pvmax=pvmax)

    def circle_detector_diffraction(self, function):
        # Add a resizable circle ROI to the diffraction canvas at the center of the Q space
        x_range = self.Q_canvas.img_size[-1] * self.Q_canvas.scale
        y_range = self.Q_canvas.img_size[-2] * self.Q_canvas.scale
        x0 = self.Q_center[1] * self.Q_canvas.scale
        y0 = self.Q_center[0] * self.Q_canvas.scale
        radius = 0.05 * min(
            x_range, y_range
        )  # Default radius as 5% of the smaller dimension of the canvas
        selector = pg.CircleROI(
            [x0 - radius, y0 - radius],
            radius=radius,
            pen=pg.mkPen("yellow", width=5),
            movable=True,
            rotatable=False,
            resizable=True,
            removable=True,
            maxBounds=QRectF(0, 0, x_range, y_range),
        )

        self.Q_canvas.canvas.selector.append(selector)
        self.Q_canvas._make_active_selector(selector)
        self.Q_canvas.canvas.viewbox.addItem(selector)
        selector.addTranslateHandle([0.5, 0.5])

        # # Change colors of the side handles
        h = selector.getHandles()
        for handle in h:
            handle.pen = pg.mkPen("red", width=5)
            handle.hoverPen = pg.mkPen("red", width=2)
            handle.currentPen = handle.pen
            handle.update()

        # Add apply button to update
        if (
            self.Q_canvas.buttons["ok"] is None
        ):  # Only add the button if it doesn't already exist
            OK_icon = os.path.join(self.Q_canvas.wkdir, "icons/OK.png")
            self.Q_canvas.buttons["ok"] = QAction(
                QIcon(OK_icon), "Apply Virtual Detector", parent=self.Q_canvas
            )
            self.Q_canvas.buttons["ok"].setShortcut("Return")
            self.Q_canvas.buttons["ok"].setStatusTip("Apply Virtual Detector (Enter)")
            self.Q_canvas.buttons["ok"].triggered.connect(function)
            self.Q_canvas.toolbar.addAction(self.Q_canvas.buttons["ok"])

        # selector.sigRegionChangeFinished.connect(function)  # Connect the region change signal to the provided function to update the virtual image when the circle ROI is moved or resized
        selector.sigRemoveRequested.connect(lambda roi: self.remove_roi_Q(roi))

        # Add an "Add" action to the selector context menu
        add_action = QAction("Add ROI", self.Q_canvas)
        add_action.triggered.connect(self.add_circle_detector_diffraction)
        menu = selector.getMenu()
        menu.addAction(add_action)

    def add_circle_detector_diffraction(self):
        # This method can be called to add a new circle detector without removing the existing one
        self.circle_detector_diffraction(function=self.update_detector_diffraction)

    def update_detector_diffraction(self):
        # Update the virtual image with all selectors
        centers = []
        radii = []
        if not self.Q_canvas.canvas.selector:
            return  # No selectors, do not update the virtual image
        for selector in self.Q_canvas.canvas.selector:
            pos = (
                selector.pos() + selector.size() * 0.5
            )  # Get the center position of the circle ROI
            radius = int(
                selector.size().x() / 2 / self.Q_canvas.scale
            )  # Assuming the size is the diameter of the circle
            x_center = pos.x() / self.Q_canvas.scale
            y_center = pos.y() / self.Q_canvas.scale
            centers.append((x_center, y_center))
            radii.append(radius)
        mask = create_mask(self.Q_size, centers, radii, edge_blur=0).astype(
            np.float64, copy=False
        )
        # Calculate the virtual image in a separate thread
        self.worker = Worker(self.get_virtual_image_with_mask, mask)
        self.R_canvas.toggle_progress_bar("ON")
        self.worker.finished.connect(lambda: self.R_canvas.toggle_progress_bar("OFF"))
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.result.connect(self._on_com_result)
        self.worker.start()

    def annular_detector_diffraction(self, function):
        # Add a resizable annular ROI to the diffraction canvas at the center of the Q space
        x_range = self.Q_canvas.img_size[-1] * self.Q_canvas.scale
        y_range = self.Q_canvas.img_size[-2] * self.Q_canvas.scale
        x0 = self.Q_center[1] * self.Q_canvas.scale
        y0 = self.Q_center[0] * self.Q_canvas.scale
        inner_radius = 0.1 * min(x_range, y_range)
        outer_radius = 0.3 * min(x_range, y_range)
        selector = AnnularROI(
            [x0, y0],
            inner_radius=inner_radius,
            outer_radius=outer_radius,
            pen=pg.mkPen("yellow", width=5),
            movable=True,
            rotatable=False,
            resizable=True,
            removable=True,
            maxBounds=QRectF(0, 0, x_range, y_range),
        )
        self.Q_canvas.canvas.selector.append(selector)
        self.Q_canvas._make_active_selector(selector)
        self.Q_canvas.canvas.viewbox.addItem(selector)

        # Add apply button to update
        OK_icon = os.path.join(self.Q_canvas.wkdir, "icons/OK.png")
        self.Q_canvas.buttons["ok"] = QAction(
            QIcon(OK_icon), "Apply Virtual Detector", parent=self.Q_canvas
        )
        self.Q_canvas.buttons["ok"].setShortcut("Return")
        self.Q_canvas.buttons["ok"].setStatusTip("Apply Virtual Detector (Enter)")
        self.Q_canvas.buttons["ok"].triggered.connect(function)
        self.Q_canvas.toolbar.addAction(self.Q_canvas.buttons["ok"])

        # selector.sigAnnulusChangeFinished.connect(function)  # Connect the annulus change signal to the provided function to update the virtual image when the annular ROI is moved or resized
        selector.sigRemoveRequested.connect(lambda roi: self.remove_roi_Q(roi))

    def get_virtual_image_with_mask(self, mask):
        # This method can be called to get the virtual image based on a custom mask
        # Use contraction to avoid allocating a full 4D temporary (img_data * mask).
        mask = np.asarray(mask)
        virtualimg = np.tensordot(self.img_data, mask, axes=([2, 3], [0, 1]))
        return virtualimg

    def get_annular_mask(self, size, center, inner_radius, outer_radius):
        mask = np.zeros(size)
        y, x = np.ogrid[: size[0], : size[1]]
        dist_from_center = np.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2)
        mask[
            (dist_from_center >= inner_radius) & (dist_from_center <= outer_radius)
        ] = 1
        return mask

    def update_annular_detector_diffraction(self):
        # Update the virtual image with all selectors
        selector = self.Q_canvas.canvas.selector[
            0
        ]  # Assuming only one selector for annular detector
        Q_scale = self.Q_canvas.scale
        center = selector.center
        inner_radius = selector.inner_radius
        outer_radius = selector.outer_radius
        x_center = center[0] / Q_scale
        y_center = center[1] / Q_scale
        inner_radius_px = inner_radius / Q_scale
        outer_radius_px = outer_radius / Q_scale

        mask = self.get_annular_mask(
            self.Q_size, (x_center, y_center), inner_radius_px, outer_radius_px
        ).astype(np.float64, copy=False)
        self.worker = Worker(self.get_virtual_image_with_mask, mask)
        self.R_canvas.toggle_progress_bar("ON")
        self.worker.finished.connect(lambda: self.R_canvas.toggle_progress_bar("OFF"))
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.result.connect(self._on_com_result)
        self.worker.start()

    def com(self):
        self.circle_detector_diffraction(lambda: self.update_com(signal="CoM"))
        # Set the circle non-removable
        roi = self.Q_canvas.canvas.selector[0]
        roi.removable = False
        if roi.menu is not None and hasattr(roi.menu, "remAct"):
            roi.menu.removeAction(roi.menu.remAct)
            roi.menu.remAct.deleteLater()
            del roi.menu.remAct

    def icom(self):
        self.circle_detector_diffraction(lambda: self.update_com(signal="iCoM"))
        roi = self.Q_canvas.canvas.selector[0]
        roi.removable = False
        if roi.menu is not None and hasattr(roi.menu, "remAct"):
            roi.menu.removeAction(roi.menu.remAct)
            roi.menu.remAct.deleteLater()
            del roi.menu.remAct

    def dcom(self):
        self.circle_detector_diffraction(lambda: self.update_com(signal="dCoM"))
        roi = self.Q_canvas.canvas.selector[0]
        roi.removable = False
        if roi.menu is not None and hasattr(roi.menu, "remAct"):
            roi.menu.removeAction(roi.menu.remAct)
            roi.menu.remAct.deleteLater()
            del roi.menu.remAct

    def update_com(self, signal="CoM"):
        selector = self.Q_canvas.canvas.selector[0]  # Only the first selector for CoM
        pos = (
            selector.pos() + selector.size() * 0.5
        )  # Get the center position of the circle ROI
        radius = int(
            selector.size().x() / 2 / self.Q_canvas.scale
        )  # Assuming the size is the diameter of the circle
        x_center = pos.x() / self.Q_canvas.scale
        y_center = pos.y() / self.Q_canvas.scale

        # Calculate CoM with a separate thread
        self.worker = Worker(
            self.calculate_com, self.img_data, (x_center, y_center), radius, mode=signal
        )
        self.R_canvas.toggle_progress_bar("ON")
        self.worker.finished.connect(lambda: self.R_canvas.toggle_progress_bar("OFF"))
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.result.connect(self._on_com_result)
        self.worker.start()

    def _on_com_result(self, virtualimg):
        # Worker signals are delivered to the GUI thread, so UI updates are safe here.
        self.R_canvas.canvas.img_data = virtualimg
        if np.iscomplexobj(virtualimg):
            self.R_canvas.canvas.data_type = "Complex Image"
            self.R_canvas.attribute["complex_display"] = "Phase"
        else:
            self.R_canvas.canvas.data_type = "Image"
        self.R_canvas.canvas.update_img(virtualimg)

    def calculate_com(self, data, center, radius, mode="CoM"):
        x_center, y_center = center
        Q_size = data.shape[2], data.shape[3]
        # radius: single value for circle, tuple for annulus (inner_radius, outer_radius)
        if isinstance(radius, (int, float)):
            mask = create_mask(
                Q_size, [(int(x_center), int(y_center))], [radius], edge_blur=0
            ).astype(np.float64, copy=False)
        elif isinstance(radius, (tuple, list)) and len(radius) == 2:
            mask = self.get_annular_mask(Q_size, center, radius[0], radius[1]).astype(
                np.float64, copy=False
            )

        # Vectorized weighted reductions without allocating a 4D masked copy.
        yy = np.arange(Q_size[0], dtype=np.float64)[:, None]  # axis=2
        xx = np.arange(Q_size[1], dtype=np.float64)[None, :]  # axis=3
        mass = np.tensordot(data, mask, axes=([2, 3], [0, 1]))
        com_y_num = np.tensordot(data, mask * yy, axes=([2, 3], [0, 1]))
        com_x_num = np.tensordot(data, mask * xx, axes=([2, 3], [0, 1]))

        # Avoid divide-by-zero
        eps = 1e-12
        com_y = com_y_num / np.maximum(mass, eps)
        com_x = com_x_num / np.maximum(mass, eps)

        # The com is to the image center, need to subtract the center coordinates
        self.com_y = com_y - y_center
        self.com_x = com_x - x_center

        if mode == "CoM":
            virtualimg = self.com_x + 1j * self.com_y
        elif mode == "iCoM":
            virtualimg = reconstruct_iDPC(self.com_x, self.com_y)
        elif mode == "dCoM":
            virtualimg = reconstruct_dDPC(self.com_x, self.com_y)

        return virtualimg

    def dpc(self):
        self.annular_detector_diffraction(lambda: self.update_dpc(signal="CoM"))

    def idpc(self):
        self.annular_detector_diffraction(lambda: self.update_dpc(signal="iCoM"))

    def ddpc(self):
        self.annular_detector_diffraction(lambda: self.update_dpc(signal="dCoM"))

    def update_dpc(self, signal="CoM"):
        # This method can be called to update the DPC image based on the current CoM shifts
        selector = self.Q_canvas.canvas.selector[
            0
        ]  # Assuming only one selector for annular detector
        Q_scale = self.Q_canvas.scale
        center = selector.center
        inner_radius = selector.inner_radius
        outer_radius = selector.outer_radius
        x_center = center[0] / Q_scale
        y_center = center[1] / Q_scale
        inner_radius_px = inner_radius / Q_scale
        outer_radius_px = outer_radius / Q_scale

        # Calculate CoM with a separate thread
        self.worker = Worker(
            self.calculate_com,
            self.img_data,
            (x_center, y_center),
            (inner_radius_px, outer_radius_px),
            mode=signal,
        )
        self.R_canvas.toggle_progress_bar("ON")
        self.worker.finished.connect(lambda: self.R_canvas.toggle_progress_bar("OFF"))
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.result.connect(self._on_com_result)
        self.worker.start()

    def crop_R(self):
        # This method can be called to crop the R image based on the current rectangle selector
        selector = self.R_canvas.canvas.selector[
            0
        ]  # Assuming only one selector for cropping
        pos = selector.pos()  # Get the top-left position of the rectangle ROI
        size = selector.size()  # Get the size of the rectangle ROI
        x_start = round(pos.x() / self.R_canvas.scale)
        y_start = round(pos.y() / self.R_canvas.scale)
        x_end = round((pos.x() + size.x()) / self.R_canvas.scale)
        y_end = round((pos.y() + size.y()) / self.R_canvas.scale)
        # Crop the 4D data in place
        self.img_data = self.img_data[y_start:y_end, x_start:x_end, :, :]
        # Update the img4d dictionary to reflect the cropped data
        self.R_size = self.img_data.shape[0], self.img_data.shape[1]
        self.R_center = self.R_size[0] // 2, self.R_size[1] // 2
        self.R_canvas.canvas.img_size = self.R_size
        self.img4d["data"] = self.img_data
        self.img4d["axes"][0]["size"] = self.R_size[0]
        self.img4d["axes"][1]["size"] = self.R_size[1]

        # Update the virtual image canvas with the cropped data
        v_img_data = self.img_data[:, :, self.Q_center[0], self.Q_center[1]]
        self.R_canvas.canvas.update_img(v_img_data)

        # Update the process history
        self.R_canvas.update_metadata(
            "Real space cropped to x:[{}:{}], y:[{}:{}]".format(
                x_start, x_end, y_start, y_end
            )
        )

        # Clean up the selector and buttons after cropping
        self.R_canvas.clean_up(selector=True, buttons=True, modes=True, status_bar=True)

        self.R_canvas.point_detector()  # Re-add the point detector to the virtual image canvas after cropping

    def crop_Q(self):
        # This method can be called to crop the Q image based on the current rectangle selector
        selector = self.Q_canvas.canvas.selector[
            0
        ]  # Assuming only one selector for cropping
        pos = selector.pos()  # Get the top-left position of the rectangle ROI
        size = selector.size()  # Get the size of the rectangle ROI
        x_start = round(pos.x() / self.Q_canvas.scale)
        y_start = round(pos.y() / self.Q_canvas.scale)
        x_end = round((pos.x() + size.x()) / self.Q_canvas.scale)
        y_end = round((pos.y() + size.y()) / self.Q_canvas.scale)
        # Crop the 4D data in place
        self.img_data = self.img_data[:, :, y_start:y_end, x_start:x_end]
        # Update the img4d dictionary to reflect the cropped data
        self.Q_size = self.img_data.shape[2], self.img_data.shape[3]
        self.Q_center = self.Q_size[0] // 2, self.Q_size[1] // 2
        self.Q_canvas.canvas.img_size = self.Q_size
        self.img4d["data"] = self.img_data
        self.img4d["axes"][2]["size"] = self.Q_size[1]
        self.img4d["axes"][3]["size"] = self.Q_size[0]

        # # Update the diffraction image canvas with the cropped data
        q_img_data = self.img_data[self.R_center[0], self.R_center[1], :, :]
        pvmin = self.Q_canvas.pvmin
        pvmax = self.Q_canvas.pvmax
        self.Q_canvas.canvas.update_img(q_img_data, pvmin=pvmin, pvmax=pvmax)

        # Update the process history
        self.Q_canvas.update_metadata(
            "Reciprocal space cropped to qx:[{}:{}], qy:[{}:{}]".format(
                x_start, x_end, y_start, y_end
            )
        )

        # Clean up the selector and buttons after cropping
        self.Q_canvas.clean_up(selector=True, buttons=True, modes=True, status_bar=True)

        self.Q_canvas.point_detector()  # Re-add the point detector to the diffraction canvas after cropping

    def flip_horizontal_R(self):
        # This method can be called to flip the R image horizontally
        self.img_data = self.img_data[:, ::-1, :, :]
        self.img4d["data"] = self.img_data
        # Update the virtual image canvas with the flipped data
        self.update_point_detector_diffraction()
        # Update the process history
        self.R_canvas.update_metadata("Real space flipped horizontally")

    def flip_vertical_R(self):
        # This method can be called to flip the R image vertically
        self.img_data = self.img_data[::-1, :, :, :]
        self.img4d["data"] = self.img_data
        # Update the virtual image canvas with the flipped data
        self.update_point_detector_diffraction()
        # Update the process history
        self.R_canvas.update_metadata("Real space flipped vertically")

    def flip_horizontal_Q(self):
        # This method can be called to flip the Q image horizontally
        self.img_data = self.img_data[:, :, :, ::-1]
        self.img4d["data"] = self.img_data
        # Update the diffraction image canvas with the flipped data
        self.update_point_detector_virtualimg()
        # Update the process history
        self.Q_canvas.update_metadata("Reciprocal space flipped horizontally")

    def flip_vertical_Q(self):
        # This method can be called to flip the Q image vertically
        self.img_data = self.img_data[:, :, ::-1, :]
        self.img4d["data"] = self.img_data
        # Update the diffraction image canvas with the flipped data
        self.update_point_detector_virtualimg()
        # Update the process history
        self.Q_canvas.update_metadata("Reciprocal space flipped vertically")


# ================== Annular selector ROI ============================
class AnnularROI(pg.CircleROI):
    sigAnnulusChangeFinished = pyqtSignal(object)

    def __init__(self, center, inner_radius, outer_radius, **kwargs):
        # center: tuple/list of (x, y) in scene coordinates
        self.inner_radius = float(inner_radius)
        self.outer_radius = float(outer_radius)
        self.center = (float(center[0]), float(center[1]))

        pos_inner = (
            self.center[0] - self.inner_radius,
            self.center[1] - self.inner_radius,
        )
        super().__init__(pos_inner, radius=self.inner_radius, **kwargs)

        pen = kwargs.get("pen", pg.mkPen("yellow", width=5))
        movable = kwargs.get("movable", True)
        rotatable = kwargs.get("rotatable", False)
        resizable = kwargs.get("resizable", True)
        # Add a translate handle to the inner circle for moving the entire annulus
        self.addTranslateHandle([0.5, 0.5])

        # Change handle colors of the inner circle
        handles = self.getHandles()
        handle_pen = pg.mkPen("red", width=5)
        for handle in handles:
            handle.pen = handle_pen
            handle.hoverPen = pg.mkPen("red", width=2)
            handle.currentPen = handle.pen
            handle.update()

        # Outer ring is visual-only; parented so the annulus is one add/remove ROI item.
        self.outer_circle = pg.CircleROI(
            [0, 0],
            radius=self.outer_radius,
            pen=pen,
            movable=movable,
            rotatable=rotatable,
            resizable=resizable,
        )
        self.outer_circle.setParentItem(self)
        self.outer_circle.setZValue(-1)
        self._syncing = False
        # Change handle colors of the outer circle
        outer_handles = self.outer_circle.getHandles()
        for handle in outer_handles:
            handle.pen = handle_pen
            handle.hoverPen = pg.mkPen("red", width=2)
            handle.currentPen = handle.pen
            handle.update()

        self.sigRegionChanged.connect(self.update_outer_circle)
        self.outer_circle.sigRegionChanged.connect(self.update_inner_from_outer)
        self.sigRegionChangeFinished.connect(self._on_inner_change_finished)
        self.outer_circle.sigRegionChangeFinished.connect(
            self._on_outer_change_finished
        )
        self.update_outer_circle()

    def update_outer_circle(self):
        if self._syncing:
            return
        self._syncing = True

        # Parent-local alignment: keep both circles concentric.
        inner_radius = self.size().x() / 2.0
        local_offset = inner_radius - self.outer_radius
        self.outer_circle.blockSignals(True)
        try:
            self.outer_circle.setPos(local_offset, local_offset)
            self.outer_circle.setSize(
                (2.0 * self.outer_radius, 2.0 * self.outer_radius)
            )
        finally:
            self.outer_circle.blockSignals(False)

        pos = self.pos()
        self.inner_radius = inner_radius
        self.center = (pos.x() + inner_radius, pos.y() + inner_radius)

        self._syncing = False

    def update_inner_from_outer(self):
        if self._syncing:
            return
        self._syncing = True

        # Outer circle geometry is in parent-local coordinates.
        outer_pos = self.outer_circle.pos()
        outer_radius = self.outer_circle.size().x() / 2.0

        inner_radius = self.size().x() / 2.0
        center_local = QPointF(
            outer_pos.x() + outer_radius, outer_pos.y() + outer_radius
        )
        inner_center_local = QPointF(inner_radius, inner_radius)
        delta = center_local - inner_center_local

        # Suppress inner ROI signals while it follows the outer ROI.
        self.blockSignals(True)
        try:
            # Move inner circle by center delta; this avoids frame-mixing errors.
            self.setPos(self.pos() + delta)

            # Persist updated annulus geometry.
            self.outer_radius = outer_radius
            pos = self.pos()
            self.center = (pos.x() + inner_radius, pos.y() + inner_radius)

            # Re-anchor outer ring around the new parent origin.
            self.outer_circle.setPos(
                inner_radius - self.outer_radius, inner_radius - self.outer_radius
            )
            self.outer_circle.setSize(
                (2.0 * self.outer_radius, 2.0 * self.outer_radius)
            )
        finally:
            self.blockSignals(False)

        self._syncing = False

    def _on_inner_change_finished(self, _roi=None):
        if self._syncing:
            return
        self.sigAnnulusChangeFinished.emit(self)

    def _on_outer_change_finished(self, _roi=None):
        # Ensure final geometry is synchronized, then emit one finished signal for the annular ROI.
        self.update_inner_from_outer()
        self.sigAnnulusChangeFinished.emit(self)
