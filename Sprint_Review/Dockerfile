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
COPY database.py keys.py redis_client.py sprint_review.py .env /usr/src/app/

ENTRYPOINT ["python3"]
# Run sprint_review.py when the container launches
CMD ["sprint_review.py"]
