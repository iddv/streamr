# 🏗️ StreamrP2P Infrastructure

AWS CDK infrastructure for the StreamrP2P "restreaming as support" P2P streaming platform.

## 🌐 **Live Beta Environment**

**Status**: ✅ Deployed and Running  
**Region**: eu-west-1 (Ireland)  
**Stage**: beta  

### **Live Endpoints**
- **🎛️ Web Dashboard**: http://streamr-p2p-beta-alb-722019741.eu-west-1.elb.amazonaws.com/
- **📡 RTMP Streaming**: `rtmp://108.130.35.167:1935/live`
- **🖥️ EC2 Instance**: i-0ac35c7a6284b6b49 (108.130.35.167)
- **🗄️ PostgreSQL**: streamr-p2p-beta-db.c3q28wieso7a.eu-west-1.rds.amazonaws.com:5432
- **⚡ Redis Cache**: streamr-p2p-beta-cache.e6qheu.0001.euw1.cache.amazonaws.com:6379

### **SSH Access**
```bash
ssh -i ~/.ssh/mailserver.pem ec2-user@108.130.35.167
```

## 🎯 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │   Application   │    │   Foundation    │    │   Compute    │ │
│  │   Load Balancer │    │   VPC Network   │    │   EC2 + SRS  │ │
│  │                 │    │                 │    │              │ │
│  │  ┌───────────┐  │    │  ┌───────────┐  │    │ ┌──────────┐ │ │
│  │  │    ALB    │  │    │  │    VPC    │  │    │ │ Docker   │ │ │
│  │  │  (HTTP)   │  │    │  │  Subnets  │  │    │ │ Compose  │ │ │
│  │  └───────────┘  │    │  └───────────┘  │    │ └──────────┘ │ │
│  └─────────────────┘    └─────────────────┘    └──────────────┘ │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │   Database      │    │   Cache         │                    │
│  │   RDS Postgres  │    │   ElastiCache   │                    │
│  │                 │    │   Redis         │                    │
│  │  ┌───────────┐  │    │  ┌───────────┐  │                    │
│  │  │ PostgreSQL│  │    │  │   Redis   │  │                    │
│  │  │  15.4     │  │    │  │  Cluster  │  │                    │
│  │  └───────────┘  │    │  └───────────┘  │                    │
│  └─────────────────┘    └─────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

## 🎭 Multi-Stage Configuration

### Beta Stage
- **Purpose**: Experiments and iterative changes
- **Instance**: t3.micro
- **Protection**: None (easy teardown)
- **Monitoring**: Basic
- **SSH Access**: ✅ Enabled

### Gamma Stage  
- **Purpose**: Pre-prod stable continuous testing (friends testing)
- **Instance**: t3.small
- **Protection**: Deletion protection enabled
- **Monitoring**: Detailed with alarms
- **SSH Access**: ✅ Enabled

### Prod Stage
- **Purpose**: Live operations
- **Instance**: t3.medium
- **Protection**: Full protection + Multi-AZ
- **Monitoring**: Full monitoring with alarms
- **SSH Access**: ❌ Disabled

## 🌍 Multi-Region Support

| Region | Name | Primary | AZs |
|--------|------|---------|-----|
| eu-west-1 | ireland | ✅ Primary | 2 |
| us-east-1 | virginia | Secondary | 3 |
| ap-southeast-1 | singapore | Secondary | 3 |

## 🚀 Quick Start (Beta Stage)

### Prerequisites
```bash
# Install AWS CDK
npm install -g aws-cdk

# Configure AWS credentials
aws configure

# Verify setup
aws sts get-caller-identity
```

### Deploy Beta Stage
```bash
# Navigate to infrastructure directory
cd infrastructure

# Install dependencies
npm install

# Deploy to beta stage (eu-west-1)
./scripts/deploy-beta.sh

# Deploy to different region
./scripts/deploy-beta.sh us-east-1
```

### Deploy Other Stages
```bash
# Deploy gamma stage
npx cdk deploy --context stage=gamma --context region=eu-west-1 --all

# Deploy prod stage
npx cdk deploy --context stage=prod --context region=eu-west-1 --all
```

## 📁 Project Structure

```
infrastructure/
├── bin/
│   └── infrastructure.ts          # Main CDK app entry point
├── lib/
│   ├── config/
│   │   ├── types.ts               # TypeScript interfaces
│   │   ├── streamr-config.ts      # Main configuration
│   │   └── deployment-context.ts  # Context utilities
│   └── stacks/
│       ├── foundation-stack.ts    # VPC, RDS, ElastiCache
│       └── application-stack.ts   # EC2, ALB, Security Groups
├── scripts/
│   └── deploy-beta.sh            # Beta deployment script
├── test/                         # CDK unit tests
├── cdk.json                      # CDK configuration
└── package.json                  # Dependencies
```

## ⚙️ Configuration

All configuration is centralized in `lib/config/streamr-config.ts`:

```typescript
// Example: Adding a new region
regions: {
  'eu-central-1': {
    region: 'eu-central-1',
    name: 'frankfurt',
    isPrimary: false,
    availabilityZones: 3,
  },
}

// Example: Adding a new stage
stages: {
  staging: {
    name: 'staging',
    description: 'Staging environment for QA',
    isProd: false,
    enableDeletionProtection: true,
    instanceSize: 'small',
    // ... other config
  },
}
```

## 🔧 Useful Commands

### Development
```bash
# Synthesize CloudFormation templates
npx cdk synth --context stage=beta

# Compare deployed stack with current state
npx cdk diff --context stage=beta

# List all stacks
npx cdk list --context stage=beta

# View stack outputs
aws cloudformation describe-stacks --stack-name streamr-p2p-beta-ireland-foundation
```

### Deployment
```bash
# Deploy specific stack
npx cdk deploy streamr-p2p-beta-ireland-foundation --context stage=beta

# Deploy all stacks
npx cdk deploy --all --context stage=beta

# Destroy stacks (be careful!)
npx cdk destroy --all --context stage=beta
```

### Instance Management
```bash
# Get instance public IP
aws ec2 describe-instances \
  --filters 'Name=tag:Name,Values=streamr-p2p-beta-instance' \
  --query 'Reservations[].Instances[].PublicIpAddress' \
  --output text

# SSH to instance
ssh -i ~/.ssh/mailserver.pem ec2-user@<INSTANCE_IP>

# View instance logs
aws logs tail /aws/ec2/streamr-p2p --follow
```

## 🔒 Security Features

### Network Security
- **VPC Isolation**: Private subnets for database and cache
- **Security Groups**: Least-privilege access rules
- **RTMP Direct Access**: Port 1935 bypasses ALB for streaming performance
- **SSH Access**: Controlled by stage (disabled in prod)

### IAM Security
- **Instance Role**: Minimal permissions for secrets and monitoring
- **Secrets Manager**: Database credentials auto-generated and rotated
- **CloudWatch**: Centralized logging and monitoring

### Data Protection
- **Encryption**: RDS and EBS encryption enabled
- **Backups**: Automated backups based on stage
- **Deletion Protection**: Enabled for gamma/prod stages

## 🎛️ Monitoring & Observability

### CloudWatch Integration
- **Instance Metrics**: CPU, memory, disk, network
- **Application Logs**: Centralized logging via CloudWatch agent
- **Custom Metrics**: StreamrP2P-specific metrics (planned)
- **Alarms**: Automated alerting for gamma/prod stages

### Health Checks
- **ALB Health Check**: `/health` endpoint on port 8000
- **Instance Status**: EC2 status checks
- **Application Health**: Custom health monitoring (planned)

## 💰 Cost Optimization

### Beta Stage (~$27/month)
- t3.micro instances
- No Multi-AZ
- Minimal backups
- Basic monitoring

### Gamma Stage (~$45/month)
- t3.small instances
- Single-AZ with backups
- Detailed monitoring
- 7-day backup retention

### Prod Stage (~$120/month)
- t3.medium instances
- Multi-AZ deployment
- Full monitoring and alarms
- 30-day backup retention

## 🔄 CI/CD Integration (Future)

Planned integration with GitHub Actions:

```yaml
# .github/workflows/deploy.yml
- name: Deploy to Beta
  run: |
    cd infrastructure
    npx cdk deploy --context stage=beta --require-approval never

- name: Deploy to Gamma (on main branch)
  run: |
    cd infrastructure
    npx cdk deploy --context stage=gamma --require-approval never
```

## 🆘 Troubleshooting

### Common Issues

**CDK Bootstrap Error**
```bash
# Bootstrap CDK in your region
npx cdk bootstrap --region eu-west-1
```

**Permission Denied**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Ensure IAM permissions for CDK deployment
```

**Stack Dependency Error**
```bash
# Deploy foundation stack first
npx cdk deploy streamr-p2p-beta-ireland-foundation --context stage=beta
```

### Getting Help

1. **Check CloudFormation Events**: AWS Console → CloudFormation → Stack → Events
2. **View CDK Logs**: `npx cdk deploy --verbose`
3. **Instance Logs**: SSH to instance and check `/var/log/cloud-init-output.log`

## 🎯 Next Steps

1. **Deploy Beta**: Get your first AWS deployment running
2. **Application Deployment**: Deploy StreamrP2P code to the instance
3. **Domain Setup**: Configure Route53 and SSL certificates
4. **Monitoring**: Set up custom dashboards and alerts
5. **Multi-Region**: Expand to additional regions
6. **CI/CD**: Automate deployments with GitHub Actions

---

**Ready to deploy?** Run `./scripts/deploy-beta.sh` and get your StreamrP2P platform running in the cloud! 🚀
# Fresh deployment after database migration fix
# Trigger deployment after rollback
