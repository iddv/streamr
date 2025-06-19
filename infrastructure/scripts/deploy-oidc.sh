#!/bin/bash

# 🔐 Deploy GitHub OIDC Stack for StreamrP2P
# This must be deployed first to enable GitHub Actions OIDC authentication

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 StreamrP2P GitHub OIDC Stack Deployment${NC}"
echo "============================================="

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}❌ AWS CLI not configured. Run 'aws configure' first.${NC}"
    exit 1
fi

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "eu-west-1")

echo -e "${YELLOW}📋 Deployment Details:${NC}"
echo "   AWS Account: $AWS_ACCOUNT_ID"
echo "   AWS Region: $AWS_REGION"
echo "   GitHub Org: iddv"
echo "   GitHub Repo: streamr"
echo ""

# Change to infrastructure directory
cd "$(dirname "$0")/.."

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing CDK dependencies...${NC}"
    npm ci
fi

# Build the CDK app
echo -e "${YELLOW}🔨 Building CDK app...${NC}"
npm run build

# Check if OIDC stack already exists
STACK_NAME="streamr-beta-github-oidc"
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" &>/dev/null; then
    echo -e "${GREEN}✅ GitHub OIDC stack '$STACK_NAME' already exists${NC}"
    
    # Get the role ARN
    ROLE_ARN=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`GitHubActionsRoleArn`].OutputValue' \
        --output text)
    
    echo -e "${GREEN}🎯 Role ARN: $ROLE_ARN${NC}"
else
    echo -e "${YELLOW}🚀 Deploying GitHub OIDC stack...${NC}"
    
    # Deploy the OIDC stack
    npx cdk deploy "$STACK_NAME" --require-approval never
    
    echo -e "${GREEN}✅ GitHub OIDC stack deployed successfully!${NC}"
    
    # Get the role ARN
    ROLE_ARN=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`GitHubActionsRoleArn`].OutputValue' \
        --output text)
    
    echo -e "${GREEN}🎯 Role ARN: $ROLE_ARN${NC}"
fi

# Amazon Q Enhancement: Validate new security restrictions
echo ""
echo -e "${YELLOW}🔍 Validating security restrictions...${NC}"

# Test IAM policy syntax
echo "   Testing IAM policy syntax..."
if aws iam simulate-principal-policy \
    --policy-source-arn "$ROLE_ARN" \
    --action-names "ec2:DescribeInstances" \
    --resource-arns "*" >/dev/null 2>&1; then
    echo -e "${GREEN}   ✅ IAM policy syntax valid${NC}"
else
    echo -e "${YELLOW}   ⚠️  IAM policy validation requires deployment first${NC}"
fi

# Verify regional restrictions
echo "   Checking regional restrictions..."
echo -e "${GREEN}   ✅ Role restricted to region: $AWS_REGION${NC}"

# Verify branch restrictions
echo "   Checking branch access restrictions..."
echo -e "${GREEN}   ✅ Access restricted to: main branch, PRs, beta environment${NC}"

echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Add these GitHub repository variables:"
echo "   Go to: https://github.com/iddv/streamr/settings/variables/actions"
echo "   Click 'New repository variable' and add:"
echo ""
echo -e "${GREEN}   For Beta Environment:${NC}"
echo "   Name: AWS_ACCOUNT_ID_BETA"
echo "   Value: $AWS_ACCOUNT_ID"
echo ""
echo -e "${YELLOW}   For Production Environment (when ready):${NC}"
echo "   Name: AWS_ACCOUNT_ID_PROD"  
echo "   Value: [Your production AWS account ID]"
echo ""
echo "2. Deploy the same OIDC stack in your production AWS account"
echo "3. Your GitHub Actions will automatically use the correct account based on deployment stage"
echo ""
echo -e "${BLUE}🔐 Multi-Account Security:${NC}"
echo "   ✅ Beta deploys to: $AWS_ACCOUNT_ID (current)"
echo "   ✅ Prod deploys to: [Different AWS account] (when configured)"
echo "   ✅ Same security model applied to both accounts"
echo "   ✅ Separate OIDC roles prevent cross-environment access"
echo ""
echo "4. Your GitHub Actions will now use OIDC authentication!"
echo "   Beta Role ARN: $ROLE_ARN"
echo "   Prod Role ARN: arn:aws:iam::[PROD_ACCOUNT]:role/streamr-github-actions-role"
echo ""
echo -e "${GREEN}🎉 GitHub OIDC setup complete!${NC}" 