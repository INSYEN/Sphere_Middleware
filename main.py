#!/usr/bin/env python
#
# Copyright 2015 INSYEN, AG
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
from twisted.web import server
from twisted.internet import reactor

import TwistedHTTPActions
from WebActions import WebActions


# from twisted.internet import protocol, reactor, endpoints
configOutline = """[mongodb]
host=localhost
port=12345
bbName=dtnDB

[http]
host=0.0.0.0
port=8090

[dtnmp]
host=localhost
port=12345

[system]
frontendAgent=TwistedHTTPActions;"""
if __name__ == '__main__':
    # Parse the arguments
    print configOutline
    argParser = argparse.ArgumentParser(description='The Alpha backend for Sphere/DTNoTron')
    argParser.add_argument('--configFile', nargs='+', default='middleware.conf', help='Change config file')
    # argParser.add_argument('port',nargs='+',type=int,help='Change listening port')
    args = argParser.parse_args()

    config = ConfigParser.SafeConfigParser()
    config.readfp(io.BytesIO(configOutline))
    # Before anyone yells at me that this will crash if the file/arg doesn't exist. configParser.read will silently ignore
    # invalid file entires, because python gives you just enough rope to hang yourself
    config.read(args.configFile)

    webActions = WebActions(config)
    site = server.Site(TwistedHTTPActions.TwistedHTTPActions(webActions, config))
    reactor.listenTCP(8090, site)
    reactor.run()