# TemCompanion
TemCompanion is a convenient and lightweight tool to view, edit, and convert TEM micrographs to the common image formats including tiff, png, and jpg. The data import is built on the ``rsciio`` module and TemCompanion is currently programmed to support FEI Velox (*.emd) format, Gatan DigitalMicrograph (*.dm3, *.dm4) format, and FEI TIA (*.ser) format. These formats cover most of the scenarios of TEM data acquisition. More formats may be added in later releases given enough interests. TemCompanion was developed based on the [EMD converter](https://github.com/matao1984/emd-converter) that was explicitly used for data convertion. On top of it, a simple data viewer has been added, together with some useful functions including rotate, crop, measure, calibrate, and FFT. These would cover most of the TEM data processing and analysis needs. Also added is filtering functions, based on the [hrtem_filter](https://github.com/matao1984/hrtem_filter). Three filter functions, including Wiener, averaging background subtraction (ABS), and non-linear filters, are made available for filtering high-resolution TEM images. 

TemCompanion was written by Dr. Tao Ma. For questions, suggestions, bug reports, feature requests, etc, please send a message to matao1984@gmail.com.

## 1. Installation
The tool requires Python 3 environment. I recommend to install Anaconda which is the most straightforward way. Download and install the Python 3 version of Anaconda from here: https://www.anaconda.com/.

After the Anaconda is installed, open the Anaconda prompt console. Download the ``temcompanion`` folder from this page or using the ``git`` tool via: ``git clone https://github.com/matao1984/temcompanion``. Then, navigate to the ``temcompanion`` folder with ``cd [PATH]`` and install with pip:

``conda create -n temcompanion python=3.12``

``conda activate temcompanion``

``pip install ./``

The ``pip`` should prepare all the dependencies and install the tool automatically.

## 2. Usage
Simply type ``temcom`` in the Anaconda prompt console. A GUI will pop up. Load the data through the "Open Files" button, view the images with the "Preview" button. All the processing and analysis functions are available in the preview window. Each preview window can be individually saved and converted to the common image formats. The tool will still work for batch convertion as ``EMD Converter`` does.

## 3. Formats
### 3.1 Input formats
Currently, TemCompanion is programmed to support FEI Velox (*.emd) format, Gatan DigitalMicrograph (*.dm3, *.dm4) format, and FEI TIA (*.ser) format. New formats can be added, given enough interests and the format is supported by ``rsciio``. A complete list of supported formats can be found [here](https://hyperspy.org/rosettasciio/supported_formats/index.html). 

### 3.2 List of available functions
Currently available functions include:
* Preview any image type signals. If the input file contains multiple image frames, a slider bar is added on the image to navigate.
* Rotate image: positive angles would rotate the image counterclockwise and vice versa. The image will expand upon rotation.
* Crop image: crop to any size with a GUI rectangle selection.
* Adjust vmin/vmax for display.
* Apply a color map to images.
* Add a scalebar and customize its color, location, etc.
* View and set the pixel scale.
* Measure distance and angle interactively by drawing a line on images.
* Extract line profiles interactively.
* Compute a fast Fourier transform directly or with a Hann window applied.
* Compute live FFT from a selected area that can be adjusted interactively.
* Apply masks on FFT and compute masked inverse FFT.
* Measure d-spacing from FFT spots. The center of FFT peaks is fitted with a center of mass function. The angle from horizontal direction is also measured.
* Apply Wiener, ABS, non-linear, Butterworth, and Gaussian filters on HRTEM/HRSTEM images. The filter parameters can be adjusted.
* View the axes information and metadata of the TEM data file.
* The processing history by TemCompanion is saved in the metadata tree under "process" entry.
* Align image stack with both phase cross-correlation (rigid) and optical flow (non rigid).
* Copy displayed images directly and paste to power point, etc.


### 3.3 Output formats
When selecting '.tiff' format, TemCompanion tries to convert the images into 16-bit tif files containing the pixel resolution, which can be read directly by Gatan DigitalMicrograph and Fiji ImageJ. Some images contain foat data, such as DPC images, EDS quantification maps, and filtered images. These images will be saved as 32-bit float to ensure that data is not changed. Note that 32-bit tiff files may not be handled correctly by the system picture viewers, but can be read with Gatan DigitalMicrograph and Fiji ImageJ. 

All image data and operations are handled as python dictionaries, which can be saved with ``pickle`` as *.pkl files. This format is good for saving the in-processing data at any stages, as well as exchanging with other python-enabled programs, codes, notebooks, etc.


Other image formats including png and jpg, both gray scale and color, are lossy conversion, which means the original data are manipulated (e.g., data are normalized and rescaled to 8-bit gray scale). These formats are good for direct use, but not ideal for image analysis as some data are lost in the conversion. Also, the pixel size information is not kept in these formats. A scale bar can be burnt on if the "Scale bar" option is checked.  


## 4. About the emd format
Velox saves all types of data, including simple images, image stacks, SI data, DPC, etc, into a single emd format. While these files share the same format, the data structures are quite different. TemCompanion has been tested for simple images, image stacks, DPC images, and EDS mapping data. For EDS mapping data, it will only read the image type signals, e.g., STEM images and quantification maps, and ignore the spectra data. For DPC data, it will read all the quadrant signals, computed signals (e.g., A-C, B-D, iDPC, dDPC, etc.), but currently will not work on the composite DPC images, which combines the DPCx and DPCy signals into complex data. Future release may fix this problem.

## 5. Citation
A paper is in preparation. Please also consider citing/acknowledging the [``rsciio``](https://hyperspy.org/rosettasciio/index.html#citing-rosettasciio).

## 6. Change history

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

- Mask in FFT and iFFT
  
- Executable App bundle for Windows and MacOS

- Better color maps for EDS maps
