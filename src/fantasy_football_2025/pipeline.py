"""
SageMaker Pipeline for Fantasy Football Data Collection.

This pipeline automates the collection of:
1. Sleeper API data (league info, rosters, players, etc.)
2. NFL data (schedules, stats, etc.)
3. Data processing and storage
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import boto3
import sagemaker
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.functions import JsonGet
from sagemaker.workflow.parameters import ParameterInteger, ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep

logger = logging.getLogger(__name__)


class FantasyFootballPipeline:
    """SageMaker Pipeline for Fantasy Football data collection."""

    def __init__(
        self,
        pipeline_name: str = "fantasy-football-data-pipeline",
        region: str = "us-east-1",
        role_arn: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ):
        self.pipeline_name = pipeline_name
        self.region = region
        self.sagemaker_session = sagemaker.Session()

        # Get default role if not provided
        if role_arn is None:
            self.role_arn = sagemaker.get_execution_role()
        else:
            self.role_arn = role_arn

        # Get default bucket if not provided
        if bucket_name is None:
            self.bucket_name = self.sagemaker_session.default_bucket()
        else:
            self.bucket_name = bucket_name

        self.s3_client = boto3.client("s3", region_name=region)

    def create_pipeline(self) -> Pipeline:
        """Create the SageMaker pipeline."""

        # Pipeline parameters
        league_id_param = ParameterString(
            name="LeagueID", default_value="your-league-id"
        )

        user_id_param = ParameterString(name="UserID", default_value="your-user-id")

        season_param = ParameterString(name="Season", default_value="2024")

        week_param = ParameterInteger(name="Week", default_value=1)

        # Create processing steps
        sleeper_data_step = self._create_sleeper_data_step(
            league_id_param, user_id_param, season_param
        )

        nfl_data_step = self._create_nfl_data_step(season_param, week_param)

        data_processing_step = self._create_data_processing_step(
            sleeper_data_step, nfl_data_step
        )

        # Create pipeline
        pipeline = Pipeline(
            name=self.pipeline_name,
            parameters=[league_id_param, user_id_param, season_param, week_param],
            steps=[sleeper_data_step, nfl_data_step, data_processing_step],
            sagemaker_session=self.sagemaker_session,
        )

        return pipeline

    def _create_sleeper_data_step(
        self,
        league_id_param: ParameterString,
        user_id_param: ParameterString,
        season_param: ParameterString,
    ) -> ProcessingStep:
        """Create step for pulling Sleeper API data."""

        # Create SKLearn processor
        sklearn_processor = SKLearnProcessor(
            framework_version="1.0-1",
            role=self.role_arn,
            instance_type="ml.m5.large",
            instance_count=1,
            base_job_name="sleeper-data-processing",
            sagemaker_session=self.sagemaker_session,
        )

        # Define processing script
        processing_script = """
import os
import sys
import json
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '/opt/ml/processing/input/code')

from fantasy_football_2025.sleeper_client import SleeperClient, SleeperConfig

def main():
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Get parameters from environment
    league_id = os.environ.get('LEAGUE_ID')
    user_id = os.environ.get('USER_ID')
    season = os.environ.get('SEASON', '2024')
    output_dir = '/opt/ml/processing/output'
    
    logger.info(f"Pulling Sleeper data for league {league_id}")
    
    # Create Sleeper client
    config = SleeperConfig(
        league_id=league_id,
        user_id=user_id,
        season=season
    )
    
    client = SleeperClient(config, use_database=False)
    
    # Pull all data
    client.export_league_data(output_dir)
    
    # Create metadata file
    metadata = {
        'league_id': league_id,
        'user_id': user_id,
        'season': season,
        'pulled_at': datetime.now().isoformat(),
        'data_types': ['league_info', 'rosters', 'users', 'players', 'transactions']
    }
    
    with open(f'{output_dir}/metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info("Sleeper data pull completed successfully")

if __name__ == "__main__":
    main()
"""

        # Create processing step
        step = ProcessingStep(
            name="SleeperDataPull",
            processor=sklearn_processor,
            inputs=[
                ProcessingInput(
                    source=processing_script,
                    destination="/opt/ml/processing/input/code",
                    input_name="code",
                )
            ],
            outputs=[
                ProcessingOutput(
                    output_name="sleeper_data",
                    source="/opt/ml/processing/output",
                    destination=f"s3://{self.bucket_name}/fantasy-football/sleeper-data",
                )
            ],
            job_arguments=[
                "--code-file",
                "/opt/ml/processing/input/code/process_sleeper.py",
            ],
            environment={
                "LEAGUE_ID": league_id_param,
                "USER_ID": user_id_param,
                "SEASON": season_param,
            },
        )

        return step

    def _create_nfl_data_step(
        self, season_param: ParameterString, week_param: ParameterInteger
    ) -> ProcessingStep:
        """Create step for pulling NFL data."""

        # Create SKLearn processor
        sklearn_processor = SKLearnProcessor(
            framework_version="1.0-1",
            role=self.role_arn,
            instance_type="ml.m5.large",
            instance_count=1,
            base_job_name="nfl-data-processing",
            sagemaker_session=self.sagemaker_session,
        )

        # Define processing script
        processing_script = """
import os
import sys
import json
import logging
import pandas as pd
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '/opt/ml/processing/input/code')

import nfl_data_py as nfl

def main():
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Get parameters from environment
    season = int(os.environ.get('SEASON', '2024'))
    week = int(os.environ.get('WEEK', '1'))
    output_dir = '/opt/ml/processing/output'
    
    logger.info(f"Pulling NFL data for season {season}, week {week}")
    
    # Pull NFL data
    data_types = {}
    
    try:
        # Team schedules
        schedules = nfl.import_schedules([season])
        data_types['schedules'] = len(schedules)
        schedules.to_csv(f'{output_dir}/nfl_schedules.csv', index=False)
        
        # Player stats
        stats = nfl.import_seasonal_data([season])
        data_types['player_stats'] = len(stats)
        stats.to_csv(f'{output_dir}/nfl_player_stats.csv', index=False)
        
        # Play-by-play data for specific week
        if week <= 18:  # Regular season
            pbp = nfl.import_pbp_data([season])
            weekly_pbp = pbp[pbp['week'] == week]
            data_types['play_by_play'] = len(weekly_pbp)
            weekly_pbp.to_csv(f'{output_dir}/nfl_pbp_week_{week}.csv', index=False)
        
        # Team data
        teams = nfl.import_team_desc()
        data_types['teams'] = len(teams)
        teams.to_csv(f'{output_dir}/nfl_teams.csv', index=False)
        
        # Player data
        players = nfl.import_players()
        data_types['players'] = len(players)
        players.to_csv(f'{output_dir}/nfl_players.csv', index=False)
        
    except Exception as e:
        logger.error(f"Error pulling NFL data: {e}")
        raise
    
    # Create metadata file
    metadata = {
        'season': season,
        'week': week,
        'pulled_at': datetime.now().isoformat(),
        'data_types': data_types
    }
    
    with open(f'{output_dir}/nfl_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info("NFL data pull completed successfully")

if __name__ == "__main__":
    main()
"""

        # Create processing step
        step = ProcessingStep(
            name="NFLDataPull",
            processor=sklearn_processor,
            inputs=[
                ProcessingInput(
                    source=processing_script,
                    destination="/opt/ml/processing/input/code",
                    input_name="code",
                )
            ],
            outputs=[
                ProcessingOutput(
                    output_name="nfl_data",
                    source="/opt/ml/processing/output",
                    destination=f"s3://{self.bucket_name}/fantasy-football/nfl-data",
                )
            ],
            job_arguments=[
                "--code-file",
                "/opt/ml/processing/input/code/process_nfl.py",
            ],
            environment={"SEASON": season_param, "WEEK": week_param},
        )

        return step

    def _create_data_processing_step(
        self, sleeper_step: ProcessingStep, nfl_step: ProcessingStep
    ) -> ProcessingStep:
        """Create step for processing and combining data."""

        # Create SKLearn processor
        sklearn_processor = SKLearnProcessor(
            framework_version="1.0-1",
            role=self.role_arn,
            instance_type="ml.m5.xlarge",
            instance_count=1,
            base_job_name="data-processing",
            sagemaker_session=self.sagemaker_session,
        )

        # Define processing script
        processing_script = """
import os
import sys
import json
import logging
import pandas as pd
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '/opt/ml/processing/input/code')

def main():
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    sleeper_data_dir = '/opt/ml/processing/input/sleeper_data'
    nfl_data_dir = '/opt/ml/processing/input/nfl_data'
    output_dir = '/opt/ml/processing/output'
    
    logger.info("Processing and combining fantasy football data")
    
    # Load metadata
    with open(f'{sleeper_data_dir}/metadata.json', 'r') as f:
        sleeper_metadata = json.load(f)
    
    with open(f'{nfl_data_dir}/nfl_metadata.json', 'r') as f:
        nfl_metadata = json.load(f)
    
    # Process and combine data
    # This is where you'd implement your data processing logic
    # For example, matching players between Sleeper and NFL data
    
    # Create combined metadata
    combined_metadata = {
        'sleeper_data': sleeper_metadata,
        'nfl_data': nfl_metadata,
        'processed_at': datetime.now().isoformat(),
        'processing_version': '1.0'
    }
    
    with open(f'{output_dir}/combined_metadata.json', 'w') as f:
        json.dump(combined_metadata, f, indent=2)
    
    logger.info("Data processing completed successfully")

if __name__ == "__main__":
    main()
"""

        # Create processing step
        step = ProcessingStep(
            name="DataProcessing",
            processor=sklearn_processor,
            inputs=[
                ProcessingInput(
                    source=processing_script,
                    destination="/opt/ml/processing/input/code",
                    input_name="code",
                ),
                ProcessingInput(
                    source=sleeper_step.properties.ProcessingOutputConfig.Outputs[
                        "sleeper_data"
                    ].S3Output.S3Uri,
                    destination="/opt/ml/processing/input/sleeper_data",
                    input_name="sleeper_data",
                ),
                ProcessingInput(
                    source=nfl_step.properties.ProcessingOutputConfig.Outputs[
                        "nfl_data"
                    ].S3Output.S3Uri,
                    destination="/opt/ml/processing/input/nfl_data",
                    input_name="nfl_data",
                ),
            ],
            outputs=[
                ProcessingOutput(
                    output_name="processed_data",
                    source="/opt/ml/processing/output",
                    destination=f"s3://{self.bucket_name}/fantasy-football/processed-data",
                )
            ],
            job_arguments=[
                "--code-file",
                "/opt/ml/processing/input/code/process_combined.py",
            ],
        )

        return step

    def deploy_pipeline(self) -> str:
        """Deploy the pipeline to SageMaker."""
        pipeline = self.create_pipeline()
        pipeline.upsert(role_arn=self.role_arn)
        return pipeline.arn

    def execute_pipeline(
        self, league_id: str, user_id: str, season: str = "2024", week: int = 1
    ) -> str:
        """Execute the pipeline with given parameters."""
        pipeline = self.create_pipeline()
        pipeline.upsert(role_arn=self.role_arn)

        execution = pipeline.start(
            parameters={
                "LeagueID": league_id,
                "UserID": user_id,
                "Season": season,
                "Week": week,
            }
        )

        return execution.arn


def main():
    """Main function for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Fantasy Football SageMaker Pipeline")
    parser.add_argument("--deploy", action="store_true", help="Deploy the pipeline")
    parser.add_argument("--execute", action="store_true", help="Execute the pipeline")
    parser.add_argument("--league-id", required=True, help="Sleeper league ID")
    parser.add_argument("--user-id", required=True, help="Sleeper user ID")
    parser.add_argument("--season", default="2024", help="NFL season")
    parser.add_argument("--week", type=int, default=1, help="NFL week")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--role-arn", help="SageMaker execution role ARN")
    parser.add_argument("--bucket", help="S3 bucket name")

    args = parser.parse_args()

    # Create pipeline
    pipeline = FantasyFootballPipeline(
        region=args.region, role_arn=args.role_arn, bucket_name=args.bucket
    )

    if args.deploy:
        arn = pipeline.deploy_pipeline()
        print(f"Pipeline deployed: {arn}")

    if args.execute:
        execution_arn = pipeline.execute_pipeline(
            league_id=args.league_id,
            user_id=args.user_id,
            season=args.season,
            week=args.week,
        )
        print(f"Pipeline execution started: {execution_arn}")


if __name__ == "__main__":
    main()
