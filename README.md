# CampusFix — Smart Campus Maintenance System

**ICT5205 Assignment 3 | AWS Distributed Application Prototype**

**Project status:** Successfully deployed and functionally tested on AWS.

## 1. Project Overview

CampusFix is a cloud-based maintenance reporting application developed as an academic prototype for ICT5205 Assignment 3.

The system allows students and campus users to report maintenance issues, optionally upload supporting photographs, and track issue progress using a unique tracking ID.

Authorised maintenance staff can access a protected dashboard, review submitted requests, and update their status.

The application uses AWS serverless and managed services to demonstrate a distributed architecture with asynchronous notifications, cloud storage, authentication, monitoring, and Infrastructure as Code.

## 2. Live Application

**Website:** https://dy5mpxcnbr23i.cloudfront.net

**Source repository:** https://github.com/MRDarkkk/ICT5205-CampusFix

The public reporting and tracking interface can be accessed through the website.

Administrative features require authorised staff credentials, which are not published in this repository.

The deployed demonstration may be taken offline after assessment to avoid ongoing AWS costs.

## 3. AWS Architecture

CampusFix uses the following AWS services:

- **Amazon CloudFront:** HTTPS delivery of the frontend application.
- **Amazon S3:** Private storage for website files and uploaded maintenance photographs.
- **Amazon API Gateway:** HTTP API for application operations.
- **AWS Lambda:** Serverless processing of maintenance requests and background notifications.
- **Amazon DynamoDB:** Storage of maintenance issues and notification event records.
- **Amazon Cognito:** Authentication for authorised maintenance staff.
- **Amazon SQS:** Asynchronous notification processing using a main queue and dead-letter queue.
- **Amazon SNS:** Email notifications to a confirmed subscriber.
- **Amazon CloudWatch:** Application logs and operational monitoring.
- **AWS IAM:** Service permissions and access controls.
- **AWS SAM / CloudFormation:** Repeatable infrastructure deployment.

### Application Workflow

1. A student submits a maintenance issue using the public web application.
2. API Gateway invokes the backend Lambda function.
3. The maintenance record is stored in DynamoDB.
4. The student receives a unique tracking ID for checking progress.
5. Optional photographs are uploaded to private S3 storage.
6. Notification messages are processed asynchronously through SQS and a worker Lambda function.
7. Amazon SNS sends an email notification to the confirmed subscriber.
8. Authorised staff access the dashboard and update issue status.
9. Students can track the updated issue status using their tracking ID.

## 4. API Endpoints

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/issues` | Public | Submit a maintenance issue |
| GET | `/issues/{id}` | Public | Track an issue using its unique ID |
| POST | `/uploads/presign` | Public | Obtain a presigned upload for an optional photo |
| GET | `/admin/issues` | Staff only | Retrieve recent maintenance issues |
| PATCH | `/admin/issues/{id}` | Staff only | Update issue status |
| GET | `/admin/issues/{id}/photo` | Staff only | Obtain temporary access to a private photograph |

Administrative endpoints are protected using Cognito JWT authentication and server-side staff group checks.

## 5. Implementation and Testing

CampusFix was deployed to AWS in the Sydney region (`ap-southeast-2`) using AWS SAM and CloudFormation.

The CloudFormation stack reached **CREATE_COMPLETE**.

The recorded testing evidence includes:

- 18 automated tests passed in the captured pytest execution.
- Successful submission of maintenance requests.
- Successful tracking of issues using generated tracking IDs.
- Staff dashboard access and issue status updates.
- Issue progression through Open, In Progress, and Resolved.
- Validation of invalid requests and missing records.
- Authentication and access-control checks for protected routes.
- Private S3 photograph access through temporary authorised URLs.
- Successful asynchronous processing of notification messages.
- Successful delivery of a CampusFix maintenance notification email through Amazon SNS.
- CloudWatch evidence confirming notification-worker execution.

These results demonstrate functional behaviour in the tested scenarios. They do not establish comprehensive performance, load-testing, or production-readiness guarantees.

## 6. Automated Tests

The backend uses Python 3.13.

To run the offline automated tests after installing the development dependencies:

```bash
python -m pip install -r tests/requirements-dev.txt
python -m compileall -q code/backend
python -m pytest -q tests
```

The automated tests use mocked AWS clients and do not require a live AWS deployment.

## 7. Repository Structure

```text
ICT5205-CampusFix/
├── code/
│   ├── backend/
│   └── frontend/
├── deploy/
│   ├── template.yaml
│   ├── deploy.sh
│   ├── publish-frontend.sh
│   └── DEPLOYMENT_GUIDE.md
├── documentation/
│   ├── USER_MANUAL.md
│   ├── EVIDENCE_REGISTER.md
│   └── REVIEW_STATUS.md
├── images/
├── tests/
├── .gitignore
└── README.md
```

The `images/` folder contains selected screenshots documenting the deployed application, AWS infrastructure, automated tests, and notification processing.

## 8. Deployment Instructions

The deployment configuration and supporting scripts are available in the `deploy/` folder.

Read `deploy/DEPLOYMENT_GUIDE.md` before attempting deployment.

Deployment requires an appropriately configured AWS account, suitable IAM permissions, and the necessary AWS SAM tooling.

AWS services may incur charges. Do not deploy the infrastructure without appropriate authorisation and cost monitoring.

## 9. Security Controls

CampusFix incorporates:

- Cognito authentication for staff.
- Server-side authorisation for protected administrative operations.
- Private S3 photograph storage.
- Temporary presigned URLs for controlled photo access.
- IAM permissions scoped to application requirements.
- HTTPS website delivery through CloudFront.
- SQS dead-letter queue configuration.
- CloudWatch logging and monitoring.

Credentials, access tokens, and passwords are not intentionally included in the public repository.

Maintenance tracking IDs should be treated as confidential.

## 10. Documentation and Evidence

Supporting materials are available in:

- `documentation/USER_MANUAL.md` — instructions for using CampusFix.
- `documentation/EVIDENCE_REGISTER.md` — evidence documentation.
- `documentation/REVIEW_STATUS.md` — implementation review notes.
- `images/` — screenshots of the application, infrastructure, testing, and notifications.

The final assessment submission includes separate reporting and presentation deliverables as required by the ICT5205 assessment instructions.

## 11. Project Scope and Limitations

CampusFix is an educational prototype, not an official university maintenance or emergency reporting service.

Although core workflows and security checks have been tested, the application has not been independently security audited or comprehensively load tested.

The system demonstrates the practical integration of AWS managed services in a distributed application architecture.
