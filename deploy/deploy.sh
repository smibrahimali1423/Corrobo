#!/bin/bash
# Pull an API image from ECR and (re)start the production stack.
#   Usage: /opt/corrobo/deploy.sh [image-tag]     (default: latest)
# Run on the EC2 host -- by the GitHub deploy workflow via SSM Run Command,
# or manually from an SSM Session Manager shell.
set -euo pipefail

TAG="${1:-latest}"
cd "$(dirname "$0")"
# shellcheck source=/dev/null
source ./deploy.conf # AWS_REGION, ECR_REPOSITORY_URL, SSM_PREFIX, SITE_ADDRESS, CORS_ORIGINS

param() { # param <name> [required|optional]
  local value
  if value="$(aws ssm get-parameter --region "$AWS_REGION" --with-decryption \
      --name "$SSM_PREFIX/$1" --query Parameter.Value --output text 2>/dev/null)"; then
    printf '%s' "$value"
  elif [ "${2:-required}" = "required" ]; then
    echo "Missing required SSM parameter $SSM_PREFIX/$1 (see docs/DEPLOYMENT.md)" >&2
    return 1
  fi
}

POSTGRES_PASSWORD="$(param postgres_password)"
JWT_SECRET="$(param jwt_secret)"
GEMINI_API_KEY="$(param gemini_api_key optional)" # app degrades gracefully without it

# Rendered fresh on every deploy so rotating a secret in SSM + redeploying
# is all it takes. Readable by root only.
umask 077
cat > .env <<ENV
API_IMAGE=$ECR_REPOSITORY_URL:$TAG
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
JWT_SECRET=$JWT_SECRET
GEMINI_API_KEY=$GEMINI_API_KEY
SITE_ADDRESS=$SITE_ADDRESS
CORS_ORIGINS=$CORS_ORIGINS
ENV

REGISTRY="${ECR_REPOSITORY_URL%%/*}"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY"

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker image prune -f

# Wait for the API's healthcheck (migrations run on container start).
for _ in $(seq 1 30); do
  status="$(docker inspect --format '{{.State.Health.Status}}' "$(docker compose -f docker-compose.prod.yml ps -q api)")"
  if [ "$status" = "healthy" ]; then
    echo "Deployed $TAG: api is healthy."
    exit 0
  fi
  sleep 5
done
echo "api did not become healthy; check: docker compose -f docker-compose.prod.yml logs api" >&2
exit 1
