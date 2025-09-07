FROM python:3.10-slim

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser

# Set working directory
WORKDIR /app

# Copy only dependency files first for caching
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full application
COPY . .

# Set permissions (optional)
RUN chown -R appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Default command
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
