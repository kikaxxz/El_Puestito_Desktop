import os
import sys
import shutil

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_appdata_dir():
    appdata = os.getenv('APPDATA')
    app_dir = os.path.join(appdata, 'ElPuestito')
    if not os.path.exists(app_dir):
        os.makedirs(app_dir)
    return app_dir

def get_persistent_path(filename, relative_source_folder="Assets"):
    appdata_dir = get_appdata_dir()
    dest_path = os.path.join(appdata_dir, filename)
    
    if not os.path.exists(dest_path):
        source_path = os.path.join(get_base_dir(), relative_source_folder, filename)
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
    return dest_path

def get_asset_path(filename):
    return os.path.join(get_base_dir(), "Assets", filename)

def get_image_dir():
    appdata = get_appdata_dir()
    img_dir = os.path.join(appdata, 'images')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)
    return img_dir

def resolve_image_path(filename):
    # Primero busca en AppData/images
    img_dir = get_image_dir()
    appdata_path = os.path.join(img_dir, filename)
    if os.path.exists(appdata_path):
        return img_dir, filename
    
    # Si no existe, usa Assets/ (fallback para imagenes iniciales)
    return os.path.join(get_base_dir(), "Assets"), filename