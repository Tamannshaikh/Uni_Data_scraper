FROM python:3.12-slim

# 1. Copy and install Python requirements first
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 2. Set Playwright path to a shared, accessible directory
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN mkdir -p /ms-playwright && chmod 777 /ms-playwright

# 3. Install Playwright OS dependencies and browser as root
RUN playwright install-deps chromium && \
    playwright install chromium

# 4. Hugging Face Spaces require running as a non-root user with UID 1000
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /home/user/app

# 5. Copy application files and change ownership
COPY --chown=user . .

ENV PORT=7860
EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
