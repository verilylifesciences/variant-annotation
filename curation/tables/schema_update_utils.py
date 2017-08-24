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
"""Library to update a variants table schema with field descriptions.
"""

import glob
import gzip
import logging
import re

from gcloud import bigquery

# If TensorFlow is installed, use its gfile library.
try:
  from tensorflow import gfile
except ImportError:
  logging.warning('TensorFlow not installed; VCF in Cloud Storage unsupported')


# String length limit for BigQuery table and column descriptions.  See:
#   https://cloud.google.com/bigquery/docs/reference/rest/v2/tables.
_MAX_LENGTH = 1024
_TRUNCATION_WARNING = 'Truncating %s to comply with BigQuery length limits'

_FIXED_VARIANT_FIELDS = {
    'reference_name':
        'An identifier from the reference genome or an angle-bracketed ID '
        'string pointing to a contig in the assembly file.',
    'start': 'The reference position, with the first base having position 0.',
    'end': 'End position of the variant described in this record.',
    'reference_bases':
        'Each base must be one of A,C,G,T,N (case insensitive). Multiple '
        'bases are permitted. The value in the \'start\' field refers to the '
        'position of the first base in the string.',
    'alternate_bases':
        'List of alternate non-reference alleles.',
    'variant_id': 'Google Genomics variant id.',
    'quality': 'Phred-scaled quality score for the assertion made in ALT.',
    'names': 'List of unique identifiers for the variant where available.',
    'call': 'Per-sample measurements.',
}

_FIXED_CALL_FIELDS = {
    'call_set_id':
        'The id of the callset from which this data was exported from the '
        'Google Genomics Variants API.',
    'call_set_name':
        'Sample identifier from source data.',
    'genotype':
        'List of genotypes.',
    'genotype_likelihood':
        'List of genotype likelihoods.',
    'phaseset':
        'If this value is null, the data is unphased.  Otherwise it is phased.',
    'qual': 'Phred-scaled quality score for the assertion made in ALT.',
}


class Descriptions(object):
  """Encapsulate field descriptions as parsed from a VCF."""

  def __init__(self):
    self.filter_description = None
    self.format_fields = {}
    self.info_fields = {}

  @staticmethod
  def _parse_filter_header(line_no, line):
    value = line.split('=', 1)[1]

    m = re.match(r'<ID=([^,]+),Description="(.*)">', value)
    if not m:
      raise ValueError('Failed to parse line %d: %s' % (line_no, line))

    return {'id': m.group(1), 'description': m.group(2)}

  @staticmethod
  def _parse_format_or_info_header(line_no, line):
    value = line.split('=', 1)[1]

    m = re.match(r'<ID=([^,]+),Number=([^,]+),Type=([^,]+),Description="(.*)">',
                 value)
    if not m:
      raise ValueError('Failed to parse line %d: %s' % (line_no, line))

    return {'id': m.group(1), 'description': m.group(4)}

  def add_from_vcf(self, path):
    """Add descriptions from a VCF.

    Args:
      path: Path to local or remote (in Cloud Storage via a "gs://" path, if
          TensorFlow is installed) VCF file, optionally gzip-compressed
          (requires a ".gz" suffix).
    """
    filter_desc = []
    format_fields = {}
    info_fields = {}

    # Handle wildcards in the path by expanding and taking the first file.
    if path.startswith('gs://'):
      path = gfile.Glob(path)[0]
      f = gfile.Open(path)
    else:
      path = glob.glob(path)[0]
      f = open(path)

    # Handle gzipped VCF files.
    if path.endswith('.gz'):
      f = gzip.GzipFile(fileobj=f)

    line_no = 0
    for line in f:
      line_no += 1

      if line.startswith('##FORMAT='):
        header = self._parse_format_or_info_header(line_no, line)
        format_fields[header['id']] = header['description']

      elif line.startswith('##INFO='):
        header = self._parse_format_or_info_header(line_no, line)
        info_fields[header['id']] = header['description']

      elif line.startswith('##FILTER='):
        header = self._parse_filter_header(line_no, line)
        filter_desc.append(header)

      # Reached the end of the VCF header
      if line.startswith('#CHROM'):
        break

    # Update the member fields
    self.filter_description = '\n'.join(
        ['%s: %s' % (item['id'], item['description']) for item in filter_desc])

    # If the filter description is too long, only include the field names.
    if len(self.filter_description) > _MAX_LENGTH:
      logging.warning(_TRUNCATION_WARNING, 'variant filter thresholds')
      self.filter_description = '\n'.join([item['id'] for item in filter_desc])

    self.format_fields = format_fields
    self.info_fields = info_fields


def tokenize_table_name(full_table_name):
  """Tokenize a BigQuery table_name.

  Splits a table name in the format of 'PROJECT_ID.DATASET_NAME.TABLE_NAME' to
  a tuple of three strings, in that order.  PROJECT_ID may contain periods (for
  domain-scoped projects).

  Args:
    full_table_name: BigQuery table name, as PROJECT_ID.DATASET_NAME.TABLE_NAME.
  Returns:
    A tuple of project_id, dataset_name, and table_name.

  Raises:
    ValueError: If full_table_name cannot be parsed.
  """
  delimiter = '.'
  tokenized_table = full_table_name.split(delimiter)
  if not tokenized_table or len(tokenized_table) < 3:
    raise ValueError('Table name must be of the form '
                     'PROJECT_ID.DATASET_NAME.TABLE_NAME')
  # Handle project names with periods, e.g. domain.org:project_id.
  return (delimiter.join(tokenized_table[:-2]),
          tokenized_table[-2],
          tokenized_table[-1])


def update_table_schema(destination_table, source_vcf, description=None):
  """Updates a BigQuery table with the variants schema using a VCF header.

  Args:
    destination_table: BigQuery table name, PROJECT_ID.DATASET_NAME.TABLE_NAME.
    source_vcf: Path to local or remote (Cloud Storage) VCF or gzipped VCF file.
    description: Optional description for the BigQuery table.

  Raises:
    ValueError: If destination_table cannot be parsed.
  """

  dest_table = tokenize_table_name(destination_table)
  dest_project_id, dest_dataset_name, dest_table_name = dest_table

  # Load the source VCF
  descriptions = Descriptions()
  descriptions.add_from_vcf(source_vcf)

  # Initialize the BQ client
  client = bigquery.Client(project=dest_project_id)

  # Load the destination table
  dest_dataset = client.dataset(dest_dataset_name)
  dest_dataset.reload()

  dest_table = dest_dataset.table(dest_table_name)
  dest_table.reload()

  if description is not None:
    dest_table.patch(description=description[:_MAX_LENGTH])
    if len(description) > _MAX_LENGTH:
      logging.warning(_TRUNCATION_WARNING, 'table description')

  # Set the description on the variant fields and the call fields.
  #
  # The (non-fixed) variant field descriptions come from the ##INFO headers
  # The (non-fixed) call fields descriptions can come from the ##FORMAT headers
  #   as well as the ##INFO headers.

  # Process variant fields
  call_field = None
  for field in dest_table.schema:
    if field.name.lower() in _FIXED_VARIANT_FIELDS:
      field.description = _FIXED_VARIANT_FIELDS[field.name.lower()]
      logging.debug('Variant(fixed): %s: %s', field.name, field.description)

    elif field.name in descriptions.info_fields:
      field.description = descriptions.info_fields[field.name]
      logging.debug('Variant(INFO) %s: %s', field.name, field.description)

    elif field.name.lower() == 'filter':
      field.description = descriptions.filter_description

    if field.name == 'call':
      call_field = field

    if field.description is not None and len(field.description) > _MAX_LENGTH:
      logging.warning(_TRUNCATION_WARNING, field.name)
      field.description = field.description[:_MAX_LENGTH]

  # Process call fields
  for field in call_field.fields:
    if field.name.lower() in _FIXED_CALL_FIELDS:
      field.description = _FIXED_CALL_FIELDS[field.name.lower()]
      logging.debug('Call(fixed): %s: %s', field.name, field.description)

    elif field.name in descriptions.format_fields:
      field.description = descriptions.format_fields[field.name]
      logging.debug('Call(FORMAT) %s: %s', field.name, field.description)

    elif field.name in descriptions.info_fields:
      field.description = descriptions.info_fields[field.name]
      logging.debug('Call(INFO) %s: %s', field.name, field.description)

    elif field.name.lower() == 'filter':
      field.description = descriptions.filter_description

    if field.description is not None and len(field.description) > _MAX_LENGTH:
      logging.warning(_TRUNCATION_WARNING, field.name)
      field.description = field.description[:_MAX_LENGTH]

  logging.info('Updating table %s', dest_table.path)
  dest_table.patch(schema=dest_table.schema)
