import re
import json
from .exceptions import UnsupportedOperationError, ParserDefinitionError

class DSLInterpreter:
    def __init__(self):
        pass

    def evaluate(self, field_def, state):
        op = field_def.get('op')
        source_key = field_def.get('source')
        
        # Whitelist of allowed operations
        _allowed_ops = {
            'extract', 'cast', 'lookup', 'parse_timestamp', 'extract_regex',
            'extract_json', 'extract_kv', 'extract_csv', 'drop'
        }
        
        if op not in _allowed_ops:
            raise UnsupportedOperationError(f"Unsupported operation: {op}")

        if source_key not in state and source_key != 'raw_event':
            return None
            
        val = state.get(source_key) if source_key != 'raw_event' else state.get('raw_event', '')
        if val is None:
            return None

        if op == 'extract_regex':
            pattern = field_def.get('pattern')
            if not pattern:
                raise ParserDefinitionError("Missing 'pattern' for extract_regex")
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
            if not target_type:
                raise ParserDefinitionError("Missing 'type' for cast")
            try:
                if target_type == 'integer':
                    return int(val)
                elif target_type == 'boolean':
                    return str(val).lower() in ('true', '1', 't', 'y', 'yes', 'syn')
                elif target_type == 'string':
                    return str(val)
                else:
                    raise ParserDefinitionError(f"Unsupported cast type: {target_type}")
            except (ValueError, TypeError):
                return None
                
        elif op == 'lookup':
            values = field_def.get('values')
            if values is None or not isinstance(values, dict):
                raise ParserDefinitionError("Missing or invalid 'values' dictionary for lookup")
            return values.get(str(val))
            
        elif op == 'extract':
            return val
            
        elif op == 'parse_timestamp':
            fmt = field_def.get('format')
            if not fmt:
                raise ParserDefinitionError("Missing 'format' for parse_timestamp")
            try:
                from datetime import datetime
                dt = datetime.strptime(str(val), fmt)
                return dt.isoformat()
            except Exception:
                return None

        elif op == 'extract_json':
            try:
                return json.loads(str(val))
            except Exception:
                return None

        elif op == 'extract_kv':
            sep = field_def.get('separator')
            if not sep:
                raise ParserDefinitionError("Missing 'separator' for extract_kv")
            kv_str = str(val)
            result = {}
            for part in kv_str.split(sep):
                if '=' in part:
                    k, v = part.split('=', 1)
                    result[k.strip()] = v.strip()
            return result

        elif op == 'extract_csv':
            sep = field_def.get('separator')
            if not sep:
                raise ParserDefinitionError("Missing 'separator' for extract_csv")
            return str(val).split(sep)

        elif op == 'drop':
            return None

        raise UnsupportedOperationError(f"Operation {op} missing implementation handler")
