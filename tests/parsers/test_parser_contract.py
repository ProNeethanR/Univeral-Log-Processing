"""Parser DSL contract alignment: shipped parsers must validate against
contracts/parser_mapping.schema.json. Mirrors test_contract_alignment but for
the DSL contract that governs parsers/*.yaml.
"""

import glob
import json
import os

import jsonschema
import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DSL_SCHEMA = json.load(
    open(os.path.join(REPO_ROOT, "contracts", "parser_mapping.schema.json"), encoding="utf-8")
)


def _shipped_parsers():
    files = glob.glob(os.path.join(REPO_ROOT, "parsers", "*.yaml")) + glob.glob(
        os.path.join(REPO_ROOT, "parsers", "**", "*.yaml"), recursive=True
    )
    return sorted(set(files))


def test_shipped_parsers_exist():
    assert _shipped_parsers(), "no parsers/syslog.yaml shipped"


@pytest.mark.parametrize("path", _shipped_parsers())
def test_shipped_parser_validates_against_dsl_contract(path):
    data = yaml.safe_load(open(path, encoding="utf-8"))
    jsonschema.validate(instance=data, schema=DSL_SCHEMA)


def test_dsl_contract_permits_exactly_nine_operations():
    ops = DSL_SCHEMA["properties"]["fields"]["additionalProperties"]["properties"]["op"]["enum"]
    assert sorted(ops) == [
        "cast",
        "drop",
        "extract",
        "extract_csv",
        "extract_json",
        "extract_kv",
        "extract_regex",
        "lookup",
        "parse_timestamp",
    ]
    assert len(ops) == 9