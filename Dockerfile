# Use an official Python runtime as a parent image
FROM python:3.10-slim

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y ffmpeg

# Set up the working directory
WORKDIR /app

# Copy only the requirements files to the working directory
COPY pyproject.toml poetry.lock /app/

# Install Poetry
RUN pip install poetry

# Install project dependencies using Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy the application code to the container
COPY . /app/

# Change permissions for the 'speech/main.py' file
RUN chmod +x /app/speech/main.py

# Specify the command to run on container start
CMD ["poetry", "run", "python3", "speech/main.py"]
