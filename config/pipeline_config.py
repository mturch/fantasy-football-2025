"""
Configuration for Fantasy Football SageMaker Pipeline.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Configuration for the SageMaker pipeline."""
    
    # AWS Configuration
    region: str = "us-east-1"
    role_arn: Optional[str] = None
    bucket_name: Optional[str] = None
    
    # Pipeline Configuration
    pipeline_name: str = "fantasy-football-data-pipeline"
    
    # Data Sources
    league_id: str = ""
    user_id: str = ""
    season: str = "2024"
    week: int = 1
    
    # Processing Configuration
    sleeper_instance_type: str = "ml.m5.large"
    nfl_instance_type: str = "ml.m5.large"
    processing_instance_type: str = "ml.m5.xlarge"
    
    # Output Configuration
    output_prefix: str = "fantasy-football"
    
    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Create configuration from environment variables."""
        return cls(
            region=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            role_arn=os.getenv("SAGEMAKER_ROLE_ARN"),
            bucket_name=os.getenv("S3_BUCKET_NAME"),
            league_id=os.getenv("LEAGUE_ID", ""),
            user_id=os.getenv("USER_ID", ""),
            season=os.getenv("SEASON", "2024"),
            week=int(os.getenv("WEEK", "1")),
            sleeper_instance_type=os.getenv("SLEEPER_INSTANCE_TYPE", "ml.m5.large"),
            nfl_instance_type=os.getenv("NFL_INSTANCE_TYPE", "ml.m5.large"),
            processing_instance_type=os.getenv("PROCESSING_INSTANCE_TYPE", "ml.m5.xlarge"),
            output_prefix=os.getenv("OUTPUT_PREFIX", "fantasy-football")
        )
    
    def validate(self) -> None:
        """Validate configuration."""
        if not self.league_id:
            raise ValueError("LEAGUE_ID is required")
        if not self.user_id:
            raise ValueError("USER_ID is required")
        if not self.role_arn:
            raise ValueError("SAGEMAKER_ROLE_ARN is required")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "region": self.region,
            "role_arn": self.role_arn,
            "bucket_name": self.bucket_name,
            "pipeline_name": self.pipeline_name,
            "league_id": self.league_id,
            "user_id": self.user_id,
            "season": self.season,
            "week": self.week,
            "sleeper_instance_type": self.sleeper_instance_type,
            "nfl_instance_type": self.nfl_instance_type,
            "processing_instance_type": self.processing_instance_type,
            "output_prefix": self.output_prefix
        }


# Default configuration
DEFAULT_CONFIG = PipelineConfig() 