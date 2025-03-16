# TemCompanion
TemCompanion is a convenient and lightweight tool to view, edit, and convert TEM micrographs to the common image formats including tiff, png, and jpg. The data import is built on the ``rsciio`` module and TemCompanion is currently programmed to support FEI Velox (*.emd) format, Gatan DigitalMicrograph (*.dm3, *.dm4) format, FEI TIA (*.ser) format, MRC format, and common image formats including TIFF, PNG, and JPG. These formats cover most of the scenarios of TEM data acquisition. More formats may be added in later releases given enough interests. TemCompanion was orignally developed based on the [EMD converter](https://github.com/matao1984/emd-converter) that was explicitly used for data convertion. On top of it, a simple data viewer has been added, together with some useful functions including rotate, crop, measure, calibrate, and FFT. These would cover most of the TEM data processing and analysis needs. Also added is filtering functions, based on the [hrtem_filter](https://github.com/matao1984/hrtem_filter). In addition, it supports the above operations on image stacks. A full list of available functions is as follows:

# List of available functions
* Preview any image type signals. If the input file contains multiple image frames, a slider bar is added on the image to navigate.
* Rotate image: positive angles would rotate the image counterclockwise and vice versa. The image will expand upon rotation.
* Crop image: crop to any size with a GUI rectangle selection.
* Adjust vmin/vmax for display.
* Apply a color map to images.
* Add a scalebar and customize its color, location, etc.
* View and set the pixel scale.
* Measure distance and angle interactively by drawing a line on images.
* Extract line profiles interactively.
* Simple math on two images or stacks: addition, subtraction, multiplication, division, and inversion.
* Compute a fast Fourier transform directly or with a Hann window applied.
* Compute live FFT from a selected area that can be adjusted interactively.
* Apply masks on FFT and compute masked inverse FFT.
* Measure d-spacing from FFT or diffraction patterns. The spot position is fitted with a center of mass function. The angle from horizontal direction is also measured.
* Apply Wiener, ABS, non-linear, Butterworth, and Gaussian filters on HRTEM/HRSTEM images. The filter parameters can be adjusted.
* View the axes information and metadata of the TEM data file.
* The processing history by TemCompanion is saved in the metadata tree under "process" entry.
* Import image series from a folder.
* Crop, rotate, flip, resampling, and export stack images.
* Reorder and delete frames of a stack.
* Align image stack with both phase cross-correlation (rigid) and optical flow (non rigid).
* Copy displayed images directly and paste to power point, etc.
* Run geometric phase analysis on HR(S)TEM images.
* Reconstruct iDPC and dDPC images from quadrant detector images or stacks (either raw A, B, C, D images or A-C, B-D images). The rotation angle can be guessed by either minimum curl or maximum contrast algorithms.

TemCompanion was written by Dr. Tao Ma. For questions, suggestions, bug reports, feature requests, etc, please send a message to matao1984@gmail.com.

## 1. Installation
__The stand alone Win64 and MacOS ARM bundles can be downloaded from here:__
[https://github.com/matao1984/temcompanion/releases](https://github.com/matao1984/temcompanion/releases)

Written in pure python, TemCompanion can also be installed through python 3 environment on any platform. For example, if using conda, run these lines:
``conda create -n temcompanion python=3.12``

``conda activate temcompanion``

``pip install git+https://matao1984/temcompanion``

The ``pip`` should prepare all the dependencies and install the tool automatically.

## 2. Usage
The standalone executables can be run directly. If installed through python, simply type ``temcom`` in the console to start the program. The main GUI will pop up. Load the data through the "Open Images" button. Alternatively, TemCompanion also supports dragging and dropping supported files onto the main window to open the data. TemCompanion will try to find all the image type signals in the loaded file and open them in a separate window. All the processing and analysis functions can be called in the preview window through either the menu bar or right click on the image canvas. Each preview window can be individually processed, saved, and converted to the common image formats. 

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
- Common image formats (*.tiff, *.jpg, *.png, etc) ,
    - TemCompanion will try to convert the image into RGB and ignore calibration.
- Image series
    - TemCompanion will search the given folder for the supported files with the same extention as the selected file. A dialog will then pop up that allows to reorder and delete files to be loaded. Then all files will be loaded as a 3D image stack.

- New formats can be added, given enough interests and the format is supported by ``rsciio``. A complete list of supported formats can be found [here](https://hyperspy.org/rosettasciio/supported_formats/index.html). 


### 3.2 Output formats
- TIFF format
When selecting '16-bit TIFF' format, TemCompanion tries to convert the images into 16-bit tif files containing the pixel resolution, which can be read directly by Gatan DigitalMicrograph and Fiji ImageJ. Some images contain foat data, such as DPC images, EDS quantification maps, and filtered images. These images should be saved as 32-bit float by selecting '32-bit TIFF' to ensure that data is not changed. Note that 32-bit tiff files may not be handled correctly by the system picture viewers, but can be read with Gatan DigitalMicrograph and Fiji ImageJ. 


- 8-bit grayscale images (TIFF, PNG, JPG)
The image data will be rescaled to 8-bit integers and saved as grayscale images. The conversion is done by pillow. The pixel calibration is not saved. A scale bar can be added if the "scale bar" option is checked in the image settings.

- Color images (TIFF, PNG, JPG)
If a color map is applied, the image should be saved in RGB format. This conversion is done by Matplotlib. The output image should look exactly the same as in the preview window. Note that some non squre images would appear with a padded white edge, which will be saved as well. It is difficult to program in the way that it fits all different aspect ratios of the input images. But by resizing the preview window it can sometimes readjust to remove the white borders.

- Pickle format
All image data and operations are handled internally as python dictionaries, which can be saved with ``pickle`` as *.pkl files. When selecting this format, the entire python dictionaries including all the data arrays, axes information, and metadata will be saved. This format is good for saving the in-processing data at any stages, as well as exchanging with other python-enabled programs, codes, notebooks, etc.

Note that the saving function only saves the displayed image. If working on an image stack, use the "Export as tiff stack" or "Save as series" in the stack functions to save all the frames.

## 4. Descriptions of functions

### 4.1 Basic processing functions
- Crop:
Crop the image by dragging a box. Alternatively, "Manual input" button allows to define the exact cropping range.
- Rotate:
Rotate the image by the given angle in degree. A positive angle will rotate the image counterclockwise; a negative angle will rotate clockwise. The rotated image will be padded with 0 and no cropping is performed.
- Flip:
Flip the current image either horizontally or vertically.
- Resampling:
Resample the image by a given factor. e.g., A factor of 2 will upsample a 1024x1024 image to 2048x2048; and a factor of 0.5 will downsample it to 512x512.
- Simple math:
Perform simple math on two opened images. Supported operations are: addition, subtraction, multiplication, division, and inversion. If inversion is selected, only the signal 1 will be processed and the signal 2 will be ignored.

### 4.2 Fast Fourier transforms
- FFT
Perform FFT on the current image and display in a separate window. If the image is non square, the FFT is computed from the biggest square cropped from the image.
- Windowed FFT
Apply and Hann window before computing the FFT to remove the edge effect.
- Live FFT
Compute FFT from a selected square box on the image. The box can be dragged and resized and the FFT will update automatically.
- Mask and iFFT (only available on FFT)
Apply one or a few pairs of circular masks on the FFT spots and compute inverse FFT. The red circle is the active mask and can be dragged by mouse or resized by scrolling. The yellow circle is the mirrored mask of the red and will update automatically. More masks can be added with the "Add" button. When another pair of masks is added, which will be set to active mask automatically, the previous active mask will turn to orange color. The orange masks can be reactivated by clicking on them. When the "iFFT" button is clicked, an image will be computed from the masked region using inverse FFT. The edge of the masks is smoothed by a cosine function to remove the edge effect.

### 4.3 Analyse functions
- Set scale
Redefine the pixel calibration. The acceptable units for real space images are: m, cm, mm, um, &#03BCm, nm, pm. The units for reciprocal space images are 1/(real space unit).


## 4. About the emd format
Velox saves all types of data, including simple images, image stacks, SI data, DPC, etc, into a single emd format. While these files share the same format, the data structures are quite different. TemCompanion has been tested for simple images, image stacks, DPC images, and EDS mapping data. For EDS mapping data, it will only read the image type signals, e.g., STEM images and quantification maps, and ignore the spectra data. For DPC data, it will read all the quadrant signals, computed signals (e.g., A-C, B-D, iDPC, dDPC, etc.), but currently will not work on the composite DPC images, which combines the DPCx and DPCy signals into complex data. Since this type of images is rarely used, there is currently no plan to include it in TemCompanion, unless there's enough interest in the future.

## 5. Citation
A paper is in preparation. Please also consider citing/acknowledging the [``rsciio``](https://hyperspy.org/rosettasciio/index.html#citing-rosettasciio).

## 6. Change history

### v1.2.3
- Fixed an incorrect definition of high pass filter in DPC reconstruction that caused the UI to crash on non-square images.
- Fixed dDPC output was set to 'int16' instead of 'float32'.
- Add support for *.mrc file (image stack only). If the metadata txt file exists, it will be loaded as well.
- New feature: import image series of the same type in one folder
- New feature: "Sort stack" function to reorder and delete frames in a stack
- Change copy image shortcut to ctrl+alt+c or cmd+option+c and release ctrl+c/cmd+c to system copy shortcut

### v1.2.2
- Add right click menu
- Add save as 8-bit tiff and color tiff
- Stack can also be exported as 8-bit tiff and color tiff, png, and jpg
- Added check for the image sizes when computing DPC to prevent crashing
- Fixed letter $\mu$ in micrometer scale bar cannot display correctly.

### v1.2.1
- Support drag and drop file(s) into the main UI or the batch converter
- Figure tries to keep the aspect ratio upon resizing (for the most of the cases)
- A mini colorbar can be added to the top right corner
- Minor bug fixes...

  
### v1.2
- New feature: Measure diffraction pattern
- New feature: Simple math of add, subtract, multiply, divide, inverse on two images or stacks
- New feature: Calculate iDPC and dDPC from 4 or 2 images or stacks with a given angle. The rotation angle can be guessed by either min curl or max contrast.
- Bug fix: units in some data are not recogonized due to extra space, such as '1 / nm'.
- Added save as type: 32-bit float TIFF

### v1.1
- New Features: Geometric phase analysis
- New function: resampling (both up and down)
- Improved mode switching between measure, line profile, etc.
- Manual input vmin vmax together with the slider bar
- Fixed some tif images cannot be imported with missing modules
  
### v1.0
- Significant update with redesigned UI. Now it is separated from the old EMD-converter.
- Batch converter function calls the old Emd-converter and runs batch conversion.
- Added flip image and stack
- Added custom color map for colors to transition from black at 0 intensity
- Standalone bundles for Windows x64 and MacOS ARM are available, which do not require a python environment and installation.

### v0.6
- Fixed crop and crop stack have the same effect in stack images
- Improved speed for interactive measurement and line profile
- Improved measurement results displaying
- Improved units convertion between image and FFT. Now can compute FFT from uncalibrated images and diffraction patterns.
- Added shortcuts for most of the functions
- Added mask and ifft filtering
- Improved image setting dialog

### v0.5
- The line in measuurement and lineprofile modes can be dragged and resized interactively.
- Added scalebar customization: turn on/off, color, location, etc.
- Copy image directly to the clipboard and paste in Power Point, etc.

### v0.4
- New feature: Live FFT with resizable window
- Added axes viewer to view image size, scale, etc.
- Hold shift key to crop a square
- Import image formats like tif, png, jpg, etc, both rgb and grayscale

### v0.3
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


### v0.2
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

### v0.1
- First version!

## 7. Working on list
- <del> Export metadata

- <del> Angle measurement in measure mode

- <del> Improve FFT peak measurement accuracy

- <del> Extract line profile 

- <del> Image registration

- <del> Live FFT with interactive area selection

- <del> Mask in FFT and iFFT
  
- <del> Executable App bundle for Windows and MacOS

- <del> Better color maps for EDS maps

