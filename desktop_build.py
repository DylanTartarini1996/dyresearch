import PyInstaller.__main__
import os
import sys

from app import APP_NAME

base_dir = os.path.abspath(os.path.dirname(__file__))

def build():
    params = [
        os.path.join(base_dir, 'app', 'server.py'), # Entry point
        f'--name={APP_NAME}',
        '--onedir',
        '--windowed',
        '--clean',

        # Exclude massive chunks of torch
        '--exclude-module=tensorboard',
        '--exclude-module=torch.distributed',
        
        # Add the folders
        f'--add-data={os.path.join(base_dir, "app")}{os.pathsep}app',
        f'--add-data={os.path.join(base_dir, "dyresearch")}{os.pathsep}dyresearch',
        
        '--hidden-import=uvicorn',
        '--hidden-import=lancedb',
        '--collect-all=docling',
        '--collect-all=lancedb',
        '--collect-all=uvicorn',
    ]
    
    print(f"Starting PyInstaller with base_dir: {base_dir}")
    PyInstaller.__main__.run(params)

if __name__ == "__main__":
    build()