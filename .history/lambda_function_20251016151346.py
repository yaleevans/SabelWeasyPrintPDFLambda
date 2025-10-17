import json
import base64
from weasyprint import HTML
from io import BytesIO
import logging

# Set up logging for CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Lambda execution started.")
    w = 3

    try:
        # 1. Parse the JSON body from the API Gateway event
        body_string = event.get("body")
        if not body_string:
            logger.error("No request body found.")
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing request body."}),
            }

        # API Gateway proxy integration base64 encodes the body, so we need to decode it first
        if event.get("isBase64Encoded", False):
            body_string = base64.b64decode(body_string).decode("utf-8")

        body = json.loads(body_string)
        logger.info(f"Parsed request body keys: {list(body.keys())}")

        # 2. Extract data for the PDF
        document_title = body.get("document_title", "Report")
        notes_text = body.get("notes_text", "No notes provided.")
        # Ensure the background color is correctly extracted
        background_color = body.get("pdf_background_color", "#FFFFFF")
        transaction_id = body.get("transactionId", "N/A")

        # 3. Create the HTML source
        source_html = f"""
        <html>
        <head>
            <style>
                @page {{ size: A4; margin: 1cm; }}
                body {{ font-family: sans-serif; background-color: {background_color}; }}
                h1 {{ color: #333; }}
                .notes {{ margin-top: 20px; padding: 10px; border: 1px solid #ccc; }}
            </style>
        </head>
        <body>
            <h1>{document_title}</h1>
            <p><strong>Transaction ID:</strong> {transaction_id}</p>
            <div class="notes">{notes_text}</div>
        </body>
        </html>
        """
        logger.info("HTML source generated.")

        # 4. Convert HTML to PDF using WeasyPrint
        pdf_bytes = HTML(string=source_html).write_pdf()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/pdf",
                "Content-Disposition": 'attachment; filename="UpdatedReport.pdf"',
                # Add CORS header if needed for browser clients
                "Access-Control-Allow-Origin": "*",
            },
            "body": base64.b64encode(pdf_bytes).decode(
                "utf-8"
            ),  # The Base64-encoded PDF
            "isBase64Encoded": True,  # <--- THIS FLAG IS CRUCIAL
        }

    except Exception as e:
        logger.error(f"An unhandled error occurred: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Internal Server Error: {str(e)}"}),
        }
