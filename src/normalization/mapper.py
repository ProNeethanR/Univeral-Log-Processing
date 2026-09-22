"""
OCSF Field Mapper and Normalization Integration for ULPF.

Maps extracted log parser fields to OCSF schema representations
and integrates with the offline OCSF 1.3.0 runtime validator.

Normalization policy notes
--------------------------
* ``class_uid``, ``category_uid``, ``activity_id``, ``type_uid``:
    Derived from the OCSF 1.3.0 frozen schema for Network Activity (uid=4001).
    These are schema-verified constants, not source-extracted values.

* ``severity_id``:
    ULPF explicit normalization policy default: ``1`` (Informational).
    RFC3164 Syslog does not carry a normalised severity field that maps to
    the OCSF severity_id enum.  The ULPF project policy is to default to
    Informational (1) until a richer source (e.g. syslog PRI, CEF severity)
    is available.  This is a deliberate project policy decision, NOT a
    value extracted from the source log.

* ``time``:
    RFC3164 BSD Syslog timestamps carry month, day, and HH:MM:SS only.
    They carry no year and no timezone.  The repository contains no
    capture metadata, fixture annotation, or project convention that
    establishes the correct year or timezone for these events.
    The mapper therefore does NOT populate ``time`` from RFC3164 components
    alone.  Callers that have an established year/timezone context MUST
    supply ``time`` directly in the parsed fields dict.

* ``metadata.product.vendor_name``:
    The OCSF 1.3.0 schema requires ``metadata.product.vendor_name``.
    The syslog ``host`` field is a network hostname, not a vendor identity.
    The ULPF project does not currently have a legitimate vendor source
    for these Syslog events.  The mapper does NOT fabricate a vendor name.
* ``connection_info.direction_id``:
    The OCSF 1.3.0 ``network_connection_info`` object requires ``direction_id``
    (confirmed required in the frozen schema).  The mapper emits it with the
    honest value derivable from the parsed fields:
      - ``1`` (Inbound)  when ``syslog_action == 'INBLOCK'``
                          or (``IN`` present and ``OUT`` empty)
      - ``2`` (Outbound) when (``OUT`` present and ``IN`` empty)
      - ``0`` (Unknown)  in all other cases, including the common fixture
                          pattern where both ``IN`` and ``OUT`` are set to
                          the same bridge interface.
    Note: the pre-existing ground-truth fixture (``syslog-001.json``) omits
    ``direction_id`` from ``connection_info``.  This means the existing
    ground truth does not represent a fully OCSF-valid event — it predates
    OCSF validation enforcement.  The mapper emits the field as required by
    the frozen schema; the ground-truth discrepancy is a known pre-existing
    deficiency in the fixture (not a mapper regression).
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from src.normalization.ocsf_validator import (
    DEFAULT_SCHEMA_PATH,
    OCSFValidator,
    OCSFValidationResult,
)
from src.registry import get_source_profile, ProfileNotFoundError
import datetime
import zoneinfo


class MappingResult(dict):
    """
    A dictionary containing the mapped OCSF event, enriched with lineage metadata.
    This subclass allows backwards compatibility with callers expecting a raw dict.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.injected_fields = []
        self.policy_fields = []
        self.source_profile_id = None
        self.source_profile_version = None


class OCSFMapper:
    def __init__(
        self,
        validator: Optional[OCSFValidator] = None,
        schema_path: Union[str, Path] = DEFAULT_SCHEMA_PATH,
    ):
        self.validator = validator or OCSFValidator(schema_path=schema_path)


    def map_syslog(self, fields: Dict[str, Any], source_id: Optional[str] = None, profile_version: Optional[str] = None) -> Dict[str, Any]:
        unmapped = {}
        src_endpoint = {}
        dst_endpoint = {}
        connection_info = {}
        metadata = {}
        event_time = None

        injected_fields = []

        # 1. Attempt to load Source Profile if context is provided
        profile = None
        if source_id and profile_version:
            # Case E: Will raise ProfileNotFoundError if missing
            profile = get_source_profile(source_id, profile_version)
            profile_id = f"{source_id}:{profile_version}"
            event_profile_id = profile_id

            # Construct authoritative metadata
            if 'vendor_name' in profile and 'product_name' in profile:
                metadata = {
                    "product": {
                        "vendor_name": profile["vendor_name"],
                        "name": profile["product_name"]
                    }
                }
                injected_fields.append({
                    "field": "metadata",
                    "source": "source_profile",
                    "profile_id": profile_id
                })

            # Construct authoritative timestamp
            if 'capture_year' in profile and 'capture_timezone' in profile:
                month_str = fields.get('syslog_month')
                day = fields.get('syslog_day') or fields.get('syslog_day_int')
                time_str = fields.get('syslog_time')

                if month_str and day and time_str:
                    try:
                        dt_str = f"{profile['capture_year']} {month_str} {day} {time_str}"
                        dt = datetime.datetime.strptime(dt_str, "%Y %b %d %H:%M:%S")
                        dt = dt.replace(tzinfo=zoneinfo.ZoneInfo(profile['capture_timezone']))
                        event_time = int(dt.timestamp())
                        injected_fields.append({
                            "field": "time",
                            "source": "source_profile",
                            "profile_id": profile_id
                        })
                    except Exception:
                        pass # Case F: incomplete event without time

        tracing = []

        def add_trace(src_f, sem_m, tgt):
            tracing.append({
                "source_field": src_f,
                "semantic_meaning": sem_m,
                "ocsf_target": tgt
            })

        if 'SRC' in fields:
            src_endpoint['ip'] = fields['SRC']
            add_trace("SRC", "Source IP Address", "src_endpoint")
        if 'SPT_int' in fields:
            src_endpoint['port'] = fields['SPT_int']
            add_trace("SPT", "Source Port", "src_endpoint")
        if 'IN' in fields and fields['IN']:
            src_endpoint['interface_name'] = fields['IN']
            add_trace("IN", "Ingress Interface", "src_endpoint")
        if 'LEN_int' in fields:
            src_endpoint['bytes'] = fields['LEN_int']
            add_trace("LEN", "Packet length", "src_endpoint")
        if 'MAC' in fields:
            src_endpoint['mac'] = fields['MAC']
            add_trace("MAC", "MAC Address", "src_endpoint")

        if 'DST' in fields:
            dst_endpoint['ip'] = fields['DST']
            add_trace("DST", "Destination IP Address", "dst_endpoint")
        if 'DPT_int' in fields:
            dst_endpoint['port'] = fields['DPT_int']
            add_trace("DPT", "Destination Port", "dst_endpoint")
        if 'OUT' in fields and fields['OUT']:
            dst_endpoint['interface_name'] = fields['OUT']
            add_trace("OUT", "Egress Interface", "dst_endpoint")


        if 'PROTO' in fields:
            connection_info['protocol_name'] = fields['PROTO']
            # direction_id is REQUIRED by the OCSF 1.3.0 network_connection_info object.
            # Derive the most honest value possible from parsed source fields;
            # default to 0 (Unknown) when directionality cannot be established.
            action = fields.get('syslog_action')
            if action == 'INBLOCK' or (fields.get('IN') and not fields.get('OUT')):
                connection_info['direction_id'] = 1  # Inbound
            elif fields.get('OUT') and not fields.get('IN'):
                connection_info['direction_id'] = 2  # Outbound
            else:
                connection_info['direction_id'] = 0  # Unknown
            add_trace("PROTO", "L4 Protocol", "connection_info")

        # Unmapped fields
        if 'DF' in fields:
            unmapped['DF'] = "true"
            add_trace("DF", "Don't Fragment flag set", "unmapped.DF")
        if 'SYN' in fields:
            unmapped['SYN'] = "true"
            add_trace("SYN", "TCP SYN flag set", "unmapped.SYN")
        if 'syslog_month' in fields:
            unmapped['syslog_month'] = fields['syslog_month']
            add_trace("syslog_month", "Month of the event", "unmapped.syslog_month")
        if 'WINDOW_int' in fields:
            unmapped['WINDOW'] = str(fields['WINDOW_int'])
            add_trace("WINDOW", "TCP Window Size", "unmapped.WINDOW")
        if 'PREC' in fields:
            unmapped['PREC'] = fields['PREC']
            add_trace("PREC", "Precedence", "unmapped.PREC")
        if 'TOS' in fields:
            unmapped['TOS'] = fields['TOS']
            add_trace("TOS", "Type of Service", "unmapped.TOS")
        if 'URGP_int' in fields:
            unmapped['URGP'] = str(fields['URGP_int'])
            add_trace("URGP", "Urgent Pointer", "unmapped.URGP")
        if 'PHYSIN' in fields:
            unmapped['PHYSIN'] = fields['PHYSIN']
            add_trace("PHYSIN", "Physical Ingress Interface", "unmapped.PHYSIN")
        if 'syslog_time' in fields:
            unmapped['syslog_time'] = fields['syslog_time']
            add_trace("syslog_time", "Time of the event", "unmapped.syslog_time")
        if 'RES' in fields:
            unmapped['RES'] = fields['RES']
            add_trace("RES", "Reserved bits", "unmapped.RES")
        if 'ID_int' in fields:
            unmapped['ID'] = str(fields['ID_int'])
            add_trace("ID", "IP ID", "unmapped.ID")
        if 'PHYSOUT' in fields:
            unmapped['PHYSOUT'] = fields['PHYSOUT']
            add_trace("PHYSOUT", "Physical Egress Interface", "unmapped.PHYSOUT")
        if 'TTL_int' in fields:
            unmapped['TTL'] = str(fields['TTL_int'])
            add_trace("TTL", "Time to Live", "unmapped.TTL")
        if 'syslog_day_int' in fields:
            unmapped['syslog_day'] = str(fields['syslog_day_int'])
            add_trace("syslog_day", "Day of the event", "unmapped.syslog_day")
        if 'syslog_host' in fields:
            unmapped['syslog_host'] = fields['syslog_host']
            add_trace("syslog_host", "Hostname of the reporting device", "unmapped.syslog_host")
        if 'TYPE_int' in fields:
            unmapped['TYPE'] = str(fields['TYPE_int'])
            add_trace("TYPE", "ICMP Type", "unmapped.TYPE")
        if 'CODE_int' in fields:
            unmapped['CODE'] = str(fields['CODE_int'])
            add_trace("CODE", "ICMP Code", "unmapped.CODE")
        if 'SEQ_int' in fields:
            unmapped['SEQ'] = str(fields['SEQ_int'])
            add_trace("SEQ", "Sequence number", "unmapped.SEQ")

        if 'syslog_action' in fields:
            unmapped['syslog_action'] = fields['syslog_action'].strip()
            add_trace("syslog_action", "Action or flow direction", "unmapped.syslog_action")

        unmapped['tracing'] = tracing

        event = MappingResult()
        event.injected_fields = injected_fields
        event.source_profile_id = event_profile_id if profile else None
        event.source_profile_version = profile_version if profile else None

        if unmapped:
            event['unmapped'] = unmapped
        if src_endpoint:
            event['src_endpoint'] = src_endpoint
        if dst_endpoint:
            event['dst_endpoint'] = dst_endpoint
        if connection_info:
            event['connection_info'] = connection_info

        if metadata:
            event['metadata'] = metadata
        if event_time is not None:
            event['time'] = event_time

        # Pass through base OCSF metadata/class identification attributes if present in fields
        for base_key in ('class_uid', 'category_uid', 'activity_id', 'type_uid', 'time', 'severity_id', 'metadata', 'profiles', 'class_name'):
            if base_key in fields and base_key not in event:
                event[base_key] = fields[base_key]

        return event

    def enrich_ocsf_headers(self, fields: Dict[str, Any], ocsf_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Populates schema-verifiable OCSF 1.3.0 classification attributes for Network Activity events.

        What this method sets and why
        ------------------------------
        class_uid=4001     Schema-confirmed uid for 'network_activity'.
        category_uid=4     Schema-confirmed category for 'Network Activity'.
        activity_id=6      Schema enum value 6='Traffic' (network traffic report).
                           Applied uniformly to inbound/blocked/outbound events because
                           the OCSF network_activity class captures traffic observation;
                           it has no separate 'block' or 'deny' activity_id.
        type_uid=400106    Computed as class_uid*100+activity_id per OCSF formula;
                           confirmed in the frozen schema enum.
        severity_id=1      ULPF normalization policy default: Informational.
                           RFC3164 Syslog carries no field that maps to OCSF
                           severity_id.  This value is a deliberate project policy
                           choice, NOT extracted from the source log.

        What this method deliberately does NOT set
        -------------------------------------------
        time               RFC3164 timestamps carry no year or timezone.
                           The repository has no capture metadata establishing
                           either.  Fabricating a year would produce an
                           unverifiable epoch.  Callers must supply 'time'
                           directly in fields if they have a legitimate source.
        metadata           The OCSF schema requires metadata.product.vendor_name.
                           The syslog 'host' field is a network hostname, not a
                           vendor name.  No legitimate vendor source exists in
                           the current project.  Fabricating a vendor would
                           produce an unverifiable metadata object.
        """
        if isinstance(ocsf_event, MappingResult):
            event = MappingResult(ocsf_event)
            event.injected_fields = list(ocsf_event.injected_fields)
            event.policy_fields = list(ocsf_event.policy_fields)
            event.source_profile_id = ocsf_event.source_profile_id
            event.source_profile_version = ocsf_event.source_profile_version
        else:
            event = MappingResult(ocsf_event)

        # Schema-verified classification constants (OCSF 1.3.0 network_activity)
        for key, default_val in [
            ('class_uid', 4001),
            ('category_uid', 4),
            ('activity_id', 6),
            ('type_uid', 400106)
        ]:
            if key not in event:
                val = fields.get(key, default_val)
                event[key] = val
                event.policy_fields.append({
                    "field": key,
                    "source": "normalization_policy",
                    "value": val,
                    "rationale": "Schema-verified classification constant"
                })

        # ULPF policy default: Informational severity when no source field exists.
        # See module docstring for the normalization policy rationale.
        if 'severity_id' not in event:
            val = fields.get('severity_id', 1)
            event['severity_id'] = val
            event.policy_fields.append({
                "field": "severity_id",
                "source": "normalization_policy",
                "value": val,
                "rationale": "ULPF policy default"
            })

        # 'time' and 'metadata' are intentionally NOT set here.
        # See module docstring for the evidence gaps that prevent fabrication.
        # Pass-through: if the caller already placed these in fields, forward them.
        for passthrough_key in ('time', 'metadata'):
            if passthrough_key in fields and passthrough_key not in event:
                event[passthrough_key] = fields[passthrough_key]

        return event

    def map_and_validate_syslog(
        self,
        fields: Dict[str, Any],
        raise_on_error: bool = False,
        source_id: Optional[str] = None,
        profile_version: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], OCSFValidationResult]:
        """
        Maps Syslog fields to OCSF event representation and validates against OCSF 1.3.0 schema.
        """
        raw_mapped = self.map_syslog(fields, source_id, profile_version)
        enriched_event = self.enrich_ocsf_headers(fields, raw_mapped)
        validation_result = self.validator.validate(enriched_event, raise_on_error=raise_on_error)
        return enriched_event, validation_result

    def normalize_and_validate(
        self,
        fields: Dict[str, Any],
        source_type: str = "syslog",
        raise_on_error: bool = False,
        source_id: Optional[str] = None,
        profile_version: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], OCSFValidationResult]:
        """
        Normalizes parser fields using specified source mapper and validates against OCSF 1.3.0 schema.
        """
        if source_type == "syslog":
            return self.map_and_validate_syslog(fields, raise_on_error=raise_on_error, source_id=source_id, profile_version=profile_version)
        else:
            raise ValueError(f"Unsupported normalization source_type: {source_type}")
