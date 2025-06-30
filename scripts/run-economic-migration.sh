#!/bin/bash

# 💰 StreamrP2P Economic Validation Migration Runner
# Based on proven run-migration-fixed.sh pattern
# Launches operational bastion and runs economic validation migration

set -e

STAGE="${1:-beta}"
REGION="eu-west-1"
FOUNDATION_STACK_NAME="streamr-p2p-$STAGE-$REGION-foundation"
MIGRATION_FILE="coordinator/economic_validation_migration.sql"

echo "💰 StreamrP2P Economic Validation Migration Runner"
echo "Stage: $STAGE"
echo "Region: $REGION"
echo "Migration: $MIGRATION_FILE"
echo ""

# Check if migration file exists
if [ ! -f "$MIGRATION_FILE" ]; then
    echo "❌ Migration file not found: $MIGRATION_FILE"
    echo "   Please run this script from the project root directory."
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    if [ ! -z "$INSTANCE_ID" ]; then
        echo ""
        echo "🧹 Cleaning up bastion instance: $INSTANCE_ID"
        aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $REGION >/dev/null 2>&1 || true
        echo "✅ Cleanup initiated"
    fi
}

# Set trap to cleanup on script exit
trap cleanup EXIT

# Get infrastructure details from CloudFormation
echo "📡 Getting infrastructure details from CloudFormation..."

SUBNET_ID=$(aws cloudformation describe-stacks \
    --stack-name "$FOUNDATION_STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`OperationalSubnetId`].OutputValue' \
    --output text --region $REGION)

SG_ID=$(aws cloudformation describe-stacks \
    --stack-name "$FOUNDATION_STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`OperationalBastionSecurityGroupId`].OutputValue' \
    --output text --region $REGION)

INSTANCE_PROFILE_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$FOUNDATION_STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`OperationalBastionInstanceProfileArn`].OutputValue' \
    --output text --region $REGION)

DB_SECRET_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$FOUNDATION_STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`DatabaseSecretArn`].OutputValue' \
    --output text --region $REGION)

# Extract instance profile name from ARN
INSTANCE_PROFILE_NAME=$(echo $INSTANCE_PROFILE_ARN | cut -d'/' -f2)

if [ -z "$SUBNET_ID" ] || [ -z "$SG_ID" ] || [ -z "$INSTANCE_PROFILE_NAME" ] || [ -z "$DB_SECRET_ARN" ]; then
    echo "❌ Failed to get infrastructure details from CloudFormation stack: $FOUNDATION_STACK_NAME"
    echo "   Make sure the foundation stack is deployed and outputs are available."
    exit 1
fi

echo "✅ Infrastructure details retrieved"
echo ""

# Launch bastion instance
echo "🏗️ Launching operational bastion instance..."

AMI_ID=$(aws ssm get-parameters --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64 --region $REGION --query 'Parameters[0].[Value]' --output text)
if [ -z "$AMI_ID" ]; then
    echo "❌ Could not find the latest Amazon Linux 2023 AMI in $REGION."
    exit 1
fi
echo "✅ Using AMI: $AMI_ID"

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type t4g.nano \
    --subnet-id $SUBNET_ID \
    --security-group-ids $SG_ID \
    --iam-instance-profile Name=$INSTANCE_PROFILE_NAME \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=economic-migration-bastion-$STAGE},{Key=Purpose,Value=EconomicValidationMigration},{Key=Stage,Value=$STAGE}]" \
    --user-data "$(echo '#!/bin/bash
yum update -y
yum install -y postgresql15 jq
echo "Economic migration bastion ready" > /tmp/bastion-ready
' | base64 -w 0)" \
    --query 'Instances[0].InstanceId' --output text --region $REGION)

echo "✅ Bastion instance launched: $INSTANCE_ID"
echo ""

# Wait for SSM agent to be ready
echo "⏳ Waiting for SSM agent to be ready..."
for i in {1..30}; do
    if aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$INSTANCE_ID" --region $REGION --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null | grep -q "Online"; then
        echo "✅ SSM agent is online!"
        break
    fi
    echo "   Attempt $i/30: SSM agent not ready yet, waiting 10 seconds..."
    sleep 10
done

# Step 1: Get database credentials
echo "🔗 Getting database credentials..."
COMMAND_ID=$(aws ssm send-command \
    --instance-ids $INSTANCE_ID \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["echo Getting database credentials...", "DB_SECRET=$(aws secretsmanager get-secret-value --secret-id '"$DB_SECRET_ARN"' --query SecretString --output text --region '"$REGION"')", "echo $DB_SECRET | jq -r .host > /tmp/db_host", "echo $DB_SECRET | jq -r .username > /tmp/db_user", "echo $DB_SECRET | jq -r .password > /tmp/db_password", "echo $DB_SECRET | jq -r .dbname > /tmp/db_name", "echo Database credentials stored"]' \
    --query 'Command.CommandId' --output text --region $REGION)

aws ssm wait command-executed --command-id $COMMAND_ID --instance-id $INSTANCE_ID --region $REGION

# Step 2: Create migration SQL file on bastion
echo "📝 Uploading economic validation migration SQL..."
MIGRATION_CONTENT=$(cat "$MIGRATION_FILE" | sed 's/"/\\"/g' | tr '\n' ' ')
COMMAND_ID=$(aws ssm send-command \
    --instance-ids $INSTANCE_ID \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["echo Uploading economic validation migration SQL...", "cat > /tmp/economic_migration.sql << '"'"'EOF'"'"'", "'"$MIGRATION_CONTENT"'", "EOF", "echo Economic validation migration SQL uploaded"]' \
    --query 'Command.CommandId' --output text --region $REGION)

aws ssm wait command-executed --command-id $COMMAND_ID --instance-id $INSTANCE_ID --region $REGION

# Step 3: Run economic validation migration
echo "🚀 Running economic validation migration..."
COMMAND_ID=$(aws ssm send-command \
    --instance-ids $INSTANCE_ID \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["echo Running economic validation migration...", "DB_HOST=$(cat /tmp/db_host)", "DB_USER=$(cat /tmp/db_user)", "DB_PASSWORD=$(cat /tmp/db_password)", "DB_NAME=$(cat /tmp/db_name)", "echo Connecting to database: $DB_HOST", "PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f /tmp/economic_migration.sql", "echo Economic validation migration completed successfully!"]' \
    --query 'Command.CommandId' --output text --region $REGION)

echo "📋 Command ID: $COMMAND_ID"
echo "⏳ Waiting for migration to complete..."

aws ssm wait command-executed --command-id $COMMAND_ID --instance-id $INSTANCE_ID --region $REGION

# Check if migration succeeded
STATUS=$(aws ssm get-command-invocation \
    --command-id $COMMAND_ID \
    --instance-id $INSTANCE_ID \
    --query 'Status' --output text --region $REGION)

echo ""
echo "📊 Migration Status: $STATUS"
echo ""

if [ "$STATUS" = "Success" ]; then
    echo "✅ Economic validation migration completed successfully!"
    
    # Show the command output
    echo ""
    echo "📋 Migration output:"
    aws ssm get-command-invocation \
        --command-id $COMMAND_ID \
        --instance-id $INSTANCE_ID \
        --query 'StandardOutputContent' --output text --region $REGION
else
    echo "❌ Migration failed!"
    echo ""
    echo "📋 Error output:"
    aws ssm get-command-invocation \
        --command-id $COMMAND_ID \
        --instance-id $INSTANCE_ID \
        --query 'StandardErrorContent' --output text --region $REGION
fi

echo ""
echo "🎉 Economic validation migration process completed!"
echo ""
echo "✅ Next steps:"
echo "   1. Verify new tables exist: bandwidth_ledger, user_accounts"
echo "   2. Check streams table has new economic columns"
echo "   3. Deploy updated coordinator code with economic API endpoints" 