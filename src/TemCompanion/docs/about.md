# About TemCompanion

TemCompanion is an open-source, multi-platform GUI program for TEM image processing and analysis, developed by Dr. Tao Ma. For questions, suggestions, bug reports, feature requests, etc, please send a message to [matao1984@gmail.com](mailto:matao1984@gmail.com).

Visit the [GitHub repository](https://github.com/matao1984/temcompanion) for source code, releases, and contributions.

## Latest release

<p>Latest stable version: <span id="latest-release-version" aria-live="polite">Checking GitHub&hellip;</span>.
<br>
<a href="https://github.com/matao1984/temcompanion/releases/latest" target="_blank" rel="noopener noreferrer">View latest release</a>.</p>
<noscript>Enable JavaScript to display the version and release date, or use the release link above.</noscript>

## Support

Your support is important! <a href="https://paypal.me/matao1984?country.x=US&amp;locale.x=en_US" target="_blank" rel="noopener noreferrer">Buy me a coffee</a> if you like it!

## Change History

<!-- CHANGELOG_SNIPPET_START -->

### 1.4.2
- Fixed a bug in loading stack images with 3d arrays caused by the construction of color wheel.
- Fixed incorrect positions for stack reslicing.
- For image stacks, determine the contrast limits based on the entire stack data.
- Fixed auto range adds 1 blank pixel on the image.
- Added HDF5Loader dialog to explore and open any dataset saved in hdf5 format.
- Drag-and-drop behavior has been changed: images and 4D datasets can be dropped onto the Open Image/4D-STEM buttons.

### 1.4.1
- All 4D-STEM processing was changed to lazy operations with Dask arrays by default.
- Added support for NanoMegas ASTAR block files (*.blo)
  - The centering and distortion calibration information in the file header is saved in the metadata, but not applied.
  - The diffraction calibration is in cm/pixel. To get the correct scale in 1/nm, use scale = R / (Lλ) where:
    - R is the original calibration in cm/pixel;
    - L is the calibrated camera length in cm;
    - λ is the electron wave length in nm.
- Fixed reading DigitalMicrograph files saved in GMS 3.6.2.
- Added indicators on image when measuring peaks from line profile.
- Save numpy files with metadata saved in json.

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

<!-- CHANGELOG_SNIPPET_END -->
See the [full change history](User%20Guide.md#8-change-history) for earlier releases.
