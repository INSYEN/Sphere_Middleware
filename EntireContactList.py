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

from RoutingAlgorithmParent import RoutingAlgorithmParent
from DBManager import *
from SystemCommand import SystemCommand


class EntireContactList(RoutingAlgorithmParent):
    def __init__(self, db):
        super(EntireContactList, self).__init__(db)

    def CreateOperations(self, fromNode, toNode, protocol, startTime, endTime, xmitRate, delay):
        # Iterate through, print every single contact.
        contactList = []
        allContacts = self.sess.query(dbContact)
        # self.contactList.append(SystemCommand('contact',{'protocol':protocol,'fromNode':fromNode,'toNode':toNode,'startTime':startTime,'endTime':endTime,'owltDelay':delay,'bitRate':xmitRate}))
        for contact in allContacts:
            print contact
            contactList.append(SystemCommand('contact', contact.SanitizedDict()));
        # Now, provide the dict-based structure
        outputList = {}
        print 'contactList Length: %d' % (len(contactList))
        for node in self.sess.query(dbNode.nodeNum):
            print node
            outputList[node[0]] = contactList

        return outputList
