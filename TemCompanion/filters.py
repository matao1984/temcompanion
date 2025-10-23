import numpy as np
from scipy.fft import fft2, fftshift, ifftshift, ifft2
from scipy.signal import medfilt2d
from numba import njit, prange

# Crop the input images if they are not square
def crop_to_square(img):
    y, x = img.shape
    if x > y:
        new_start = int((x - y) / 2)
        new_end = new_start + y 
        img_crop = img[:,new_start:new_end]
    else:
        new_start = int((y - x) / 2)
        new_end = new_start + x 
        img_crop = img[new_start:new_end,:]
    return img_crop

def pad_to_square(img):
    '''
    Pad the input images to be square by adding zeros on the right and bottom sides
    '''
    # Get current dimensions
    rows, cols = img.shape

    # Determine the maximum dimension
    max_dim = max(rows, cols)

    # Calculate padding for rows and columns
    row_padding = max_dim - rows
    col_padding = max_dim - cols

    # Apply padding using np.pad()
    # Pad bottom for rows, and right for columns
    padded_arr = np.pad(img, ((0, row_padding), (0, col_padding)), mode='constant', constant_values=0)

    return padded_arr




# For radial integration, convert image indices to polar coordinates
def img_to_polar(img):
    # Feed an image array, generate a polar indices array 
    y, x = np.indices(img.shape)
    center = img.shape[0] // 2, img.shape[1] // 2
    x = x - center[0]
    y = y - center[1]
    rho = np.hypot(y, x) # calculate sqrt(x**2 + y**2)
    #rho = rho.astype(int) # Convert rho to int for simplicity
    #phi = np.arctan2(y, x) # Don't need this    
    return rho # rho is the radial distance

# Gaussian low pass filter
def gaussian_lowpass(img, cutoff_ratio):
    """
    img: image array to be filtered, must be square
    cutoff_ratio: cutoff ratio in frequency domain
    """
    img_shape = img.shape
    if img_shape[0] != img_shape[1]:
        img = pad_to_square(img)
    r = img_to_polar(img)
    
    # Compute the FFT to find the frequency transform
    fshift = fftshift(fft2(img))

    # Calculate the cutoff frequency
    cutoff = img.shape[0] * cutoff_ratio
    
    # Create Gaussian mask
    gaussian_filter = np.exp(- (r**2) / (2 * (cutoff**2)))
    
    # Apply the filter to the frequency domain representation of the image
    filtered_fshift = fshift * gaussian_filter

    # Apply the inverse FFT to return to the spatial domain
    img_glp = ifft2(ifftshift(filtered_fshift)).real
    img_glp = img_glp[:img_shape[0], :img_shape[1]]
    return img_glp

# Butterworth lowpass filter
def bw_lowpass(img, order, cutoff_ratio):
    """
    img: image array to be filtered, must be square
    order: Butterworth order
    cutoff_ratio: cutoff ratio in frequency domain
    """
    img_shape = img.shape
    if img_shape[0] != img_shape[1]:
        img = pad_to_square(img)
    r = img_to_polar(img) # Convert to polar indices
    bw = 1/(1+0.414*(r/(cutoff_ratio * r.shape[0]))**(2*order))
    
    # Compute the FFT to find the frequency transform
    fshift = fftshift(fft2(img))

    # Apply the filter to the frequency domain representation of the image
    filtered_fshift = fshift * bw

    # Apply the inverse FFT to return to the spatial domain
    img_bw = ifft2(ifftshift(filtered_fshift)).real
    img_bw = img_bw[:img_shape[0], :img_shape[1]]
    return img_bw

# Radial integration
def radial_integration(img, bin=1, return_masks = False):
    # Get the polar indices array
    r = img_to_polar(img)

    r_max = np.max(r)
    # Get the bin indices for each pixel
    bins = np.arange(0, r_max+bin, bin)
    bin_indices = np.digitize(r, bins) - 1
    bins = bins[:img.shape[0]//2] # Limit the bins to half the image size
    # Sum values in each bin
    radial_profile = np.bincount(bin_indices.flatten(), weights=img.flatten(), minlength=len(bins))
    radial_profile = radial_profile[:len(bins)-1]
    
    
    # # Sum the image values within each bin
    # radial_profile = np.array([img[bin_indices == i].mean() for i in range(len(bins)-1)])

    if return_masks:
        # Create masks for each bin
        bin_range = np.arange(len(bins)-1)
        masks = (bin_indices == bin_range[:, None, None])
        # masks = np.zeros((len(bins)-1, img.shape[0], img.shape[1]), dtype=bool)
        # for i in range(len(bins)-1):
        #     masks[i][bin_indices == i] = True
        return bins[:-1], radial_profile, masks
    else:
        return bins[:-1], radial_profile


# Function to get an averaged background from a real-space HR image

def get_avg_background(img, delta=5):
    """
    img: 2D array of real-space HR image data
    delta: a threashold for background averaging
    """
    # Get the polar indices array
    #r = img_to_polar(img)
    y, x = np.indices(img.shape)
    center = (img.shape[0] + 1) / 2, (img.shape[1] +1 ) / 2
    x = x - center[0]
    y = y - center[1]
    r = np.hypot(y, x)

    # Get a Butterworth filter on image to remove the edge effect
    noedgebw = 1/(1+0.414*(r/(0.4 * r.shape[0]))**(2*12))
    noedgeimg = img * noedgebw
    f_noedge = fftshift(fft2(noedgeimg))
    # Light filter the FFT for processing
    f_mag = medfilt2d(np.abs(f_noedge),kernel_size=5)

    # Get the radial integration and masks

    _, f_mean, masks = radial_integration(f_mag, return_masks=True)
        
    f_mag = remove_peaks_bin(f_mag, masks, f_mean, delta=delta)

    return f_mag


@njit(parallel=True, fastmath=True)
def remove_peaks_bin(img, masks, means, delta=5):
    """
    Optimized version that pre-extracts ROI coordinates for faster iteration.
    """
    delta_factor = 1.0 + delta / 100.0
    img_out = img.copy()
    
    for i in prange(len(means)):
        if means[i] <= 0:
            continue
            
        mask = masks[i]
        mean_val = means[i] * delta_factor
        diff_pc = np.inf
        iter_count = 0
        max_iter = 100
        
        # Extract ROI data
        roi = []
        roi_coords = []
        for y in range(mask.shape[0]):
            for x in range(mask.shape[1]):
                if mask[y, x]:
                    roi.append(img[y, x])
                    roi_coords.append((y,x))
        
        if not roi:
            continue  # Skip empty masks
        
        while diff_pc > delta and mean_val > 0 and iter_count < max_iter:
            sum_roi = 0
            count = len(roi_coords)
            for point in roi:            
                if point > mean_val:
                    point = mean_val
                sum_roi += point
            # Calculate new mean
            new_mean = (sum_roi / count) * delta_factor
            
            # Calculate percentage difference
            if mean_val > 1e-10:
                diff_pc = abs((new_mean - mean_val) / mean_val) * 100.0
            else:
                diff_pc = 0.0
            
            mean_val = new_mean
            iter_count += 1

        # Write the final mean value to the image
        for coord in roi_coords:
            y, x = coord
            img_out[y, x] = mean_val
    
    return img_out


# Wiener filter function
def wiener_filter(img, delta=5, lowpass=True, lowpass_cutoff=0.3, lowpass_order=2):
    """
    Wiener filter for HRTEM images
    img: the image data array
    delta: a threashold for background averaging
    lowpass: also apply a lowpass filter after filtering
    lowpass_cutoff: a cutoff ratio in frequency domain for the lowpass
    lowpass_order: order for the Butterworth filter; smaller int retults more tapered cutoff
    Return: filtered image array and difference
    """
    img_shape = img.shape
    if img_shape[0] != img_shape[1]:
        img = pad_to_square(img)

    f_img = fftshift(fft2(img))
    fu = np.abs(f_img)
    fa = get_avg_background(img, delta=delta)
    fu_squared = np.square(fu)
    fa_squared = np.square(fa)
    wf = (fu_squared - fa_squared)/fu_squared
    wf[wf<0] = 0
    f_img_wf = f_img * wf
    img_wf_padded = ifft2(ifftshift(f_img_wf)).real
    img_wf = img_wf_padded[:img_shape[0], :img_shape[1]]
    img = img[:img_shape[0], :img_shape[1]]
    if lowpass:
        img_wf = bw_lowpass(img_wf, lowpass_order, lowpass_cutoff)
    img_wf = np.single(img_wf)
    img_diff = img - img_wf
    return img_wf, img_diff
    
# Average background subtraction filter function
def abs_filter(img, delta=5, lowpass=True, lowpass_cutoff=0.3, lowpass_order=2):
    """
    ABS filter for HRTEM images
    img: the image data array
    delta: a threashold for background averaging
    lowpass: also apply a lowpass filter after filtering
    lowpass_cutoff: a cutoff ratio in frequency domain for the lowpass
    lowpass_order: order for the Butterworth filter; smaller int retults more tapered cutoff
    Return: filtered image array and difference
    """
    img_shape = img.shape
    if img_shape[0] != img_shape[1]:
        img = pad_to_square(img)
    f_img = fftshift(fft2(img))
    fu = np.abs(f_img)
    fa = get_avg_background(img, delta=delta)
    absf = (fu - fa)/fu
    absf[absf<0] = 0
    f_img_absf = f_img * absf
    img_absf = ifft2(ifftshift(f_img_absf)).real
    img_absf = img_absf[:img_shape[0], :img_shape[1]]
    img = img[:img_shape[0], :img_shape[1]]
    if lowpass:
        img_absf = bw_lowpass(img_absf, lowpass_order, lowpass_cutoff)
    img_absf = np.single(img_absf)
    img_diff = img - img_absf
    return img_absf, img_diff


# Nonlinear filter function            
def nlfilter(img, N=50, delta=10, lowpass_cutoff=0.3, lowpass = True, lowpass_order=2):
    """
    Non-linear filter
    img: img 2D-array
    N: number of iterations
    lowpass_cutoff: cutoff of the low pass filter
    lowpass: apply a Butterworth lowpass filter after Wiener filter
    The Butterworth filter will use lowpass_order and lowpass_cutoff
    Return: filtered image array and difference
    """
    img_shape = img.shape
    if img_shape[0] != img_shape[1]:
        img = pad_to_square(img)
    x_in = img
    i=0
    while i < N:
        x_lp = gaussian_lowpass(x_in, lowpass_cutoff)
        x_diff = x_in - x_lp
        x_diff_wf, _ = wiener_filter(x_diff, 
                                     delta=delta,
                                     lowpass=lowpass, 
                                     lowpass_cutoff=lowpass_cutoff, 
                                     lowpass_order=lowpass_order)
        x_in = x_lp + x_diff_wf
        i = i+1

    img_filtered = x_in[:img_shape[0], :img_shape[1]]
    img_filtered = np.single(img_filtered) # Convert to 32 bit float
    img = img[:img_shape[0], :img_shape[1]]
    img_diff = img - img_filtered
    return img_filtered, img_diff
