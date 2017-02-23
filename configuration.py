import json
import os

from jsonschema import validate

SELF_PATH = os.path.dirname(os.path.realpath(__file__))
SETTINGS = json.loads(open(os.path.join(SELF_PATH, "cfg.json")).read())


schema = {
    "title": "Config",
    "type": "object",
    "properties": {
        "translate-key": {
            "type": "string",
        },
        "mailer": {
            "type": "object",
            "properties": {
                    "server": {"type": "string"},
                    "port": {"type": "number"},
                    "sender": {"type": "string"},
                },
            "required": ["server", "port", "sender"],
        },
        "sendto": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "minItems": 1,
                "uniqueItems": True,
            }

    },
    "required": ["mailer", "sendto"]
}


validate(SETTINGS, schema)