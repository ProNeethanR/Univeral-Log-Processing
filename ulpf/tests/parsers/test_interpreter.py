import pytest
from src.parsers.interpreter import DSLInterpreter
from src.parsers.exceptions import UnsupportedOperationError, ParserDefinitionError

def test_extract_valid():
    interpreter = DSLInterpreter()
    state = {"raw_event": "test"}
    field_def = {"op": "extract", "source": "raw_event"}
    assert interpreter.evaluate(field_def, state) == "test"

def test_extract_invalid_input():
    interpreter = DSLInterpreter()
    state = {}
    field_def = {"op": "extract", "source": "missing_field"}
    assert interpreter.evaluate(field_def, state) is None

def test_cast_valid():
    interpreter = DSLInterpreter()
    state = {"status_code": "200"}
    field_def = {"op": "cast", "source": "status_code", "type": "integer"}
    assert interpreter.evaluate(field_def, state) == 200

def test_cast_malformed():
    interpreter = DSLInterpreter()
    state = {"status_code": "200"}
    field_def = {"op": "cast", "source": "status_code"}
    with pytest.raises(ParserDefinitionError, match="Missing 'type' for cast"):
        interpreter.evaluate(field_def, state)

def test_cast_invalid_input():
    interpreter = DSLInterpreter()
    state = {"status_code": "not_an_int"}
    field_def = {"op": "cast", "source": "status_code", "type": "integer"}
    assert interpreter.evaluate(field_def, state) is None

def test_lookup_valid():
    interpreter = DSLInterpreter()
    state = {"severity": "1"}
    field_def = {
        "op": "lookup", 
        "source": "severity", 
        "values": {"1": "High", "2": "Medium"}
    }
    assert interpreter.evaluate(field_def, state) == "High"

def test_lookup_malformed():
    interpreter = DSLInterpreter()
    state = {"severity": "1"}
    field_def = {"op": "lookup", "source": "severity"}
    with pytest.raises(ParserDefinitionError, match="Missing or invalid 'values' dictionary"):
        interpreter.evaluate(field_def, state)

def test_lookup_invalid_input():
    interpreter = DSLInterpreter()
    state = {"severity": "3"}
    field_def = {
        "op": "lookup", 
        "source": "severity", 
        "values": {"1": "High", "2": "Medium"}
    }
    assert interpreter.evaluate(field_def, state) is None

def test_parse_timestamp_valid():
    interpreter = DSLInterpreter()
    state = {"time": "2024-01-01 12:00:00"}
    field_def = {"op": "parse_timestamp", "source": "time", "format": "%Y-%m-%d %H:%M:%S"}
    assert interpreter.evaluate(field_def, state) == "2024-01-01T12:00:00"

def test_parse_timestamp_malformed():
    interpreter = DSLInterpreter()
    state = {"time": "2024-01-01 12:00:00"}
    field_def = {"op": "parse_timestamp", "source": "time"}
    with pytest.raises(ParserDefinitionError, match="Missing 'format' for parse_timestamp"):
        interpreter.evaluate(field_def, state)

def test_parse_timestamp_invalid_input():
    interpreter = DSLInterpreter()
    state = {"time": "invalid_date"}
    field_def = {"op": "parse_timestamp", "source": "time", "format": "%Y-%m-%d"}
    assert interpreter.evaluate(field_def, state) is None

def test_extract_regex_valid():
    interpreter = DSLInterpreter()
    state = {"raw_event": "user=admin login=success"}
    field_def = {"op": "extract_regex", "source": "raw_event", "pattern": r"user=(?P<val>\w+)"}
    assert interpreter.evaluate(field_def, state) == "admin"

def test_extract_regex_malformed():
    interpreter = DSLInterpreter()
    state = {"raw_event": "user=admin"}
    field_def = {"op": "extract_regex", "source": "raw_event"}
    with pytest.raises(ParserDefinitionError, match="Missing 'pattern' for extract_regex"):
        interpreter.evaluate(field_def, state)

def test_extract_regex_invalid_input():
    interpreter = DSLInterpreter()
    state = {"raw_event": "login=success"}
    field_def = {"op": "extract_regex", "source": "raw_event", "pattern": r"user=(?P<val>\w+)"}
    assert interpreter.evaluate(field_def, state) is None

def test_extract_json_valid():
    interpreter = DSLInterpreter()
    state = {"raw_event": '{"key": "value"}'}
    field_def = {"op": "extract_json", "source": "raw_event"}
    assert interpreter.evaluate(field_def, state) == {"key": "value"}

def test_extract_json_invalid_input():
    interpreter = DSLInterpreter()
    state = {"raw_event": 'not json'}
    field_def = {"op": "extract_json", "source": "raw_event"}
    assert interpreter.evaluate(field_def, state) is None

def test_extract_kv_valid():
    interpreter = DSLInterpreter()
    state = {"raw_event": "a=1,b=2"}
    field_def = {"op": "extract_kv", "source": "raw_event", "separator": ","}
    assert interpreter.evaluate(field_def, state) == {"a": "1", "b": "2"}

def test_extract_kv_malformed():
    interpreter = DSLInterpreter()
    state = {"raw_event": "a=1,b=2"}
    field_def = {"op": "extract_kv", "source": "raw_event"}
    with pytest.raises(ParserDefinitionError, match="Missing 'separator' for extract_kv"):
        interpreter.evaluate(field_def, state)

def test_extract_csv_valid():
    interpreter = DSLInterpreter()
    state = {"raw_event": "a,b,c"}
    field_def = {"op": "extract_csv", "source": "raw_event", "separator": ","}
    assert interpreter.evaluate(field_def, state) == ["a", "b", "c"]

def test_extract_csv_malformed():
    interpreter = DSLInterpreter()
    state = {"raw_event": "a,b,c"}
    field_def = {"op": "extract_csv", "source": "raw_event"}
    with pytest.raises(ParserDefinitionError, match="Missing 'separator' for extract_csv"):
        interpreter.evaluate(field_def, state)

def test_drop_valid():
    interpreter = DSLInterpreter()
    state = {"raw_event": "test"}
    field_def = {"op": "drop", "source": "raw_event"}
    assert interpreter.evaluate(field_def, state) is None

def test_unknown_operation_rejection():
    interpreter = DSLInterpreter()
    state = {"raw_event": "test"}
    field_def = {"op": "unknown_op", "source": "raw_event"}
    with pytest.raises(UnsupportedOperationError, match="Unsupported operation: unknown_op"):
        interpreter.evaluate(field_def, state)
