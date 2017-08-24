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
r"""Import variant data in a VCF file to a BigQuery variants table.

Example usage:

python import_vcf_to_bigquery.py \
    --source-vcf "gs://BUCKET_NAME/PATH/TO/variants.vcf.gz" \
    --project "PROJECT_ID" \
    --dataset "DATASET_NAME" \
    --variantset "VARIANTSET_NAME" \
    --destination-table "PROJECT_ID.DATASET_NAME.TABLE_NAME" \
    --expand-wildcards
"""

import argparse
import logging

import vcf_to_bigquery_utils


def _parse_arguments():
  """Parses command line arguments.

  Returns:
    A Namespace of parsed arguments.
  """
  parser = argparse.ArgumentParser(
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
      "--source-vcf",
      nargs="+",
      required=True,
      help=("Cloud Storage path[s] to [gzip-compressed] VCF file[s],"
            " wildcards accepted (* but not **)."))
  parser.add_argument(
      "--project",
      required=True,
      help="Cloud project for imported Google Genomics data.")
  parser.add_argument(
      "--dataset",
      required=True,
      help=("Google Genomics dataset name or id"
            " (existing datasets will be appended)."))
  parser.add_argument(
      "--variantset",
      required=True,
      help=("Google Genomics variant set name or id"
            " (existing targets will be appended)."))
  parser.add_argument(
      "--new-dataset",
      action="store_true",
      help="Create a new dataset, even if one with this name exists.")
  parser.add_argument(
      "--new-variantset",
      action="store_true",
      help="Create a new variant set, even if one with this name exists.")
  parser.add_argument(
      "--expand-wildcards",
      action="store_true",
      help="Expand wildcards in VCF paths and use parallel imports.")
  parser.add_argument(
      "--destination-table",
      required=True,
      help="Full path to destination BigQuery table "
           "(PROJECT_ID.DATASET_NAME.TABLE_NAME).")
  parser.add_argument(
      "--description",
      help="Description for destination BigQuery table.")

  return parser.parse_args()


def main():
  args = _parse_arguments()
  logging.basicConfig(level=logging.INFO)

  uploader = vcf_to_bigquery_utils.VcfUploader(args.project)
  uploader.upload_variants(dataset=args.dataset,
                           variantset=args.variantset,
                           source_vcfs=args.source_vcf,
                           destination_table=args.destination_table,
                           expand_wildcards=args.expand_wildcards,
                           new_dataset=args.new_dataset,
                           new_variantset=args.new_variantset,
                           description=args.description)


if __name__ == "__main__":
  main()
