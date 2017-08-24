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


# This script will preprocess the dbNSFP database according to the
# instructions for the VEP plugin, given here:
#   https://github.com/Ensembl/VEP_plugins/blob/release/87/dbNSFP.pm.
#
# Args:
#   $1: Output path.
#   $2: The dbNSFP input filename.

set -o nounset
set -o errexit

readonly DEFAULT_OUTPUT_PATH=${OUTPUT_PATH:-}
readonly DBNSFP_BASE=${1:-$DEFAULT_OUTPUT_PATH}
readonly DBNSFP_ZIP_FILE=${2:-dbNSFP.zip}

# Process a list of dbNSFP database files by sorting and indexing them with
# tabix.  We sort each chromosome separately, leaving the comment line at the
# top.  Additionally, add "chr" to the start of the chromosome names (column 1).
# Concatenate the resulting files and run tabix to index the final file.
#
# Args:
#   $1: The combined output file name.
#  ...: Input files, typically one per chromosome.
function process_tables() {
  local -r gzip_file="$1"
  shift 1
  local file
  for file in $(printf '%s\n' "$@" | sort); do
    # Write the comment lines for this file.
    awk '/^#/' "${file}"
    # Write the position-sorted non-comment lines for this file.
    awk '!/^#/{print "chr"$0}' "${file}" | \
      sort --key=2,2n --stable --parallel=8
  done | \
    bgzip --threads 8 -c > \
      "${gzip_file}"
  tabix -s 1 -b 2 -e 2 "${gzip_file}"
  # TODO: Determine if "chr" needs to be prepended for GRCh37.
}

main() {
  local -r gzip_file="dbNSFP.gz"
  local -r readme_file=("dbNSFP"*"readme.txt")

  unzip "${DBNSFP_ZIP_FILE}"

  process_tables "${gzip_file}" "dbNSFP"*"chr"*

  if [[ ! -z "${DBNSFP_BASE}" ]] ; then
    # Move the processed files to the output directory.
    mkdir -p "${DBNSFP_BASE}"
    mv "${gzip_file}" "${DBNSFP_BASE}"
    mv "${gzip_file}.tbi" "${DBNSFP_BASE}"
    if [[ -f "${readme_file[0]}" ]] ; then
      mv "${readme_file[0]}" "${DBNSFP_BASE}"
    else
      # TODO: Understand why the readme file is sometimes not found.
      ls
      ls "${readme_file[0]}"
    fi
  fi
}

main "$@"
