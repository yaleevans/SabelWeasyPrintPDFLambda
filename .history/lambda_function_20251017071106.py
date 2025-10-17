import json
import os
import boto3
import base64 # <-- NEW IMPORT
from weasyprint import HTML, CSS

# Initialize the S3 client outside the handler for better performance
s3_client = boto3.client('s3')

# --- READ ENVIRONMENT VARIABLE ---
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')

def lambda_handler(event, context):
    """
    Generates a PDF, saves a copy to S3, Base64-encodes the content, and returns the Base64 string in a JSON payload.
    """
    if not S3_BUCKET_NAME:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': "Lambda environment variable S3_BUCKET_NAME is not set."})
        }
    
    BUCKET = S3_BUCKET_NAME 
    
    try:
        # --- 1. Define Input Parameters ---
        TEMPLATE_KEY = event['template_s3_key']
        OUTPUT_FILENAME = event['output_filename']
        OUTPUT_KEY_PREFIX = event.get('output_s3_key_prefix', '') 
        DATA_MAPPING = event.get('data', {})
        BACKGROUND_COLOR = event.get('background_color', 'white') 
        
        FINAL_OUTPUT_KEY = f"{OUTPUT_KEY_PREFIX}{OUTPUT_FILENAME}"
        
        # --- 2. Fetch HTML Template & Inject Styling ---
        s3_response = s3_client.get_object(Bucket=BUCKET, Key=TEMPLATE_KEY)
        html_content = s3_response['Body'].read().decode('utf-8')

        css_style_injection = f"<style>@page {{ background-color: {BACKGROUND_COLOR} !important; }}</style>"
        html_content = html_content.replace("</head>", f"{css_style_injection}</head>")

        # --- 3. Dynamic Variable Replacement ---
        for key, value in DATA_MAPPING.items():
            placeholder = f"{{ {key} }}"
            html_content = html_content.replace(placeholder, str(value))
        
        # --- 4. Generate PDF BYTES ---
        base_url = f"s3://{BUCKET}/" 
        pdf_bytes = HTML(string=html_content, base_url=base_url).write_pdf()

        # --- 5. Save PDF to Target S3 Location (Feature 4 - Copy) ---
        # This keeps the request to save a copy in S3
        s3_client.put_object(
            Bucket=BUCKET,
            Key=FINAL_OUTPUT_KEY,
            Body=pdf_bytes,
            ContentType='application/pdf'
        )
        
        # --- 6. Base64 Encode the PDF Bytes (NEW STEP) ---
        pdf_base64_string = base64.b64encode(pdf_bytes).decode('utf-8')

        # --- 7. Return the Base64 string and S3 path in a JSON response ---
        return {
            'statusCode': 200,
            'headers': {
                # This header is often required for API Gateway when returning Base64
                'Content-Type': 'application/json' 
            },
            'body': json.dumps({
                'message': 'PDF generated and uploaded successfully.',
                's3_path': f"s3://{BUCKET}/{FINAL_OUTPUT_KEY}",
                'pdf_base64': pdf_base64_string # <-- The PDF content is here
            })
        }

    except KeyError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f"Missing required field in payload: {e}"})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }