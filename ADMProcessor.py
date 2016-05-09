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
from __future__ import generators
import json

from jsonschema import validate

from Validators import Validator


class ampParameterOid(object):
    # parameters are formatted as (type,VALIDATED value) tuples
    def __init__(self, admItem=None, itemName=None):
        self.admItem = admItem
        self.name = itemName
        self.parameters = list()


class AmpSingleCommandBuilder(object):
    def __init__(self, admItem, admProc, type=None):
        if admItem is None:
            raise ValueError('Invalid admItem')
        self.admItem = admItem
        self.admProc = admProc

        if type is not None:
            self.type = type
        else:
            self.type = admItem['midType']

    def __call__(self, *args, **kwargs):
        return self.admProc.CreateParameterizedOid(self.type, None, self.admItem, *args, **kwargs)


class JSONADMProcessor(object):
    def __init__(self):
        self.jsonData = {};
        # The schema currently exists in a file, but will likely be inlined.
        # When that happens, the following lines will have to change
        self.schema = json.load(open("ADM/ADMSchema.json"))
        self.passInvalidAtomics = True

    def AddADMText(self, text):
        # Validate the JSON in the text
        try:
            tempJson = json.loads(text)
            validate(tempJson, self.schema)
            admName = tempJson["name"]
        except:
            raise

        self.jsonData[admName] = tempJson

    def AddADMFile(self, filename):
        file = open(filename)

        self.AddADMText(file.read())

    def GetADMItem(self, type, elementName):
        # try:
        for (admName, admData) in self.jsonData.iteritems():
            try:
                if elementName in admData[type]:
                    retADM = admData[type][elementName]
                    retADM['midType'] = type
                    retADM['name'] = elementName
                    return retADM
            except KeyError:
                pass
        if self.passInvalidAtomics == True and type == 'atomic':
            retADM = {}
            retADM['midType'] = type
            retADM['name'] = elementName
            return retADM
        # Search failed, throw
        raise ValueError('Cannot find ADM')

    def CreateValidator(self, type, searchCriteria):
        try:
            admItem = self.GetADMItem(type, searchCriteria)
        except ValueError:
            pass
            # Is this a datalist/multi-element validator
            # if type(admItem['validator']) == list:
            #    outValidator =
            # return outValidator

    def CreateParameterizedOid(self, type, searchCriteria=None, foundAdm=None, *args):
        admParameters = []
        if foundAdm == None:
            try:
                admItem = self.GetADMItem(type, searchCriteria)
                admParameters = admItem['parameters']
            except ValueError:
                return None
        else:
            admItem = foundAdm
            admParameters = admItem['parameters']

        # Check length of parameters
        # if len(admParameters) != len(args):
        #    raise AttributeError('incorrect length %d %d ' % (len(admParameters), len(args)))
        #    return None

        ampCommandItem = ampParameterOid(admItem)
        ampCommandItem.type = type
        ampCommandItem.name = searchCriteria
        ampCommandItem.admItem = admItem

        for data, parameter in zip(args, admParameters):
            # Create validator
            validator = Validator.factory(parameter['type'])(parameter['validator'])
            # For named arguments
            try:
                validator.parameterNames = parameter['names']
            except KeyError:
                pass
            ampCommandItem.parameters.append((parameter['type'], validator.validate(data)))
        return ampCommandItem

    def getValidator(self, midType=None, name=None, admItem=None):
        validator = None
        try:
            if admItem == None:
                admItem = self.GetADMItem(midType, name)
            try:
                admFormat = admItem['format']
            except KeyError:  # We're in a subvalidator
                admFormat = admItem
            admType = admFormat['type']
        except ValueError:
            return None

        try:
            admValidator = admFormat['validator']
        except KeyError:
            admValidator = admType
        # Check if this is a "simple" validator
        print admValidator
        if type(admValidator) is not dict:
            validator = Validator.factory(admValidator)(admValidator)
        else:
            # Create validator
            validator = Validator.factory(admType)(admValidator)
            # For named arguments
            try:
                print 'Named arguments: ' + str(admValidator['names'])
                validator.parameterNames = admValidator['names']
            except KeyError:
                pass

        return validator

    # Return a list of every ADM which is currently loaded
    def getADMNames(self):
        return self.jsonData.keys()

    # Return a list of every MID of a given type for a given ADM
    def GetADMMidList(self, admName, midType):
        try:
            return self.jsonData[admName][midType].keys()
        except KeyError:
            raise AttributeError
