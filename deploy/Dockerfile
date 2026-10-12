# ITC5205 Assignment 2: YOLOv5n inference using an AWS Lambda container image.
# Build context MUST be D:\ITC5205\lambda-app (not the deploy folder).
FROM public.ecr.aws/lambda/python:3.12

# The Lambda filesystem is read-only outside /tmp during invocation.
ENV PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache \
    MPLCONFIGDIR=/tmp/matplotlib \
    YOLO_CONFIG_DIR=/tmp/Ultralytics \
    PYTHONPATH=${LAMBDA_TASK_ROOT}/code

# OpenCV needs these Linux runtime libraries on the Lambda AL2023 base image.
RUN dnf install -y mesa-libGL glib2 && dnf clean all

COPY deploy/requirements.txt /tmp/lambda-requirements.txt
COPY yolov5/requirements.txt /tmp/yolov5-requirements.txt

# CPU wheels only: no CUDA/GPU libraries are required by Lambda.
RUN python -m pip install --no-cache-dir torch torchvision \
      --index-url https://download.pytorch.org/whl/cpu
RUN python -m pip install --no-cache-dir \
      -r /tmp/yolov5-requirements.txt \
      -r /tmp/lambda-requirements.txt \
    && python -m pip check

# Match the directory paths expected by code/lambda_function.py.
COPY code/ ${LAMBDA_TASK_ROOT}/code/
COPY yolov5/ ${LAMBDA_TASK_ROOT}/yolov5/
COPY yolov5n.pt ${LAMBDA_TASK_ROOT}/yolov5n.pt

# Check Python syntax and core packages at build time. AWS clients are initialised
# only at Lambda runtime, when the AWS Region is supplied by Lambda.
RUN python -m py_compile ${LAMBDA_TASK_ROOT}/code/lambda_function.py \
    && python -c "import torch, cv2, boto3; print('Lambda dependencies imported')"

CMD ["lambda_function.lambda_handler"]
