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
from TypedDataCollection import TypedDataCollection
from Validators import *
import re


class TCPResponseParser(object):
    validTypeStr = ''
    _intTypeStr = ''

    def __init__(self, type):
        self._intTypeStr = type

    @staticmethod
    def factory(typeStr):
        for subclass in TCPResponseParser.__subclasses__():
            item = subclass.validTypeStr
            if type(item) == list and typeStr in item:
                return subclass(typeStr)
            elif TCPResponseParser.validTypeStr == item:
                return item(typeStr)
        raise ValueError("Internal type couldn't be determined. Type:" + str(typeStr))

    def fromString(self, data):
        return None


# This parser will use the existing validator classes in order to typecast
class ValidatorBasedTCPResponseParser(TCPResponseParser):
    validTypeStr = ['int32', 'uint32', 'int64', 'uint64', 'string', 'real32', 'real64', 'vast', 'uvast']

    def fromString(self, data):
        return Validator.factory(self._intTypeStr)().validate(data)


# This parser works for DCs
class DCTCPResponseParser(TCPResponseParser):
    validTypeStr = ['dc', 'tdc']
    allowedTypes = ['tdc']

    def fromString(self, data):
        # One condition here: If the DC is a container for TDCs, then the implementation will only allow TDC entries,
        # and we'll punt to the TDC parser

        if len(self.allowedTypes) == 1 and self.allowedTypes[0] == 'tdc':
            outList = TDCTCPResponseParser('tdc').fromString(data)
            # Check if the data is properly formatted
        if data.startswith(b'{') == False and data.endswith(b'}') == False:
            raise ValueError('Invalid DC for response parsing')

        strippedData = data[1:-1]
        # Break the data into elements and validate
        # Note: The implementation doesn't quote-escape strings, at least not at the moment



        #
        # #Otherwise, we perform normally
        # for item in strippedData.split(','):
        #     for type in list(self.allowedTypes):
        #         try:
        #             outList.append(TCPResponseParser.factory(type).fromString(data))
        #
        #         except ValueError:
        #             pass

        # if len(outList) == 0:
        #    raise ValueError("Couldn't process any DC items")
        # else:
        return outList


class TDCTCPResponseParser(TCPResponseParser):
    validTypeStr = 'none'

    def fromString(self, data):
        itemregex = re.compile("\((\S+)\) (\S+)")
        datalists = list()
        charidx = 0
        searchchar = "["
        startchar = 0

        # Note, this emulates the C behavior, and doesn't use recursive regex or outside dependencies
        while charidx != -1:
            charidx = data.find(searchchar, charidx)

            if charidx > 0:
                if searchchar == "[":
                    startchar = charidx + 1
                    searchchar = "]"

                    continue
                else:
                    searchchar = "["
                    curdatalistText = data[startchar:charidx]
                    curdatalist = TypedDataCollection()
                    # Now, break
                    for curitem in curdatalistText.split(","):

                        output = itemregex.match(curitem)
                        if output is None:
                            continue

                        type = output.group(1)
                        valueText = output.group(2)
                        value = TCPResponseParser.factory(type).fromString(valueText)

                        curdatalist.append(type, value)

                    datalists.append(curdatalist)
            else:
                break

        return datalists
