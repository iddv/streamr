import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as elbv2_targets from 'aws-cdk-lib/aws-elasticloadbalancingv2-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { DeploymentContext } from '../config/types';
import { streamrConfig } from '../config/streamr-config';

export interface ApplicationStackProps extends cdk.StackProps {
  readonly context: DeploymentContext;
  readonly vpc: ec2.IVpc;
  readonly dbSecurityGroup: ec2.SecurityGroup;
  readonly cacheSecurityGroup: ec2.SecurityGroup;
  readonly deploymentBucket: s3.IBucket;
}

export class ApplicationStack extends cdk.Stack {
  public readonly instance: ec2.Instance;
  public readonly loadBalancer: elbv2.ApplicationLoadBalancer;
  public readonly instanceSecurityGroup: ec2.SecurityGroup;
  public readonly elasticIp: ec2.CfnEIP;

  constructor(scope: Construct, id: string, props: ApplicationStackProps) {
    super(scope, id, props);

    const { context, vpc, dbSecurityGroup, cacheSecurityGroup, deploymentBucket } = props;
    const { stageConfig } = context;

    // Tags for all resources in this stack
    cdk.Tags.of(this).add('Project', streamrConfig.app.name);
    cdk.Tags.of(this).add('Stage', context.stage);
    cdk.Tags.of(this).add('Region', context.region);
    cdk.Tags.of(this).add('Owner', streamrConfig.app.owner);

    // Security Group for EC2 Instance
    this.instanceSecurityGroup = new ec2.SecurityGroup(this, 'InstanceSecurityGroup', {
      vpc,
      securityGroupName: context.resourceName('instance-sg'),
      description: `EC2 instance security group for ${context.stage} stage`,
      allowAllOutbound: true,
    });

    // Security Group for ALB
    const albSecurityGroup = new ec2.SecurityGroup(this, 'ALBSecurityGroup', {
      vpc,
      securityGroupName: context.resourceName('alb-sg'),
      description: `ALB security group for ${context.stage} stage`,
      allowAllOutbound: true,
    });

    // Allow HTTP and HTTPS traffic to ALB
    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(80),
      'Allow HTTP traffic'
    );
    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      'Allow HTTPS traffic'
    );

    // 🎯 IMPROVED: Allow SRS HTTP/HLS traffic to ALB (port 8080)
    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(8080),
      'Allow SRS HTTP/HLS streaming traffic to ALB'
    );

    // Allow RTMP traffic directly to instance (RTMP requires TCP, ALB is HTTP-only)
    this.instanceSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(1935),
      'Allow RTMP streaming traffic (direct access only)'
    );

    // Allow HTTP traffic from ALB to instance (coordinator API)
    this.instanceSecurityGroup.addIngressRule(
      albSecurityGroup,
      ec2.Port.tcp(8000),
      'Allow HTTP traffic from ALB to coordinator'
    );

    // 🎯 IMPROVED: Allow SRS HTTP/HLS traffic from ALB to instance  
    this.instanceSecurityGroup.addIngressRule(
      albSecurityGroup,
      ec2.Port.tcp(8080),
      'Allow SRS HTTP/HLS traffic from ALB to instance'  
    );

    // Allow SSH access (for beta stage only)
    if (!stageConfig.isProd) {
      this.instanceSecurityGroup.addIngressRule(
        ec2.Peer.anyIpv4(),
        ec2.Port.tcp(22),
        'Allow SSH access (non-prod only)'
      );
    }

    // Add egress rules to instance security group to connect to database and cache
    this.instanceSecurityGroup.addEgressRule(
      ec2.Peer.ipv4(vpc.vpcCidrBlock),
      ec2.Port.tcp(streamrConfig.database.port),
      'Allow database access from application'
    );

    this.instanceSecurityGroup.addEgressRule(
      ec2.Peer.ipv4(vpc.vpcCidrBlock),
      ec2.Port.tcp(streamrConfig.cache.port),
      'Allow cache access from application'
    );

    // IAM Role for EC2 Instance
    const instanceRole = new iam.Role(this, 'InstanceRole', {
      roleName: context.resourceName('instance-role'),
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
      ],
    });

    // Allow instance to read secrets
    instanceRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
        'secretsmanager:DescribeSecret',
      ],
      resources: [`arn:aws:secretsmanager:${context.region}:*:secret:${context.resourceName('db-credentials')}*`],
    }));

    // Allow instance to signal CloudFormation
    instanceRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'cloudformation:SignalResource',
        'cloudformation:DescribeStacks',
      ],
      resources: [
        `arn:aws:cloudformation:${context.region}:*:stack/${this.stackName}/*`,
        `arn:aws:cloudformation:${context.region}:*:stack/${context.stackName('foundation')}/*`,
      ],
    }));

    // Allow instance to access deployment bucket
    instanceRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:ListBucket',
      ],
      resources: [
        deploymentBucket.bucketArn,
        `${deploymentBucket.bucketArn}/*`,
      ],
    }));

    // Key Pair for SSH access (beta stage only)
    let keyName: string | undefined;
    if (!stageConfig.isProd) {
      keyName = 'streamr-beta-key'; // Use StreamrP2P-specific key pair
    }

    // User Data Script
    const userData = ec2.UserData.forLinux();

    // EC2 Instance
    this.instance = new ec2.Instance(this, 'Instance', {
      instanceName: context.resourceName('instance'),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T3,
        this.getInstanceSize(stageConfig.instanceSize)
      ),
      machineImage: ec2.MachineImage.latestAmazonLinux2023(),
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      securityGroup: this.instanceSecurityGroup,
      role: instanceRole,
      userData,
      keyName,
      detailedMonitoring: stageConfig.monitoring.detailed,
    });

    // 🎯 STABLE ENDPOINT SOLUTION: Elastic IP for permanent IP address
    this.elasticIp = new ec2.CfnEIP(this, 'ElasticIP', {
      domain: 'vpc',
      tags: [
        {
          key: 'Name',
          value: context.resourceName('elastic-ip'),
        },
        {
          key: 'Project',
          value: streamrConfig.app.name,
        },
        {
          key: 'Stage',
          value: context.stage,
        },
      ],
    });

    // Associate Elastic IP with EC2 Instance
    new ec2.CfnEIPAssociation(this, 'ElasticIPAssociation', {
      eip: this.elasticIp.ref,
      instanceId: this.instance.instanceId,
    });

    // Get CloudFormation instance for logical ID and creation policy
    const cfnInstance = this.instance.node.defaultChild as ec2.CfnInstance;

    // Add user data commands
    userData.addCommands(
      '#!/bin/bash -xe',
      'exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1',
      'echo "=== StreamrP2P UserData Script Started ==="',
      'yum update -y',
      'yum install -y docker git jq',
      'systemctl start docker',
      'systemctl enable docker',
      'usermod -a -G docker ec2-user',
      '',
      '# Install Docker Compose',
      'curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose',
      'chmod +x /usr/local/bin/docker-compose',
      '',
      '# Install AWS CLI v2',
      'curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"',
      'unzip awscliv2.zip',
      './aws/install',
      '',
      '# Create application directory',
      'mkdir -p /opt/streamr-coordinator',
      'chown ec2-user:ec2-user /opt/streamr-coordinator',
      '',
      '# Clone and deploy StreamrP2P application',
      'cd /opt/streamr-coordinator',
      'git clone https://github.com/iddv/streamr.git .',
      'cd coordinator',
      '',
      '# Fetch database credentials from AWS Secrets Manager',
      `SECRET_ARN="arn:aws:secretsmanager:${context.region}:${this.account}:secret:${context.resourceName('db-credentials')}"`,
      'echo "Fetching database credentials from Secrets Manager..."',
      'SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id "$SECRET_ARN" --query SecretString --output text)',
      '',
      '# Check if secret was fetched successfully',
      'if [ -z "$SECRET_JSON" ]; then',
      '    echo "ERROR: Failed to retrieve secret from Secrets Manager. Aborting." >&2',
      '    exit 1',
      'fi',
      '',
      '# Extract database credentials from secret JSON',
      'DB_USERNAME=$(echo "$SECRET_JSON" | jq -r .username)',
      'DB_PASSWORD=$(echo "$SECRET_JSON" | jq -r .password)',
      'DB_HOST=$(echo "$SECRET_JSON" | jq -r .host)',
      'DB_PORT=$(echo "$SECRET_JSON" | jq -r .port)',
      'DB_NAME=$(echo "$SECRET_JSON" | jq -r .dbname)',
      '',
      '# Get cache endpoint from CloudFormation',
      `CACHE_ENDPOINT=$(aws cloudformation describe-stacks --stack-name ${context.stackName('foundation')} --region ${context.region} --query 'Stacks[0].Outputs[?OutputKey==\`CacheEndpoint\`].OutputValue' --output text)`,
      '',
      '# Create production environment configuration with real AWS credentials',
      'cat > .env << ENVEOF',
      'DATABASE_URL=postgresql://$DB_USERNAME:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME',
      'REDIS_URL=redis://$CACHE_ENDPOINT:6379',
      'ENVIRONMENT=production', 
      'LOG_LEVEL=INFO',
      'WORKERS=2',
      'ENVEOF',
      '',
      '# Create SRS streaming server configuration',
      'cat > srs.conf << SRSEOF',
      '# SRS configuration for StreamrP2P',
      'listen              1935;',
      'max_connections     1000;',
      'srs_log_tank        file;',
      'srs_log_file        ./objs/srs.log;',
      '',
      'http_api {',
      '    enabled         on;',
      '    listen          8080;',
      '    crossdomain     on;',
      '}',
      '',
      'http_server {',
      '    enabled         on;',
      '    listen          8085;',
      '    dir             ./objs/nginx/html;',
      '}',
      '',
      'vhost __defaultVhost__ {',
      '    # FIX: Disable ATC to prevent timestamp drift',
      '    atc off;',
      '    ',
      '    # Enable HLS for web playback',
      '    hls {',
      '        enabled         on;',
      '        hls_path        ./objs/nginx/html;',
      '        hls_fragment    10;',
      '        hls_window      60;',
      '        ',
      '        # CRITICAL FIXES for A/V sync:',
      '        hls_wait_keyframe on;    # Wait for keyframes before segmenting',
      '        hls_gop_cache off;       # Disable GOP cache for accurate timing',
      '        hls_dts_directly on;     # Use precise DTS timestamps (SRS 5.0+ feature)',
      '    }',
      '    ',
      '    # Enable HTTP-FLV for low-latency',
      '    http_remux {',
      '        enabled     on;',
      '        mount       [vhost]/[app]/[stream].flv;',
      '    }',
      '    ',
      '    # Enable DVR for recording',
      '    dvr {',
      '        enabled      off;',
      '    }',
      '}',
      'SRSEOF',
      '',
      '# Create production docker-compose configuration',
      'cat > docker-compose.prod.yml << COMPOSEEOF',
      'version: "3.8"',
      'services:',
      '  coordinator:',
      '    build: .',
      '    ports:',
      '      - "8000:8000"',
      '    env_file:',
      '      - .env',
      '    restart: unless-stopped',
      '    depends_on:',
      '      - streamr-srs',
      '    networks:',
      '      - streamr-network',
      '',
      '  streamr-srs:',
      '    image: ossrs/srs:5',
      '    ports:',
      '      - "1935:1935"',
      '      - "1985:1985"',
      '      - "8080:8080"',
      '    volumes:',
      '      - "./srs.conf:/usr/local/srs/conf/srs.conf"',
      '    restart: unless-stopped',
      '    networks:',
      '      - streamr-network',
      '',
      'networks:',
      '  streamr-network:',
      '    driver: bridge',
      'COMPOSEEOF',
      '',
      '# Build and start services with production configuration',
      'echo "Building and starting StreamrP2P services..."',
      '/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d --build',
      '',
      '# Verify services are running',
      'echo "Waiting for services to start..."',
      'sleep 30',
      'if ! /usr/local/bin/docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then',
      '    echo "ERROR: Services failed to start properly" >&2',
      '    echo "=== Docker Compose Logs ===" >&2',
      '    /usr/local/bin/docker-compose -f docker-compose.prod.yml logs >&2',
      '    echo "=== Container Status ===" >&2',
      '    /usr/local/bin/docker-compose -f docker-compose.prod.yml ps >&2',
      '    /opt/aws/bin/cfn-signal -e 1 --stack ${this.stackName} --resource ${cfnInstance.logicalId} --region ${context.region}',
      '    exit 1',
      'fi',
      '',
      '# Test coordinator health',
      'echo "Testing coordinator health..."',
      'for i in {1..10}; do',
      '    if curl -f http://localhost:8000/health >/dev/null 2>&1; then',
      '        echo "✅ Coordinator health check passed"',
      '        break',
      '    fi',
      '    echo "Attempt $i: Coordinator not ready yet, waiting..."',
      '    sleep 10',
      'done',
      '',
      '# Install CloudWatch agent',
      'cd /',
      'wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm',
      'rpm -U ./amazon-cloudwatch-agent.rpm',
      '',
      `# Set environment variables`,
      `echo "export STAGE=${context.stage}" >> /home/ec2-user/.bashrc`,
      `echo "export REGION=${context.region}" >> /home/ec2-user/.bashrc`,
      `echo "export DB_SECRET_ARN=${context.resourceName('db-credentials')}" >> /home/ec2-user/.bashrc`,
      '',
      '# Signal completion to CloudFormation',
      'echo "🎉 StreamrP2P deployment completed successfully!"',
      `/opt/aws/bin/cfn-signal -e $? --stack ${this.stackName} --resource ${cfnInstance.logicalId} --region ${context.region}`
    );

    // Apply creation policy for CloudFormation signal
    cfnInstance.cfnOptions.creationPolicy = {
      resourceSignal: {
        timeout: 'PT30M', // Increased timeout to 30 minutes
        count: 1,
      },
    };

    // Application Load Balancer
    this.loadBalancer = new elbv2.ApplicationLoadBalancer(this, 'LoadBalancer', {
      loadBalancerName: context.resourceName('alb'),
      vpc,
      internetFacing: true,
      securityGroup: albSecurityGroup,
    });

    // Target Group for the coordinator API (port 8000)
    const coordinatorTargetGroup = new elbv2.ApplicationTargetGroup(this, 'CoordinatorTargetGroup', {
      targetGroupName: context.resourceName('coordinator-tg'),
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      vpc,
      targets: [new elbv2_targets.InstanceTarget(this.instance)],
      healthCheck: {
        enabled: true,
        path: '/health',
        protocol: elbv2.Protocol.HTTP,
        port: '8000',
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 3,
        timeout: cdk.Duration.seconds(5),
        interval: cdk.Duration.seconds(30),
      },
    });

    // HTTP Listener with path-based routing (single listener approach)
    const listener = this.loadBalancer.addListener('HTTPListener', {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
      defaultTargetGroups: [coordinatorTargetGroup],
    });

    // NOTE: For now, keep SRS traffic direct to instance via Elastic IP
    // Path-based ALB routing for SRS would require significant SRS config changes
    // This gives us stable endpoints without complex ALB routing conflicts

    // Outputs - UPDATED for stable endpoint architecture
    new cdk.CfnOutput(this, 'LoadBalancerDNS', {
      value: this.loadBalancer.loadBalancerDnsName,
      description: 'Application Load Balancer DNS Name (Stable)',
      exportName: context.stackName('alb-dns'),
    });

    new cdk.CfnOutput(this, 'WebDashboard', {
      value: `http://${this.loadBalancer.loadBalancerDnsName}/`,
      description: 'Web Dashboard URL (Stable ALB)',
      exportName: context.stackName('web-dashboard'),
    });

    new cdk.CfnOutput(this, 'SRSStreamingEndpoint', {
      value: `http://${this.elasticIp.ref}:8080/live/{stream}.m3u8`,
      description: 'SRS Streaming Endpoint (Stable Elastic IP)',
      exportName: context.stackName('srs-endpoint'),
    });

    new cdk.CfnOutput(this, 'RTMPEndpoint', {
      value: `rtmp://${this.elasticIp.ref}:1935/live`,
      description: 'RTMP Publishing Endpoint (Stable Elastic IP)',
      exportName: context.stackName('rtmp-endpoint'),
    });

    new cdk.CfnOutput(this, 'InstancePublicIP', {
      value: this.elasticIp.ref,
      description: 'EC2 Instance Stable Public IP (Elastic IP)',
      exportName: context.stackName('instance-public-ip'),
    });

    new cdk.CfnOutput(this, 'InstanceId', {
      value: this.instance.instanceId,
      description: 'EC2 Instance ID',
      exportName: context.stackName('instance-id'),
    });

    new cdk.CfnOutput(this, 'StableEndpointSummary', {
      value: `Dashboard: http://${this.loadBalancer.loadBalancerDnsName}/ | Streaming: http://${this.elasticIp.ref}:8080/live/{stream}.m3u8 | RTMP: rtmp://${this.elasticIp.ref}:1935/live`,
      description: '🎯 STABLE ENDPOINTS - Dashboard via ALB, Streaming via Elastic IP',
      exportName: context.stackName('stable-endpoints'),
    });
  }

  private getInstanceSize(size: string): ec2.InstanceSize {
    switch (size) {
      case 'micro': return ec2.InstanceSize.MICRO;
      case 'small': return ec2.InstanceSize.SMALL;
      case 'medium': return ec2.InstanceSize.MEDIUM;
      case 'large': return ec2.InstanceSize.LARGE;
      default: return ec2.InstanceSize.MICRO;
    }
  }
} 