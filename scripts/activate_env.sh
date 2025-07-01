#!/bin/bash
# Usage: scripts/activate_env.sh DEV|TEST|PRODUCTION

ENV="$1"
if [[ -z "$ENV" ]]; then
  echo "Usage: $0 DEV|TEST|PRODUCTION"
  exit 1
fi

VENV_DIR=".venv-$ENV"
if [[ ! -d "$VENV_DIR" ]]; then
  echo "Virtual environment $VENV_DIR does not exist. Run 'make venv-$ENV' first."
  exit 1
fi

echo "Activating $ENV environment..."
export ENVIRONMENT="$ENV"
source "$VENV_DIR/bin/activate"
source scripts/set_env.sh

# Drop into a new shell with everything set
exec $SHELL 