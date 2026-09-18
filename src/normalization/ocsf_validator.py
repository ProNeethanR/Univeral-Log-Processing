"""
OCSF 1.3.0 Runtime Validator for ULPF.

Provides offline validation of candidate OCSF event dictionaries against
the local frozen OCSF 1.3.0 schema (schema/ocsf/ocsf_schema.json).
"""

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from src.parsers.exceptions import OCSFValidationError

EXPECTED_OCSF_SHA256 = "6ccff0f70b6216abc8f82be3756a9a167662a535c64a6a60df111b0db363e3e2"
EXPECTED_OCSF_VERSION = "1.3.0"
DEFAULT_SCHEMA_PATH = "schema/ocsf/ocsf_schema.json"


class OCSFFieldError:
    """Represents a specific OCSF event field validation failure."""

    def __init__(
        self,
        path: str,
        message: str,
        error_type: str,
        schema_rule: Optional[str] = None,
    ):
        self.path = path
        self.message = message
        self.error_type = error_type
        self.schema_rule = schema_rule

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "message": self.message,
            "error_type": self.error_type,
            "schema_rule": self.schema_rule,
        }

    def __repr__(self) -> str:
        return f"OCSFFieldError(path={self.path!r}, error_type={self.error_type!r}, message={self.message!r})"


class OCSFValidationResult:
    """Structured result of an OCSF event validation run."""

    def __init__(
        self,
        is_valid: bool,
        errors: Optional[List[OCSFFieldError]] = None,
        class_name: Optional[str] = None,
        class_uid: Optional[int] = None,
        ocsf_version: str = EXPECTED_OCSF_VERSION,
    ):
        self.is_valid = is_valid
        self.errors = errors if errors is not None else []
        self.class_name = class_name
        self.class_uid = class_uid
        self.ocsf_version = ocsf_version

    def raise_if_invalid(self) -> None:
        """Raises OCSFValidationError if the event is not valid."""
        if not self.is_valid:
            err_details = "; ".join(
                [f"[{e.error_type}] {e.path}: {e.message}" for e in self.errors]
            )
            raise OCSFValidationError(f"OCSF event validation failed: {err_details}")

    def __repr__(self) -> str:
        status = "VALID" if self.is_valid else f"INVALID ({len(self.errors)} errors)"
        return f"OCSFValidationResult(status={status}, class={self.class_name!r}, uid={self.class_uid})"


class OCSFValidator:
    """
    Offline OCSF 1.3.0 event validator.
    
    Verifies candidate OCSF event dictionaries against the frozen OCSF 1.3.0 schema artifact.
    """

    def __init__(
        self,
        schema_path: Union[str, Path] = DEFAULT_SCHEMA_PATH,
        expected_sha256: str = EXPECTED_OCSF_SHA256,
        expected_version: str = EXPECTED_OCSF_VERSION,
    ):
        self.schema_path = Path(schema_path)
        self.expected_sha256 = expected_sha256
        self.expected_version = expected_version

        self.schema: Dict[str, Any] = {}
        self.classes_by_uid: Dict[int, Tuple[str, Dict[str, Any]]] = {}
        self.classes_by_name: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        self.objects: Dict[str, Dict[str, Any]] = {}
        self.types: Dict[str, Dict[str, Any]] = {}
        self.dictionary_attributes: Dict[str, Dict[str, Any]] = {}

        self.string_type_names: Set[str] = set()
        self.integer_type_names: Set[str] = set()
        self.float_type_names: Set[str] = set()
        self.boolean_type_names: Set[str] = set()

        self._load_and_verify_schema()

    def _load_and_verify_schema(self) -> None:
        if not self.schema_path.exists():
            raise FileNotFoundError(
                f"OCSF schema file not found at path: {self.schema_path}"
            )

        raw_bytes = self.schema_path.read_bytes()
        actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()

        if self.expected_sha256 and actual_sha256.lower() != self.expected_sha256.lower():
            raise ValueError(
                f"OCSF schema SHA-256 integrity verification failed! "
                f"Expected: {self.expected_sha256}, Actual: {actual_sha256}"
            )

        try:
            schema_obj = json.loads(raw_bytes.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to parse OCSF schema JSON: {e}") from e

        schema_version = schema_obj.get("version")
        if self.expected_version and schema_version != self.expected_version:
            raise ValueError(
                f"OCSF schema version mismatch! "
                f"Expected: {self.expected_version}, Actual: {schema_version}"
            )

        self.schema = schema_obj
        self.objects = schema_obj.get("objects", {})
        self.types = schema_obj.get("types", {})
        self.dictionary_attributes = schema_obj.get("dictionary_attributes", {})

        self._build_type_categories()

        classes = schema_obj.get("classes", {})
        for cls_name, cls_def in classes.items():
            uid = cls_def.get("uid")
            if uid is not None:
                self.classes_by_uid[int(uid)] = (cls_name, cls_def)
            self.classes_by_name[cls_name] = (cls_name, cls_def)

    def _build_type_categories(self) -> None:
        for t_name, t_def in self.types.items():
            base_t = t_def.get("type") or t_def.get("type_name") or t_name
            base_str = str(base_t).lower()

            if t_name in ("boolean_t",):
                self.boolean_type_names.add(t_name)
            elif t_name in ("integer_t", "long_t", "port_t", "timestamp_t") or base_str in ("integer_t", "long_t", "integer", "long"):
                self.integer_type_names.add(t_name)
            elif t_name in ("float_t",) or base_str in ("float_t", "float"):
                self.float_type_names.add(t_name)
            elif t_name in ("string_t",) or base_str in ("string_t", "string") or t_def.get("type") == "string_t":
                self.string_type_names.add(t_name)

    def validate(
        self,
        event: Dict[str, Any],
        raise_on_error: bool = False,
    ) -> OCSFValidationResult:
        """
        Validates a candidate OCSF event dictionary against OCSF 1.3.0 schema.
        
        The candidate event dictionary is NOT modified.
        """
        if not isinstance(event, dict):
            res = OCSFValidationResult(
                is_valid=False,
                errors=[
                    OCSFFieldError(
                        path="$",
                        message="Candidate OCSF event must be a JSON object (dict).",
                        error_type="wrong_type",
                    )
                ],
            )
            if raise_on_error:
                res.raise_if_invalid()
            return res

        # Ensure immutability by operating on a deepcopy for inspection
        event_copy = copy.deepcopy(event)
        errors: List[OCSFFieldError] = []

        # Identify class
        class_uid = event_copy.get("class_uid")
        class_name = event_copy.get("class_name")

        target_cls_name: Optional[str] = None
        target_cls_def: Optional[Dict[str, Any]] = None

        if class_uid is not None:
            if isinstance(class_uid, bool) or not isinstance(class_uid, int):
                errors.append(
                    OCSFFieldError(
                        path="class_uid",
                        message=f"Field 'class_uid' must be an integer, got {type(class_uid).__name__}",
                        error_type="wrong_type",
                    )
                )
            elif class_uid in self.classes_by_uid:
                target_cls_name, target_cls_def = self.classes_by_uid[class_uid]
            else:
                errors.append(
                    OCSFFieldError(
                        path="class_uid",
                        message=f"Unknown OCSF class_uid: {class_uid}",
                        error_type="unknown_class",
                    )
                )
        elif class_name is not None:
            if isinstance(class_name, str) and class_name in self.classes_by_name:
                target_cls_name, target_cls_def = self.classes_by_name[class_name]
                class_uid = target_cls_def.get("uid")
            else:
                errors.append(
                    OCSFFieldError(
                        path="class_name",
                        message=f"Unknown OCSF class_name: {class_name}",
                        error_type="unknown_class",
                    )
                )
        else:
            errors.append(
                OCSFFieldError(
                    path="$",
                    message="OCSF event missing mandatory class identification ('class_uid' or 'class_name').",
                    error_type="missing_class",
                )
            )

        if target_cls_def is None:
            res = OCSFValidationResult(
                is_valid=False,
                errors=errors,
                class_name=target_cls_name,
                class_uid=class_uid if isinstance(class_uid, int) else None,
            )
            if raise_on_error:
                res.raise_if_invalid()
            return res

        active_profiles = self._extract_active_profiles(event_copy)

        # Validate class attributes
        cls_attributes = target_cls_def.get("attributes", {})
        self._validate_object_fields(
            data=event_copy,
            attr_specs=cls_attributes,
            path="",
            active_profiles=active_profiles,
            errors=errors,
        )

        is_valid = len(errors) == 0
        res = OCSFValidationResult(
            is_valid=is_valid,
            errors=errors,
            class_name=target_cls_name,
            class_uid=class_uid if isinstance(class_uid, int) else None,
        )
        if raise_on_error:
            res.raise_if_invalid()
        return res

    def _extract_active_profiles(self, event: Dict[str, Any]) -> Set[str]:
        profiles: Set[str] = set()
        meta = event.get("metadata")
        if isinstance(meta, dict):
            profs = meta.get("profiles")
            if isinstance(profs, list):
                for p in profs:
                    if isinstance(p, str):
                        profiles.add(p)
        top_profs = event.get("profiles")
        if isinstance(top_profs, list):
            for p in top_profs:
                if isinstance(p, str):
                    profiles.add(p)
        return profiles

    def _validate_object_fields(
        self,
        data: Dict[str, Any],
        attr_specs: Dict[str, Dict[str, Any]],
        path: str,
        active_profiles: Set[str],
        errors: List[OCSFFieldError],
    ) -> None:
        # Check required fields
        for attr_name, attr_spec in attr_specs.items():
            field_path = f"{path}.{attr_name}" if path else attr_name
            req = attr_spec.get("requirement")
            prof = attr_spec.get("profile")

            if req == "required":
                is_req = False
                if prof is None:
                    is_req = True
                elif prof in active_profiles:
                    is_req = True

                if is_req and attr_name not in data:
                    errors.append(
                        OCSFFieldError(
                            path=field_path,
                            message=f"Missing required field '{field_path}'",
                            error_type="missing_required",
                            schema_rule=f"requirement={req}, profile={prof}",
                        )
                    )

        # Validate present fields in data
        for attr_name, val in data.items():
            field_path = f"{path}.{attr_name}" if path else attr_name
            attr_spec = attr_specs.get(attr_name)

            if not attr_spec:
                # Fall back to dictionary_attributes if available
                attr_spec = self.dictionary_attributes.get(attr_name)

            if not attr_spec:
                # Field is not in class schema or dictionary
                continue

            self._validate_value(
                val=val,
                attr_spec=attr_spec,
                field_path=field_path,
                active_profiles=active_profiles,
                errors=errors,
            )

    def _validate_value(
        self,
        val: Any,
        attr_spec: Dict[str, Any],
        field_path: str,
        active_profiles: Set[str],
        errors: List[OCSFFieldError],
    ) -> None:
        is_array = attr_spec.get("is_array", False)
        attr_type = attr_spec.get("type", "string_t")
        obj_type = attr_spec.get("object_type")

        if is_array:
            if not isinstance(val, list):
                errors.append(
                    OCSFFieldError(
                        path=field_path,
                        message=f"Field '{field_path}' must be a list/array, got {type(val).__name__}",
                        error_type="wrong_type",
                        schema_rule=f"is_array=True, type={attr_type}",
                    )
                )
                return

            for idx, item in enumerate(val):
                item_path = f"{field_path}[{idx}]"
                self._validate_single_value(
                    val=item,
                    attr_spec=attr_spec,
                    attr_type=attr_type,
                    obj_type=obj_type,
                    field_path=item_path,
                    active_profiles=active_profiles,
                    errors=errors,
                )
        else:
            self._validate_single_value(
                val=val,
                attr_spec=attr_spec,
                attr_type=attr_type,
                obj_type=obj_type,
                field_path=field_path,
                active_profiles=active_profiles,
                errors=errors,
            )

    def _validate_single_value(
        self,
        val: Any,
        attr_spec: Dict[str, Any],
        attr_type: str,
        obj_type: Optional[str],
        field_path: str,
        active_profiles: Set[str],
        errors: List[OCSFFieldError],
    ) -> None:
        if val is None:
            return

        # Primitive type checks
        if attr_type in self.integer_type_names:
            if isinstance(val, bool) or not isinstance(val, int):
                errors.append(
                    OCSFFieldError(
                        path=field_path,
                        message=f"Field '{field_path}' expected integer ({attr_type}), got {type(val).__name__}",
                        error_type="wrong_type",
                        schema_rule=f"type={attr_type}",
                    )
                )
                return
        elif attr_type in self.float_type_names:
            if isinstance(val, bool) or not isinstance(val, (float, int)):
                errors.append(
                    OCSFFieldError(
                        path=field_path,
                        message=f"Field '{field_path}' expected float ({attr_type}), got {type(val).__name__}",
                        error_type="wrong_type",
                        schema_rule=f"type={attr_type}",
                    )
                )
                return
        elif attr_type in self.string_type_names:
            if not isinstance(val, str):
                errors.append(
                    OCSFFieldError(
                        path=field_path,
                        message=f"Field '{field_path}' expected string ({attr_type}), got {type(val).__name__}",
                        error_type="wrong_type",
                        schema_rule=f"type={attr_type}",
                    )
                )
                return
        elif attr_type in self.boolean_type_names:
            if not isinstance(val, bool):
                errors.append(
                    OCSFFieldError(
                        path=field_path,
                        message=f"Field '{field_path}' expected boolean ({attr_type}), got {type(val).__name__}",
                        error_type="wrong_type",
                        schema_rule=f"type={attr_type}",
                    )
                )
                return
        elif attr_type in ("object_t",):
            if not isinstance(val, dict):
                errors.append(
                    OCSFFieldError(
                        path=field_path,
                        message=f"Field '{field_path}' expected object ({attr_type}), got {type(val).__name__}",
                        error_type="wrong_type",
                        schema_rule=f"type={attr_type}",
                    )
                )
                return
            if obj_type and obj_type in self.objects:
                nested_obj_spec = self.objects[obj_type]
                nested_attr_specs = nested_obj_spec.get("attributes", {})
                self._validate_object_fields(
                    data=val,
                    attr_specs=nested_attr_specs,
                    path=field_path,
                    active_profiles=active_profiles,
                    errors=errors,
                )

        # Enum validation
        enum_dict = attr_spec.get("enum")
        if not enum_dict:
            dict_name = attr_spec.get("sibling") or field_path.split(".")[-1]
            dict_attr = self.dictionary_attributes.get(dict_name)
            if dict_attr:
                enum_dict = dict_attr.get("enum")

        if enum_dict and isinstance(enum_dict, dict):
            val_str = str(val)
            valid_keys = set(enum_dict.keys())
            if val_str not in valid_keys:
                allowed_samples = sorted(list(valid_keys))[:10]
                errors.append(
                    OCSFFieldError(
                        path=field_path,
                        message=f"Field '{field_path}' value {val!r} is not a valid enum value. Allowed enum keys: {allowed_samples}",
                        error_type="invalid_enum",
                        schema_rule=f"enum={valid_keys}",
                    )
                )


def validate_ocsf_event(
    event: Dict[str, Any],
    schema_path: Union[str, Path] = DEFAULT_SCHEMA_PATH,
    raise_on_error: bool = False,
) -> OCSFValidationResult:
    """
    Convenience function to validate an OCSF event using default schema.
    """
    validator = OCSFValidator(schema_path=schema_path)
    return validator.validate(event, raise_on_error=raise_on_error)
