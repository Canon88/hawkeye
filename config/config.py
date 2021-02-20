import os
import json
import yaml

class Config():
    def __init__(self):
        pass

    def load(self, file):
        with open(file, 'r', encoding="utf-8") as f:
            config = f.read()
            config = yaml.safe_load(config)
            return config


if __name__ == '__main__':
    config = Config()
    data = config.load('config.yaml')
    print(json.dumps(data))