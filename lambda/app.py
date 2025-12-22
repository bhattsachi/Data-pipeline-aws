
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
SECRET_NAME = os.environ.get("SECRET_NAME", "")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "unknown")
APPLICATION_NAME = os.environ.get("APPLICATION_NAME", "unknown")


def get_secret():
    try:
        secret_id = SECRET_ARN if SECRET_ARN else SECRET_NAME
        if not secret_id:
            raise ValueError("SECRET_ARN or SECRET_NAME not configured")
        
        response = secrets_client.get_secret_value(SecretId=secret_id)
        return json.loads(response.get("SecretString", "{}"))
    except ClientError as e:
        logger.error(f"Failed to get secret: {e}")
        raise


def create_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }


def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    http_method = event.get("httpMethod", "UNKNOWN")
    path = event.get("path", "/")
    request_id = event.get("requestContext", {}).get("requestId", "unknown")
    
    try:
        secret_data = get_secret()
        
        if path == "/health":
            response_body = {
                "status": "healthy",
                "message": "Service is running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environment": ENVIRONMENT,
                "application": APPLICATION_NAME,
                "request_id": request_id,
                "secret_config": {
                    "app_name": secret_data.get("app_name"),
                    "environment": secret_data.get("environment"),
                    "api_key_present": "api_key" in secret_data,
                },
            }
        elif path == "/test":
            request_body = {}
            if event.get("body"):
                try:
                    request_body = json.loads(event["body"])
                except json.JSONDecodeError:
                    request_body = {"raw": event["body"]}
            
            response_body = {
                "status": "success",
                "message": "Test endpoint working",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environment": ENVIRONMENT,
                "echo": {
                    "method": http_method,
                    "path": path,
                    "body": request_body,
                },
                "secret_verified": bool(secret_data.get("api_key")),
            }
        else:
            response_body = {
                "status": "success",
                "message": f"Received request to {path}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        
        return create_response(200, response_body)
        
    except Exception as e:
        logger.exception(f"Error: {e}")
        return create_response(500, {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
