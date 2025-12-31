# FROM public.ecr.aws/lambda/python:3.10

# RUN addgroup -S nonroot \
#     && adduser -S nonroot -G nonroot

# USER nonroot

# # Set environment variables for MySQL connection
# ENV db_endpoint=mysql_host
# ENV db_port=3306

# # Copy requirements.txt
# COPY requirements.txt ${LAMBDA_TASK_ROOT}

# # Install the specified packages
# RUN pip install -r requirements.txt

# # Copy function code
# COPY services  azure_scan.py common.py database.py db_handler.py  keys.py azures.py ${LAMBDA_TASK_ROOT}

# # Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
# CMD [ "azures.lambda_handler" ]


FROM public.ecr.aws/docker/library/python:3.10.14-bookworm

RUN addgroup -S nonroot \
    && adduser -S nonroot -G nonroot

USER nonroot

# Set environment variables for MySQL connection
ENV db_endpoint=mysql_host
ENV db_port=3306

# Set the working directory in the container
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# Copy only requirements.txt first to leverage Docker cache
COPY requirements.txt /usr/src/app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY invoices database.py email_notifier.py keys.py tenant_audit.py encryption.py html_table.py /usr/src/app/

ENTRYPOINT ["python3"]
# Run run.py when the container launches
CMD ["tenant_audit.py"]