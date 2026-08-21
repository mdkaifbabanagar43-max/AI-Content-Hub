import boto3, json, os
from dotenv import load_dotenv

load_dotenv('.env')

aws_access = os.getenv('AWS_ACCESS_KEY_ID').strip('"\'')
aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY').strip('"\'')

sts = boto3.client('sts', region_name='us-east-1', aws_access_key_id=aws_access, aws_secret_access_key=aws_secret)
account_id = sts.get_caller_identity()['Account']

s3 = boto3.client('s3', region_name='us-east-1', aws_access_key_id=aws_access, aws_secret_access_key=aws_secret)
bucket_name = 'shortcutai-nova-assets-1'

policy = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Sid': 'AllowBedrockAccess',
            'Effect': 'Allow',
            'Principal': {
                'Service': 'bedrock.amazonaws.com'
            },
            'Action': [
                's3:GetObject',
                's3:PutObject',
                's3:ListBucket'
            ],
            'Resource': [
                f'arn:aws:s3:::{bucket_name}',
                f'arn:aws:s3:::{bucket_name}/*'
            ],
            'Condition': {
                'StringEquals': {
                    'aws:SourceAccount': account_id
                }
            }
        }
    ]
}

s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
print('Successfully attached Bedrock bucket policy to ' + bucket_name)
