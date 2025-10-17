import json
import os
import boto3
import base64
from weasyprint import HTML, CSS
import logging  # <-- NEW IMPORT

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
    logger.info(f"Received event payload: {event}")  # <-- LOG: Full incoming payload

    if not S3_BUCKET_NAME:
        logger.error("Lambda environment variable S3_BUCKET_NAME is not set.")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": "Lambda environment variable S3_BUCKET_NAME is not set."}
            ),
        }

    BUCKET = S3_BUCKET_NAME
    logger.info(f"Using S3 Bucket: {BUCKET}")  # <-- LOG: S3 Bucket Name

    try:
        if "body" in event and event["body"] is not None:
            # The body comes as a JSON string, so we must parse it into a Python dict
            payload = json.loads(event["body"])
        else:
            # Handle cases where the body might be empty or missing
            raise KeyError("Request body is empty or missing in the event.")

        logger.info(f"Successfully parsed request payload: {payload.keys()}")
        # --- 1. Define Input Parameters (FIXED) ---

        # Required inputs for dynamic folder name
        # FIX: Access payload instead of event
        EVENT_NAME = payload["eventName"]
        USER = payload["user"]

        # Filename input property
        # FIX: Access payload instead of event
        PDF_FILENAME = payload["pdf_filename"]

        # Other required and optional inputs
        # FIX: Access payload instead of event
        TEMPLATE_KEY = payload["template_s3_key"]
        DATA_MAPPING = payload.get("variableSubstitutions", {})  # .get() from payload
        BACKGROUND_COLOR = payload.get(
            "background_color", "white"
        )  # .get() from payload

        logger.info(
            f"Input details: EventName={EVENT_NAME}, User={USER}, Filename={PDF_FILENAME}, TemplateKey={TEMPLATE_KEY}, BackgroundColor={BACKGROUND_COLOR}"
        )

        # --- 2. Dynamically Construct Output Key Prefix ---
        OUTPUT_KEY_PREFIX = f"{EVENT_NAME}-{USER}/"
        FINAL_OUTPUT_KEY = f"{OUTPUT_KEY_PREFIX}{PDF_FILENAME}"

        logger.info(
            f"Determined full S3 output path (key): {FINAL_OUTPUT_KEY}"
        )  # <-- LOG: Full output key

        # --- 3. Fetch HTML Template & Inject Styling ---
        logger.info(
            f"Fetching template from S3 Key: {TEMPLATE_KEY}"
        )  # <-- LOG: Template fetch initiation
        s3_response = s3_client.get_object(Bucket=BUCKET, Key=TEMPLATE_KEY)
        html_content = s3_response["Body"].read().decode("utf-8")

        # --- 4. Dynamic Variable Replacement ---
        DATA_MAPPING["background_color"] = BACKGROUND_COLOR  # <-- ADD THIS LINE
        logger.info(
            f"BACKGROUND_COLOR: {BACKGROUND_COLOR}"
        )
        logger.info(
            f"Performing variable substitutions: {list(DATA_MAPPING.keys())}"
        )  # <-- LOG: Keys being substituted
        for key, value in DATA_MAPPING.items():
            placeholder = f"{{ {key} }}"
            html_content = html_content.replace(placeholder, str(value))
        logger.info("Variable substitution complete, html_content = %s", html_content)  # <-- LOG: Completion of substitution

        # --- 5. Generate PDF BYTES ---
        base_url = f"s3://{BUCKET}/"
        logger.info(
            f"Starting PDF generation using WeasyPrint with base_url: {base_url}"
        )
        pdf_bytes = HTML(string=html_content, base_url=base_url).write_pdf()

        # --- 6. Save PDF to Target S3 Location ---
        logger.info(
            f"Uploading generated PDF (size: {len(pdf_bytes)} bytes) to S3..."
        )  # <-- LOG: PDF size/upload
        s3_client.put_object(
            Bucket=BUCKET,
            Key=FINAL_OUTPUT_KEY,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )
        logger.info("PDF successfully uploaded to S3.")

        # --- 7. Base64 Encode and Return ---
        pdf_base64_string = base64.b64encode(pdf_bytes).decode("utf-8")

        logger.info(
            "PDF Base64 encoding complete. Returning success response."
        )  # <-- LOG: Final action

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "PDF generated and uploaded successfully.",
                    "s3_path": f"s3://{BUCKET}/{FINAL_OUTPUT_KEY}",
                    # The Base64 string is included, but we don't log the massive string itself.
                    "pdf_base64": pdf_base64_string,
                }
            ),
        }

    except KeyError as e:
        logger.error(f"Missing required field in payload: {e}")  # <-- ERROR LOG
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required field in payload: {e}"}),
        }
    except Exception as e:
        logger.error(
            f"An unexpected error occurred: {e}", exc_info=True
        )  # <-- DETAILED ERROR LOG
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
