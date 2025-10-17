# Start with the official AWS Python 3.12 base image
FROM public.ecr.aws/lambda/python:3.12

# Install the system dependencies (Pango, Cairo, etc.)
# We use dnf (Amazon Linux 2023) to get these packages.
# --nodocs reduces the final image size.
RUN dnf install -y \
    cairo-devel \
        pango-devel \
	    gdk-pixbuf2-devel \
	        libffi-devel \
		    # Clean up dnf cache to keep the image small
		        && dnf clean all \
			    && rm -rf /var/cache/dnf

# Copy your Python application code into the container
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Install Python dependencies (WeasyPrint)
# Since the system libraries are installed, this step will now work correctly.
RUN pip install weasyprint

# Set the CMD to your function handler
CMD [ "lambda_function.lambda_handler" ]
