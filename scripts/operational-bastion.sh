#!/bin/bash

# 🔧 StreamrP2P Operational Bastion Manager
# Launches a temporary bastion instance for operational tasks like database migrations

set -e

STAGE="${1:-beta}"
REGION="eu-west-1"
FOUNDATION_STACK_NAME="streamr-p2p-$STAGE-ireland-foundation"

echo "🚀 StreamrP2P Operational Bastion Manager"
echo "Stage: $STAGE"
echo "Region: $REGION"
echo ""

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

# Extract instance profile name from ARN
INSTANCE_PROFILE_NAME=$(echo $INSTANCE_PROFILE_ARN | cut -d'/' -f2)

if [ -z "$SUBNET_ID" ] || [ -z "$SG_ID" ] || [ -z "$INSTANCE_PROFILE_NAME" ]; then
    echo "❌ Failed to get infrastructure details from CloudFormation stack: $FOUNDATION_STACK_NAME"
    echo "   Make sure the foundation stack is deployed and outputs are available."
    exit 1
fi

echo "✅ Infrastructure details retrieved:"
echo "   Subnet: $SUBNET_ID"
echo "   Security Group: $SG_ID"
echo "   Instance Profile: $INSTANCE_PROFILE_NAME"
echo ""

# Launch bastion instance
echo "🏗️ Launching operational bastion instance..."

# Use Amazon Linux 2023 ARM64 (t4g.nano compatible)
echo "🔎 Finding latest Amazon Linux 2023 ARM64 AMI for region $REGION..."
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
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=operational-bastion-temp-$STAGE},{Key=Purpose,Value=OperationalTasks},{Key=Stage,Value=$STAGE}]" \
    --user-data "$(echo '#!/bin/bash
yum update -y
yum install -y postgresql15 jq
echo "Operational bastion ready for $STAGE stage" > /tmp/bastion-ready
' | base64 -w 0)" \
    --query 'Instances[0].InstanceId' --output text --region $REGION)

echo "✅ Bastion instance launched: $INSTANCE_ID"
echo ""

# Wait for SSM agent to be ready
echo "⏳ Waiting for SSM agent to be ready (this may take 1-2 minutes)..."
aws ssm wait instance-information-available --instance-id $INSTANCE_ID --region $REGION

echo "✅ SSM agent is ready!"
echo ""

# Show connection instructions
echo "🔗 Bastion instance is ready for operational tasks!"
echo ""
echo "To connect via SSM Session Manager:"
echo "   aws ssm start-session --target $INSTANCE_ID --region $REGION"
echo ""
echo "📋 Useful commands once connected:"
echo ""
echo "   # Get database credentials:"
echo "   DB_SECRET_ARN=\$(aws cloudformation describe-stacks --stack-name $FOUNDATION_STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==\`DatabaseSecretArn\`].OutputValue' --output text --region $REGION)"
echo "   DB_SECRET=\$(aws secretsmanager get-secret-value --secret-id \$DB_SECRET_ARN --query SecretString --output text --region $REGION)"
echo "   DB_HOST=\$(echo \$DB_SECRET | jq -r .host)"
echo "   DB_USER=\$(echo \$DB_SECRET | jq -r .username)"
echo "   DB_PASSWORD=\$(echo \$DB_SECRET | jq -r .password)"
echo "   DB_NAME=\$(echo \$DB_SECRET | jq -r .dbname)"
echo ""
echo "   # Connect to database:"
echo "   PGPASSWORD=\$DB_PASSWORD psql -h \$DB_HOST -U \$DB_USER -d \$DB_NAME"
echo ""
echo "   # Run migration (if you upload the SQL file):"
echo "   PGPASSWORD=\$DB_PASSWORD psql -h \$DB_HOST -U \$DB_USER -d \$DB_NAME -f /tmp/database_migration_lifecycle.sql"
echo ""
echo "⚠️  The bastion instance will be automatically terminated when you exit this script (Ctrl+C)"
echo ""

# Wait for user to finish their work
echo "Press Ctrl+C when you're done with operational tasks..."
while true; do
    sleep 5
    # Check if instance is still running
    STATE=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].State.Name' --output text --region $REGION 2>/dev/null || echo "terminated")
    if [ "$STATE" != "running" ]; then
        echo "Instance is no longer running. Exiting..."
        break
    fi
done 