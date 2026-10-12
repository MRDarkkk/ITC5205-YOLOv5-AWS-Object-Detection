ITC5205 – Assignment 2
Project: Image Object Identification System Using YOLOv5 and AWS

Student Name: Vishesh
Student Number: 240400

Project Description:

This project implements an image object identification system using the pretrained YOLOv5n model and AWS cloud services.

Users can submit an image stored in Amazon S3 through a secure API Gateway endpoint. AWS Lambda processes the image using YOLOv5, identifies objects, and generates an annotated image containing bounding boxes and labels.

The annotated image and detection results are saved in Amazon S3, while detection information is recorded in Amazon DynamoDB.

AWS CodeBuild and Amazon ECR were used to build and deploy the containerised Lambda application. Amazon CloudWatch was used to monitor execution performance, errors and concurrent requests.

Main Technologies:
- Python and PyTorch
- YOLOv5n
- AWS Lambda
- Amazon API Gateway
- Amazon S3
- Amazon DynamoDB
- Amazon ECR and CodeBuild
- Amazon CloudWatch

Project Files:
- code/: Lambda application source code
- deploy/: Docker and dependency configuration
- yolov5/: YOLOv5 source repository
- yolov5n.pt: Pretrained model weights
- buildspec.yml: AWS CodeBuild configuration
- images/: Project screenshots and supporting figures

Note: The API requires AWS IAM authentication. YOLOv5 is developed by Ultralytics, and its original licensing and attribution files are retained.