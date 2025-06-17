# 🏗️ StreamrP2P CDK Infrastructure Plan

## 🎯 **Final Architecture Decision**

Based on consultation with our zen technical advisors and SRS containerization research, here's our **pragmatic Phase 2A architecture**:

### **✅ Advisor Consensus: Simple & Effective**

Both advisors agreed: **The ECS Fargate approach is over-engineered for Phase 2A**. 

**Key Findings:**
- 🔍 **SRS Containerization**: Community Docker images exist but no official support
- ⚠️ **Session Affinity**: RTMP streams are stateful - container restarts = dropped streams
- 💰 **Cost Reality**: Fargate 3x more expensive than EC2 for our use case
- 🚀 **Speed Priority**: Get friends testing THIS WEEK vs perfect architecture

## 🏗️ **Recommended Architecture: EC2 + Managed Services**

### **Core Infrastructure**
```
┌─────────────────────────────────────────────────────────────┐
│                    Internet Gateway                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Public Subnet                              │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │       ALB       │    │   EC2 Instance  │               │
│  │   (HTTPS/HTTP)  │────▶│   t3.micro      │               │
│  │   Port 443/80   │    │   (Docker)      │               │
│  └─────────────────┘    └─────────┬───────┘               │
│                                   │ Direct RTMP           │
│                                   │ Port 1935             │
└───────────────────────────────────┼───────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────┐
│                 Private Subnet                             │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │  RDS PostgreSQL │    │ ElastiCache     │               │
│  │   db.t3.micro   │    │ cache.t4g.micro │               │
│  │   Port 5432     │    │ Port 6379       │               │
│  └─────────────────┘    └─────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### **Service Mapping**
| Component | AWS Service | Instance Type | Cost |
|-----------|-------------|---------------|------|
| **Coordinator** | EC2 (Docker) | t3.micro | **FREE** (750hrs/month) |
| **Worker** | EC2 (Docker) | t3.micro | **FREE** (same instance) |
| **SRS Streaming** | EC2 (Docker) | t3.micro | **FREE** (same instance) |
| **Database** | RDS PostgreSQL | db.t3.micro | **FREE** (750hrs/month) |
| **Cache** | ElastiCache Redis | cache.t4g.micro | ~$11/month |
| **Load Balancer** | ALB | Standard | ~$16/month |

**Total Monthly Cost: ~$27/month** (vs $100+ for ECS Fargate)

## 📋 **CDK Implementation Plan**

### **Stack Architecture**
```typescript
// Two-stack approach for lifecycle management
1. FoundationStack:    VPC, RDS, ElastiCache (stateful)
2. ApplicationStack:   EC2, ALB, Security Groups (stateless)
```

### **Foundation Stack (Persistent Resources)**
```typescript
export class StreamrFoundationStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // VPC with public/private subnets
    const vpc = new ec2.Vpc(this, 'StreamrVPC', {
      maxAzs: 2,
      natGateways: 0, // Cost optimization - EC2 in public subnet
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
        }
      ]
    });

    // RDS PostgreSQL
    const dbInstance = new rds.DatabaseInstance(this, 'StreamrDB', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_15
      }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
      vpc: vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      databaseName: 'streamr',
      credentials: rds.Credentials.fromGeneratedSecret('streamr'),
      removalPolicy: RemovalPolicy.RETAIN, // CRITICAL: Don't delete data
      backupRetention: Duration.days(7),
    });

    // ElastiCache Redis
    const redisSubnetGroup = new elasticache.CfnSubnetGroup(this, 'RedisSubnetGroup', {
      description: 'Subnet group for StreamrP2P Redis',
      subnetIds: vpc.privateSubnets.map(subnet => subnet.subnetId),
    });

    const redisCluster = new elasticache.CfnCacheCluster(this, 'StreamrRedis', {
      cacheNodeType: 'cache.t4g.micro',
      engine: 'redis',
      numCacheNodes: 1,
      cacheSubnetGroupName: redisSubnetGroup.ref,
      vpcSecurityGroupIds: [redisSecurityGroup.securityGroupId],
    });

    // Outputs for ApplicationStack
    new CfnOutput(this, 'VpcId', { value: vpc.vpcId });
    new CfnOutput(this, 'DatabaseEndpoint', { value: dbInstance.instanceEndpoint.hostname });
    new CfnOutput(this, 'RedisEndpoint', { value: redisCluster.attrRedisEndpointAddress });
  }
}
```

### **Application Stack (Deployable Resources)**
```typescript
export class StreamrApplicationStack extends Stack {
  constructor(scope: Construct, id: string, props: StreamrApplicationStackProps) {
    super(scope, id, props);

    // Security Groups
    const albSecurityGroup = new ec2.SecurityGroup(this, 'ALBSecurityGroup', {
      vpc: props.vpc,
      allowAllOutbound: false,
    });
    albSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80));
    albSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443));

    const ec2SecurityGroup = new ec2.SecurityGroup(this, 'EC2SecurityGroup', {
      vpc: props.vpc,
      allowAllOutbound: true,
    });
    ec2SecurityGroup.addIngressRule(albSecurityGroup, ec2.Port.tcp(8000)); // FastAPI
    ec2SecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(1935)); // RTMP direct
    ec2SecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(8081)); // SRS API
    ec2SecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(22));  // SSH

    // EC2 Instance
    const ec2Instance = new ec2.Instance(this, 'StreamrInstance', {
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
      machineImage: new ec2.AmazonLinuxImage({
        generation: ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
      }),
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
      securityGroup: ec2SecurityGroup,
      keyName: 'mailserver', // Your existing key pair
      userData: ec2.UserData.forLinux(),
    });

    // User Data Script
    ec2Instance.addUserData(
      'yum update -y',
      'yum install -y docker git',
      'systemctl start docker',
      'systemctl enable docker',
      'usermod -aG docker ec2-user',
      'curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose',
      'chmod +x /usr/local/bin/docker-compose',
      'cd /home/ec2-user',
      'git clone https://github.com/your-username/streamr.git', // Your repo
      'cd streamr/coordinator',
      // Set environment variables for RDS and Redis
      `echo "DATABASE_URL=postgresql://streamr:${props.dbPassword}@${props.dbEndpoint}:5432/streamr" > .env`,
      `echo "REDIS_URL=redis://${props.redisEndpoint}:6379" >> .env`,
      'docker-compose up -d --build'
    );

    // Application Load Balancer
    const alb = new elbv2.ApplicationLoadBalancer(this, 'StreamrALB', {
      vpc: props.vpc,
      internetFacing: true,
      securityGroup: albSecurityGroup,
    });

    const listener = alb.addListener('HTTPSListener', {
      port: 443,
      certificates: [props.certificate], // ACM certificate
      defaultAction: elbv2.ListenerAction.fixedResponse(404),
    });

    const targetGroup = new elbv2.ApplicationTargetGroup(this, 'StreamrTargetGroup', {
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      vpc: props.vpc,
      targetType: elbv2.TargetType.INSTANCE,
      targets: [new targets.InstanceTarget(ec2Instance)],
      healthCheck: {
        path: '/health',
        protocol: elbv2.Protocol.HTTP,
        port: '8000',
      },
    });

    listener.addAction('StreamrAction', {
      action: elbv2.ListenerAction.forward([targetGroup]),
    });

    // Outputs
    new CfnOutput(this, 'LoadBalancerDNS', { value: alb.loadBalancerDnsName });
    new CfnOutput(this, 'EC2PublicIP', { value: ec2Instance.instancePublicIp });
  }
}
```

## 🚀 **Deployment Strategy**

### **Phase 2A: This Week**
```bash
# 1. Deploy Foundation (one-time)
cdk deploy StreamrFoundationStack

# 2. Deploy Application (repeatable)
cdk deploy StreamrApplicationStack

# 3. Friends connect to:
# - Web Dashboard: https://streamr-alb-123.eu-west-1.elb.amazonaws.com
# - RTMP Streaming: rtmp://ec2-ip:1935/live/stream_id
```

### **Friend Onboarding**
```bash
# Update setup-friend-node.sh with AWS endpoints
COORDINATOR_URL="https://streamr-alb-123.eu-west-1.elb.amazonaws.com"
RTMP_URL="rtmp://3.248.123.45:1935"  # EC2 public IP
```

## 🔒 **Security Considerations**

### **Immediate (Phase 2A)**
- ✅ RDS in private subnet (no internet access)
- ✅ ElastiCache in private subnet
- ✅ ALB with HTTPS termination
- ✅ Security groups with least privilege
- ⚠️ RTMP direct access (acceptable for friends testing)

### **Phase 2B Hardening**
- 🔐 API key authentication for coordinator
- 🔐 RTMP authentication for streaming
- 🔐 VPN or private networking for RTMP
- 🔐 WAF for ALB protection

## 💰 **Cost Breakdown**

### **Free Tier Eligible**
- EC2 t3.micro: 750 hours/month = **FREE**
- RDS db.t3.micro: 750 hours/month = **FREE**
- ALB: First 750 hours = **FREE**

### **Paid Components**
- ElastiCache cache.t4g.micro: ~$11/month
- ALB beyond free tier: ~$16/month
- Data transfer: ~$0.09/GB

**Total: ~$27/month for Phase 2A testing**

## 📋 **Implementation Checklist**

### **Week 1: Foundation**
- [ ] Create CDK project structure
- [ ] Implement FoundationStack
- [ ] Deploy VPC, RDS, ElastiCache
- [ ] Test database connectivity

### **Week 2: Application**
- [ ] Implement ApplicationStack
- [ ] Configure EC2 user data script
- [ ] Deploy ALB and EC2 instance
- [ ] Test end-to-end deployment

### **Week 3: Friend Testing**
- [ ] Update friend setup scripts
- [ ] Generate API keys for friends
- [ ] Monitor system during friend testing
- [ ] Collect feedback and iterate

## 🎯 **Success Criteria**

**Phase 2A Complete When:**
- ✅ Friends can connect from external networks
- ✅ RTMP streaming works reliably
- ✅ Coordinator dashboard accessible via HTTPS
- ✅ System runs 24/7 without intervention
- ✅ Cost stays under $30/month

**Ready for Phase 2B When:**
- ✅ 5+ friends successfully tested
- ✅ System handles concurrent streams
- ✅ Performance metrics collected
- ✅ Security hardening requirements defined

This pragmatic approach gets StreamrP2P on professional AWS infrastructure **this week** while keeping costs low and complexity manageable! 🚀 