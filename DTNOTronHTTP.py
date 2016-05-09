#!/usr/bin/env python
#
# Copyright 2015-2016 INSYEN, AG
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

from twisted.web import server
from twisted.internet import reactor
from twisted.web.resource import Resource
import calendar
from datetime import datetime
import json
from CommandProcessor import *
from time import mktime


class DTNOTronHTTPCommands(object):
    def __init__(self, commandProcessor):
        self.commandProcessor = commandProcessor

    def status(self, jsonData):
        print 'in Status'
        try:
            reportResult = self.commandProcessor.ProcessCommand(SystemCommand('getNodeReports',
                                                                              {'maxReports': 5,
                                                                               'nodeNum': jsonData['node2monitor']}))
            print 'Have %d results' % len(reportResult)

            outReports = {}
            # Show a blank page if we don't have any data
            if len(reportResult) == 0:
                print '0 reports'
                return CommandStatus(CommandStatus.status_ok, {})

            # Add the timestamp value
            outReports['timestamp'] = mktime(reportResult[0]['reportTime'].timetuple())

            for report in reportResult:
                outReports['%s @ %s' % (report['reportMid'], str(report['reportTime']))] = str(report['value'])

        except AttributeError as e:
            print e
            return CommandStatus(CommandStatus.status_error)
        return CommandStatus(CommandStatus.status_ok, outReports)


class TwistedHTTPActions(Resource):
    isLeaf = True

    def __init__(self, CommandProcessor, config):
        Resource.__init__(self)
        self.CommandProcessor = CommandProcessor
        self.config = config
        self.httpFunctions = DTNOTronHTTPCommands(CommandProcessor)

        # Lambda functions for conversion
        timeConverter = lambda v: calendar.timegm(v.timetuple())

        self.actionTranslations = {'add': 'addContact', 'delete': 'deleteContact',
                                   'addReportTemplate': 'addReportTemplate',
                                   'removeReportTemplate': 'removeReportTemplate'
            , 'addNode': 'addNode', 'removeNode': 'removeNode', 'updateNode': 'updateNode',
                                   'update': 'getContacts'}
        self.parameterTranslations = {'to': 'toNode', 'from': 'fromNode', 'nodes': 'nodeList', 'stopTime': 'endTime',
                                      'delay': 'owltDelay'}
        self.parameterTypeTranslations = {'startTime': datetime.fromtimestamp, 'endTime': datetime.fromtimestamp,
                                          'protocol': lambda v: v.lower()}
        self.returnedResultTypeTranslations = {'startTime': timeConverter, 'endTime': timeConverter,
                                               'protocol': lambda v: v.upper()}
        self.permittedActions = ['add', 'delete', 'update', 'status', 'addReportTemplate', 'removeReportTemplate',
                                 'addNode', 'removeNode', 'updateNode', 'getNodes', 'getReports',
                                 'getCommandGenerators',
                                 'getProtocolDefaults', 'getReportingMids', 'getReportTypes', 'getReportDefaults',
                                 'getNodeReports']

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

    def translateKeyValues(self, inData, keyTranslators, valueTranslators, deleteUnmappable=False):
        outData = {}
        unmappable = False
        for key, value in inData.iteritems():
            if keyTranslators is not None:
                try:
                    key = keyTranslators[key]
                except KeyError:
                    unmappable = True
                    pass
            if valueTranslators is not None:
                try:
                    value = valueTranslators[key](value)
                except KeyError:
                    unmappable = True
                    pass
            if deleteUnmappable == True & unmappable == True:
                continue
            outData[key] = value
            unmappable = False

        return outData

    def render_POST(self, request):
        self.sendHeaders(request)
        commandResult = None
        newData = request.content.getvalue()
        reqData = json.loads(newData)
        # Set default return status for DTNOTron web frontend
        statusText = b"{\n\"\": \"\"\n}"
        # Call DTNMP management function
        action = reqData['action']
        actionName = None
        del reqData['action']
        ##This is a stub for an access control system...
        ret = 500
        if action in self.permittedActions:
            try:
                # Build command
                # First, check if this is a command which we can process from within the HTTP system.
                try:
                    commandResult = getattr(self.httpFunctions, action)(reqData)
                    actionName = 'httpFunction'
                except AttributeError:
                    # It wasn't, check for commandprocessor-based functions
                    try:
                        actionName = self.actionTranslations[action]

                    except KeyError:
                        actionName = action

                    outCommand = SystemCommand(actionName)
                    outCommand.__dict__.update(
                        self.translateKeyValues(reqData, self.parameterTranslations, self.parameterTypeTranslations))

                    # outCommand.setParameters(dict(map(lambda (k,v):if self.parameterTranslations.(self.parameterTranslations[k],v) ,reqData.iteritems())))
                    commandResult = self.CommandProcessor.ProcessCommand(outCommand)

                # We should have a command result
                if commandResult == None:
                    ret = 500

                elif commandResult.status == CommandStatus.status_ok:
                    ret = 200
                    # if commandStatus.data != None:
                    if actionName == 'updateNode':
                        outputDict = {k: 'valid' if v is True else 'invalid' for k, v in commandResult.data.iteritems()}
                        statusText = json.dumps({'nodeStatus': outputDict})

                    elif actionName == 'getContacts':
                        nodeData = []
                        for item in commandResult.data:
                            itemDict = self.translateKeyValues(item.__dict__,
                                                               None, self.returnedResultTypeTranslations)
                        try:
                            itemDict = self.translateKeyValues(itemDict,
                                                               {v: k for k, v in self.parameterTranslations.items()},
                                                               None)
                            nodeData.append(itemDict)
                        except UnboundLocalError:
                            pass

                        statusText = json.dumps({'listOfLinks': nodeData})
                    elif actionName == 'httpFunction':  # We assume that the native function performs output processing
                        statusText = json.dumps(commandResult.data)
                        print statusText
                    # General catch-alls
                    else:
                        print 'In catchall %s' % str(type(commandResult.data))
                        if type(commandResult.data) is list:

                            outputList = []

                            for item in commandResult.data:
                                if type(item) is dict:
                                    try:
                                        print item
                                        outputList.append(item)
                                    except:
                                        continue
                            if len(outputList) == 0:
                                outputList = commandResult.data
                        elif type(commandResult.data) is dict:
                            outputList = [commandResult.data]
                        else:
                            pass

                        try:
                            statusText = json.dumps({actionName: outputList})
                        except UnboundLocalError:
                            pass

                elif commandResult.status == CommandStatus.status_error:
                    ret = 500

            except AttributeError:
                raise

        else:
            print "Action not permitted for user"
            ret = 500

        request.setResponseCode(ret)
        return statusText

    @staticmethod
    def render_GET(request):
        return

    def render_OPTIONS(self, request):
        self.sendHeaders(request)
        # request.responseHeaders.addRawHeader('Content-type', 'application/json')
        request.setResponseCode(204)
        return ''


class EventClass:
    def AddListener(self, listener):
        self.listeners.append(listener)

    def SendMessage(self, message):
        for listener in self.listeners:
            listener(message)


class FrontendInterface():
    def SetCommandProcessor(self, processor):
        self.commandProcessor = processor

    def SetConfig(self, config):
        self.config = config

    def start(self):
        pass

    def stop(self):
        pass


class DTNOTronHTTP(FrontendInterface):
    def __init__(self, commandProcessor=None):
        self.CommandProcessor = commandProcessor

    def start(self):
        site = server.Site(TwistedHTTPActions(self.CommandProcessor, self.config))
        reactor.listenTCP(int(self.config['port']), site)
        reactor.run()

    def stop(self):
        reactor.stop()
