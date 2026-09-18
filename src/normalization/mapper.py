class OCSFMapper:
    def __init__(self):
        pass
        
    def map_syslog(self, fields):
        unmapped = {}
        src_endpoint = {}
        dst_endpoint = {}
        connection_info = {}
        
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
        if 'MAC' in fields and len(fields['MAC'].split(':')) > 6:
            src_endpoint['mac'] = ':'.join(fields['MAC'].split(':')[6:])
            add_trace("MAC", "MAC address", "src_endpoint")
            
        if 'DST' in fields:
            dst_endpoint['ip'] = fields['DST']
            add_trace("DST", "Destination IP Address", "dst_endpoint")
        if 'DPT_int' in fields:
            dst_endpoint['port'] = fields['DPT_int']
            add_trace("DPT", "Destination Port", "dst_endpoint")
        if 'OUT' in fields and fields['OUT']:
            dst_endpoint['interface_name'] = fields['OUT']
            add_trace("OUT", "Egress Interface", "dst_endpoint")
        if 'MAC' in fields and len(fields['MAC'].split(':')) >= 6:
            dst_endpoint['mac'] = ':'.join(fields['MAC'].split(':')[:6])
            
        if 'PROTO' in fields:
            connection_info['protocol_name'] = fields['PROTO']
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
        if 'MAC' in fields:
            unmapped['MAC'] = fields['MAC']
            add_trace("MAC", "MAC address", "unmapped.MAC")
        if 'syslog_action' in fields:
            unmapped['syslog_action'] = fields['syslog_action'].strip()
            add_trace("syslog_action", "Action or flow direction", "unmapped.syslog_action")
            
        unmapped['tracing'] = tracing
        
        event = {}
        if unmapped:
            event['unmapped'] = unmapped
        if src_endpoint:
            event['src_endpoint'] = src_endpoint
        if dst_endpoint:
            event['dst_endpoint'] = dst_endpoint
        if connection_info:
            event['connection_info'] = connection_info
            
        return event
