#!/usr/bin/python3
# ---------------------------------------------------
# Tested on Kerio OS / Kerio control 9.3.1 build 3465
# ---------------------------------------------------

import json
import urllib.request
import http.cookiejar
import os
import ssl

from kerio_sync_conf import *

# Skip SSL verification
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context

# Cookie storage is necessary for session handling
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
urllib.request.install_opener(opener)

def callMethod(method, params, token=None):
    data = {"method": method, "id": 1, "jsonrpc": "2.0", "params": params}
    req = urllib.request.Request(url=ip_address + '/admin/api/jsonrpc/')
    req.add_header('Content-Type', 'application/json')
    if (token is not None):
        req.add_header('X-Token', token)
    httpResponse = urllib.request.urlopen(req, json.dumps(data).encode())
    if (httpResponse.status == 200):
        body = httpResponse.read().decode()
        return json.loads(body)

print("=* Syncing IP Services *=")
ip_address = masterserver
session = callMethod("Session.login", {"userName": username, "password": password, "application": {"vendor": "Kerio", "name": "Control Api", "version": "Python"}})
token = session["result"]["token"]
# print("Masterserver token:", token)
request = callMethod("IpServices.get", {"query": {}}, token)
ipServicesListMaster = request["result"]["list"]
# ipServicesListMasterTotal = request["result"]["totalItems"]
# print("IP Services Total count on Masterserver:",  ipServicesListMasterTotal)
# print("IP Services on Masterserver:")
callMethod("Session.logout", {}, token)
# for a, ipService in enumerate(ipServicesListMaster):
#    print(a, ipService)

# Since IpServices.create doesn't add members to groups, leaving them empty,
# search for groupnames on Masterserver (services that have members)
list_names_of_grouped_services_on_master = []
for y, ipService in enumerate(ipServicesListMaster):
    if ipServicesListMaster[y]["group"] == True:
        list_names_of_grouped_services_on_master.append(ipServicesListMaster[y]["name"])
# print(list_names_of_grouped_services_on_master)
grouped_list_size = (len(list_names_of_grouped_services_on_master))

# Slave actions
for i, slaveserver in enumerate(slaveservers):
    ip_address = slaveserver
    session = callMethod("Session.login", {"userName": username, "password": password, "application": {"vendor": "Kerio", "name": "Control Api", "version": "Python"}})
    token = session["result"]["token"]
#    print("Slaveserver", i, "token:", token)
    request = callMethod("IpServices.get", {"query": {}}, token)
    ipServicesListSlave = request["result"]["list"]
    if ipServicesListMaster == ipServicesListSlave:
        print("IpServices configuration on Slaveserver", i, "is exactly the same as on the Masterserver. No operation is needed.")
        if i == 0:
            i = 1
        elif i == len(slaveservers):
            break
        continue
#    ipServicesListSlaveTotal = request["result"]["totalItems"]
#    print("IP Services Total count on Slaveserver", i, ":", ipServicesListSlaveTotal)
#    print("IP Services on Slaveserver", i, ":")
#    for a1, ipService in enumerate(ipServicesListSlave):
#        print(a1, ipService)

# IpServices.set only updates the existing IpServices, so for full sync I'll use
# IpServices.remove -> IpServices.apply -> IpServices.create -> IpServices.apply
# Creating the list of serviceIds to remove (all that exists on Slave)
    ids_for_remove_on_slave = []
    for n, ipService in enumerate(ipServicesListSlave):
        ids_for_remove_on_slave.append(ipServicesListSlave[n]["id"])

# Remove all IP Services from Slaveserver
    request = callMethod("IpServices.remove", {"serviceIds": ids_for_remove_on_slave}, token)
    print("Slaveserver", i, "IpServices remove response:", request["result"])
# IpServices.remove works without cutting-off prevention procedures (not after 30 seconds,
# but even after reboot config hasn't been restored automatically), although API Manual
# says IpServices.apply require cutting-off prevention. I'll use it anyway
    # Apply - Config timestamp - Config confirm
    request = callMethod("IpServices.apply", {}, token)
    print("Slaveserver", i, "IpServices apply response:", request["result"])

# Hope it's not needed, but API manual says to perform this operations after each "IpServices.apply" method's use
    configTimestampRequest = callMethod("Session.getConfigTimestamp", {}, token)
    configTimestampResponse = configTimestampRequest["result"]
    print("Slaveserver", i, "Config timestamp for 'IpServices.apply' operation response:", configTimestampResponse)
    confirmConfigRequest = callMethod("Session.confirmConfig", configTimestampResponse, token)
    print("Slaveserver", i, "Config confirm for 'IpServices.apply' operation response:", confirmConfigRequest["result"])

    # Create new IpServices on Slaveserver
    request = callMethod("IpServices.create", {"services": ipServicesListMaster}, token)
    print("Slaveserver", i, "IpServices create response:", request["result"]["errors"])

#   Need to apply changes to update ipServicesList on Slave (we use new ipServicesList for groupnames rouine)
    request = callMethod("IpServices.apply", {}, token)
    print("Slaveserver", i, "IpServices apply response:", request["result"])
    configTimestampRequest = callMethod("Session.getConfigTimestamp", {}, token)
    configTimestampResponse = configTimestampRequest["result"]
    print("Slaveserver", i, "Config timestamp for 'IpServices.apply' operation response:", configTimestampResponse)
    confirmConfigRequest = callMethod("Session.confirmConfig", configTimestampResponse, token)
    print("Slaveserver", i, "Config confirm for 'IpServices.apply' operation response:", confirmConfigRequest["result"])

# --------------- Long way to fill groups with members -------------------
# Request new (newly created) ipServicesList on Slave
    request = callMethod("IpServices.get", {"query": {}}, token)
    ipServicesListSlave = request["result"]["list"]

# Searching new (newly created) ids of grouped services on Slave
    list_ids_of_grouped_services_on_slave = []
    for e in range(grouped_list_size):
        service_name = (list_names_of_grouped_services_on_master[e])
        for s, ipService in enumerate(ipServicesListSlave):
            if service_name == ipServicesListSlave[s]["name"]:
                list_ids_of_grouped_services_on_slave.append(ipServicesListSlave[s]["id"])
#    print(list_ids_of_grouped_services_on_slave)

# Collect all members by filtering services' list on Masterserver
    list_all_services_members = []
# Auxiliary list for future use (counts how many members will be in each service, consistently)
    each_service_members_count = []
    for h in range(grouped_list_size):
        service_name = (list_names_of_grouped_services_on_master[h])
# Auxiliary list, used once only for grouping
        grouped_services_members = []
        for j, ipService in enumerate(ipServicesListMaster):
            if service_name == ipServicesListMaster[j]["name"]:
                grouped_services_members.append(ipServicesListMaster[j]["members"])
                each_service_members_count.append((len(grouped_services_members[0])))
                for q in range(len(grouped_services_members[0])):
                    list_all_services_members.append(grouped_services_members[0][q]["name"])

# Collect ids of members on Slaveserver
    list_ids_of_members_on_slave = []
    for v in range(len(list_all_services_members)):
        service_name = (list_all_services_members[v])
        for d, ipService in enumerate(ipServicesListSlave):
            if service_name == ipServicesListSlave[d]["name"]:
                list_ids_of_members_on_slave.append(ipServicesListSlave[d]["id"])

# Now we need to convert list_ids_of_members_on_slave from format ['14', '18', '26']
# to [{'id': '14'}, {'id':'18'}, {'id':'26}'], because API function "IpServices.set"
# allows to send param "list of members" only in this format
# API manual says "true list of member IpService ids"

    true_list_ids_of_members_on_slave = []
    for v1 in list_ids_of_members_on_slave:
        true_list_ids_of_members_on_slave.append({'id': v1})

    for c, count in enumerate(each_service_members_count):
        request = callMethod("IpServices.set", {"serviceIds": [list_ids_of_grouped_services_on_slave[c]], "details": {"members": true_list_ids_of_members_on_slave[:count]}}, token)
        print("Slaveserver", i, "IpServices.set (grouping) response:", request)
# cut processed slices from list
        del ([true_list_ids_of_members_on_slave[:count]])

# Not DRY, fix later
    request = callMethod("IpServices.apply", {}, token)
    print("Slaveserver", i, "IpServices apply response:", request["result"])
    configTimestampRequest = callMethod("Session.getConfigTimestamp", {}, token)
    configTimestampResponse = configTimestampRequest["result"]
    print("Slaveserver", i, "Config timestamp for 'IpServices.apply' operation response:", configTimestampResponse)
    confirmConfigRequest = callMethod("Session.confirmConfig", configTimestampResponse, token)
    print("Slaveserver", i, "Config confirm for 'IpServices.apply' operation response:", confirmConfigRequest["result"])
    callMethod("Session.logout", {}, token)
print("=* IP Services sync completed *=")
