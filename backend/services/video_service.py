import os
import boto3
import time
import json
import uuid

# AWS Bedrock Nova Reel requires an S3 bucket for output
S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET", "shortcutai-nova-assets-1")

def _get_aws_clients():
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    aws_access = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if aws_access and aws_secret:
        aws_access = aws_access.strip('"\'')
        aws_secret = aws_secret.strip('"\'')
        
        bedrock = boto3.client(
            'bedrock-runtime', 
            region_name=region,
            aws_access_key_id=aws_access,
            aws_secret_access_key=aws_secret
        )
        s3 = boto3.client(
            's3', 
            region_name=region,
            aws_access_key_id=aws_access,
            aws_secret_access_key=aws_secret
        )
    else:
        bedrock = boto3.client('bedrock-runtime', region_name=region)
        s3 = boto3.client('s3', region_name=region)
        
    return bedrock, s3

def _ensure_s3_bucket(s3_client, region):
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
    except Exception:
        # Bucket doesn't exist or we don't have access, try to create it
        try:
            if region == 'us-east-1':
                s3_client.create_bucket(Bucket=S3_BUCKET_NAME)
            else:
                s3_client.create_bucket(
                    Bucket=S3_BUCKET_NAME,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
        except Exception as e:
            print(f"Failed to create S3 bucket {S3_BUCKET_NAME}: {e}")

def generate_nova_reel_clip(prompt: str, seed: int = None) -> str:
    """
    Generates a 6-second video clip using Amazon Nova Reel.
    Returns the local path to the downloaded MP4 file.
    """
    bedrock, s3 = _get_aws_clients()
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    _ensure_s3_bucket(s3, region)

    model_id = "amazon.nova-reel-v1:0"
    
    s3_destination = f"s3://{S3_BUCKET_NAME}/nova/"

    body = {
        "taskType": "TEXT_VIDEO",
        "textToVideoParams": {
            "text": prompt
        },
        "videoGenerationConfig": {
            "durationSeconds": 6,
            "fps": 24,
            "dimension": "1280x720",
        }
    }
    
    if seed is not None:
        body["videoGenerationConfig"]["seed"] = seed

    print(f"[NovaReel] Starting Async Invoke for prompt: '{prompt}'")
    
    # Get AWS Account ID for bucketOwner parameter (required for Nova Reel S3 output)
    sts = boto3.client('sts', region_name=region, 
                       aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "").strip('"\''), 
                       aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "").strip('"\''))
    account_id = sts.get_caller_identity()['Account']

    response = bedrock.start_async_invoke(
        modelId=model_id,
        modelInput=body,
        outputDataConfig={
            "s3OutputDataConfig": {
                "s3Uri": s3_destination,
                "bucketOwner": account_id
            }
        }
    )
    
    invocation_arn = response['invocationArn']
    print(f"[NovaReel] Invocation ARN: {invocation_arn}")
    
    # Poll for completion
    max_retries = 60 # 60 * 10s = 10 minutes
    retries = 0
    while retries < max_retries:
        status_response = bedrock.get_async_invoke(invocationArn=invocation_arn)
        status = status_response['status']
        print(f"[NovaReel] Status: {status} ({retries}/{max_retries})")
        
        if status == 'Completed':
            break
        elif status == 'Failed':
            error_message = status_response.get('failureMessage', 'Unknown error')
            raise Exception(f"Nova Reel generation failed: {error_message}")
            
        time.sleep(10)
        retries += 1
        
    if retries >= max_retries:
        raise Exception("Nova Reel generation timed out.")
        
    # Bedrock automatically appends the invocation ID (the last part of the ARN) to the S3 URI
    bedrock_invocation_id = invocation_arn.split('/')[-1]
    output_prefix = f"nova/{bedrock_invocation_id}/output.mp4"
    local_dir = "/app/temp"
    if not os.path.exists(local_dir):
        os.makedirs(local_dir, exist_ok=True)
        
    local_path = os.path.join(local_dir, f"nova_reel_{bedrock_invocation_id}.mp4")
    
    print(f"[NovaReel] Downloading video from {s3_destination}output.mp4")
    s3.download_file(S3_BUCKET_NAME, output_prefix, local_path)
    print(f"[NovaReel] Video downloaded to {local_path}")
    
    return local_path
