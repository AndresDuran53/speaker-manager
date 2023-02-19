import json 

class ConfigurationReader():

    fileName = "configuration.json"

    def __init__(self):
        pass

    def read_config_file(self):
        with open(self.fileName, "r") as jsonfile:
            data = json.load(jsonfile)
            jsonfile.close()
        return data
