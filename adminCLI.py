#!/usr/bin/env python
#
# Copyright 2015 INSYEN, AG
#
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

__author__ = 'jeremy'

import sys
import httplib
import json
class Actions():
    def __init__(self):
        self.http = httplib.HTTPConnection('127.0.0.1',8090)
    def addNode(self,args):
        if len(args) < 3:
            print "Not enough args"
            sys.exit(0)
        nodeData = {'nodeNum':int(args[0]),'hostName':args[1],'port': int(args[2]),'dtnmpEid':'ipn:%s.1'%args[0],'protocol': args[3],'action':'addNode'}
        print nodeData
        self.send(nodeData)
    def addReportTemplate(self,args):
        if len(args) < 2:
            print "Not enough args"
            sys.exit(0)
        reportData  = {'nodeNum':int(args[0]),"mids":args[1].split(','),'action':'addReportTemplate'}
        print reportData
        self.send(reportData)

    def send(self,data):
        self.http.request('POST','/',json.dumps(data))
        res = self.http.getresponse()

        if res.status == httplib.OK:
            print "Successful"
            return 0
        if res.status == httplib.CONFLICT: #We're defining conflict as a duplicate in the dtnotron DB
            print "Failed: Duplicate data"
            return -1

def PrintUsage():
    print "adminCLI <command> <opts>"
    print "commands/options:"
    print "addNode - nodeNumber,host,port,proto"
    print "addReportTemplate - nodeNumber [mids]"
if len(sys.argv)<2:
    PrintUsage()
    sys.exit(0)

args=sys.argv[2:]

actions = Actions()
getattr(actions,sys.argv[1])(args)

