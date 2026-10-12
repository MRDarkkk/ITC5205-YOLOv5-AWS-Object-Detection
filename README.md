# ITC5205 Assignment 2 — Object Detection with YOLOv5 on AWS

## About this project

For this assignment, I built an image object detection system using **YOLOv5n** and several AWS services. The idea was to take an image already stored in Amazon S3, identify the objects in it, and keep both the visual result and the detection details in the cloud.

The process starts when an authorised user sends an image key to **Amazon API Gateway**. API Gateway passes that request to an **AWS Lambda** function running inside a Docker container. The function reads the image from S3, uses YOLOv5n to detect objects, and creates an image with bounding boxes around them. It then saves that annotated image and a JSON results file in S3. Basic information about the detections is also recorded in **Amazon DynamoDB**. I used **Amazon CloudWatch** to check what happened during testing and to investigate errors and response times.

I used the pretrained YOLOv5n model and the original Ultralytics YOLOv5 code. **I did not train a new detection model for this assignment.** My work focused on getting the model running as part of an AWS-based application and testing the complete process.

My student details are in `readme.txt`.

## How the system works

```text
Authenticated client (AWS Signature Version 4)
                  |
                  v
Amazon API Gateway — HTTP API, POST /detect, AWS_IAM authorization
                  |
                  v
AWS Lambda — Python 3.12 container, YOLOv5n running on CPU
          |                     |
          v                     v
Amazon S3                   Amazon DynamoDB
input/ images               detection_id (partition key)
output/ annotated JPEGs     source_image, labels,
output/ results JSON        object_count, output references

Deployment: AWS CodeBuild -> Amazon ECR -> AWS Lambda
Monitoring: Amazon CloudWatch
```

I separated image storage from processing. S3 holds the input and output files, while DynamoDB stores the smaller pieces of information that describe each detection. The Lambda function handles the image processing, so I did not need to keep an EC2 server running for inference.

## What's in this repository?

```text
code/lambda_function.py      Lambda request handling, detection and storage logic

deploy/Dockerfile            Instructions for building the Lambda container
deploy/requirements.txt      boto3 dependency

buildspec.yml                AWS CodeBuild commands (kept at the repository root)
.dockerignore                Files excluded from the Docker build context
.gitignore                   Files excluded from Git

yolov5/                     Original Ultralytics YOLOv5 source code
yolov5n.pt                   Pretrained YOLOv5n model weights
images/                      Assignment screenshots and figures
readme.txt                   Student details and brief project description
```

**One important detail:** the Docker build has to run from the **repository root**, not from inside `deploy/`. The Dockerfile needs access to `code/`, `deploy/`, `yolov5/` and `yolov5n.pt` in their current locations.

## Tools and AWS configuration

I used **Python 3.12**, PyTorch on CPU, YOLOv5n, Pillow and OpenCV for the detection part of the project. The AWS services used were **Lambda, API Gateway, S3, DynamoDB, ECR, CodeBuild, CloudWatch and IAM**.

The deployment I tested used these settings:

| Setting | Value |
|---|---|
| AWS Region | `ap-southeast-2` (Sydney) |
| Lambda function | `itc5205-yolov5-detector` |
| Lambda memory | 2,048 MB |
| Lambda timeout | 180 seconds |
| Lambda temporary storage | 1,024 MB |
| ECR repository | `itc5205-yolov5-lambda` |
| DynamoDB table | `itc5205-yolov5-detections` |

These are the settings from my implementation, not necessarily the only settings that would work. Some Python packages in the Dockerfile are not pinned to exact versions, so rebuilding the image at a later date could install different versions. That is something I would check before deploying the project again.

## Sending an image for detection

The API accepts the **S3 key of an existing image**. The user does not upload the actual image bytes in the API request.

Example request body:

```json
{"image_key": "input/people.png"}
```

The Lambda code accepts `.jpg`, `.jpeg` and `.png` files stored under `input/`. It also checks that an image is no larger than **5 MB** or **20 million pixels**.

If everything works, the API responds with **HTTP 200** and information such as the `detection_id`, the source image, object labels, confidence scores, bounding-box coordinates, and the number of detected objects. It also returns the S3 locations of the output files.

For each successful request, the system creates:

- `output/<detection_id>_annotated.jpg` — the image with detected objects marked on it.
- `output/<detection_id>_results.json` — the detailed detection results.
- A DynamoDB record using `detection_id` as its key, when `DDB_TABLE` is configured.

I also tested how the application responds to incorrect requests. It returns **HTTP 400** for invalid image keys or malformed JSON, **HTTP 404** when an S3 image is missing and the required bucket permission is available, and **HTTP 413** for images that exceed the configured limits.

## How to deploy the project

These are the main steps I followed. The final assignment report provides the more detailed developer manual, including configuration screenshots and troubleshooting notes. Anyone reproducing the project should use their **own AWS account, IAM roles and resource names**. AWS credentials should never be saved in this repository.

1. **Set up S3.** Create a private bucket in your chosen AWS Region, keep public access blocked, and upload sample images inside `input/`. Outputs will be written under `output/`.
2. **Create the DynamoDB table.** Use `detection_id` as the partition key with type **String**. My table used on-demand capacity.
3. **Create an ECR repository.** This will store the Docker container image used by Lambda.
4. **Prepare the CodeBuild source ZIP.** Zip the *contents* of the repository root, rather than the parent folder. `buildspec.yml`, `code/`, `deploy/`, `yolov5/`, `yolov5n.pt` and `.dockerignore` must appear at the top level inside the ZIP. Upload that ZIP to S3.
5. **Set up AWS CodeBuild.** Use a Linux x86_64 build environment with Docker available and **privileged mode enabled**. The CodeBuild role needs access to the source ZIP, permission to write logs and permission to push the image to ECR. The included `buildspec.yml` builds the container and pushes image tag `v1`.
6. **Create the Lambda function.** Choose **Container image** and select the image pushed to ECR. The handler is configured through the Dockerfile. In my deployment, I set memory to **2,048 MB**, timeout to **180 seconds**, and temporary storage to **1,024 MB**. Set these environment variables:

   ```text
   S3_BUCKET=<YOUR_PRIVATE_BUCKET_NAME>
   DDB_TABLE=<YOUR_DYNAMODB_TABLE_NAME>
   ```

7. **Configure the Lambda execution role.** It needs CloudWatch logging permissions, S3 `GetObject` for `input/*`, S3 `PutObject` for `output/*`, and DynamoDB `PutItem` for the table. I also added S3 `ListBucket` for the bucket after testing showed that a nonexistent object was returning an unhelpful error. Keep permissions limited to the resources the application actually uses.
8. **Create API Gateway.** Set up an **HTTP API** with a `POST /detect` route connected to the Lambda function using payload format **2.0**. Enable `AWS_IAM` authorisation, ensure API Gateway has permission to invoke Lambda, and deploy the API stage.
9. **Check the full workflow.** Send an authenticated request, confirm that Lambda runs, then check the annotated image and JSON result in S3 and the corresponding record in DynamoDB. CloudWatch is useful if something fails.

### API address and authentication

The endpoint used in my implementation was:

```text
POST https://pw9nkfiete.execute-api.ap-southeast-2.amazonaws.com/detect
```

This endpoint **does not allow anonymous requests**. Requests must be signed using **AWS Signature Version 4 (SigV4)** by an AWS identity with permission to invoke the API. Do not share access keys or session tokens.

For troubleshooting, the Lambda function can also be invoked directly with the AWS CLI, provided the caller has `lambda:InvokeFunction` permission:

```bash
aws lambda invoke \
  --region ap-southeast-2 \
  --function-name itc5205-yolov5-detector \
  --cli-binary-format raw-in-base64-out \
  --payload '{"image_key":"input/people.png"}' \
  /tmp/itc5205-response.json
cat /tmp/itc5205-response.json
```

**A direct Lambda invocation is not the same as an API Gateway test.** To test the actual API integration, send an HTTP `POST` request with the JSON body shown above and sign it for the AWS service `execute-api` in the selected Region.

## What happened during testing?

I tested the application with three sample images showing vehicles, people and animals. I also checked API authentication, invalid requests, cold and warm Lambda runs, and a small concurrent-request test.

| Test | What I observed |
|---|---|
| Authenticated API request | HTTP `200`; results stored in S3 and DynamoDB |
| Request without AWS authentication | HTTP `403` |
| Invalid image key | HTTP `400` |
| Malformed JSON | HTTP `400` |
| Image missing from S3 | HTTP `404` after the IAM permission adjustment |
| First measured API request | 7.559 seconds |
| Next warm API request | 0.442 seconds |
| Highest Lambda concurrency recorded | `3` executions |
| Lambda throttles in the observed interval | `0` |
| Three concurrent client requests | Two received HTTP `200`; one timed out after 30 seconds |

CloudWatch showed that the Lambda execution linked to the timed-out request **still completed detection**, but took about **33.93 seconds**. This was one of the more useful findings because it showed that successful backend processing does not always mean the client receives a response on time.

The cold/warm comparison also made a clear difference in this small test. The first measured request took 7.559 seconds, compared with 0.442 seconds for the following warm request. This fits what I saw in the logs: loading the model in a new Lambda environment takes extra time, while a reused environment can process the next image more quickly.

These measurements come from **a small number of tests**, not a large benchmark. They show that the system works with overlapping requests, but they do not prove that it would handle high traffic without delays.

## Problems I ran into

A few issues came up while building and testing the application:

- **Building the Lambda container:** the application needed YOLOv5 and its Python dependencies inside a container image. I used AWS CodeBuild to build that image and pushed it to ECR before connecting it to Lambda.
- **Missing S3 image returned HTTP 500:** my Lambda code already had a response for a missing object, but S3 was not returning the expected missing-object error. After adding the required bucket-level `s3:ListBucket` permission to the Lambda role, the API returned the more useful **HTTP 404** response.
- **Different cold and warm response times:** the model took longer to load in a fresh Lambda execution environment. I confirmed this by comparing API timings with CloudWatch execution reports.
- **One request timed out during concurrency testing:** when I sent three requests together, two returned successfully and the third exceeded the 30-second client timeout. CloudWatch confirmed that all three Lambda executions finished detection, so the main issue was response time rather than recorded Lambda throttling.

I have left these findings in the documentation because they explain what I actually tested and where the current system still has limitations.

## Quick troubleshooting notes

| Issue | First thing to check |
|---|---|
| API returns `403` | The caller's IAM permission and SigV4 signing for `execute-api` |
| API returns `400` | JSON format and whether the key looks like `input/car.png` |
| An image returns `404` | Whether that object exists in S3 and the Lambda role has the relevant access |
| API returns `500` | The Lambda logs in `/aws/lambda/itc5205-yolov5-detector`, permissions and environment variables |
| Docker/CodeBuild fails | ZIP structure, Docker privileged mode, ECR push permission and package downloads |
| First detection is slow | Lambda initialisation and time taken to load YOLOv5 |
| Client times out | Client and API timeout limits, plus the actual Lambda execution duration |

## Images, model and attribution

The sample images used for this assignment were `car.png`, `people.png` and `animals.png`. They were **AI-generated test images**, not part of a public benchmark dataset. For that reason, the results should be understood as functional tests rather than evidence of the model's accuracy on a recognised dataset.

YOLOv5 and the pretrained model weights come from **Ultralytics**:

- Original project: https://github.com/ultralytics/yolov5
- Licence and notices: see `yolov5/LICENSE` and the original project repository.

I have kept the original YOLOv5 source and attribution files in the project. The model and the upstream source code should not be mistaken for work I created myself.

## Security and AWS usage

I kept the S3 bucket and ECR repository private, and configured API Gateway to require IAM authorisation. The repository should not contain AWS access keys, session tokens, private keys or screenshots showing secrets.

AWS services can generate charges, particularly when building images or running repeated inference tests. Resource usage and cleanup need to be checked separately after submission.

## Other assignment files

This repository provides the code and deployment configuration. The assignment also requires a technical report with the architecture, developer and user manuals, testing evidence, reflection answers and references; an `images/` folder containing report figures; a separate full source-code document; and a recorded presentation link. Those items are prepared as separate submission materials where required.
