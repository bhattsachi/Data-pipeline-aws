import boto3
import pandas as pd
import json
import yaml
from io import BytesIO

# Initialize S3 client
s3 = boto3.client('s3')

# Input and output bucket details
# Testing with Mani 
bucket_name = 'dev-batuu-test'
input_prefix = 'snaplogic-migration/task_output/'
output_prefix = 'snaplogic-migration/stepfunction_scripts/'
yaml_key = f"{output_prefix}all_stepfunctions.yaml"

# List all CSV files in the input prefix
response = s3.list_objects_v2(Bucket=bucket_name, Prefix=input_prefix)
csv_files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.csv')]

# Load existing YAML if present
existing_definitions = []
try:
    yaml_obj = s3.get_object(Bucket=bucket_name, Key=yaml_key)
    existing_yaml = yaml_obj['Body'].read().decode('utf-8')
    existing_definitions = yaml.safe_load(existing_yaml) or []
    print(f"✅ Loaded existing YAML with {len(existing_definitions)} definitions")
except s3.exceptions.NoSuchKey:
    print("ℹ️ No existing YAML found. Starting fresh.")

new_definitions = []

for csv_key in csv_files:
    # Read CSV content from S3
    response = s3.get_object(Bucket=bucket_name, Key=csv_key)
    df = pd.read_csv(response['Body'])

    # Group by Job name
    jobs = df.groupby('Job name')

    for job_name, group in jobs:
        pipeline_parameters = {}
        pipeline_name = None

        for _, row in group.iterrows():
            param_name = row['Parameter name']
            subparam_name = row['Subparameter name']
            value = row['Value'] if 'Value' in row else ""
            value = "" if pd.isna(value) else str(value)

            if param_name == 'pipeline_parameters' and pd.notna(subparam_name):
                pipeline_parameters[subparam_name] = value

            if 'Pipeline name' in row and pd.notna(row['Pipeline name']):
                pipeline_name = row['Pipeline name']

        glue_job_name = pipeline_name if pipeline_name else 'DefaultGlueJob'
        glue_arguments = {f"--{k}": v for k, v in pipeline_parameters.items()}

        # Build Step Function definition with failure notification
        # Assumes an SNS topic exists for notifications
        sns_topic_arn = "arn:aws:sns:us-east-2:533267066040:glue-job-failure-notify:f39f1ce9-972f-4fae-ab8c-ce67e92fee73"
        definition = {
            "name": job_name,
            "definition": {
                "Comment": f"Step Function for {job_name}",
                "StartAt": "InvokeGlueJob",
                "States": {
                    "InvokeGlueJob": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::glue:startJobRun.sync",
                        "Parameters": {
                            "JobName": glue_job_name,
                            "Arguments": glue_arguments
                        },
                        "Next": "CheckGlueJobStatus"
                    },
                    "CheckGlueJobStatus": {
                        "Type": "Choice",
                        "Choices": [
                            {
                                "Variable": "$.JobRun.State",
                                "StringEquals": "FAILED",
                                "Next": "NotifyFailure"
                            }
                        ],
                        "Default": "SuccessState"
                    },
                    "NotifyFailure": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::sns:publish",
                        "Parameters": {
                            "TopicArn": sns_topic_arn,
                            "Message": {
                                "Fn::Sub": f"Glue job {glue_job_name} failed. Notification sent to naikwadin@magellanhealth.com."
                            },
                            "Subject": f"Glue Job Failure: {glue_job_name}"
                        },
                        "Next": "FailState"
                    },
                    "FailState": {
                        "Type": "Fail",
                        "Error": "GlueJobFailed",
                        "Cause": f"Glue job {glue_job_name} failed."
                    },
                    "SuccessState": {
                        "Type": "Succeed"
                    }
                }
            }
        }

        # Upload individual JSON file
        output_key = f"{output_prefix}{job_name}.json"
        s3.put_object(
            Bucket=bucket_name,
            Key=output_key,
            Body=json.dumps(definition["definition"], indent=2)
        )

        new_definitions.append(definition)

# Merge old and new definitions
all_definitions = existing_definitions + new_definitions

# Convert to YAML
yaml_content = yaml.dump(all_definitions, sort_keys=False)

# Upload updated YAML to S3
s3.put_object(Bucket=bucket_name, Key=yaml_key, Body=yaml_content)

print(f"✅ Updated YAML with {len(all_definitions)} total definitions at s3://{bucket_name}/{yaml_key}")