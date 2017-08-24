  --
  -- Prepare ClinVar for the JOIN.
  --
  clinvar AS (
  SELECT
    reference_name,
    start,
    `end`,
    reference_bases,
    alternate_bases,
    -- Used to check for correctness of the JOIN.
    CONCAT('rs', CAST(RS AS STRING)) AS clinvar_rsid,
    -- ClinVar uses field CLNALLE to indicate "variant alleles from REF
    -- or ALT columns.  0 is REF, 1 is the first ALT allele, etc.  This
    -- is used to match alleles with other corresponding clinical (CLN)
    -- INFO tags.  A value of -1 indicates that no allele was found to
    -- match a corresponding HGVS allele name."
    CLNDBN[OFFSET(clnalle_offset)] AS CLNDBN,
    CLNACC[OFFSET(clnalle_offset)] AS CLNACC,
    CLNDSDB[OFFSET(clnalle_offset)] AS CLNDSDB,
    CLNDSDBID[OFFSET(clnalle_offset)] AS CLNDSDBID,
    CLNREVSTAT[OFFSET(clnalle_offset)] AS CLNREVSTAT,
    CLNSIG[OFFSET(clnalle_offset)] AS CLNSIG
  FROM
    `{{ CLINVAR_TABLE }}` v,
    UNNEST(ARRAY_CONCAT([reference_bases], v.alternate_bases)) AS alternate_bases WITH OFFSET alt_offset,
    v.CLNALLE clnalle WITH OFFSET clnalle_offset
  WHERE
    clnalle = alt_offset)
