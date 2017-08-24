  --
  -- Create a table containing all possible SNPs for a reference genome.
  --
  -- Split the sequences from the FASTA file.
  --
  base_pairs AS (
  SELECT
    chr,
    sequence_start,
    SPLIT(sequence, '') AS bps
  FROM
    `{{ SEQUENCE_TABLE }}`
  # Use this replacement to test on small amount of data.  Otherwise replace
  # it with the empty string.
  {{ SEQUENCE_FILTER }} ),
  --
  -- Expand the data to one row per base pair.  Also upper case the
  -- base pair and compute the end position.
  --
  all_refs AS (
  SELECT
    chr AS original_reference_name,
    SUBSTR(chr, 4) AS reference_name,
    sequence_start + base_pair_offset AS start,
    sequence_start + base_pair_offset + 1 AS `end`,
    UPPER(base_pair) AS reference_bases,
    base_pair AS original_reference_bases
  FROM
    base_pairs,
    base_pairs.bps base_pair
  WITH
  OFFSET
    base_pair_offset),
  --
  -- Create a table holding the four possible values for
  -- alternate_bases.
  --
  all_alternate_bases AS (
  SELECT
    'A' AS alternate_bases
  UNION ALL
  SELECT
    'C' AS alternate_bases
  UNION ALL
  SELECT
    'G' AS alternate_bases
  UNION ALL
  SELECT
    'T' AS alternate_bases ),
  all_possible_snps AS (
    --
    -- CROSS JOIN with all possible mutations for the base pair.  Note
    -- that 'N' will result in four possible mutations.
    --
  SELECT
    reference_name,
    original_reference_name,
    start,
    `end`,
    reference_bases,
    original_reference_bases,
    alternate_bases
  FROM
    all_refs
  CROSS JOIN
    all_alternate_bases
    )
