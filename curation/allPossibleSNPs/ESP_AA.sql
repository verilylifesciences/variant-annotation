  --
  -- Prepare ESP AA for the JOIN.
  --
  ESP_AA AS (
  SELECT
    reference_name,
    start,
    `end`,
    reference_bases,
    alternate_bases,
    AF AS ESP_AA_AF,
    -- Used to check for correctness of the JOIN.
    names[OFFSET(0)] AS ESP_AA_rsid
  FROM
    `{{ ESP_AA_TABLE }}` v,
    v.alternate_bases alternate_bases )
