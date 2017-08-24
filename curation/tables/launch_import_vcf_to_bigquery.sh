#!/bin/bash
#
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
#
# Launch VCF importing code using parameter values set in environment variables.
# ${SOURCE_VCFS} is a single environment variable that optionally refers to
# multiple files, separated by whitespace and optionally quote-delimited.

# TODO: Copy local ${SOURCE_VCFS} to Cloud Storage if they are remote (HTTP or
#   FTP) or local. Also uncompress input files for faster imports.

# Handle quotes in VCF paths in original job array list with an eval.
eval source_vcfs_array=("${SOURCE_VCFS}")
python /usr/local/bin/import_vcf_to_bigquery.py \
  --source-vcf "${source_vcfs_array[@]}" \
  --project "${PROJECT}" \
  --dataset "${DATASET}" \
  --variantset "${VARIANTSET}" \
  --destination-table "${TABLE}" \
  --description "${SOURCE_VCFS}" \
  --expand-wildcards
