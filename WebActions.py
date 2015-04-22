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

from collections import OrderedDict
import json
import threading

from DTNMPManager import DTNMPManager
from DBManager import MongoManager

class RoutingAlgorithmParent():
    def __init__(self, db):
        self.db = db

    def CreateOperations(self, fromNode, toNode, protocol, startTime, endTime, xmitRate, delay):
        print "NOTHING HAPPENS HERE"

class EntireContactListRoutingAlgorithm(RoutingAlgorithmParent):
    def __init__(self, db):
        super.__init__(db)
        self.contactList = list()

    def CreateOperations(self, fromNode, toNode, protocol, startTime, endTime, xmitRate, delay):
        #Iterate through, print every single contact.
        allContacts=self.db.contactCollection.find({},_id=False)
        for contact in allContacts:
            self.contactList.append({'contact':contact});
        return self.contactList

class NearestNeighborRoutingAlgorithm(RoutingAlgorithmParent):
    def __init__(self, db):
        return

    def CreateOperations(self, fromNode, toNode, protocol, startTime, endTime, xmitRate, delay):
        # Find plan data and add the plan
        retval = list()
        retval.append(('contact',
                       {'node': fromNode, 'from': fromNode, 'to': toNode, 'protocol': protocol, 'startTime': startTime,
                        'endTime': endTime, 'xmitrate': xmitRate,'delay':delay}))

        # check if we have to create a static routing entry, this is a hack until I get a better grip on mongo
        ##first, find nodes which are directly connected
        adjneighbors = self.db.contactCollection.find({'to': fromNode})

        print '%d ' % (adjneighbors.count())

        for node in adjneighbors:
            print node
            adjnodes = self.db.contactCollection.find({'from': node['from']})
            # create query
            notquery = list()
            #notquery.append({'from':srcNode['nodeNum']})

            for curadj in adjnodes:
                notquery.append({'to': {"$ne": curadj["to"]}})

            if len(notquery) != 0:
                nquery = [{'from': node['to']}] + notquery
                print nquery
                neighbornodes = self.db.contactCollection.find({'$and': nquery})
                #neighbornodes = self.db.contactCollection.find({'$and':[{'from':srcNode['nodeNum']},notquery]})

                print 'DEBUG: # neighboring nodes = %d' % (neighbornodes.count())

                for neighbor in neighbornodes:
                    print '\t\t neighbor ' + str(neighbor['from'])
                    retval.append((
                        'group',
                        {'node': node['from'], 'from': neighbor['to'], 'to': neighbor['to'], 'via': node['to']}))

        return retval

class WebActions():
    def __init__(self,config):
        self.config=config
        self.dtnmpManager = DTNMPManager(config.get('dtnmp','host'), config.getint('dtnmp','port'))
        self.db = MongoManager()
        self.actions = NearestNeighborRoutingAlgorithm(self.db)
        self.dtnmpManager.SetVarCallback(self.varCallback)
        self.curReportValue = 0
        self._status = b"{\n\"token\": \"xxx\"\n}"
        self.reportProductionFrequency = 10
        # Start timer
        self.timerCallback()

    def varCallback(self, varData):
        self.db.db.ReportCollection.insert(varData)

    def timerCallback(self):
        allNodes = self.db.FindNodes()
        print "In timer callback"
        for node in allNodes:
            # Find all reports for this node
            reportsForNode = self.db.db.ConfigCollection.find({'nodeNum': node['nodeNum']})
            if reportsForNode is not None:
                for report in reportsForNode:
                    self.dtnmpManager.CreateReport(node['dtnmpEid'], 10, 1, report['mids'])

        threading.Timer(self.reportProductionFrequency, self.timerCallback).start()

    def status(self, reqData):
        try:
            nodeName = self.db.FindNode({'nodeNum': reqData['node2monitor']})['dtnmpEid']
        except TypeError:
            return 200
        print "nodeName: " + nodeName
        # newestReportSingle = self.db.db.ReportCollection.find_one({'node':nodeName}).sort("timestamp",-1).limit(1)
        newestReportSingle = self.db.db.ReportCollection.find_one({'node': nodeName}, sort=[("timestamp", -1)])
        if newestReportSingle is None:
            return 200

        allReports = self.db.db.ReportCollection.find({'timestamp': newestReportSingle['timestamp'], 'node': nodeName})
        outputReports = OrderedDict()
        for report in allReports:
            outputReports[report['name']] = str(report['value'])
        outputReports['timestamp'] = newestReportSingle['timestamp']
        self._status = json.dumps(outputReports)

        return 200

    def delete(self, reqData):
        print reqData
        contactandgroup = self.actions.CreateOperations(reqData['from'], reqData['to'],
                                                             reqData['protocol'].lower(), reqData['startTime'] ,
                                                             reqData['stopTime'] , reqData['bitRate'], reqData['delay'])
        for operation in contactandgroup:
            curOp = operation[0]
            curData = operation[1]
            curEid = self.db.FindNode({'nodeNum': curData['node']})['dtnmpEid']

            if curOp == "contact":
                srcNode = self.db.FindNode({'nodeNum': curData['from'], 'protocol': curData['protocol']})
                destNode = self.db.FindNode({'nodeNum': curData['to'], 'protocol': curData['protocol']})

                self.dtnmpManager.RemoveContact(curEid, curData['from'], curData['to'], curData['startTime'])
                self.dtnmpManager.RemoveRange(curEid, curData['from'], curData['to'], curData['startTime'])
                self.db.contactCollection.remove(
                    {'from:': curData['from'], 'to:': curData['to'], 'startTime:': curData['startTime'] })
                self.dtnmpManager.RemovePlan(srcNode['dtnmpEid'], destNode['nodeNum'])

            elif curOp == "group":
                # srcNode = self.db.FindNode({'nodeNum': curData['via']})
                self.dtnmpManager.RemoveGroup(curEid, curData['from'], curData['to'])

        return 200

    def add(self, reqData):
        print reqData
        contactandgroup = self.actions.CreateOperations(reqData['from'], reqData['to'],
                                                             reqData['protocol'].lower(), reqData['startTime'] ,
                                                             reqData['stopTime'] , reqData['bitRate'], reqData['delay'])
        for operation in contactandgroup:
            curOp = operation[0]
            curData = operation[1]
            curEid = self.db.FindNode({'nodeNum': int(curData['node'])})['dtnmpEid']

            if curOp == "contact":
                srcNode = self.db.FindNode({'nodeNum': curData['from'], 'protocol': curData['protocol']})
                destNode = self.db.FindNode({'nodeNum': curData['to'], 'protocol': curData['protocol']})

                self.dtnmpManager.AddContact(curEid, curData['from'], curData['to'], curData['startTime'],
                                             curData['endTime'], curData['xmitrate'])
                self.dtnmpManager.AddRange(curEid, curData['from'], curData['to'], curData['startTime'],
                                             curData['endTime'], curData['delay'])
                self.dtnmpManager.AddPlan(srcNode['dtnmpEid'], destNode['nodeNum'], destNode['protocol'],
                                          destNode['hostName'], destNode['port'])

            elif curOp == "group":
                #srcNode = self.db.FindNode({'nodeNum': curData['via']})
                self.dtnmpManager.AddGroup(curEid, curData['from'], curData['to'], curData['via'])

        self.db.AddContact(reqData)
        return 200

    #Handle updates based on timeline shifts, etc
    def update(self,reqData):
        print reqData
        # Craft the node range statement... This could use some refining.
        rangequery = {'$or' : [{ 'startTime': {'$gt': reqData['startTime']}}, {'stopTime': {'$lt': reqData['stopTime']}}]}
        foundcontacts = self.db.db.ContactCollection.find(rangequery,{'_id': False})
        outputContacts = list()
        if foundcontacts.count() != 0:
            #Create block

            for contact in foundcontacts:
                outputContacts.append(contact)

        self._status=json.dumps({'listOfLinks':outputContacts})
        return 200

    # Management actions
    def addNode(self, reqData):
        print "Adding Node"
        # Check if node exists in DB
        if self.db.FindNode(reqData) is not None:
            return 200

        self.db.AddNode(reqData)
        return 200

    def addReportTemplate(self, reqData):
        print "Adding report template"
        if self.db.db.ConfigCollection.find(reqData) is None:
            self.db.db.ConfigCollection.insert(reqData)
            return 200
        else:
            return 500

    def removeReportTemplate(self, reqData):
        print "Removing report template - Not implemented"
        ##STUB

    def removeNode(self, reqData):
        print "Removing node - Someone should implement this"
        #Step 1: Check for all FUTURE contacts which use this node, and fail
        #Step 2: Invalidate
        ##STUB
