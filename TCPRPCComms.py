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
from TypedDataCollection import TypedDataCollection

__author__ = 'jeremy'
from twisted.internet.protocol import Protocol, ReconnectingClientFactory
from twisted.internet import reactor
import re
from ADMProcessor import *
from TCPResponseParsers import *

class TextPrinter(object):
    typeName = None
    internalType = None
    preferredClass = None
    maxLength = 2048;

    @staticmethod
    def factory(typeName, validClass=None):

        for item in TextPrinter.__subclasses__():
            if validClass != None:
                if item.preferredClass == validClass:
                    return item
            elif type(item.typeName) == list:
                if typeName in item.typeName:
                    return item
            elif typeName == item.typeName:
                return item

        raise ValueError("Internal type couldn't be determined")

    def toString(self, data):
        if self.internalType is not None:
            try:
                return self.internalType(data)
            except:
                raise ValueError

        elif self.internalType is None:
            raise ValueError
            return None


class numPrinter(TextPrinter):
    typeName = ["uint32", "uint64", "int32", "int64", "vast", "uvast", "float32"]
    internalType = str


class strPrinter(TextPrinter):
    typeName = 'string'
    internalType = str


class dcPrinter(TextPrinter):
    typeName = 'dc'
    internalType = None

    def toString(self, data):
        outString = '{'
        firstItem = True
        for item in data:
            tempString = TextPrinter.factory("null", item.__class__)().toString(item)+','
            if len(tempString) + len(outString) > self.maxLength:
                #This will need to be split
                raise BufferError(item)
            else:
                outString += tempString

        outString = outString[0:len(outString)-1] +  '}'
        return outString


class tdcPrinter(TextPrinter):
    typeName = 'tdc'
    internalType = None
    preferredClass = TypedDataCollection

    def toString(self, data):
        outString = '['
        firstItem = True
        for item in data.data:
            try:
                tempString = '(%s)%s,' % (item[0], (TextPrinter.factory(item[0])().toString(item[1])))
                outString += tempString

            except ValueError:
                pass

        outString = outString[0:len(outString)-1] + ']'
        return outString

class TCPRPCComms():
    def __init__(self, config,admProc):
        self.host = config['host']
        self.port = int(config['port'])
        self._extNewVarCallback = None
        self._extNewContactCallback = None
        self.varCallList = dict()
        self.curReportValue = 0
        self.maxCommandLength = 4096
        self.factory = DTNMPManagerClientFactory()
        self.factory.parent = self
        self._extContactCallback = None
        self._extRangeCallback = None
        self.lastCommand= []
        self.admProc = admProc
        self.curCommand = []
        self.varCallList["total_reports"] = self.intUpdateReportCount
        self.varCallList["num_reports"] = self.intRequestReportPrint
        reactor.connectTCP(self.host, self.port, self.factory)

    def intUpdateReportCount(self, varData):
        if varData['value'] > self.curReportValue:
            self.curReportValue = varData['value']
            # Perform another callback
            # self.dtnmpManager.GetReports()
            self.SendCommand("ipn:0.0", "reports.number")

    def intRequestReportPrint(self, varData):
        if varData['value'] != 0:
            self.getReports(varData['node'])
            self.SendCommand(varData['node'], "reports.delete")

    def varCallbackProcessor(self, varData):
        self.varCallList.get(varData["name"], self._defaultNewVarCallback)(varData)

    def _defaultNewVarCallback(self, output):
        #Get validator for the given variable, and make sure that it matches the known type
        admData = self.admProc.GetADMItem('atomic',output['name'])
        admFormat = admData['format']

        if admFormat['type'] == output['type'] or output['type'] == 'tdc':
            try:
                output['value'] = self.admProc.getValidator(admItem=admFormat).validate(output['value'])
            except ValueError:
                print 'Validation Error'
                pass
        self._extNewVarCallback(output)

    def SetVarCallback(self, callback):
        self._extNewVarCallback = callback

    def SetSingleVarCallback(self,varType,callback):
        pass

    def intVarDetok(self, data):
        print "caught variable: " + str(data)
        regex = "v:(\S+)@(\d+)\\\\(\S+)\((\S+)\)=(.*)"
        for dataChunk in data.split(';'):
            dataChunk = dataChunk.lstrip('\r\n')
            reout = re.match(regex, dataChunk)
            if reout is None:
                print 'No match "' + dataChunk + '"'
                continue
            output = dict()
            output['node'] = reout.group(1)
            output['timestamp'] = int(reout.group(2))
            output['name'] = reout.group(3)
            output['type'] = reout.group(4)
            output['valuestr'] = reout.group(5)
            output['value'] = TCPResponseParser.factory(output['type']).fromString(output['valuestr'])

        self.varCallbackProcessor(output)

    def _getCommand(self,commandString):
        commandEnd = commandString.find('=;')
        return commandEnd

    def intSend(self, data):
        udata = data.decode("utf-8")
        asciidata = udata.encode("ascii", "ignore")
        curCommand = self._getCommand(asciidata)

        if curCommand == None:
            raise IOError
        else:
            self.curCommand.append(curCommand)
        self.factory.send(asciidata)

    def intReceive(self, data):
        if data[:2] == 'v:':  # Variable!
            # Call internal detokenizer
            self.intVarDetok(data)
        # else: #This is a command response
        #     try:
        #         self.curCommand.
        #     if self._getCommand(data) in self.curCommand:



    def sendControl(self, agentEid, commandModifier, command):
        self.registerNode(agentEid)
        commandText = '%s\controls.%s.%s=' % (agentEid, commandModifier, command.admItem['name'])
        for parameter in command.parameters:
            paramType = parameter[0]
            #Check if we've gone over the "sane" maximium string length
            try:
                outText = TextPrinter.factory(paramType)().toString(parameter[1])
                commandText += outText
            except BufferError as e:
                print 'Command attribute is too long.'

        commandText += ';'
        if len(commandText) > self.maxCommandLength:
            raise AttributeError('Command is too long')

        self.intSend(commandText)

    def sendTimeBasedReport(self, agentEid, frequency, numEvals, requestedMids):
        self.registerNode(agentEid)
        reportString = '%s\\reports.time=0,%d,%d,' % (agentEid, frequency, numEvals)
        for item in requestedMids:
            reportString = reportString + "{" + item + "},"
        reportString += ';'
        self.intSend(reportString)

    def getReports(self, destAddr):
        output = "%s\\reports.show;" % destAddr
        self.intSend(output)

    def registerNode(self, destAddr):
        output = "%s\manager.register;" % (destAddr)
        # print output
        self.intSend(output)

    def deregisterNode(self, ampEid):
        output = "%s\manager.deregister;" % (ampEid)
        self.intSend(output)

    def SendCommand(self,ampEid,command):
        output = "%s\\%s;" % (ampEid, command)
        self.intSend(output)

class DTNMPManagerProtocol(Protocol):
    def __init__(self):
        # Nothing really goes on here
        return

    def connectionMade(self):
        self.factory.connections.append(self)

    def connectionLost(self, reason):
        self.factory.connections.remove(self)

    def dataReceived(self, data):
        print "Debug recv: " + data
        self.factory.recv(data)
        # Check if this is a command response or a variable.

    def dataSend(self, data):
        print "send data: " + data
        self.transport.write(data)


class DTNMPManagerClientFactory(ReconnectingClientFactory):
    protocol = DTNMPManagerProtocol

    def __init__(self):
        self.connections = []

    def startedConnecting(self, connector):
        print 'Started to connect.'

    def buildProtocol(self, addr):
        self.resetDelay()
        proto = self.protocol()
        proto.factory = self

        return proto

    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason
        ReconnectingClientFactory.clientConnectionFailed(self, connector,
                                                         reason)

    def send(self, data):
        for conn in self.connections:
            conn.dataSend(data)

    def recv(self, data):
        self.parent.intReceive(data)
