#!/usr/bin/env bash
# Send new/updated csv.gz (except files with today date name in format YY-mm-dd.csv.gz) from the 'ORDERBOOK_PATH' path to the s3 bucket 'BUCKET'. Removes uploaded files
# required ORDERBOOK_PATH
# required BUCKET

if [[ -z "${ORDERBOOK_PATH}" ]]; then
  echo 'Error: ORDERBOOK_PATH does not set'
  exit 1
else
  echo "Orderbook path: ${ORDERBOOK_PATH}"
fi

if [[ -z "${BUCKET}" ]]; then
  echo 'Error: BUCKET does not set'
  exit 1
else
  echo "S3 Bucket: ${BUCKET}"
fi

today_file="$(date +%Y-%m-%d).csv.gz"
echo "Ignore files mask: */${today_file}"

aws s3 sync "${ORDERBOOK_PATH}" "s3://${BUCKET}" --exclude "*/${today_file}" && find "${ORDERBOOK_PATH}" -type f -name '*.csv.gz' ! -name "${today_file}" -exec rm -f {} \;
echo 'Dump ended'
