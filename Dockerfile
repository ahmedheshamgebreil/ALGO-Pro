# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port that Streamlit will run on
EXPOSE 8501

# Healthcheck to ensure the container is running correctly
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Command to run the application
ENTRYPOINT ["streamlit", "run", "app_updated.py", "--server.port=8501", "--server.address=0.0.0.0"]
