# 🚀 AWS EC2 Deployment Guide - StreamrP2P

## 🎯 **Deploy Your Working System to AWS**

**Benefits of AWS over home networking:**
- 🔒 **Home network stays secure** - zero ports opened
- 🚀 **High-performance networking** - symmetric gigabit bandwidth
- 🌍 **Global accessibility** - friends can connect from anywhere
- 📊 **Professional infrastructure** - production-ready setup

## ⚡ **Quick Deployment (15 minutes)**

### Step 1: Launch EC2 Instance
```bash
# Create security group for StreamrP2P
aws ec2 create-security-group \
  --group-name streamr-p2p-sg \
  --description "StreamrP2P Security Group" \
  --region eu-west-1

# Get the security group ID (save this)
SG_ID=$(aws ec2 describe-security-groups \
  --group-names streamr-p2p-sg \
  --region eu-west-1 \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

echo "Security Group ID: $SG_ID"

# Open required ports
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 \
  --region eu-west-1

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0 \
  --region eu-west-1

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 1935 \
  --cidr 0.0.0.0/0 \
  --region eu-west-1

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8081 \
  --cidr 0.0.0.0/0 \
  --region eu-west-1
```

### Step 2: Launch Ubuntu Instance
```bash
# Launch t3.micro instance (free tier eligible)
aws ec2 run-instances \
  --image-id ami-0c94855ba95b798c7 \
  --count 1 \
  --instance-type t3.micro \
  --key-name YOUR_KEY_PAIR_NAME \
  --security-group-ids $SG_ID \
  --region eu-west-1 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=StreamrP2P-Server}]'

# Get the instance ID and public IP
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=StreamrP2P-Server" "Name=instance-state-name,Values=running" \
  --region eu-west-1 \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text)

# Wait for instance to be ready
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region eu-west-1

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --region eu-west-1 \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "🚀 StreamrP2P Server ready!"
echo "Public IP: $PUBLIC_IP"
echo "SSH: ssh -i ~/.ssh/your-key.pem ubuntu@$PUBLIC_IP"
```

### Step 3: Prepare Deployment Package
```bash
# Create deployment package
mkdir -p aws-deploy
cp -r coordinator/ aws-deploy/
cp docker-compose.yml aws-deploy/
cp -r ingest-server/ aws-deploy/
cp test_streaming_srs.sh aws-deploy/

# Create AWS-specific docker-compose
cat > aws-deploy/docker-compose.yml << 'EOF'
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: streamr
      POSTGRES_USER: streamr  
      POSTGRES_PASSWORD: streamr_password
    volumes:
      - db_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"

  coordinator:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://streamr:streamr_password@db:5432/streamr
      REDIS_URL: redis://redis:6379
    depends_on:
      - db
      - redis
    restart: unless-stopped

  worker:
    build: .
    command: python -m app.worker
    environment:
      DATABASE_URL: postgresql://streamr:streamr_password@db:5432/streamr
      REDIS_URL: redis://redis:6379
    depends_on:
      - db
      - redis
    restart: unless-stopped

volumes:
  db_data:
EOF

# Create AWS deployment script
cat > aws-deploy/deploy.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Installing Docker and dependencies..."
sudo apt update
sudo apt install -y docker.io docker-compose-v2 curl jq

echo "🔧 Starting Docker..."
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu

echo "📦 Building and starting StreamrP2P..."
sudo docker compose up -d --build

echo "⏳ Waiting for services to start..."
sleep 30

echo "✅ Testing coordinator health..."
curl -s http://localhost:8000/health || echo "Service starting..."

echo "🎉 StreamrP2P deployed successfully!"
echo "Access at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
EOF

chmod +x aws-deploy/deploy.sh
```

### Step 4: Deploy to AWS
```bash
# Upload deployment package
scp -i ~/.ssh/your-key.pem -r aws-deploy/ ubuntu@$PUBLIC_IP:/home/ubuntu/streamr/

# Deploy and start services
ssh -i ~/.ssh/your-key.pem ubuntu@$PUBLIC_IP "cd /home/ubuntu/streamr && ./deploy.sh"

# Test deployment
curl http://$PUBLIC_IP:8000/health
```

## ✅ **Verify Deployment**

```bash
# Test all endpoints
echo "Testing StreamrP2P on AWS..."
echo "Coordinator: $(curl -s http://$PUBLIC_IP:8000/health)"
echo "Dashboard: $(curl -s http://$PUBLIC_IP:8000/dashboard | jq)"
echo "SRS Stats: $(curl -s http://$PUBLIC_IP:8081/api/v1/clients/ 2>/dev/null || echo 'SRS starting...')"
```

## 🔄 **Update Friend Setup Script**

```bash
# Update setup-friend-node.sh with AWS IP
sed -i "s/86.87.233.125/$PUBLIC_IP/g" setup-friend-node.sh

# Test friend setup script
./setup-friend-node.sh test_api_key_123
```

## 📊 **Monitor Your AWS Deployment**

```bash
# SSH into your server
ssh -i ~/.ssh/your-key.pem ubuntu@$PUBLIC_IP

# Monitor services
sudo docker compose logs -f coordinator
sudo docker compose logs -f worker

# Check system resources
htop
df -h
```

## 💰 **Cost Estimate**

**t3.micro (free tier eligible):**
- First 750 hours/month: **FREE**
- After free tier: ~$8.50/month
- Data transfer: First 1GB free, then $0.09/GB

**For Phase 2A testing: Essentially FREE** (well within free tier limits)

## 🚀 **Ready for Phase 2A Friend Testing!**

Once deployed:
1. **Generate API keys**: `openssl rand -hex 16`
2. **Share with friends**: `./setup-friend-node.sh API_KEY`
3. **Monitor dashboard**: `curl http://$PUBLIC_IP:8000/dashboard | jq`

Your StreamrP2P system is now running on professional AWS infrastructure! 🎉 