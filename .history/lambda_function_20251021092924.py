import json
import os
import boto3
import base64
from weasyprint import HTML, CSS
import logging

# Configure the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize the S3 client outside the handler for better performance
s3_client = boto3.client("s3")

# --- READ ENVIRONMENT VARIABLE ---
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")


def lambda_handler(event, context):
    """
    Generates a PDF, saves a copy to S3 with a path derived from 'eventName' and 'user',
    Base64-encodes the content, and returns the Base64 string in a JSON payload.
    """
    logger.info("--- STARTING PDF GENERATION PROCESS ---")
    logger.info(f"Received event payload: {event}")

    if not S3_BUCKET_NAME:
        logger.error("Lambda environment variable S3_BUCKET_NAME is not set.")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": "Lambda environment variable S3_BUCKET_NAME is not set."}
            ),
        }

    BUCKET = S3_BUCKET_NAME
    logger.info(f"Using S3 Bucket: {BUCKET}")

    try:
        if 'body' in event and event['body']:
            payload = json.loads(event['body'])
        else:
            payload = event

        # --- 1. Extract Required Fields ---
        eventName = payload['eventName']
        user = payload['user']
        template_s3_key = payload['template_s3_key']
        pdf_filename = payload['pdf_filename']
        variable_substitutions = payload.get('variableSubstitutions', {})

        # --- 2. Extract Optional/Dynamic Fields (Background/Font Color) ---
        background_color = payload.get('background_color', 'white')
        font_color = payload.get('font_color', 'black')
        
        # --- NEW: Extract breakfast boolean, default to False ---
        breakfast_required = payload.get('breakfast', False)

        # Add dynamic fields to the substitution dictionary
        variable_substitutions['background_color'] = background_color
        variable_substitutions['font_color'] = font_color
        
        # --- NEW: Set indicator string for HTML template ---
        variable_substitutions['breakfast_indicator'] = 'B' if breakfast_required else ''

        logger.info(
            f"Input details: EventName={eventName}, User={user}, Filename={pdf_filename}, TemplateKey={template_s3_key}, BackgroundColor={background_color}, FontColor={font_color}, BreakfastRequired={breakfast_required}"
        )

        # --- 3. Determine S3 Output Key ---
        FINAL_OUTPUT_KEY = (
            f"{eventName.replace(' ', '_')}-{user}/{pdf_filename}"
        )
        logger.info(
            f"Determined full S3 output path (key): {FINAL_OUTPUT_KEY}"
        )

        # --- 4. Fetch Template from S3 ---
        logger.info(
            f"Fetching template from S3 Key: {template_s3_key}"
        )
        s3_object = s3_client.get_object(
            Bucket=BUCKET, Key=template_s3_key
        )
        html_content = s3_object['Body'].read().decode('utf-8')

        # --- 5. Perform Variable Substitution ---
        logger.info(
            f"Performing variable substitutions: {list(variable_substitutions.keys())}"
        )
        for key, value in variable_substitutions.items():
            # Escape percent signs in values before substitution
            if isinstance(value, str):
                escaped_value = value.replace('%', '%%') 
            else:
                escaped_value = str(value)
                
            html_content = html_content.replace(f"{{ {key} }}", escaped_value)


        logger.info("Variable substitution complete. Starting PDF generation...")

        # --- 6. Generate PDF ---
        html = HTML(string=html_content, base_url=f"s3://{BUCKET}/")
        pdf_bytes = html.write_pdf()

        # --- 7. Upload to S3 ---
        logger.info(f"Uploading generated PDF (size: {len(pdf_bytes)} bytes) to S3...")
        s3_client.put_object(
            Bucket=BUCKET,
            Key=FINAL_OUTPUT_KEY,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )
        logger.info("PDF successfully uploaded to S3.")

        # --- 8. Base64 Encode and Return ---
        pdf_base64_string = base64.b64encode(pdf_bytes).decode("utf-8")

        logger.info(
            "PDF Base64 encoding complete. Returning success response."
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "PDF generated and uploaded successfully.",
                    "s3_path": f"s3://{BUCKET}/{FINAL_OUTPUT_KEY}",
                    "pdf_base64": pdf_base64_string,
                }
            ),
        }

    except KeyError as e:
        logger.error(f"Missing required field in payload: {e}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required field in payload: {e}"}),
        }
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal Server Error: {e}"}),
        }
