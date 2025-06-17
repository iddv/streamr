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