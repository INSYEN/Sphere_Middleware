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


class Validator(object):
    typeName = None
    validatorData = None
    parameterNames = None

    def __init__(self, validatorData=None):
        self.validatorData = validatorData

    @staticmethod
    def factory(typeName):
        for item in Validator.__subclasses__():
            if type(item.typeName) == list:
                if typeName in item.typeName:
                    return item
            elif typeName == item.typeName:
                return item
        raise ValueError('Could not find validator for type: ' + typeName)

    def validate(self, data):
        if self.internalType is not None:
            try:
                return self.internalType(data)
            except:
                raise ValueError

        elif self.internalType is None:
            raise ValueError
            return None


class intValidator(Validator):
    typeName = ["uint16", "uint32", "uint64", "int16", "int32", "int64", "vast", "uvast"]
    internalType = int


class floatValidator(Validator):
    typeName = ["float32", "float64", "real32", "real64"]
    internalType = float


class stringValidator(Validator):
    typeName = "string"
    internalType = str


class dcValidator(Validator):
    typeName = 'dc'

    def createMultiValidator(self, typeData):
        for type in typeData:
            yield (type, Validator.factory(type)())

    def validate(self, data):
        if self.validatorData is None:
            raise ValueError

        if type(data) != list:
            raise ValueError
        outData = []
        # Iterate through the data
        for item in data:
            outElement = None
            # The validator parameter of a dc can be a dict or a list, if it's a list, then we try things until it
            # validates. however, if it is a dict, then we must pass it as a subvalidator for a TDC
            if type(self.validatorData) == dict:
                validator = Validator.factory(self.validatorData['type'])(self.validatorData['validator'])
                try:
                    validator.parameterNames = self.validatorData['names']
                except KeyError:
                    pass
                outElement = validator.validate(item)
            else:
                for validatorType in self.validatorData:
                    try:
                        outElement = Validator.factory(validatorType).validate(item)
                        break
                    except ValueError:
                        raise
            # Check if there is valid data
            if outElement != None:
                outData.append(outElement)
            else:
                raise ValueError("No validator found for item with Python type %s" % item)

        return outData


class tdcValidator(Validator):
    typeName = 'tdc'

    def createMultiValidator(self, typeData):
        for type in typeData:
            yield (type, Validator.factory(type)())

    def validate(self, data):
        if self.validatorData is None:
            raise ValueError
            # It's possible for a validator to have multiple possible subvalidators, this is currently based on if the
            # first item in the validator is a list
        if type(self.validatorData[0]) is list:
            for potentialValidator in self.validatorData:
                try:
                    data.Format(self.createMultiValidator(potentialValidator), self.parameterNames)
                    return data
                except ValueError:
                    pass
            # Reached end of validator list
            raise ValueError('Could not find a valid subvalidator')

        else:
            try:
                data.Format(self.createMultiValidator(self.validatorData), self.parameterNames)
                return data
            except ValueError:
                raise ValueError('TDC Validation failed')
