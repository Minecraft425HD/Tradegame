# Configuration file for the application
# Description: This file contains the configuration for the application

import json

def load_colors(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        colors = json.load(file)
    return {name: tuple(color) for name, color in colors.items()}
