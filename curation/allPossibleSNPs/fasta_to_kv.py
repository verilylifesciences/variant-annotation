#!/usr/bin/env python

# Copyright 2017 Verily Life Sciences Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""Convert FASTA files to a map-reduceable format.

Example Input:
>chr22
CAAGG
TTAGC
CCCCC

Example Output:
>chr22>0>CAAGG
>chr22>5>TTAGC
>chr22>10>CCCCC

It is very fast (~2 minutes for a 3 GB FASTA) when run on Compute Engine
utilizing streaming download and upload.
https://cloud.google.com/storage/docs/gsutil/commands/cp#streaming-transfers

For uncompressed FASTA files:

gsutil cat \
  gs://genomics-public-data/references/GRCh38_Verily/GRCh38_Verily_v1.genome.fa
  \
  | \
  ./fasta_to_kv.py \
  | \
  gsutil cp - gs://MY-BUCKET/refs/GRCh38_Verily_v1.genome.txt

For compressed FASTA files, use the appropriate command to unzip the file
before passing it to this script:

gsutil cat \
  gs://genomics-public-data/references/hg19/*fa.gz \
  | \
  gunzip \
  | \
  ./fasta_to_kv.py \
  | \
  gsutil cp - gs://MY-BUCKET/refs/hg19.txt
"""

import sys

sequence = ""
position = 0

for line in sys.stdin:
  trimmed = line.strip()
  if not trimmed:
    break

  if trimmed.startswith(";"):
    # Skip comment lines.
    continue

  if trimmed.startswith(">"):
    # We've started a new sequence.  Reset the state.
    sequence = trimmed
    position = 0
    continue

  # Write out the sequence with a prefix indicating its context.  Use '>'
  # as the delimiter since its a safe character to use in the file.
  sys.stdout.write(sequence + ">" + str(position) + ">" + trimmed + "\n")
  position += len(trimmed)
