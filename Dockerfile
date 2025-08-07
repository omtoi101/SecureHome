# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# - build-essential and cmake are needed for dlib (a dependency of face_recognition)
# - libgl1-mesa-glx and libglib2.0-0 are needed for opencv-python
# - ffmpeg is required for video processing
# - v4l-utils provides tools for video4linux, which can be useful for debugging
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# We install numpy first as it's a build dependency for other packages
RUN pip install --no-cache-dir numpy
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create directories that the application uses for output
RUN mkdir -p /app/logs \
             /app/clipped \
             /app/screenshots \
             /app/images

# Expose port 8040 to the outside world
EXPOSE 8040

# Run run.py when the container launches
CMD ["python", "run.py"]
