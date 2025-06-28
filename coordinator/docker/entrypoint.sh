#!/bin/bash
set -e

echo "=== StreamrP2P ECS Container Starting ==="

# Check if running in ECS (AWS environment)
if [ -n "$AWS_DEFAULT_REGION" ] && [ -n "$DB_SECRET_NAME" ]; then
    echo "🔧 ECS Environment detected - fetching AWS configuration..."
    
    # Fetch database credentials from AWS Secrets Manager
    echo "📡 Fetching database credentials from Secrets Manager..."
    if SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id "$DB_SECRET_NAME" --query SecretString --output text); then
        # Extract database credentials from secret JSON
        DB_USERNAME=$(echo "$SECRET_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['username'])")
        DB_PASSWORD=$(echo "$SECRET_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['password'])")
        DB_HOST=$(echo "$SECRET_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['host'])")
        DB_PORT=$(echo "$SECRET_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['port'])")
        DB_NAME=$(echo "$SECRET_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['dbname'])")
        
        # Set DATABASE_URL environment variable
        export DATABASE_URL="postgresql://$DB_USERNAME:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
        echo "✅ Database configuration loaded"
    else
        echo "❌ Failed to retrieve database secret from Secrets Manager"
        exit 1
    fi
    
    # Fetch cache endpoint from CloudFormation (if FOUNDATION_STACK_NAME is set)
    if [ -n "$FOUNDATION_STACK_NAME" ]; then
        echo "📡 Fetching cache endpoint from CloudFormation..."
        if CACHE_ENDPOINT=$(aws cloudformation describe-stacks --stack-name "$FOUNDATION_STACK_NAME" --region "$AWS_DEFAULT_REGION" --query 'Stacks[0].Outputs[?OutputKey==`CacheEndpoint`].OutputValue' --output text); then
            export REDIS_URL="redis://$CACHE_ENDPOINT:6379"
            echo "✅ Cache configuration loaded"
        else
            echo "⚠️  Warning: Could not retrieve cache endpoint from CloudFormation"
            # Continue without Redis if not available
        fi
    fi
    
    echo "🚀 AWS configuration complete"
else
    echo "🏠 Local development environment detected - using existing environment variables"
fi

# Ensure required environment variables are set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL not set"
    exit 1
fi

# Set default values for production
export ENVIRONMENT=${ENVIRONMENT:-production}
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export WORKERS=${WORKERS:-2}

echo "📊 Configuration Summary:"
echo "   Environment: $ENVIRONMENT"
echo "   Log Level: $LOG_LEVEL"
echo "   Workers: $WORKERS"
echo "   Database: ${DATABASE_URL%%@*}@***" # Hide password in logs
if [ -n "$REDIS_URL" ]; then
    echo "   Redis: $REDIS_URL"
fi

echo "🎯 Starting StreamrP2P Coordinator..."

# Execute the main command
exec "$@"