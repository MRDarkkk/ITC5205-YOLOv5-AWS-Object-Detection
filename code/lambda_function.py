"""AWS Lambda handler for ITC5205 YOLOv5 image object detection.

Request JSON (API Gateway or direct Lambda test):
    {"image_key": "input/car.jpg"}

Required environment variable: S3_BUCKET
Optional environment variable: DDB_TABLE (enable after DynamoDB is created)

The deployment container must include:
    /var/task/code/lambda_function.py  (this file)
    /var/task/yolov5/                  (pinned official YOLOv5 repository)
    /var/task/yolov5n.pt               (pretrained model weights)
"""

import io
import json
import logging
import os
import uuid
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from PIL import Image, UnidentifiedImageError

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

S3 = boto3.client("s3")
DYNAMODB = boto3.resource("dynamodb")
APP_ROOT = Path(__file__).resolve().parent.parent
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def _response(status_code, payload):
    """Return a JSON response compatible with API Gateway HTTP API."""
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload),
    }


def _request_image_key(event):
    """Get image_key from a direct Lambda event or API Gateway JSON body."""
    request = event if isinstance(event, dict) else {}
    if "body" in request:
        body = request["body"]
        if isinstance(body, str):
            try:
                request = json.loads(body)
            except json.JSONDecodeError as exc:
                raise ValueError("Request body must contain valid JSON") from exc
        elif isinstance(body, dict):
            request = body
        else:
            raise ValueError("Request body must be a JSON object")

    if not isinstance(request, dict):
        raise ValueError("Request body must be a JSON object")
    key = request.get("image_key")
    if not isinstance(key, str) or not key.startswith("input/") or key.endswith("/"):
        raise ValueError("image_key must be an S3 object under input/")
    if any(part in ("", ".", "..") for part in key.split("/")):
        raise ValueError("image_key contains an invalid path segment")
    if not key.lower().endswith((".jpg", ".jpeg", ".png")):
        raise ValueError("Only JPEG and PNG images are supported")
    return key


@lru_cache(maxsize=1)
def _load_model():
    """Load YOLOv5n only once per Lambda execution environment."""
    import torch

    repo_path = APP_ROOT / "yolov5"
    weights_path = APP_ROOT / "yolov5n.pt"
    if not repo_path.is_dir() or not weights_path.is_file():
        raise RuntimeError("YOLOv5 repository or model weights missing from container")

    LOGGER.info("Loading YOLOv5n model from packaged files")
    model = torch.hub.load(
        str(repo_path), "custom", path=str(weights_path), source="local", device="cpu"
    )
    model.conf = 0.25
    model.eval()
    return model


def lambda_handler(event, context):
    """Detect objects in a private S3 image and save annotated output."""
    try:
        bucket = os.environ.get("S3_BUCKET")
        if not bucket:
            raise RuntimeError("S3_BUCKET environment variable is missing")

        image_key = _request_image_key(event)
        LOGGER.info("Processing image key: %s", image_key)

        source_object = S3.get_object(Bucket=bucket, Key=image_key)
        if source_object.get("ContentLength", 0) > MAX_IMAGE_BYTES:
            return _response(413, {"error": "Image exceeds the 5 MB limit"})
        image_bytes = source_object["Body"].read(MAX_IMAGE_BYTES + 1)
        if len(image_bytes) > MAX_IMAGE_BYTES:
            return _response(413, {"error": "Image exceeds the 5 MB limit"})

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            LOGGER.warning("Image could not be decoded: %s", exc)
            return _response(400, {"error": "The uploaded object is not a valid image"})

        if image.width * image.height > MAX_IMAGE_PIXELS:
            return _response(413, {"error": "Image dimensions are too large"})

        model = _load_model()
        predictions = model(image, size=640)
        names = predictions.names
        detections = []
        for x1, y1, x2, y2, confidence, class_id in predictions.xyxy[0].cpu().tolist():
            label = names[int(class_id)]
            detections.append({
                "label": label,
                "confidence": round(float(confidence), 4),
                "box_xyxy": [round(float(value), 2) for value in (x1, y1, x2, y2)],
            })

        # YOLOv5 draws the predicted bounding boxes onto the image.
        annotated = Image.fromarray(predictions.render()[0]).convert("RGB")
        annotated_buffer = io.BytesIO()
        annotated.save(annotated_buffer, format="JPEG", quality=90)

        detection_id = uuid.uuid4().hex
        annotated_key = f"output/{detection_id}_annotated.jpg"
        result_key = f"output/{detection_id}_results.json"
        result = {
            "detection_id": detection_id,
            "source_image": image_key,
            "annotated_image": annotated_key,
            "detections": detections,
            "object_count": len(detections),
        }

        S3.put_object(
            Bucket=bucket, Key=annotated_key,
            Body=annotated_buffer.getvalue(), ContentType="image/jpeg",
        )
        S3.put_object(
            Bucket=bucket, Key=result_key,
            Body=json.dumps(result, indent=2).encode("utf-8"),
            ContentType="application/json",
        )

        # DynamoDB integration is activated later by setting DDB_TABLE.
        table_name = os.environ.get("DDB_TABLE")
        if table_name:
            DYNAMODB.Table(table_name).put_item(Item={
                "detection_id": detection_id,
                "source_image": image_key,
                "annotated_image": annotated_key,
                "result_json": result_key,
                "object_count": len(detections),
                "labels": [item["label"] for item in detections],
            })
        else:
            LOGGER.info("DDB_TABLE is unset; skipping DynamoDB until configured")

        LOGGER.info("Detection complete: %s objects, ID=%s", len(detections), detection_id)
        return _response(200, {**result, "result_json": result_key})

    except ValueError as exc:
        LOGGER.warning("Invalid request: %s", exc)
        return _response(400, {"error": str(exc)})
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code in ("NoSuchKey", "404"):
            return _response(404, {"error": "Image not found in S3"})
        LOGGER.exception("AWS service request failed")
        return _response(500, {"error": "AWS service request failed; check CloudWatch logs"})
    except Exception:
        LOGGER.exception("Object detection failed")
        return _response(500, {"error": "Image processing failed; check CloudWatch logs"})
