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

__author__ = 'jeremy'

from twisted.web.resource import Resource

import json


class TwistedHTTPActions(Resource):
    isLeaf = True

    def __init__(self, webActions, config):
        Resource.__init__(self)
        self.webActions = webActions
        self.config = config
        self.permittedActions = ['add','delete','update','status','addReportTemplate','removeReportTemplate','addNode','removeNode','updateNode']

    def getChild(self, name, request):
        if name == '':
            return self
        return Resource.getChild(self, name, request)

    @staticmethod
    def sendHeaders(request):
        request.responseHeaders.addRawHeader('Access-Control-Allow-Origin', b"*")
        request.responseHeaders.addRawHeader('Access-Control-Allow-Methods', 'GET,HEAD,PUT,PATCH,POST,DELETE')
        request.responseHeaders.addRawHeader('Access-Control-Allow-Headers', 'content-type')
        request.responseHeaders.addRawHeader('Access-Control-Max-Age', 2520)
        request.responseHeaders.addRawHeader('Connection', 'keep-alive')
        request.responseHeaders.addRawHeader(b'Cache-Control', 'no-cache')
        request.responseHeaders.addRawHeader(b"Content-Type", b"application/json; charset=utf-8")

    def render_POST(self, request):
        self.sendHeaders(request)
        newData = request.content.getvalue()
        reqData = json.loads(newData)
        # Call DTNMP management function
        action = reqData['action']
        del reqData['action']

        ret = 200
        self.webActions._status = b"{\n\"\": \"\"\n}"
        ##This is a stub for an access control system...
        if action in self.permittedActions:
            try:
                ret = getattr(self.webActions, action)(reqData)
            except AttributeError:
                #   print "Couldn't find action " + action
                pass
        else:
            print "Action not permitted for user"
            ret=500
        request.setResponseCode(ret)
        return self.webActions._status

    @staticmethod
    def render_GET(request):
        return "test"

    def render_OPTIONS(self, request):
        self.sendHeaders(request)
        # request.responseHeaders.addRawHeader('Content-type', 'application/json')
        request.setResponseCode(204)
        return ''