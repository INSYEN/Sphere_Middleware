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

from sqlalchemy import create_engine, ForeignKey, Integer, Enum, Text, Column, DateTime, and_, or_, between, exc, \
    distinct
from sqlalchemy import desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship

import sqlalchemy

base = declarative_base()


class dbBase:
    def SanitizedDict(self):
        retDict = self.__dict__
        retDict.pop('_sa_instance_state', None);
        return retDict


class dbNode(base, dbBase):
    __tablename__ = 'nodes'

    nodeNum = Column(Integer, primary_key=True)
    ampEid = Column(Text)
    hostName = Column(Text, nullable=True)
    protocols = Column(JSONB)
    commandGenerator = Column(Text, default="default")
    reportsToRun = Column(ARRAY(Integer))
    activeReports = Column(ARRAY(Integer), default=[])

    def fromSystemCommand(self, command):
        self.nodeNum = command.nodeNum
        self.ampEid = command.ampEid
        self.hostName = command.hostName
        self.protocols = command.protocols
        self.commandGenerator = command.commandGenerator
        self.reportsToRun = command.reportsToRun


class dbContact(base, dbBase):
    __tablename__ = 'contacts'

    id = Column(Integer, primary_key=True)
    fromNode = Column(Integer)
    toNode = Column(Integer)
    startTime = Column(DateTime)
    endTime = Column(DateTime)
    bitRate = Column(Integer)
    owltDelay = Column(Integer)
    contactStatus = Column(Enum('pending', 'valid', name='contactValidityEnum'))
    reportedTime = Column(DateTime, nullable=True, default=None)
    protocol = Column(Text)
    # extraData = Column(JSON)

    def fromSystemCommand(self, systemCommand):
        # We do it this way to avoid overwriting things that we care about
        self.bitRate = systemCommand.bitRate
        self.owltDelay = systemCommand.owltDelay
        self.startTime = systemCommand.startTime
        self.endTime = systemCommand.endTime
        self.protocol = systemCommand.protocol
        self.bitRate = systemCommand.bitRate
        self.toNode = systemCommand.toNode
        self.fromNode = systemCommand.fromNode
        self.reportedTime = None


class dbReport(base, dbBase):
    __tablename__ = 'reports'
    id = Column(Integer, primary_key=True)
    ampEid = Column(Text)
    reportMid = Column(Text, nullable=True, default=None)
    reportType = Column(Text)
    reportTime = Column(DateTime)
    reportString = Column(Text)
    value = Column(JSONB)


class dbReportConfig(base, dbBase):
    __tablename__ = 'reportConfig'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text)
    type = Column(Enum('state', 'time', name='reportTypeEnum'))
    requestedMIDs = Column(ARRAY(Text))
    reportConfig = Column(JSONB)

    def fromSystemCommand(self, systemCommand):
        try:
            self.id = systemCommand.id
        except AttributeError:
            pass
        self.name = systemCommand.name
        self.type = systemCommand.type
        self.requestedMIDs = systemCommand.requestedMIDs
        self.reportConfig = systemCommand.reportConfig


class DBManager(object):
    def __init__(self, config=None):
        self.SessionFactory = None
        self.engine = None

    def connect(self, *args, **kwargs):
        if len(args) == 1:
            urlAsset = sqlalchemy.engine.url.make_url(args[0])
        elif len(args) == 0 and len(kwargs) > 0:
            urlAsset = sqlalchemy.engine.URL(**kwargs)
        db = create_engine(urlAsset)
        self.engine = db.connect()
        base.metadata.create_all(self.engine)
        self.SessionFactory = sessionmaker(self.engine)
