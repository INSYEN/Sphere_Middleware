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
from DBManager import *
from SystemCommand import SystemCommand
import RoutingAlgorithmParent


class NearestNeighbor(RoutingAlgorithmParent):
    def CreateOperations(self, fromNode, toNode, protocol, startTime, endTime, xmitRate, delay):

        # Find plan data and add the plan
        commandStack = []
        commandStack.append(SystemCommand('contact',
                                          {'node': fromNode, 'from': fromNode, 'to': toNode, 'protocol': protocol,
                                           'startTime': startTime,
                                           'endTime': endTime, 'xmitrate': xmitRate, 'delay': delay}))

        # check if we have to create a static routing entry,
        ##first, find nodes which are directly connected
        adjneighbors = self.sess.query(dbNode).filter(dbNode.nodeNum == fromNode)

        for node in adjneighbors:
            adjnodes = self.db.contactCollection.find({'from': node['from']})
            # create query
            notquery = list()
            # notquery.append({'from':srcNode['nodeNum']})
            # Now, search for nodes to create groups with
            for curadj in adjnodes:
                notquery.append({'to': {"$ne": curadj["to"]}})

            if len(notquery) != 0:
                nquery = [{'from': node['to']}] + notquery
                neighbornodes = self.db.contactCollection.find({'$and': nquery})
                # neighbornodes = self.db.contactCollection.find({'$and':[{'from':srcNode['nodeNum']},notquery]})

                print 'DEBUG: # neighboring nodes = %d' % (neighbornodes.count())

                for neighbor in neighbornodes:
                    print '\t\t neighbor ' + str(neighbor['from'])
                    retval.append((
                        'group',
                        {'node': node['from'], 'from': neighbor['to'], 'to': neighbor['to'], 'via': node['to']}))

        return retval
