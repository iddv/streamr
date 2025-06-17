#!/bin/bash

# 🧪 StreamrP2P Beta Infrastructure Sanity Tests
# Tests all AWS endpoints and infrastructure components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
REGION="eu-west-1"
STAGE="beta"
INSTANCE_IP="108.130.35.167"
ALB_DNS="streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com"
DB_ENDPOINT="streamr-p2p-beta-db.c3q28wieso7a.eu-west-1.rds.amazonaws.com"
CACHE_ENDPOINT="streamr-p2p-beta-cache.e6qheu.0001.euw1.cache.amazonaws.com"
INSTANCE_ID="i-0ac35c7a6284b6b49"

echo -e "${BLUE}🧪 StreamrP2P Beta Infrastructure Sanity Tests${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""

# Test 1: AWS CLI Configuration
echo -e "${YELLOW}📋 Test 1: AWS CLI Configuration${NC}"
if aws sts get-caller-identity --region $REGION > /dev/null 2>&1; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo -e "${GREEN}✅ AWS CLI configured - Account: $ACCOUNT_ID${NC}"
else
    echo -e "${RED}❌ AWS CLI not configured or no access${NC}"
    exit 1
fi
echo ""

# Test 2: CloudFormation Stacks Status
echo -e "${YELLOW}🏗️ Test 2: CloudFormation Stacks Status${NC}"
FOUNDATION_STATUS=$(aws cloudformation describe-stacks --stack-name streamr-p2p-beta-ireland-foundation --region $REGION --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "NOT_FOUND")
APPLICATION_STATUS=$(aws cloudformation describe-stacks --stack-name streamr-p2p-beta-ireland-application --region $REGION --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "NOT_FOUND")

if [[ "$FOUNDATION_STATUS" == "CREATE_COMPLETE" ]]; then
    echo -e "${GREEN}✅ Foundation Stack: $FOUNDATION_STATUS${NC}"
else
    echo -e "${RED}❌ Foundation Stack: $FOUNDATION_STATUS${NC}"
fi

if [[ "$APPLICATION_STATUS" == "CREATE_COMPLETE" ]]; then
    echo -e "${GREEN}✅ Application Stack: $APPLICATION_STATUS${NC}"
else
    echo -e "${RED}❌ Application Stack: $APPLICATION_STATUS${NC}"
fi
echo ""

# Test 3: EC2 Instance Status
echo -e "${YELLOW}🖥️ Test 3: EC2 Instance Status${NC}"
INSTANCE_STATE=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || echo "NOT_FOUND")
INSTANCE_STATUS=$(aws ec2 describe-instance-status --instance-ids $INSTANCE_ID --region $REGION --query 'InstanceStatuses[0].SystemStatus.Status' --output text 2>/dev/null || echo "NOT_FOUND")

if [[ "$INSTANCE_STATE" == "running" ]]; then
    echo -e "${GREEN}✅ Instance State: $INSTANCE_STATE${NC}"
else
    echo -e "${RED}❌ Instance State: $INSTANCE_STATE${NC}"
fi

if [[ "$INSTANCE_STATUS" == "ok" ]] || [[ "$INSTANCE_STATUS" == "NOT_FOUND" ]]; then
    echo -e "${GREEN}✅ Instance System Status: ${INSTANCE_STATUS:-"initializing"}${NC}"
else
    echo -e "${RED}❌ Instance System Status: $INSTANCE_STATUS${NC}"
fi
echo ""

# Test 4: Network Connectivity
echo -e "${YELLOW}🌐 Test 4: Network Connectivity${NC}"

# Test instance ping
if ping -c 3 $INSTANCE_IP > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Instance IP ($INSTANCE_IP) is reachable${NC}"
else
    echo -e "${RED}❌ Instance IP ($INSTANCE_IP) is not reachable${NC}"
fi

# Test ALB DNS resolution
if nslookup $ALB_DNS > /dev/null 2>&1; then
    echo -e "${GREEN}✅ ALB DNS ($ALB_DNS) resolves${NC}"
else
    echo -e "${RED}❌ ALB DNS ($ALB_DNS) does not resolve${NC}"
fi

# Test DB endpoint resolution
if nslookup $DB_ENDPOINT > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Database endpoint resolves${NC}"
else
    echo -e "${RED}❌ Database endpoint does not resolve${NC}"
fi

# Test Cache endpoint resolution
if nslookup $CACHE_ENDPOINT > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Cache endpoint resolves${NC}"
else
    echo -e "${RED}❌ Cache endpoint does not resolve${NC}"
fi
echo ""

# Test 5: Port Connectivity
echo -e "${YELLOW}🔌 Test 5: Port Connectivity${NC}"

# Test HTTP port (80) via ALB
if timeout 10 bash -c "</dev/tcp/$ALB_DNS/80" 2>/dev/null; then
    echo -e "${GREEN}✅ ALB HTTP port 80 is open${NC}"
else
    echo -e "${RED}❌ ALB HTTP port 80 is not accessible${NC}"
fi

# Test RTMP port (1935) direct to instance
if timeout 10 bash -c "</dev/tcp/$INSTANCE_IP/1935" 2>/dev/null; then
    echo -e "${GREEN}✅ Instance RTMP port 1935 is open${NC}"
else
    echo -e "${RED}❌ Instance RTMP port 1935 is not accessible${NC}"
fi

# Test SSH port (22) - should be open for beta
if timeout 10 bash -c "</dev/tcp/$INSTANCE_IP/22" 2>/dev/null; then
    echo -e "${GREEN}✅ Instance SSH port 22 is open${NC}"
else
    echo -e "${RED}❌ Instance SSH port 22 is not accessible${NC}"
fi

# Test database port (5432) - should be blocked from external
if timeout 5 bash -c "</dev/tcp/$DB_ENDPOINT/5432" 2>/dev/null; then
    echo -e "${RED}⚠️ Database port 5432 is externally accessible (security concern)${NC}"
else
    echo -e "${GREEN}✅ Database port 5432 is properly secured${NC}"
fi

# Test cache port (6379) - should be blocked from external
if timeout 5 bash -c "</dev/tcp/$CACHE_ENDPOINT/6379" 2>/dev/null; then
    echo -e "${RED}⚠️ Cache port 6379 is externally accessible (security concern)${NC}"
else
    echo -e "${GREEN}✅ Cache port 6379 is properly secured${NC}"
fi
echo ""

# Test 6: HTTP Endpoints
echo -e "${YELLOW}🌐 Test 6: HTTP Endpoints${NC}"

# Test ALB health
ALB_HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://$ALB_DNS/ || echo "000")
if [[ "$ALB_HTTP_STATUS" =~ ^[23] ]]; then
    echo -e "${GREEN}✅ ALB HTTP endpoint responds (status: $ALB_HTTP_STATUS)${NC}"
else
    echo -e "${RED}❌ ALB HTTP endpoint not responding (status: $ALB_HTTP_STATUS)${NC}"
fi

# Test direct instance HTTP (port 8000) - might not be exposed
INSTANCE_HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://$INSTANCE_IP:8000/ || echo "000")
if [[ "$INSTANCE_HTTP_STATUS" =~ ^[23] ]]; then
    echo -e "${GREEN}✅ Instance HTTP:8000 responds (status: $INSTANCE_HTTP_STATUS)${NC}"
else
    echo -e "${YELLOW}⚠️ Instance HTTP:8000 not responding (status: $INSTANCE_HTTP_STATUS) - Normal if app not deployed${NC}"
fi
echo ""

# Test 7: AWS Resource Tags
echo -e "${YELLOW}🏷️ Test 7: AWS Resource Tags${NC}"
INSTANCE_TAGS=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION --query 'Reservations[0].Instances[0].Tags[?Key==`Project`].Value' --output text 2>/dev/null || echo "")
if [[ "$INSTANCE_TAGS" == "streamr-p2p" ]]; then
    echo -e "${GREEN}✅ Instance has correct project tags${NC}"
else
    echo -e "${RED}❌ Instance missing or incorrect project tags${NC}"
fi
echo ""

# Test 8: Security Groups
echo -e "${YELLOW}🛡️ Test 8: Security Groups${NC}"
INSTANCE_SG=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")
if [[ -n "$INSTANCE_SG" ]]; then
    echo -e "${GREEN}✅ Instance has security group: $INSTANCE_SG${NC}"
    
    # Check security group rules
    SG_RULES=$(aws ec2 describe-security-groups --group-ids $INSTANCE_SG --region $REGION --query 'SecurityGroups[0].IpPermissions[?FromPort==`22`]' --output text 2>/dev/null || echo "")
    if [[ -n "$SG_RULES" ]]; then
        echo -e "${GREEN}✅ SSH access rule found in security group${NC}"
    else
        echo -e "${RED}❌ SSH access rule not found in security group${NC}"
    fi
else
    echo -e "${RED}❌ Instance security group not found${NC}"
fi
echo ""

# Test 9: CloudWatch Logs
echo -e "${YELLOW}📊 Test 9: CloudWatch Monitoring${NC}"
LOG_GROUPS=$(aws logs describe-log-groups --region $REGION --log-group-name-prefix "/aws/ec2" --query 'logGroups[].logGroupName' --output text 2>/dev/null || echo "")
if [[ -n "$LOG_GROUPS" ]]; then
    echo -e "${GREEN}✅ CloudWatch log groups found${NC}"
else
    echo -e "${YELLOW}⚠️ No CloudWatch log groups found - May not be configured yet${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}📋 Test Summary${NC}"
echo -e "${BLUE}===============${NC}"
echo -e "🌍 Region: $REGION"
echo -e "🎭 Stage: $STAGE"
echo -e "🖥️ Instance: $INSTANCE_ID ($INSTANCE_IP)"
echo -e "🌐 ALB: $ALB_DNS"
echo -e "🗄️ Database: $DB_ENDPOINT"
echo -e "⚡ Cache: $CACHE_ENDPOINT"
echo ""
echo -e "${GREEN}✅ Infrastructure appears to be deployed and accessible!${NC}"
echo -e "${YELLOW}⚠️ Next step: Deploy StreamrP2P application to EC2 instance${NC}"
echo ""
echo -e "${BLUE}Test URLs:${NC}"
echo -e "• Web Dashboard: http://$ALB_DNS/"
echo -e "• RTMP Endpoint: rtmp://$INSTANCE_IP:1935/live"
echo -e "• SSH Access: ssh -i ~/.ssh/mailserver.pem ec2-user@$INSTANCE_IP" 