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
"""Library to upload VCF files to Google Genomics and BigQuery.
"""

import logging
import time

from apiclient import discovery
from oauth2client.client import GoogleCredentials
from retrying import retry

# Use tensorflow.gfile library, if available, to expand wildcards (optional).
try:
  from tensorflow import gfile
except ImportError:
  gfile = None

import schema_update_utils

class VcfUploader(object):
  """Class for managing a Google Genomics API connection and data transfers.

  Handles finding and creating variant sets and datasets and uploading and
  exporting variants stored in VCF.  The main entry point is
  upload_variants(...), but other intermediate pipeline steps may also be used.
  """

  def __init__(self, project, credentials=None):
    """Create VcfUploader class.

    Args:
      project: Cloud project to use for Genomics objects.
      credentials: Credentials object to use, get_application_default() if None.
    """
    if credentials is None:
      credentials = GoogleCredentials.get_application_default()
    self.project = project
    self.service = discovery.build("genomics", "v1", credentials=credentials)

  @staticmethod
  def find_id_or_name(name, candidates):
    """Find a value linked as "id" or "name" in a collection of dicts.

    Args:
      name: string to search for in "id" and "name" fields.
      candidates: collection of dicts that should have "id" and "name" keys.

    Returns:
      choice["id"] for the unique matching choice (matched by "name" or "id").
      Returns None if no matching choice is found.

    Raises:
      LookupError: If multiple items match the targeted name.
    """
    target_id = None

    for choice in candidates:
      if choice.get("id") == name or choice.get("name") == name:
        if target_id is not None:
          raise LookupError("Found multiple hits for requested name")
        target_id = choice["id"]

    return target_id

  def find_or_create_dataset(self,
                             dataset_name,
                             always_create=False):
    """Finds or creates a Google Genomics dataset by name or id.

    If an existing dataset in the project has a name or ID of dataset_name, it
    will be reused and its id will be returned, unless always_create is True.
    A new dataset will be created if an existing one is not found.

    Args:
      dataset_name: Name or id of existing dataset, or name for a new dataset.
      always_create: Always create a new dataset with the requested name.

    Returns:
      The id of the existing or newly-created Genomics dataset.
    """
    request = self.service.datasets().list(projectId=self.project)
    response = request.execute()

    dataset_id = self.find_id_or_name(dataset_name,
                                      response["datasets"])

    if dataset_id is None or always_create:
      request = self.service.datasets().create(
          body={"name": dataset_name,
                "projectId": self.project})
      response = request.execute()
      dataset_id = response["id"]

    return dataset_id

  def find_or_create_variantset(self,
                                variantset_name,
                                dataset_id,
                                description="",
                                always_create=False):
    """Finds or creates a Google Genomics variant set by name or id.

    If an existing variant set in the project has a name or ID of
    variantset_name, it will be reused and its id will be returned, unless
    always_create is True.  A new variant set will be created if an existing
    one is not found.

    Args:
      variantset_name: Name or id of existing variant set, or name for a new
          variant set.
      dataset_id: Id of the dataset to find or create the variant set.
      description: The description for the variant set.
      always_create: Always create a new variant set with the requested name.

    Returns:
      The id of the existing or newly-created Genomics variant set.
    """
    request = self.service.variantsets().search(
        body={"datasetIds": dataset_id})
    response = request.execute()

    variantset_id = self.find_id_or_name(variantset_name,
                                         response["variantSets"])

    if variantset_id is None or always_create:
      request = self.service.variantsets().create(
          body={"name": variantset_name,
                "datasetId": dataset_id,
                "description": description,
          })
      response = request.execute()
      variantset_id = response["id"]
    return variantset_id

  def import_variants(self, source_uris, variantset_id):
    """Imports variants stored in a VCF file on Cloud Storage to a variant set.

    Args:
      source_uris: List of paths to VCF file[s] in Cloud Storage, wildcards
          accepted (*, not **).
      variantset_id: Id of the variant set to load the variants.

    Returns:
      The name of the loading operation.
    """
    request = self.service.variants().import_(
        body={"variantSetId": variantset_id,
              "sourceUris": source_uris})
    response = request.execute()
    return response["name"]

  # Handle transient HTTP errors by retrying several times before giving up.
  # Works around race conditions that arise when the operation ID is not
  # found, which yields a 404 error.
  @retry(stop_max_attempt_number=10, wait_exponential_multiplier=2000)
  def wait_for_operation(self, operation_id, wait_seconds=30):
    """Blocks until the Genomics operation completes.

    Args:
      operation_id: The name (id string) of the loading operation.
      wait_seconds: Number of seconds to wait between polling attempts.

    Returns:
      True if the operation succeeded, False otherwise.
    """
    request = self.service.operations().get(name=operation_id)
    while not request.execute()["done"]:
      time.sleep(wait_seconds)

    # If the operation succeeded, there will be a "response" field and not an
    # "error" field, see:
    # https://cloud.google.com/genomics/reference/rest/Shared.Types/ListOperationsResponse#Operation
    response = request.execute()
    return "response" in response and "error" not in response

  def export_variants(self, variantset_id, destination_table):
    """Exports variants from Google Genomics to BigQuery.

    Per the Genomics API, this will overwrite any existing BigQuery table with
    this name.

    Args:
      variantset_id: Id of the variant set to export.
      destination_table: BigQuery output, as PROJECT_ID.DATASET_NAME.TABLE_NAME.

    Returns:
      The name of the export operation.
    """
    tokenized_table = schema_update_utils.tokenize_table_name(destination_table)
    bigquery_project_id, dataset_name, table_name = tokenized_table

    request = self.service.variantsets().export(
        variantSetId=variantset_id,
        body={"projectId": bigquery_project_id,
              "bigqueryDataset": dataset_name,
              "bigqueryTable": table_name})
    response = request.execute()
    return response["name"]

  def upload_variants(self,
                      dataset,
                      variantset,
                      source_vcfs,
                      destination_table,
                      expand_wildcards=False,
                      new_dataset=False,
                      new_variantset=False,
                      description=None):
    """Imports variants stored in a VCF in Cloud Storage to BigQuery.

    Handle all intermediate steps, including finding dataset and variant sets.

    Args:
      dataset: Name or id of existing dataset, or name for a new dataset.
      variantset: Name or id of existing variant set, or name for a new one.
      source_vcfs: List of VCF file[s] in Cloud Storage, wildcards accepted
          (*, not **).
      destination_table: BigQuery output, as PROJECT_ID.DATASET_NAME.TABLE_NAME.
      expand_wildcards: Expand wildcards in VCF paths and use parallel imports.
      new_dataset: Always create a new dataset with the requested name.
      new_variantset: Always create a new variant set with the requested name.
      description: Optional description for the BigQuery table.

    Raises:
      RuntimeError: If an upload or export request does not succeed.
    """

    dataset_id = self.find_or_create_dataset(dataset,
                                             always_create=new_dataset)

    variantset_id = self.find_or_create_variantset(
        variantset,
        dataset_id,
        description="\t".join(source_vcfs),
        always_create=new_variantset)

    # Spawn off parallel imports for each VCF.
    if expand_wildcards and gfile is not None:
      # Expand any wildcarded paths and concatenate all files together.
      source_vcfs = sum([gfile.Glob(source_vcf) for source_vcf in source_vcfs],
                        [])

    operation_ids = []
    for source_vcf in source_vcfs:
      operation_ids.append(self.import_variants(source_vcf, variantset_id))
      logging.info("Importing %s (%s)", source_vcf, operation_ids[-1])

    # Wait for all imports to complete successfully before exporting variantset.
    for operation_id in operation_ids:
      if not self.wait_for_operation(operation_id):
        raise RuntimeError("Failed to import variants to Genomics (%s)"
                           % operation_id)

    operation_id = self.export_variants(variantset_id, destination_table)
    logging.info("Exporting %s (%s)", variantset, operation_id)

    if not self.wait_for_operation(operation_id):
      raise RuntimeError("Failed to export variants to BigQuery (%s)"
                         % operation_id)

    # Assume the VCF header is the same for all files and so just use the first.
    logging.info("Updating schema for %s", variantset)
    schema_update_utils.update_table_schema(destination_table,
                                            source_vcfs[0],
                                            description=description)
