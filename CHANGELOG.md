# Changelog

All notable changes to this project are documented in this file.

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
