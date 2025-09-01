# variables_config.py
# Description: This file contains the variables used in the project

import json

def load_variables(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            variables = json.load(file)
        return variables

def save_variables(file_path, variables):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(variables, file, indent=4)
