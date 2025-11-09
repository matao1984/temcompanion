import sys
import os
import pickle
import json
from .main import main as app_entry
from multiprocessing import freeze_support

# Default configuration setup
def setup_config():
    version = '1.3.2dev'
    release_date = '2025-11-09'
    if getattr(sys, 'frozen', False):
        wkdir = os.path.join(sys._MEIPASS, 'TemCompanion')
    elif __file__:
        wkdir = os.path.dirname(__file__)
    colormap_path = os.path.join(wkdir, 'colormap.pkl')
    config_path = os.path.join(wkdir, 'default_config.json')
    with open(colormap_path, 'rb') as f:
        colormap = pickle.load(f)

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    config['version'] = version
    config['release_date'] = release_date
    config['working_directory'] = wkdir
    config['colormap'] = colormap

    return config


def main():
    freeze_support()
    config = setup_config()
    app_entry(config)



if __name__ == "__main__":
    main()