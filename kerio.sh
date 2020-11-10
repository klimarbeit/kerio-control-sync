#!/bin/bash
python3 step1_urlgroups_sync.py
python3 step2_ip_services_sync.py
python3 step3_ipaddressgroups_sync.py
python3 step4_traffic_policy_sync.py
python3 step5_bandwidth_and_qos_sync.py
