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

print("=* Syncing Bandwidth management and QoS *=")
ip_address = masterserver
session = callMethod("Session.login", {"userName": username, "password": password, "application": {"vendor": "Kerio", "name": "Control Api", "version": "Python"}})
token = session["result"]["token"]
#print("Masterserver token:", token)
request = callMethod("BandwidthManagement.get", {}, token)
bmConfigMaster = request["result"]["config"]
request = callMethod("BandwidthManagement.getBandwidth", {}, token)
bmRulesMaster = request["result"]["list"]
interfaceIdMaster = bmConfigMaster["rules"][0]["interfaceId"]["id"]
interfaceNameMaster = bmConfigMaster["rules"][0]["interfaceId"]["name"]
#print("BandwidthManagement config on Masterserver:")
# print(bmConfigMaster)
#print("BandwidthManagement list on Masterserver:")
# print(bmRulesMaster)
print("Interface name on Master:", interfaceNameMaster)
print("Interface id on Master:", interfaceIdMaster)
callMethod("Session.logout", {}, token)

# Slave actions
for i, slaveserver in enumerate(slaveservers):
    ip_address = slaveserver
    session = callMethod("Session.login", {"userName": username, "password": password, "application": {"vendor": "Kerio", "name": "Control Api", "version": "Python"}})
    token = session["result"]["token"]
#    print("Slaveserver", i, "token:", token)
    request = callMethod("BandwidthManagement.get", {}, token)
    bmConfigSlave = request["result"]["config"]
    request = callMethod("BandwidthManagement.getBandwidth", {}, token)
    bmRulesSlave = request["result"]["list"]
    interfaceIdSlave = bmConfigSlave["rules"][0]["interfaceId"]["id"]
    interfaceNameSlave = bmConfigSlave["rules"][0]["interfaceId"]["name"]
    #print("BandwidthManagement config on Slaveserver", i, ":")
    # print(bmConfigSlave)
    #print("BandwidthManagement list on Slaveserver", i, ":")
    # print(bmRulesSlave)
    print("Interface name on Slaveserver", i, ":", interfaceNameSlave)
    print("Interface id on Slaveserver", i, ":", interfaceIdSlave)

    # Master server's Interface id and name substitution in bmConfig with Slave's cridentials
    n = 0
    while bmConfigMaster["rules"][n]["interfaceId"]["id"] is not "":
        bmConfigMaster["rules"][n]["interfaceId"]["id"] = bmConfigSlave["rules"][0]["interfaceId"]["id"]
        n += 1
    n = 0
    while bmConfigMaster["rules"][n]["interfaceId"]["name"] is not "":
        bmConfigMaster["rules"][n]["interfaceId"]["name"] = bmConfigSlave["rules"][0]["interfaceId"]["name"]
        n += 1

    request = callMethod("BandwidthManagement.set", {"config": bmConfigMaster}, token)
    print("Slaveserver", i, "'BandwidthManagement.set' response:", request["result"])

    #configTimestampRequest = callMethod("Session.getConfigTimestamp", {}, token)
    #configTimestampResponse = configTimestampRequest["result"]
    #print("Slaveserver", i, "Config timestamp for 'BandwidthManagement.set' operation response:", configTimestampResponse)
    # Request:  {"jsonrpc":"2.0","id":3,"method":"Session.confirmConfig","params":{"clientTimestampList":[{"name":"config","timestamp":517}]}}
    # Response: {"jsonrpc":"2.0","id":3,"result":{"confirmed":true}}
    #confirmConfigRequest = callMethod("Session.confirmConfig", configTimestampResponse, token)
    #print("Slaveserver", i, "Config confirm for 'BandwidthManagement.set' operation response:", confirmConfigRequest["result"])

    # Masterserver's Interface id and name substitution in bmRules with Slave's cridentials
    bmRulesMaster[0]["id"] = bmRulesSlave[0]["id"]
    bmRulesMaster[0]["name"] = bmRulesSlave[0]["name"]
    request = callMethod("BandwidthManagement.setBandwidth", {"list": bmRulesMaster}, token)
    print("Slaveserver", i, "'BandwidthManagement.setBandwidth' response:", request["result"])
    configTimestampRequest = callMethod("Session.getConfigTimestamp", {}, token)
    # Cutting-off prevention procedures (not DRY, maybe will change it later);
    # hope it doesn't needed, because it gives same timestamps with previous operation, but accordingly
    # to manual we should do this because both of used methods
    # (BandwidthManagement.set and BandwidthManagement.setBandwidth) require cutting-off protection)
    configTimestampResponse = configTimestampRequest["result"]
    print("Slaveserver", i, "Config timestamp for 'BandwidthManagement.setBandwidth' operation response:", configTimestampResponse)
    confirmConfigRequest = callMethod("Session.confirmConfig", configTimestampResponse, token)
    print("Slaveserver", i, "Config confirm for 'BandwidthManagement.setBandwidth' operation response:", confirmConfigRequest["result"])
    callMethod("Session.logout", {}, token)
print("=* Bandwidth management and QoS sync completed *=")
