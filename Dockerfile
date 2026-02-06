FROM pytorch/pytorch:2.10.0-cuda13.0-cudnn9-devel

WORKDIR /app

# in order to leverage the preinstalled packages in the base image, 
# we need to install the dependencies with --break-system-packages
# uv will not help here, so we need to repeat the dependencies
RUN pip install --break-system-packages \
    "garak==0.13.3" \
    "gradio>=5.0.0" \
    "guidellm>=0.5.3" \
    "nemoguardrails>=0.20.0" \
    "openai>=1.45.0,<2" \
    "python-dotenv[cli]"

COPY railyard/ railyard/
COPY app.py .

EXPOSE 7860

ENV PYTHONPATH=/app
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

CMD ["python", "app.py"]