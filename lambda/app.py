"""
Lambda function for health check endpoint.
Reads a secret from AWS Secrets Manager and returns a JSON response.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
log_level = os.environ.get("LOG_LEVEL", "INFO")
logger.setLevel(getattr(logging, log_level, logging.INFO))

# Initialize clients outside handler for connection reuse
secrets_client = boto3.client("secretsmanager")

# Environment variables
SECRET_ARN = os.environ.get("SECRET_ARN", "")
SECRET_NAME = os.environ.get("SECRET_NAME", "")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "unknown")
APPLICATION_NAME = os.environ.get("APPLICATION_NAME", "unknown")


def get_secret() -> dict[str, Any]:
    """
    Retrieve the secret from AWS Secrets Manager.
    
    Returns:
        dict: The secret value as a dictionary.
        
    Raises:
        ClientError: If there's an error retrieving the secret.
    """
    try:
        # Prefer ARN over name for specificity
        secret_id = SECRET_ARN if SECRET_ARN else SECRET_NAME
        
        if not secret_id:
            raise ValueError("Neither SECRET_ARN nor SECRET_NAME is configured")
        
        logger.info(f"Retrieving secret: {SECRET_NAME}")
        
        response = secrets_client.get_secret_value(SecretId=secret_id)
        
        # Parse the secret string
        secret_string = response.get("SecretString", "{}")
        secret_data = json.loads(secret_string)
        
        logger.info("Successfully retrieved secret")
        return secret_data
        
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        
        logger.error(f"Failed to retrieve secret: {error_code} - {error_message}")
        
        # Handle specific error types
        if error_code == "DecryptionFailureException":
            raise Exception("Cannot decrypt secret - check KMS permissions") from e
        elif error_code == "InternalServiceErrorException":
            raise Exception("Secrets Manager internal error") from e
        elif error_code == "InvalidParameterException":
            raise Exception("Invalid parameter provided") from e
        elif error_code == "InvalidRequestException":
            raise Exception("Invalid request - parameter conflict") from e
        elif error_code == "ResourceNotFoundException":
            raise Exception(f"Secret not found: {SECRET_NAME}") from e
        elif error_code == "AccessDeniedException":
            raise Exception("Access denied - check IAM permissions") from e
        else:
            raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse secret JSON: {e}")
        raise Exception("Secret value is not valid JSON") from e


def create_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """
    Create a standardized API Gateway proxy response.
    
    Args:
        status_code: HTTP status code.
        body: Response body dictionary.
        
    Returns:
        dict: API Gateway proxy response format.
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-Application": APPLICATION_NAME,
            "X-Environment": ENVIRONMENT,
            "X-Request-Time": datetime.now(timezone.utc).isoformat(),
        },
        "body": json.dumps(body, default=str),
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Lambda handler for health check endpoint.
    
    Reads a secret from Secrets Manager and returns a health status response.
    
    Args:
        event: API Gateway proxy event.
        context: Lambda context object.
        
    Returns:
        dict: API Gateway proxy response.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Extract request information
    http_method = event.get("httpMethod", "UNKNOWN")
    path = event.get("path", "/")
    request_id = event.get("requestContext", {}).get("requestId", "unknown")
    
    logger.info(f"Processing {http_method} request to {path} (requestId: {request_id})")
    
    try:
        # Retrieve secret from Secrets Manager
        secret_data = get_secret()
        
        # Build response based on path
        if path == "/health":
            response_body = {
                "status": "healthy",
                "message": "Service is running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environment": ENVIRONMENT,
                "application": APPLICATION_NAME,
                "request_id": request_id,
                "lambda_request_id": context.aws_request_id,
                "secret_config": {
                    "app_name": secret_data.get("app_name", "unknown"),
                    "environment": secret_data.get("environment", "unknown"),
                    "api_key_present": "api_key" in secret_data,
                    # Never expose the actual API key!
                },
            }
        elif path == "/test":
            # Parse request body if present
            request_body = {}
            if event.get("body"):
                try:
                    request_body = json.loads(event["body"])
                except json.JSONDecodeError:
                    request_body = {"raw": event["body"]}
            
            response_body = {
                "status": "success",
                "message": "Test endpoint is working",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environment": ENVIRONMENT,
                "application": APPLICATION_NAME,
                "request_id": request_id,
                "echo": {
                    "method": http_method,
                    "path": path,
                    "body": request_body,
                    "query_params": event.get("queryStringParameters", {}),
                },
                "secret_verified": bool(secret_data.get("api_key")),
            }
        else:
            response_body = {
                "status": "success",
                "message": f"Received request to {path}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environment": ENVIRONMENT,
            }
        
        logger.info(f"Returning successful response for {path}")
        return create_response(200, response_body)
        
    except Exception as e:
        logger.exception(f"Error processing request: {e}")
        
        error_response = {
            "status": "error",
            "message": "Internal server error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": ENVIRONMENT,
            "request_id": request_id,
        }
        
        return create_response(500, error_response)