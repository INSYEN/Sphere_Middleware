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
from twisted.internet.protocol import Protocol, ReconnectingClientFactory
from twisted.internet import reactor
import re

class datalistParser():
    def __init__(self):
        self.itemregex=re.compile("\((\S+)\) (\S+)")

    def parse(self,data):
        datalists = list()
        charidx = 0
        searchchar = b"["
        startchar=0

        #Note, this emulates the C behavior, and doesn't use recursive regex or outside dependencies
        while charidx != -1:
            charidx = data.find(searchchar,charidx)

            if charidx > 0:
                if searchchar == "[":
                    startchar=charidx+1
                    searchchar = b"]"

                    continue
                else:
                    searchchar=b"["
                    curdatalistText = data[startchar:charidx]

                    curdatalist=list()
                    #Now, break
                    for curitem in curdatalistText.split(","):

                        output=self.itemregex.match(curitem)
                        if output is None:
                            continue

                        type=output.group(1)
                        valueText= output.group(2)

                        if type=="string":
                            value=valueText
                        elif type=="real32" or type=="real64":
                            value = float(valueText)
                        else:
                            value=int(valueText)

                        curdatalist.append((type,value))
                        datalists.append(curdatalist)
            else:
                break

        return datalists







class DTNMPManager():
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self._extNewVarCallback = None
        self._extNewContactCallback = None
        self.varCallList = dict()
        self.curReportValue = 0

        # Add default variable callbacks
        self.varCallList["total_reports"] = self.intUpdateReportCount
        self.varCallList["num_reports"] = self.intRequestReportPrint
        self.varCallList["CGR_GET_ALL_CONTACTS"] = self.intGenerateContactList;
        self.varCallList["CGR_GET_ALL_RANGES"] = self.intGenerateRangeList;

        self.factory = DTNMPManagerClientFactory()
        self.factory.parent = self
        self._extContactCallback= None
        self._extRangeCallback = None

        reactor.connectTCP(self.host, self.port, self.factory)

    def intGenerateContactList(self,varData):
        dlParser = datalistParser()

        for item in dlParser.parse(varData['value']):
             #Step 1.1: put object into dict
            output = dict();
            output['from']=item[0][1]
            output['to']=item[1][1]
            output['startTime']=item[2][1]
            output['stopTime']=item[3][1]
            output['bitRate']=item[5][1]

            #Step 1.2: Call parent callback
            if self._extNewContactCallback is not None:
                self._extNewContactCallback(output,varData['timestamp'])

    def intGenerateRangeList(self,varData):
        dlParser = datalistParser()

        for item in dlParser.parse(varData['value']):
             #Step 1.1: put object into dict
            output = dict();
            output['from']=item[0][1]
            output['to']=item[1][1]
            output['startTime']=item[2][1]
            output['stopTime']=item[3][1]
            output['delay']=item[4][1]
            #Step 1.2: Call parent callback
            if self._extRangeCallback is not None:
                self._extRangeCallback(output,varData['timestamp'])

    def intUpdateReportCount(self, varData):
        if varData['value'] > self.curReportValue:
            self.curReportValue = varData['value']
            # Perform another callback
            # self.dtnmpManager.GetReports()
            self.SendCommand("ipn:0.0", "reports.number")

    def intRequestReportPrint(self, varData):
        if varData['value'] != 0:
            self.ShowReports(varData['node'])
            self.SendCommand(varData['node'],"reports.delete")

    def varCallbackProcessor(self, varData):
        self.varCallList.get(varData["name"], self.defaultNewVarCallback)(varData)

    def defaultNewVarCallback(self, varData):
        self._extNewVarCallback(varData)

    def SetVarCallback(self, callback):
        self._extNewVarCallback = callback

    def SetContactCallback(self,callback):
        self._extNewContactCallback=callback

    def SetRangeCallback(self,callback):
        self._extNewRangeCallback=callback

    def intVarDetok(self, data):
        regex = "v:(\S+)@(\d+)\\\\(\S+)\((\S+)\)=(.*)"
        for dataChunk in data.split(';'):
            dataChunk = dataChunk.lstrip('\r\n')
            reout = re.match(regex, dataChunk)
            if reout is None:
                print 'No match "' + dataChunk + '"'
                continue
            output = dict()
            output['node'] = reout.group(1)
            output['timestamp'] = reout.group(2)
            output['name'] = reout.group(3)
            output['type'] = reout.group(4)
            output['valuestr'] = reout.group(5)
            print 'name: ' + reout.group(3) + 'val: ' + output['valuestr'] + ' done'
            # This is not a very good type-checker, but we've already checked ourselves 3 times.
            if output['type'] == 'uint32' or output['type'] == 'int32' or output['type'] == 'vast' or output[
                'type'] == 'uvast' or output['type'] == 'real32':
                output['value'] = int(output['valuestr'])
            else:
                output['value'] = str(output['valuestr'])

            self.varCallbackProcessor(output)
            # Twisted specific stuff

    def intSend(self, data):
        udata = data.decode("utf-8")
        asciidata = udata.encode("ascii", "ignore")
        self.factory.send(asciidata)

        print data

    def intReceive(self, data):
        if data[:2] == 'v:':  # Variable!
            # Call internal detokenizer
            self.intVarDetok(data)

    def AddPlan(self, destAddr, toNode, protocol, host, port):
        output = "%s\controls.create.ion_plan_add={[(uvast) %d,(string) %s,(string) %s,(uint32) %d]};" % (
            destAddr, toNode, protocol, host, port)
        # print output
        self.intSend(output)


    def AddContact(self, destAddr, fromNode, toNode, startTime, endTime, xmitRate):
        output = "%s\controls.create.cgr_contact_add={[(uvast) %d,(uvast) %d,(uint64) %d,(uint64) %d,(real32) 1.00,(uint32) %d]};" % (
            destAddr, fromNode, toNode, startTime, endTime, int(xmitRate))
        # print output
        self.intSend(output)

    def AddRange(self, destAddr, fromNode, toNode, startTime, endTime, owlt):
        output = "%s\controls.create.cgr_range_add={[(uvast) %d,(uvast) %d,(uint64) %d,(uint64) %d,(real32) 1.00,(uint32) %d]};" % (
            destAddr, fromNode, toNode, startTime, endTime, int(owlt))
        # print output
        self.intSend(output)

    def AddGroup(self, destAddr, fromNode, toNode, viaNode):
        output = "%s\controls.create.ion_group_add={[(uvast) %d,(uvast) %d,(string) ipn:%d.0]};" % (
            destAddr, fromNode, toNode, viaNode)
        # print output
        self.intSend(output)

    def RemovePlan(self, destAddr, toNode):
        output = "%s\controls.create.ion_plan_remove={[(uvast) %d]};" % (destAddr, toNode)
        # print output
        self.intSend(output)

    def RemoveContact(self, destAddr, fromNode, toNode, startTime):
        output = "%s\controls.create.cgr_contact_remove={[(uvast) %d,(uvast) %d,(uint64) %d]};" % (
            destAddr, fromNode, toNode, startTime)
        # print output
        self.intSend(output)

    def RemoveRange(self, destAddr, fromNode, toNode, startTime):
        output = "%s\controls.create.cgr_range_remove={[(uvast) %d,(uvast) %d,(uint64) %d]};" % (
            destAddr, fromNode, toNode, startTime)
        # print output
        self.intSend(output)

    def RemoveGroup(self, destAddr, fromNode, toNode):
        output = "%s\controls.create.ion_group_remove={[(uvast) %d,(uvast) %d}];" % (destAddr, fromNode, toNode)
        # print output
        self.intSend(output)

    def RegisterNode(self, destAddr):
        output = "%s\manager.register;" % (destAddr)
        # print output
        self.intSend(output)

    def CreateReport(self, destAddr, interval, numevals, reportMids):
        reportString = ""
        for item in reportMids:
            reportString = reportString + "{" + item + "},"

        output = "%s\\reports.time=0,%d,%d,%s;" % (destAddr, interval, numevals, reportString)
        self.intSend(output)

    def ShowReports(self, destAddr):
        output = "%s\\reports.show;" % destAddr
        self.intSend(output)

    def SendCommand(self, destAddr, command):
        output = "%s\\%s;" % (destAddr, command)
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
        print "recv Debug: " + data
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
        print 'Connected.'
        print 'Resetting reconnection delay'
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