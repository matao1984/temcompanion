# TemCompanion
TemCompanion is a convenient and lightweight tool to view, edit, and convert TEM micrographs to the common image formats including tiff, png, and jpg. The data import is built on the ``rsciio`` module and TemCompanion is currently programmed to support FEI Velox (*.emd) format, Gatan DigitalMicrograph (*.dm3, *.dm4) format, and FEI TIA (*.ser) format. These formats cover most of the scenarios of TEM data acquisition. More formats may be added in later releases given enough interests. TemCompanion was developed based on the [EMD converter](https://github.com/matao1984/emd-converter) that was explicitly used for data convertion. On top of it, a simple data viewer has been added, together with some useful functions including rotate, crop, measure, calibrate, and FFT. These would cover most of the TEM data processing and analysis needs. Also added is filtering functions, based on the [hrtem_filter](https://github.com/matao1984/hrtem_filter). Various filter functions, including Wiener, averaging background subtraction (ABS), non-linear filter, Butterworth low-pass, and Gaussian filter, are made available for filtering high-resolution TEM images.

TemCompanion was written by Dr. Tao Ma. For questions, suggestions, bug reports, feature requests, etc, please send a message to matao1984@gmail.com.

## 1. Installation
__New! The stand alone Win64 and MacOS ARM bundles are available. Download from here:__
[https://github.com/matao1984/temcompanion/releases](https://github.com/matao1984/temcompanion/releases)

The tool requires Python 3 environment. I recommend to install Anaconda which is the most straightforward way. Download and install the Python 3 version of Anaconda from here: https://www.anaconda.com/.

After the Anaconda is installed, open the Anaconda prompt console. Download the ``temcompanion`` folder from this page or using the ``git`` tool via: ``git clone https://github.com/matao1984/temcompanion``. Then, navigate to the ``temcompanion`` folder with ``cd [PATH]`` and install with pip:

```
conda create -n temcompanion python=3.12

conda activate temcompanion

pip install ./
```

The ``pip`` should prepare all the dependencies and install the tool automatically.

## 2. Usage
Simply type ``temcom`` in the Anaconda prompt console. A GUI will pop up. Load the data through the "Open Files" button, view the images with the "Preview" button. All the processing and analysis functions are available in the preview window. Each preview window can be individually saved and converted to the common image formats. The tool will still work for batch convertion as ``EMD Converter`` does.

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
- Common image formats (*.tiff, *.jpg, *.png, etc) ,
    - TemCompanion will try to convert the image into RGB and ignore calibration.
- Image series
    - TemCompanion will search the given folder for the supported files with the same extention as the selected file. A dialog will then pop up that allows to reorder and delete files to be loaded. Then all files will be loaded as a 3D image stack.

- New formats can be added, given enough interests and the format is supported by ``rsciio``. A complete list of supported formats can be found [here](https://hyperspy.org/rosettasciio/supported_formats/index.html).

### 3.2 List of available functions
Currently available functions on image data include:
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

Currently available functions on 4D-STEM data:
* View and navigate the 4D data in both real space and reciprocal space
* Crop and flip data in both spaces
* Calibrate both real space and reciprocal space
* Generate virtual image from point, circle, or annular detectors with interactive and resizable ROIs
* Average diffraction patterns from selected regions in real space
* CoM, iCoM, dCoM, DPC, iDPC, and dDPC reconstruction from 4D-STEM data




### 3.3 Output formats
When selecting '16-bit TIFF' format, TemCompanion tries to convert the images into 16-bit tif files containing the pixel resolution, which can be read directly by Gatan DigitalMicrograph and Fiji ImageJ. Some images contain foat data, such as DPC images, EDS quantification maps, and filtered images. These images should be saved as 32-bit float by selecting '32-bit TIFF' to ensure that data is not changed. Note that 32-bit tiff files may not be handled correctly by the system picture viewers, but can be read with Gatan DigitalMicrograph and Fiji ImageJ.

All image data and operations are handled as python dictionaries, which can be saved with ``pickle`` as *.pkl files. This format is good for saving the in-processing data at any stages, as well as exchanging with other python-enabled programs, codes, notebooks, etc.


Other image formats including png and jpg, both gray scale and color, are lossy conversion, which means the original data are manipulated (e.g., data are normalized and rescaled to 8-bit gray scale). These formats are good for direct use, but not ideal for image analysis as some data are lost in the conversion. Also, the pixel size information is not kept in these formats. A scale bar can be burnt on if the "Scale bar" option is checked.


## 4. About the emd format
Velox saves all types of data, including simple images, image stacks, SI data, DPC, etc, into a single emd format. While these files share the same format, the data structures are quite different. TemCompanion has been tested for simple images, image stacks, DPC images, and EDS mapping data. For EDS mapping data, it will only read the image type signals, e.g., STEM images and quantification maps, and ignore the spectra data. For DPC data, it will read all the quadrant signals, computed signals (e.g., A-C, B-D, iDPC, dDPC, etc.). Now it also reads the complex DPC images and display it in a phase-magnitude color map. Users can also choose to display magnitude, real and imaginary part only, available in image settings.

## 5. Citation
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

## 6. Change history

<!-- CHANGELOG_SNIPPET_START -->

## [2.0.0]
- Added support for 4D-STEM data.
- Supported formats:
  - EMPAD (*.xml + *.raw)
  - USID (*.hdf5)
  - Gatan DigitalMicrograph (*.dm3, *.dm4) (Experimental)
  - py4DSTEM (*.h5, *.hdf5) (Experimental)
- Available functions for 4D-STEM data include:
  - View and navigate the 4D data in both real space and reciprocal space
  - Crop and flip data in both spaces
  - Calibrate both real space and reciprocal space
  - Generate virtual image from point, circle, or annular detectors with interactive and resizable ROIs
  - Average diffraction patterns from selected regions in real space
  - CoM, iCoM, dCoM, DPC, iDPC, and dDPC reconstruction from 4D-STEM data

## [1.3.4]
- Added support for complex images (e.g., DPC or CoM) with options for phase (default), magnitude, real, and imaginary.
- Added dialog for exporting gif animation with customizable frame time and label.
- Minor bug fixes.

## [1.3.3]
- Fixed a bug in live FFT handling unit conversion.
- Fixed set scale dialog not showing the correct units.
- Changed handle colors for line ROIs to indicate the start (yellow) and end points (blue).
- Added scale size option in the scalebar settings.

## [1.3.2]
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

## [1.3.1]
- Reorganized the project structure.
- Redesigned the main UI with pyqtgraph to improve rendering performance.
- Optimized operation workflow with pyqtgraph functions.
- Modified filters to support non-square images.
- Live iFFT also supports non-square images.

## [1.3.0dev]
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

## [1.2.6]
- Fixed app crash when measuring on live FFT.
- Fixed windowed FFT not working on non-calibrated images.
- Added automatic window positioning with functions.
- Added selecting reference area for GPA.
- Added adaptive GPA with WFR algorithm.
- Improved memory consumption.

## [1.2.5]
- Improved rendering speed for interactive measuring and line profile using blitting.

## [1.2.4]
- Fixed incorrect data type handling in stack operations that caused app crash.
- Added save metadata option for batch conversion.

## [1.2.3]
- Fixed an incorrect definition of high-pass filter in DPC reconstruction that caused UI crashes on non-square images.
- Fixed dDPC output type from `int16` to `float32`.
- Added support for *.mrc files (image stack only), including metadata txt file when present.
- Added import image series of the same type in one folder.
- Added "Sort stack" function to reorder and delete frames in a stack.
- Changed copy image shortcut to `Ctrl+Alt+C` / `Cmd+Option+C` and released `Ctrl+C` / `Cmd+C` back to system copy.

## [1.2.2]
- Added right-click menu.
- Added save as 8-bit TIFF and color TIFF.
- Stack can now be exported as 8-bit/color TIFF, PNG, and JPG.
- Added image size checks before computing DPC to prevent crashes.
- Fixed the micrometer symbol display in scalebar.

## [1.2.1]
- Added drag-and-drop file support in main UI and batch converter.
- Figure now tries to keep aspect ratio upon resizing in most cases.
- Added mini colorbar option at top-right corner.
- Minor bug fixes.

## [1.2]
- Added diffraction pattern measurement.
- Added simple math (add, subtract, multiply, divide, inverse) on two images or stacks.
- Added iDPC and dDPC calculation from 4 or 2 images/stacks with angle input and auto-guess by minimum curl or maximum contrast.
- Fixed unit parsing for values with extra spaces (e.g., `1 / nm`).
- Added save type: 32-bit float TIFF.

## [1.1]
- Added geometric phase analysis.
- Added resampling (up and down).
- Improved mode switching between measure, line profile, etc.
- Added manual vmin/vmax input with slider.
- Fixed import issues for some TIFF images with missing modules.

## [1.0]
- Significant update with redesigned UI, separated from old EMD-converter.
- Batch converter function calls old EMD-converter for batch conversion.
- Added flip image and stack.
- Added custom colormap transitioning from black at zero intensity.
- Released standalone bundles for Windows x64 and macOS ARM.

## [0.6]
- Fixed crop and crop stack having the same effect in stack images.
- Improved speed for interactive measurement and line profile.
- Improved measurement result display.
- Improved unit conversion between image and FFT.
- Added shortcuts for most functions.
- Added FFT mask and iFFT filtering.
- Improved image settings dialog.

## [0.5]
- Made line ROIs in measurement and line-profile modes draggable and resizable.
- Added scalebar customization (on/off, color, location, etc.).
- Added copy image directly to clipboard for pasting into PowerPoint and similar apps.

## [v0.4]
- New feature: Live FFT with resizable window
- Added axes viewer to view image size, scale, etc.
- Hold shift key to crop a square
- Import image formats like tif, png, jpg, etc, both rgb and grayscale

## [v0.3]
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

## [v0.2]
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

## [v0.1]
- First version!

<!-- CHANGELOG_SNIPPET_END -->
