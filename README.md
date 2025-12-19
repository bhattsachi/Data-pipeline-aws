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


