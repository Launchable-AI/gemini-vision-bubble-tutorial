import boto3
import json

def lambda_handler(event, context):
    
    # Initialize a boto3 client for Lambda
    lambda_client = boto3.client('lambda')

    video_url = event['body']['video_url']
    
    # Payload that you want to pass to the other function
    payload = {
        'body': {
            'video_url': video_url
            }
    }

    # Function name or ARN of the Lambda function you want to invoke
    function_name = 'arn:aws:lambda:us-east-1:485117195026:function:video-processor'

    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps(payload)
        )
        return {
            'statusCode': 200,
            'body': json.dumps('Invoke request sent.')
        }
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps(str(e))
        }
