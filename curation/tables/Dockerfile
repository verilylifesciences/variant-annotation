FROM gcr.io/cloud-builders/gcloud

RUN apt-get update \
  && apt-get install -y python-setuptools \
  && pip install --upgrade \
    gcloud \
    google-api-python-client \
    google-cloud-bigquery \
    retrying \
    tensorflow


COPY *.py /usr/local/bin/
COPY launch_import_vcf_to_bigquery.sh /usr/local/bin/

ENTRYPOINT ["bash"]
