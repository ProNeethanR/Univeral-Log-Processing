"""
demo.py — ULPF SIH Demo Execution Script

Runs the complete end-to-end Universal Log Pre-processing Framework pipeline
on the synthetic fixture `syslog-demo-001`, injecting authoritative source
context, generating OCSF 1.3.0 Network Activity events, and validating them.
"""

import json
import tempfile
import shutil
from pathlib import Path

from src.registry import configure_profile_storage, register_source_profile, register_parser
from src.parsers.engine import ParserEngine
from src.normalization.mapper import OCSFMapper

def main():
    print("=" * 70)
    print("  ULPF — Universal Log Pre-processing Framework Demo (syslog-demo-001)")
    print("=" * 70)

    tmp = tempfile.mkdtemp()
    try:
        # 1. Setup isolated durable profile storage
        configure_profile_storage(Path(tmp))

        # 2. Register & activate authoritative demo source context
        demo_profile = {
            "source": "syslog-demo-001",
            "profile_version": "1.0.0",
            "capture_year": 2026,
            "capture_timezone": "UTC",
            "vendor_name": "Linux",
            "product_name": "iptables"
        }
        register_source_profile("syslog-demo-001", "1.0.0", demo_profile, activate=True)
        register_parser("syslog-demo-001", "1.0.0", "parsers/syslog.yaml")
        print("[+] Registered & activated Source Profile: syslog-demo-001:1.0.0")
        print(f"    - capture_year:     {demo_profile['capture_year']}")
        print(f"    - capture_timezone: {demo_profile['capture_timezone']}")
        print(f"    - vendor_name:      {demo_profile['vendor_name']}")
        print(f"    - product_name:     {demo_profile['product_name']}")

        # 3. Initialize Parser and OCSF Mapper
        engine = ParserEngine("syslog-demo-001", "1.0.0")
        mapper = OCSFMapper()

        # 4. Read and process synthetic demo log
        log_path = Path("fixtures/raw/syslog/syslog-demo-001.log")
        with open(log_path, "r", encoding="utf-8") as f:
            raw_lines = [line.strip() for line in f if line.strip()]

        print(f"\n[+] Loaded demo fixture: {log_path} ({len(raw_lines)} events)")

        # 5. Process all events
        all_passed = True
        for i, line in enumerate(raw_lines, 1):
            parsed = engine.parse(line)
            raw_mapped = mapper.map_syslog(parsed, source_id="syslog-demo-001", profile_version="1.0.0")
            enriched = mapper.enrich_ocsf_headers(parsed, raw_mapped)
            val = mapper.validator.validate(enriched)

            status = "PASS" if val.is_valid else "FAIL"
            if not val.is_valid:
                all_passed = False
            print(f"    Event {i}: {parsed.get('PROTO', 'IP')} {parsed.get('SRC')}:{parsed.get('SPT', '')} -> "
                  f"{parsed.get('DST')}:{parsed.get('DPT', '')} | OCSF 1.3.0 Validation: {status}")

            if i == 1:
                sample_event = enriched

        print(f"\n[+] Overall OCSF 1.3.0 Validation: {'PASS (100%)' if all_passed else 'FAIL'}")

        print("\n" + "=" * 70)
        print("  Sample Transformed Event (Event 1 in OCSF 1.3.0 JSON)")
        print("=" * 70)
        print(json.dumps(sample_event, indent=2))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
