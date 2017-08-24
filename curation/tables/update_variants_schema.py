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
"""Tool to update a variants table schema with field descriptions.
"""

import argparse

import schema_update_utils


def _parse_arguments():
  """Parses command line arguments.

  Returns:
    A Namespace of parsed arguments.
  """
  parser = argparse.ArgumentParser(
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
      '--source-vcf',
      required=True,
      help='Path to local or remote (Cloud Storage) VCF or gzipped VCF file.')
  parser.add_argument(
      '--destination-table',
      required=True,
      help='Full path to destination table '
           '(PROJECT_ID.DATASET_NAME.TABLE_NAME)')
  return parser.parse_args()


def main():
  args = _parse_arguments()

  schema_update_utils.update_table_schema(args.destination_table,
                                          args.source_vcf)


if __name__ == '__main__':
  main()
