import json

class JsonCreator:
    def __init__(self, data):
        self.data = data

    def create_json(self, filename):
        with open(filename, 'w') as json_file:
            json.dump(self.data, json_file)

    def add_to_json(self, filename, new_data):
        with open(filename, 'r+') as json_file:
            data = json.load(json_file)
            data.update(new_data)
            json_file.seek(0)
            json.dump(data, json_file)