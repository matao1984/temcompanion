import sys
import os
import pickle
from .main import main

def setup_config():
    version = '1.3.0'
    release_date = '2025-11-01'
    if getattr(sys, 'frozen', False):
        wkdir = os.path.join(sys._MEIPASS, 'TemCompanion')
    elif __file__:
        wkdir = os.path.dirname(__file__)
    colormap_path = os.path.join(wkdir, 'colormap.pkl')
    with open(colormap_path, 'rb') as f:
        colormap = pickle.load(f)
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
        'color': 'yellow',
        'location': 'lower left',
        'dimension': 'si-length',
        'colorbar': False
    }
    return config




if __name__ == "__main__":
    config = setup_config()
    main(config)