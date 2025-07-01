# Fantasy Football SageMaker Pipeline

This document describes the SageMaker pipeline for automated fantasy football data collection.

## Overview

The pipeline automates the collection and processing of:
- **Sleeper API data**: League info, rosters, players, transactions, etc.
- **NFL data**: Schedules, player stats, play-by-play data, etc.
- **Data processing**: Combining and processing the collected data

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Sleeper Data  │    │    NFL Data     │    │ Data Processing │
│     Pull Step   │    │    Pull Step    │    │     Step        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   S3 Storage    │
                    │  (Processed)    │
                    └─────────────────┘
```

## Prerequisites

1. **AWS Account** with SageMaker access
2. **AWS CLI** configured with appropriate permissions
3. **SageMaker Execution Role** with permissions for:
   - S3 read/write access
   - SageMaker processing jobs
   - ECR access (if using custom images)

## Setup

### 1. Environment Variables

Create a `.env` file with your configuration:

```bash
# AWS Configuration
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# SageMaker Configuration
SAGEMAKER_ROLE_ARN=arn:aws:iam::123456789012:role/SageMakerExecutionRole
S3_BUCKET_NAME=your-sagemaker-bucket

# Fantasy Football Configuration
LEAGUE_ID=your-sleeper-league-id
USER_ID=your-sleeper-user-id
SEASON=2024
WEEK=1

# Pipeline Configuration
SLEEPER_INSTANCE_TYPE=ml.m5.large
NFL_INSTANCE_TYPE=ml.m5.large
PROCESSING_INSTANCE_TYPE=ml.m5.xlarge
OUTPUT_PREFIX=fantasy-football
```

### 2. Build Docker Image

```bash
# Build and push to ECR
make pipeline-build-image AWS_REGION=us-east-1 AWS_ACCOUNT_ID=123456789012 IMAGE_NAME=fantasy-football-2025
```

### 3. Deploy Pipeline

```bash
# Deploy the pipeline to SageMaker
make pipeline-deploy LEAGUE_ID=your-league-id USER_ID=your-user-id
```

## Usage

### Execute Pipeline

```bash
# Execute the pipeline with specific parameters
make pipeline-execute LEAGUE_ID=your-league-id USER_ID=your-user-id SEASON=2024 WEEK=1
```

### Local Development

```bash
# Run pipeline locally with Docker
make docker-pipeline

# Pull Sleeper data only
docker-compose -f docker-compose.pipeline.yml run --rm sleeper-data

# Pull NFL data only
docker-compose -f docker-compose.pipeline.yml run --rm nfl-data
```

### AWS CLI Commands

```bash
# Test AWS connectivity
make aws-test

# Setup AWS credentials
make aws-setup
```

## Pipeline Steps

### 1. Sleeper Data Pull

- **Purpose**: Collect fantasy football data from Sleeper API
- **Data**: League info, rosters, players, transactions, matchups
- **Output**: JSON files and metadata

### 2. NFL Data Pull

- **Purpose**: Collect NFL statistics and schedule data
- **Data**: Schedules, player stats, play-by-play, team info
- **Output**: CSV files and metadata

### 3. Data Processing

- **Purpose**: Combine and process collected data
- **Operations**: Data cleaning, player matching, aggregation
- **Output**: Processed datasets ready for analysis

## Output Structure

```
s3://your-bucket/fantasy-football/
├── sleeper-data/
│   ├── league_info.json
│   ├── rosters.json
│   ├── players.json
│   ├── transactions.json
│   └── metadata.json
├── nfl-data/
│   ├── nfl_schedules.csv
│   ├── nfl_player_stats.csv
│   ├── nfl_teams.csv
│   ├── nfl_players.csv
│   └── nfl_metadata.json
└── processed-data/
    ├── combined_metadata.json
    └── processed_datasets/
```

## Monitoring

### SageMaker Console

1. Navigate to SageMaker Console
2. Go to Pipelines section
3. Find your pipeline execution
4. Monitor step-by-step progress

### CloudWatch Logs

Each processing step generates logs in CloudWatch:
- `/aws/sagemaker/ProcessingJobs`
- `/aws/sagemaker/Pipelines`

### S3 Monitoring

Monitor data collection progress in your S3 bucket:
```bash
aws s3 ls s3://your-bucket/fantasy-football/ --recursive
```

## Troubleshooting

### Common Issues

1. **Permission Errors**
   - Ensure SageMaker execution role has proper permissions
   - Check S3 bucket access

2. **Docker Build Failures**
   - Verify Docker is running
   - Check ECR repository exists

3. **Pipeline Execution Failures**
   - Check CloudWatch logs for detailed error messages
   - Verify environment variables are set correctly

### Debug Commands

```bash
# Check pipeline status
aws sagemaker list-pipeline-executions --pipeline-name fantasy-football-data-pipeline

# Get execution details
aws sagemaker describe-pipeline-execution --pipeline-execution-arn <execution-arn>

# Check processing job logs
aws logs describe-log-groups --log-group-name-prefix "/aws/sagemaker/ProcessingJobs"
```

## Cost Optimization

- Use smaller instance types for development
- Schedule pipeline execution during off-peak hours
- Monitor usage with AWS Cost Explorer
- Consider using Spot instances for processing jobs

## Security

- Use IAM roles with minimal required permissions
- Enable CloudTrail for audit logging
- Encrypt data at rest and in transit
- Regularly rotate access keys

## Next Steps

1. **Automation**: Set up EventBridge triggers for weekly execution
2. **Monitoring**: Add CloudWatch alarms for pipeline failures
3. **Scaling**: Implement parallel processing for multiple leagues
4. **ML Integration**: Add model training and inference steps 