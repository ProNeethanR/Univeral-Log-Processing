import re
import json

class DSLInterpreter:
    def __init__(self):
        pass

    def evaluate(self, field_def, state):
        op = field_def.get('op')
        source_key = field_def.get('source')
        
        # If the source is not in state, and it's not raw_event, we drop it
        if source_key not in state and source_key != 'raw_event':
            return None
            
        val = state.get(source_key) if source_key != 'raw_event' else state.get('raw_event', '')
        if val is None:
            return None

        if op == 'extract_regex':
            pattern = field_def.get('pattern')
            if not pattern:
                return None
            match = re.search(pattern, str(val))
            if match:
                if 'val' in match.groupdict():
                    return match.group('val')
                if len(match.groups()) > 0:
                    return match.group(1)
                return match.group(0)
            return None
            
        elif op == 'cast':
            target_type = field_def.get('type')
            try:
                if target_type == 'integer':
                    return int(val)
                elif target_type == 'boolean':
                    return str(val).lower() in ('true', '1', 't', 'y', 'yes', 'syn')
                elif target_type == 'string':
                    return str(val)
            except (ValueError, TypeError):
                return None
                
        elif op == 'lookup':
            values = field_def.get('values', {})
            return values.get(str(val))
            
        elif op == 'extract':
            return val
            
        elif op == 'drop':
            return None

        return None
