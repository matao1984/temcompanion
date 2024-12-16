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
Currently, TemCompanion is programmed to support FEI Velox (*.emd) format, Gatan DigitalMicrograph (*.dm3, *.dm4) format, and FEI TIA (*.ser) format. New formats can be added, given enough interests and the format is supported by ``rsciio``. A complete list of supported formats can be found [here: ](https://hyperspy.org/rosettasciio/supported_formats/index.html). 

### 3.2 Output formats
When selecting '.tif' format, the software converts the images into 16-bit tif files containing the pixel resolution. The "Scale bar" option is ignored for this format. For DigitalMicrograph users, you can simply drag the converted tif files into GMS, which should be able to read the data including the pixel size losslessly. This is the most convenient way to convert emd files into GMS I have found so far.

All other formats are lossy conversion, which convert the original data into unsigned 8-bit int. These formats are good for direct use, but not ideal for image analysis as some data are lost in the conversion. Also, the pixel size information is not kept in these formats. A scale bar can be added if the "Scale bar" option is checked. 

## 4. About the emd format
Velox saves all types of data, including simple images, image stacks, SI data, DPC, etc, into a single emd format. While these files share the same format, the data structures are quite different. This converter has been tested for simple images, image stacks, DPC images, and EDS mapping data. For simple images, the converter just makes the conversion in the selected output directory. For image stacks and DPC images, the converter first makes a folder with the file name and converts all the image frames into that folder. For EDS mapping data, the converter converts all the image data, e.g., maps for each element, and ignores the spectra data.

## 5. Change history
### v0.3
- Improved UI.

### v0.2
- Improved font settings in MacOS.
- Now only DCFI type and EDS map files will be saved in a separate folder.
- Add "tif + png" option that converts to both tif (16 bit) and png formats.
- If conversion fails on one file, e.g., the file is locked by Velox, it skips the file and continue to the next one.

### v0.1
- First version!
