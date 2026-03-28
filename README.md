# Pipeline 

pipeline-stack.yml - Main CloudFormation template that creates:
CodePipeline with 5 stages (Source, Validation, Dev Deploy)
3 CodeBuild projects for validation and deployment
S3 artifact bucket with cross-account access
IAM roles and policies


cross-account-role.yml - IAM role template for Dev and Test accounts to allow cross-account deployments

buildspec-deploy.yml - CodeBuild specification that packages Lambda functions and deploys CloudFormation stacks

deploy-pipeline.sh - Interactive bash script for easy pipeline deployment

dev-params.json & test-params.json - Environment-specific configuration parameters

# ###############################################################################

Objective
Design and implement a CI/CD pipeline using AWS CodePipeline and CloudFormation (with AWS SAM) that provisions and deploys a simple serverless application.
You will build a CodePipeline with three stages:
• Source
• Build
• Deploy

The pipeline must deploy a serverless REST API composed of:
• AWS Lambda
• AWS Secrets Manager
• Amazon API Gateway (REST API)

All infrastructure must be defined using CloudFormation and AWS SAM.
Manual resource creation via the AWS Console is not allowed.

Functional Requirements

1. Source Stage
•	Source code must be hosted in GitHub
•	The pipeline must pull code using CodeStar Connections
•	Branch selection must be configurable (for example: dev)
2. Build Stage
•	Use AWS CodeBuild
•	The build stage must:
I.	Package CloudFormation/SAM templates
II.	Upload artifacts to S3
III.	Produce a packaged template ready for deployment
• A buildspec.yml file is required
• The build must fail clearly if packaging or validation fails

3. Deploy Stage
•	Use AWS CloudFormation to deploy resources
•	The deploy stage must create or update a CloudFormation stack
•	Stack updates must be idempotent

Serverless Application Requirements
AWS Lambda
•	Runtime: Python 3.12
•	A simple handler that:
–	Reads a secret from AWS Secrets Manager
–	Returns a JSON response
•	Proper IAM permissions must be defined using least privilege

AWS Secrets Manager
•	A secret must be created via CloudFormation
•	The Lambda function must reference the secret using:
–	Environment variables
–	IAM permissions (no hard-coded values)
API Gateway (REST API)
•	Must be created using AWS SAM
•	Must expose at least one endpoint:
–	Method: POST
–	Path: /health or /test
•	API Gateway must integrate with the Lambda function
•	Lambda proxy integration is acceptable


Infrastructure as Code Requirements
•	All resources must be defined using:
–	AWS CloudFormation
–	AWS SAM (Transform: AWS::Serverless-2016-10-31)
•	Nested stacks are allowed but not required
•	Parameters must be used for:
–	Environment name
–	Application name
•	Templates must be deployable using aws cloudformation package and deploy
•	
Repository Structure (Suggested)
.
├── cloudformation/
│   ├── pipeline.yaml
├── lambda/
│   └── app.py
├── buildspec.yml
├── serverless-app-template.yaml
└── <env>.json

Security & Best Practices
•	No secrets committed to GitHub
•	IAM roles must follow least privilege
•	Hard-coded ARNs should be avoided
•	CloudFormation parameters should be used appropriately
•	Clear separation between pipeline infrastructure and application infrastructure

Deliverables
GitHub repository containing:
• CloudFormation templates
• SAM templates
• Lambda code
• buildspec.yml
• Environment-specific parameter file
The solution must deploy successfully resources mentioned above in a same AWS account

#########################################

## Architecture 
 
 ![alt text](image-1.png)

## ARN Connection


![alt text](image.png)

## Response body
{
  "status": "healthy",
  "message": "Service is running",
  "timestamp": "2024-01-15T10:30:45.123456+00:00",
  "environment": "dev",
  "application": "serverless-app",
  "request_id": "abc123-def456",
  "secret_config": {
    "app_name": "serverless-app",
    "environment": "dev",
    "api_key_present": true    // ← Boolean, NOT the actual key!
  }
}

## Complete Flow Diagram
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LAMBDA EXECUTION FLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘

     CLIENT                    API GATEWAY                    LAMBDA
        │                          │                            │
        │  POST /health            │                            │
        │─────────────────────────>│                            │
        │                          │                            │
        │                          │  Invoke Lambda             │
        │                          │  event = {                 │
        │                          │    "httpMethod": "POST",   │
        │                          │    "path": "/health",      │
        │                          │    ...                     │
        │                          │  }                         │
        │                          │───────────────────────────>│
        │                          │                            │
        │                          │              ┌─────────────┴─────────────┐
        │                          │              │  lambda_handler(event,    │
        │                          │              │                context)   │
        │                          │              │                           │
        │                          │              │  1. Log event             │
        │                          │              │  2. Extract path, method  │
        │                          │              │  3. Call get_secret()     │
        │                          │              │     └─> Secrets Manager   │
        │                          │              │  4. Build response_body   │
        │                          │              │  5. Return response       │
        │                          │              └─────────────┬─────────────┘
        │                          │                            │
        │                          │  Response:                 │
        │                          │  {                         │
        │                          │    "statusCode": 200,      │
        │                          │    "body": "{...}"         │
        │                          │  }                         │
        │                          │<───────────────────────────│
        │                          │                            │
        │  HTTP 200 OK             │                            │
        │  {"status": "healthy"}   │                            │
        │<─────────────────────────│                            │
        │                          │                            │

```

### SAM Transform
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Transform: AWS::Serverless-2016-10-31                                       │
│                                                                             │
│  This is the MAGIC that makes SAM work!                                     │
│                                                                             │
│  What it does:                                                              │
│  1. Tells CloudFormation to use the SAM preprocessor                        │
│  2. Enables simplified resource types like:                                 │
│     - AWS::Serverless::Function (instead of AWS::Lambda::Function)         │
│     - AWS::Serverless::Api (instead of AWS::ApiGateway::RestApi)           │
│                                                                             │
│  Behind the scenes, SAM Transform converts:                                 │
│                                                                             │
│  AWS::Serverless::Function  ──────►  AWS::Lambda::Function                  │
│                                      AWS::Lambda::Permission                │
│                                      AWS::IAM::Role (if not provided)      │
│                                                                             │
│  AWS::Serverless::Api       ──────►  AWS::ApiGateway::RestApi              │
│                                      AWS::ApiGateway::Stage                │
│                                      AWS::ApiGateway::Deployment           │
│                                      + many more resources                 │
└─────────────────────────────────────────────────────────────────────────────┘



┌─────────────────────────────────────────────────────────────────────────────┐
│  Parameters are INPUT VARIABLES for your template                           │
│                                                                             │
│  They allow you to:                                                         │
│  1. Reuse the same template for different environments                      │
│  2. Customize deployments without changing the template                     │
│  3. Pass values at deploy time                                              │
│                                                                             │
│  Usage when deploying:                                                      │
│  aws cloudformation deploy \                                                │
│    --parameter-overrides \                                                  │
│      EnvironmentName=prod \        ← Overrides default "dev"               │
│      ApplicationName=my-app \      ← Overrides default "serverless-app"    │
│      LogRetentionDays=30           ← Overrides default 14                  │
└─────────────────────────────────────────────────────────────────────────────┘

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Environment Variables = Configuration passed to Lambda                     │
│                                                                             │
│  These become available in your Python code via os.environ:                │
│                                                                             │
│  YAML:                              Python:                                 │
│  SECRET_ARN: !Ref ApplicationSecret │ os.environ.get("SECRET_ARN")         │
│                                     │ → "arn:aws:secretsmanager:..."       │
│                                     │                                       │
│  SECRET_NAME: !Sub ...              │ os.environ.get("SECRET_NAME")        │
│                                     │ → "serverless-app/dev/app-secret"    │
│                                     │                                       │
│  ENVIRONMENT: !Ref EnvironmentName  │ os.environ.get("ENVIRONMENT")        │
│                                     │ → "dev"                              │
│                                     │                                       │
│  APPLICATION_NAME: !Ref ...         │ os.environ.get("APPLICATION_NAME")   │
│                                     │ → "serverless-app"                   │
└─────────────────────────────────────────────────────────────────────────────┘


## why use Environment Variables?**

┌─────────────────────────────────────────────────────────────────────────────┐
│  ✓ DO: Use environment variables                                            │
│    - Configuration is separate from code                                    │
│    - Same code works in dev/staging/prod                                   │
│    - Easy to change without redeploying code                               │
│                                                                             │
│  ✗ DON'T: Hard-code values in Python                                       │
│    # Bad!                                                                   │
│    SECRET_NAME = "serverless-app/dev/app-secret"  ← Hard-coded            │
│                                                                             │
│    # Good!                                                                  │
│    SECRET_NAME = os.environ.get("SECRET_NAME")    ← From environment       │
└─────────────────────────────────────────────────────────────────────────────┘


### Events (API Gateway Triggers) Explained
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Events define WHAT TRIGGERS the Lambda function                            │
│                                                                             │
│  This creates 3 triggers:                                                   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Event Name    │  Method  │  Path    │  Full URL                    │   │
│  ├────────────────┼──────────┼──────────┼──────────────────────────────┤   │
│  │  HealthPost    │  POST    │  /health │  POST https://xxx.../health  │   │
│  │  HealthGet     │  GET     │  /health │  GET  https://xxx.../health  │   │
│  │  TestPost      │  POST    │  /test   │  POST https://xxx.../test    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  RestApiId: !Ref ApiGateway                                                │
│  └── Links these events to our API Gateway resource                        │
│                                                                             │
│  Behind the scenes, SAM creates:                                           │
│  1. API Gateway Method for each event                                      │
│  2. API Gateway Integration (Lambda proxy)                                 │
│  3. Lambda Permission (allows API Gateway to invoke Lambda)                │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Request Flow:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   Client                API Gateway              Lambda                     │
│     │                       │                      │                        │
│     │  POST /health         │                      │                        │
│     │──────────────────────►│                      │                        │
│     │                       │  Invoke              │                        │
│     │                       │─────────────────────►│                        │
│     │                       │                      │  lambda_handler()      │
│     │                       │                      │  path == "/health"     │
│     │                       │                      │  method == "POST"      │
│     │                       │◄─────────────────────│                        │
│     │  200 OK               │  Response            │                        │
│     │◄──────────────────────│                      │                        │
│     │                       │                      │                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│  !Sub performs multiple substitutions:                                       │
│                                                                             │
│  ${ApiGateway}     → API Gateway ID (e.g., "abc123xyz")                    │
│  ${AWS::Region}    → Current region (e.g., "us-east-1")                    │
│  ${EnvironmentName}→ Parameter value (e.g., "dev")                         │
│                                                                             │
│  Result:                                                                    │
│  https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev                 │
│          ↑                     ↑                       ↑                   │
│          │                     │                       └── Stage           │
│          │                     └── Region                                   │
│          └── API Gateway ID                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Intrinsic Functions Summary

| Function | Syntax | Purpose | Example |
|----------|--------|---------|---------|
| `!Ref` | `!Ref ResourceName` | Get resource ID/name or parameter value | `!Ref EnvironmentName` → `"dev"` |
| `!Sub` | `!Sub ${Variable}` | String substitution | `!Sub ${AppName}-api` → `"myapp-api"` |
| `!GetAtt` | `!GetAtt Resource.Attribute` | Get resource attribute | `!GetAtt Role.Arn` → `"arn:aws:iam::..."` |
| `!Join` | `!Join [delimiter, [values]]` | Join strings | `!Join ["-", ["a", "b"]]` → `"a-b"` |
| `!If` | `!If [condition, true, false]` | Conditional value | `!If [IsProd, "large", "small"]` |

---

## Complete Resource Diagram
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RESOURCES CREATED                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   ┌────────────────────┐                                                   │
│   │  ApplicationSecret │  AWS::SecretsManager::Secret                      │
│   │                    │  serverless-app/dev/app-secret                    │
│   └─────────┬──────────┘                                                   │
│             │                                                               │
│             │ !Ref (provides ARN)                                          │
│             ▼                                                               │
│   ┌────────────────────┐      ┌─────────────────────┐                      │
│   │ LambdaExecutionRole│      │ HealthCheckLogGroup │                      │
│   │                    │      │                     │                      │
│   │  IAM Role with:    │      │  CloudWatch Logs    │                      │
│   │  - CloudWatch Logs │      │  14 day retention   │                      │
│   │  - Secrets Manager │      │                     │                      │
│   └─────────┬──────────┘      └──────────┬──────────┘                      │
│             │                            │                                  │
│             │ !GetAtt Arn                │ LogGroupName references          │
│             ▼                            ▼                                  │
│   ┌─────────────────────────────────────────────────┐                      │
│   │           HealthCheckFunction                    │                      │
│   │                                                  │                      │
│   │  AWS::Serverless::Function                      │                      │
│   │  - Handler: app.lambda_handler                  │                      │
│   │  - Runtime: python3.12                          │                      │
│   │  - Environment variables                        │                      │
│   └─────────────────────┬───────────────────────────┘                      │
│                         │                                                   │
│                         │ Events                                            │
│                         ▼                                                   │
│   ┌─────────────────────────────────────────────────┐                      │
│   │              ApiGateway                          │                      │
│   │                                                  │                      │
│   │  AWS::Serverless::Api                           │                      │
│   │  - Stage: dev                                   │                      │
│   │  - Endpoints:                                   │                      │
│   │    POST /health                                 │                      │
│   │    GET  /health                                 │                      │
│   │    POST /test                                   │                      │
│   └─────────────────────────────────────────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference Card
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SERVERLESS-APP-TEMPLATE.YAML QUICK REFERENCE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Parameters (inputs):                                                       │
│  - EnvironmentName: dev/staging/prod                                       │
│  - ApplicationName: app name for resource naming                           │
│  - LogRetentionDays: CloudWatch log retention                              │
│                                                                             │
│  Resources created:                                                         │
│  1. ApplicationSecret    - Secrets Manager with auto-generated API key     │
│  2. LambdaExecutionRole  - IAM role with least privilege                   │
│  3. HealthCheckFunction  - Lambda function (Python 3.12)                   │
│  4. HealthCheckLogGroup  - CloudWatch Logs with retention                  │
│  5. ApiGateway           - REST API with /health and /test endpoints       │
│                                                                             │
│  Outputs:                                                                   │
│  - ApiEndpoint          - Base API URL                                     │
│  - HealthEndpoint       - Full health check URL                            │
│  - LambdaFunctionName   - Lambda function name                             │
│  - SecretArn            - Secrets Manager ARN                              │
│                                                                             │
│  Deploy command:                                                            │
│  sam deploy --parameter-overrides EnvironmentName=prod                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```
## Pipeline Flow

┌─────────────────────────────────────────────────────────────────────────────┐
│  ArtifactBucket = Storage for pipeline artifacts                            │
│                                                                             │
│  This bucket stores:                                                        │
│  1. Source code zip from GitHub                                            │
│  2. Build outputs (packaged SAM template)                                  │
│  3. Deployment artifacts                                                   │
│                                                                             │
│  Pipeline Flow:                                                             │
│  ┌────────┐    ┌─────────────────┐    ┌────────┐    ┌────────────────┐    │
│  │ GitHub │───►│ ArtifactBucket  │───►│ Build  │───►│ ArtifactBucket │    │
│  │        │    │ (source.zip)    │    │        │    │ (packaged.yaml)│    │
│  └────────┘    └─────────────────┘    └────────┘    └────────────────┘    │
│                                                           │                │
│                                                           ▼                │
│                                                      ┌────────┐           │
│                                                      │ Deploy │           │
│                                                      └────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘

### CodeBuild Project Explained
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CodeBuild Project = The BUILD stage definition                             │
│                                                                             │
│  This defines:                                                              │
│  1. WHAT to build (Source)                                                 │
│  2. WHERE to build (Environment)                                           │
│  3. HOW to build (BuildSpec)                                               │
│  4. WHERE to put results (Artifacts)                                       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    CodeBuild Execution                               │   │
│  │                                                                     │   │
│  │   1. Spin up container (Environment)                               │   │
│  │      └── amazon linux 2, small compute                             │   │
│  │                                                                     │   │
│  │   2. Download source (from pipeline)                               │   │
│  │      └── source code from S3 artifact bucket                       │   │
│  │                                                                     │   │
│  │   3. Run buildspec.yml commands                                    │   │
│  │      └── install SAM, validate, package                           │   │
│  │                                                                     │   │
│  │   4. Upload artifacts (to pipeline)                                │   │
│  │      └── packaged-template.yaml, config.json                      │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```
### Pipeline Explained
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CodePipeline = The orchestrator of your CI/CD workflow                     │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                          PIPELINE FLOW                                 │ │
│  │                                                                       │ │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐│ │
│  │  │    SOURCE    │───►│    BUILD     │───►│         DEPLOY           ││ │
│  │  │              │    │              │    │                          ││ │
│  │  │ GitHubSource │    │  SAMPackage  │    │ CreateChangeSet          ││ │
│  │  │              │    │              │    │       │                  ││ │
│  │  │ (pulls code) │    │ (runs        │    │       ▼                  ││ │
│  │  │              │    │  buildspec)  │    │ ExecuteChangeSet         ││ │
│  │  └──────────────┘    └──────────────┘    └──────────────────────────┘│ │
│  │        │                    │                       │                 │ │
│  │        ▼                    ▼                       ▼                 │ │
│  │  SourceOutput         BuildOutput            Stack Updated            │ │
│  │  (code.zip)           (packaged.yaml)        (resources created)     │ │
│  │                                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Outputs:
  PipelineUrl:
    Description: URL to the CodePipeline in AWS Console
    Value: !Sub https://${AWS::Region}.console.aws.amazon.com/codesuite/codepipeline/pipelines/${Pipeline}/view

  ArtifactBucket:
    Description: S3 bucket for pipeline artifacts
    Value: !Ref ArtifactBucket
```

### Outputs Explained
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Outputs = Values shown after deployment                                    │
│                                                                             │
│  PipelineUrl:                                                               │
│  !Sub https://${AWS::Region}.console.aws.amazon.com/codesuite/             │
│       codepipeline/pipelines/${Pipeline}/view                              │
│                                                                             │
│  Substitutions:                                                             │
│  ${AWS::Region} → "us-east-1"                                              │
│  ${Pipeline}    → "serverless-app-pipeline-dev" (the pipeline resource)   │
│                                                                             │
│  Result: https://us-east-1.console.aws.amazon.com/codesuite/               │
│          codepipeline/pipelines/serverless-app-pipeline-dev/view           │
│                                                                             │
│  You can click this URL to go directly to your pipeline!                   │
│                                                                             │
│  View outputs via CLI:                                                      │
│  aws cloudformation describe-stacks --stack-name my-stack \                │
│    --query "Stacks[0].Outputs"                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Pipeline Flow Diagram
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COMPLETE PIPELINE FLOW                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   GITHUB                                                                    │
│   ┌─────────────────────┐                                                  │
│   │  Repository         │                                                  │
│   │  - serverless-app-  │                                                  │
│   │    template.yaml    │                                                  │
│   │  - lambda/app.py    │                                                  │
│   │  - buildspec.yml    │                                                  │
│   └──────────┬──────────┘                                                  │
│              │                                                              │
│              │ CodeConnection                                               │
│              ▼                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │                         CODEPIPELINE                                  │ │
│   │                                                                      │ │
│   │  ┌────────────────┐   ┌────────────────┐   ┌────────────────────┐  │ │
│   │  │  SOURCE STAGE  │   │  BUILD STAGE   │   │   DEPLOY STAGE     │  │ │
│   │  │                │   │                │   │                    │  │ │
│   │  │ GitHubSource   │──►│  SAMPackage    │──►│ CreateChangeSet    │  │ │
│   │  │                │   │                │   │       │            │  │ │
│   │  │ Pull code      │   │ Run buildspec  │   │       ▼            │  │ │
│   │  │ from branch    │   │ - sam validate │   │ ExecuteChangeSet   │  │ │
│   │  │                │   │ - sam package  │   │                    │  │ │
│   │  └───────┬────────┘   └───────┬────────┘   └─────────┬──────────┘  │ │
│   │          │                    │                      │              │ │
│   │          ▼                    ▼                      ▼              │ │
│   │    SourceOutput          BuildOutput           CloudFormation       │ │
│   │    (code.zip)            (packaged.yaml)       Stack Created        │ │
│   │                                                                      │ │
│   └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│                                    │                                        │
│                                    ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │                    DEPLOYED RESOURCES                                 │ │
│   │                                                                      │ │
│   │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐ │ │
│   │  │   API Gateway  │  │    Lambda      │  │   Secrets Manager      │ │ │
│   │  │                │  │                │  │                        │ │ │
│   │  │ /health (POST) │──│ app.py         │──│ app-secret             │ │ │
│   │  │ /test (POST)   │  │ lambda_handler │  │ (auto-generated key)   │ │ │
│   │  └────────────────┘  └────────────────┘  └────────────────────────┘ │ │
│   │                                                                      │ │
│   └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## IAM Roles Summary
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           IAM ROLES OVERVIEW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PipelineRole                                                        │   │
│  │  Used by: CodePipeline                                              │   │
│  │  Permissions:                                                        │   │
│  │   - codeconnections:UseConnection (GitHub)                          │   │
│  │   - s3:* (artifact bucket)                                          │   │
│  │   - codebuild:* (trigger builds)                                    │   │
│  │   - cloudformation:* (deploy stacks)                                │   │
│  │   - iam:PassRole (pass CloudFormationRole)                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  CodeBuildRole                                                       │   │
│  │  Used by: CodeBuild                                                 │   │
│  │  Permissions:                                                        │   │
│  │   - logs:* (write build logs)                                       │   │
│  │   - s3:* (read source, write artifacts)                             │   │
│  │   - cloudformation:ValidateTemplate                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  CloudFormationRole                                                  │   │
│  │  Used by: CloudFormation (during deploy)                            │   │
│  │  Permissions:                                                        │   │
│  │   - AdministratorAccess (creates Lambda, API GW, Secrets, IAM)     │   │
│  │   ⚠️  Use least privilege in production!                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference Card
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PIPELINE.YAML QUICK REFERENCE                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Parameters (6):                                                            │
│  - CodeConnectionArn    : GitHub connection ARN                            │
│  - GitHubOwner          : GitHub username/org                              │
│  - GitHubRepo           : Repository name                                  │
│  - GitHubBranch         : Branch to monitor (default: main)               │
│  - ApplicationName      : App name (default: serverless-app)              │
│  - EnvironmentName      : Environment (dev/staging/prod)                  │
│                                                                             │
│  Resources (6):                                                             │
│  1. ArtifactBucket      : S3 bucket for pipeline artifacts                │
│  2. PipelineRole        : IAM role for CodePipeline                       │
│  3. CodeBuildRole       : IAM role for CodeBuild                          │
│  4. CloudFormationRole  : IAM role for CloudFormation deploy              │
│  5. CodeBuildProject    : Build project configuration                     │
│  6. Pipeline            : CodePipeline with 3 stages                      │
│                                                                             │
│  Pipeline Stages (3):                                                       │
│  1. Source  → Pull code from GitHub via CodeConnection                    │
│  2. Build   → Run buildspec.yml (sam package)                             │
│  3. Deploy  → CreateChangeSet + ExecuteChangeSet                          │
│                                                                             │
│  Outputs (2):                                                               │
│  - PipelineUrl     : Direct link to pipeline in console                   │
│  - ArtifactBucket  : Name of the S3 artifact bucket                       │
│                                                                             │
│  Deploy command:                                                            │
│  aws cloudformation deploy \                                               │
│    --template-file pipeline.yaml \                                         │
│    --stack-name my-pipeline \                                              │
│    --parameter-overrides \                                                 │
│      CodeConnectionArn="arn:aws:codeconnections:..." \                    │
│      GitHubOwner="myuser" \                                                │
│      GitHubRepo="myrepo" \                                                 │
│    --capabilities CAPABILITY_NAMED_IAM                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

discard-paths: yes
```
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  discard-paths: yes                                                         │
│                                                                             │
│  Controls whether directory structure is preserved in artifact.            │
│                                                                             │
│  discard-paths: yes (flatten):                                             │
│  ┌────────────────────────────┐    ┌────────────────────────────┐         │
│  │  Build Directory:          │    │  Artifact ZIP:             │         │
│  │  /codebuild/output/        │    │                            │         │
│  │  ├── src/                  │ ──►│  packaged-template.yaml   │         │
│  │  │   └── packaged.yaml     │    │  config.json              │         │
│  │  └── config/               │    │                            │         │
│  │      └── config.json       │    │  (flat structure)         │         │
│  └────────────────────────────┘    └────────────────────────────┘         │
│                                                                             │
│  discard-paths: no (preserve):                                             │
│  ┌────────────────────────────┐    ┌────────────────────────────┐         │
│  │  Build Directory:          │    │  Artifact ZIP:             │         │
│  │  /codebuild/output/        │    │  src/                      │         │
│  │  ├── src/                  │ ──►│  └── packaged.yaml        │         │
│  │  │   └── packaged.yaml     │    │  config/                   │         │
│  │  └── config/               │    │  └── config.json          │         │
│  │      └── config.json       │    │                            │         │
│  └────────────────────────────┘    └────────────────────────────┘         │
│                                                                             │
│  Why use discard-paths: yes?                                               │
│  - Simpler to reference in deploy stage                                   │
│  - TemplatePath: BuildOutput::packaged-template.yaml (not full path)     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Build Flow Diagram. (buidlspec.yml)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COMPLETE BUILD FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  INSTALL PHASE                                                       │   │
│  │                                                                     │   │
│  │  1. Set Python 3.12 as runtime                                     │   │
│  │  2. Upgrade pip                                                     │   │
│  │  3. Install AWS SAM CLI                                            │   │
│  │  4. Verify SAM version                                             │   │
│  │                                                                     │   │
│  │  Duration: ~30-60 seconds                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PRE_BUILD PHASE                                                     │   │
│  │                                                                     │   │
│  │  1. Validate SAM template (sam validate --lint)                    │   │
│  │  2. Validate CloudFormation syntax (aws cloudformation validate)   │   │
│  │                                                                     │   │
│  │  If validation fails → BUILD STOPS                                 │   │
│  │                                                                     │   │
│  │  Duration: ~5-10 seconds                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  BUILD PHASE                                                         │   │
│  │                                                                     │   │
│  │  1. Run sam package                                                 │   │
│  │     - Zip lambda/ directory                                        │   │
│  │     - Upload ZIP to S3 bucket                                      │   │
│  │     - Create packaged-template.yaml                                │   │
│  │                                                                     │   │
│  │  2. Create config.json                                             │   │
│  │     - Parameter values                                             │   │
│  │     - Tags                                                          │   │
│  │                                                                     │   │
│  │  Duration: ~20-40 seconds                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  POST_BUILD PHASE                                                    │   │
│  │                                                                     │   │
│  │  1. Print completion message                                       │   │
│  │  2. List files (verify artifacts exist)                           │   │
│  │                                                                     │   │
│  │  Duration: ~1-2 seconds                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ARTIFACTS                                                           │   │
│  │                                                                     │   │
│  │  Files collected:                                                   │   │
│  │  ┌─────────────────────────┐                                       │   │
│  │  │ packaged-template.yaml  │ → SAM template with S3 refs          │   │
│  │  │ config.json             │ → Parameters and tags                │   │
│  │  └─────────────────────────┘                                       │   │
│  │                              │                                      │   │
│  │                              ▼                                      │   │
│  │                         ZIP & Upload                                │   │
│  │                              │                                      │   │
│  │                              ▼                                      │   │
│  │                    S3: BuildOutput artifact                        │   │
│  │                              │                                      │   │
│  │                              ▼                                      │   │
│  │                       Deploy Stage                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  TOTAL DURATION: ~1-2 minutes                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

# List all CodeConnections
aws codeconnections list-connections --output table

# Or get specific connection ARN by name
aws codeconnections list-connections \
  --query "Connections[?ConnectionName=='GitHub-pipeline'].ConnectionArn" \
  --output text

# Verify connection status (must be AVAILABLE)
aws codeconnections get-connection \
  --connection-arn "arn:aws:codeconnections:us-east-2:615299756109:connection/1f6ccd5f-ab59-4669-8829-216b19d3d570" \
  --query "Connection.ConnectionStatus" \
  --output text

# Set your values (UPDATE THESE!)
export AWS_REGION="us-east-2"
export CONNECTION_ARN="arn:aws:codeconnections:us-east-2:615299756109:connection/1f6ccd5f-ab59-4669-8829-216b19d3d570"
export GITHUB_OWNER="bhattsachi"
export GITHUB_REPO="Data-pipeline-aws"
export GITHUB_BRANCH="Dev-pipeline"
export APP_NAME="serverless-app"
export ENV_NAME="dev"

# Verify variables are set
echo "Region: $AWS_REGION"
echo "Connection: $CONNECTION_ARN"
echo "GitHub: $GITHUB_OWNER/$GITHUB_REPO ($GITHUB_BRANCH)"
echo "App: $APP_NAME-$ENV_NAME"

# Deploy the pipeline
aws cloudformation deploy \
  --template-file cloudformation/pipeline.yml \
  --stack-name ${APP_NAME}-pipeline-${ENV_NAME} \
  --parameter-overrides \
    CodeConnectionArn="$CONNECTION_ARN" \
    GitHubOwner="$GITHUB_OWNER" \
    GitHubRepo="$GITHUB_REPO" \
    GitHubBranch="$GITHUB_BRANCH" \
    ApplicationName="serverless-app" \
    EnvironmentName="dev" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $AWS_REGION

# Wait for stack to complete
aws cloudformation wait stack-create-complete \
  --stack-name ${APP_NAME}-pipeline-${ENV_NAME} \
  --region $AWS_REGION

echo "Pipeline stack deployed!"

# Get pipeline URL
PIPELINE_URL=$(aws cloudformation describe-stacks \
  --stack-name ${APP_NAME}-pipeline-${ENV_NAME} \
  --query "Stacks[0].Outputs[?OutputKey=='PipelineUrl'].OutputValue" \
  --output text \
  --region $AWS_REGION)

echo "Pipeline URL: $PIPELINE_URL"

# Get pipeline name
PIPELINE_NAME=$(aws cloudformation describe-stacks \
  --stack-name ${APP_NAME}-pipeline-${ENV_NAME} \
  --query "Stacks[0].Outputs[?OutputKey=='PipelineName'].OutputValue" \
  --output text \
  --region $AWS_REGION)

echo "Pipeline Name: $PIPELINE_NAME"

# Manually start pipeline execution
aws codepipeline start-pipeline-execution \
  --name ${APP_NAME}-pipeline-${ENV_NAME} \
  --region $AWS_REGION

echo "Pipeline execution started!"

# Check pipeline status
aws codepipeline get-pipeline-state \
  --name ${APP_NAME}-pipeline-${ENV_NAME} \
  --query "stageStates[*].{Stage:stageName,Status:latestExecution.status}" \
  --output table \
  --region $AWS_REGION

# Watch pipeline progress (run multiple times)
watch -n 10 "aws codepipeline get-pipeline-state \
  --name ${APP_NAME}-pipeline-${ENV_NAME} \
  --query 'stageStates[*].{Stage:stageName,Status:latestExecution.status}' \
  --output table"
```

**Expected Output (In Progress):**
```
---------------------------
|    GetPipelineState     |
+----------+--------------+
|  Stage   |   Status     |
+----------+--------------+
|  Source  |  Succeeded   |
|  Build   |  InProgress  |
|  Deploy  |  None        |
+----------+--------------+
```

**Expected Output (Complete):**
```
---------------------------
|    GetPipelineState     |
+----------+--------------+
|  Stage   |   Status     |
+----------+--------------+
|  Source  |  Succeeded   |
|  Build   |  Succeeded   |
|  Deploy  |  Succeeded   |
+----------+--------------+

# Wait for application stack to be created
aws cloudformation wait stack-create-complete \
  --stack-name ${APP_NAME}-${ENV_NAME} \
  --region $AWS_REGION

# Get API endpoints
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name ${APP_NAME}-${ENV_NAME} \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text \
  --region $AWS_REGION)

HEALTH_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name ${APP_NAME}-${ENV_NAME} \
  --query "Stacks[0].Outputs[?OutputKey=='HealthEndpoint'].OutputValue" \
  --output text \
  --region $AWS_REGION)

echo ""
echo "=========================================="
echo "  API ENDPOINTS"
echo "=========================================="
echo "Base URL:    $API_ENDPOINT"
echo "Health:      $HEALTH_ENDPOINT"
echo "Test:        ${API_ENDPOINT}/test"
echo "=========================================="

# POST request to /health
curl -X POST "$HEALTH_ENDPOINT" \
  -H "Content-Type: application/json" \
  | jq .

# Expected Response:
# {
#   "status": "healthy",
#   "message": "Service is running",
#   "timestamp": "2024-01-15T10:30:45.123456+00:00",
#   "environment": "dev",
#   "application": "serverless-app",
#   "request_id": "abc123-def456",
#   "secret_config": {
#     "app_name": "serverless-app",
#     "environment": "dev",
#     "api_key_present": true
#   }
# }

# POST request to /test with JSON body
curl -X POST "${API_ENDPOINT}/test" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello World",
    "user": "John Doe",
    "test": true
  }' | jq .

# Expected Response:
# {
#   "status": "success",
#   "message": "Test endpoint working",
#   "timestamp": "2024-01-15T10:30:45.123456+00:00",
#   "environment": "dev",
#   "echo": {
#     "method": "POST",
#     "path": "/test",
#     "body": {
#       "message": "Hello World",
#       "user": "John Doe",
#       "test": true
#     }
#   },
#   "secret_verified": true
# }

# Get detailed error message
aws codepipeline get-pipeline-state \
  --name serverless-app-pipeline-dev \
  --query "stageStates[?stageName=='Source'].actionStates[0].latestExecution.errorDetails" \
  --output json
```
```
#!/bin/bash

# ════════════════════════════════════════════════════════════════════════════
# UPDATE THESE VALUES
# ════════════════════════════════════════════════════════════════════════════
PIPELINE_NAME="serverless-app-pipeline-dev"
CONNECTION_ARN="arn:aws:codeconnections:us-east-2:615299756109:connection/1f6ccd5f-ab59-4669-8829-216b19d3d570"

# ════════════════════════════════════════════════════════════════════════════
# GET ROLE NAME
# ════════════════════════════════════════════════════════════════════════════
echo "Getting pipeline role..."
ROLE_ARN=$(aws codepipeline get-pipeline \
  --name $PIPELINE_NAME \
  --query "pipeline.roleArn" \
  --output text)
ROLE_NAME=$(echo $ROLE_ARN | cut -d'/' -f2)
echo "Role: $ROLE_NAME"

# ════════════════════════════════════════════════════════════════════════════
# ADD POLICY
# ════════════════════════════════════════════════════════════════════════════
CONNECTION_ARN="arn:aws:codeconnections:us-east-2:615299756109:connection/1f6ccd5f-ab59-4669-8829-216b19d3d570"

echo "Adding CodeConnections permission..."
aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name CodeConnectionsAccess \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": [
          \"codeconnections:UseConnection\",
          \"codeconnections:GetConnection\"
        ],
        \"Resource\": \"$CONNECTION_ARN\"
      }
    ]
  }"

echo "✓ Permission added!"
# ----------------
# Check existing policy
# -----------------------
aws iam get-role-policy \
 --role-name "$ROLE_NAME" \
 --policy-name "CodeConnectionsAccess"
# ════════════════════════════════════════════════════════════════════════════
# RETRY PIPELINE
# ════════════════════════════════════════════════════════════════════════════
echo "Restarting pipeline..."
aws codepipeline start-pipeline-execution --name $PIPELINE_NAME

echo "✓ Pipeline restarted!"
echo ""
echo "Monitor status with:"
echo "aws codepipeline get-pipeline-state --name $PIPELINE_NAME --query \"stageStates[*].[stageName,latestExecution.status]\" --output table"

# List all policies on the role
echo "=== Inline Policies ==="
aws iam list-role-policies --role-name $ROLE_NAME

echo ""
echo "=== CodeConnections Policy Content ==="
aws iam get-role-policy \
  --role-name $ROLE_NAME \
  --policy-name CodeConnectionsAccess \
  --query "PolicyDocument" \
  --output json

# Start new pipeline execution
aws codepipeline start-pipeline-execution \
  --name serverless-app-pipeline-dev

# Watch the status
aws codepipeline get-pipeline-state \
  --name serverless-app-pipeline-dev \
  --query 'stageStates[*].[stageName,latestExecution.status]' \
  --output table"
```

### Expected Result
```
------------------------------
|     GetPipelineState       |
+----------+-----------------+
|  Source  |  InProgress     |  ← Should progress now!
|  Build   |  None           |
|  Deploy  |  None           |
+----------+-----------------+
```

Then:
```
------------------------------
|     GetPipelineState       |
+----------+-----------------+
|  Source  |  Succeeded      |  ← Fixed!
|  Build   |  InProgress     |
|  Deploy  |  None           |
+----------+-----------------+  

ROLE_NAME="serverless-app-pipeline-role-dev"

# Grant broader codeconnections access (for testing only!)
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "CodeConnectionsFullAccess" \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": [
          \"codeconnections:*\"
        ],
        \"Resource\": \"*\"
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": [
          \"codestar-connections:*\"
        ],
        \"Resource\": \"*\"
      }
    ]
  }"

echo "Broad permissions added. Try pipeline again."

aws codepipeline get-pipeline \
  --name serverless-app-pipeline-dev  \
  --region us-east-2 \
  --query "pipeline.stages[?name=='Source'].actions[0].configuration.[FullRepositoryId,BranchName]" \
  --output table
```

**Example Output:**
```
-------------------------------------------
|              GetPipeline                |
+-----------------------+-----------------+
|  Data-pipeline-aws    |  Dev-pipeline   |   ← Branch name configured
+-----------------------+-----------------+



cd Data-pipeline-aws

# Replace .yaml with .yml in buildspec.yml
sed -i 's/serverless-app-template\.yaml/serverless-app-template.yml/g' buildspec.yml

# Verify the change
grep "serverless-app-template" buildspec.yml

# Commit and push
git add buildspec.yml
git commit -m "Fix: Use .yml extension for template file"
git push origin main

aws cloudformation deploy \
  --template-file cloudformation/pipeline.yml \
  --stack-name serverless-app-pipeline-dev \
  --parameter-overrides \
    CodeConnectionArn="arn:aws:codeconnections:us-east-2:615299756109:connection/1f6ccd5f-ab59-4669-8829-216b19d3d570" \
    GitHubOwner="YOUR_GITHUB_USERNAME" \
    GitHubRepo="Data-pipeline-aws" \
    GitHubBranch="main" \
    ApplicationName="serverless-app" \
    EnvironmentName="dev" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-2

echo "✓ Pipeline redeployed!"

rise21up#

git clone https://github.com/bhattsachi/Data-pipeline-aws.git

# Usefull commands

# Monitor pipeline
aws codepipeline get-pipeline-state \
  --name serverless-app-pipeline-dev \
  --region us-east-2 \
  --query "stageStates[*].[stageName,latestExecution.status]" \
  --output table

# View Lambda logs
aws logs tail /aws/lambda/serverless-app-dev-health --follow --region us-east-2

# Get all stack outputs
aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs" \
  --output table

## Get all URL path
# Get ALL outputs from your stack
aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs" \
  --output table

  ##  Complete Test scripts


REGION="us-east-2"
STACK_NAME="serverless-app-dev"

echo "=== Getting API Information ==="

# Get API endpoint
API_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text)

HEALTH_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query "Stacks[0].Outputs[?OutputKey=='HealthEndpoint'].OutputValue" \
  --output text)

echo ""
echo "API Base URL: $API_URL"
echo "Health URL:   $HEALTH_URL"
echo ""

echo "=== Testing Health Endpoint (POST) ==="
echo "URL: $HEALTH_URL"
echo "Response:"
curl -s -X POST "$HEALTH_URL" -H "Content-Type: application/json" | jq .

echo ""
echo "=== Testing Health Endpoint (GET) ==="
curl -s -X GET "$HEALTH_URL" | jq .

echo ""
echo "=== Testing Test Endpoint (POST) ==="
echo "URL: ${API_URL}/test"
curl -s -X POST "${API_URL}/test" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}' | jq .


## Final API END point Output

API Base URL: https://2vkbu4xudg.execute-api.us-east-2.amazonaws.com/dev
echo "URL: ${API_URL}/test"
URL: https://2vkbu4xudg.execute-api.us-east-2.amazonaws.com/dev/test

~ $ curl -s -X POST "${API_URL}/test" \
>   -H "Content-Type: application/json" \
>   -d '{"message": "Hello!"}' | jq .
{
  "status": "success",
  "message": "Test endpoint working",
  "timestamp": "2025-12-23T23:51:52.871388+00:00",
  "environment": "dev",
  "echo": {
    "method": "POST",
    "path": "/test",
    "body": {
      "message": "Hello!"
    }
  },
  "secret_verified": true
}

https://2vkbu4xudg.execute-api.us-east-2.amazonaws.com/dev

## API Gateway Endpoint testing ( getting response back from Lambda)
  curl -s -X POST "https://2vkbu4xudg.execute-api.us-east-2.amazonaws.com/dev/test" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}' | jq .

## Response from Lambda 
  {
  "status": "success",
  "message": "Test endpoint working",
  "timestamp": "2025-12-29T22:21:18.740613+00:00",
  "environment": "dev",
  "echo": {
    "method": "POST",
    "path": "/test",
    "body": {
      "message": "Hello!"
    }
  },
  "secret_verified": true
}

## ----------------------------------------------------------
   ## STEP FUNCTION  AND GLUE JOBS SECTION 
## ----------------------------------------------------------

 import boto3
import pandas as pd
import json
import yaml
from io import BytesIO

# Initialize S3 client
s3 = boto3.client('s3')

# Input and output bucket details
bucket_name = 'dev-batuu-mh-apps'
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
        sns_topic_arn = "arn:aws:sns:us-east-1:533267066040:glue-job-failure-notify:f39f1ce9-972f-4fae-ab8c-ce67e92fee73"
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
## ------------
## Folder structure
from step_functions_manager import StepFunctionsManager

manager = StepFunctionsManager(region="us-east-2")

# Create role
role_arn = manager.create_step_function_role("my-sfn-role")

# Create state machine
sm_arn = manager.create_glue_job_state_machine(
    state_machine_name="my-glue-orchestrator",
    glue_job_name="serverless-app-csv-processor-dev",
    role_arn=role_arn,
    input_path="s3://my-bucket/input/",
    output_path="s3://my-bucket/output/"
)

# Start execution
exec_arn = manager.start_execution(
    state_machine_arn=sm_arn,
    input_path="s3://my-bucket/input/",
    output_path="s3://my-bucket/output/"
)

# Wait for completion
result = manager.wait_for_completion(exec_arn)
print(f"Final status: {result['status']}")

## Final Folder Structure
```
Data-pipeline-aws/
├── serverless-app-template.yml    ← SAM template (API + Glue only)
├── buildspec.yml
├── dev.json
│
├── lambda/
│   └── api/
│       └── app.py                 ← API Lambda only
│
├── glue/
│   ├── csv_processor.py           ← Glue script
│   └── sample_data.csv
│
├── scripts/                       ← NEW: Python scripts for Step Functions
│   ├── step_functions_manager.py  ← Full-featured manager class
│   ├── run_glue_workflow.py       ← Simple CLI script
│   └── requirements.txt
│
└── cloudformation/
    └── pipeline.yaml
```

---

## Summary
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                            │
│              │
│  Step Functions created programmatically via Python (Boto3)        │
│                                                                             │
│  BENEFITS:                                                                  │
│  ✓ Dynamic state machine creation                                          │
│  ✓ Easy to modify workflow logic in Python                                │
│  ✓ Can create multiple state machines programmatically                    │
│  ✓ Reusable manager class                                                  │
│  ✓ No Lambda functions for orchestration                                  │
│                                                                             │
│  WORKFLOW:                                                                  │
│  1. Pipeline deploys API + Glue Job                                        │
│  2. Python script creates Step Functions state machine                    │
│  3. Python script starts execution                                         │
│  4. Step Functions directly invokes Glue job                              │
│  5. Glue job processes CSV and writes output                              │
│                                                                             │
│  COMMAND:                                                                   │
│  python3 scripts/run_glue_workflow.py --region us-east-2                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

The generated Step Function has this workflow:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  START                                                                      │
│    │                                                                        │
│    ▼                                                                        │
│  ┌─────────────────┐                                                       │
│  │ InvokeGlueJob   │──── Runs Glue job with arguments                     │
│  │ (with retry)    │     Retry: 2 attempts, 60s interval                  │
│  └────────┬────────┘                                                       │
│           │                                                                 │
│     ┌─────┴─────┐ (on error)                                               │
│     │           │                                                          │
│     ▼           ▼                                                          │
│  ┌──────────────────┐   ┌─────────────────┐                                │
│  │CheckGlueJobStatus│   │  NotifyFailure  │──► SNS Notification            │
│  └────────┬─────────┘   └────────┬────────┘                                │
│           │                      │                                          │
│     ┌─────┴─────┐                ▼                                          │
│     │           │         ┌─────────────┐                                  │
│     ▼           ▼         │  FailState  │                                  │
│  ┌────────┐  ┌────────┐   └─────────────┘                                  │
│  │SUCCESS │  │ FAILED │                                                    │
│  └────────┘  └───┬────┘                                                    │
│                  │                                                          │
│                  ▼                                                          │
│           NotifyFailure ──► SNS                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘show the repository structure after the latest changes4:03 PMRepository Structure After Latest Changes
bashcd ~/Data-pipeline-aws

echo "=== Repository Structure ==="
find . -type f \( -name "*.py" -o -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.csv" -o -name "*.txt" -o -name "*.md" \) | grep -v __pycache__ | grep -v ".git" | sort
```

---

## Complete Folder Structure
```
Data-pipeline-aws/
│
├── serverless-app-template.yml      ← Main SAM/CloudFormation template
├── buildspec.yml                    ← CodeBuild build instructions
├── dev.json                         ← Environment configuration
├── README.md                        ← Project documentation (optional)
│
├── lambda/                          ← Lambda functions
│   └── api/
│       └── app.py                   ← API Gateway Lambda handler
│
├── glue/                            ← Glue resources
│   ├── csv_processor.py             ← Glue PySpark ETL script
│   └── sample_data.csv              ← Sample test data
│
├── scripts/                         ← Python scripts (Boto3)
│   ├── __init__.py
│   ├── invoke_step_function.py      ← Main Step Function manager
│   ├── check_status.py              ← Check execution status
│   ├── upload_and_run.py            ← Upload data and run workflow
│   └── requirements.txt             ← Python dependencies
│
└── cloudformation/                  ← Infrastructure templates
    └── pipeline.yaml                ← CI/CD Pipeline template
```

---

## Detailed File Descriptions
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ROOT FILES                                                                 │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  serverless-app-template.yml                                               │
│  └── Main SAM template defining:                                           │
│      • API Gateway + Lambda (health endpoint)                              │
│      • Glue Job (CSV processor)                                            │
│      • Step Functions State Machine                                        │
│      • S3 Bucket (data storage)                                            │
│      • IAM Roles                                                           │
│      • Secrets Manager                                                     │
│                                                                             │
│  buildspec.yml                                                             │
│  └── CodeBuild instructions:                                               │
│      • Install SAM CLI                                                     │
│      • Validate template                                                   │
│      • Package application                                                 │
│      • Upload Glue scripts to S3                                          │
│                                                                             │
│  dev.json                                                                  │
│  └── Environment-specific parameters:                                      │
│      • EnvironmentName: dev                                                │
│      • ApplicationName: serverless-app                                    │
│      • LogRetentionDays: 14                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  lambda/api/                                                               │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  app.py                                                                    │
│  └── API Lambda function:                                                  │
│      • GET/POST /health - Health check endpoint                           │
│      • Reads secrets from Secrets Manager                                 │
│      • Returns JSON responses                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  glue/                                                                     │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  csv_processor.py                                                          │
│  └── Glue PySpark script:                                                  │
│      • Reads CSV from S3 input path                                       │
│      • Adds processed_at timestamp column                                 │
│      • Writes output as Parquet and CSV                                   │
│      • Arguments: --INPUT_PATH, --OUTPUT_PATH                             │
│                                                                             │
│  sample_data.csv                                                           │
│  └── Test data with columns:                                               │
│      • id, name, email, age, department, salary                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  scripts/                                                                  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  invoke_step_function.py (MAIN SCRIPT)                                    │
│  └── Step Function Manager:                                                │
│      • --generate    : Read CSV from S3, generate Step Function definitions│
│      • --list        : List available step functions                      │
│      • --invoke      : Create state machine and start execution           │
│      • --create-state-machine : Create/update state machine only          │
│      Features:                                                             │
│      • SNS failure notifications                                          │
│      • Retry logic for Glue exceptions                                    │
│      • Uploads individual JSON + combined YAML to S3                      │
│      • Merges with existing definitions                                   │
│                                                                             │
│  check_status.py                                                           │
│  └── Check execution status:                                               │
│      • --list        : List recent executions                             │
│      • <exec-arn>    : Check specific execution                           │
│                                                                             │
│  upload_and_run.py                                                         │
│  └── Upload CSV and run workflow:                                          │
│      • Uploads file to S3 input folder                                    │
│      • Starts Step Function execution                                     │
│      • Waits for completion                                                │
│                                                                             │
│  requirements.txt                                                          │
│  └── Python dependencies:                                                  │
│      • boto3>=1.28.0                                                      │
│      • pandas                                                              │
│      • pyyaml                                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  cloudformation/                                                           │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  pipeline.yaml                                                             │
│  └── CI/CD Pipeline:                                                       │
│      • Source Stage - GitHub (CodeConnections)                            │
│      • Build Stage - CodeBuild (SAM package)                              │
│      • Deploy Stage - CloudFormation (CreateChangeSet, ExecuteChangeSet)  │
│      Resources:                                                            │
│      • CodePipeline                                                        │
│      • CodeBuild Project                                                   │
│      • S3 Artifact Bucket                                                  │
│      • IAM Roles (Pipeline, CodeBuild, CloudFormation)                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Visual Tree Structure
```
Data-pipeline-aws/
│
│   # ═══════════════════════════════════════════════════════════════════════
│   # ROOT - Main Configuration Files
│   # ═══════════════════════════════════════════════════════════════════════
│
├── serverless-app-template.yml    # SAM template (API + Glue + Step Functions)
├── buildspec.yml                  # CodeBuild instructions
├── dev.json                       # Environment parameters
│
│   # ═══════════════════════════════════════════════════════════════════════
│   # LAMBDA - API Functions
│   # ═══════════════════════════════════════════════════════════════════════
│
├── lambda/
│   └── api/
│       └── app.py                 # Health check API handler
│
│   # ═══════════════════════════════════════════════════════════════════════
│   # GLUE - ETL Scripts
│   # ═══════════════════════════════════════════════════════════════════════
│
├── glue/
│   ├── csv_processor.py           # PySpark ETL script
│   └── sample_data.csv            # Test data
│
│   # ═══════════════════════════════════════════════════════════════════════
│   # SCRIPTS - Python Boto3 Scripts
│   # ═══════════════════════════════════════════════════════════════════════
│
├── scripts/
│   ├── __init__.py                # Package init
│   ├── invoke_step_function.py    # Main manager (generate/invoke)
│   ├── check_status.py            # Status checker
│   ├── upload_and_run.py          # Upload + run helper
│   └── requirements.txt           # Dependencies
│
│   # ═══════════════════════════════════════════════════════════════════════
│   # CLOUDFORMATION - Infrastructure
│   # ═══════════════════════════════════════════════════════════════════════
│
└── cloudformation/
    └── pipeline.yaml              # CI/CD Pipeline

Update requirements.txt
bashcat > scripts/requirements.txt << 'EOF'
boto3>=1.28.0
pandas>=2.0.0
pyyaml>=6.0
EOF

echo "✓ Updated scripts/requirements.txt"

Quick Reference Commands
bash# ═══════════════════════════════════════════════════════════════════════════
# DEPLOYMENT (via CI/CD)
# ═══════════════════════════════════════════════════════════════════════════

# Push to GitHub → Pipeline auto-deploys
git add .
git commit -m "Your commit message"
git push origin main

# ═══════════════════════════════════════════════════════════════════════════
# STEP FUNCTION SCRIPTS
# ═══════════════════════════════════════════════════════════════════════════

# Install dependencies
pip install -r scripts/requirements.txt

# Generate Step Function definitions from CSV
python scripts/invoke_step_function.py --generate \
  --bucket dev-batuu-mh-apps \
  --input-prefix snaplogic-migration/task_output/ \
  --output-prefix snaplogic-migration/stepfunction_scripts/

# List available step functions
python scripts/invoke_step_function.py --list

# Create state machine in AWS
python scripts/invoke_step_function.py --create-state-machine JOB_NAME \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/StepFunctionsRole

# Invoke step function
python scripts/invoke_step_function.py --invoke JOB_NAME \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/StepFunctionsRole

# Check execution status
python scripts/check_status.py --list
python scripts/check_status.py EXECUTION_ARN

# Upload data and run
python scripts/upload_and_run.py data.csv

# ═══════════════════════════════════════════════════════════════════════════
# AWS CLI COMMANDS
# ═══════════════════════════════════════════════════════════════════════════

# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --query "Stacks[0].Outputs" \
  --output table

# Upload Glue script
aws s3 cp glue/csv_processor.py s3://BUCKET/scripts/csv_processor.py

# Check pipeline status
aws codepipeline get-pipeline-state \
  --name serverless-app-pipeline-dev \
  --query "stageStates[*].[stageName,latestExecution.status]" \
  --output table
```

---

## Summary
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  REPOSITORY STRUCTURE SUMMARY                                              │
│                                                                             │
│  Total Folders: 5                                                          │
│  ├── lambda/api/         (1 file)  - API Lambda                           │
│  ├── glue/               (2 files) - Glue scripts + test data             │
│  ├── scripts/            (5 files) - Python Boto3 scripts                 │
│  └── cloudformation/     (1 file)  - CI/CD Pipeline                       │
│                                                                             │
│  Total Files: 12                                                           │
│  ├── Root:        3 (template, buildspec, dev.json)                       │
│  ├── Lambda:      1 (app.py)                                              │
│  ├── Glue:        2 (csv_processor.py, sample_data.csv)                   │
│  ├── Scripts:     5 (invoke, check, upload, __init__, requirements)       │
│  └── CFN:         1 (pipeline.yaml)                                       │
│                                                                             │
│  KEY COMPONENTS:                                                            │
│  • CloudFormation defines infrastructure (Step Functions in YAML)         │
│  • Python scripts invoke/manage Step Functions (Boto3)                    │
│  • CI/CD pipeline auto-deploys on GitHub push                             │
│  • No Lambda in Step Functions workflow (direct Glue invocation)          │
│  • SNS notifications on Glue job failures                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘use pipfile instead of requirement.txt4:06 PMUpdate: Use Pipfile Instead of requirements.txt
Step 1: Remove requirements.txt and Create Pipfile
bashcd ~/Data-pipeline-aws/scripts

# Remove requirements.txt
rm -f requirements.txt

# Create Pipfile
cat > Pipfile << 'EOF'
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
boto3 = ">=1.28.0"
pandas = ">=2.0.0"
pyyaml = ">=6.0"

[dev-packages]
pytest = ">=7.0.0"
pytest-cov = ">=4.0.0"
black = ">=23.0.0"
flake8 = ">=6.0.0"
mypy = ">=1.0.0"
boto3-stubs = {extras = ["stepfunctions", "s3", "glue", "sts"], version = ">=1.28.0"}

[requires]
python_version = "3.9"

[scripts]
generate = "python invoke_step_function.py --generate"
list = "python invoke_step_function.py --list"
check = "python check_status.py --list"
lint = "flake8 ."
format = "black ."
test = "pytest"
EOF

echo "✓ Created scripts/Pipfile"

Step 2: Create Pipfile.lock (Optional - Generated by pipenv)
bash# Create a basic Pipfile.lock structure
# Note: This will be regenerated when you run `pipenv install`

cat > Pipfile.lock << 'EOF'
{
    "_meta": {
        "hash": {
            "sha256": "placeholder-will-be-regenerated-by-pipenv"
        },
        "pipfile-spec": 6,
        "requires": {
            "python_version": "3.9"
        },
        "sources": [
            {
                "name": "pypi",
                "url": "https://pypi.org/simple",
                "verify_ssl": true
            }
        ]
    },
    "default": {},
    "develop": {}
}
EOF

echo "✓ Created scripts/Pipfile.lock (placeholder)"
echo "  Run 'pipenv install' to generate actual lock file"
```

---

## Step 3: Update Repository Structure
```
Data-pipeline-aws/
│
├── serverless-app-template.yml
├── buildspec.yml
├── dev.json
│
├── lambda/
│   └── api/
│       └── app.py
│
├── glue/
│   ├── csv_processor.py
│   └── sample_data.csv
│
├── scripts/
│   ├── __init__.py
│   ├── invoke_step_function.py
│   ├── check_status.py
│   ├── upload_and_run.py
│   ├── Pipfile                    ← NEW (replaces requirements.txt)
│   └── Pipfile.lock               ← NEW (dependency lock)
│
└── cloudformation/
    └── pipeline.yaml

Step 4: Usage with Pipenv
bash# ═══════════════════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════════════════

# Install pipenv if not installed
pip install pipenv

# Navigate to scripts folder
cd ~/Data-pipeline-aws/scripts

# Install dependencies
pipenv install

# Install dev dependencies too
pipenv install --dev

# ═══════════════════════════════════════════════════════════════════════════
# RUNNING SCRIPTS
# ═══════════════════════════════════════════════════════════════════════════

# Option 1: Use pipenv run
pipenv run python invoke_step_function.py --generate
pipenv run python invoke_step_function.py --list
pipenv run python check_status.py --list

# Option 2: Use pipenv shell (activates virtual environment)
pipenv shell
python invoke_step_function.py --generate
python invoke_step_function.py --list
exit  # Exit virtual environment

# Option 3: Use predefined scripts from Pipfile
pipenv run generate    # Same as: python invoke_step_function.py --generate
pipenv run list        # Same as: python invoke_step_function.py --list
pipenv run check       # Same as: python check_status.py --list

# ═══════════════════════════════════════════════════════════════════════════
# DEVELOPMENT
# ═══════════════════════════════════════════════════════════════════════════

# Format code
pipenv run format

# Lint code
pipenv run lint

# Run tests
pipenv run test

# ═══════════════════════════════════════════════════════════════════════════
# DEPENDENCY MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

# Add new package
pipenv install package-name

# Add dev package
pipenv install --dev package-name

# Update all packages
pipenv update

# Generate requirements.txt (if needed for compatibility)
pipenv requirements > requirements.txt

# Check for security vulnerabilities
pipenv check

Step 5: Complete Updated Pipfile with All Options
bashcat > scripts/Pipfile << 'EOF'
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
# AWS SDK
boto3 = ">=1.28.0"
botocore = ">=1.31.0"

# Data Processing
pandas = ">=2.0.0"

# Configuration
pyyaml = ">=6.0"

[dev-packages]
# Testing
pytest = ">=7.0.0"
pytest-cov = ">=4.0.0"
pytest-mock = ">=3.10.0"
moto = ">=4.0.0"  # AWS mocking for tests

# Code Quality
black = ">=23.0.0"
flake8 = ">=6.0.0"
isort = ">=5.12.0"
mypy = ">=1.0.0"

# Type Stubs
boto3-stubs = {extras = ["stepfunctions", "s3", "glue", "sts", "cloudformation", "sns"], version = ">=1.28.0"}
pandas-stubs = ">=2.0.0"

[requires]
python_version = "3.9"

[scripts]
# Step Function Management
generate = "python invoke_step_function.py --generate"
list = "python invoke_step_function.py --list"
check = "python check_status.py --list"

# Code Quality
lint = "flake8 ."
format = "black ."
sort = "isort ."
typecheck = "mypy ."

# Testing
test = "pytest"
test-cov = "pytest --cov=. --cov-report=html"

# All checks
all-checks = "bash -c 'black . && isort . && flake8 . && mypy . && pytest'"
EOF

echo "✓ Created scripts/Pipfile with full configuration"

Step 6: Add .python-version (Optional)
bashcat > scripts/.python-version << 'EOF'
3.9
EOF

echo "✓ Created scripts/.python-version"

Step 7: Update .gitignore for Pipenv
bash# Add to root .gitignore if not exists
cat >> .gitignore << 'EOF'

# Pipenv
.venv/
*.egg-info/
dist/
build/
.eggs/

# Don't commit Pipfile.lock if you want flexibility
# (Comment out if you want reproducible builds)
# Pipfile.lock
EOF

echo "✓ Updated .gitignore"
```

---

## Final Repository Structure
```
Data-pipeline-aws/
│
├── .gitignore                       ← Updated with Pipenv entries
├── serverless-app-template.yml
├── buildspec.yml
├── dev.json
│
├── lambda/
│   └── api/
│       └── app.py
│
├── glue/
│   ├── csv_processor.py
│   └── sample_data.csv
│
├── scripts/
│   ├── __init__.py
│   ├── invoke_step_function.py
│   ├── check_status.py
│   ├── upload_and_run.py
│   ├── Pipfile                      ← Dependencies + scripts
│   ├── Pipfile.lock                 ← Locked versions
│   └── .python-version              ← Python version specification
│
└── cloudformation/
    └── pipeline.yaml
```

---

## Quick Reference: Pipenv vs pip
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PIPENV COMMANDS                      EQUIVALENT PIP COMMANDS              │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  pipenv install                       pip install -r requirements.txt      │
│  pipenv install boto3                 pip install boto3                    │
│  pipenv install --dev pytest          pip install pytest (dev only)        │
│  pipenv uninstall boto3               pip uninstall boto3                  │
│  pipenv update                        pip install --upgrade -r req.txt     │
│  pipenv shell                         source venv/bin/activate             │
│  pipenv run python script.py          python script.py (in venv)           │
│  pipenv lock                          pip freeze > requirements.txt        │
│  pipenv requirements                  cat requirements.txt                 │
│  pipenv check                         pip-audit (separate tool)            │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BENEFITS OF PIPENV:                                                        │
│  ✓ Automatic virtual environment management                                │
│  ✓ Separates dev and production dependencies                              │
│  ✓ Lock file for reproducible builds                                      │
│  ✓ Security vulnerability checking                                        │
│  ✓ Custom scripts in Pipfile                                              │
│  ✓ Python version specification                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Commit Changes
bashcd ~/Data-pipeline-aws

# Remove old requirements.txt
rm -f scripts/requirements.txt

# Add new files
git add scripts/Pipfile
git add scripts/.python-version
git add .gitignore

# Commit
git commit -m "Replace requirements.txt with Pipfile (pipenv)"

# Push
git push origin main

echo "✓ Changes committed and pushed!"
```

---

## Summary
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  CHANGES MADE:                                                              │
│                                                                             │
│  REMOVED:                                                                   │
│  • scripts/requirements.txt                                                │
│                                                                             │
│  ADDED:                                                                     │
│  • scripts/Pipfile           - Dependencies + dev deps + custom scripts   │
│  • scripts/Pipfile.lock      - Locked dependency versions                 │
│  • scripts/.python-version   - Python version specification               │
│                                                                             │
│  USAGE:                                                                     │
│  • pipenv install            - Install all dependencies                   │
│  • pipenv run generate       - Generate Step Function definitions         │
│  • pipenv run list           - List available step functions              │
│  • pipenv run check          - Check execution status                     │
│  • pipenv run lint           - Run linter                                 │
│  • pipenv run format         - Format code                                │
│  • pipenv run test           - Run tests                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘create the pipfile on the root directory4:08 PMMove Pipfile to Root Directory
bashcd ~/Data-pipeline-aws

# Remove Pipfile from scripts folder if exists
rm -f scripts/Pipfile
rm -f scripts/Pipfile.lock
rm -f scripts/.python-version
rm -f scripts/requirements.txt

# Create Pipfile in root directory
cat > Pipfile << 'EOF'
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
# AWS SDK
boto3 = ">=1.28.0"
botocore = ">=1.31.0"

# Data Processing
pandas = ">=2.0.0"

# Configuration
pyyaml = ">=6.0"

[dev-packages]
# Testing
pytest = ">=7.0.0"
pytest-cov = ">=4.0.0"
pytest-mock = ">=3.10.0"
moto = ">=4.0.0"

# Code Quality
black = ">=23.0.0"
flake8 = ">=6.0.0"
isort = ">=5.12.0"
mypy = ">=1.0.0"

# Type Stubs
boto3-stubs = {extras = ["stepfunctions", "s3", "glue", "sts", "cloudformation", "sns"], version = ">=1.28.0"}
pandas-stubs = ">=2.0.0"

[requires]
python_version = "3.9"

[scripts]
# Step Function Management
generate = "python scripts/invoke_step_function.py --generate"
list = "python scripts/invoke_step_function.py --list"
invoke = "python scripts/invoke_step_function.py --invoke"
check = "python scripts/check_status.py --list"
upload = "python scripts/upload_and_run.py"

# Code Quality
lint = "flake8 scripts/ lambda/ glue/"
format = "black scripts/ lambda/ glue/"
sort = "isort scripts/ lambda/ glue/"
typecheck = "mypy scripts/"

# Testing
test = "pytest tests/"
test-cov = "pytest tests/ --cov=scripts --cov-report=html"

# All checks
check-all = "bash -c 'black scripts/ lambda/ glue/ && isort scripts/ lambda/ glue/ && flake8 scripts/ lambda/ glue/'"
EOF

echo "✓ Created Pipfile in root directory"

Create .python-version in Root
bashcat > .python-version << 'EOF'
3.9
EOF

echo "✓ Created .python-version"

Update .gitignore
bashcat > .gitignore << 'EOF'
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual environments
.venv/
venv/
ENV/
env/

# Pipenv
*.egg-info/
dist/
build/
.eggs/

# IDE
.idea/
.vscode/
*.swp
*.swo

# AWS SAM
.aws-sam/
samconfig.toml

# Testing
.pytest_cache/
htmlcov/
.coverage
coverage.xml

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Local env files
.env
.env.local

# Temporary files
*.tmp
*.temp
EOF

echo "✓ Created .gitignore"
```

---

## Updated Repository Structure
```
Data-pipeline-aws/
│
├── Pipfile                          ← Dependencies (ROOT)
├── Pipfile.lock                     ← Locked versions (generated by pipenv)
├── .python-version                  ← Python version
├── .gitignore                       ← Git ignore rules
│
├── serverless-app-template.yml      ← Main SAM template
├── buildspec.yml                    ← CodeBuild instructions
├── dev.json                         ← Environment config
│
├── lambda/
│   └── api/
│       └── app.py                   ← API Lambda handler
│
├── glue/
│   ├── csv_processor.py             ← Glue PySpark script
│   └── sample_data.csv              ← Sample test data
│
├── scripts/
│   ├── __init__.py
│   ├── invoke_step_function.py      ← Step Function manager
│   ├── check_status.py              ← Status checker
│   └── upload_and_run.py            ← Upload + run helper
│
├── tests/                           ← Test files (optional)
│   └── __init__.py
│
└── cloudformation/
    └── pipeline.yaml                ← CI/CD Pipeline

Create Tests Directory (Optional)
bashmkdir -p tests

cat > tests/__init__.py << 'EOF'
"""Tests for Step Function scripts."""
EOF

cat > tests/test_invoke_step_function.py << 'EOF'
"""Tests for invoke_step_function.py"""

import pytest
from unittest.mock import MagicMock, patch


class TestStepFunctionManager:
    """Test cases for StepFunctionManager class."""

    def test_placeholder(self):
        """Placeholder test."""
        assert True
EOF

echo "✓ Created tests directory"

Usage Commands
bash# ═══════════════════════════════════════════════════════════════════════════
# SETUP (Run from root directory)
# ═══════════════════════════════════════════════════════════════════════════

cd ~/Data-pipeline-aws

# Install pipenv if not installed
pip install pipenv

# Install all dependencies
pipenv install

# Install with dev dependencies
pipenv install --dev

# ═══════════════════════════════════════════════════════════════════════════
# RUNNING SCRIPTS (Using Pipfile scripts)
# ═══════════════════════════════════════════════════════════════════════════

# Generate Step Function definitions from CSV
pipenv run generate

# List available step functions
pipenv run list

# Check execution status
pipenv run check

# Upload data and run
pipenv run upload data.csv

# ═══════════════════════════════════════════════════════════════════════════
# RUNNING SCRIPTS (Direct commands)
# ═══════════════════════════════════════════════════════════════════════════

# Using pipenv run
pipenv run python scripts/invoke_step_function.py --generate
pipenv run python scripts/invoke_step_function.py --list
pipenv run python scripts/invoke_step_function.py --invoke JOB_NAME --role-arn ARN

# Or activate shell first
pipenv shell
python scripts/invoke_step_function.py --generate
python scripts/invoke_step_function.py --list
exit

# ═══════════════════════════════════════════════════════════════════════════
# CODE QUALITY
# ═══════════════════════════════════════════════════════════════════════════

# Format code
pipenv run format

# Lint code
pipenv run lint

# Sort imports
pipenv run sort

# Type checking
pipenv run typecheck

# Run all checks
pipenv run check-all

# ═══════════════════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════════════════

# Run tests
pipenv run test

# Run tests with coverage
pipenv run test-cov

# ═══════════════════════════════════════════════════════════════════════════
# DEPENDENCY MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

# Add new package
pipenv install package-name

# Add dev package
pipenv install --dev package-name

# Update all packages
pipenv update

# Check for vulnerabilities
pipenv check

# Generate requirements.txt (if needed)
pipenv requirements > requirements.txt
pipenv requirements --dev > requirements-dev.txt

Verify Structure
bashecho "=== Repository Structure ==="
find . -type f \( -name "*.py" -o -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.csv" -o -name "Pipfile*" -o -name ".python-version" -o -name ".gitignore" \) | grep -v __pycache__ | grep -v ".git/" | sort
```

**Expected Output:**
```
./.gitignore
./.python-version
./Pipfile
./buildspec.yml
./cloudformation/pipeline.yaml
./dev.json
./glue/csv_processor.py
./glue/sample_data.csv
./lambda/api/app.py
./scripts/__init__.py
./scripts/check_status.py
./scripts/invoke_step_function.py
./scripts/upload_and_run.py
./serverless-app-template.yml
./tests/__init__.py
./tests/test_invoke_step_function.py

Commit Changes
bashcd ~/Data-pipeline-aws

git add .
git commit -m "Move Pipfile to root directory, add tests structure"
git push origin main

echo "✓ Changes committed and pushed!"
```

---

## Summary
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  REPOSITORY STRUCTURE                                                       │
│                                                                             │
│  Data-pipeline-aws/                                                         │
│  │                                                                          │
│  ├── Pipfile                 ← Dependencies (ROOT LEVEL)                   │
│  ├── .python-version         ← Python 3.9                                  │
│  ├── .gitignore              ← Git ignore rules                            │
│  │                                                                          │
│  ├── serverless-app-template.yml                                           │
│  ├── buildspec.yml                                                         │
│  ├── dev.json                                                              │
│  │                                                                          │
│  ├── lambda/api/app.py                                                     │
│  ├── glue/csv_processor.py                                                 │
│  ├── glue/sample_data.csv                                                  │
│  │                                                                          │
│  ├── scripts/                                                              │
│  │   ├── invoke_step_function.py                                          │
│  │   ├── check_status.py                                                  │
│  │   └── upload_and_run.py                                                │
│  │                                                                          │
│  ├── tests/                                                                │
│  │   └── test_invoke_step_function.py                                     │
│  │                                                                          │
│  └── cloudformation/pipeline.yaml                                          │
│                                                                             │
│  PIPENV COMMANDS (from root):                                              │
│  • pipenv install           - Install dependencies                        │
│  • pipenv run generate      - Generate Step Function definitions          │
│  • pipenv run list          - List step functions                         │
│  • pipenv run check         - Check execution status                      │
│  • pipenv run format        - Format code with black                      │
│  • pipenv run lint          - Lint code with flake8                       │
│  • pipenv run test          - Run tests                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘now show all the files contents and commands to execute the pipeline4:11 PMComplete Project Files and Execution Commands
Repository Structure
Data-pipeline-aws/
│
├── Pipfile                          ← Python dependencies
├── .python-version                  ← Python version
├── .gitignore                       ← Git ignore rules
│
├── serverless-app-template.yml      ← Main SAM template
├── buildspec.yml                    ← CodeBuild instructions
├── dev.json                         ← Environment config
│
├── lambda/
│   └── api/
│       └── app.py                   ← API Lambda handler
│
├── glue/
│   ├── csv_processor.py             ← Glue PySpark script
│   └── sample_data.csv              ← Sample test data
│
├── scripts/
│   ├── __init__.py
│   ├── invoke_step_function.py      ← Step Function manager
│   ├── check_status.py              ← Status checker
│   └── upload_and_run.py            ← Upload + run helper
│
├── tests/
│   ├── __init__.py
│   └── test_invoke_step_function.py
│
└── cloudformation/
    └── pipeline.yaml                ← CI/CD Pipeline

File 1: Pipfile
bashcat > Pipfile << 'EOF'
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
boto3 = ">=1.28.0"
botocore = ">=1.31.0"
pandas = ">=2.0.0"
pyyaml = ">=6.0"

[dev-packages]
pytest = ">=7.0.0"
pytest-cov = ">=4.0.0"
pytest-mock = ">=3.10.0"
moto = ">=4.0.0"
black = ">=23.0.0"
flake8 = ">=6.0.0"
isort = ">=5.12.0"
mypy = ">=1.0.0"
boto3-stubs = {extras = ["stepfunctions", "s3", "glue", "sts", "cloudformation", "sns"], version = ">=1.28.0"}
pandas-stubs = ">=2.0.0"

[requires]
python_version = "3.9"

[scripts]
generate = "python scripts/invoke_step_function.py --generate"
list = "python scripts/invoke_step_function.py --list"
invoke = "python scripts/invoke_step_function.py --invoke"
check = "python scripts/check_status.py --list"
upload = "python scripts/upload_and_run.py"
lint = "flake8 scripts/ lambda/ glue/"
format = "black scripts/ lambda/ glue/"
sort = "isort scripts/ lambda/ glue/"
typecheck = "mypy scripts/"
test = "pytest tests/"
test-cov = "pytest tests/ --cov=scripts --cov-report=html"
check-all = "bash -c 'black scripts/ lambda/ glue/ && isort scripts/ lambda/ glue/ && flake8 scripts/ lambda/ glue/'"
EOF

File 2: .python-version
bashcat > .python-version << 'EOF'
3.9
EOF

File 3: .gitignore
bashcat > .gitignore << 'EOF'
# Byte-compiled
__pycache__/
*.py[cod]
*$py.class

# Virtual environments
.venv/
venv/
ENV/

# Pipenv
*.egg-info/
dist/
build/
.eggs/

# IDE
.idea/
.vscode/
*.swp

# AWS SAM
.aws-sam/
samconfig.toml

# Testing
.pytest_cache/
htmlcov/
.coverage

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Local env
.env
.env.local
EOF

File 4: serverless-app-template.yml
bashcat > serverless-app-template.yml << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Serverless API with Glue Job and Step Functions

Parameters:
  EnvironmentName:
    Type: String
    Default: dev
  ApplicationName:
    Type: String
    Default: serverless-app
  LogRetentionDays:
    Type: Number
    Default: 14

Globals:
  Function:
    Timeout: 30
    MemorySize: 256
    Runtime: python3.9

Resources:
  # ==========================================================================
  # SECRETS MANAGER
  # ==========================================================================
  ApplicationSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: !Sub ${ApplicationName}/${EnvironmentName}/app-secret
      GenerateSecretString:
        SecretStringTemplate: !Sub '{"app_name": "${ApplicationName}", "environment": "${EnvironmentName}"}'
        GenerateStringKey: api_key
        PasswordLength: 32
        ExcludePunctuation: true

  # ==========================================================================
  # API LAMBDA
  # ==========================================================================
  ApiLambdaRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub ${ApplicationName}-api-lambda-role-${EnvironmentName}
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: LambdaPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - logs:CreateLogGroup
                  - logs:CreateLogStream
                  - logs:PutLogEvents
                Resource: '*'
              - Effect: Allow
                Action:
                  - secretsmanager:GetSecretValue
                Resource: !Ref ApplicationSecret

  HealthCheckFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub ${ApplicationName}-${EnvironmentName}-health
      Handler: app.lambda_handler
      CodeUri: lambda/api/
      Role: !GetAtt ApiLambdaRole.Arn
      Environment:
        Variables:
          SECRET_ARN: !Ref ApplicationSecret
          ENVIRONMENT: !Ref EnvironmentName
          APPLICATION_NAME: !Ref ApplicationName
      Events:
        HealthGet:
          Type: Api
          Properties:
            RestApiId: !Ref ApiGateway
            Path: /health
            Method: GET
        HealthPost:
          Type: Api
          Properties:
            RestApiId: !Ref ApiGateway
            Path: /health
            Method: POST

  HealthCheckLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub /aws/lambda/${HealthCheckFunction}
      RetentionInDays: !Ref LogRetentionDays

  ApiGateway:
    Type: AWS::Serverless::Api
    Properties:
      Name: !Sub ${ApplicationName}-api-${EnvironmentName}
      StageName: !Ref EnvironmentName

  # ==========================================================================
  # GLUE DATA BUCKET
  # ==========================================================================
  GlueDataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub ${ApplicationName}-glue-data-${AWS::AccountId}-${AWS::Region}
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256

  # ==========================================================================
  # GLUE JOB
  # ==========================================================================
  GlueJobRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub ${ApplicationName}-glue-role-${EnvironmentName}
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: glue.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole
      Policies:
        - PolicyName: S3Access
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                  - s3:DeleteObject
                  - s3:ListBucket
                Resource:
                  - !GetAtt GlueDataBucket.Arn
                  - !Sub ${GlueDataBucket.Arn}/*

  CsvProcessorGlueJob:
    Type: AWS::Glue::Job
    Properties:
      Name: !Sub ${ApplicationName}-csv-processor-${EnvironmentName}
      Description: Glue job to process CSV files
      Role: !GetAtt GlueJobRole.Arn
      GlueVersion: '4.0'
      WorkerType: G.1X
      NumberOfWorkers: 2
      Timeout: 60
      Command:
        Name: glueetl
        ScriptLocation: !Sub s3://${GlueDataBucket}/scripts/csv_processor.py
        PythonVersion: '3'
      DefaultArguments:
        '--job-language': python
        '--job-bookmark-option': job-bookmark-enable
        '--enable-metrics': 'true'
        '--enable-continuous-cloudwatch-log': 'true'
        '--INPUT_PATH': !Sub s3://${GlueDataBucket}/input/
        '--OUTPUT_PATH': !Sub s3://${GlueDataBucket}/output/

  # ==========================================================================
  # STEP FUNCTIONS
  # ==========================================================================
  StepFunctionsRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub ${ApplicationName}-stepfn-role-${EnvironmentName}
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: states.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: GlueAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - glue:StartJobRun
                  - glue:GetJobRun
                  - glue:GetJobRuns
                  - glue:BatchStopJobRun
                Resource:
                  - !Sub arn:aws:glue:${AWS::Region}:${AWS::AccountId}:job/${ApplicationName}-csv-processor-${EnvironmentName}
        - PolicyName: CloudWatchLogs
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - logs:CreateLogDelivery
                  - logs:GetLogDelivery
                  - logs:UpdateLogDelivery
                  - logs:DeleteLogDelivery
                  - logs:ListLogDeliveries
                  - logs:PutResourcePolicy
                  - logs:DescribeResourcePolicies
                  - logs:DescribeLogGroups
                Resource: '*'

  StepFunctionsLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub /aws/stepfunctions/${ApplicationName}-glue-orchestrator-${EnvironmentName}
      RetentionInDays: !Ref LogRetentionDays

  GlueOrchestratorStateMachine:
    Type: AWS::StepFunctions::StateMachine
    Properties:
      StateMachineName: !Sub ${ApplicationName}-glue-orchestrator-${EnvironmentName}
      RoleArn: !GetAtt StepFunctionsRole.Arn
      LoggingConfiguration:
        Level: ALL
        IncludeExecutionData: true
        Destinations:
          - CloudWatchLogsLogGroup:
              LogGroupArn: !GetAtt StepFunctionsLogGroup.Arn
      DefinitionString: !Sub |
        {
          "Comment": "Orchestrate Glue Job",
          "StartAt": "StartGlueJob",
          "States": {
            "StartGlueJob": {
              "Type": "Task",
              "Resource": "arn:aws:states:::glue:startJobRun.sync",
              "Parameters": {
                "JobName": "${ApplicationName}-csv-processor-${EnvironmentName}",
                "Arguments": {
                  "--INPUT_PATH.$": "$.inputPath",
                  "--OUTPUT_PATH.$": "$.outputPath"
                }
              },
              "ResultPath": "$.glueResult",
              "Next": "JobSucceeded",
              "Catch": [
                {
                  "ErrorEquals": ["States.ALL"],
                  "ResultPath": "$.error",
                  "Next": "JobFailed"
                }
              ],
              "Retry": [
                {
                  "ErrorEquals": ["Glue.AWSGlueException"],
                  "IntervalSeconds": 60,
                  "MaxAttempts": 2,
                  "BackoffRate": 2.0
                }
              ]
            },
            "JobSucceeded": {
              "Type": "Pass",
              "Parameters": {
                "status": "SUCCEEDED",
                "message": "Glue job completed successfully",
                "jobRunId.$": "$.glueResult.JobRunId"
              },
              "End": true
            },
            "JobFailed": {
              "Type": "Fail",
              "Error": "GlueJobFailed",
              "Cause": "Glue job execution failed"
            }
          }
        }

# ==========================================================================
# OUTPUTS
# ==========================================================================
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
EOF

File 5: buildspec.yml
bashcat > buildspec.yml << 'EOF'
version: 0.2

phases:
  install:
    runtime-versions:
      python: 3.9
    commands:
      - echo "Installing dependencies..."
      - pip install --upgrade pip
      - pip install aws-sam-cli
      - sam --version

  pre_build:
    commands:
      - echo "=== Pre-build phase ==="
      - echo "ENVIRONMENT_NAME=${ENVIRONMENT_NAME}"
      - echo "APPLICATION_NAME=${APPLICATION_NAME}"
      - echo "ARTIFACT_BUCKET=${ARTIFACT_BUCKET}"
      - echo "Validating SAM template..."
      - sam validate --template serverless-app-template.yml --lint

  build:
    commands:
      - echo "=== Build phase ==="
      - echo "Packaging SAM application..."
      - sam package --template-file serverless-app-template.yml --output-template-file packaged-template.yaml --s3-bucket ${ARTIFACT_BUCKET} --s3-prefix sam-artifacts/${APPLICATION_NAME}/${ENVIRONMENT_NAME}
      
      - echo "Creating config.json..."
      - |
        cat > config.json << CONFIGEOF
        {
          "Parameters": {
            "EnvironmentName": "${ENVIRONMENT_NAME}",
            "ApplicationName": "${APPLICATION_NAME}",
            "LogRetentionDays": "14"
          },
          "Tags": {
            "Environment": "${ENVIRONMENT_NAME}",
            "Application": "${APPLICATION_NAME}",
            "ManagedBy": "CloudFormation"
          }
        }
        CONFIGEOF
      - cat config.json

  post_build:
    commands:
      - echo "=== Post-build phase ==="
      - echo "Uploading Glue script..."
      - |
        GLUE_BUCKET="${APPLICATION_NAME}-glue-data-$(aws sts get-caller-identity --query Account --output text)-${AWS_REGION}"
        if [ -f "glue/csv_processor.py" ]; then
          aws s3 cp glue/csv_processor.py s3://${GLUE_BUCKET}/scripts/csv_processor.py --region ${AWS_REGION} || echo "Bucket may not exist yet"
        fi
        if [ -f "glue/sample_data.csv" ]; then
          aws s3 cp glue/sample_data.csv s3://${GLUE_BUCKET}/input/sample_data.csv --region ${AWS_REGION} || echo "Bucket may not exist yet"
        fi
      - echo "Build completed!"

artifacts:
  files:
    - packaged-template.yaml
    - config.json
  discard-paths: yes
EOF

File 6: dev.json
bashcat > dev.json << 'EOF'
{
  "Parameters": {
    "EnvironmentName": "dev",
    "ApplicationName": "serverless-app",
    "LogRetentionDays": "14"
  },
  "Tags": {
    "Environment": "dev",
    "Application": "serverless-app",
    "ManagedBy": "CloudFormation"
  }
}
EOF

File 7: lambda/api/app.py
bashmkdir -p lambda/api

cat > lambda/api/app.py << 'EOF'
"""
API Lambda Handler
Health check endpoint for the serverless application.
"""

import json
import logging
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

secrets_client = boto3.client("secretsmanager")

SECRET_ARN = os.environ.get("SECRET_ARN", "")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "unknown")
APPLICATION_NAME = os.environ.get("APPLICATION_NAME", "unknown")


def get_secret():
    """Retrieve secret from Secrets Manager."""
    try:
        if not SECRET_ARN:
            return {}
        response = secrets_client.get_secret_value(SecretId=SECRET_ARN)
        return json.loads(response.get("SecretString", "{}"))
    except ClientError as e:
        logger.error(f"Failed to get secret: {e}")
        return {}


def create_response(status_code, body):
    """Create API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }


def lambda_handler(event, context):
    """Main Lambda handler."""
    logger.info(f"Event: {json.dumps(event)}")

    path = event.get("path", "/")
    http_method = event.get("httpMethod", "GET")

    try:
        secret_data = get_secret()

        if path == "/health":
            return create_response(200, {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environment": ENVIRONMENT,
                "application": APPLICATION_NAME,
                "secret_loaded": bool(secret_data),
            })
        else:
            return create_response(200, {
                "status": "success",
                "path": path,
                "method": http_method,
            })

    except Exception as e:
        logger.exception(f"Error: {e}")
        return create_response(500, {
            "status": "error",
            "message": str(e),
        })
EOF

File 8: glue/csv_processor.py
bashmkdir -p glue

cat > glue/csv_processor.py << 'EOF'
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
    sys.exit(0)

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
EOF

File 9: glue/sample_data.csv
bashcat > glue/sample_data.csv << 'EOF'
id,name,email,age,department,salary,hire_date
1,John Smith,john.smith@example.com,35,Engineering,85000,2020-01-15
2,Jane Doe,jane.doe@example.com,28,Marketing,65000,2021-03-22
3,Bob Johnson,bob.johnson@example.com,42,Finance,95000,2018-07-10
4,Alice Brown,alice.brown@example.com,31,Engineering,78000,2019-11-05
5,Charlie Wilson,charlie.wilson@example.com,45,HR,72000,2017-04-18
6,Diana Miller,diana.miller@example.com,29,Marketing,68000,2022-01-30
7,Edward Davis,edward.davis@example.com,38,Engineering,92000,2016-09-12
8,Fiona Garcia,fiona.garcia@example.com,33,Finance,88000,2019-06-25
9,George Martinez,george.martinez@example.com,41,HR,75000,2018-02-14
10,Helen Rodriguez,helen.rodriguez@example.com,27,Engineering,70000,2023-05-08
EOF

File 10: scripts/init.py
bashmkdir -p scripts

cat > scripts/__init__.py << 'EOF'
"""Scripts for Step Functions management and Glue job orchestration."""
EOF

File 11: scripts/invoke_step_function.py
bashcat > scripts/invoke_step_function.py << 'EOF'
#!/usr/bin/env python3
"""
Step Function Generator and Invoker

This script:
1. Reads CSV files from S3 containing job configurations
2. Generates Step Function definitions with Glue job invocation
3. Includes SNS failure notifications
4. Uploads individual JSON definitions and combined YAML to S3
5. Can invoke Step Functions executions

Usage:
    python scripts/invoke_step_function.py --generate
    python scripts/invoke_step_function.py --list
    python scripts/invoke_step_function.py --invoke JOB_NAME --role-arn ARN
"""

import boto3
import pandas as pd
import json
import yaml
import argparse
import time
from datetime import datetime
from typing import Dict, List, Any, Optional


class StepFunctionManager:
    """Manage Step Functions - generate definitions and invoke executions."""

    def __init__(
        self,
        region: str = "us-east-1",
        bucket_name: str = "dev-batuu-mh-apps",
        input_prefix: str = "snaplogic-migration/task_output/",
        output_prefix: str = "snaplogic-migration/stepfunction_scripts/",
        sns_topic_arn: str = "arn:aws:sns:us-east-1:533267066040:glue-job-failure-notify"
    ):
        """Initialize with configuration."""
        self.region = region
        self.bucket_name = bucket_name
        self.input_prefix = input_prefix
        self.output_prefix = output_prefix
        self.sns_topic_arn = sns_topic_arn
        self.yaml_key = f"{output_prefix}all_stepfunctions.yaml"

        # Initialize AWS clients
        self.s3 = boto3.client("s3", region_name=region)
        self.sfn = boto3.client("stepfunctions", region_name=region)
        self.sts = boto3.client("sts", region_name=region)
        self.account_id = self.sts.get_caller_identity()["Account"]

    def list_csv_files(self) -> List[str]:
        """List all CSV files in the input prefix."""
        response = self.s3.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=self.input_prefix
        )
        csv_files = [
            obj["Key"]
            for obj in response.get("Contents", [])
            if obj["Key"].endswith(".csv")
        ]
        return csv_files

    def load_existing_yaml(self) -> List[Dict]:
        """Load existing YAML definitions if present."""
        try:
            yaml_obj = self.s3.get_object(
                Bucket=self.bucket_name,
                Key=self.yaml_key
            )
            existing_yaml = yaml_obj["Body"].read().decode("utf-8")
            existing_definitions = yaml.safe_load(existing_yaml) or []
            print(f"✅ Loaded existing YAML with {len(existing_definitions)} definitions")
            return existing_definitions
        except self.s3.exceptions.NoSuchKey:
            print("ℹ️  No existing YAML found. Starting fresh.")
            return []
        except Exception as e:
            print(f"⚠️  Error loading YAML: {e}")
            return []

    def read_csv_from_s3(self, csv_key: str) -> pd.DataFrame:
        """Read CSV file from S3."""
        response = self.s3.get_object(Bucket=self.bucket_name, Key=csv_key)
        df = pd.read_csv(response["Body"])
        return df

    def build_step_function_definition(
        self,
        job_name: str,
        glue_job_name: str,
        glue_arguments: Dict[str, str]
    ) -> Dict[str, Any]:
        """Build Step Function definition with Glue job invocation."""
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
                        "Next": "CheckGlueJobStatus",
                        "Catch": [
                            {
                                "ErrorEquals": ["States.ALL"],
                                "ResultPath": "$.error",
                                "Next": "NotifyFailure"
                            }
                        ],
                        "Retry": [
                            {
                                "ErrorEquals": ["Glue.AWSGlueException"],
                                "IntervalSeconds": 60,
                                "MaxAttempts": 2,
                                "BackoffRate": 2.0
                            }
                        ]
                    },
                    "CheckGlueJobStatus": {
                        "Type": "Choice",
                        "Choices": [
                            {
                                "Variable": "$.JobRunState",
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
                            "TopicArn": self.sns_topic_arn,
                            "Message.$": "States.Format('Glue job {} failed.', $.JobName)",
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
        return definition

    def generate_definitions_from_csv(self) -> List[Dict]:
        """Generate Step Function definitions from CSV files."""
        csv_files = self.list_csv_files()
        print(f"📄 Found {len(csv_files)} CSV files")

        new_definitions = []

        for csv_key in csv_files:
            print(f"\n📖 Processing: {csv_key}")
            df = self.read_csv_from_s3(csv_key)

            if "Job name" not in df.columns:
                print(f"  ⚠️  No 'Job name' column found, skipping...")
                continue

            jobs = df.groupby("Job name")

            for job_name, group in jobs:
                pipeline_parameters = {}
                pipeline_name = None

                for _, row in group.iterrows():
                    param_name = row.get("Parameter name", "")
                    subparam_name = row.get("Subparameter name", "")
                    value = row.get("Value", "")
                    value = "" if pd.isna(value) else str(value)

                    if param_name == "pipeline_parameters" and pd.notna(subparam_name):
                        pipeline_parameters[subparam_name] = value

                    if "Pipeline name" in row and pd.notna(row["Pipeline name"]):
                        pipeline_name = row["Pipeline name"]

                glue_job_name = pipeline_name if pipeline_name else "DefaultGlueJob"
                glue_arguments = {f"--{k}": v for k, v in pipeline_parameters.items()}

                definition = self.build_step_function_definition(
                    job_name=job_name,
                    glue_job_name=glue_job_name,
                    glue_arguments=glue_arguments
                )

                output_key = f"{self.output_prefix}{job_name}.json"
                self.s3.put_object(
                    Bucket=self.bucket_name,
                    Key=output_key,
                    Body=json.dumps(definition["definition"], indent=2)
                )
                print(f"  ✅ Created: {job_name}.json")

                new_definitions.append(definition)

        return new_definitions

    def update_yaml_file(self, new_definitions: List[Dict]) -> str:
        """Merge new definitions with existing YAML and upload."""
        existing_definitions = self.load_existing_yaml()
        existing_by_name = {d["name"]: d for d in existing_definitions}

        for new_def in new_definitions:
            existing_by_name[new_def["name"]] = new_def

        all_definitions = list(existing_by_name.values())
        yaml_content = yaml.dump(all_definitions, sort_keys=False, default_flow_style=False)

        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=self.yaml_key,
            Body=yaml_content
        )

        yaml_path = f"s3://{self.bucket_name}/{self.yaml_key}"
        print(f"\n✅ Updated YAML with {len(all_definitions)} total definitions at {yaml_path}")
        return yaml_path

    def list_step_functions(self) -> List[Dict]:
        """List all step functions from YAML."""
        definitions = self.load_existing_yaml()
        return [
            {
                "name": d["name"],
                "glue_job": d["definition"]["States"]["InvokeGlueJob"]["Parameters"]["JobName"]
            }
            for d in definitions
        ]

    def get_definition_by_name(self, job_name: str) -> Optional[Dict]:
        """Get step function definition by name."""
        definitions = self.load_existing_yaml()
        for d in definitions:
            if d["name"] == job_name:
                return d
        return None

    def create_state_machine(self, job_name: str, role_arn: str) -> str:
        """Create or update Step Functions state machine in AWS."""
        definition = self.get_definition_by_name(job_name)
        if not definition:
            raise ValueError(f"No definition found for job: {job_name}")

        state_machine_name = f"sfn-{job_name}"
        definition_str = json.dumps(definition["definition"])

        try:
            response = self.sfn.create_state_machine(
                name=state_machine_name,
                definition=definition_str,
                roleArn=role_arn,
                type="STANDARD"
            )
            print(f"✅ Created state machine: {state_machine_name}")
            return response["stateMachineArn"]

        except self.sfn.exceptions.StateMachineAlreadyExists:
            state_machine_arn = f"arn:aws:states:{self.region}:{self.account_id}:stateMachine:{state_machine_name}"
            self.sfn.update_state_machine(
                stateMachineArn=state_machine_arn,
                definition=definition_str,
                roleArn=role_arn
            )
            print(f"✅ Updated state machine: {state_machine_name}")
            return state_machine_arn

    def invoke_step_function(
        self,
        state_machine_arn: str,
        input_data: Optional[Dict] = None,
        execution_name: Optional[str] = None
    ) -> str:
        """Start Step Functions execution."""
        if execution_name is None:
            execution_name = f"exec-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        if input_data is None:
            input_data = {}

        response = self.sfn.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=json.dumps(input_data)
        )

        print(f"✅ Started execution: {execution_name}")
        print(f"   ARN: {response['executionArn']}")
        return response["executionArn"]

    def get_execution_status(self, execution_arn: str) -> Dict[str, Any]:
        """Get execution status."""
        response = self.sfn.describe_execution(executionArn=execution_arn)

        result = {
            "executionArn": execution_arn,
            "status": response["status"],
            "startDate": response.get("startDate"),
            "stopDate": response.get("stopDate"),
        }

        if response.get("output"):
            result["output"] = json.loads(response["output"])
        if response.get("error"):
            result["error"] = response["error"]
            result["cause"] = response.get("cause")

        return result

    def wait_for_completion(
        self,
        execution_arn: str,
        poll_interval: int = 30,
        timeout: int = 3600
    ) -> Dict[str, Any]:
        """Wait for execution to complete."""
        start_time = time.time()

        while True:
            status = self.get_execution_status(execution_arn)
            current_status = status["status"]
            print(f"  Status: {current_status}")

            if current_status in ["SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]:
                return status

            if time.time() - start_time > timeout:
                raise TimeoutError(f"Execution did not complete within {timeout} seconds")

            time.sleep(poll_interval)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Step Function Generator and Invoker")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--bucket", default="dev-batuu-mh-apps", help="S3 bucket")
    parser.add_argument("--input-prefix", default="snaplogic-migration/task_output/", help="Input prefix")
    parser.add_argument("--output-prefix", default="snaplogic-migration/stepfunction_scripts/", help="Output prefix")
    parser.add_argument("--sns-topic", default="arn:aws:sns:us-east-1:533267066040:glue-job-failure-notify", help="SNS topic")
    parser.add_argument("--generate", action="store_true", help="Generate definitions from CSV")
    parser.add_argument("--list", action="store_true", help="List step functions")
    parser.add_argument("--invoke", metavar="JOB_NAME", help="Invoke step function")
    parser.add_argument("--create-state-machine", metavar="JOB_NAME", help="Create state machine")
    parser.add_argument("--role-arn", help="IAM role ARN for Step Functions")
    parser.add_argument("--no-wait", action="store_true", help="Don't wait for completion")

    args = parser.parse_args()

    manager = StepFunctionManager(
        region=args.region,
        bucket_name=args.bucket,
        input_prefix=args.input_prefix,
        output_prefix=args.output_prefix,
        sns_topic_arn=args.sns_topic
    )

    print("=" * 60)
    print("STEP FUNCTION MANAGER")
    print("=" * 60)

    if args.generate:
        print("\n📝 Generating Step Function definitions...")
        new_definitions = manager.generate_definitions_from_csv()
        print(f"\n✅ Generated {len(new_definitions)} definitions")
        if new_definitions:
            manager.update_yaml_file(new_definitions)
        return 0

    if args.list:
        print("\n📋 Available Step Functions:")
        print("-" * 60)
        step_functions = manager.list_step_functions()
        if not step_functions:
            print("No step functions found.")
        else:
            for sf in step_functions:
                print(f"  • {sf['name']:<40} -> {sf['glue_job']}")
        return 0

    if args.create_state_machine:
        if not args.role_arn:
            print("❌ --role-arn required")
            return 1
        state_machine_arn = manager.create_state_machine(args.create_state_machine, args.role_arn)
        print(f"   ARN: {state_machine_arn}")
        return 0

    if args.invoke:
        if not args.role_arn:
            print("❌ --role-arn required")
            return 1

        state_machine_arn = manager.create_state_machine(args.invoke, args.role_arn)
        execution_arn = manager.invoke_step_function(state_machine_arn=state_machine_arn)

        if args.no_wait:
            return 0

        print("\n⏳ Waiting for completion...")
        result = manager.wait_for_completion(execution_arn)

        print("\n" + "=" * 60)
        print(f"RESULT: {result['status']}")
        print("=" * 60)
        return 0 if result["status"] == "SUCCEEDED" else 1

    print("\nNo action specified. Use --help for options.")
    return 0


if __name__ == "__main__":
    exit(main())
EOF

chmod +x scripts/invoke_step_function.py

File 12: scripts/check_status.py
bashcat > scripts/check_status.py << 'EOF'
#!/usr/bin/env python3
"""
Check Step Functions execution status.

Usage:
    python scripts/check_status.py --list
    python scripts/check_status.py <execution-arn>
"""

import boto3
import json
import argparse
from datetime import datetime


def get_stack_outputs(stack_name: str, region: str) -> dict:
    """Get CloudFormation stack outputs."""
    cfn = boto3.client("cloudformation", region_name=region)
    response = cfn.describe_stacks(StackName=stack_name)
    return {o["OutputKey"]: o["OutputValue"] for o in response["Stacks"][0].get("Outputs", [])}


def list_executions(state_machine_arn: str, region: str, max_results: int = 10):
    """List recent executions."""
    sfn = boto3.client("stepfunctions", region_name=region)
    response = sfn.list_executions(stateMachineArn=state_machine_arn, maxResults=max_results)

    print(f"\n{'Name':<45} {'Status':<12} {'Start Date'}")
    print("-" * 80)

    for e in response.get("executions", []):
        start_date = e["startDate"].strftime("%Y-%m-%d %H:%M:%S") if e.get("startDate") else "N/A"
        print(f"{e['name']:<45} {e['status']:<12} {start_date}")


def get_execution_details(execution_arn: str, region: str):
    """Get execution details."""
    sfn = boto3.client("stepfunctions", region_name=region)
    response = sfn.describe_execution(executionArn=execution_arn)

    result = {
        "executionArn": execution_arn,
        "status": response["status"],
        "startDate": str(response.get("startDate")),
        "stopDate": str(response.get("stopDate")),
    }

    if response.get("input"):
        result["input"] = json.loads(response["input"])
    if response.get("output"):
        result["output"] = json.loads(response["output"])
    if response.get("error"):
        result["error"] = response["error"]
        result["cause"] = response.get("cause")

    print(json.dumps(result, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="Check Step Functions status")
    parser.add_argument("execution_arn", nargs="?", help="Execution ARN")
    parser.add_argument("--region", default="us-east-2", help="AWS region")
    parser.add_argument("--stack-name", default="serverless-app-dev", help="Stack name")
    parser.add_argument("--list", action="store_true", help="List recent executions")

    args = parser.parse_args()

    if args.list or not args.execution_arn:
        try:
            outputs = get_stack_outputs(args.stack_name, args.region)
            state_machine_arn = outputs.get("StateMachineArn")
            if state_machine_arn:
                list_executions(state_machine_arn, args.region)
            else:
                print("State machine ARN not found in stack outputs")
        except Exception as e:
            print(f"Error: {e}")
        return 0

    get_execution_details(args.execution_arn, args.region)
    return 0


if __name__ == "__main__":
    exit(main())
EOF

chmod +x scripts/check_status.py

File 13: scripts/upload_and_run.py
bashcat > scripts/upload_and_run.py << 'EOF'
#!/usr/bin/env python3
"""
Upload CSV to S3 and run Step Functions workflow.

Usage:
    python scripts/upload_and_run.py data.csv
    python scripts/upload_and_run.py data.csv --no-wait
"""

import boto3
import json
import argparse
import os
import time
from datetime import datetime


def get_stack_outputs(stack_name: str, region: str) -> dict:
    """Get CloudFormation stack outputs."""
    cfn = boto3.client("cloudformation", region_name=region)
    response = cfn.describe_stacks(StackName=stack_name)
    return {o["OutputKey"]: o["OutputValue"] for o in response["Stacks"][0].get("Outputs", [])}


def upload_file(file_path: str, bucket: str, key: str, region: str):
    """Upload file to S3."""
    s3 = boto3.client("s3", region_name=region)
    s3.upload_file(file_path, bucket, key)
    print(f"✅ Uploaded {file_path} to s3://{bucket}/{key}")


def start_execution(state_machine_arn: str, input_path: str, output_path: str, region: str) -> str:
    """Start Step Functions execution."""
    sfn = boto3.client("stepfunctions", region_name=region)

    execution_name = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    response = sfn.start_execution(
        stateMachineArn=state_machine_arn,
        name=execution_name,
        input=json.dumps({"inputPath": input_path, "outputPath": output_path})
    )

    print(f"✅ Started execution: {execution_name}")
    return response["executionArn"]


def wait_for_completion(execution_arn: str, region: str, poll_interval: int = 30) -> dict:
    """Wait for execution to complete."""
    sfn = boto3.client("stepfunctions", region_name=region)

    while True:
        response = sfn.describe_execution(executionArn=execution_arn)
        status = response["status"]
        print(f"  Status: {status}")

        if status in ["SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]:
            return {"status": status, "output": response.get("output")}

        time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="Upload and run workflow")
    parser.add_argument("file", help="CSV file to upload")
    parser.add_argument("--region", default="us-east-2", help="AWS region")
    parser.add_argument("--stack-name", default="serverless-app-dev", help="Stack name")
    parser.add_argument("--no-wait", action="store_true", help="Don't wait")

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        return 1

    print("=" * 60)
    print("UPLOAD AND RUN WORKFLOW")
    print("=" * 60)

    # Get outputs
    outputs = get_stack_outputs(args.stack_name, args.region)
    bucket = outputs["GlueDataBucketName"]
    state_machine_arn = outputs["StateMachineArn"]
    input_path = outputs["GlueInputPath"]
    output_path = outputs["GlueOutputPath"]

    # Upload
    file_name = os.path.basename(args.file)
    upload_file(args.file, bucket, f"input/{file_name}", args.region)

    # Run
    execution_arn = start_execution(state_machine_arn, input_path, output_path, args.region)

    if args.no_wait:
        return 0

    # Wait
    print("\n⏳ Waiting for completion...")
    result = wait_for_completion(execution_arn, args.region)

    print(f"\n{'=' * 60}")
    print(f"RESULT: {result['status']}")
    print("=" * 60)

    return 0 if result["status"] == "SUCCEEDED" else 1


if __name__ == "__main__":
    exit(main())
EOF

chmod +x scripts/upload_and_run.py

File 14: tests/init.py
bashmkdir -p tests

cat > tests/__init__.py << 'EOF'
"""Tests for the data pipeline project."""
EOF

File 15: tests/test_invoke_step_function.py
bashcat > tests/test_invoke_step_function.py << 'EOF'
"""Tests for invoke_step_function.py"""

import pytest


class TestStepFunctionManager:
    """Test cases for StepFunctionManager."""

    def test_placeholder(self):
        """Placeholder test."""
        assert True

    def test_build_definition(self):
        """Test building step function definition."""
        # Add actual tests here
        pass
EOF

File 16: cloudformation/pipeline.yaml
bashmkdir -p cloudformation

cat > cloudformation/pipeline.yaml << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Description: CI/CD Pipeline for Serverless Application

Parameters:
  CodeConnectionArn:
    Type: String
    Description: ARN of the CodeConnections connection to GitHub

  GitHubOwner:
    Type: String
    Description: GitHub repository owner

  GitHubRepo:
    Type: String
    Default: Data-pipeline-aws

  GitHubBranch:
    Type: String
    Default: main

  ApplicationName:
    Type: String
    Default: serverless-app

  EnvironmentName:
    Type: String
    Default: dev

Resources:
  # ==========================================================================
  # S3 ARTIFACT BUCKET
  # ==========================================================================
  ArtifactBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub ${ApplicationName}-artifacts-${AWS::AccountId}-${AWS::Region}
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256

  # ==========================================================================
  # CODEBUILD ROLE
  # ==========================================================================
  CodeBuildRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub ${ApplicationName}-codebuild-role-${EnvironmentName}
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: codebuild.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: CodeBuildPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - logs:CreateLogGroup
                  - logs:CreateLogStream
                  - logs:PutLogEvents
                Resource: '*'
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:GetObjectVersion
                  - s3:PutObject
                Resource:
                  - !GetAtt ArtifactBucket.Arn
                  - !Sub ${ArtifactBucket.Arn}/*
              - Effect: Allow
                Action:
                  - s3:PutObject
                  - s3:GetObject
                  - s3:ListBucket
                Resource:
                  - !Sub arn:aws:s3:::${ApplicationName}-glue-data-${AWS::AccountId}-${AWS::Region}
                  - !Sub arn:aws:s3:::${ApplicationName}-glue-data-${AWS::AccountId}-${AWS::Region}/*
              - Effect: Allow
                Action:
                  - cloudformation:ValidateTemplate
                Resource: '*'
              - Effect: Allow
                Action:
                  - sts:GetCallerIdentity
                Resource: '*'
              - Effect: Allow
                Action:
                  - codeconnections:UseConnection
                  - codeconnections:GetConnection
                Resource: !Ref CodeConnectionArn

  # ==========================================================================
  # CODEBUILD PROJECT
  # ==========================================================================
  CodeBuildProject:
    Type: AWS::CodeBuild::Project
    Properties:
      Name: !Sub ${ApplicationName}-build-${EnvironmentName}
      ServiceRole: !GetAtt CodeBuildRole.Arn
      Artifacts:
        Type: CODEPIPELINE
      Environment:
        Type: LINUX_CONTAINER
        ComputeType: BUILD_GENERAL1_SMALL
        Image: aws/codebuild/amazonlinux2-x86_64-standard:4.0
        EnvironmentVariables:
          - Name: ENVIRONMENT_NAME
            Value: !Ref EnvironmentName
          - Name: APPLICATION_NAME
            Value: !Ref ApplicationName
          - Name: ARTIFACT_BUCKET
            Value: !Ref ArtifactBucket
      Source:
        Type: CODEPIPELINE
        BuildSpec: buildspec.yml

  # ==========================================================================
  # PIPELINE ROLE
  # ==========================================================================
  PipelineRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub ${ApplicationName}-pipeline-role-${EnvironmentName}
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: codepipeline.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: PipelinePolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:GetObjectVersion
                  - s3:PutObject
                Resource:
                  - !GetAtt ArtifactBucket.Arn
                  - !Sub ${ArtifactBucket.Arn}/*
              - Effect: Allow
                Action:
                  - codebuild:BatchGetBuilds
                  - codebuild:StartBuild
                Resource: !GetAtt CodeBuildProject.Arn
              - Effect: Allow
                Action:
                  - cloudformation:CreateStack
                  - cloudformation:UpdateStack
                  - cloudformation:DeleteStack
                  - cloudformation:DescribeStacks
                  - cloudformation:CreateChangeSet
                  - cloudformation:ExecuteChangeSet
                  - cloudformation:DeleteChangeSet
                  - cloudformation:DescribeChangeSet
                Resource: !Sub arn:aws:cloudformation:${AWS::Region}:${AWS::AccountId}:stack/${ApplicationName}-${EnvironmentName}/*
              - Effect: Allow
                Action:
                  - iam:PassRole
                Resource: !GetAtt CloudFormationRole.Arn
              - Effect: Allow
                Action:
                  - codeconnections:UseConnection
                  - codeconnections:GetConnection
                Resource: !Ref CodeConnectionArn

  # ==========================================================================
  # CLOUDFORMATION ROLE
  # ==========================================================================
  CloudFormationRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub ${ApplicationName}-cfn-role-${EnvironmentName}
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: cloudformation.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AdministratorAccess

  # ==========================================================================
  # PIPELINE
  # ==========================================================================
  Pipeline:
    Type: AWS::CodePipeline::Pipeline
    Properties:
      Name: !Sub ${ApplicationName}-pipeline-${EnvironmentName}
      RoleArn: !GetAtt PipelineRole.Arn
      ArtifactStore:
        Type: S3
        Location: !Ref ArtifactBucket
      Stages:
        # SOURCE STAGE
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
                OutputArtifactFormat: CODE_ZIP
              OutputArtifacts:
                - Name: SourceOutput
              RunOrder: 1

        # BUILD STAGE
        - Name: Build
          Actions:
            - Name: BuildAction
              ActionTypeId:
                Category: Build
                Owner: AWS
                Provider: CodeBuild
                Version: '1'
              Configuration:
                ProjectName: !Ref CodeBuildProject
              InputArtifacts:
                - Name: SourceOutput
              OutputArtifacts:
                - Name: BuildOutput
              RunOrder: 1

        # DEPLOY STAGE
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
                TemplateConfiguration: BuildOutput::config.json
                Capabilities: CAPABILITY_IAM,CAPABILITY_AUTO_EXPAND,CAPABILITY_NAMED_IAM
                RoleArn: !GetAtt CloudFormationRole.Arn
              InputArtifacts:
                - Name: BuildOutput
              RunOrder: 1

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
              RunOrder: 2

Outputs:
  PipelineName:
    Value: !Ref Pipeline

  ArtifactBucketName:
    Value: !Ref ArtifactBucket
EOF

Execution Commands
Step 1: Initial Setup
bash# Navigate to project directory
cd ~/Data-pipeline-aws

# Install pipenv
pip install pipenv

# Install dependencies
pipenv install

# Install dev dependencies (optional)
pipenv install --dev

Step 2: Deploy CI/CD Pipeline (One-time)
bash# Variables - UPDATE THESE
REGION="us-east-2"
GITHUB_OWNER="your-github-username"
CODE_CONNECTION_ARN="arn:aws:codeconnections:us-east-2:YOUR_ACCOUNT_ID:connection/YOUR_CONNECTION_ID"

# Deploy pipeline stack
aws cloudformation deploy \
  --template-file cloudformation/pipeline.yaml \
  --stack-name serverless-app-pipeline-dev \
  --parameter-overrides \
    CodeConnectionArn="$CODE_CONNECTION_ARN" \
    GitHubOwner="$GITHUB_OWNER" \
    GitHubRepo="Data-pipeline-aws" \
    GitHubBranch="main" \
    ApplicationName="serverless-app" \
    EnvironmentName="dev" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $REGION

echo "✅ Pipeline deployed!"

Step 3: Push Code to GitHub (Triggers Pipeline)
bashcd ~/Data-pipeline-aws

# Initialize git (if not done)
git init

# Add remote (if not done)
git remote add origin https://github.com/YOUR_USERNAME/Data-pipeline-aws.git

# Add all files
git add .

# Commit
git commit -m "Initial commit - Complete data pipeline"

# Push
git push -u origin main

echo "✅ Code pushed! Pipeline will trigger automatically."

Step 4: Monitor Pipeline
bash# Check pipeline status
aws codepipeline get-pipeline-state \
  --name serverless-app-pipeline-dev \
  --region us-east-2 \
  --query "stageStates[*].[stageName,latestExecution.status]" \
  --output table

# Watch pipeline (run multiple times)
watch -n 30 "aws codepipeline get-pipeline-state --name serverless-app-pipeline-dev --region us-east-2 --query 'stageStates[*].[stageName,latestExecution.status]' --output table"

Step 5: After Pipeline Deploys - Upload Glue Script
bash# Get bucket name
GLUE_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs[?OutputKey=='GlueDataBucketName'].OutputValue" \
  --output text)

echo "Bucket: $GLUE_BUCKET"

# Upload Glue script
aws s3 cp glue/csv_processor.py s3://$GLUE_BUCKET/scripts/csv_processor.py --region us-east-2

# Upload sample data
aws s3 cp glue/sample_data.csv s3://$GLUE_BUCKET/input/sample_data.csv --region us-east-2

echo "✅ Files uploaded!"

# Verify
aws s3 ls s3://$GLUE_BUCKET/ --recursive --region us-east-2

Step 6: Get Stack Outputs
aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs" \
  --output table

Step 7: Test API Endpoint
bash# Get health endpoint
HEALTH_URL=$(aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs[?OutputKey=='HealthEndpoint'].OutputValue" \
  --output text)

echo "Health URL: $HEALTH_URL"

# Test
curl -s "$HEALTH_URL" | jq .

Step 8: Run Step Function (Using Python Scripts)
bashcd ~/Data-pipeline-aws

# Option 1: Using pipenv run
pipenv run python scripts/upload_and_run.py glue/sample_data.csv

# Option 2: Using pipenv shell
pipenv shell
python scripts/upload_and_run.py glue/sample_data.csv
exit

# Option 3: Direct AWS CLI
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs[?OutputKey=='StateMachineArn'].OutputValue" \
  --output text)

GLUE_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs[?OutputKey=='GlueDataBucketName'].OutputValue" \
  --output text)

aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input "{\"inputPath\": \"s3://$GLUE_BUCKET/input/\", \"outputPath\": \"s3://$GLUE_BUCKET/output/\"}" \
  --region us-east-2

Step 9: Check Execution Status
bash# List recent executions
pipenv run python scripts/check_status.py --list

# Or using AWS CLI
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs[?OutputKey=='StateMachineArn'].OutputValue" \
  --output text)

aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --region us-east-2 \
  --query "executions[0:5].[name,status,startDate]" \
  --output table

Step 10: Check Glue Output
bashGLUE_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs[?OutputKey=='GlueDataBucketName'].OutputValue" \
  --output text)

# List output files
aws s3 ls s3://$GLUE_BUCKET/output/ --recursive --region us-east-2

# Download output
aws s3 cp s3://$GLUE_BUCKET/output/csv/ ./output/ --recursive --region us-east-2

Quick Reference - All Commands
bash# ═══════════════════════════════════════════════════════════════════════════
# PIPENV COMMANDS (from root directory)
# ═══════════════════════════════════════════════════════════════════════════

pipenv install                    # Install dependencies
pipenv install --dev              # Install with dev dependencies
pipenv shell                      # Activate virtual environment
pipenv run generate               # Generate Step Function definitions
pipenv run list                   # List step functions
pipenv run check                  # Check execution status
pipenv run format                 # Format code with black
pipenv run lint                   # Lint code with flake8
pipenv run test                   # Run tests

# ═══════════════════════════════════════════════════════════════════════════
# PYTHON SCRIPTS
# ═══════════════════════════════════════════════════════════════════════════

pipenv run python scripts/invoke_step_function.py --generate
pipenv run python scripts/invoke_step_function.py --list
pipenv run python scripts/invoke_step_function.py --invoke JOB_NAME --role-arn ARN
pipenv run python scripts/check_status.py --list
pipenv run python scripts/upload_and_run.py data.csv

# ═══════════════════════════════════════════════════════════════════════════
# AWS CLI
# ═══════════════════════════════════════════════════════════════════════════

# Pipeline status
aws codepipeline get-pipeline-state --name serverless-app-pipeline-dev --region us-east-2

# Stack outputs
aws cloudformation describe-stacks --stack-name serverless-app-dev --region us-east-2 --query "Stacks[0].Outputs"

# Start Step Function
aws stepfunctions start-execution --state-machine-arn ARN --input '{"inputPath":"...","outputPath":"..."}'

# Check executions
aws stepfunctions list-executions --state-machine-arn ARN --region us-east-2

# ═══════════════════════════════════════════════════════════════════════════
# GIT
# ═══════════════════════════════════════════════════════════════════════════

git add .
git commit -m "Your message"
git push origin main
```

---

## Summary
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  COMPLETE DATA PIPELINE PROJECT                                            │
│                                                                             │
│  16 Files Total:                                                           │
│  ├── Root: Pipfile, .python-version, .gitignore                           │
│  ├── Config: serverless-app-template.yml, buildspec.yml, dev.json         │
│  ├── Lambda: lambda/api/app.py                                            │
│  ├── Glue: glue/csv_processor.py, glue/sample_data.csv                    │
│  ├── Scripts: scripts/*.py (4 files)                                      │
│  ├── Tests: tests/*.py (2 files)                                          │
│  └── CloudFormation: cloudformation/pipeline.yaml                         │
│                                                                             │
│  WORKFLOW:                                                                  │
│  1. git push → Pipeline triggers                                          │
│  2. CodeBuild packages SAM application                                    │
│  3. CloudFormation deploys resources                                      │
│  4. Upload CSV to S3                                                       │
│  5. Run Step Function (via Python script or CLI)                          │
│  6. Step Function invokes Glue job                                        │
│  7. Check output in S3                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


# Generate Step Function definitions from CSV files
python scripts/invoke_step_function.py --generate

# List available step functions
python scripts/invoke_step_function.py --list

# Create state machine in AWS
python scripts/invoke_step_function.py --create-state-machine JOB_NAME \
  --role-arn arn:aws:iam::533267066040:role/StepFunctionsGlueRole

# Invoke step function and wait for completion
python scripts/invoke_step_function.py --invoke JOB_NAME \
  --role-arn arn:aws:iam::533267066040:role/StepFunctionsGlueRole

# Invoke without waiting
python scripts/invoke_step_function.py --invoke JOB_NAME \
  --role-arn arn:aws:iam::533267066040:role/StepFunctionsGlueRole \
  --no-wait

# Custom S3 paths
python scripts/invoke_step_function.py --generate \
  --bucket my-bucket \
  --input-prefix data/input/ \
  --output-prefix data/output/
```

---

## Step Function Definition Structure

The generated Step Function has this workflow:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  START                                                                      │
│    │                                                                        │
│    ▼                                                                        │
│  ┌─────────────────┐                                                       │
│  │ InvokeGlueJob   │──── Runs Glue job with arguments                     │
│  │ (with retry)    │     Retry: 2 attempts, 60s interval                  │
│  └────────┬────────┘                                                       │
│           │                                                                 │
│     ┌─────┴─────┐ (on error)                                               │
│     │           │                                                          │
│     ▼           ▼                                                          │
│  ┌──────────────────┐   ┌─────────────────┐                                │
│  │CheckGlueJobStatus│   │  NotifyFailure  │──► SNS Notification            │
│  └────────┬─────────┘   └────────┬────────┘                                │
│           │                      │                                          │
│     ┌─────┴─────┐                ▼                                          │
│     │           │         ┌─────────────┐                                  │
│     ▼           ▼         │  FailState  │                                  │
│  ┌────────┐  ┌────────┐   └─────────────┘                                  │
│  │SUCCESS │  │ FAILED │                                                    │
│  └────────┘  └───┬────┘                                                    │
│                  │                                                          │
│                  ▼                                                          │
│           NotifyFailure ──► SNS                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

"StartGlueJob": {
  ...
  "ResultPath": "$.glueResult",
  "Next": "JobSucceeded",        # ← Go here on success
  "Catch": [
    {
      "ErrorEquals": ["States.ALL"],
      "Next": "JobFailed"        # ← Go here on error
    }
  ]
}
```

---

## Complete Flow Diagram
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  COMPLETE INVOCATION FLOW                                                   │
│                                                                             │
│  ┌─────────────────┐                                                       │
│  │  Python Script  │                                                       │
│  │  (Boto3)        │                                                       │
│  └────────┬────────┘                                                       │
│           │                                                                 │
│           │ 1. sfn.start_execution(                                        │
│           │      stateMachineArn=ARN,                                      │
│           │      input={"inputPath": "s3://...", "outputPath": "s3://..."} │
│           │    )                                                           │
│           ▼                                                                 │
│  ┌─────────────────┐                                                       │
│  │ Step Functions  │                                                       │
│  │ State Machine   │                                                       │
│  └────────┬────────┘                                                       │
│           │                                                                 │
│           │ 2. Execute "StartGlueJob" state                                │
│           │    Resource: arn:aws:states:::glue:startJobRun.sync           │
│           │    Parameters:                                                 │
│           │      JobName: serverless-app-csv-processor-dev                │
│           │      Arguments:                                                │
│           │        --INPUT_PATH: $.inputPath                              │
│           │        --OUTPUT_PATH: $.outputPath                            │
│           ▼                                                                 │
│  ┌─────────────────┐                                                       │
│  │   AWS Glue      │                                                       │
│  │   Service       │                                                       │
│  └────────┬────────┘                                                       │
│           │                                                                 │
│           │ 3. glue.start_job_run(                                         │
│           │      JobName='serverless-app-csv-processor-dev',              │
│           │      Arguments={                                               │
│           │        '--INPUT_PATH': 's3://bucket/input/',                  │
│           │        '--OUTPUT_PATH': 's3://bucket/output/'                 │
│           │      }                                                         │
│           │    )                                                           │
│           ▼                                                                 │
│  ┌─────────────────┐                                                       │
│  │  Spark Cluster  │                                                       │
│  │  (G.1X Workers) │                                                       │
│  └────────┬────────┘                                                       │
│           │                                                                 │
│           │ 4. Download script from S3:                                    │
│           │    s3://bucket/scripts/csv_processor.py                       │
│           │                                                                 │
│           │ 5. Run script:                                                 │
│           │    python csv_processor.py \                                  │
│           │      --JOB_NAME serverless-app-csv-processor-dev \            │
│           │      --INPUT_PATH s3://bucket/input/ \                        │
│           │      --OUTPUT_PATH s3://bucket/output/                        │
│           ▼                                                                 │
│  ┌─────────────────┐                                                       │
│  │csv_processor.py │                                                       │
│  │                 │                                                       │
│  │ args = getResolvedOptions(sys.argv,                                    │
│  │          ['JOB_NAME', 'INPUT_PATH', 'OUTPUT_PATH'])                    │
│  │                                                                         │
│  │ # Read from input path                                                 │
│  │ # Process data                                                         │
│  │ # Write to output path                                                 │
│  └────────┬────────┘                                                       │
│           │                                                                 │
│           │ 6. Job completes → Returns result to Glue                     │
│           ▼                                                                 │
│  ┌─────────────────┐                                                       │
│  │   AWS Glue      │ ← Job status: SUCCEEDED                              │
│  └────────┬────────┘                                                       │
│           │                                                                 │
│           │ 7. Step Functions receives result (because of .sync)          │
│           ▼                                                                 │
│  ┌─────────────────┐                                                       │
│  │ Step Functions  │                                                       │
│  │ → JobSucceeded  │                                                       │
│  └────────┬────────┘                                                       │
│           │                                                                 │
│           │ 8. Execution complete                                          │
│           ▼                                                                 │
│  ┌─────────────────┐                                                       │
│  │  Python Script  │ ← Receives final status                              │
│  │  (waiting)      │                                                       │
│  └─────────────────┘                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Concepts Summary
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  KEY CONCEPTS                                                               │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. SERVICE INTEGRATION                                                     │
│     "arn:aws:states:::glue:startJobRun.sync"                              │
│     Step Functions has native integration with Glue - no Lambda needed!   │
│                                                                             │
│  2. .sync SUFFIX                                                           │
│     Makes Step Functions wait for Glue job to complete                    │
│     Without it, Step Functions would immediately move to next state       │
│                                                                             │
│  3. PARAMETER PASSING                                                       │
│     "--INPUT_PATH.$": "$.inputPath"                                       │
│     The .$ suffix means "get value from JSON path"                        │
│                                                                             │
│  4. getResolvedOptions                                                     │
│     Glue utility function to parse command-line arguments                 │
│     Arguments are passed as --KEY value format                            │
│                                                                             │
│  5. SCRIPT LOCATION                                                        │
│     Glue job definition specifies:                                        │
│     ScriptLocation: s3://bucket/scripts/csv_processor.py                  │
│     Glue downloads and runs this script                                   │
│                                                                             │
│  6. NO LAMBDA REQUIRED                                                     │
│     Direct integration: Step Functions → Glue                             │
│     Simpler, cheaper, less code to maintain                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

## Rerun Step function
# Using the Python script
pipenv run python scripts/invoke_step_function.py --run --region us-east-2

# Or using AWS CLI
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
  --stack-name serverless-app-dev \
  --region us-east-2 \
  --query "Stacks[0].Outputs[?OutputKey=='StateMachineArn'].OutputValue" \
  --output text)

GLUE_BUCKET="serverless-app-glue-data-615299756109-us-east-2"

aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input "{\"inputPath\": \"s3://$GLUE_BUCKET/input/\", \"outputPath\": \"s3://$GLUE_BUCKET/output/\"}" \
  --region us-east-2


#  methodArn is the Amazon Resource Name (ARN) that uniquely identifies the API Gateway method being invoked. It's automatically passed to your Lambda authorizer by API Gateway.

arn:aws:execute-api:{region}:{account-id}:{api-id}/{stage}/{http-method}/{resource-path}

arn:aws:execute-api:us-east-2:615299756109:abc123def4/dev/GET/health
                    ─────────  ────────────  ──────────  ───  ───  ──────
                       │            │            │        │    │     │
                    Region     Account ID    API ID   Stage Method  Path

                    """
API Gateway Request Header Authorizer
Validates Client-ID header against allowed list
"""

import os
import json
import boto3


def handler(event, context):
    """
    Lambda Authorizer for API Gateway
    Validates Client-ID header against allowed list
    """
    print(f"Event: {json.dumps(event)}")
    
    # Get Client-ID from headers (case-insensitive)
    headers = event.get('headers', {})
    client_id = (
        headers.get('Client-ID') or 
        headers.get('client-id') or 
        headers.get('CLIENT-ID') or
        headers.get('x-client-id') or
        headers.get('X-Client-ID')
    )
    
    # Get method ARN for policy
    method_arn = event.get('methodArn', '')
    
    # Get valid client IDs from environment
    valid_client_ids_str = os.environ.get('VALID_CLIENT_IDS', '')
    valid_client_ids = [cid.strip() for cid in valid_client_ids_str.split(',') if cid.strip()]
    
    # Validate Client-ID
    if not client_id:
        return generate_policy('anonymous', 'Deny', method_arn)
    
    if client_id not in valid_client_ids:
        return generate_policy(client_id, 'Deny', method_arn)
    
    return generate_policy(client_id, 'Allow', method_arn, context={
        'clientId': client_id,
        'environment': os.environ.get('ENVIRONMENT', 'dev')
    })


def generate_policy(principal_id, effect, resource, context=None):
    """Generate IAM policy document for API Gateway"""
    arn_parts = resource.split('/')
    base_arn = '/'.join(arn_parts[:2])
    
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': effect,
                'Resource': f"{base_arn}/*"
            }]
        }
    }
    
    if context:
        policy['context'] = context
    
    return policy
```

---

## Architecture Diagram
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Data-pipeline-aws                                                         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  API Gateway                                                         │   │
│  │  ┌─────────────────┐    ┌──────────────────┐    ┌────────────────┐ │   │
│  │  │ Client Request  │───►│ Authorizer       │───►│ Health Lambda  │ │   │
│  │  │ + Client-ID     │    │ (authorizer.py)  │    │ (app.py)       │ │   │
│  │  └─────────────────┘    └──────────────────┘    └────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Step Functions                                                      │   │
│  │  ┌─────────────────┐    ┌──────────────────┐    ┌────────────────┐ │   │
│  │  │ Start           │───►│ Glue Job         │───►│ Success/Fail   │ │   │
│  │  │                 │    │ (csv_processor)  │    │ + SNS Notify   │ │   │
│  │  └─────────────────┘    └──────────────────┘    └────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  S3 Bucket                                                          │   │
│  │  ├── /scripts/csv_processor.py                                      │   │
│  │  ├── /input/*.csv                                                   │   │
│  │  └── /output/parquet/ & /output/csv/                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  CLIENT REQUEST                                                            │
│  ───────────────                                                           │
│  GET /health                                                               │
│  Headers: Client-ID: client-app-1                                          │
│                                                                             │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        API GATEWAY                                   │   │
│  │                                                                      │   │
│  │  Step 1: Receive request                                            │   │
│  │  Step 2: Extract Client-ID header                                   │   │
│  │  Step 3: Call Authorizer Lambda ─────────────────────┐              │   │
│  │                                                       │              │   │
│  │         ┌─────────────────────────────────────────────┼──────────┐  │   │
│  │         │                                             ▼          │  │   │
│  │         │  ┌─────────────────────────────────────────────────┐   │  │   │
│  │         │  │  AUTHORIZER LAMBDA (authorizer.py)              │   │  │   │
│  │         │  │                                                  │   │  │   │
│  │         │  │  - Validates Client-ID                          │   │  │   │
│  │         │  │  - Returns Allow/Deny policy                    │   │  │   │
│  │         │  └─────────────────────────────────────────────────┘   │  │   │
│  │         │                         │                              │  │   │
│  │         │                         │ Returns policy               │  │   │
│  │         │                         ▼                              │  │   │
│  │         │              ┌─────────────────────┐                   │  │   │
│  │         │              │ Allow    │   Deny   │                   │  │   │
│  │         │              └────┬─────┴────┬─────┘                   │  │   │
│  │         │                   │          │                         │  │   │
│  │         └───────────────────┼──────────┼─────────────────────────┘  │   │
│  │                             │          │                            │   │
│  │  Step 4a: If ALLOW ─────────┘          └───── Step 4b: If DENY     │   │
│  │         │                                            │              │   │
│  │         ▼                                            ▼              │   │
│  │  ┌─────────────────┐                    ┌─────────────────────┐    │   │
│  │  │ Call app.py     │                    │ Return 403 Forbidden│    │   │
│  │  │ (Health Lambda) │                    │ (Never calls app.py)│    │   │
│  │  └─────────────────┘                    └─────────────────────┘    │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

# API Gateway with Authorizer
ApiGateway:
  Type: AWS::Serverless::Api
  Properties:
    Name: !Sub ${ApplicationName}-api-${EnvironmentName}
    StageName: !Ref EnvironmentName
    Auth:
      DefaultAuthorizer: ClientIdAuthorizer        # ← Use this authorizer
      Authorizers:
        ClientIdAuthorizer:
          FunctionArn: !GetAtt ClientIdAuthorizerFunction.Arn  # ← Points to authorizer Lambda
          Identity:
            Headers:
              - Client-ID                          # ← Extract this header

# Health Check Lambda (app.py)
HealthCheckFunction:
  Type: AWS::Serverless::Function
  Properties:
    Handler: app.lambda_handler
    CodeUri: lambda/api/
    Events:
      HealthGet:
        Type: Api
        Properties:
          RestApiId: !Ref ApiGateway               # ← Uses the API Gateway above
          Path: /health                            # ← (which has the authorizer)
          Method: GET


---

## Sequence Diagram
```
   Client              API Gateway           Authorizer            app.py
     │                     │                    │                    │
     │  GET /health        │                    │                    │
     │  Client-ID: app-1   │                    │                    │
     │────────────────────►│                    │                    │
     │                     │                    │                    │
     │                     │  Invoke Lambda     │                    │
     │                     │  with headers      │                    │
     │                     │───────────────────►│                    │
     │                     │                    │                    │
     │                     │                    │  Validate          │
     │                     │                    │  Client-ID         │
     │                     │                    │                    │
     │                     │  Return Policy     │                    │
     │                     │  (Allow/Deny)      │                    │
     │                     │◄───────────────────│                    │
     │                     │                    │                    │
     │                     │                    │                    │
     │            ┌────────┴────────┐           │                    │
     │            │                 │           │                    │
     │         ALLOW              DENY         │                    │
     │            │                 │           │                    │
     │            ▼                 ▼           │                    │
     │     ┌──────────────┐  ┌──────────┐      │                    │
     │     │ Call app.py  │  │ Return   │      │                    │
     │     │              │  │ 403      │      │                    │
     │     └──────┬───────┘  └────┬─────┘      │                    │
     │            │               │            │                    │
     │            │  Invoke       │            │                    │
     │            │  Lambda       │            │                    │
     │            │───────────────┼────────────┼───────────────────►│
     │            │               │            │                    │
     │            │               │            │   Process request  │
     │            │               │            │   Return response  │
     │            │               │            │                    │
     │            │◄──────────────┼────────────┼────────────────────│
     │            │               │            │                    │
     │  Response  │               │            │                    │
     │◄───────────┤               │            │                    │
     │            │               │            │                    │
     │  OR        │               │            │                    │
     │◄───────────┴───────────────┘            │                    │
     │  403 Forbidden                          │                    │
     │                                         │                    │