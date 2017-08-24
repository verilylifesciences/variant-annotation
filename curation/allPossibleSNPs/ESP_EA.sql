  --
  -- Prepare ESP EA for the JOIN.
  --
  ESP_EA AS (
  SELECT
    reference_name,
    start,
    `end`,
    reference_bases,
    alternate_bases,
    AF AS ESP_EA_AF,
    -- Used to check for correctness of the JOIN.
    names[OFFSET(0)] AS ESP_EA_rsid
  FROM
    `{{ ESP_EA_TABLE }}` v,
    v.alternate_bases alternate_bases )
