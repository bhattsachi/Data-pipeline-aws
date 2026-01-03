"""
Glue ETL Job - CSV Processor
Reads CSV from S3, transforms, and writes output.
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql.functions import current_timestamp, lit

# Get job arguments
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'INPUT_PATH', 'OUTPUT_PATH'])

# Initialize contexts
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Get paths
input_path = args['INPUT_PATH']
output_path = args['OUTPUT_PATH']

print("=" * 60)
print(f"GLUE JOB: {args['JOB_NAME']}")
print(f"Input: {input_path}")
print(f"Output: {output_path}")
print("=" * 60)

# Read CSV from S3
datasource = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [input_path], "recurse": True},
    format="csv",
    format_options={"withHeader": True, "separator": ","},
    transformation_ctx="datasource"
)

# Get record count
record_count = datasource.count()
print(f"Records found: {record_count}")

if record_count == 0:
    print("No records to process!")
    job.commit()
else:
# Show sample data
print("\nSample data:")
datasource.toDF().show(5)

# Transform - Add metadata columns
df = datasource.toDF()
df_transformed = df \
    .withColumn("processed_at", current_timestamp()) \
    .withColumn("job_name", lit(args['JOB_NAME']))

# Convert back to DynamicFrame
transformed = DynamicFrame.fromDF(df_transformed, glueContext, "transformed")

# Write as Parquet
print(f"\nWriting Parquet to: {output_path}parquet/")
glueContext.write_dynamic_frame.from_options(
    frame=transformed,
    connection_type="s3",
    connection_options={"path": f"{output_path}parquet/"},
    format="parquet"
)

# Write as CSV
print(f"Writing CSV to: {output_path}csv/")
glueContext.write_dynamic_frame.from_options(
    frame=transformed,
    connection_type="s3",
    connection_options={"path": f"{output_path}csv/"},
    format="csv",
    format_options={"separator": ",", "writeHeader": True}
)

print("\n" + "=" * 60)
print(f"COMPLETED - {record_count} records processed")
print("=" * 60)

job.commit()

## testing ## 


