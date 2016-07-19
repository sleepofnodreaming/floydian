import json
import os

SELF_PATH = os.path.dirname(os.path.realpath(__file__))
SETTINGS = json.loads(open(os.path.join(SELF_PATH, "cfg.json")).read()) # todo add config validation.