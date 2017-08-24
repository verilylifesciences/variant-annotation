#!/bin/bash

# Copyright 2017 Verily Life Sciences Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# Download dbNSFP from Google Drive per
#   https://sites.google.com/site/jpopgen/dbNSFP
#
# Args:
#   $1: The GoogleDrive file id.
#   $2: The destination filename.

set -o nounset
set -o errexit

# Default value is for dbNSFPv3.4c.zip
readonly DEFAULT_FILEID=${FILEID:-0B60wROKy6OqcaWJ4Y0xvR2k1aUU}
readonly DRIVE_FILEID=${1:-$DEFAULT_FILEID}
readonly DESTINATION=${2:-dbNSFP.zip}

# The following code will download a large world-readable file from Google
# Drive. Implementation adapted from http://stackoverflow.com/a/43478623
curl -c /tmp/cookie -L -o /tmp/probe.bin \
  "https://drive.google.com/uc?export=download&id=${DRIVE_FILEID}"
confirm=$(tr ';' '\n' </tmp/probe.bin | grep confirm)
confirm=${confirm:8:4}
curl -C - -b /tmp/cookie -L -o "${DESTINATION}" \
  "https://drive.google.com/uc?export=download&id=${DRIVE_FILEID}&confirm=${confirm}"
