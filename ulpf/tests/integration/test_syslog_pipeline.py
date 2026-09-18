import json
import hashlib
from src.parsers.engine import ParserEngine
from src.normalization.mapper import OCSFMapper

def test_syslog_pipeline():
    with open('p:/Univeral Log Processing/ulpf/fixtures/raw/syslog/syslog-001.log', 'rb') as f:
        raw_bytes = f.read()
        
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    assert sha256 == "a3783b7c387f7248d8c90c315b9b06a73bf4f7e6d0a6631b0a2449afd5706552", "SHA256 mismatch"
    
    raw_lines = raw_bytes.decode('utf-8').strip().split('\n')
    engine = ParserEngine('p:/Univeral Log Processing/ulpf/parsers/syslog.yaml')
    mapper = OCSFMapper()
    
    with open('p:/Univeral Log Processing/ulpf/fixtures/expected/syslog/syslog-001.json', 'r') as f:
        expected = json.load(f)
        
    discrepancies = []
    
    for i, line in enumerate(raw_lines):
        line = line.strip()
        if not line:
            continue
            
        parsed_fields = engine.parse(line)
        ocsf = mapper.map_syslog(parsed_fields)
        
        exp_event = expected[i]
        
        if 'unmapped' in ocsf and 'tracing' in ocsf['unmapped']:
            ocsf['unmapped']['tracing'] = sorted(ocsf['unmapped']['tracing'], key=lambda x: x['source_field'])
        if 'unmapped' in exp_event['ocsf_event'] and 'tracing' in exp_event['ocsf_event']['unmapped']:
            exp_event['ocsf_event']['unmapped']['tracing'] = sorted(exp_event['ocsf_event']['unmapped']['tracing'], key=lambda x: x['source_field'])
            
        try:
            assert exp_event['ocsf_event'] == ocsf
        except AssertionError as e:
            discrepancies.append(f"Mismatch at line {i+1}\nExpected: {exp_event['ocsf_event']}\nActual:   {ocsf}\n")
            
    if discrepancies:
        with open('p:/Univeral Log Processing/ulpf/tests/integration/discrepancies_report.txt', 'w') as f:
            for d in discrepancies:
                f.write(d + "\n")
        assert False, f"Found {len(discrepancies)} discrepancies. See discrepancies_report.txt"
        
    print("Integration test passed! All 25 lines parsed and mapped correctly.")
