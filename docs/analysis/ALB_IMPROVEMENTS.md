# 🔄 ALB Improvements for StreamrP2P

**Current State**: ALB configured with basic health checks  
**Goal**: Production-ready load balancer setup with proper monitoring

---

## ✅ **Current ALB Configuration (Good)**

```typescript
// Already implemented in application-stack.ts
healthCheck: {
  enabled: true,
  path: '/health',
  protocol: elbv2.Protocol.HTTP,
  port: '8000',
  healthyThresholdCount: 2,
  unhealthyThresholdCount: 3,
  timeout: cdk.Duration.seconds(5),
  interval: cdk.Duration.seconds(30),
}
```

**What works well**:
- ✅ Health checks on `/health` endpoint
- ✅ Proper thresholds for healthy/unhealthy detection
- ✅ Security groups allowing HTTP/HTTPS traffic
- ✅ Target group pointing to EC2 instance

---

## 🚀 **Recommended Improvements**

### **1. Enhanced Health Check Configuration**
```typescript
// Better health check settings
healthCheck: {
  enabled: true,
  path: '/health',
  protocol: elbv2.Protocol.HTTP,
  port: '8000',
  healthyThresholdCount: 2,
  unhealthyThresholdCount: 3,
  timeout: cdk.Duration.seconds(10),     // Increased from 5s
  interval: cdk.Duration.seconds(15),    // Reduced from 30s (faster detection)
  healthyHttpCodes: '200',               // Only accept 200 status
}
```

### **2. HTTP to HTTPS Redirect**
```typescript
// Add HTTPS listener (when SSL certificate available)
const httpsListener = this.loadBalancer.addListener('HTTPSListener', {
  port: 443,
  protocol: elbv2.ApplicationProtocol.HTTPS,
  certificates: [certificate], // ACM certificate
  defaultTargetGroups: [targetGroup],
});

// Redirect HTTP to HTTPS
this.loadBalancer.addListener('HTTPRedirect', {
  port: 80,
  protocol: elbv2.ApplicationProtocol.HTTP,
  defaultAction: elbv2.ListenerAction.redirect({
    protocol: 'HTTPS',
    port: '443',
    permanent: true,
  }),
});
```

### **3. Enhanced Monitoring**
```typescript
// CloudWatch alarms for ALB health
const unhealthyTargetAlarm = new cloudwatch.Alarm(this, 'UnhealthyTargets', {
  metric: targetGroup.metricUnhealthyHostCount(),
  threshold: 1,
  evaluationPeriods: 2,
  treatMissingData: cloudwatch.TreatMissingData.BREACHING,
});

const responseTimeAlarm = new cloudwatch.Alarm(this, 'HighResponseTime', {
  metric: targetGroup.metricTargetResponseTime(),
  threshold: 5, // 5 seconds
  evaluationPeriods: 3,
});
```

### **4. Access Logging**
```typescript
// Enable ALB access logs
const accessLogsBucket = new s3.Bucket(this, 'ALBAccessLogs', {
  bucketName: context.resourceName('alb-logs'),
  lifecycleRules: [{
    expiration: cdk.Duration.days(30),
  }],
});

this.loadBalancer.logAccessLogs(accessLogsBucket);
```

### **5. Sticky Sessions (if needed)**
```typescript
// For session persistence
targetGroup.enableCookieStickiness(cdk.Duration.hours(1));
```

### **6. Advanced Target Group Attributes**
```typescript
// Better target group configuration
const targetGroup = new elbv2.ApplicationTargetGroup(this, 'TargetGroup', {
  targetGroupName: context.resourceName('tg'),
  port: 8000,
  protocol: elbv2.ApplicationProtocol.HTTP,
  vpc,
  targets: [new elbv2_targets.InstanceTarget(this.instance)],
  
  // Advanced settings
  deregistrationDelay: cdk.Duration.seconds(30), // Faster shutdown
  stickinessCookieDuration: cdk.Duration.hours(1),
  stickinessCookieName: 'streamr-session',
  
  healthCheck: {
    enabled: true,
    path: '/health',
    protocol: elbv2.Protocol.HTTP,
    port: '8000',
    healthyThresholdCount: 2,
    unhealthyThresholdCount: 3,
    timeout: cdk.Duration.seconds(10),
    interval: cdk.Duration.seconds(15),
    healthyHttpCodes: '200',
  },
});
```

---

## 🎯 **Testing Strategy**

### **Current Testing (Good)**
```bash
# Use ALB endpoint instead of EC2 direct
curl http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/health
```

### **Enhanced Testing**
```bash
# Test all endpoints through ALB
curl http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/dashboard
curl http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/streams
curl http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/payouts

# Test load balancer health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names streamr-p2p-beta-tg \
    --query 'TargetGroups[0].TargetGroupArn' --output text)
```

### **Monitoring Commands**
```bash
# Check ALB metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/streamr-p2p-beta-alb/xyz \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# Check target health
aws elbv2 describe-target-health --target-group-arn $TG_ARN
```

---

## 📊 **ALB vs Direct EC2 Benefits**

| Aspect | Direct EC2 | Through ALB |
|--------|------------|-------------|
| **Health Monitoring** | Manual | ✅ Automatic |
| **High Availability** | Single point of failure | ✅ Multi-AZ ready |
| **SSL Termination** | Application handles | ✅ ALB handles |
| **Monitoring** | CloudWatch basic | ✅ Rich ALB metrics |
| **Scaling** | Manual | ✅ Auto Scaling ready |
| **Security** | Direct exposure | ✅ Security layer |

---

## 🚀 **Implementation Priority**

### **Phase 1: Use ALB for Everything (NOW)**
- ✅ Test all endpoints through ALB
- ✅ Update documentation to use ALB endpoints
- ✅ Configure monitoring dashboards

### **Phase 2: SSL Certificate (Next Week)**
- 🔄 Get ACM certificate
- 🔄 Add HTTPS listener
- 🔄 Redirect HTTP to HTTPS

### **Phase 3: Enhanced Monitoring (Month 2)**
- 🔄 CloudWatch alarms
- 🔄 Access logging
- 🔄 Performance monitoring

### **Phase 4: Auto Scaling (Phase 3)**
- 🔄 Target group for multiple instances
- 🔄 Auto Scaling Group integration
- 🔄 Blue/green deployments

---

## 🎯 **Success Metrics**

### **Current Goal**
- ✅ All API calls go through ALB
- ✅ Health checks work properly
- ✅ No direct EC2 access needed

### **Future Goals** 
- 🎯 99.9% uptime through ALB
- 🎯 Sub-second response times
- 🎯 Automatic failover capability
- 🎯 Zero-downtime deployments

---

*Using ALB as the single entry point enables proper high availability, monitoring, and scaling capabilities for StreamrP2P.* 