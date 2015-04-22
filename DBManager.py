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
from pymongo import MongoClient


class MongoManager():
    def __init__(self):
        self.client = None
        self.db = None
        self.nodeCollection = None
        self.contactCollection = None

        self.client = MongoClient()
        self.db = self.client.dtnDB
        self.nodeCollection = self.db.NodeCollection
        self.contactCollection = self.db.ContactCollection

    def AddNode(self, node):
        print node
        nodeId = self.nodeCollection.insert(node)

    def AddContact(self, blob):
        if self.contactCollection.find_one(blob) is None:
            contactId = self.contactCollection.insert(blob)

    def FindNode(self, node):
        dbQuery = self.nodeCollection.find_one(node)
        return dbQuery

    def FindContact(self, node):
        dbQuery = self.contactCollection.find_one(node)
        return dbQuery

    def FindNodes(self, node=None):
        dbQuery = self.nodeCollection.find(node)
        return dbQuery

    def FindContacts(self, node=None):
        dbQuery = self.contactCollection.find(node)
        return dbQuery