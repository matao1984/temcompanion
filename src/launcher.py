"""Launcher entry for PyInstaller bundle.
Also can be used to run the application directly from source.
"""

import sys
import os
import pickle
from TemCompanion.main import main


def setup_config():
    version = '1.3.1'
    release_date = '2025-11-02'
    if getattr(sys, 'frozen', False):
        wkdir = os.path.join(sys._MEIPASS, 'TemCompanion')
    elif __file__:
        wkdir = os.path.join(os.path.dirname(__file__), 'TemCompanion')
    colormap_path = os.path.join(wkdir, 'colormap.pkl')
    with open(colormap_path, 'rb') as f:
        colormap = pickle.load(f)

    sb_color = 'yellow'
    
    config = {
        'version': version,
        'release_date': release_date,
        'working_directory': wkdir,
        'colormap': colormap,
        # Some default image settings
        'cmap': 'gray',
        'fft_cmap': 'inferno',
        'vmin': None,
        'vmax': None,
        'pvmin': 0.1,
        'pvmax': 99.9,
        'fft_pvmin': 30,
        'fft_pvmax': 99.9,
        'gamma': 1.0,
        'scalebar': True,
        'color': sb_color,
        'location': 'lower left',
        'dimension': 'si-length',
        'colorbar': False
    }
    return config




if __name__ == "__main__":
    config = setup_config()
    main(config)