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

FLAGS_HELP="
Runs VEP on one or more files using the pipelines api (via dsub.py) and
writes the output to BigQuery. Positional parameters must be files stored
on GCS (may be gzipped).  Files must be in ensembl format or VCF format.

USAGE: ./run_vep_remote.sh [flags] args
"

if [[ ! -e ./shflags ]]; then
  echo This script assumes https://github.com/kward/shflags is located \
    in the current working directory.  To obtain the file: \
    curl -O https://raw.githubusercontent.com/kward/shflags/master/src/shflags
  exit 1
fi

source ./shflags

DEFINE_string project_id ""  \
  "The Cloud Platform project id to use."

DEFINE_string bucket "" \
  "Bucket to use for temporary files and logging."

DEFINE_string dataset "vep" \
  "BigQuery destination dataset name. The dataset will be created, if needed."

DEFINE_string table_name "testing" \
  "BigQuery destination table name. This table will be created."

DEFINE_string vep_schema_file "./vep_schema.json" \
  "BigQuery schema for VEP annotations."

# The reference genome versions must match between the image and the database.
DEFINE_string docker_image "" \
   "VEP docker image corresponding to the reference genome of the input."

DEFINE_integer shards_per_file 1 \
  "The number of concurrent dsub jobs to run, each working on a separate shard of the input file(s)."

DEFINE_string zones "us-*" \
  "Compute engine zones in which to run dsub."

DEFINE_integer disk_size "200" \
  "Size of dsub data disk."

DEFINE_integer boot_disk_size "30" \
  "Size of dsub boot disk."

DEFINE_integer min_gb_ram 8 \
  "Minimum amount of RAM for dsub."

DEFINE_string docker_script "./vep_into_bigquery_for_docker.sh" \
   "Script that will be run by dsub."

function main() {
  if [[ -z "${FLAGS_project_id}" ]] ; then
    echo "--project_id is required."
    exit 1
  fi

  if [[ -z "${FLAGS_bucket}" ]] ; then
    echo "--bucket is required."
    exit 1
  fi

  if [[ -z "${FLAGS_docker_image}" ]] ; then
    echo "--docker_image is required."
    exit 1
  fi

  local -r description="VEP pipeline on $* using ${FLAGS_docker_image}"

  gsutil \
    cp \
    "${FLAGS_vep_schema_file}" \
    "${FLAGS_bucket}/schema.json"

  bq \
    --project_id "${FLAGS_project_id}" \
    mk -f "${FLAGS_dataset}"

  # Note: this will cause the script to fail if the table already exists.
  bq \
    --project_id "${FLAGS_project_id}" \
    mk --table \
    "${FLAGS_dataset}.${FLAGS_table_name}"

  bq \
    --project_id "${FLAGS_project_id}" \
    update \
    --table \
    --description "${description}" \
    "${FLAGS_dataset}.${FLAGS_table_name}"

  local -r temp_dir=$(mktemp -d)

  # Create TSV file to pass into dsub.
  # Will run VEP in parallel for each of the INPUT_FILE and put the result in
  # BQ_DATASET_NAME.BQ_TABLE_NAME.
  # SHARD_INDEX is 1..NUM_SHARDS
  (
    # Pass input file flags using "=" since the later logic changes spaces to
    # tabs. dsub wants spaces, so we convert the "=" characters after
    # converting spaces.
    echo --input=SCHEMA_FILE \
         BQ_DATASET_NAME \
         BQ_TABLE_NAME \
         --input=INPUT_FILE \
         NUM_SHARDS \
         SHARD_INDEX \
      | tr '= ' ' \t'

    local file
    for file in "$@"; do
      local -i shard_index
      for shard_index in $(seq "${FLAGS_shards_per_file}"); do
        echo "${FLAGS_bucket}/schema.json" \
             "${FLAGS_dataset}" \
             "${FLAGS_table_name}" \
             "${file}" \
             "${FLAGS_shards_per_file}" \
             "${shard_index}"
      done
    done | tr ' ' '\t'
  ) > "${temp_dir}/table.tsv"

  dsub \
    --wait \
    --project "${FLAGS_project_id}" \
    --zones "${FLAGS_zones}" \
    --logging "${FLAGS_bucket}/logging" \
    --image "${FLAGS_docker_image}" \
    --min-ram "${FLAGS_min_gb_ram}" \
    --disk-size "${FLAGS_disk_size}" \
    --boot-disk-size "${FLAGS_boot_disk_size}" \
    --tasks "${temp_dir}/table.tsv" \
    --script "${FLAGS_docker_script}"
}


# Parse the command-line.
FLAGS "$@" || exit $?
eval set -- "${FLAGS_ARGV}"

set -o xtrace
set -o nounset
set -o errexit

main "$@"
