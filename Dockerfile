FROM python:3.9-slim

# Set environment variables to avoid Python buffering output
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt first and install dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code into the container
COPY ./app .

# Expose the FastAPI default port
EXPOSE 8000

# Command to run the FastAPI app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
