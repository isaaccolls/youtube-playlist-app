import os
import json

def create_directory(path):
    """
    Crea un directorio si no existe.
    """
    if not os.path.exists(path):
        os.makedirs(path)

def read_json(file_path):
    """
    Lee un archivo JSON y devuelve su contenido.
    """
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data

def write_json(file_path, data):
    """
    Escribe un diccionario en un archivo JSON.
    """
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)