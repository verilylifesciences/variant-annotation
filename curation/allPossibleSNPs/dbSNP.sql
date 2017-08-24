  --
  -- Prepare dbSNP for the JOIN.
  --
  -- http://varianttools.sourceforge.net/Annotation/DbSNP
  -- Multiple alternate alleles sometimes correspond to the same rsid.
  -- Some variants have multiple rsids.
  --
  dbSNP AS (
  SELECT
    reference_name,
    start,
    `end`,
    reference_bases, -- on the + strand
    alternate_bases, -- on the + strand
    names AS rs_names,
    RS,
    -- Used to check for correctness of the JOIN.
    CONCAT('rs', CAST(RS AS STRING)) AS dbSNP_rsid
  FROM
    `{{ DBSNP_TABLE }}` v,
    v.alternate_bases alternate_bases )
