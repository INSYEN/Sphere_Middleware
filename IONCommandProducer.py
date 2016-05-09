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
from TypedDataCollection import TypedDataCollection

__author__ = 'jeremy'

from collections import defaultdict
from SystemCommand import SystemCommand
from ADMProcessor import *
from DBManager import *
from datetime import datetime


class IONCommandProducer(object):
    class InstructionTypes(object):
        contact = None
        range = None
        span = None
        outduct = None
        plan = None

    class AddInstructions(InstructionTypes):
        def __init__(self, admProc):
            self.contact = AmpSingleCommandBuilder(admProc.GetADMItem('controls', 'cgr_contact_add'), admProc)
            self.range = AmpSingleCommandBuilder(admProc.GetADMItem('controls', 'cgr_range_add'), admProc)
            self.span = AmpSingleCommandBuilder(admProc.GetADMItem('controls', 'ltp_span_add'), admProc)
            self.outduct = AmpSingleCommandBuilder(admProc.GetADMItem('controls', 'ion_outduct_add'), admProc)
            self.plan = AmpSingleCommandBuilder(admProc.GetADMItem('controls', 'ion_plan_add'), admProc)

    class DeleteInstructions(InstructionTypes):
        def __init__(self, admProc):
            self.contact = AmpSingleCommandBuilder(admProc.GetADMItem('controls', 'cgr_contact_remove'), admProc)
            self.range = AmpSingleCommandBuilder(admProc.GetADMItem('controls', 'cgr_range_remove'), admProc)
            self.span = AmpSingleCommandBuilder(admProc.GetADMItem('controls', 'ltp_span_remove'), admProc)
            self.outduct = AmpSingleCommandBuilder(admProc.GetADMItem('controls', 'ion_outduct_remove'), admProc)
            self.plan = AmpSingleCommandBuilder(admProc.GetADMItem('controls', 'ion_plan_remove'), admProc)

    class perNodeInstructions(object):
        # def returnDefaultDict(self):
        def __init__(self):
            self.contacts = []
            self.ranges = []

    def __init__(self, db, admProc):
        self.db = db
        self.dbSession = db.SessionFactory()
        self.admProc = admProc
        self.maxContactEntries = 1
        self.maxRangeEntries = 1
        self.addEmitter = self.AddInstructions(self.admProc)
        self.removeEmitter = self.DeleteInstructions(self.admProc)
        self.cachedContacts = {}
        self.cachedRanges = {}

    def emitNamedOperations(self, commandStack, nodeNum, emitter):
        print 'emitNamedOperations ->'
        ampCommandStack = []
        perNodeContacts = defaultdict(self.perNodeInstructions)
        linksConfigured = []

        for operation in commandStack:
            print 'commandStack iteration'
            if operation.action == "contact":
                try:
                    srcNode = self.dbSession.query(dbNode).filter(and_(dbNode.nodeNum == operation.fromNode,
                                                                       dbNode.protocols.has_key(
                                                                           operation.protocol))).one()
                    destNode = self.dbSession.query(dbNode).filter(and_(dbNode.nodeNum == operation.toNode,
                                                                        dbNode.protocols.has_key(
                                                                            operation.protocol))).one()
                except exc.SQLAlchemyError:
                    raise AttributeError('Couldnt find nodes')

                print "New Contact: (%s %d %d %d)" % (
                    srcNode.ampEid, operation.fromNode, operation.toNode, operation.bitRate)
                perNodeContacts[srcNode.ampEid].contacts.append(TypedDataCollection(fromNode=operation.fromNode,
                                                                                    toNode=operation.toNode,
                                                                                    startTime=operation.startTime,
                                                                                    endTime=operation.endTime,
                                                                                    bitRate=operation.bitRate))

                perNodeContacts[srcNode.ampEid].ranges.append(TypedDataCollection(fromNode=operation.fromNode,
                                                                                  toNode=operation.toNode,
                                                                                  startTime=operation.startTime,
                                                                                  endTime=operation.endTime,
                                                                                  owltDelay=operation.owltDelay))

                # The following operations should only be performed for the acting node, and only if these operations havent already been set up
                if operation.fromNode == nodeNum and self.createlinkConfigTuple(operation) not in linksConfigured:
                    ##For LTP contacts
                    if operation.protocol == 'ltp':
                        try:
                            protocolData = destNode.protocols[operation.protocol]
                            if srcNode.cla == 'udp':
                                lsoString = "udplso %s:%d" % (srcNode.hostName, protocolData['port'])

                            ampCommandStack.append((srcNode.ampEid, emitter.outduct([TypedDataCollection(
                                protocol=srcNode.protocol, toNode=operation.toNode, cloCmd="ltpclo")])))
                            # This command tests another feature of the TypedDataCollection implementation, where unused
                            # parameters will be truncated
                            ampCommandStack.append(
                                (srcNode.ampEid, emitter.span([TypedDataCollection(operation.toNode,
                                                                                   protocolData['maxImportSessions'],
                                                                                   protocolData[
                                                                                       'srcNode.maxExportSessions'],
                                                                                   protocolData['srcNode.segSize'],
                                                                                   protocolData['srcNode.sizeLimit'],
                                                                                   protocolData['srcNode.timeLimit'],
                                                                                   protocolData[' srcNode.queueTime'],
                                                                                   protocolData['srcNode.purgeVal'],
                                                                                   lsoString)])))
                            ampCommandStack.append((srcNode.ampEid, emitter.plan(
                                [TypedDataCollection(nodeNum=destNode.nodeNum, protocol=operation.protocol,
                                                     hostName=destNode.nodeNum)])))

                        except KeyError:
                            print "Not all required LTP-related values are present"
                            raise AttributeError
                    else:
                        try:
                            port = destNode.protocols[operation.protocol]['port']
                        except KeyError:  # Can't find the required protocol
                            raise AttributeError

                        ampCommandStack.append((srcNode.ampEid, emitter.plan([TypedDataCollection(
                            nodeNum=destNode.nodeNum, protocol=operation.protocol, hostName=destNode.hostName,
                            port=port)])))
                        # Add list tuple
                        linksConfigured.append(self.createlinkConfigTuple(operation))

            elif operation.command == "group":
                ampCommandStack.append((srcNode.ampEid, emitter.group([TypedDataCollection(fromNode=operation.fromNode,
                                                                                           toNode=operation.toNode,
                                                                                           viaEid=operation.via)])))


        # Now, handle the contacts and ranges (put them at the top of the stack)
        for (nodeEid, nodeData) in perNodeContacts.iteritems():
            print nodeEid + str(len(nodeData.contacts))
            # Split contacts
            if self.maxContactEntries == 0:
                ampCommandStack.insert(0, (nodeEid, emitter.contact(nodeData.contacts)))
            else:
                for entry in [nodeData.contacts[i:i + self.maxContactEntries] for i in xrange(0, len(nodeData.contacts),
                                                                                              self.maxContactEntries)]:
                    print 'entry: ' + str(entry)
                    ampCommandStack.insert(0, (nodeEid, emitter.contact(entry)))

            # Split ranges
            if self.maxRangeEntries == 0:
                ampCommandStack.insert(0, (nodeEid, emitter.range(nodeData.ranges)))
            else:
                for entry in [nodeData.ranges[i:i + self.maxRangeEntries] for i in xrange(0, len(nodeData.ranges),
                                                                                          self.maxRangeEntries)]:
                    ampCommandStack.insert(0, (nodeEid, emitter.range(entry)))

        return ampCommandStack

    def emitAddOperations(self, commandStack, nodeNum):
        return self.emitNamedOperations(commandStack, nodeNum, self.addEmitter)

    def emitRemoveOperations(self, commandStack, nodeNum):
        return self.emitNamedOperations(commandStack, nodeNum, self.removeEmitter)

    # Stuff for report processing
    def _searchAndRemoveCachedReportOrRanges(self, dict, timestamp):
        # Search the provided list
        outItem = None
        for itemTimestamp, item in dict.iteritems():
            if itemTimestamp >= timestamp:  # This is a good candidate
                print 'Found report'
                outItem = item
        if outItem is not None:
            return item
        # No range found, throw a KeyError
        raise KeyError

    def createAbstractContact(self, contact, range):
        outContact = SystemCommand('none')
        outContact.fromNode = contact['fromNode']
        outContact.toNode = contact['toNode']
        outContact.startTime = datetime.fromtimestamp(contact['startTime'])
        outContact.endTime = datetime.fromtimestamp(contact['endTime'])
        outContact.bitRate = contact['bitRate']
        outContact.owltDelay = range['owltDelay']
        print 'Abstract contact: ' + str(outContact)
        return outContact

    def getContactFromReport(self, report):
        # We generate an abstract contact from the generated report, in order to test node integrity
        # The issue is that an abstract report is generated from two components: the contact as well as the range
        # so, we'll cache reports/ranges based on time
        # TODO: Simplify this function
        if report['name'] == 'CGR_GET_ALL_CONTACTS':
            try:
                range = self._searchAndRemoveCachedReportOrRanges(self.cachedRanges, report['timestamp'])
                contact = report['value']
            except KeyError:
                self.cachedContacts[report['timestamp']] = report['value']
                return

        elif report['name'] == 'CGR_GET_ALL_RANGES':
            try:
                contact = self._searchAndRemoveCachedReportOrRanges(self.cachedContacts, report['timestamp'])
                range = report['value']
            except KeyError:
                self.cachedRanges[report['timestamp']] = report['value']
                return
        else:
            return
        print "Found report! %d %d" % (len(self.cachedContacts), len(self.cachedContacts))
        # Now, create the reports
        outReports = []
        for singleContact in contact:
            print singleContact.__dict__
            for singleRange in range:
                #                if singleRange[0] == singleContact[0] and singleRange[1] == \
                #                        singleContact[1] and singleRange[2] == singleContact[2] and \
                #                                singleRange[3] == singleContact[3]:
                if singleRange['startTime'] == singleContact['startTime'] and singleRange['endTime'] == \
                        singleContact['endTime'] and singleRange['fromNode'] == singleContact['fromNode'] and \
                                singleRange['toNode'] == singleContact['toNode']:
                    print 'matched'
                    outReports.append(self.createAbstractContact(singleContact, singleRange))
        return outReports

    def getMonitoringMids(self):
        return ['CGR_GET_ALL_CONTACTS', 'CGR_GET_ALL_RANGES']

    @staticmethod
    def createlinkConfigTuple(operation):
        return (operation.fromNode, operation.toNode, operation.protocol)
