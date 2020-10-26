#!/usr/bin/python3
# ---------------------------------------------------
# Tested on Kerio OS / Kerio control 9.3.1 build 3465
# ---------------------------------------------------

# Kerio Control API Manual doesn't contain sufficent info about IpAddressGroups operations (I've founded only
# .apply and .reset functions, but there's no get/set/etc...), so we'll use Kerio Connect Admin API Manual
# https://manuals.gfi.com/en/kerio/api/connect/admin/reference/interfacekerio_1_1web_1_1_ip_address_groups.html

import json
import urllib.request
import http.cookiejar
import os
import ssl

from kerio_vi_sync_conf import *

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

print("=* Syncing IpAddressGroups *=")
ip_address = masterserver
session = callMethod("Session.login", {"userName": username, "password": password, "application": {"vendor": "Kerio", "name": "Control Api", "version": "Python"}})
token = session["result"]["token"]
#print("Masterserver token:", token)
request = callMethod("IpAddressGroups.get", {"query": {}}, token)
ipaddrentryListMaster = request["result"]["list"]
ipaddrentryListMasterTotal = request["result"]["totalItems"]
request = callMethod("IpAddressGroups.getGroupList", {"query": {}}, token)
#print("IpAddressGroups Total count on Masterserver:", ipaddrentryListMasterTotal)
#print("IpAddressGroups on Masterserver:")
# for a, entry in enumerate(ipaddrentryListMaster):
#    print(a, entry)
ipaddrGroupListMaster = request["result"]["groups"]
# for a2, groupid in enumerate(ipaddrGroupListMaster):
#    print(a2, groupid)
callMethod("Session.logout", {}, token)

for i, slaveserver in enumerate(slaveservers):
    ip_address = slaveserver
    session = callMethod("Session.login", {"userName": username, "password": password, "application": {"vendor": "Kerio", "name": "Control Api", "version": "Python"}})
    token = session["result"]["token"]
#    print("Slaveserver", i, "token:", token)
    request = callMethod("IpAddressGroups.get", {"query": {}}, token)
    ipaddrentryListSlave = request["result"]["list"]
    ipaddrentryListSlaveTotal = request["result"]["totalItems"]
    request = callMethod("IpAddressGroups.getGroupList", {"query": {}}, token)
#    print("IpAddressGroups Total count on Slaveserver", i, ":", ipaddrentryListSlaveTotal)
#    print("IpAddressGroups on Slaveserver", i, ":")
#    for a1, entry in enumerate(ipaddrentryListSlave):
#        print(a1, entry)
    ipaddrGroupListSlave = request["result"]["groups"]
#    for a3, groupid in enumerate(ipaddrGroupListSlave):
#        print(a3, groupid)
    if ipaddrentryListMaster == ipaddrentryListSlave and ipaddrGroupListSlave == ipaddrGroupListMaster:
        print("IpAddressGroups configuration on Slaveserver", i, "is exactly the same as on the Masterserver. No operation is needed.")
        if i == 0:
            i = 1
        elif i == len(slaveservers):
            break
        continue

# Creating the list of groupIds to remove (all that exists on Slave)
    ids_for_remove_on_slave = []
    for n, entry in enumerate(ipaddrentryListSlave):
        ids_for_remove_on_slave.append(ipaddrentryListSlave[n]["id"])
#    print(ids_for_remove_on_slave)

# Before removing and (or) setting IpAddressGroups we need to check whether removal or update can cut off the administrator
# from remote administration by performing .validateRemove and (or) .validateSet checks
# IpAddressGroups::validateRemove (out ErrorList errors, in KIdList groupIds)
# IpAddressGroups::validateSet (out ErrorList errors, in KIdList groupIds, in IpAddressEntry details)

    request = callMethod("IpAddressGroups.validateRemove", {"groupIds": ids_for_remove_on_slave}, token)
    ipaddrGroupVaildateCheck = request["result"]
    if ipaddrGroupVaildateCheck != {'errors': []}:
        print("Removal will cut off the administrator from remote administration. Check group Ids that cause the error(s)")
        break
    print("Slaveserver", i, "IpAddressGroups.validateRemove response:", ipaddrGroupVaildateCheck)

# IpAddressGroups.remove -> IpAddressGroups.apply -> IpAddressGroups.create -> IpAddressGroups.apply
# Remove IpAddressGroups from Slaveserver
    request = callMethod("IpAddressGroups.remove", {"groupIds": ids_for_remove_on_slave}, token)
    print("Slaveserver", i, "IpAddressGroups.remove response:", request["result"])
    # Apply - Config timestamp - Config confirm
    request = callMethod("IpAddressGroups.apply", {}, token)
    print("Slaveserver", i, "IpAddressGroups.apply response:", request["result"])
    configTimestampRequest = callMethod("Session.getConfigTimestamp", {}, token)
    configTimestampResponse = configTimestampRequest["result"]
    print("Slaveserver", i, "Config timestamp for 'IpAddressGroups.apply' operation response:", configTimestampResponse)
    confirmConfigRequest = callMethod("Session.confirmConfig", configTimestampResponse, token)
    print("Slaveserver", i, "Config confirm for 'IpAddressGroups.apply' operation response:", confirmConfigRequest["result"])

    # Create new IpAddressGroups on Slaveserver
    request = callMethod("IpAddressGroups.create", {"groups": ipaddrentryListMaster}, token)
    print("Slaveserver", i, "IpAddressGroups create response:", request["result"]["errors"])

# Not DRY, fix later
    request = callMethod("IpAddressGroups.apply", {}, token)
    print("Slaveserver", i, "IpAddressGroups.apply response:", request["result"])
    configTimestampRequest = callMethod("Session.getConfigTimestamp", {}, token)
    configTimestampResponse = configTimestampRequest["result"]
    print("Slaveserver", i, "Config timestamp for 'IpAddressGroups.apply' operation response:", configTimestampResponse)
    confirmConfigRequest = callMethod("Session.confirmConfig", configTimestampResponse, token)
    print("Slaveserver", i, "Config confirm for 'IpAddressGroups.apply' operation response:", confirmConfigRequest["result"])
    callMethod("Session.logout", {}, token)
print("=* IpAddressGroups sync completed *=")
