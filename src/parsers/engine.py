import yaml
from .interpreter import DSLInterpreter
from .dsl_validator import DSLValidator

class ParserEngine:
    def __init__(self, parser_def_path, schema_path='p:/Univeral Log Processing/ulpf/contracts/parser_mapping.schema.json'):
        with open(parser_def_path, 'r') as f:
            self.parser_def = yaml.safe_load(f)
            
        validator = DSLValidator(schema_path)
        validator.validate(self.parser_def)
        
        self.interpreter = DSLInterpreter()

    def parse(self, raw_event):
        state = {'raw_event': raw_event}
        
        fields = self.parser_def.get('fields', {})
        for field_name, field_def in fields.items():
            result = self.interpreter.evaluate(field_def, state)
            if result is not None:
                state[field_name] = result
                
        output = {k: v for k, v in state.items() if k != 'raw_event'}
        return output
