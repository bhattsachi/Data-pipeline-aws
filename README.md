# Pipeline 

pipeline-stack.yml - Main CloudFormation template that creates:
CodePipeline with 5 stages (Source, Validation, Dev Deploy, Approval, Test Deploy)
3 CodeBuild projects for validation and deployment
S3 artifact bucket with cross-account access
IAM roles and policies


cross-account-role.yml - IAM role template for Dev and Test accounts to allow cross-account deployments

buildspec-deploy.yml - CodeBuild specification that packages Lambda functions and deploys CloudFormation stacks

deploy-pipeline.sh - Interactive bash script for easy pipeline deployment

dev-params.json & test-params.json - Environment-specific configuration parameters
#