#!/bin/bash

# Deploy StreamrP2P Beta Stage
set -e

STAGE="beta"
REGION="${1:-eu-west-1}"

echo "🚀 Deploying StreamrP2P Beta Stage to $REGION"
echo "======================================================"

# Validate AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

# Bootstrap CDK if needed
echo "🔧 Checking CDK bootstrap..."
if ! aws cloudformation describe-stacks --stack-name CDKToolkit --region $REGION > /dev/null 2>&1; then
    echo "📦 Bootstrapping CDK in region $REGION..."
    npx cdk bootstrap --region $REGION
fi

# Synthesize CloudFormation templates
echo "🔍 Synthesizing CloudFormation templates..."
npx cdk synth --context stage=$STAGE --context region=$REGION

# Deploy stacks
echo "🚀 Deploying foundation stack..."
npx cdk deploy streamr-p2p-beta-ireland-foundation \
    --context stage=$STAGE \
    --context region=$REGION \
    --require-approval never

echo "🚀 Deploying application stack..."
npx cdk deploy streamr-p2p-beta-ireland-application \
    --context stage=$STAGE \
    --context region=$REGION \
    --require-approval never

echo "✅ Beta deployment complete!"
echo ""
echo "📊 Next Steps:"
echo "1. SSH into the instance and deploy your application code"
echo "2. Test the RTMP endpoint and web dashboard"
echo "3. Invite friends to test with the setup script"
echo ""
echo "🔗 Useful Commands:"
echo "   View outputs: npx cdk list --context stage=$STAGE"
echo "   Get instance IP: aws ec2 describe-instances --filters 'Name=tag:Name,Values=streamr-p2p-beta-instance' --query 'Reservations[].Instances[].PublicIpAddress' --output text --region $REGION"
echo "   SSH to instance: ssh -i ~/.ssh/mailserver.pem ec2-user@<INSTANCE_IP>" 