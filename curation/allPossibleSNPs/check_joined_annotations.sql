#standardSQL
--
-- Compare the dbSNP ids retrieved from a variety of annotation sources
-- to ensure that the multiple sources were joined correctly.
--
-- Replace `YOUR_NEWLY_CREATED_ANNOTATIONS_TABLE` with the table to which the
-- JOINed annotations were materialized.
--
SELECT
{% for source in annot_sources %}
  COUNTIF({{source}}_rsid = dbSNP_rsid)/COUNTIF({{source}}_rsid IS NOT NULL) AS {{source}}_matched,
  COUNTIF({{source}}_rsid IS NOT NULL) AS {{source}}_compared,
{% endfor %}
  COUNT(dbSNP_rsid) AS num_in_dbSNP
FROM `YOUR_NEWLY_CREATED_ANNOTATIONS_TABLE`
WHERE
  dbSNP_rsid IS NOT NULL

