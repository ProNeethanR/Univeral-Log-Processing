"""
Parser Engine for ULPF.

Centralized log parser execution engine that resolves parser definitions
via the Parser Registry (src.registry.get_parser).
"""

from pathlib import Path
from typing import Any, Dict, Union
import yaml

from src.registry import get_parser
from .dsl_validator import DSLValidator
from .interpreter import DSLInterpreter

DEFAULT_DSL_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "contracts" / "parser_mapping.schema.json"
)


class ParserEngine:
    """
    ParserEngine evaluates raw logs against a registered YAML DSL parser mapping definition.
    
    Parsers are resolved authoritatively through the Parser Registry using (source, version).
    """

    def __init__(
        self,
        source: str,
        version: str,
        schema_path: Union[str, Path] = DEFAULT_DSL_SCHEMA_PATH,
    ):
        self.source = source
        self.version = version
        self.schema_path = Path(schema_path)

        # 1. Obtain parser definition path authoritatively from Parser Registry
        self.parser_path = get_parser(source, version)

        # 2. Load parser definition YAML file
        with open(self.parser_path, "r", encoding="utf-8") as f:
            self.parser_def = yaml.safe_load(f)

        if not isinstance(self.parser_def, dict):
            raise ValueError(
                f"Invalid YAML content in parser definition file: {self.parser_path}"
            )

        # 3. Validate parser definition against the frozen DSL contract schema
        validator = DSLValidator(str(self.schema_path))
        validator.validate(self.parser_def)

        # 4. Instantiate DSL Interpreter
        self.interpreter = DSLInterpreter()

    def parse(self, raw_event: str) -> Dict[str, Any]:
        """
        Parses a raw log line string using the loaded DSL parser definition.
        """
        state: Dict[str, Any] = {"raw_event": raw_event}

        fields = self.parser_def.get("fields", {})
        for field_name, field_def in fields.items():
            result = self.interpreter.evaluate(field_def, state)
            if result is not None:
                state[field_name] = result

        output = {k: v for k, v in state.items() if k != "raw_event"}
        return output
