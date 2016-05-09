#!/usr/bin/env python
#
# Copyright 2016 INSYEN, AG
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
# disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following
# disclaimer in the documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

__author__ = 'Jeremy'
import ConfigParser
import argparse
import io
import importlib

import CommandProcessor

# from twisted.internet import protocol, reactor, endpoints
configOutline = """[DTNOTronHTTP]
host=0.0.0.0
port=8090

[TCPRPCComms]
host=localhost
port=12345

[ADM]
LoadADMS=ADM/IONADM.json
         ADM/CGRADM.json
         ADM/LTPADM.json
         ADM/BPADM.json

[database]
url=postgres://dtnotron:dtnotron@localhost/dtnotron

[system]
frontendAgent=DTNOTronHTTP
DefaultContactListCreator=EntireContactList
DefaultCommandGenerator=IONCommandProducer
ampManager=TCPRPCComms
reportDefaultsFile=reportDefaults.json
protocolDefaultsFile=protocolDefaults.json
"""

if __name__ == '__main__':
    # Parse the arguments
    argParser = argparse.ArgumentParser(description='The Beta backend for DTN-O-Tron')
    argParser.add_argument('--configFile', nargs='+', default='middleware.conf', help='Change config file')
    # argParser.add_argument('port',nargs='+',type=int,help='Change listening port')
    args = argParser.parse_args()

    config = ConfigParser.SafeConfigParser()
    config.readfp(io.BytesIO(configOutline))
    # Before anyone yells at me that this will crash if the file/arg doesn't exist. configParser.read will silently ignore
    # invalid file entires, because python gives you just enough rope to hang yourself
    config.read(args.configFile)

    # Init various components...
    commandProcessor = CommandProcessor.CommandProcessor(config)
    # Start frontend
    frontendStr = config.get('system', 'frontendAgent')
    frontend = getattr(importlib.import_module(frontendStr), frontendStr)(commandProcessor)
    print 'Starting ' + frontendStr
    frontend.SetConfig(dict(config.items(frontendStr)))
    frontend.start()
