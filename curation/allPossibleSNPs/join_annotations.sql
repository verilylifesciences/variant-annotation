#standardSQL
WITH
{% if 'dbSNP' in annot_sources %}
{% include 'dbSNP.sql' %},
{% endif %}

{% if 'clinvar' in annot_sources %}
{% include 'clinvar.sql' %},
{% endif %}

{% if 'thousandGenomes' in annot_sources %}
{% include 'thousandGenomes.sql' %},
{% endif %}

{% if 'ESP_AA' in annot_sources %}
{% include 'ESP_AA.sql' %},
{% endif %}

{% if 'ESP_EA' in annot_sources %}
{% include 'ESP_EA.sql' %},
{% endif %}

{% include 'all_possible_snps.sql' %}

--
-- Then JOIN with the individual variant annotation DBs.
--
SELECT
  *
FROM
  all_possible_snps
{% for source in annot_sources %}
LEFT OUTER JOIN {{source}}
  USING(reference_name, start, `end`, reference_bases, alternate_bases)
{% endfor %}

