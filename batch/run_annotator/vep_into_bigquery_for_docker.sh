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

# Runs VEP on an ensembl format file or a VCF file using the pipelines api
# (via dsub.py) and writes the output to BigQuery. Positional parameters must
# be files stored on GCS (may be gzipped).

# This script is meant to be run within a docker container to run VEP on a
# single shard of an ensembl format or VCF file.
#
# Takes flags as the environment variables:
# SCHEMA_FILE BQ_DATASET_NAME BQ_TABLE_NAME INPUT_FILE NUM_SHARDS SHARD_INDEX
#
# The following environment variables should be specified in the Docker image,
# since they are properties of the downloaded databases which are specific to
# the image (there is a one-to-one relationship):
# GENOME_ASSEMBLY VEP_SPECIES DBNSFP_BASE
#
# We also allow for including as a module so that the functions (in
# particular apply_shard_file) can be tested.

# Applies shard to $1 in-place.
#
# Args:
#   file: file to be sharded (in-place)
#   shard_count: the number of shards
#   cur_shard: integer from 1...num_shards (inclusive)
#
# Comment lines (starting with #) are always included. Of the remaining lines,
# the index chunk of ceil(num_non_comment_lines / num_shards) lines
# is kept, with the final shard (cur_shard=shard_count) potentially having
# fewer lines.
#
# We use shard_count and cur_shard here because using num_shards and shard_index
# confuses the linter because they are too close to NUM_SHARDS and SHARD_INDEX,
# which aren't actually defined here.
function apply_shard_file() {
  local -r file=$1
  local -ri shard_count=$2
  local -ri cur_shard=$3

  if [[ "${shard_count}" -eq 1 ]]; then
    return
  fi

  local -r temp_sharded_file="${file}.sharded"

  # Pass through the file twice; once to get the number of non-comment lines
  # and then to use that to output the specific shard.
  gawk -vnum_shards="${shard_count}" -vshard_index="${cur_shard}" '
    # Note: line_count and non_comment_line_index refer only to non-comment
    # lines.

    ARGIND==1 {
      if (!/^#/)
        line_count++
      next
    }

    ARGIND==2 && FNR==1 {
      lines_per_shard = int((line_count + num_shards - 1) / num_shards)

      # If num_shards > line_count, then this could be greater than the number
      # of lines, which will lead to empty output files.
      first_line = (shard_index - 1) * lines_per_shard + 1

      # Note: this could be greater than line_count when num_shards > line_count
      # or for num_shards == shard_index. The later will lead to a file with
      # fewer than lines_per_shard non-comment lines.
      last_line = first_line + lines_per_shard - 1
    }

    !/^#/{line_index++}

    /^#/ || (line_index >= first_line && line_index <= last_line) {
      print
    }' "${file}"{,} > "${temp_sharded_file}"

  mv "${temp_sharded_file}" "${file}"
}

if [[ -z "${INPUT_FILE}" ]]; then
  echo 'Running script in bash library mode.'
else
  set -o xtrace
  set -o nounset
  set -o errexit

  # Localize dbNSFP database files.  We can't use dsub to do this for us because
  # the current version (specified by filename or bucket) is only known inside
  # the container.
  gsutil -q cp "${DBNSFP_BASE}.gz" "${TMPDIR}/dbNSFP.gz"
  gsutil -q cp "${DBNSFP_BASE}.gz.tbi" "${TMPDIR}/dbNSFP.gz.tbi"

  if [[ $INPUT_FILE == *.vcf.gz || $INPUT_FILE == *.vcf ]]; then
    # The cut operaton removes any genotype information from the input VCF files
    # (which, in the case of 1k genomes, takes up ~75% of the output JSON file).
    gunzip -cf "${INPUT_FILE}" | cut -f1-8 > /mnt/data/input_file
    readonly FORMAT="vcf"
  else
    gunzip -cf "${INPUT_FILE}" > /mnt/data/input_file
    readonly FORMAT="ensembl"
  fi

  rm "${INPUT_FILE}"

  apply_shard_file /mnt/data/input_file "${NUM_SHARDS}" "${SHARD_INDEX}"

  readonly NUM_CORES=$(grep --count --word-regexp "^processor" /proc/cpuinfo)

  cd "${VEP_BASE}"

  # Depending on the version of dbNSFP used, not all the columns
  # listed below may be available. VEP will issue a warning about
  # those missing columns and run successfully.
  "${VEP_BASE}/vep" \
    --cache \
    --offline \
    --no_stats \
    --allele_number \
    --force_overwrite \
    --fork "${NUM_CORES}" \
    --json \
    --species "${VEP_SPECIES}" \
    --assembly "${GENOME_ASSEMBLY}" \
    --sift b \
    --polyphen b \
    --hgvs \
    --plugin Condel,Condel/config,b \
    --plugin "dbNSFP,${TMPDIR}/dbNSFP.gz,ExAC_Adj_AC,ExAC_Adj_AF,ExAC_nonTCGA_Adj_AC,ExAC_nonTCGA_Adj_AF,ExAC_nonpsych_Adj_AC,ExAC_nonpsych_Adj_AF,GenoCanyon_score,phyloP100way_vertebrate,phyloP20way_mammalian,phastCons100way_vertebrate,phastCons20way_mammalian,SiPhy_29way_logOdds,TWINSUK_AC,TWINSUK_AF,clinvar_rs,Ensembl_geneid,Ensembl_transcriptid,Ensembl_proteinid,LRT_score,ALSPAC_AC,ALSPAC_AF,ESP6500_AA_AC,ESP6500_AA_AF,ESP6500_EA_AC,ESP6500_EA_AF,clinvar_trait,GTEx_V6_gene,GTEx_V6_tissue" \
    --format "${FORMAT}" \
    -i /mnt/data/input_file \
    -o /mnt/data/output.json

  if [[ -s /mnt/data/output.json ]]; then
    bq \
      --quiet \
      load \
      --source_format NEWLINE_DELIMITED_JSON \
      "${BQ_DATASET_NAME}.${BQ_TABLE_NAME}" \
      /mnt/data/output.json \
      "${SCHEMA_FILE}"
  else
    echo "VEP output file empty." >&2
  fi
  if [[ -s /mnt/data/output.json_warnings.txt ]]; then
    # Record any VEP export errors in stdout.  These are typically complaints
    # about unmatched "random" or alternate haplotype contigs in the database.
    echo "JSON warnings reported:"
    cat /mnt/data/output.json_warnings.txt
  fi

fi

