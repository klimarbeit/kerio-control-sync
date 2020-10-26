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

print("=* Syncing UrlGroups *=")

ip_address = masterserver
session = callMethod("Session.login", {"userName": username, "password": password, "application": {"vendor": "Kerio", "name": "Control Api", "version": "Python"}})
token = session["result"]["token"]
#print("Masterserver token:", token)
request = callMethod("UrlGroups.get", {"query": {}}, token)
urlgroupsListMaster = request["result"]["list"]
#urlgroupsListMasterTotal = request["result"]["totalItems"]
#print("UrlGroups Total count on Masterserver:",  urlgroupsListMasterTotal)
#print("UrlGroups on Masterserver:")
# for a, urlgroup in enumerate(urlgroupsListMaster):
#    print(a, urlgroup)
callMethod("Session.logout", {}, token)

for i, slaveserver in enumerate(slaveservers):
    ip_address = slaveserver
    session = callMethod("Session.login", {"userName": username, "password": password, "application": {"vendor": "Kerio", "name": "Control Api", "version": "Python"}})
    token = session["result"]["token"]
#    print("Slaveserver", i, "token:", token)
    request = callMethod("UrlGroups.get", {"query": {}}, token)
    urlgroupsListSlave = request["result"]["list"]
    if urlgroupsListMaster == urlgroupsListSlave:
        print("UrlGroups configuration on Slaveserver", i, "is exactly the same as on the Masterserver. No operation is needed.")
        if i == 0:
            i = 1
        elif i == len(slaveservers):
            break
        continue
#    urlgroupsListSlaveTotal = request["result"]["totalItems"]
#    print("UrlGroups Total count on Slaveserver", i, ":", urlgroupsListSlaveTotal)
#    print("UrlGroups on Slaveserver", i, ":")
#    for a1, urlgroup in enumerate(urlgroupsListSlave):
#        print(a1, urlgroup)

# UrlGroups.set only updates the existing UrlGroups, so for full sync I'll use
# UrlGroups.remove -> UrlGroups.apply -> UrlGroups.create -> UrlGroups.apply
# Creating the list of groupIds to remove (all that exists on Slave)
    ids_for_remove_on_slave = []
    for n, urlgroup in enumerate(urlgroupsListSlave):
        ids_for_remove_on_slave.append(urlgroupsListSlave[n]["id"])
#    print(ids_for_remove_on_slave)

# Remove UrlGroups from Slaveserver
    request = callMethod("UrlGroups.remove", {"groupIds": ids_for_remove_on_slave}, token)
    print("Slaveserver", i, "'UrlGroups.remove' response:", request["result"])
    # Apply - Config timestamp - Config confirm
    request = callMethod("UrlGroups.apply", {}, token)
    print("Slaveserver", i, "'UrlGroups.apply' response:", request["result"])
    configTimestampRequest = callMethod("Session.getConfigTimestamp", {}, token)
    configTimestampResponse = configTimestampRequest["result"]
    print("Slaveserver", i, "Config timestamp for 'UrlGroups.apply' operation response:", configTimestampResponse)
    confirmConfigRequest = callMethod("Session.confirmConfig", configTimestampResponse, token)
    print("Slaveserver", i, "Config confirm for 'UrlGroups.apply' operation response:", confirmConfigRequest["result"])

    # Create new UrlGroups on Slaveserver
    request = callMethod("UrlGroups.create", {"groups": urlgroupsListMaster}, token)
    print("Slaveserver", i, "'UrlGroups.create' response:", request["result"]["errors"])
    request = callMethod("UrlGroups.apply", {}, token)
    print("Slaveserver", i, "UrlGroups apply response:", request["result"])
    configTimestampRequest = callMethod("Session.getConfigTimestamp", {}, token)
    configTimestampResponse = configTimestampRequest["result"]
    print("Slaveserver", i, "Config timestamp for 'UrlGroups.apply' operation response:", configTimestampResponse)
    confirmConfigRequest = callMethod("Session.confirmConfig", configTimestampResponse, token)
    print("Slaveserver", i, "Config confirm for 'UrlGroups.apply' operation response:", confirmConfigRequest["result"])
    callMethod("Session.logout", {}, token)
print("=* UrlGroups Sync Completed *=")
