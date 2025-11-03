# Gaussian Highpass Filter Implementation

## Summary
A Gaussian highpass filter has been successfully implemented in TemCompanion to enhance high-frequency features in images, particularly useful for improving the depiction of iDPC (integrated Differential Phase Contrast) images.

## Changes Made

### 1. Core Filter Implementation (`filters.py`)
- **Added `gaussian_highpass()` function** (lines 79-97)
  - Implements a Gaussian highpass filter in the Fourier domain
  - Uses the inverse of the Gaussian lowpass filter: `1 - exp(-(r²)/(2σ²))`
  - Supports non-square images through automatic padding
  - Default cutoff ratio: 0.02 (suitable for iDPC images)

### 2. Filter Registration (`functions.py`)
- **Updated `apply_filter()` function**
  - Added 'Gaussian-HP' to the filter dictionary
  - Configured to handle the new filter type alongside existing filters
  
- **Updated file saving functions**
  - Modified `save_file_as()` to support `apply_gaussian_hp` parameter
  - Updated `save_as_tif16()` to export Gaussian HP filtered TIFF files
  - Updated `save_with_pil()` to export Gaussian HP filtered images with scalebars

### 3. User Interface Updates

#### Main Application (`main.py`)
- Added default parameter: `"GS-HP-cutoff": "0.02"`

#### Canvas/Toolbar (`canvas.py`)
- **Added menu item**: Filter → Apply Gaussian high pass (Ctrl+Shift+H)
- **Added toolbar button**: Gaussian Highpass Filter with tooltip
- **Implemented `gaussian_highpass_filter()` method**
  - Follows the same pattern as other filters
  - Supports both single images and image stacks
  - Runs in separate thread to keep UI responsive
  - Displays progress bar during processing

#### Filter Settings Dialog (`UI_elements.py`)
- **Added Gaussian Highpass section in `FilterSettingDialog`**
  - Input field for cutoff parameter
  - Helpful tooltip explaining usage for iDPC images
  
- **Updated `FilterSettingBatchConvert`**
  - Added checkbox to enable/disable Gaussian HP filtering
  - Added configuration group for Gaussian HP parameters
  - Integrated with batch conversion workflow

### 4. Batch Conversion Support (`batch_convert.py`)
- Added `apply_gaussian_hp` flag initialization
- Updated filter parameter handling
- Modified `BatchConversionWorker` to pass Gaussian HP parameters
- Integrated with batch file conversion pipeline

## Usage

### Interactive Filtering
1. Open an image in TemCompanion
2. Go to **Filter** → **Apply Gaussian high pass** (or use Ctrl+Shift+H)
3. The filter will use the cutoff value from Filter Settings
4. For image stacks, you can choose to apply to current frame or entire stack

### Adjusting Filter Parameters
1. Go to **Filter** → **Filter Settings**
2. Scroll to "Gaussian Highpass Filter Settings" section
3. Adjust the "Gaussian HP cutoff" value:
   - **Lower values** (e.g., 0.01-0.03): Preserve more high frequencies - better for subtle features
   - **Higher values** (e.g., 0.05-0.10): More aggressive highpass - removes more low frequencies
   - **Default: 0.02** - optimized for iDPC images

### Batch Processing
1. Open **Batch Conversion** window
2. Click **Also Apply Filters**
3. Check "Apply Gaussian Highpass Filter"
4. Configure cutoff parameter if needed
5. Add files and convert - filtered versions will be saved with "_Gaussian_HP" suffix

## Technical Details

### Filter Mathematics
The Gaussian highpass filter is implemented in Fourier space:
```
H(r) = 1 - exp(-r²/(2σ²))
```
Where:
- `r` is the radial distance from the center in Fourier space
- `σ = image_size × cutoff_ratio`
- Lower cutoff values preserve more high frequencies

### Why Gaussian Highpass for iDPC?
iDPC (integrated Differential Phase Contrast) images often contain:
- **Low-frequency artifacts** from integration and reconstruction
- **Phase ramps** and background variations
- **Valuable high-frequency features** representing material structure

The Gaussian highpass filter:
- Removes smooth background variations
- Enhances edges and fine structures
- Preserves phase information at higher frequencies
- Uses smooth frequency rolloff (unlike hard cutoff filters)

### Performance Considerations
- Non-square images are automatically padded to square before FFT
- Original dimensions are restored after filtering
- Filter runs in separate thread to maintain UI responsiveness
- Progress bar indicates processing status

## File Structure
Modified files:
```
temcompanion/src/TemCompanion/
├── filters.py              # Core filter implementation
├── functions.py            # Filter application and file I/O
├── main.py                 # Default parameters
├── canvas.py               # UI and menu integration
├── UI_elements.py          # Dialog components
└── batch_convert.py        # Batch processing support
```

## Testing Recommendations
1. Test on iDPC images with different cutoff values (0.01 - 0.10)
2. Compare with existing Gaussian lowpass filter
3. Test on both square and non-square images
4. Verify batch conversion with multiple filters enabled
5. Test on image stacks (apply to single frame vs. entire stack)

## Future Enhancements
- Add visual preview of filter effect in settings dialog
- Implement frequency space visualization
- Add preset configurations for different imaging modes
- Consider adaptive cutoff based on image statistics
