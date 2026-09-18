import json
import jsonschema

class DSLValidator:
    def __init__(self, schema_path):
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
            
    def validate(self, parser_def):
        jsonschema.validate(instance=parser_def, schema=self.schema)
