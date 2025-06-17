#!/bin/bash

# StreamrP2P Cost Control Script
# Manages AWS resources to minimize costs when not actively testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FOUNDATION_STACK="streamr-p2p-beta-ireland-foundation"
APPLICATION_STACK="streamr-p2p-beta-ireland-application"
REGION="eu-west-1"

# Function to display usage
usage() {
    echo -e "${BLUE}StreamrP2P Cost Control${NC}"
    echo "======================"
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  status       - Show current resource status and estimated costs"
    echo "  pause        - Stop EC2 instance to minimize costs (keeps data)"
    echo "  resume       - Start EC2 instance for testing"
    echo "  scale-down   - Scale database to minimum size (requires downtime)"
    echo "  scale-up     - Scale database back to normal size"
    echo "  estimate     - Show detailed cost breakdown"
    echo "  schedule     - Set up automated start/stop schedule"
    echo "  emergency    - Emergency cost reduction (stops everything)"
    echo ""
    echo "Examples:"
    echo "  $0 status           # Check current status"
    echo "  $0 pause            # Stop instance when done testing"
    echo "  $0 resume           # Start instance for testing session"
    echo "  $0 estimate         # See cost breakdown"
}

# Function to get current costs
get_cost_estimate() {
    echo -e "${BLUE}💰 Current Cost Estimate${NC}"
    echo "========================"
    
    # Get instance state
    INSTANCE_ID=$(aws cloudformation describe-stacks \
        --stack-name $APPLICATION_STACK \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
        --output text 2>/dev/null || echo "N/A")
    
    if [ "$INSTANCE_ID" != "N/A" ]; then
        INSTANCE_STATE=$(aws ec2 describe-instances \
            --instance-ids $INSTANCE_ID \
            --region $REGION \
            --query 'Reservations[0].Instances[0].State.Name' \
            --output text 2>/dev/null || echo "unknown")
        echo -e "EC2 Instance (t3.micro): ${INSTANCE_STATE}"
    fi
    
    echo ""
    echo -e "${YELLOW}Monthly Cost Breakdown:${NC}"
    echo "• EC2 t3.micro (running 24/7):     ~$8.50/month"
    echo "• EC2 t3.micro (running 8h/day):   ~$2.83/month"
    echo "• RDS PostgreSQL db.t3.micro:      ~$13.00/month"
    echo "• ElastiCache Redis cache.t3.micro: ~$5.50/month"
    echo "• Application Load Balancer:        ~$16.20/month"
    echo "• Data Transfer (minimal):          ~$1.00/month"
    echo "• CloudWatch Logs (basic):          ~$0.50/month"
    echo ""
    echo -e "${GREEN}Total (24/7):     ~$44.70/month${NC}"
    echo -e "${GREEN}Total (8h/day):   ~$38.53/month${NC}"
    echo -e "${GREEN}Total (paused):   ~$36.20/month${NC}"
    echo ""
    echo -e "${BLUE}💡 Cost Optimization Tips:${NC}"
    echo "• Stop EC2 when not testing: Save ~$5.67/month"
    echo "• Use schedule automation: Save 60-70% on EC2 costs"
    echo "• Database can't be stopped but is already minimal size"
    echo "• ALB is needed for production-like testing"
}

# Function to check resource status
check_status() {
    echo -e "${BLUE}📊 Resource Status${NC}"
    echo "=================="
    
    # Check CloudFormation stacks
    echo -e "${YELLOW}CloudFormation Stacks:${NC}"
    for stack in $FOUNDATION_STACK $APPLICATION_STACK; do
        STATUS=$(aws cloudformation describe-stacks \
            --stack-name $stack \
            --region $REGION \
            --query 'Stacks[0].StackStatus' \
            --output text 2>/dev/null || echo "NOT_FOUND")
        echo "• $stack: $STATUS"
    done
    
    echo ""
    
    # Check EC2 instance
    echo -e "${YELLOW}EC2 Instance:${NC}"
    INSTANCE_ID=$(aws cloudformation describe-stacks \
        --stack-name $APPLICATION_STACK \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
        --output text 2>/dev/null || echo "N/A")
    
    if [ "$INSTANCE_ID" != "N/A" ]; then
        INSTANCE_INFO=$(aws ec2 describe-instances \
            --instance-ids $INSTANCE_ID \
            --region $REGION \
            --query 'Reservations[0].Instances[0].[State.Name,InstanceType,PublicIpAddress]' \
            --output text 2>/dev/null || echo "unknown unknown unknown")
        echo "• Instance ID: $INSTANCE_ID"
        echo "• State: $(echo $INSTANCE_INFO | cut -d' ' -f1)"
        echo "• Type: $(echo $INSTANCE_INFO | cut -d' ' -f2)"
        echo "• IP: $(echo $INSTANCE_INFO | cut -d' ' -f3)"
    else
        echo "• No instance found"
    fi
    
    echo ""
    
    # Check RDS
    echo -e "${YELLOW}RDS Database:${NC}"
    DB_IDENTIFIER=$(aws cloudformation describe-stacks \
        --stack-name $FOUNDATION_STACK \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`DatabaseIdentifier`].OutputValue' \
        --output text 2>/dev/null || echo "N/A")
    
    if [ "$DB_IDENTIFIER" != "N/A" ]; then
        DB_STATUS=$(aws rds describe-db-instances \
            --db-instance-identifier $DB_IDENTIFIER \
            --region $REGION \
            --query 'DBInstances[0].DBInstanceStatus' \
            --output text 2>/dev/null || echo "unknown")
        DB_CLASS=$(aws rds describe-db-instances \
            --db-instance-identifier $DB_IDENTIFIER \
            --region $REGION \
            --query 'DBInstances[0].DBInstanceClass' \
            --output text 2>/dev/null || echo "unknown")
        echo "• Database ID: $DB_IDENTIFIER"
        echo "• Status: $DB_STATUS"
        echo "• Class: $DB_CLASS"
    else
        echo "• No database found"
    fi
    
    echo ""
    
    # Check ElastiCache
    echo -e "${YELLOW}ElastiCache Redis:${NC}"
    CACHE_ID=$(aws cloudformation describe-stacks \
        --stack-name $FOUNDATION_STACK \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`CacheClusterId`].OutputValue' \
        --output text 2>/dev/null || echo "N/A")
    
    if [ "$CACHE_ID" != "N/A" ]; then
        CACHE_STATUS=$(aws elasticache describe-cache-clusters \
            --cache-cluster-id $CACHE_ID \
            --region $REGION \
            --query 'CacheClusters[0].CacheClusterStatus' \
            --output text 2>/dev/null || echo "unknown")
        CACHE_TYPE=$(aws elasticache describe-cache-clusters \
            --cache-cluster-id $CACHE_ID \
            --region $REGION \
            --query 'CacheClusters[0].CacheNodeType' \
            --output text 2>/dev/null || echo "unknown")
        echo "• Cache ID: $CACHE_ID"
        echo "• Status: $CACHE_STATUS"
        echo "• Type: $CACHE_TYPE"
    else
        echo "• No cache found"
    fi
}

# Function to pause (stop) EC2 instance
pause_instance() {
    echo -e "${YELLOW}⏸️ Pausing EC2 Instance...${NC}"
    
    INSTANCE_ID=$(aws cloudformation describe-stacks \
        --stack-name $APPLICATION_STACK \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
        --output text 2>/dev/null || echo "N/A")
    
    if [ "$INSTANCE_ID" = "N/A" ]; then
        echo -e "${RED}❌ No instance found${NC}"
        return 1
    fi
    
    CURRENT_STATE=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --region $REGION \
        --query 'Reservations[0].Instances[0].State.Name' \
        --output text)
    
    if [ "$CURRENT_STATE" = "stopped" ]; then
        echo -e "${GREEN}✅ Instance already stopped${NC}"
        return 0
    fi
    
    if [ "$CURRENT_STATE" != "running" ]; then
        echo -e "${YELLOW}⚠️ Instance is in $CURRENT_STATE state${NC}"
        return 1
    fi
    
    echo "Stopping instance $INSTANCE_ID..."
    aws ec2 stop-instances --instance-ids $INSTANCE_ID --region $REGION > /dev/null
    
    echo "Waiting for instance to stop..."
    aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID --region $REGION
    
    echo -e "${GREEN}✅ Instance stopped successfully${NC}"
    echo -e "${BLUE}💰 Cost savings: ~$5.67/month while stopped${NC}"
    echo -e "${YELLOW}💡 To resume testing: $0 resume${NC}"
}

# Function to resume (start) EC2 instance
resume_instance() {
    echo -e "${YELLOW}▶️ Resuming EC2 Instance...${NC}"
    
    INSTANCE_ID=$(aws cloudformation describe-stacks \
        --stack-name $APPLICATION_STACK \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
        --output text 2>/dev/null || echo "N/A")
    
    if [ "$INSTANCE_ID" = "N/A" ]; then
        echo -e "${RED}❌ No instance found${NC}"
        return 1
    fi
    
    CURRENT_STATE=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --region $REGION \
        --query 'Reservations[0].Instances[0].State.Name' \
        --output text)
    
    if [ "$CURRENT_STATE" = "running" ]; then
        echo -e "${GREEN}✅ Instance already running${NC}"
        NEW_IP=$(aws ec2 describe-instances \
            --instance-ids $INSTANCE_ID \
            --region $REGION \
            --query 'Reservations[0].Instances[0].PublicIpAddress' \
            --output text)
        echo -e "${BLUE}📡 Public IP: $NEW_IP${NC}"
        return 0
    fi
    
    if [ "$CURRENT_STATE" != "stopped" ]; then
        echo -e "${YELLOW}⚠️ Instance is in $CURRENT_STATE state${NC}"
        return 1
    fi
    
    echo "Starting instance $INSTANCE_ID..."
    aws ec2 start-instances --instance-ids $INSTANCE_ID --region $REGION > /dev/null
    
    echo "Waiting for instance to start..."
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
    
    # Get new public IP (it changes after stop/start)
    NEW_IP=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --region $REGION \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)
    
    echo -e "${GREEN}✅ Instance started successfully${NC}"
    echo -e "${BLUE}📡 New Public IP: $NEW_IP${NC}"
    echo -e "${YELLOW}💡 Wait 2-3 minutes for services to start, then test endpoints${NC}"
    echo ""
    echo -e "${BLUE}Updated Endpoints:${NC}"
    echo "• Coordinator API: http://$NEW_IP:8000"
    echo "• Dashboard: http://$NEW_IP:8000/dashboard"
    echo "• RTMP Ingest: rtmp://$NEW_IP:1935/live/"
}

# Function to set up automated scheduling
setup_schedule() {
    echo -e "${BLUE}⏰ Automated Scheduling Setup${NC}"
    echo "============================="
    echo ""
    echo "You can set up automated start/stop to minimize costs:"
    echo ""
    echo -e "${YELLOW}Option 1: AWS Instance Scheduler${NC}"
    echo "• Automatically start/stop based on schedule"
    echo "• Example: Run only weekdays 9 AM - 6 PM"
    echo "• Can save 60-70% on EC2 costs"
    echo ""
    echo -e "${YELLOW}Option 2: Cron Jobs (Local)${NC}"
    echo "• Set up cron jobs on your local machine"
    echo "• Requires your machine to be on at scheduled times"
    echo ""
    echo -e "${YELLOW}Option 3: Lambda Scheduler${NC}"
    echo "• CloudWatch Events + Lambda functions"
    echo "• Most reliable, always works"
    echo ""
    echo "Would you like me to set up any of these? (Manual setup required)"
}

# Function for emergency cost reduction
emergency_stop() {
    echo -e "${RED}🚨 Emergency Cost Reduction${NC}"
    echo "=========================="
    echo ""
    echo -e "${YELLOW}⚠️ This will stop the EC2 instance immediately${NC}"
    echo "• Database and cache will continue running (can't be stopped)"
    echo "• You'll save ~$5.67/month on EC2 costs"
    echo "• Data will be preserved"
    echo ""
    read -p "Are you sure you want to proceed? (y/N): " confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        pause_instance
        echo ""
        echo -e "${GREEN}✅ Emergency stop completed${NC}"
        echo -e "${BLUE}💡 To resume: $0 resume${NC}"
    else
        echo "Operation cancelled"
    fi
}

# Main script logic
case "${1:-}" in
    "status")
        check_status
        echo ""
        get_cost_estimate
        ;;
    "pause")
        pause_instance
        ;;
    "resume")
        resume_instance
        ;;
    "estimate")
        get_cost_estimate
        ;;
    "schedule")
        setup_schedule
        ;;
    "emergency")
        emergency_stop
        ;;
    "scale-down"|"scale-up")
        echo -e "${YELLOW}⚠️ Database scaling not implemented yet${NC}"
        echo "Database is already at minimum size (db.t3.micro)"
        echo "Scaling would require CloudFormation update"
        ;;
    *)
        usage
        ;;
esac 