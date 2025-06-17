# 🌐 StreamrP2P Live Beta Endpoints

**Status**: ✅ Live and Running  
**Region**: eu-west-1 (Ireland)  
**Stage**: beta  
**Last Updated**: June 18, 2025  

---

## 🚀 **Quick Access**

### **SSH to Instance**
```bash
ssh -i ~/.ssh/mailserver.pem ec2-user@108.130.35.167
```

### **Run Sanity Tests**
```bash
./infrastructure/scripts/sanity-test.sh
```

---

## 🌐 **Live Endpoints**

### **🎛️ Web Dashboard** *(After App Deployment)*
```
http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/
```

### **📡 RTMP Streaming** *(After App Deployment)*
```
rtmp://108.130.35.167:1935/live
```

### **🖥️ EC2 Instance**
- **Instance ID**: i-0ac35c7a6284b6b49
- **Public IP**: 108.130.35.167
- **Instance Type**: t3.micro
- **SSH Key**: mailserver.pem

### **🌐 Load Balancer**
```
streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com
```

### **🗄️ PostgreSQL Database**
- **Endpoint**: streamr-p2p-beta-db.c3q28wieso7a.eu-west-1.rds.amazonaws.com
- **Port**: 5432
- **Database**: streamr
- **Credentials**: AWS Secrets Manager (`streamr-p2p-beta-db-credentials`)

### **⚡ Redis Cache**
- **Endpoint**: streamr-p2p-beta-cache.e6qheu.0001.euw1.cache.amazonaws.com
- **Port**: 6379

---

## 🔧 **AWS Resource Information**

### **CloudFormation Stacks**
- **Foundation**: streamr-p2p-beta-ireland-foundation
- **Application**: streamr-p2p-beta-ireland-application

### **Security Groups**
- **Instance SG**: sg-09766b60ffc982ad4
- **ALB SG**: (auto-generated)
- **Database SG**: (auto-generated)
- **Cache SG**: (auto-generated)

### **IAM Roles**
- **Instance Role**: streamr-p2p-beta-instance-role
- **Permissions**: Secrets Manager, CloudWatch, CloudFormation signaling

---

## 💰 **Cost Information**

**Monthly Estimate**: ~$27/month
- EC2 t3.micro: ~$8.50
- RDS db.t3.micro: ~$12.00
- ElastiCache cache.t4g.micro: ~$6.00
- ALB: ~$0.50

---

## 🧪 **Health Status**

### **Infrastructure** ✅
- CloudFormation stacks: CREATE_COMPLETE
- EC2 instance: running
- Database: available
- Cache: available

### **Application** ⚠️ 
- ALB target health: unhealthy (no app deployed yet)
- HTTP endpoints: 502 (expected)
- RTMP port: not accessible (expected)

**Note**: Application layer issues are expected until StreamrP2P is deployed to the instance.

---

## 📝 **Useful Commands**

### **AWS CLI Commands**
```bash
# Check stack status
aws cloudformation describe-stacks --stack-name streamr-p2p-beta-ireland-foundation --region eu-west-1

# Check instance status
aws ec2 describe-instances --instance-ids i-0ac35c7a6284b6b49 --region eu-west-1

# Check ALB target health
aws elbv2 describe-target-health --region eu-west-1 \
  --target-group-arn $(aws elbv2 describe-target-groups \
  --region eu-west-1 --names streamr-p2p-beta-tg \
  --query 'TargetGroups[0].TargetGroupArn' --output text)
```

### **Instance Commands** *(After SSH)*
```bash
# Check Docker status
sudo systemctl status docker

# View cloud-init logs
sudo journalctl -u cloud-init -f

# Check instance metadata
curl http://169.254.169.254/latest/meta-data/instance-id
```

---

## 🎯 **Next Steps**

1. **Deploy StreamrP2P Application** to EC2 instance
2. **Configure Environment Variables** (database, cache connections)
3. **Start Services** (coordinator, SRS, monitoring)
4. **Verify Health Endpoints** (ALB target becomes healthy)
5. **Begin Friends Testing** 🚀

---

*For detailed test results, see `docs/testing/BETA_INFRASTRUCTURE_TEST_RESULTS.md`* 

# StreamrP2P Live Endpoints - Phase 2C Complete

## 🎉 Application Successfully Deployed!

**Status**: Phase 2C Complete - Application deployed and operational  
**Progress**: 90% complete (Phase 2D: Friends Testing remaining)  
**Infrastructure**: AWS eu-west-1 (Ireland)  
**Deployment Date**: June 17, 2025  

## 🌐 Live Service Endpoints

### Primary Application (via ALB - Recommended)
- **API Root**: http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/
- **Health Check**: http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/health
- **Dashboard**: http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/dashboard
- **Stream Management**: http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/streams
- **Node Heartbeat**: http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/nodes/heartbeat
- **Payouts**: http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/payouts
- **Leaderboard**: http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/leaderboard

### Streaming Services (Direct Instance Access)
- **RTMP Ingest**: rtmp://34.245.123.90:1935/live/{stream_key}
- **HLS Playback**: http://34.245.123.90:8085/live/{stream_key}.m3u8
- **SRS HTTP-FLV**: http://34.245.123.90:8085/live/{stream_key}.flv

### Infrastructure Details
- **Instance**: i-0c5a5c767bec5c27e (34.245.123.90)
- **Load Balancer**: streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com
- **Database**: streamr-p2p-beta-db.c3q28wieso7a.eu-west-1.rds.amazonaws.com:5432
- **Cache**: streamr-p2p-beta-cache.e6qheu.0001.euw1.cache.amazonaws.com:6379
- **SSH Access**: `ssh -i ~/.ssh/streamr-beta-key.pem ec2-user@34.245.123.90`

## 🧪 Testing Commands

### Test API
```bash
# Health check
curl http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/health

# View dashboard
curl http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/dashboard

# Register a test stream
curl -X POST http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/streams \
  -H "Content-Type: application/json" \
  -d '{"stream_id":"test123","sponsor_address":"0x123","token_balance":1000,"rtmp_url":"rtmp://34.245.123.90:1935/live/test123"}'
```

### Test Streaming
```bash
# Stream a test video (requires ffmpeg)
ffmpeg -re -i test.mp4 -c copy -f flv rtmp://34.245.123.90:1935/live/test123

# View stream via HLS
curl http://34.245.123.90:8085/live/test123.m3u8
```

## 💰 Cost Management

### Current Monthly Costs (~$45/month)
- **EC2 t3.micro**: ~$8.50/month (24/7) or ~$2.83/month (8h/day)
- **RDS PostgreSQL db.t3.micro**: ~$13.00/month (cannot be stopped)
- **ElastiCache Redis cache.t3.micro**: ~$5.50/month (cannot be stopped)
- **Application Load Balancer**: ~$16.20/month (cannot be stopped)
- **Data Transfer**: ~$1.00/month
- **CloudWatch Logs**: ~$0.50/month

### Cost Optimization Options

#### 1. **Stop EC2 When Not Testing** (Save ~$5.67/month)
```bash
# Stop instance (saves ~$5.67/month)
./infrastructure/scripts/cost-control.sh pause

# Resume for testing (IP will change)
./infrastructure/scripts/cost-control.sh resume

# Check current status and costs
./infrastructure/scripts/cost-control.sh status
```

#### 2. **Scheduled Automation** (Save 60-70% on EC2)
- **Weekdays only**: 9 AM - 6 PM saves ~$5.10/month
- **Weekends only**: Save ~$6.12/month  
- **Evening hours**: 6 PM - 10 PM saves ~$6.80/month

#### 3. **Emergency Cost Reduction**
```bash
# Immediate stop with confirmation
./infrastructure/scripts/cost-control.sh emergency
```

### **Minimum Possible Cost**: ~$36.20/month (EC2 stopped)
- Database, cache, and ALB continue running (needed for data persistence)
- EC2 can be started/stopped as needed for testing
- **Data is preserved** when EC2 is stopped

## 🔧 Management Commands

### Application Management
```bash
# View container status
ssh -i ~/.ssh/streamr-beta-key.pem ec2-user@34.245.123.90 "cd /opt/streamr-coordinator && docker-compose ps"

# View logs
ssh -i ~/.ssh/streamr-beta-key.pem ec2-user@34.245.123.90 "cd /opt/streamr-coordinator && docker-compose logs -f coordinator"

# Restart services
ssh -i ~/.ssh/streamr-beta-key.pem ec2-user@34.245.123.90 "cd /opt/streamr-coordinator && docker-compose restart"
```

### Infrastructure Management
```bash
# Cost control
./infrastructure/scripts/cost-control.sh status
./infrastructure/scripts/cost-control.sh pause
./infrastructure/scripts/cost-control.sh resume

# Infrastructure validation
./infrastructure/scripts/sanity-test.sh

# Redeploy application
./infrastructure/scripts/deploy-application.sh
```

## 🚀 Next Steps: Phase 2D - Friends Testing

1. **Share endpoints** with friends for testing
2. **Create test streams** using the RTMP endpoint
3. **Monitor costs** using the cost-control script
4. **Scale testing** based on feedback
5. **Optimize** based on usage patterns

## 🔒 Security Notes

- **Database & Cache**: Properly isolated, not externally accessible
- **Application**: Accessible via ALB only (production security)
- **RTMP & HLS**: Direct instance access for streaming performance
- **SSH**: Enabled for beta testing and debugging
- **ALB**: Handles all HTTP/HTTPS traffic securely

## 📊 Success Metrics

- ✅ **Infrastructure**: Deployed and validated
- ✅ **Application**: Running and responding to requests
- ✅ **Database**: Connected and operational
- ✅ **Streaming**: SRS server ready for RTMP/HLS
- ✅ **Security**: Production-grade security groups
- ✅ **Cost Controls**: Pause/resume functionality implemented
- ✅ **Monitoring**: Health checks and logging operational

**Ready for Phase 2D: Friends Testing! 🎉** 