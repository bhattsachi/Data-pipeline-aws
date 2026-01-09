# AWS Serverless Data Pipeline - DevOps Guide

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Initial Setup](#initial-setup)
4. [Deployment Checklist](#deployment-checklist)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Environment Configuration](#environment-configuration)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Rollback Procedures](#rollback-procedures)
9. [Monitoring & Alerts](#monitoring--alerts)
10. [Security Checklist](#security-checklist)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                        AWS SERVERLESS DATA PIPELINE                        │
│                                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌───────────┐  │
│  │   Client    │───►│ API Gateway  │───►│ Authorizer  │───►│  Lambda   │  │
│  │  + Client-ID│    │              │    │  Lambda     │    │  (app.py) │  │
│  └─────────────┘    └──────────────┘    └─────────────┘    └───────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         STEP FUNCTIONS                               │   │
│  │  ┌───────────┐    ┌──────────────┐    ┌──────────────┐             │   │
│  │  │  Start    │───►│  Glue Job    │───►│ SNS Notify   │             │   │
│  │  │           │    │  (ETL)       │    │ (on failure) │             │   │
│  │  └───────────┘    └──────────────┘    └──────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           S3 BUCKET                                  │   │
│  │  /scripts/csv_processor.py  │  /input/*.csv  │  /output/parquet/   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         CI/CD PIPELINE                               │   │
│  │  GitHub ──► CodePipeline ──► CodeBuild ──► CloudFormation Deploy   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Pre-Deployment Checklist

### AWS Account Setup
- [ ] AWS Account created and configured
- [ ] IAM user/role with appropriate permissions
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] SAM CLI installed (`sam --version`)

### GitHub Setup
- [ ] Repository created
- [ ] Code pushed to main branch
- [ ] AWS CodeConnections (CodeStar) connection created and authorized

### Required Permissions
- [ ] CloudFormation full access
- [ ] S3 full access
- [ ] Lambda full access
- [ ] API Gateway full access
- [ ] Glue full access
- [ ] Step Functions full access
- [ ] IAM role creation permissions
- [ ] SNS full access
- [ ] Secrets Manager access
- [ ] CodePipeline/CodeBuild access

### Local Development
- [ ] Python 3.9+ installed
- [ ] Pipenv installed (`pip install pipenv`)
- [ ] Dependencies installed (`pipenv install`)

---

## Initial Setup

### Step 1: Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/Data-pipeline-aws.git
cd Data-pipeline-aws
```

### Step 2: Install Dependencies
```bash
pip install pipenv
pipenv install
```

### Step 3: Configure AWS CLI
```bash
aws configure
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region name: us-east-2
# Default output format: json
```

### Step 4: Create CodeConnections Connection
```bash
# Create connection (must be authorized in AWS Console)
aws codeconnections create-connection \
  --connection-name github-connection \
  --provider-type GitHub \
  --region us-east-2

# Note: Complete authorization in AWS Console
# Console → CodePipeline → Settings → Connections → Update pending connection
```

### Step 5: Deploy CI/CD Pipeline
```bash
# Set variables
REGION="us-east-2"
GITHUB_OWNER="your-github-username"
GITHUB_REPO="Data-pipeline-aws"
CODE_CONNECTION_ARN="arn:aws:codeconnections:us-east-2:ACCOUNT_ID:connection/CONNECTION_ID"

# Deploy pipeline
aws cloudformation deploy \
  --template-file cloudformation/pipeline.yaml \
  --stack-name serverless-app-pipeline-dev \
  --parameter-overrides \
    CodeConnectionArn="$CODE_CONNECTION_ARN" \
    GitHubOwner="$GITHUB_OWNER" \
    GitHubRepo="$GITHUB_REPO" \
    GitHubBranch="main" \
    EnvironmentName="dev" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $REGION
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] All code changes committed and pushed
- [ ] Unit tests passing (`pipenv run pytest`)
- [ ] Environment configuration updated (`dev.json`)
- [ ] Notification emails configured
- [ ] Valid Client IDs configured

### During Deployment
- [ ] Pipeline triggered (automatic on git push)
- [ ] Source stage completed
- [ ] Build stage completed
- [ ] Deploy stage completed

### Monitor Deployment
```bash
# Check pipeline status
aws codepipeline get-pipeline-state \
  --name serverless-app-pipeline-dev \
  --region us-east-2 \
  --query "stageStates[*].[stageName,latestExecution.status]" \
  --output table

# Watch CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "StackEvents[0:10].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId]" \
  --output table
```

---

## Post-Deployment Verification

### Step 1: Verify Stack Outputs
```bash
# Get all outputs
aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs" \
  --output table
```

### Step 2: Test API Endpoint
```bash
# Get API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs[?OutputKey=='HealthEndpoint'].OutputValue" \
  --output text)

# Test with valid Client-ID
curl -H "Client-ID: client-app-1" $API_ENDPOINT

# Test without Client-ID (should fail with 401)
curl $API_ENDPOINT

# Test with invalid Client-ID (should fail with 403)
curl -H "Client-ID: invalid" $API_ENDPOINT
```

### Step 3: Verify S3 Bucket
```bash
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs[?OutputKey=='GlueDataBucketName'].OutputValue" \
  --output text)

# Check Glue script exists
aws s3 ls s3://$BUCKET/scripts/

# Upload sample data
aws s3 cp glue/sample_data.csv s3://$BUCKET/input/
```

### Step 4: Test Step Function
```bash
# Get State Machine ARN
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs[?OutputKey=='StateMachineArn'].OutputValue" \
  --output text)

# Run Step Function
aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input "{\"inputPath\": \"s3://$BUCKET/input/\", \"outputPath\": \"s3://$BUCKET/output/\"}" \
  --region us-east-2

# Check execution status
aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --region us-east-2 \
  --query "executions[0:5].[name,status,startDate]" \
  --output table
```

### Step 5: Verify Output
```bash
# Check output files
aws s3 ls s3://$BUCKET/output/ --recursive
```

### Verification Checklist
- [ ] API Gateway responds with 200 (valid Client-ID)
- [ ] API Gateway responds with 401 (missing Client-ID)
- [ ] API Gateway responds with 403 (invalid Client-ID)
- [ ] Glue script exists in S3
- [ ] Step Function executes successfully
- [ ] Output files created in S3
- [ ] SNS notifications working (test with intentional failure)
- [ ] CloudWatch logs available

---

## Environment Configuration

### Parameters by Environment

| Parameter | Dev | Staging | Prod |
|-----------|-----|---------|------|
| EnvironmentName | dev | staging | prod |
| LogRetentionDays | 14 | 30 | 90 |
| ValidClientIds | test-clients | staging-clients | prod-clients |
| NotificationEmails | dev-team | qa-team | ops-team |

### dev.json
```json
{
  "Parameters": {
    "EnvironmentName": "dev",
    "ApplicationName": "serverless-app",
    "LogRetentionDays": "14",
    "ValidClientIds": "client-app-1,client-app-2,postman-test",
    "NotificationEmail1": "dev-team@example.com",
    "NotificationEmail2": "",
    "NotificationEmail3": ""
  }
}
```

### staging.json
```json
{
  "Parameters": {
    "EnvironmentName": "staging",
    "ApplicationName": "serverless-app",
    "LogRetentionDays": "30",
    "ValidClientIds": "staging-app-1,staging-app-2",
    "NotificationEmail1": "qa-team@example.com",
    "NotificationEmail2": "dev-team@example.com",
    "NotificationEmail3": ""
  }
}
```

### prod.json
```json
{
  "Parameters": {
    "EnvironmentName": "prod",
    "ApplicationName": "serverless-app",
    "LogRetentionDays": "90",
    "ValidClientIds": "prod-app-1,prod-app-2,prod-mobile-app",
    "NotificationEmail1": "ops-team@example.com",
    "NotificationEmail2": "dev-team@example.com",
    "NotificationEmail3": "oncall@example.com"
  }
}
```

---

## Troubleshooting Guide

### Common Errors

#### 1. Pipeline Source Stage Failed
**Error:** Unable to access GitHub repository

**Solution:**
```bash
# Verify CodeConnections connection is authorized
aws codeconnections get-connection \
  --connection-arn YOUR_CONNECTION_ARN \
  --region us-east-2

# Status should be "AVAILABLE", not "PENDING"
# If PENDING, authorize in AWS Console
```

#### 2. Glue Job Failed - Script Not Found
**Error:** Error downloading from S3 for bucket: xxx, key: scripts/csv_processor.py

**Solution:**
```bash
# Upload Glue script manually
aws s3 cp glue/csv_processor.py s3://$BUCKET/scripts/csv_processor.py --region us-east-2
```

#### 3. Step Function Failed - Input Path Error
**Error:** JSONPath '$.inputPath' could not be found in the input '{}'

**Solution:**
```bash
# Always provide input when starting execution
aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input '{"inputPath": "s3://bucket/input/", "outputPath": "s3://bucket/output/"}'
```

#### 4. SNS Publish Permission Denied
**Error:** User is not authorized to perform: SNS:Publish

**Solution:**
```bash
# Add SNS permission to Step Functions role
aws iam put-role-policy \
  --role-name serverless-app-stepfn-role-dev \
  --policy-name SNSPublishAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-2:ACCOUNT_ID:serverless-app-*"
    }]
  }'
```

#### 5. API Gateway 401 Unauthorized
**Cause:** Missing Client-ID header

**Solution:**
```bash
# Include Client-ID header in request
curl -H "Client-ID: client-app-1" https://API_URL/dev/health
```

#### 6. API Gateway 403 Forbidden
**Cause:** Invalid Client-ID

**Solution:**
- Check ValidClientIds parameter in dev.json
- Redeploy if updated
- Or add new client ID to Secrets Manager

---

## Rollback Procedures

### Rollback CloudFormation Stack
```bash
# List previous successful deployments
aws cloudformation describe-stack-events \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "StackEvents[?ResourceStatus=='UPDATE_COMPLETE']"

# Rollback to previous version (automatic on failure)
# For manual rollback, redeploy previous commit:
git revert HEAD
git push origin main
```

### Rollback Glue Script
```bash
# List S3 versions (if versioning enabled)
aws s3api list-object-versions \
  --bucket $BUCKET \
  --prefix scripts/csv_processor.py

# Restore previous version
aws s3api copy-object \
  --bucket $BUCKET \
  --copy-source "$BUCKET/scripts/csv_processor.py?versionId=PREVIOUS_VERSION_ID" \
  --key scripts/csv_processor.py
```

### Emergency Stop
```bash
# Stop running Step Function execution
aws stepfunctions stop-execution \
  --execution-arn EXECUTION_ARN \
  --region us-east-2

# Stop running Glue job
aws glue batch-stop-job-run \
  --job-name serverless-app-csv-processor-dev \
  --job-run-ids JOB_RUN_ID \
  --region us-east-2
```

---

## Monitoring & Alerts

### CloudWatch Log Groups
| Resource | Log Group |
|----------|-----------|
| API Lambda | /aws/lambda/serverless-app-dev-health |
| Authorizer Lambda | /aws/lambda/serverless-app-dev-authorizer |
| Glue Job | /aws-glue/jobs |
| Step Functions | /aws/stepfunctions/serverless-app-glue-orchestrator-dev |

### View Logs
```bash
# API Lambda logs
aws logs tail /aws/lambda/serverless-app-dev-health --follow --region us-east-2

# Authorizer logs
aws logs tail /aws/lambda/serverless-app-dev-authorizer --follow --region us-east-2

# Glue job logs
aws logs tail /aws-glue/jobs --follow --region us-east-2
```

### SNS Notifications
- **Topic:** serverless-app-glue-failure-dev
- **Triggers:** Glue job failure
- **Recipients:** Configured in NotificationEmail1/2/3 parameters

### Confirm SNS Subscription
```bash
# List subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-2:ACCOUNT_ID:serverless-app-glue-failure-dev \
  --region us-east-2

# Status should be "Confirmed", not "PendingConfirmation"
```

---

## Security Checklist

### API Security
- [ ] Client-ID header authorizer enabled
- [ ] Valid Client IDs stored securely (parameter or Secrets Manager)
- [ ] HTTPS only (default in API Gateway)
- [ ] Authorization caching enabled (5 minutes)

### IAM Security
- [ ] Least privilege IAM roles
- [ ] No wildcard (*) permissions where possible
- [ ] Roles scoped to specific resources

### Data Security
- [ ] S3 bucket encryption enabled (AES256)
- [ ] S3 bucket not public
- [ ] Secrets stored in Secrets Manager
- [ ] No secrets in code or environment variables

### Network Security
- [ ] VPC configuration (if required)
- [ ] Security groups properly configured
- [ ] No public access to internal resources

### Audit & Compliance
- [ ] CloudTrail enabled
- [ ] CloudWatch logs enabled
- [ ] Log retention configured
- [ ] Access logging enabled for S3

---

## Quick Reference Commands

```bash
# ═══════════════════════════════════════════════════════════════════════════
# DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════

# Deploy CI/CD pipeline (one-time)
aws cloudformation deploy \
  --template-file cloudformation/pipeline.yaml \
  --stack-name serverless-app-pipeline-dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-2

# Trigger deployment (push to GitHub)
git add . && git commit -m "Update" && git push origin main

# ═══════════════════════════════════════════════════════════════════════════
# STACK INFORMATION
# ═══════════════════════════════════════════════════════════════════════════

# Get all stack outputs
aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs"

# Get specific output
aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text

# ═══════════════════════════════════════════════════════════════════════════
# API TESTING
# ═══════════════════════════════════════════════════════════════════════════

# Test API with Client-ID
curl -H "Client-ID: client-app-1" https://API_URL/dev/health

# ═══════════════════════════════════════════════════════════════════════════
# STEP FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

# Start execution
aws stepfunctions start-execution \
  --state-machine-arn STATE_MACHINE_ARN \
  --input '{"inputPath": "s3://bucket/input/", "outputPath": "s3://bucket/output/"}'

# List executions
aws stepfunctions list-executions \
  --state-machine-arn STATE_MACHINE_ARN \
  --query "executions[0:5].[name,status]" \
  --output table

# ═══════════════════════════════════════════════════════════════════════════
# S3 OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

# Upload input file
aws s3 cp data.csv s3://BUCKET/input/

# List output files
aws s3 ls s3://BUCKET/output/ --recursive

# ═══════════════════════════════════════════════════════════════════════════
# LOGS
# ═══════════════════════════════════════════════════════════════════════════

# Tail Lambda logs
aws logs tail /aws/lambda/serverless-app-dev-health --follow

# Tail Glue logs
aws logs tail /aws-glue/jobs --follow
```

---

## Contact & Support

| Role | Contact |
|------|---------|
| DevOps Lead | devops@example.com |
| On-Call | oncall@example.com |
| Slack Channel | #data-pipeline-support |

---

*Document Version: 1.0*
*Last Updated: January 2026*
