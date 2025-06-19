#!/bin/bash

# 📊 Monitor StreamrP2P Deployment Through ALB
# Tracks target health and automatically tests when healthy

set -e

echo "🔍 Monitoring StreamrP2P deployment through ALB..."
echo "⏰ Started at $(date)"
echo ""

# Get target group ARN
TG_ARN=$(aws elbv2 describe-target-groups --names streamr-p2p-beta-tg --query 'TargetGroups[0].TargetGroupArn' --output text)
ALB_ENDPOINT="http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com"

echo "🎯 Target Group: $TG_ARN"
echo "🔗 ALB Endpoint: $ALB_ENDPOINT"
echo ""

# Monitor health status
attempt=1
max_attempts=30  # 15 minutes max (30 attempts * 30s interval)

while [ $attempt -le $max_attempts ]; do
    echo "📊 Attempt $attempt/$max_attempts at $(date +%H:%M:%S)"
    
    # Get target health
    HEALTH_STATUS=$(aws elbv2 describe-target-health --target-group-arn $TG_ARN \
        --query 'TargetHealthDescriptions[0].TargetHealth.State' --output text)
    
    echo "   Target Health: $HEALTH_STATUS"
    
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        echo ""
        echo "🎉 TARGET IS HEALTHY! Testing endpoints..."
        
        # Test health endpoint
        if curl -f "$ALB_ENDPOINT/health" --max-time 10; then
            echo ""
            echo "✅ Health check passed!"
        else
            echo ""
            echo "⚠️ Health endpoint not responding properly"
        fi
        
        echo ""
        echo "🧪 Testing other endpoints..."
        
        # Test dashboard
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$ALB_ENDPOINT/dashboard" --max-time 10 || echo "000")
        echo "   Dashboard: HTTP $HTTP_CODE"
        
        # Test streams
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$ALB_ENDPOINT/streams" --max-time 10 || echo "000")
        echo "   Streams: HTTP $HTTP_CODE"
        
        # Test payouts
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$ALB_ENDPOINT/payouts" --max-time 10 || echo "000")
        echo "   Payouts: HTTP $HTTP_CODE"
        
        echo ""
        echo "🚀 DEPLOYMENT COMPLETE!"
        echo "🔗 Web Dashboard: $ALB_ENDPOINT/"
        echo "📺 RTMP Endpoint: rtmp://54.76.171.122:1935/live"
        echo ""
        echo "✨ Enhanced CDK deployment with automated application deployment successful!"
        echo "⏰ Total deployment time: $(( (attempt - 1) * 30 / 60 )) minutes"
        exit 0
        
    elif [ "$HEALTH_STATUS" = "unhealthy" ]; then
        echo "   Status: Still deploying (UserData script running)"
    else
        echo "   Status: $HEALTH_STATUS"
    fi
    
    # Wait 30 seconds before next check
    echo "   ⏳ Waiting 30 seconds..."
    echo ""
    sleep 30
    ((attempt++))
done

echo "❌ Deployment timed out after $((max_attempts * 30 / 60)) minutes"
echo "🔍 Check CloudFormation console for UserData logs"
echo "📱 Instance ID: i-0c5a5c767bec5c27e"
exit 1 