#!/usr/bin/python

# Copyright 2017 Verily Life Sciences Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Assemble an SQL query.

Using a basic pattern for JOINs with variant annotation databases, assemble
templated SQL into a full query that can but run to create an annotated
"all possible SNPs" table.
"""

from __future__ import absolute_import

import argparse
import logging
import sys

from jinja2 import Environment
from jinja2 import FileSystemLoader

SEQUENCE_TABLE_KEY = "SEQUENCE_TABLE"

B37_QUERY_REPLACEMENTS = {
    "SEQUENCE_FILTER": """WHERE chr IN ('chr17', '17')
    AND sequence_start BETWEEN 41196311 AND 41277499""",
    "DBSNP_TABLE": "bigquery-public-data.human_variant_annotation.ncbi_dbsnp_hg19_20170710",
    "CLINVAR_TABLE":
    "bigquery-public-data.human_variant_annotation.ncbi_clinvar_hg19_20170705",
    "THOUSAND_GENOMES_TABLE":
    "bigquery-public-data.human_variant_annotation.ensembl_1000genomes_phase3_hg19_release89",
    "ESP_AA_TABLE":
    "bigquery-public-data.human_variant_annotation.ensembl_esp6500_aa_hg19_release89",
    "ESP_EA_TABLE":
    "bigquery-public-data.human_variant_annotation.ensembl_esp6500_ea_hg19_release89",
}

B38_QUERY_REPLACEMENTS = {
    "SEQUENCE_FILTER": """WHERE chr IN ('chr17', '17')
    AND sequence_start BETWEEN 43045628 AND 43125483""",
    "DBSNP_TABLE": "bigquery-public-data.human_variant_annotation.ncbi_dbsnp_hg38_20170710",
    "CLINVAR_TABLE":
    "bigquery-public-data.human_variant_annotation.ncbi_clinvar_hg38_20170705",
    "THOUSAND_GENOMES_TABLE":
    "bigquery-public-data.human_variant_annotation.ensembl_1000genomes_phase3_hg38_release89",
    "ESP_AA_TABLE":
    "bigquery-public-data.human_variant_annotation.ensembl_esp6500_aa_hg38_release89",
    "ESP_EA_TABLE":
    "bigquery-public-data.human_variant_annotation.ensembl_esp6500_ea_hg38_release89",
}

# The table alias and the query filename must be the same.
B37_ANNOTATION_SOURCES = ["dbSNP",
                          "clinvar",
                          "thousandGenomes",
                          "ESP_AA",
                          "ESP_EA"
                          # TODO: add gnomAD here.
                         ]
B38_ANNOTATION_SOURCES = ["dbSNP",
                          "clinvar",
                          "thousandGenomes",
                          "ESP_AA",
                          "ESP_EA"]


def run(argv=None):
  """Main entry point."""
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "--sequence_table",
      required=True,
      help="Fully qualified BigQuery table name for the reference "
      "genome sequences to be converted to all-possible SNPs.")
  parser.add_argument(
      "--b37",
      dest="is_b37",
      default=True,
      action="store_true",
      help="Use annotation tables aligned to build 37 of the "
      "human genome reference.")
  parser.add_argument(
      "--b38",
      dest="is_b37",
      action="store_false",
      help="Use annotation tables aligned to build 38 of the "
      "human genome reference.")
  parser.add_argument(
      "--output",
      dest="output",
      default="annotated_snps_RENDERED.sql",
      help="Output file to which to write rendered SQL.")
  parser.add_argument(
      "--debug",
      dest="debug",
      action="store_true",
      help="Generate SQL that will yield a small table for testing purposes.")
  args = parser.parse_args(argv)

  sources = B37_ANNOTATION_SOURCES if (
      args.is_b37) else B38_ANNOTATION_SOURCES
  replacements = B37_QUERY_REPLACEMENTS.copy() if (
      args.is_b37) else B38_QUERY_REPLACEMENTS.copy()

  replacements[SEQUENCE_TABLE_KEY] = args.sequence_table

  if not args.debug:
    replacements["SEQUENCE_FILTER"] = ""

  join_template = Environment(loader=FileSystemLoader("./")).from_string(
      open("join_annotations.sql", "r").read())
  join_query = join_template.render(replacements, annot_sources=sources)
  with open(args.output, "w") as outfile:
    outfile.write(join_query)

  check_template = Environment(loader=FileSystemLoader("./")).from_string(
      open("check_joined_annotations.sql", "r").read())
  check_query = check_template.render(replacements, annot_sources=sources)
  sys.stdout.write("""
Resulting JOIN query written to output file %s.  Run that query using the
BigQuery web UI or the bq command line tool.

Be sure to test the result of the JOIN, for example:

%s
""" % (args.output, check_query))

if __name__ == "__main__":
  logging.getLogger().setLevel(logging.INFO)
  run()
