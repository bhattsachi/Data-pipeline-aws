
#!/usr/bin/env python3
"""
Invoke Step Functions State Machine to run Glue Job.

This script:
1. Gets configuration from CloudFormation stack outputs
2. Starts Step Functions execution
3. Monitors execution status
4. Returns results

Usage:
    python invoke.py
    python invoke.py --no-wait
    python invoke.py --input-path s3://bucket/custom/input/
"""

import boto3
import json
import time
import argparse
from datetime import datetime
from typing import Optional, Dict, Any


class StepFunctionInvoker:
    """Invoke and monitor Step Functions executions."""

    def __init__(self, region: str = "us-east-2"):
        """Initialize with AWS region."""
        self.region = region
        self.sfn_client = boto3.client("stepfunctions", region_name=region)
        self.cfn_client = boto3.client("cloudformation", region_name=region)

    def get_stack_outputs(self, stack_name: str) -> Dict[str, str]:
        """Get CloudFormation stack outputs."""
        try:
            response = self.cfn_client.describe_stacks(StackName=stack_name)
            outputs = {}
            for output in response["Stacks"][0].get("Outputs", []):
                outputs[output["OutputKey"]] = output["OutputValue"]
            return outputs
        except Exception as e:
            raise Exception(f"Failed to get stack outputs: {e}")

    def start_execution(
        self,
        state_machine_arn: str,
        input_path: str,
        output_path: str,
        execution_name: Optional[str] = None
    ) -> str:
        """
        Start Step Functions execution.

        Args:
            state_machine_arn: ARN of the state machine
            input_path: S3 input path for Glue job
            output_path: S3 output path for Glue job
            execution_name: Optional custom execution name

        Returns:
            Execution ARN
        """
        if execution_name is None:
            execution_name = f"exec-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        execution_input = {
            "inputPath": input_path,
            "outputPath": output_path,
            "executionTime": datetime.now().isoformat()
        }

        response = self.sfn_client.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=json.dumps(execution_input)
        )

        return response["executionArn"]

    def get_execution_status(self, execution_arn: str) -> Dict[str, Any]:
        """Get execution status."""
        response = self.sfn_client.describe_execution(executionArn=execution_arn)

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
        """
        Wait for execution to complete.

        Args:
            execution_arn: ARN of the execution
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait

        Returns:
            Final execution status
        """
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

    def list_executions(
        self,
        state_machine_arn: str,
        status_filter: Optional[str] = None,
        max_results: int = 10
    ) -> list:
        """List recent executions."""
        params = {
            "stateMachineArn": state_machine_arn,
            "maxResults": max_results
        }

        if status_filter:
            params["statusFilter"] = status_filter

        response = self.sfn_client.list_executions(**params)

        return [
            {
                "name": e["name"],
                "status": e["status"],
                "startDate": e["startDate"],
                "executionArn": e["executionArn"]
            }
            for e in response.get("executions", [])
        ]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Invoke Step Functions to run Glue job"
    )
    parser.add_argument(
        "--region",
        default="us-east-2",
        help="AWS region (default: us-east-2)"
    )
    parser.add_argument(
        "--stack-name",
        default="serverless-app-dev",
        help="CloudFormation stack name (default: serverless-app-dev)"
    )
    parser.add_argument(
        "--input-path",
        help="Custom S3 input path (overrides default)"
    )
    parser.add_argument(
        "--output-path",
        help="Custom S3 output path (overrides default)"
    )
    parser.add_argument(
        "--execution-name",
        help="Custom execution name"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for execution to complete"
    )
    parser.add_argument(
        "--list-executions",
        action="store_true",
        help="List recent executions instead of starting new one"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Seconds between status checks (default: 30)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Maximum seconds to wait (default: 3600)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("STEP FUNCTIONS INVOKER")
    print("=" * 60)

    # Initialize invoker
    invoker = StepFunctionInvoker(region=args.region)

    # Get stack outputs
    print(f"\n1. Getting stack outputs from: {args.stack_name}")
    try:
        outputs = invoker.get_stack_outputs(args.stack_name)
        state_machine_arn = outputs["StateMachineArn"]
        default_input_path = outputs["GlueInputPath"]
        default_output_path = outputs["GlueOutputPath"]
        glue_job_name = outputs["GlueJobName"]
        bucket_name = outputs["GlueDataBucketName"]

        print(f"   State Machine: {outputs['StateMachineName']}")
        print(f"   Glue Job: {glue_job_name}")
        print(f"   Bucket: {bucket_name}")
    except Exception as e:
        print(f"   Error: {e}")
        return 1

    # Use custom paths or defaults
    input_path = args.input_path or default_input_path
    output_path = args.output_path or default_output_path

    print(f"   Input Path: {input_path}")
    print(f"   Output Path: {output_path}")

    # List executions if requested
    if args.list_executions:
        print(f"\n2. Listing recent executions...")
        executions = invoker.list_executions(state_machine_arn)
        print(f"\n{'Name':<40} {'Status':<12} {'Start Date'}")
        print("-" * 80)
        for e in executions:
            print(f"{e['name']:<40} {e['status']:<12} {e['startDate']}")
        return 0

    # Start execution
    print(f"\n2. Starting execution...")
    try:
        execution_arn = invoker.start_execution(
            state_machine_arn=state_machine_arn,
            input_path=input_path,
            output_path=output_path,
            execution_name=args.execution_name
        )
        print(f"   ✓ Execution started")
        print(f"   ARN: {execution_arn}")
    except Exception as e:
        print(f"   ✗ Failed to start execution: {e}")
        return 1

    # Wait for completion if requested
    if args.no_wait:
        print(f"\n3. Not waiting (--no-wait specified)")
        print(f"   Check status with: aws stepfunctions describe-execution --execution-arn {execution_arn}")
        return 0

    print(f"\n3. Waiting for completion (poll every {args.poll_interval}s, timeout {args.timeout}s)...")
    try:
        result = invoker.wait_for_completion(
            execution_arn=execution_arn,
            poll_interval=args.poll_interval,
            timeout=args.timeout
        )
    except TimeoutError as e:
        print(f"   ✗ {e}")
        return 1

    # Print results
    print("\n" + "=" * 60)
    print("EXECUTION RESULT")
    print("=" * 60)
    print(f"Status: {result['status']}")

    if result.get("output"):
        print(f"\nOutput:")
        print(json.dumps(result["output"], indent=2, default=str))

    if result.get("error"):
        print(f"\nError: {result['error']}")
        print(f"Cause: {result.get('cause', 'Unknown')}")

    return 0 if result["status"] == "SUCCEEDED" else 1


if __name__ == "__main__":
    exit(main())
