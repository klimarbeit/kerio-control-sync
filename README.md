# kerio-control-sync
Kerio Control config sync via API calls

## Python 3.x scripts for syncing config on "Slaveservers" with "Masterserver"
Tested on Kerio OS / Kerio control 9.3.1 build 3465

**Syncs:**

1. In web interface: menu admin/Definitions/URL Groups (list name="UrlGroups" in var/winroute/winroute.cfg) — using API functions Session.login, UrlGroups.get, UrlGroups.remove, UrlGroups.create, UrlGroups.apply + cut-off procedures (Session.getConfigTimestamp, Session.confirmConfig), Session.logout
```
step1_urlgroups_sync.py
```

2. In web interface: menu admin/Definitions/Services (list name="IPServices" in var/winroute/winroute.cfg) — using API functions Session.login, IpServices.get, IpServices.remove, IpServices.create, IpServices.apply, IpServices.set + cut-off procedures (Session.getConfigTimestamp, Session.confirmConfig), Session.logout
```
step2_ip_services_sync.py
```

3. In web interface: menu admin/Definitions/IP Address Groups (list name="IpAccessList" in var/winroute/winroute.cfg) — using API functions Session.login, IpAddressGroups.get, IpAddressGroups.getGroupList, IpAddressGroups.validateRemove, IpAddressGroups.create, IpAddressGroups.apply + cut-off procedures (Session.getConfigTimestamp, Session.confirmConfig), Session.logout
```
step3_ipaddressgroups_sync.py
```

4. In web interface: menu admin/Traffic Rules (list name="TrafficRules_v2" in var/winroute/winroute.cfg) — using API functions Session.login, TrafficPolicy.get, TrafficPolicy.getDefaultRule, TrafficPolicy.set, + cut-off procedures (Session.getConfigTimestamp, Session.confirmConfig), Session.logout
```
step4_traffic_policy_sync.py
```

5. In web interface: menu admin/Bandwidth Management and QoS (list name="BandwidthManagementRules" in var/winroute/winroute.cfg) — using API functions Session.login, BandwidthManagement.get, BandwidthManagement.getBandwidth, BandwidthManagement.set, BandwidthManagement.setBandwidth + cut-off procedures (Session.getConfigTimestamp, Session.confirmConfig), Session.logout
```
step5_bandwidth_and_qos_sync.py
```

***Cridentials***
```
kerio_sync_conf.py
```
