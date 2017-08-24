  --
  -- Prepare 1000 Genomes for the JOIN.
  --
  thousandGenomes AS (
  SELECT
    reference_name,
    start,
    `end`,
    reference_bases,
    alternate_bases,
    AFR_AF[OFFSET(alt_offset)] AS AFR_AF_1000G,
    AMR_AF[OFFSET(alt_offset)] AS AMR_AF_1000G,
    EAS_AF[OFFSET(alt_offset)] AS EAS_AF_1000G,
    EUR_AF[OFFSET(alt_offset)] AS EUR_AF_1000G,
    SAS_AF[OFFSET(alt_offset)] AS SAS_AF_1000G,
    -- Used to check for correctness of the JOIN.
    names[OFFSET(0)] AS thousandGenomes_rsid
  FROM
    `{{ THOUSAND_GENOMES_TABLE }}` v,
    v.alternate_bases alternate_bases WITH OFFSET alt_offset )
