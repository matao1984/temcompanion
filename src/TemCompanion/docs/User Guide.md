# TemCompanion

## Table of Contents
- [Overview](#overview)
- [List of available functions](#list-of-available-functions)
- [1. Installation](#1-installation)
- [2. Usage](#2-usage)
- [3. Formats](#3-formats)
  - [3.1 Input formats](#31-input-formats)
  - [3.2 Output formats](#32-output-formats)
- [4. Descriptions of functions](#4-descriptions-of-functions)
  - [4.1 Basic processing functions](#41-basic-processing-functions)
  - [4.2 Analyze functions](#42-analyze-functions)
  - [4.3 Fast Fourier transforms](#43-fast-fourier-transforms)
  - [4.4 Filter](#44-filter)
  - [4.5 Stack Operations](#45-stack-operations)
  - [4.6 Supported 4D-STEM functions](#46-supported-4d-stem-functions)
- [5. Batch Convert](#5-batch-convert)
- [6. Default settings](#6-default-settings)
- [7. Citation](#7-citation)
- [8. Change history](#8-change-history)

## Overview
[TemCompanion](https://github.com/matao1984/temcompanion) is a convenient and lightweight tool to view, edit, and convert TEM micrographs to the common image formats including tiff, png, and jpg. The data import is built on the ``rsciio`` module and TemCompanion is currently programmed to support FEI Velox (*.emd) format, Gatan DigitalMicrograph (*.dm3, *.dm4) format, FEI TIA (*.ser) format, MRC format, and common image formats including TIFF, PNG, and JPG. These formats cover most of the scenarios of TEM data acquisition. More formats may be added in later releases given enough interests. TemCompanion was orignally developed based on the [EMD converter](https://github.com/matao1984/emd-converter) that was explicitly used for data convertion. On top of it, a simple data viewer has been added, together with some useful functions including rotate, crop, measure, calibrate, and FFT. These would cover most of the TEM data processing and analysis needs. Also added is filtering functions, based on the [hrtem_filter](https://github.com/matao1984/hrtem_filter). In addition, it supports the above operations on image stacks. A full list of available functions is as follows:

## List of available functions
* Preview any image type signals. If the input file contains multiple image frames, a slider bar is added on the image to navigate.
* Rotate image: positive angles would rotate the image counterclockwise and vice versa. The image will expand upon rotation.
* Crop image: crop to any size with a GUI rectangle selection.
* Adjust vmin/vmax for display.
* Apply a color map to images.
* Add a scalebar and customize its color, location, etc.
* View and set the pixel scale.
* Measure distance and angle interactively by drawing a line on images.
* Extract line profiles interactively.
* Extract radial integration from a selectable center.
* Simple math on two images or stacks: addition, subtraction, multiplication, division, and inversion.
* Compute a fast Fourier transform directly or with a Hann window applied.
* Compute live FFT from a selected area that can be adjusted interactively.
* Apply masks on FFT and compute masked inverse FFT.
* Measure d-spacing from FFT or diffraction patterns. The spot position is fitted with a center of mass function. The angle from horizontal direction is also measured.
* Apply Wiener, ABS, non-linear, Butterworth, and Gaussian filters on HRTEM/HRSTEM images. The filter parameters can be adjusted.
* View the image information and metadata of the TEM data file.
* The processing history by TemCompanion is saved in the metadata tree under "process" entry.
* Import image series from a folder.
* Crop, rotate, flip, resampling, and export stack images.
* Reorder and delete frames of a stack.
* Align image stack with both phase cross-correlation (rigid) and optical flow (non rigid).
* Copy displayed images directly and paste to power point, etc.
* Run geometric phase analysis on HR(S)TEM images.
* Reconstruct iDPC and dDPC images from quadrant detector images or stacks (either raw A, B, C, D images or A-C, B-D images). The rotation angle can be guessed by either minimum curl or maximum contrast algorithms.

__New: 4D-STEM support__

* View and navigate the 4D data in both real space and reciprocal space
* Crop and flip data in both spaces
* Calibrate both real space and reciprocal space
* Generate virtual image from point, circle, or annular detectors with interactive and resizable ROIs
* Average diffraction patterns from selected regions in real space
* CoM, iCoM, dCoM, DPC, iDPC, and dDPC reconstruction from 4D-STEM data

TemCompanion was written by Dr. Tao Ma. The source code is published at [TemCompanion's github](https://github.com/matao1984/temcompanion). For questions, suggestions, bug reports, feature requests, etc, please send a message to [matao1984@gmail.com](mailto:matao1984@gmail.com). Also, please check the [TemCompanion's github](https://github.com/matao1984/temcompanion) for latest updates and nightly builds.



## 1. Installation
__The stand alone Win64 and MacOS ARM bundles can be downloaded from here:__
[https://github.com/matao1984/temcompanion/releases](https://github.com/matao1984/temcompanion/releases)

Written in pure python, TemCompanion can also be installed through python 3 environment on any platform. For example, if using conda, run these lines:
``conda create -n temcompanion python=3.12``

``conda activate temcompanion``

``pip install git+https://matao1984/temcompanion``

The ``pip`` should prepare all the dependencies and install the tool automatically.

## 2. Usage
The standalone executables can be run directly. If installed through python, simply type ``temcom`` in the console to start the program. The main GUI will pop up. Load the image data through the "Open Images" button. Alternatively, TemCompanion also supports dragging and dropping supported image files onto the main window to open the data. TemCompanion will try to find all the image type signals in the loaded file and open them in a separate window. All the processing and analysis functions can be called in the preview window through the menu bar, with some frequently used functions available on the toolbar. Each preview window can be individually processed, saved, and converted to the common image formats.

From version 2.0.0 TemCompanion supports 4D-STEM data. The 4D dataset can be loaded by clicking "Open 4D-STEM" button. Note that drag-and-drop function treats data as image type signals and does not work for the 4D datasets.

Also available is a batch converter, which can be called by clicking the "Batch Convert" button. A separate window will pop up which works as the old ``EMD Converter`` does. The batch converter also supports drag-and-drop actions and the loaded data and be a mix of different supported formats.

## 3. Formats
### 3.1 Input formats
Currently, TemCompanion is programmed to support:
- FEI Velox format (*.emd)
- FEI TIA format (*.ser)
- Gatan DigitalMicrograph format (*.dm3, *.dm4)
- TIFF format (*.tiff, *.tif)
    - TemCompanion will try to read the pixel calibration if exists
- MRC format (*.mrc)
    - This should be a stack of 2d images, e.g., tomography data. If the txt metadata file exists, it will be loaded as well.
- Common image formats (*.tiff, *.jpg, *.png, etc)
    - TemCompanion will try to convert the image into RGB and ignore calibration.
- Numpy Array Files (*.npy)
    - A numpy array containing only the image data. No calibration and metadata will be stored and retrieved in this format.
- Image series
    - TemCompanion will search the given folder for the supported files with the same extention as the selected file. All the image files with the same extention and match the size of the selected image will be loaded into a 3D image stack.

Supported 4D-STEM data type includes:
  - EMPAD (*.xml + *.raw)
  - USID (*.hdf5)
  - Gatan DigitalMicrograph (*.dm3, *.dm4) (Experimental)
  - py4DSTEM (*.h5, *. hdf5) (Experimental)
  - Numpy Array Files (*.npy)

- New formats can be added, given enough interests and the format is supported by ``rsciio``. A complete list of supported formats can be found [here](https://hyperspy.org/rosettasciio/supported_formats/index.html).


### 3.2 Output formats
- TIFF format
When selecting '16-bit TIFF' format, TemCompanion tries to convert the images into 16-bit tif files containing the pixel resolution, which can be read directly by Gatan DigitalMicrograph and Fiji ImageJ. Some images contain foat data, such as DPC images, EDS quantification maps, and filtered images. These images should be saved as 32-bit float by selecting '32-bit TIFF' to ensure that data is not changed. Note that 32-bit tiff files may not be handled correctly by the system picture viewers, but can be read with Gatan DigitalMicrograph and Fiji ImageJ.


- 8-bit grayscale images (TIFF, PNG, JPG)
The image data will be rescaled to 8-bit integers and saved as grayscale images. The conversion is done by pillow. The pixel calibration is not saved. A scale bar can be added if the "scale bar" option is checked in the image settings.

- Color images (TIFF, PNG, JPG)
If a color map is applied, the image should be saved in RGB format. This conversion is done by Matplotlib. The output image should look exactly the same as in the preview window. Note that some non squre images would appear with a padded white edge, which will be saved as well. It is difficult to program in the way that it fits all different aspect ratios of the input images. But by resizing the preview window it can sometimes readjust to remove the white borders.

- Pickle format
All image data and operations are handled internally as python dictionaries, which can be saved with ``pickle`` as *.pkl files. When selecting this format, the entire python dictionaries including all the data arrays, axes information, and metadata will be saved. This format is good for saving the in-processing data at any stages, as well as exchanging with other python-enabled programs, codes, notebooks, etc. This format is also available for saving 4D-STEM datasets.

- Universal Spectroscopy and Imaging Data (USID)
[USID](https://pycroscopy.github.io/USID/about.html) is an open, community-driven, self-describing, and standardized schema for representing imaging and spectroscopy data of any size, dimensionality, precision, instrument of origin, or modality. TemCompanion can save 4D-STEM dataset in this format as *.hdf5 files, which include the 4D data array, all axes, and metadata.

Note that the saving function only saves the displayed image. If working on an image stack, use the "Export as tiff stack" or "Save as series" in the stack functions to save all the frames.

## 4. Descriptions of functions

### 4.1 Basic functions

- Save as:

Calls a window to save the **Current** display into supported formats. To save the entire stack, use the save functions in the stack menu.

- Copy image to clipboard:

Take a snapshot of the **Current** display to the clipboard. The snapshot can be pasted system wide from the clipboard to PowerPoint, Word, etc. The resolution of the snapshot is determined by the **Current display resolution**.

- Image settings:

Adjust the display of image or stacks. Available options are: histogram streching, gamma correction, change color maps, add a colorbar, add a scalebar, change scalebar color and locations.

- Crop:

Crop the image by dragging a box. Alternatively, "Manual input" button allows to define the exact cropping range.

- Rotate:

Rotate the image by aligning the line ROI to horizontal. "Manual rotate" button opens a dialog to take an angle in degree. A positive angle will rotate the image counterclockwise; a negative angle will rotate clockwise. The rotated image will be padded with 0 and no cropping is performed.

- Flip:

Flip the current image either horizontally or vertically.

- Resampling:

Resample the image by a given factor. e.g., A factor of 2 will upsample a 1024x1024 image to 2048x2048; and a factor of 0.5 will downsample it to 512x512.

- Simple math:

Perform simple math on two opened images. Supported operations are: addition, subtraction, multiplication, division, and inversion. If inversion is selected, only the signal 1 will be processed and the signal 2 will be ignored.



### 4.2 Analyze functions
- Set scale:

Redefine the pixel calibration. The acceptable units for real space images are: m, cm, mm, um, μm, nm, pm. The units for reciprocal space images are 1/(real space unit).

- Measure:

Draw a line ROI on the image to measure the distance and angle. The distance will be calculated with the pixel calibration. The angle is between the line and the horizontal direction. The line position and length can be changed by dragging the end points. The start point and the end point are in yellow and blue, respectively.

- Measure angle:

Measure the angle from 3 points on the image. The angle measurement ROI can be dragged and resized freely.

- Measure diffraction/FFT:

This function allows the quick measurement of diffraction/FFT spots by dragging the circle ROI. The peak position will be fitted with a center-of-mass (CoM) function within the circle. Then its calibrated distance to the center will be calculated and converted back to the real space distance. The diameter of the circle can be changed by dragging the resize handle.

To measure the diffraction patterns correctly, the center of the diffraction patterns needs to be defined. This can be done by clicking the "Define Center" or "Define Center with Two Points" button. The former allows to drag the circle ROI on the center spot of the diffraction pattern and then fit a CoM to define the center. The latter accepts two symmetric spots selected by the circle ROIs. The mid point of the two spots will be defined as the center.

- Line profile:

Draw a line ROI on the image, and the intensity profile along the line will be extracted and plotted. The line position and length can be changed by dragging the end points. The start point and the end point are in yellow and blue, respectively. The width of the line can be changed by dragging the side handle, or clicking the "+" or "-" keys.

- Radial integration:

Extract a radial integration profile from a center that can be defined by the circle ROI. Similar to the "Define Center" function, the center spot will be fitted with a CoM function with the circle ROI, whose diameter can be changed by dragging the side handle. This function can be useful for measuring complicated diffraction patterns for polycrystalline materials.

- Geometric phase analysis (GPA)

Geometric phase analysis (GPA) is a robust technique for calculating strain maps from high-resolution images by analyzing local phase changes that provide information about the local displacements of atomic planes. TemCompanion implements two algorithms to extract the geometric phase terms from a high-resolution TEM image: standard GPA, by Hÿtch et al [1], and adaptive GPA, by de Jong et al [2] that employs a windowed Fourier ridge method [3]. The algorithm selection can be made in the setting dialog by clicking the settings button. The standard GPA is chosen by default, which runs fast and often gives reasonable enough results. The adaptive GPA runs slow, but can give smoother strain maps.

Running GPA starts with selecting reference g vectors from the FFT using the circle ROIs. By default the full image area is used to compute the reference FFT. If using a specific area as reference is desired, adjust the rectangle selector in the HRTEM image. At least two non-collinear g vectors are needed to generate strain maps, using the method described in [1]. The "Refine mask" button can be used to refine the g vector positions using a CoM function. Users can add more g vectors by clicking "Add mask" button in the toolbar. When more than two g vectors are selected, the strain maps are calculated with the least square fit using the method described here [4].

Explanation of GPA parameters:

__Standard GPA__

  - _Mask radius_: Mask size used to extract the iFFT from the selected g vectors. The masks should be big enough to avoid unrealistic results. However, too big masks can also lead to unrealistic details in the strain maps.

  - _Edge smooth_: Defines the portion of the outside edge area that will be smoothed using a cosine function to avoid edge effect in iFFT

__Adaptive GPA__

  - _Window size_: The window size for the windowed Fourier ridge algorithm to extract the geometric phase. Multiple iFFTs from the window around the g vector will be extracted and the maximum values are taken for the geometric phase.
  - _Step size_: Defines the step to compute iFFT within the window. Smaller step size means more iFFTs are calculated and hence the total processing time increases.
  - _Sigma_: The sigma of a Gaussian function that is used with the Fourier window.

__Limit Display Range__

Defines the display range for the strain maps. These can be adjusted later in the image settings.

Reference:

[1] M.J. Hÿtch, E. Snoeck, R. Kilaas. Ultramicroscopy, 74 (3) (1998), 131-146, [10.1016/S0304-3991(98)00035-7](hppts://doi.org/10.1016/S0304-3991(98)00035-7)

[2] T.A. de Jong, T. Benschop, X. Chen, E.E. Krasovskii, M.J.A. de Dood, R.M. Tromp, et al.
Nat Commun, 13 (1) (2022), 70, [10.1038/s41467-021-27646-1](https://doi.org/10.1038/s41467-021-27646-1)

[3] K. Qian, Opt Lasers Eng, 45 (2) (2007), 304-317, [10.1016/j.optlaseng.2005.10.012](https://doi.org/10.1016/j.optlaseng.2005.10.012)

[4] Tao Ma, SoftwareX, 31 (2025) 102212. [10.1016/j.softx.2025.102212](https://doi.org/10.1016/j.softx.2025.102212)

- Reconstruct DPC

The differential phase contrast (DPC) STEM technique, utilizing a segmented detector, provides a quick and accurate method for retrieving the phase shift of the exit electron wave caused by a thin specimen. TemCompanion can reconstruct iDPC and dDPC images from either 4 quadrant images or 2 images of DPCx (A - C) and DPCy (B - D) using the method described by I. Lazić [1]. In practice, the DPC signals often have an offset from the image coordinates. This rotation angle is necessary to align the DPC components with the image coordinates for correct reconstruction. This parameter is usually pre-calibrated by the TEM maker. If the rotation angle is unknown, TemCompanion offers two functions to estimate it: minimizing curl or maximizing contrast. The minimum curl method identifies the rotation angle by minimizing the curl of the DPC vector field, under the assumption that the field is conservative and the curl is always zero. The maximum contrast method computes iDPC images over a range of rotation angles (0–360 °) and selects the angle that provides maximum contrast. Note that image contrast inverts if the DPC components are off by 180 °, so the maximum contrast function provides two possible rotation angle estimates. In addition, applying a high-pass filter on the reconstructed iDPC images is usually necessary to supress the unrealisic background variation. By default the high-pass cutoff is set to 0.02, meaning the 2% of the center portion in the Fourier space will be filtered out in the reconstructed iDPC images.

Reconstruct DPC function also accepts image stacks. In this case, the reconstruction is performed for each frame. An advanced use case is to combine it with the stack alignment and integration function. This allows for the creation of fast-scanned, drift-corrected iDPC and dDPC images, which is currently not available in Velox.

Reference

[1] I. Lazić, E.G.T. Bosch, S. Lazar, Ultramicroscopy, 160 (2016), 265-280, [10.1016/j.ultramic.2015.10.011](https://doi.org/10.1016/j.ultramic.2015.10.011)



### 4.3 Fast Fourier transforms
- FFT:

Perform FFT on the current image and display in a separate window. If the image is non square, it is first padded to square with 0, from which the FFT is computed.

- Windowed FFT"

Apply a Hann window before computing the FFT to remove the edge effect.

- Live FFT:

Compute FFT from a selected square box on the image. The box ROI can be dragged and resized and the FFT will update automatically. The ROI is limited to square shape.

- Mask and iFFT (only available on FFT):

Apply one or a few pairs of circular masks on the FFT spots and compute inverse FFT. More masks can be added with the "Add" button. As the masks are dragged and/or resized, the iFFT image will be calculated on-the-fly. The edge of the masks (3/10 of the mask diameter) is smoothed by a cosine function to remove the edge effect.

### 4.4 Filter

Various filters for high-resolution (S)TEM images are implemented in TemCompanion, including Wiener filter, Average Background Substraction (ABS) filter, Non-Linear filter, Butterworth low-pass filter, and Gaussian filter, based on the [hrtem_filter](https://github.com/matao1984/hrtem_filter). The details are discussed in [1], [2], [3], and [4]. Users can apply these filters on any images with the parameters set in the "Filter settings" dialog. The parameters are explained as below:

_Delta_ for WF, ABSF, and NL: A threshold used to extract the average background from the FFT of input images. When the difference between the previous iteration and the current background is smaller than delta% the iteration will stop. A bigger delta would preserve more FFT spots and hence more crystalline information, but consumes more time. Default is 10%.

_Bw order_: When a Butterworth lowpass filter is used standalone or in combination of these filters to remove the high frequency noise, the order controls how steep the cutoff happens. Higher order gives steeper cutoff. Default is 0.3.

_Cutoff_: A fraction in Fourier space where the low-pass filter starts to taper.

_NL Cycles_: Defines how many cycles of Wiener + Gaussian low-pass filtering are performed in the Non-Linear filter. Default is 10.

_High pass Gaussian cutoff_: A fraction in Fourier space where the cutoff of high-pass filter begins. Set to 0 for no high-pass filtering. Default is 0.

_Low pass Gaussian cutoff_: A fraction in Fourier space where the low-pass filter starts to taper. Similar to the Butterworth filter. Set to 1 for no low-pass filtering.

__Note__: When both the _High pass Gaussian cutoff_ and _Low pass Gaussian cutoff_ are specified for a valid number between 0-1, a band-pass filter is performed.

[1] LD Marks, Ultramicroscopy, 62 (1996), 43. [10.1016/0304-3991(95)00085-2](https://doi.org/10.1016/0304-3991(95)00085-2)

[2] R Kilaas, J. Microscopy, 190 (1998), 45. [10.1046/j.1365-2818.1998.3070861.x](https://doi.org/10.1046/j.1365-2818.1998.3070861.x)

[3] H Du, Ultramicroscopy, 151 (2015), 62. [10.1016/j.ultramic.2014.11.012](https://doi.org/10.1016/j.ultramic.2014.11.012)

[4] T. Ma, Microsc. Microanal. 30 (2024) ozae044.213. [10.1093/mam/ozae044.213](https://doi.org/10.1093/mam/ozae044.213)

### 4.5 Stack Operations

When an image stack is open, all frames will be loaded and the first frame will be displayed, together with a slider bar to switch the frames. Presing the space key can start/stop automatic playback of all the frames with a frame time of 100 ms (10 Hz). The "," and "." keys control the forward and rewind of the stack by 1 frame. In addition, the "Stack" menu is available for stack specific operations.

- Crop stack:

Crop the entire stack from a rectangle ROI. Manual input is also allowed.

- Rotate stack:

Rotate the entire stack counterclockwise by a given angle.

- Flip stack:

Flip the entire stack horizontally or vertically.

- Resampling stack:

Resample every frame of the entire stack by a given factor. e.g., A factor of 2 will upsample a 1024x1024 image to 2048x2048; and a factor of 0.5 will downsample it to 512x512.

- Reslice stack:

Extract a slice in the way that the x is along the line ROI that can be dragged and resized, and the y is along the stack direction.

- Sort stack:

Reorder the frames of the image stack by dragging the frames in a separate dialog. The frames can also be deleted from the context menu from a mouse right click.

- Align stack with cross-correlation:

A reliable stack alignment method using the phase cross-correlation algorithm with sub-pixel precision. This is commonly adopted for aligning (S)TEM images. For periodic images, e.g., HR(S)TEM images with lattice, a Hann window should be applied to the images prior to compute the phase cross-correlation to suppress the periodic features. Users can also decide whether to crop the aligned frames to the common area with an option of cropping them to the biggest square.

The images can be normalized before running the alignment. This can be set by checking the "Normalize intensities before alignment" option.

The "Use phase correlation" option determines the normalization factor for the correlation calculation. If enabled, the correlation will be normalized by the magnitude of $FFT(ref) {\cdot}FFT(moving)^*$. Otherwise, no normalization is performed. Using phase correlation can help to reduce the impact of non-uniform contrast changes.

- Align stack with optical flow iKL

The optical flow with an iterative Lucas-Kanade (iLK) solver is a commonly used non-rigid registration algorithm. TemCompanion uses the [``skimage.registration.optical_flow_ilk``](https://scikit-image.org/docs/0.23.x/api/skimage.registration.html#skimage.registration.optical_flow_ilk). To get better results with optical flow iKL, the stack must be aligned with rigid registration to some extents.

Available parameters:

_Window size_: Radius of the window considered around each pixel. Large window captures big shifts, but may lose small details; small window on big shifts, on the other hand, leads to unrealistic displacement fields.

_Prefilter before alignment_: Whether to prefilter the estimated optical flow before each image warp. When True, a median filter with window size 3 along each axis is applied. This helps to remove potential outliers.

_Integrate with Gaussian kernel_: If checked, a Gaussian kernel is used for the local integration. Otherwise, a uniform kernel is used. This helps to smooth the displacement field.

- Integrate stack:

Average through all the frames along the stack direction.

- Export as tiff stack:

Export the current image stack as a one-file tiff stack. This file can be imported into various image processing software like ImageJ, Gatan DigitalMicrograph, etc. The pixel calibration is embedded in the tiff and can usually be read by the image processing software.

- Export as GIF animation:

Export the current image stack as gif animation. The duration of each frame can be set in the dialog. An optional label can be added to the animation, either static or dynamic with a pythonic expression with `{fn}` that denotes the frame number (starting from 1). For example, if this is a thickness stack and the thickness of each frame is 2 nm, `z = {fn*2} nm` out puts a label of "z = x nm" on each frame where x = frame number x 2. This is a good way to show the stack as movies in e.g. PowerPoint slides.

- Save as series:

Save every frame of the entire stack into a folder. The supported image formats are described in 3.2.

### 4.6 Supported 4D-STEM functions
The 4D-STEM data is displayed in two linked preview windows: a virtual image window and a diffraction window. The functions implemented are slightly different.

#### 4.6.1 Virtual image window
- File:

This menu contains "Save as", "Copy Image to Clipoard", "New Image from Display", "Image Settings", "Close", and "Close All", which work in the same way as in the image windows. The "New Image from Display" will create a copy of the current image and open it as an image signal, which has all the processing and analysis functions available.

- Process:

  - Crop: Crop the data in real-space (scan positions) by an rectangle ROI. Also supports manual input.
  - Flip Horizontal/Vertical: Flip the real-space (scan positions) accordingly.

- Analysis:

This menu contains "Set Scale", "Measure", "Measure Angle", and "Line Profile" for the current virtual image. The "Set Scale" will set the real-space pixel calibration (scan size) for the dataset.

- Detector:

  - Point: A draggable point ROI on the virtual image that specifies which scan position the diffraction window displays.
  - Rectangle: A draggable and resizable rectangle that averages the diffraction patterns in the selection and display the averaged pattern in the diffraction window.

  Note that the position of the detector ROI can be adjusted by the arrow keys. Both the detector ROI can be deleted by selecting the "Delete ROI" in the context menu by right-clicking on the detector ROI.

- FFT:

This menu contains "FFT", "Windowed FFT", and "Live FFT" that calculate the Fourier transforms from the current virtual image.

- Info:

This menu displays the image information as well as the metadata.

#### 4.6.2 Diffraction window

Most of the functions are the same as those in the virtual image window, expect in the "Detector" menu:

- Point: A draggable point ROI on the diffraction pattern from which the virtual image is calculated. As the point detector is dragged, the virtual image is updated lively.
- Circle: A draggable and resizable circular detector on the diffraction pattern from which a virtual bright/dark-field image is calculated. The virtual image is not lively updated due to the intensive computation involved, until the "Apple" button on the toolbar is clicked, or "ENTER" key is clicked. It is possible to add more circle detectors from the context menu by right-clicking on the circle.
- Annular: A draggable and resizable annular detector on the diffraction pattern from which an annular detector image, e.g., ADF, is calculated. The virtual image is not lively updated due to the intensive computation involved, until the "Apple" button on the toolbar is clicked, or "ENTER" key is clicked.
- CoM: A draggable and resizable circular detector on the diffraction pattern from which the center of mass is calculated. If the CoM is selected, a complex image formed by $CoM_x + iCoM_y$ will be displayed in the virtual image window in the "phase-magnitude" mode, in which the color represents the angle of the CoM, and the brightness of the color represents the magnitude of the CoM. For iCoM or dCoM, the integrated or differentiated CoM image will be calculated. Due to the intensive computation, the virtual image is not updated until the "Apple" button on the toolbar is clicked, or "ENTER" key is clicked.
- DPC: Same as CoM, expect that the calculation is performed from an annular detector.


## 5. Batch Convert

The Batch Convert module can be used to convert multiple images into "tiff + png", "tiff", "png", and "jpg" formats. The tiff format contains 16-bit signed integers with the pixel calibration embedded, and can be imported into other image processing software like ImageJ and Gatan DigitalMicrograph, which can read the pixel calibration. This is the most convenient way to convert emd files into GMS I have found so far.

All other formats are lossy conversion, which convert the original data into unsigned 8-bit int. These formats are good for direct use, but not ideal for image analysis as some data are lost in the conversion. Also, the pixel size information is not kept in these formats. A scale bar can be added if the "Scale bar" option is checked.

The image metadata can also be exported along with the conversion, if the "Export metadata" option is checked. The exported metadata is saved in json format that is very human-readable and can be open by most of the text editors.

Optionally, one or multiple filters can be applied to the converted images. This can be configured by clicking the "Also apply filters" button.

The Batch Convert is programmed to employ multiple threads of the CPU that can significantly speed up the conversion. By default the number of threads is set to 8 or the maximum number of the available CPU threads, whichever is smaller. While more threads give faster conversion, it is advised to preserve at least 1-2 threads to handle the normal tasks of your computer.

## 6. Default settings

Some default settings for TemCompanion are saved in the default_config.json file. If installed through pip, this file should be under the src/TemCompanion folder. For Windows bundles, it should be under ./_internal/TemCompanion folder. For the one app MacOS bundle, right click on the TemCompanion.app and select "Show package contents", then navigate to Contents/Resources/TemCompanion. The available default settings are as follows:

  "cmap": "gray", -> Default colormap for images;

  "fft_cmap": "inferno", -> Default colormap for FFTs;

  "vmin": null, -> No effect;

  "vmax": null, -> No effect;

  "pvmin": 0.1, -> Default percentile to calculate the vmin for images;

  "pvmax": 99.9, -> Default percentile to calculate the vmax for images;

  "fft_pvmin": 30, -> Default percentile to calculate the vmin for FFTs;

  "fft_pvmax": 99.9, -> Default percentile to calculate the vmax for FFTs;

  "gamma": 1.0, -> Default gamma correction;

  "scalebar": true, -> Whether to display a scalebar;

  "color": "yellow", -> Default color of the scalebar;

  "location": "lower left", -> Default position for the scalebar;

  "scale_size": 20, -> Default font size of the scalebar text;

  "dimension": "si-length", -> No effect;

  "colorbar": false, -> Whether to add a colorbar to images;

  "edgesmooth": 0.3, -> Default edge smooth factor for iFFT from masks;

  "playback_speed": 100, -> Default playback speed in ms for stack images;

  "gif_duration": 200, -> Default frame duration for gif animation;

  "alignment_precision": 0.01, -> Subpixel precision for stack alignment with cross-correlation

  "filter_parameters": -> Default filter parameters;

  "Apply WF": false, -> Whether to apply WF for batch conversion

  "WF Delta": "10",

  "WF Bw-order": "4",

  "WF Bw-cutoff": "0.3",

  "Apply ABSF": false, -> Whether to apply ABSF for batch conversion

  "ABSF Delta": "10",

  "ABSF Bw-order": "4",

  "ABSF Bw-cutoff": "0.3",

  "Apply NL": false, -> Whether to apply NL for batch conversion

  "NL Cycles": "10",

  "NL Delta": "10",

  "NL Bw-order": "4",

  "NL Bw-cutoff": "0.3",

  "Apply Bw": false, -> Whether to apply Bw for batch conversion

  "Bw-order": "4",

  "Bw-cutoff": "0.3",

  "Apply GS": false, -> Whether to apply Gaussian for batch conversion

  "GS-hp-cutoff": "0",

  "GS-cutoff": "0.3"

  "default_open": "Velox emd Files (*.emd)", -> Default file type for "Open Images";

  "default_batch_open": "Velox emd Files (*.emd)", -> Default file type for the Batch Convert;

  "default_save": "16-bit TIFF Files (*.tiff)" -> Default file type for save images.

  "gpa": -> Default settings for GPA

  "mask_r": 20, -> Default mask radius for standard GPA

  "edgesmooth": 0.3, -> Default edge smooth factor for standard GPA

  "algorithm": "standard", -> Default algorithm

  "window_size": 20, -> Window size for WFR phase retrieval for adaptive GPA

  "step_size": 4, -> Step size for WFR phase retrieval for adaptive GPA

  "sigma": 10, -> Default sigma for the Gaussian window function for adaptive GPA

  "vmin": -0.1, -> Default display lower limit for strain maps

  "vmax": 0.1 -> Default display upper limit for strain maps


## 7. Citation

If TemCompanion helped your TEM image analysis in a publication, please cite:

Tao Ma, TemCompanion: An open-source multi-platform GUI program for TEM image processing and analysis, _SoftwareX_, __2025__, 31, 102212. [doi:10.1016/j.softx.2025.102212](https://doi.org/10.1016/j.softx.2025.102212).

bibtex:
```
@article{MA2025102212,
title = {TemCompanion: An open-source multi-platform GUI program for TEM image processing and analysis},
journal = {SoftwareX},
volume = {31},
pages = {102212},
year = {2025},
doi = {10.1016/j.softx.2025.102212},
author = {Tao Ma}
}
```

## 8. Change history

See [CHANGELOG.md](https://github.com/matao1984/temcompanion/blob/main/CHANGELOG.md) for the full history.

<!-- CHANGELOG_SNIPPET_START -->

### 1.4.1[dev]
- Added support for NanoMegas ASTAR block files (*.blo)
  - The centering and distortion calibration information in the file header is saved in the metadata, but not applied.
  - The diffraction calibration is in cm/pixel. To get the correct scale in 1/nm, use scale = R / (Lλ) where:
    - R is the original calibration in cm/pixel;
    - L is the calibrated camera length in cm;
    - λ is the electron wave length in nm.
- Fixed reading DigitalMicrograph files saved in GMS 3.6.2.

### 1.4.0
- Added support for 4D-STEM data.
- Supported formats:
  - EMPAD (*.xml + *.raw)
  - USID (*.hdf5)
  - Gatan DigitalMicrograph (*.dm3, *.dm4) (Experimental)
  - py4DSTEM (*.h5, *.hdf5) (Experimental)
  - Numpy Array Files (*.npy)
- Available functions for 4D-STEM data include:
  - View and navigate the 4D data in both real space and reciprocal space
  - Crop and flip data in both spaces
  - Calibrate both real space and reciprocal space
  - Generate virtual image from point, circle, or annular detectors with interactive and resizable ROIs
  - Average diffraction patterns from selected regions in real space
  - CoM, iCoM, dCoM, DPC, iDPC, and dDPC reconstruction from 4D-STEM data

### 1.3.4
- Added support for complex images (e.g., DPC or CoM) with options for phase (default), magnitude, real, and imaginary.
- Added dialog for exporting gif animation with customizable frame time and label.
- Minor bug fixes.

### 1.3.3
- Fixed a bug in live FFT handling unit conversion.
- Fixed set scale dialog not showing the correct units.
- Changed handle colors for line ROIs to indicate the start (yellow) and end points (blue).
- Added scale size option in the scalebar settings.

### 1.3.2
- Updated `filters.gaussian_lowpass` function to take a `hp_cutoff_ratio` so it can work as low-pass, high-pass, or band-pass.
- Modified DPC reconstruction functions to use this filter for high pass. The original `gaussian_high_pass` has been dropped.
- Updated DPC reconstruction to support non-square images.
- Added a `default_config.json` file for default parameters.
- Added multiprocess support in batch conversion to speed up conversion.
- Added value validation for most input parameters to prevent crashes.
- Added angle measurement tool.
- Simplified radial integration operations.
- Added User Guide manual and linked it to the main UI.
- UI remembers the last file type for open and save dialogs.
- Fixed error in `rgb2gray` function.
- Fixed CoM encountering all-zero window in some cases.
- Improved alignment algorithms.
- Fixed incorrect FFT measurement in live FFT mode.
- Updated pyqtgraph 0.14 handling for reciprocal space unit power.
- Added reorder dialog for importing image series with custom order and deletion.
- Added rotate image and stack by aligning a line ROI to horizontal.

### 1.3.1
- Reorganized the project structure.
- Redesigned the main UI with pyqtgraph to improve rendering performance.
- Optimized operation workflow with pyqtgraph functions.
- Modified filters to support non-square images.
- Live iFFT also supports non-square images.

### 1.3.0dev
- Restructured code with DPC, GPA and filter modules separated.
- Used a separate thread for time-consuming tasks while keeping the GUI responsive.
- Added progress bar for long-running tasks.
- Fixed close event handling to delete all child widgets.
- Set output to float32 for stack alignment.
- Added save stack as gif animation.
- Added reslice stack from a line.
- Added live FFT on stacks.
- Added filters for entire image stack.
- Redesigned the slider for image stack navigation.
- Added keyboard shortcuts for stack playback (`Space`, `,`, `.`).
- Added gamma correction for image adjustment.
- Rewrote some filter functions.
- Added radial integration from a selected center.
- Added arrow-key movement for crop region, live FFT region, and FFT masks.
- iFFT filtered image now auto-updates if a mask is present.

### 1.2.6
- Fixed app crash when measuring on live FFT.
- Fixed windowed FFT not working on non-calibrated images.
- Added automatic window positioning with functions.
- Added selecting reference area for GPA.
- Added adaptive GPA with WFR algorithm.
- Improved memory consumption.

### 1.2.5
- Improved rendering speed for interactive measuring and line profile using blitting.

### 1.2.4
- Fixed incorrect data type handling in stack operations that caused app crash.
- Added save metadata option for batch conversion.

### 1.2.3
- Fixed an incorrect definition of high-pass filter in DPC reconstruction that caused UI crashes on non-square images.
- Fixed dDPC output type from `int16` to `float32`.
- Added support for *.mrc files (image stack only), including metadata txt file when present.
- Added import image series of the same type in one folder.
- Added "Sort stack" function to reorder and delete frames in a stack.
- Changed copy image shortcut to `Ctrl+Alt+C` / `Cmd+Option+C` and released `Ctrl+C` / `Cmd+C` back to system copy.

### 1.2.2
- Added right-click menu.
- Added save as 8-bit TIFF and color TIFF.
- Stack can now be exported as 8-bit/color TIFF, PNG, and JPG.
- Added image size checks before computing DPC to prevent crashes.
- Fixed the micrometer symbol display in scalebar.

### 1.2.1
- Added drag-and-drop file support in main UI and batch converter.
- Figure now tries to keep aspect ratio upon resizing in most cases.
- Added mini colorbar option at top-right corner.
- Minor bug fixes.

### 1.2
- Added diffraction pattern measurement.
- Added simple math (add, subtract, multiply, divide, inverse) on two images or stacks.
- Added iDPC and dDPC calculation from 4 or 2 images/stacks with angle input and auto-guess by minimum curl or maximum contrast.
- Fixed unit parsing for values with extra spaces (e.g., `1 / nm`).
- Added save type: 32-bit float TIFF.

### 1.1
- Added geometric phase analysis.
- Added resampling (up and down).
- Improved mode switching between measure, line profile, etc.
- Added manual vmin/vmax input with slider.
- Fixed import issues for some TIFF images with missing modules.

### 1.0
- Significant update with redesigned UI, separated from old EMD-converter.
- Batch converter function calls old EMD-converter for batch conversion.
- Added flip image and stack.
- Added custom colormap transitioning from black at zero intensity.
- Released standalone bundles for Windows x64 and macOS ARM.

### 0.6
- Fixed crop and crop stack having the same effect in stack images.
- Improved speed for interactive measurement and line profile.
- Improved measurement result display.
- Improved unit conversion between image and FFT.
- Added shortcuts for most functions.
- Added FFT mask and iFFT filtering.
- Improved image settings dialog.

### 0.5
- Made line ROIs in measurement and line-profile modes draggable and resizable.
- Added scalebar customization (on/off, color, location, etc.).
- Added copy image directly to clipboard for pasting into PowerPoint and similar apps.

### 0.4
- New feature: Live FFT with resizable window
- Added axes viewer to view image size, scale, etc.
- Hold shift key to crop a square
- Import image formats like tif, png, jpg, etc, both rgb and grayscale

### 0.3
- New feature: "Stack" menu for image stacks
  - Crop stack
  - Rotate stack
  - Export stack or series
  - Align stack with phase cross-coreelation (rigid) or optical flow iLK (non-rigid)
  - Integrate stack
  - Improved font and color for the frame slider for image stacks
- Fixed filter parameters cannot be set
- Added two low-pass filters: Butterworth and Gaussian
- Remove filter menu on FFT images

### 0.2
- New feature: Extract line profile from an image.
  - The line width can be defined.
  - Customize the plot apperance, e.g., color, xlim, ylim.
  - Measure the line profile both horizontally and vertically with mouse drag
- Added status bar at the bottom of the figure window with prompt
- Improved FFT measurement to be more robust and accurate
- Move FFT measurement function to FFT image only
- Added "Cancel" button to the crop function
- Added export metadata to json and pkl
- Added angle measurement for distance measurement

### 0.1
- First version!

<!-- CHANGELOG_SNIPPET_END -->
