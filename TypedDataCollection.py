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

from datetime import datetime
import time
from Validators import Validator


class TypedDataCollection:
    def __init__(self, *args, **kwargs):
        # The internal data is a list of tuples, configured as (type,value)
        self._internalData = map(lambda x: (None, x), args)
        self.ignoreUnmappable = True
        self._dataDict = kwargs
        self._parameterNames = None
        self.validated = False

    def Format(self, validator, parameterNames=None):
        # Special case: If there is an attached dict, we need to first order the data based on keys, then go from there
        self._parameterNames = parameterNames
        if self._parameterNames is not None and self._dataDict is not None and len(self._dataDict) > 0:
            try:
                self._internalData = map(lambda k: (None, self._dataDict[k]), self._parameterNames)
            except KeyError:
                if self.ignoreUnmappable is False:
                    raise ValueError("Missing mapping values in ADM")

            if len(self._internalData) == 0:
                raise ValueError('Values could not be mapped')


        # If we had key-value arguments, they should be in the correct places now
        # Step 1, iterate through the set
        for typeValidator, item in zip(validator, self._internalData):
            # Something is empty, truncate
            if typeValidator is None or item is None:
                break
            # Handle special cases of datetime.datetime
            if type(item[1]) == datetime and typeValidator[1].internalType == int:
                # Create a time value
                insertItem = time.mktime(item[1].timetuple())
            else:
                insertItem = item[1]
            self._internalData.append((typeValidator[0], typeValidator[1].validate(insertItem)))
        # self._internalData = map(lambda (t, v): (t[0], t[1].validate(v[1])), zip(validator, self._internalData))
        self.validated = True

    def getInternalData(self, requireValidation=True):
        if self.validated is True or requireValidation is False:
            return self._internalData
        else:
            raise ValueError

    def setNames(self, parameterNames):
        self._parameterNames = parameterNames

    def append(self, type, value):
        self._internalData.append((type, Validator.factory(type)(type).validate(value)))

    def __getitem__(self, item):
        if type(item) == int:
            return self._internalData[item][1]
        elif type(item) == str:
            if self.validated is False:
                raise ValueError
            else:
                return self._internalData[self._parameterNames.index(item)][1]
        else:
            raise KeyError

    data = property(getInternalData)
