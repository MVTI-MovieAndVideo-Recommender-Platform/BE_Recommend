# Start with a base image containing Python runtime
FROM public.ecr.aws/lambda/python:3.10

# Install awscli
RUN pip install --no-cache-dir awscli

# Set working directory to the root
WORKDIR /

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app directory and lambda_function.py to /usr directory
COPY app /usr/app
COPY lambda_function.py /usr/lambda_function.py

# Define build arguments
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG SERVER_SECRET_KEY
ARG MYSQLDB_HOST
ARG MONGODB_HOST
ARG DB_USER
ARG DB_PWD
ARG MYSQLDB_NAME
ARG KAFKA_HOST

# Set environment variables using build arguments
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ENV SERVER_SECRET_KEY=${SERVER_SECRET_KEY}
ENV MYSQLDB_HOST=${MYSQLDB_HOST}
ENV MONGODB_HOST=${MONGODB_HOST}
ENV DB_USER=${DB_USER}
ENV DB_PWD=${DB_PWD}
ENV MYSQLDB_NAME=${MYSQLDB_NAME}
ENV KAFKA_HOST=${KAFKA_HOST}

# Create .env file with environment variables
RUN mkdir -p /usr/app && \
    echo "SERVER_SECRET_KEY=${SERVER_SECRET_KEY}" > /usr/app/.env && \
    echo "MYSQLDB_HOST=${MYSQLDB_HOST}" >> /usr/app/.env && \
    echo "MONGODB_HOST=${MONGODB_HOST}" >> /usr/app/.env && \
    echo "DB_USER=${DB_USER}" >> /usr/app/.env && \
    echo "DB_PWD=${DB_PWD}" >> /usr/app/.env && \
    echo "MYSQLDB_NAME=${MYSQLDB_NAME}" >> /usr/app/.env && \
    echo "KAFKA_HOST=${KAFKA_HOST}" >> /usr/app/.env

# Download files from S3 to the desired location
RUN mkdir -p /usr/app/resources/data && \
    aws s3 cp s3://mvti.site/resource/contents_embeddings_dict.pkl /usr/app/resources/data/contents_embeddings_dict.pkl && \
    aws s3 cp s3://mvti.site/resource/gbm_model.pkl /usr/app/resources/data/gbm_model.pkl && \
    aws s3 cp s3://mvti.site/resource/labse_model.h5 /usr/app/resources/data/labse_model.h5 && \
    aws s3 cp s3://mvti.site/resource/mbti_embeddings_dict.pkl /usr/app/resources/data/mbti_embeddings_dict.pkl && \
    aws s3 cp s3://mvti.site/resource/media_data.csv /usr/app/resources/data/media_data.csv

# Set the PYTHONPATH environment variable
ENV PYTHONPATH "${PYTHONPATH}:/usr:/usr/app"

# Lambda function handler
ENTRYPOINT [ "python3", "-m", "awslambdaric" ]
CMD ["lambda_function.lambda_handler"]
