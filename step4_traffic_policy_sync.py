#!/usr/bin/python3
# ---------------------------------------------------
# Tested on Kerio OS / Kerio control 9.3.1 build 3465
# ---------------------------------------------------

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

print("=* Syncing Traffic Rules (Traffic Policy) *=")
ip_address = masterserver
session = callMethod("Session.login", {"userName": username, "password": password, "application": {"vendor": "Kerio", "name": "Control Api", "version": "Python"}})
token = session["result"]["token"]
#print("Masterserver token:", token)
request = callMethod("TrafficPolicy.get", {}, token)
trafficrulesListMaster = request["result"]["list"]
defaultRule = callMethod("TrafficPolicy.getDefaultRule", {}, token)
callMethod("Session.logout", {}, token)

# print("Traffic rules on Masterserver:")

# for a, trafficruleMaster in enumerate(trafficrulesListMaster):
#    print(a, trafficruleMaster)

# print("Default Traffic Rule:")
# print(defaultRule["result"])

for i, slaveserver in enumerate(slaveservers):
    # for slaveserver in slaveservers:
    ip_address = slaveserver
    session = callMethod("Session.login", {"userName": username, "password": password, "application": {"vendor": "Kerio", "name": "Control Api", "version": "Python"}})
    token = session["result"]["token"]
#    print("Slaveserver", i, "token:", token)
    request = callMethod("TrafficPolicy.get", {}, token)
    trafficrulesListSlave = request["result"]["list"]
    if trafficrulesListMaster == trafficrulesListSlave:
        print("TrafficPolicy configuration on Slaveserver", i, "is exactly the same as on the Masterserver. No operation is needed.")
        if i == 0:
            i = 1
        elif i == len(slaveservers):
            break
        continue
# Request:  {"jsonrpc":"2.0","id":1,"method":"TrafficPolicy.set","params":{ ... }}
# Response: {"jsonrpc":"2.0","id":1,"result":{"errors":[]}}
    request = callMethod("TrafficPolicy.set", {"rules": trafficrulesListMaster, "defaultRule": defaultRule["result"]}, token)
    print("Slaveserver", i, "Traffic Policy set response:", request["result"])
# --- Requests needed to avoid cutting-off
# In some cases you are required to call methods Session.getConfigTimestamp and Session.confirmConfig
# in order to confirm you are still able to connect to firewall with new configuration.
# This mechanism protects you from cutting yourself from the firewall.
# Otherwise your changes will be lost after 30 seconds automatically.
# https://manuals.gfi.com/en/kerio/api/control/reference/cutoff_prevention.html

# Request:  {"jsonrpc":"2.0","id":2,"method":"Session.getConfigTimestamp"}
# Response: {"jsonrpc":"2.0","id":2,"result":{"clientTimestampList":[{"name":"config","timestamp":517}]}}
    configTimestampRequest = callMethod("Session.getConfigTimestamp", {}, token)
    configTimestampResponse = configTimestampRequest["result"]
    print("Slaveserver", i, "Config timestamp for 'TrafficPolicy.set' operation response:", configTimestampResponse)
# Request:  {"jsonrpc":"2.0","id":3,"method":"Session.confirmConfig","params":{"clientTimestampList":[{"name":"config","timestamp":517}]}}
# Response: {"jsonrpc":"2.0","id":3,"result":{"confirmed":true}}
    confirmConfigRequest = callMethod("Session.confirmConfig", configTimestampResponse, token)
    print("Slaveserver", i, "Config confirm for 'TrafficPolicy.set' operation response:", confirmConfigRequest["result"])
    callMethod("Session.logout", {}, token)
print("=* Traffic Rules (Traffic Policy) sync completed *=")
