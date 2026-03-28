# YAML Templates Reference Guide

This document provides a reference for all YAML/CloudFormation templates in the Data Pipeline project.

---

## Table of Contents
1. [File Structure](#file-structure)
2. [serverless-app-template.yml](#serverless-app-templateyml)
3. [cloudformation/pipeline.yaml](#cloudformationpipelineyaml)
4. [buildspec.yml](#buildspecyml)
5. [Environment Configuration Files](#environment-configuration-files)
6. [Template Customization](#template-customization)

---

## File Structure

```
Data-pipeline-aws/
├── serverless-app-template.yml    # Main application template
├── buildspec.yml                  # CodeBuild configuration
├── dev.json                       # Dev environment parameters
├── staging.json                   # Staging environment parameters (optional)
├── prod.json                      # Prod environment parameters (optional)
└── cloudformation/
    └── pipeline.yaml              # CI/CD pipeline template
```

---

## serverless-app-template.yml

### Overview
Main SAM/CloudFormation template that defines all application resources.

### Parameters

```yaml
Parameters:
  EnvironmentName:
    Type: String
    Default: dev
    Description: Environment name (dev, staging, prod)
    AllowedValues:
      - dev
      - staging
      - prod

  ApplicationName:
    Type: String
    Default: serverless-app
    Description: Application name used for resource naming

  LogRetentionDays:
    Type: Number
    Default: 14
    Description: CloudWatch log retention in days
    AllowedValues:
      - 7
      - 14
      - 30
      - 60
      - 90

  ValidClientIds:
    Type: CommaDelimitedList
    Default: "client-app-1,client-app-2,client-mobile-app"
    Description: Comma-separated list of valid Client IDs for API authorization

  NotificationEmail1:
    Type: String
    Default: ""
    Description: First email for SNS notifications

  NotificationEmail2:
    Type: String
    Default: ""
    Description: Second email for SNS notifications

  NotificationEmail3:
    Type: String
    Default: ""
    Description: Third email for SNS notifications
```

### Resources Summary

| Resource | Type | Purpose |
|----------|------|---------|
| ApplicationSecret | AWS::SecretsManager::Secret | Store application secrets |
| ApiLambdaRole | AWS::IAM::Role | IAM role for API Lambda |
| HealthCheckFunction | AWS::Serverless::Function | Health check API Lambda |
| ClientIdAuthorizerFunction | AWS::Serverless::Function | API Gateway authorizer |
| ApiGateway | AWS::Serverless::Api | API Gateway with authorizer |
| GlueDataBucket | AWS::S3::Bucket | S3 bucket for Glue data |
| GlueJobRole | AWS::IAM::Role | IAM role for Glue job |
| CsvProcessorGlueJob | AWS::Glue::Job | Glue ETL job |
| GlueJobFailureTopic | AWS::SNS::Topic | SNS topic for failure notifications |
| StepFunctionsRole | AWS::IAM::Role | IAM role for Step Functions |
| GlueOrchestratorStateMachine | AWS::StepFunctions::StateMachine | Step Functions state machine |

### Outputs

```yaml
Outputs:
  ApiEndpoint:
    Description: API Gateway endpoint
    Value: !Sub https://${ApiGateway}.execute-api.${AWS::Region}.amazonaws.com/${EnvironmentName}

  HealthEndpoint:
    Description: Health check endpoint
    Value: !Sub https://${ApiGateway}.execute-api.${AWS::Region}.amazonaws.com/${EnvironmentName}/health

  GlueDataBucketName:
    Description: S3 bucket for Glue data
    Value: !Ref GlueDataBucket

  GlueJobName:
    Description: Glue job name
    Value: !Ref CsvProcessorGlueJob

  GlueInputPath:
    Description: S3 input path
    Value: !Sub s3://${GlueDataBucket}/input/

  GlueOutputPath:
    Description: S3 output path
    Value: !Sub s3://${GlueDataBucket}/output/

  StateMachineArn:
    Description: Step Functions State Machine ARN
    Value: !Ref GlueOrchestratorStateMachine

  StateMachineName:
    Description: Step Functions State Machine Name
    Value: !Sub ${ApplicationName}-glue-orchestrator-${EnvironmentName}

  StepFunctionsRoleArn:
    Description: Step Functions Role ARN
    Value: !GetAtt StepFunctionsRole.Arn

  SNSTopicArn:
    Description: SNS Topic ARN for notifications
    Value: !Ref GlueJobFailureTopic
```

---

## cloudformation/pipeline.yaml

### Overview
CI/CD pipeline template using AWS CodePipeline and CodeBuild.

### Parameters

```yaml
Parameters:
  GitHubOwner:
    Type: String
    Description: GitHub repository owner

  GitHubRepo:
    Type: String
    Default: Data-pipeline-aws
    Description: GitHub repository name

  GitHubBranch:
    Type: String
    Default: main
    Description: GitHub branch to track

  CodeConnectionArn:
    Type: String
    Description: ARN of the CodeConnections (CodeStar) connection

  EnvironmentName:
    Type: String
    Default: dev
    Description: Environment name

  ApplicationName:
    Type: String
    Default: serverless-app
    Description: Application name
```

### Pipeline Stages

```yaml
# Stage 1: Source
- Name: Source
  Actions:
    - Name: GitHubSource
      ActionTypeId:
        Category: Source
        Owner: AWS
        Provider: CodeStarSourceConnection
        Version: '1'
      Configuration:
        ConnectionArn: !Ref CodeConnectionArn
        FullRepositoryId: !Sub ${GitHubOwner}/${GitHubRepo}
        BranchName: !Ref GitHubBranch

# Stage 2: Build
- Name: Build
  Actions:
    - Name: BuildAndPackage
      ActionTypeId:
        Category: Build
        Owner: AWS
        Provider: CodeBuild
        Version: '1'
      Configuration:
        ProjectName: !Ref CodeBuildProject

# Stage 3: Deploy
- Name: Deploy
  Actions:
    - Name: CreateChangeSet
      ActionTypeId:
        Category: Deploy
        Owner: AWS
        Provider: CloudFormation
        Version: '1'
      Configuration:
        ActionMode: CHANGE_SET_REPLACE
        StackName: !Sub ${ApplicationName}-${EnvironmentName}
        ChangeSetName: !Sub ${ApplicationName}-${EnvironmentName}-changeset
        TemplatePath: BuildOutput::packaged-template.yaml
        Capabilities: CAPABILITY_NAMED_IAM

    - Name: ExecuteChangeSet
      ActionTypeId:
        Category: Deploy
        Owner: AWS
        Provider: CloudFormation
        Version: '1'
      Configuration:
        ActionMode: CHANGE_SET_EXECUTE
        StackName: !Sub ${ApplicationName}-${EnvironmentName}
        ChangeSetName: !Sub ${ApplicationName}-${EnvironmentName}-changeset
```

---

## buildspec.yml

### Overview
CodeBuild build specification for SAM packaging and deployment.

```yaml
version: 0.2

env:
  variables:
    SAM_TEMPLATE: serverless-app-template.yml
    PACKAGED_TEMPLATE: packaged-template.yaml
    APPLICATION_NAME: serverless-app
    ENVIRONMENT_NAME: dev

phases:
  install:
    runtime-versions:
      python: 3.9
    commands:
      - echo "Installing SAM CLI..."
      - pip install aws-sam-cli
      - sam --version

  pre_build:
    commands:
      - echo "Running pre-build checks..."
      - python --version
      - aws --version

  build:
    commands:
      - echo "Building SAM application..."
      - sam build --template ${SAM_TEMPLATE}

      - echo "Packaging SAM application..."
      - sam package \
          --template-file .aws-sam/build/template.yaml \
          --output-template-file ${PACKAGED_TEMPLATE} \
          --s3-bucket ${ARTIFACT_BUCKET}

  post_build:
    commands:
      - echo "Uploading Glue script to S3..."
      - |
        GLUE_BUCKET="${APPLICATION_NAME}-glue-data-$(aws sts get-caller-identity --query Account --output text)-${AWS_REGION}"
        if [ -f "glue/csv_processor.py" ]; then
          aws s3 cp glue/csv_processor.py s3://${GLUE_BUCKET}/scripts/csv_processor.py || true
        fi

      - echo "Build completed successfully!"

artifacts:
  files:
    - packaged-template.yaml
    - dev.json
    - staging.json
    - prod.json
  discard-paths: yes

cache:
  paths:
    - '/root/.cache/pip/**/*'
```

---

## Environment Configuration Files

### dev.json

```json
{
  "Parameters": {
    "EnvironmentName": "dev",
    "ApplicationName": "serverless-app",
    "LogRetentionDays": "14",
    "ValidClientIds": "client-app-1,client-app-2,postman-test,dev-client",
    "NotificationEmail1": "dev-team@example.com",
    "NotificationEmail2": "",
    "NotificationEmail3": ""
  },
  "Tags": {
    "Environment": "dev",
    "Application": "serverless-app",
    "ManagedBy": "CloudFormation",
    "CostCenter": "development"
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
    "ValidClientIds": "staging-app-1,staging-app-2,qa-client",
    "NotificationEmail1": "qa-team@example.com",
    "NotificationEmail2": "dev-team@example.com",
    "NotificationEmail3": ""
  },
  "Tags": {
    "Environment": "staging",
    "Application": "serverless-app",
    "ManagedBy": "CloudFormation",
    "CostCenter": "qa"
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
  },
  "Tags": {
    "Environment": "prod",
    "Application": "serverless-app",
    "ManagedBy": "CloudFormation",
    "CostCenter": "production"
  }
}
```

---

## Template Customization

### Adding a New Lambda Function

```yaml
# Add to serverless-app-template.yml under Resources:

  MyNewFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub ${ApplicationName}-${EnvironmentName}-my-function
      Handler: my_handler.handler
      Runtime: python3.9
      CodeUri: lambda/my_function/
      Role: !GetAtt MyFunctionRole.Arn
      Timeout: 30
      MemorySize: 256
      Environment:
        Variables:
          ENVIRONMENT: !Ref EnvironmentName
          APPLICATION_NAME: !Ref ApplicationName
      Events:
        MyApi:
          Type: Api
          Properties:
            RestApiId: !Ref ApiGateway
            Path: /my-endpoint
            Method: POST
```

### Adding a New Glue Job

```yaml
# Add to serverless-app-template.yml under Resources:

  MyNewGlueJob:
    Type: AWS::Glue::Job
    Properties:
      Name: !Sub ${ApplicationName}-my-job-${EnvironmentName}
      Description: My new Glue job
      Role: !GetAtt GlueJobRole.Arn
      GlueVersion: '4.0'
      WorkerType: G.1X
      NumberOfWorkers: 2
      Timeout: 60
      Command:
        Name: glueetl
        ScriptLocation: !Sub s3://${GlueDataBucket}/scripts/my_job.py
        PythonVersion: '3'
      DefaultArguments:
        '--job-language': python
        '--enable-metrics': 'true'
        '--ENVIRONMENT': !Ref EnvironmentName
```

### Adding a New Step Function State

```yaml
# Modify the DefinitionString in GlueOrchestratorStateMachine:

DefinitionString: !Sub |
  {
    "Comment": "Orchestrate Multiple Glue Jobs",
    "StartAt": "StartFirstJob",
    "States": {
      "StartFirstJob": {
        "Type": "Task",
        "Resource": "arn:aws:states:::glue:startJobRun.sync",
        "Parameters": {
          "JobName": "${ApplicationName}-csv-processor-${EnvironmentName}"
        },
        "Next": "StartSecondJob"
      },
      "StartSecondJob": {
        "Type": "Task",
        "Resource": "arn:aws:states:::glue:startJobRun.sync",
        "Parameters": {
          "JobName": "${ApplicationName}-my-job-${EnvironmentName}"
        },
        "Next": "JobSucceeded"
      },
      "JobSucceeded": {
        "Type": "Pass",
        "End": true
      }
    }
  }
```

### Adding a New API Endpoint

```yaml
# Add Event to existing Lambda or create new Lambda:

Events:
  NewEndpoint:
    Type: Api
    Properties:
      RestApiId: !Ref ApiGateway
      Path: /new-endpoint
      Method: GET
      # Optional: Skip authorization for this endpoint
      # Auth:
      #   Authorizer: NONE
```

### Adding a New SNS Topic

```yaml
# Add to Resources:

  MyNewTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: !Sub ${ApplicationName}-my-topic-${EnvironmentName}
      DisplayName: My Notifications

  MyTopicSubscription:
    Type: AWS::SNS::Subscription
    Properties:
      TopicArn: !Ref MyNewTopic
      Protocol: email
      Endpoint: !Ref NotificationEmail1
```

### Adding Environment Variables

```yaml
# Lambda Function
Environment:
  Variables:
    MY_NEW_VAR: my-value
    DYNAMIC_VAR: !Ref SomeParameter
    ARN_VAR: !GetAtt SomeResource.Arn

# Glue Job (use DefaultArguments with -- prefix)
DefaultArguments:
  '--MY_NEW_VAR': my-value
  '--DYNAMIC_VAR': !Ref SomeParameter
```

---

## Useful CloudFormation Intrinsic Functions

```yaml
# Reference a parameter
!Ref ParameterName

# Reference a resource
!Ref ResourceName

# Get attribute from resource
!GetAtt ResourceName.AttributeName
!GetAtt MyLambda.Arn

# String substitution
!Sub ${ApplicationName}-${EnvironmentName}
!Sub "arn:aws:s3:::${BucketName}/*"

# Join strings
!Join ["-", [!Ref ApplicationName, !Ref EnvironmentName]]
!Join [",", !Ref ValidClientIds]

# Conditional
!If [ConditionName, ValueIfTrue, ValueIfFalse]

# Select from list
!Select [0, !Ref MyList]

# Split string
!Split [",", "a,b,c"]

# Import from another stack
!ImportValue ExportedValueName

# Get AZ
!GetAZs !Ref "AWS::Region"

# Base64 encode
!Base64 "string to encode"
```

---

## Validation Commands

```bash
# Validate SAM template
sam validate --template serverless-app-template.yml

# Validate CloudFormation template
aws cloudformation validate-template \
  --template-body file://serverless-app-template.yml

# Lint template (install cfn-lint first)
pip install cfn-lint
cfn-lint serverless-app-template.yml
```

---

*Document Version: 1.0*
*Last Updated: January 2026*
