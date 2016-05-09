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

__author__ = 'jeremy'
import importlib
from DBManager import *
from SystemCommand import SystemCommand
from IONCommandProducer import IONCommandProducer
from collections import defaultdict
from ADMProcessor import *
from datetime import datetime
class CommandStatus(object):
    status_ok, status_error, status_cmd_impossible = range(3)

    def __init__(self, status, data=None):
        self.data = data
        self.status = status

class CommandProcessor(object):
    def __init__(self, config):
        self.systemConfig = config
        self.admProc = JSONADMProcessor()

        for admFile in config.get('ADM','LoadADMS').split():
            print 'Loading ' + admFile
            self.admProc.AddADMFile(admFile)

        self.ampManagerStr = config.get('system', 'ampManager')
        self.ampManager = getattr(importlib.import_module(self.ampManagerStr), self.ampManagerStr)(
            (dict(config.items(self.ampManagerStr))),self.admProc)
        # getattr(sys.modules[__name__],self.ampManagerStr)(dict(config.items(self.ampManagerStr)))
        #Configure status callbacks for the manager interface
#        self.ampManager.SetVarCallback()
        #Set the generic callback for all new reports
        self.ampManager.SetVarCallback(self.reportVarCallback)
        # Start database
        self.db = DBManager()
        self.db.connect(config.get('database', 'url'))
        self.session = self.db.SessionFactory()
        # Start contact list generator
        self.contactListGeneratorStr = config.get('system', 'DefaultContactListCreator')
        self.contactListGenerator = getattr(importlib.import_module(self.contactListGeneratorStr),self.contactListGeneratorStr)(self.db)

        self.defaultCommandProducerStr = config.get('system', 'DefaultCommandGenerator')
        #Create a dict of command producers which are currently in use
        self.commandProducers = {}
        self.commandProducers['default'] = getattr(importlib.import_module(self.defaultCommandProducerStr),
                                                   self.defaultCommandProducerStr)(self.db,self.admProc)
        #Iterate through command producers in order to figure out which reports we need to pay attention to for contact
        #monitoring
        self.contactReportingMids = defaultdict(list)
        for name, commandProducer in self.commandProducers.iteritems():
            for mid in commandProducer.getMonitoringMids():
                self.contactReportingMids[mid].append(commandProducer)
                print 'Monitoring - %s is interested in MID: %s' % (name,mid)

        self.reportDefaults =  json.load(open(config.get('system','reportDefaultsFile')))
        self.protocolDefaults = json.load(open(config.get('system','protocolDefaultsFile')))


    def ProcessCommand(self, command):
        try:
            try:
                return getattr(self, command.action)(command)
            except exc.SQLAlchemyError as e:
                self.session.rollback()
                print "Session rollback. Message: " + str(e)
                #return CommandStatus(CommandStatus.status_error,'Action %s failed due to DB error: full text: %s' % (command.action,str(e)))
        except AttributeError:
            raise

    def GetAddDelActions(self,commandStack,emitterName):
        outputStack = []
        for nodeNum,ampEid,processor in self.session.query(dbNode.nodeNum,dbNode.ampEid,dbNode.commandGenerator):
            commandProcessor = None
            #Special case for if the database is messed up
            if processor is None:
                processor = 'default'

            #Check if there is a cached processor
            try:
                commandProcessor=self.commandProducers[processor]
            except KeyError:
                #There isn't, create one
                commandProcessor=getattr(importlib.import_module(processor),processor)(self.db,self.admProc)
                self.commandProducers[processor]=commandProcessor
            #Now, run
            try:
                outputStack += (getattr(commandProcessor,emitterName)(commandStack[nodeNum],nodeNum))
            except:
                raise

        return outputStack

    def createMonitoringReportsForNode(self,nodeNum=None,ampEid=None):
        try:
            node = self.session.query(dbNode).filter(or_(dbNode.nodeNum == nodeNum,dbNode.ampEid == ampEid)).one()
            self.ampManager.sendTimeBasedReport(node.ampEid, 1, 1,
                                                  self.commandProducers[node.commandGenerator].getMonitoringMids())
        except exc.SQLAlchemyError:
            pass

    # Actions for commands go here
    def addContact(self, command):
        #Test if there is an existing database entry, then we assume failure
        newContact = dbContact()
        newContact.fromSystemCommand(command)
        contactQuery = self.session.query(dbContact).filter_by(**command.GetParameters())
        if contactQuery.count() != 0:
            print "Existing DB entry"
            #We then make the newContact entry equal the previous entry, since we're obviously just updating
            newContact = contactQuery[0]
            #return CommandStatus(CommandStatus.status_error)
        try:
            commandStack = self.contactListGenerator.CreateOperations(command.fromNode, command.toNode,
                                                                      command.protocol.lower(), command.startTime,
                                                                      command.endTime, command.bitRate,
                                                                      command.owltDelay)
        except:
            print 'Error creating operations'
            return CommandStatus(CommandStatus.status_error)
            # We use a separate class to figure out the exact operations which need to be sent
        try:
            outputStack = self.GetAddDelActions(commandStack,'emitAddOperations')
        except Exception as e:
            raise
            print 'Error processing operations. Exception: ' + str(e)
            return CommandStatus(CommandStatus.status_error)

        try:
            print 'Command stack length: %d, output stack length: %d' % (len(commandStack),len(outputStack))
            modifiedNodes = {}
            for ampEid,element in outputStack:
                self.ampManager.sendControl(ampEid, 'create', element)
                modifiedNodes[ampEid] = 1
        except :
            print 'Error sending operations'
            return CommandStatus(CommandStatus.status_error)
        # Fire off a report and add to database
        for ampEid in modifiedNodes.keys():
            self.createMonitoringReportsForNode(ampEid=ampEid)

        newContact.contactStatus='pending'
        try:
            if contactQuery.count() == 0:
                self.session.add(newContact)
            self.session.commit()
        except exc.SQLAlchemyError:
            self.session.rollback()
            print 'Rolling back session...'
            return CommandStatus(CommandStatus.status_error)

        #Check report validity
        self._createReportsForNodes()

        return CommandStatus(CommandStatus.status_ok)


    def deleteContact(self, command):
        #First, check if this contact exists in the database
        searchContact = dbContact()
        searchContact.fromSystemCommand(command)
        try:
            searchContact = self.session.query(dbContact).filter_by(**command.GetParameters()).one()
        except exc.SQLAlchemyError: #There is no current contact
            pass


        commandStack = self.contactListGenerator.CreateOperations(command.fromNode, command.toNode,
                                                                                 command.protocol.lower(),
                                                                                 command.startTime,
                                                                                 command.endTime, command.bitRate,
                                                                                 command.owltDelay)
        # We use a separate class to figure out the exact operations which need to be sent
        outputStack = self.GetAddDelActions(commandStack,'emitRemoveOperations')
        modifiedNodes = {}

        for ampEid,element in outputStack:
            self.ampManager.sendControl(ampEid, 'create', element)
            modifiedNodes[ampEid] = 1

        # Change status to pending
        searchContact.contactStatus = 'pending'

        # Fire off a report and add to database
        for ampEid in modifiedNodes.keys():
            self.createMonitoringReportsForNode(ampEid=ampEid)

        self.session.commit()
        #Check report validity
        self._createReportsForNodes()
        return CommandStatus(CommandStatus.status_ok)

    def getContacts(self, command):
        # Query the database
        contactItems = []
        contactDbEntries = self.session.query(dbContact).filter(or_(
            between(command.startTime, dbContact.startTime, dbContact.endTime),
            between(command.endTime, dbContact.startTime, dbContact.endTime))
        )
        for item in contactDbEntries:
            tempCommand = SystemCommand('none')
            tempCommand.__dict__ = item.__dict__
            tempCommand.__dict__.pop('_sa_instance_state', None);
            contactItems.append(tempCommand)

        return CommandStatus(CommandStatus.status_ok, contactItems)

    # updateNode: Return the validity status of a given node
    # returns true if the node is valid, and false if not.
    def updateNode(self, command):
        retDict = {}
        for nodeNum in command.nodeList:
            if self.session.query(dbContact).filter(and_(dbContact.fromNode == nodeNum,dbContact.contactStatus=='valid',\
                                                         dbContact.reportedTime != None)).count() > 0:
                retDict[nodeNum] = True
            else:
                retDict[nodeNum] = False

        return CommandStatus(CommandStatus.status_ok, retDict)

    # Callbacks
    def reportVarCallback(self, variable):
        report = dbReport()
        report.ampEid = variable['node']
        report.reportTime = datetime.fromtimestamp(variable['timestamp'])
        report.reportMid = variable['name']
        if variable['type'] == 'tdc':
            outList = []
            for tdc in variable['value']:
                outList.append(tdc.getInternalData(False))
            report.value=outList
        else:
            report.value = [variable['value']]
        report.reportString = variable['valuestr']
        report.reportType = variable['type']

        #Check if this MID is in the contact monitoring MID list
        try:
            for commandGenerator in self.contactReportingMids[report.reportMid]:
                contacts = commandGenerator.getContactFromReport(variable)

                if contacts is not None:
                    print 'contacts length: %d' %len(contacts)
                    #We have a contact, query the database to check if it exists
                    for contact in contacts:
                        print 'Found contact: ' + str(contact.GetParameters())
                        contactQuery = self.session.query(dbContact).filter_by(**contact.GetParameters()).limit(1)
                        if contactQuery.count() == 0:
                            #No contact
                            print 'No contact'
                            outContact = dbContact()
                            contact.protocol='unknown'
                            outContact.fromSystemCommand(contact)
                            self.session.add(outContact)
                            self.session.commit()
                            return
                        elif contactQuery.count() == 1:
                            outContact = contactQuery[0]
                            outContact.contactStatus = 'valid'
                            outContact.reportedTime = report.reportTime
                            self.session.commit()
                            return
                        else:
                            print 'Multiple contacts matched query - DB corruption?'
                            break

        except KeyError:
            return
            #Something went wrong OR this MID was uninteresting, squirrel away for later use

        self.session.add(report)
        self.session.commit()

    # Administrative functions
    def addReportTemplate(self, command):
        report = dbReportConfig()
        report.fromSystemCommand(command)
        self.session.add(report)
        self.session.commit()

    def removeReportTemplate(self, command):
        #Remove the entry in every node
        for node in self.session.query(dbNode).filter(dbNode.activeReports.any(command.id)):
            node.activeReports.remove(command.id)
        self.session.query(dbReportConfig).filter(dbReportConfig.id == command.id).delete()
        self.session.commit()

    def addNode(self, command):
        node = dbNode()
        node.fromSystemCommand(command)
        self.session.add(node)
        self.session.commit()

    def removeNode(self, command):
        self.session.query(dbNode).filter(dbNode.nodeNum == command.nodeNum).delete()
        self.session.commit()


    def getNodes(self, command):
        # Query the datbase for all nodes
        nodeEntries = self.session.query(dbNode).all()
        reportEntries = self.session.query(dbReportConfig.id).all()
        reportEntries = map(lambda v:v[0],reportEntries)
        nodeOutputObjects = map(lambda v:v.SanitizedDict(),nodeEntries)
        #Add report validity template
        nodeOutputObjects = map (lambda v:dict(v.items()+[('validReports',reportEntries)]),nodeOutputObjects)

        return CommandStatus(CommandStatus.status_ok,nodeOutputObjects)

    def getReports(self,command):
        reportEntries = self.session.query(dbReportConfig).all()
        reportOutputObjects = map(lambda v:v.SanitizedDict(),reportEntries)
        return CommandStatus(CommandStatus.status_ok,reportOutputObjects)

    #Return all command generators which are known to the system
    def getCommandGenerators(self,command):
        if self.commandProducers is not None:
            print self.commandProducers.keys()
            return CommandStatus(CommandStatus.status_ok,self.commandProducers.keys())

    #Return all reporting MIDS which are known to the system
    def getReportingMids(self,command):
        #Generate top-level list of loaded ADMS
        outDict = {}
        for adm in self.admProc.getADMNames():
            # Get per-ADM values
            try:
                outDict[adm] = self.admProc.GetADMMidList(adm,"atomic")
            except AttributeError:
                pass #If there is no atomic section, we should just continue on

        return CommandStatus(CommandStatus.status_ok,outDict)

    # Get protocol defaults
    def getProtocolDefaults(self,command):
        return CommandStatus(CommandStatus.status_ok,self.protocolDefaults)

    def getReportDefaults(self,command):
        return CommandStatus(CommandStatus.status_ok,self.reportDefaults)

    #Report-related stuff
    # Get the most recent report(s) known to the system
    def getNodeReports(self,command):
        print command.GetParameters().keys()
        if 'nodeNum' in command.GetParameters().keys():
            print 'Adding ampEid'
            try:
                command.ampEid = self.session.query(dbNode.ampEid).filter(dbNode.nodeNum == command.nodeNum).scalar()
            except exc.SQLAlchemyError:
                return None

        reportQuery = self.session.query(dbReport).filter(dbReport.ampEid == command.ampEid)\
        .order_by(desc(dbReport.reportTime))
        try:
            reportQuery = reportQuery.limit(command.maxReports)
        except AttributeError:
            #There wasn't a max report item, we can ignore the exception
            pass
        outList = map(lambda r:r.SanitizedDict(),reportQuery.all())
        for item in outList:
            item['value'] = item['value'][0]

        return outList

    def _createReportsForNodes(self):
        #FYI: If you want to just get the report intervals for time-based reports, use
        # reportFrequencies = self.sess.query(distinct(dbReportConfig.reportConfig['interval'])).
        #                                     join(dbNode,dbNode.reportsToRun.any(dbReportConfig.id)).filter(
        #                                     and_(dbReportConfig.type=='time')).all()
        testNodesAndReports = self.session.query(dbNode,dbReportConfig).filter(dbNode.reportsToRun.any(dbReportConfig.id))
        for node, report in testNodesAndReports:
            if node.activeReports is None or report.id not in node.activeReports:
                if report.type == 'time':
                    self.ampManager.sendTimeBasedReport(node.ampEid,report.reportConfig['interval'],
                                                          report.reportConfig['count'],
                                                          report.requestedMIDs)
                    activeReports = node.activeReports[:]
                    activeReports.append(report.id)
                    node.activeReports = activeReports
                else:
                    print 'report type %s not implemented' % report.reportType

        self.session.commit()
        print 'done'
