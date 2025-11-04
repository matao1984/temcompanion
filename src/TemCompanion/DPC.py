import numpy as np
from scipy.fft import fft2, fftshift, ifft2, ifftshift, fftfreq
from .filters import gaussian_lowpass, pad_to_square
# Integrate DPC function
def reconstruct_iDPC(DPCx, DPCy, rotation=0, cutoff=0.02):
    '''
    Reconstruct iDPC image from DPCx and DPCy images
    DPCx, DPCy: arrays of the same size
    rotation: float, scan rotation offset for the setup in degrees
    cutoff: float, cutoff for the high pass filter
    ref: Ivan Lazić, et al. Ultramicroscopy 160 (2016) 265–280. 
    '''
    if DPCx.ndim == 2:
        im_y, im_x = DPCx.shape
        if im_x != im_y:
            DPCx = pad_to_square(DPCx)
            DPCy = pad_to_square(DPCy)
        # Rotate the DPC vector images
        if rotation != 0:
            ang = rotation * np.pi / 180 # Convert to radian
            DPCx, DPCy = rotate_vector(DPCx, DPCy, ang)
        # Make the k grid
        qx, qy = fftfreq(DPCx.shape[1]), fftfreq(DPCx.shape[0])
        kx, ky = np.meshgrid(qx, qy)
        d1 = kx * fft2(DPCx) + ky * fft2(DPCy)
        k2 = kx**2 + ky**2
        d2 = 2 * np.pi * k2 * 1j
        d2[0,0] = np.inf
        iDPC_fft = d1 / d2
        iDPC_fftshift = fftshift(iDPC_fft)

        # Apply a Gaussian high pass filter
        if cutoff > 0 and cutoff <= 1:
            iDPC = gaussian_lowpass(iDPC_fftshift, cutoff_ratio=1, hp_cutoff_ratio=cutoff, space='fourier')
        else:
            iDPC = np.real(ifft2(fftshift(iDPC_fftshift)))
        
        iDPC = iDPC[:im_y, :im_x]  # Crop back to original size if padded
        
        
    elif DPCx.ndim == 3:
        # Calculate on an image stack
        im_z = DPCx.shape[0]
        iDPC = np.zeros(DPCx.shape)
        for i in range(im_z):
            iDPC[i,:,:] = reconstruct_iDPC(DPCx[i], DPCy[i], rotation, cutoff)
    #iDPC_int16 = iDPC.astype('int16')
    return iDPC
    
# def gaussian_high_pass(shape, cutoff=0.02):
#     # Return a Gaussian high pass filter
#     im_y, im_x = shape
#     cx, cy = im_x // 2, im_y // 2
#     X, Y = np.meshgrid(np.arange(im_x), np.arange(im_y))
#     X -= cx
#     Y -= cy
#     sigma = im_x * cutoff
#     gaussian = np.exp(-(X**2 + Y**2) / (2 * sigma ** 2))
#     return ifftshift(1 - gaussian)

# Calculate the divergence
def reconstruct_dDPC(DPCx, DPCy, rotation, cutoff=0.02, inverse=False):
    if DPCx.ndim == 2:
        # Rotate the DPC vector images
        if rotation != 0:
            ang = rotation * np.pi / 180 # Convert to radian
            DPCx, DPCy = rotate_vector(DPCx, DPCy, ang)
        dDPCx = np.gradient(DPCx, axis=1)
        dDPCy = np.gradient(DPCy, axis=0)
        dDPC = dDPCx + dDPCy
        if cutoff > 0 and cutoff < 1:
            dDPC = gaussian_lowpass(dDPC, cutoff_ratio=1, hp_cutoff_ratio=cutoff)
        if inverse:
            dDPC = -dDPC

        #dDPC -= np.min(dDPC)
    elif DPCx.ndim == 3:
        im_z = DPCx.shape[0]
        dDPC = np.zeros(DPCx.shape)
        for i in range(im_z):
            dDPC[i,:,:] = reconstruct_dDPC(DPCx[i], DPCy[i], rotation, inverse)
    #dDPC_int16 = dDPC.astype('int16')
    return dDPC

def find_rotation_ang_max_contrast(DPCx, DPCy, step=1):
    '''Try to find the scan rotation offset of DPC signals by maximizing the contrast
    DPCx, DPCy: 2d array of the same size
    step: invertal of degrees when evaluating the contrast in 0-360 degrees 
    Return: angle'''
    im_size = 256
    if DPCx.shape[0] > im_size and DPCx.shape[1] > im_size:
        # crop the input signals to save time
        x0 = (DPCx.shape[1] - im_size) // 2
        y0 = (DPCx.shape[0] - im_size) // 2
        DPCx = DPCx[y0:y0+im_size,x0:x0+im_size]
        DPCy = DPCy[y0:y0+im_size,x0:x0+im_size]
    angles1 = np.arange(0, 180, step)
    angles2 = np.arange(-180,0, step)
    contrast = []
    for ang in angles1:
        iDPC = reconstruct_iDPC(DPCx, DPCy, ang)
        contrast.append(np.std(iDPC))
    
    i_max1 = contrast.index(max(contrast))
    contrast = []
    for ang in angles2:
        iDPC = reconstruct_iDPC(DPCx, DPCy, ang)
        contrast.append(np.std(iDPC))
    i_max2 = contrast.index(max(contrast))
    return angles1[i_max1], angles2[i_max2]

def find_rotation_ang_min_curl(DPCx, DPCy, step=1):
    '''Try to find the scan rotation offset of DPC signals by minimizing the curl
    DPCx, DPCy: 2d array of the same size
    step: invertal of degrees when evaluating the curl in 0-360 degrees 
    Return: angle
    '''
    angles = np.arange(0, 360, step)
    curls = []
    for ang in angles:
        Dx, Dy = rotate_vector(DPCx, DPCy, ang*np.pi/180)
        C = curl_2d(Dx, Dy)
        curls.append(C)
        
    cost = [np.sum(c**2) for c in curls]
    i_min = cost.index(min(cost))
    return angles[i_min]    
    
def curl_2d(Fx, Fy):
    return np.gradient(Fy, axis=1) - np.gradient(Fx, axis=0)

def rotate_vector(X, Y, ang):
    '''
    X, Y: array; components of vector along x and y
    ang: rotation angle in radian
    '''
    new_X = X * np.cos(ang) - Y * np.sin(ang)
    new_Y = X * np.sin(ang) + Y * np.cos(ang)
    return new_X, new_Y