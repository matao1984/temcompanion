#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPA module 
"""
import numpy as np
from scipy.fft import fft2, fftshift, ifft2, ifftshift
from scipy.ndimage import fourier_gaussian
from scipy.ndimage import center_of_mass
from numba import njit, prange
from .functions import norm_img

#===== GPA functions ==================================
# Conventional GPA
def get_phase_fft(img, k, r, edge_blur=0.3):
    '''Calculate phase from masked iFFT image
    Bansed on Hÿtch 1998
    r : int
        Size of the circular mask to place over the reflection
    edge_blur : float, optional
        Fraction of pixels at the edge that will be smoothed by a cosine function.
    '''
    im_y, im_x = img.shape
    cx, cy = im_x // 2, im_y // 2
    x = np.arange(im_x)
    y = np.arange(im_y)
    X, Y = np.meshgrid(x, y)
    
    # calculate the fft and mask only on one side
    fft = fftshift(fft2(img)) 
    kx, ky = k
    # need to calculate the coordinates for mask
    x = int(kx * im_x + cx)
    y = int(ky * im_y + cy)
    m = create_mask((im_y, im_x), [(x, y)], [r], edge_blur)
    fft_m = fft * m
    # calculate complex valued ifft
    ifft_m = ifft2(ifftshift(fft_m))
    # raw phase 
    phifft_m = np.angle(ifft_m)
    # corrected phase  
    P = phifft_m - 2*np.pi*(kx*X+ky*Y)
    return P
    
    
def calc_strains(P, ks):
    """
    Calculate strain with two g vectors and phases
    P : numpy array of phase image (2,m,n)
    ks: k vectors (2, 2)
    Returns
    -------
    im_exx : numpy array
        The epsilon_xx strain component 
    im_eyy : numpy array
        The epsilon_yy strain component 
    im_exy : numpy array
        Epsilon_yx = (epsilon_yx), the shear strain
    im_oxy : numpy array
        omega_xy = -omega_yx, the rotation component
    """
    # Calculate the phase derivatives

    dP1dy = calc_derivative(P[0,:,:], 0) 
    dP1dx = calc_derivative(P[0,:,:], 1)
    dP2dy = calc_derivative(P[1,:,:], 0)
    dP2dx = calc_derivative(P[1,:,:], 1)
    
    # calculate lattice points a1 and a2    
    [a1x, a2x], [a1y, a2y] = np.linalg.inv(ks)
    
    # the strain components
    exx = -1/(2*np.pi)*(a1x*dP1dx+a2x*dP2dx)
    exy = -1/(2*np.pi)*(a1x*dP1dy+a2x*dP2dy)
    eyx = -1/(2*np.pi)*(a1y*dP1dx+a2y*dP2dx)
    eyy = -1/(2*np.pi)*(a1y*dP1dy+a2y*dP2dy)
    
    Exy = (exy + eyx) / 2
    oxy = (exy - eyx) / 2

    return exx, eyy, Exy, oxy



def create_mask(img_size, center, radius, edge_blur=0.3):
    '''
    Generate a circle mask from a given point and radius
    img_size: tuple of original (FFT) image size
    center: list of tuple of the mask center
    radius: lisf of float of the radius in pixel, length must be equal to center
    edge_width: fload of the smoothed edge in pixel
    '''      
    # Create a grid of coordinates
    Y, X = np.ogrid[:img_size[0], :img_size[1]]
    mask = np.zeros(img_size, dtype=float) 
    
    for i in range(len(center)):
        x_center, y_center = center[i]
        r = radius[i]
        
        # Calculate the Euclidean distance from each grid point to the circle's center
        distance = np.sqrt((X - x_center)**2 + (Y - y_center)**2)
        
        edge_width = r * edge_blur
        # Create the base circle mask: inside the circle is 1, outside is 0
        inside_circle = (distance <= r - edge_width)
        outside_circle = (distance >= r)
    
        # Transition zone
        transition_zone = ~inside_circle & ~outside_circle
        
        # Smooth edge with a cosine function

        transition_distance = (distance - r) / edge_width
        transition_mask = 0.5 * (1 + np.cos(np.pi * transition_distance))
    
        # Combine masks
        mask[inside_circle] = 1
        mask[transition_zone] = transition_mask[transition_zone]

    return mask


def refine_center(img, g, r):
    '''
    Refine the g vector center with center of mass
    g: tuple of (x, y)
    r: radius for window size
    '''
    window_size = r
    x = int(g[0])
    y = int(g[1])
    x_min = max(x - window_size, 0)
    x_max = min(x + window_size, img.shape[1])
    y_min = max(y - window_size, 0)
    y_max = min(y + window_size, img.shape[0])

    window = img[y_min:y_max, x_min:x_max]

    # Convert the window to binary with a threshold to make CoM more accurate
    threshold = np.mean(window) + 1.5 * np.std(window)
    binary_image = window > threshold

    # Calculate the center of mass within the window
    cy, cx = center_of_mass(binary_image)
    cx += x_min
    cy += y_min
    return cx, cy

def calc_derivative(arr, axis):
    """
    Calculate the derivative of a phase image.
    """
    s1 = np.exp(-1j*arr)
    s2 = np.exp(1j*arr)
    d1 = np.gradient(s2, axis=axis) 
    #nd = np.min(d1.shape)
    dP1x = s1 * d1
    return dP1x.imag




@njit(parallel=True, fastmath=True)
def extract_strain_lstsqr(g, dPdx, dPdy):
    """
    g: (n,2) array of g-vectors
    dPdx, dPdy: (n,m,m) phase derivatives
    Solve Exx, Exy, Eyx, Eyy via least squares using normal equations (Numba-safe).
    """
    n = g.shape[0]
    m = dPdx.shape[1]

    # Outputs
    Exx = np.zeros((m, m), dtype=np.float64)
    Exy = np.zeros((m, m), dtype=np.float64)
    Eyx = np.zeros((m, m), dtype=np.float64)
    Eyy = np.zeros((m, m), dtype=np.float64)

    # Precompute normal equation matrices for the two 2x2 systems
    # System 1: [gx, gy] * [Exx, Exy]^T = b0
    # System 2: [gx, gy] * [Eyx, Eyy]^T = b1
    
    # M = sum_k [[gx^2, gx*gy], [gx*gy, gy^2]] is shared for both systems
    M00 = 0.0
    M01 = 0.0
    M11 = 0.0
    
    for k in range(n):
        gx = g[k, 0]
        gy = g[k, 1]
        M00 += gx * gx
        M01 += gx * gy
        M11 += gy * gy
    
    # Invert M (2x2 symmetric matrix)
    det = M00 * M11 - M01 * M01
    if abs(det) < 1e-18:
        # Degenerate case - use identity to avoid crash
        invM00 = 1.0
        invM01 = 0.0
        invM11 = 1.0
    else:
        inv_det = 1.0 / det
        invM00 = M11 * inv_det
        invM01 = -M01 * inv_det
        invM11 = M00 * inv_det

    c = -1.0 / (2.0 * np.pi)

    # Parallelize over pixels
    for i in prange(m):
        for j in range(m):
            # Build RHS vectors for the two systems
            # System 1: gx * Exx + gy * Exy = c * dPdx
            rhs0_0 = 0.0  # sum_k gx * c * dPdx[k,i,j]
            rhs0_1 = 0.0  # sum_k gy * c * dPdx[k,i,j]
            
            # System 2: gx * Eyx + gy * Eyy = c * dPdy
            rhs1_0 = 0.0  # sum_k gx * c * dPdy[k,i,j]
            rhs1_1 = 0.0  # sum_k gy * c * dPdy[k,i,j]
            
            for k in range(n):
                gx = g[k, 0]
                gy = g[k, 1]
                
                b0 = c * dPdx[k, i, j]
                b1 = c * dPdy[k, i, j]
                
                rhs0_0 += gx * b0
                rhs0_1 += gy * b0
                
                rhs1_0 += gx * b1
                rhs1_1 += gy * b1
            
            # Solve M * [Exx, Exy]^T = [rhs0_0, rhs0_1]^T
            exx = invM00 * rhs0_0 + invM01 * rhs0_1
            exy_ = invM01 * rhs0_0 + invM11 * rhs0_1
            
            # Solve M * [Eyx, Eyy]^T = [rhs1_0, rhs1_1]^T
            eyx = invM00 * rhs1_0 + invM01 * rhs1_1
            eyy = invM01 * rhs1_0 + invM11 * rhs1_1
            
            Exx[i, j] = exx
            Exy[i, j] = exy_
            Eyx[i, j] = eyx
            Eyy[i, j] = eyy

    # Symmetric shear and rotation
    exy = (Exy + Eyx) * 0.5
    Oxy = (Eyx - Exy) * 0.5
    
    return Exx, Eyy, exy, Oxy

# Adaptive GPA with Windowed Fourier Ridge phase retrieval
def get_phase_wfr(img, g, sigma, window_size, step):
    '''
    Calculate the phase from HRTEM image with a given g vector
    using the Windowed Fourier ridge technique.
    Algorithm explained in K Qian, Optics and Lasers in Engineering 45.2 (2007): 304-317.
    https://doi.org/10.1016/j.optlaseng.2005.10.012
    Codes adopted from pyGPA originated from:
    T.A. de Jong et al. Nat Commun 13, 70 (2022)
    https://doi.org/10.1038/s41467-021-27646-1
    Parameters:
    img: image array
    g: g vector coordinates in its FFT
    sigma: for Gaussian filter
    window_size: window size for wfr algorithm, in pixel
    step: step size in pixel for wfr
    Returns: phase as numpy array with the same size of img'''
    
    # Compute k vectors
    im_y, im_x = img.shape
    kx, ky = g
    xx, yy = np.meshgrid(np.arange(im_x), np.arange(im_y))
    
    # Compute window size and step
    kw = window_size * 1 / im_x
    kstep = step * 1 / im_x
    
    g = {'phase': np.zeros_like(img),
         'r': np.zeros_like(img),
         }
    for wx in np.arange(kx-kw, kx+kw, kstep):
        for wy in np.arange(ky-kw, ky+kw, kstep):
            multiplier = np.exp(np.pi*2j * (xx*wx + yy*wy))
            X = fft2(img * multiplier)
            sf = ifft2(fourier_gaussian(X, sigma=sigma))           
            sf *= np.exp(-2j*np.pi*((wx-kx)*xx+(wy-ky)*yy))
            t = np.abs(sf) > g['r']
            g['r'][t] = np.abs(sf)[t]
            g['phase'][t] = np.angle(sf)[t]
    phase = -g['phase']# Mysterious minus sign
    return phase

# Put together one function overall
def GPA(img, g, algorithm='standard', r=20, edge_blur=0.3, sigma=10, window_size=10, step=4):
    '''Top level GPA function
    img: np array of square shape m x m
    g: list of reference g coordinates n x 2
        when n = 2, use standard GPA to calculate strain tensors
        when n > 2, use least square fit to solve the stain tensors
    algorithm: 
        'standard': perform standard GPA by retrieving phases from masked iFFT 
        Ref: M. Hÿtch, E. Snoeck, R. Kilaas, Ultramicroscopy 74 (1998) 131–146.
        'adaptive': perform adaptive GPA by retrieving phase using WFR
        Ref: 
        K Qian, Optics and Lasers in Engineering 45.2 (2007): 304-317.
        T.A. de Jong et al. Nat Commun 13, 70 (2022)
    r: int, mask radius used for standard GPA
    edge_blur: float between 0-1, Fraction of pixels at the edge that will be smoothed by a cosine function. 
    sigma: float, sigma of the Gaussian window for WFT
    window_size: int, window size for WFR
    step: int, step for WFR
    Return: strain tensors with the same size of img
    '''
    # Normalize the input image
    img = norm_img(img)
    im_y, im_x = img.shape
    n = len(g)
    # FFT center coordinates
    cx, cy = im_x // 2, im_y // 2 
    
    P = np.zeros((n, im_y, im_x))
    dPdx = np.zeros((n, im_y, im_x))
    dPdy = np.zeros((n, im_y, im_x))
    ks = np.zeros((n,2))
    
    # Calculate the phase from the g vector list
    for i in range(n):
        x, y = g[i]
        ks[i] = (x-cx)/im_x, (y-cy)/im_y
        
        if algorithm == 'standard':
            P[i,:,:] = get_phase_fft(img, ks[i], r, edge_blur)
        else:
            P[i,:,:] = get_phase_wfr(img, ks[i], sigma, window_size, step)
        
        #Calculate the phase derivative
        dPdx[i,:,:] = calc_derivative(P[i,:,:], axis=1)
        dPdy[i,:,:] = calc_derivative(P[i,:,:], axis=0)
    
    # Calculate the strain tensors
    if n > 2:
        # use least square fit
        exx, eyy, exy, oxy = extract_strain_lstsqr(ks, dPdx, dPdy)
    else:
        # use standard method
        exx, eyy, exy, oxy = calc_strains(P, ks)
    return exx, eyy, exy, oxy


def renormalize_phase(P):
    r = (P+np.pi) % (2*np.pi) - np.pi
    return r
    



