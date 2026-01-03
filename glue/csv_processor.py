"""
Glue ETL Job - CSV Processor
Reads CSV from S3, transforms, and writes output.
"""
<<<<<<< HEAD
mport sys
import boto3
import csv
import yaml
=======

import sys
from awsglue.transforms import *
>>>>>>> ef9d5ef845115bc69861d8dee50918c4b41d5ae9
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext

def generate_yaml_from_csv(bucket_name, input_key, output_key):
    local_csv = '/tmp/Glue_job_config.csv'
    local_yaml = '/tmp/multiple_glue_jobs.yaml'
    s3 = boto3.client('s3')

    print(f"📥 Downloading CSV from s3://{bucket_name}/{input_key} ...")
    s3.download_file(bucket_name, input_key, local_csv)

    jobs = []
    with open(local_csv, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            job = {}
            for key, value in row.items():
                if not key or not key.strip():
                    continue
                v = (value or '').strip()

                # Type conversion for common cases
                if v == '':
                    value_converted = None
                elif v.lower() in ('true', 'false'):
                    value_converted = (v.lower() == 'true')
                else:
                    try:
                        value_converted = int(v)
                    except ValueError:
                        try:
                            value_converted = float(v)
                        except ValueError:
                            value_converted = v

                # Build nested dict from dot-separated keys (e.g., Command.Name)
                parts = key.split('.')
                current = job
                for i, part in enumerate(parts):
                    part = part.strip()
                    if i == len(parts) - 1:
                        current[part] = value_converted
                    else:
                        current.setdefault(part, {})
                        current = current[part]

            jobs.append(job)

    yaml_structure = {'GlueJobs': jobs}

    print(f"📝 Writing YAML to {local_yaml} ...")
    with open(local_yaml, 'w', encoding='utf-8') as yaml_out:
        yaml.safe_dump(yaml_structure, yaml_out, sort_keys=False, allow_unicode=True)

    print(f"📤 Uploading YAML to s3://{bucket_name}/{output_key} ...")
    s3.upload_file(local_yaml, bucket_name, output_key)
    print("Parsed Glue arguments:", {k: args[k] for k in ['JOB_NAME', 'BUCKET_NAME', 'INPUT_KEY', 'OUTPUT_KEY']})

if __name__ == "__main__":
    # Glue job arguments (these names must match exactly in the job parameters you pass)
    args = getResolvedOptions(sys.argv, ['JOB_NAME', 'BUCKET_NAME', 'INPUT_KEY', 'OUTPUT_KEY'])

    # Optional: debug print to confirm what args were passed
    print("Parsed Glue arguments:", {k: args[k] for k in ['JOB_NAME', 'BUCKET_NAME', 'INPUT_KEY', 'OUTPUT_KEY']})

    sc = SparkContext()
    glueContext = GlueContext(sc)
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)

    # ✅ Use the argument KEYS, not literal values
    generate_yaml_from_csv(
        bucket_name=args['BUCKET_NAME'],
        input_key=args['INPUT_KEY'],
        output_key=args['OUTPUT_KEY']
    )