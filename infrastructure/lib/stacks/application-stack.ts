import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import { DeploymentContext } from '../config/types';
import { streamrConfig } from '../config/streamr-config';

export interface ApplicationStackProps extends cdk.StackProps {
  readonly context: DeploymentContext;
  readonly vpc: ec2.IVpc;
  readonly dbSecurityGroup: ec2.SecurityGroup;
  readonly cacheSecurityGroup: ec2.SecurityGroup;
  readonly deploymentBucket: s3.IBucket;
  readonly ecrRepository: ecr.IRepository;
  readonly ecsCluster: ecs.ICluster;
}

export class ApplicationStack extends cdk.Stack {
  public readonly service: ecs.FargateService;
  public readonly loadBalancer: elbv2.ApplicationLoadBalancer;
  public readonly serviceSecurityGroup: ec2.SecurityGroup;
  public readonly taskDefinition: ecs.FargateTaskDefinition;

  constructor(scope: Construct, id: string, props: ApplicationStackProps) {
    super(scope, id, props);

    const { context, vpc, dbSecurityGroup, cacheSecurityGroup, deploymentBucket, ecrRepository, ecsCluster } = props;
    const { stageConfig } = context;

    // Get image tag from CDK context (passed from CI/CD pipeline)
    const imageTag = this.node.tryGetContext('imageTag') || 'latest';

    // Tags for all resources in this stack
    cdk.Tags.of(this).add('Project', streamrConfig.app.name);
    cdk.Tags.of(this).add('Stage', context.stage);
    cdk.Tags.of(this).add('Region', context.region);
    cdk.Tags.of(this).add('Owner', streamrConfig.app.owner);

    // Security Group for ECS Service
    this.serviceSecurityGroup = new ec2.SecurityGroup(this, 'ServiceSecurityGroup', {
      vpc,
      securityGroupName: context.resourceName('service-sg'),
      description: `ECS service security group for ${context.stage} stage`,
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

    // Allow SRS HTTP/HLS traffic to ALB (port 8080)
    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(8080),
      'Allow SRS HTTP/HLS streaming traffic to ALB'
    );

    // Allow RTMP traffic directly to service (RTMP requires TCP, ALB is HTTP-only)
    this.serviceSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(1935),
      'Allow RTMP streaming traffic (direct access only)'
    );

    // Allow SRS HTTP/HLS traffic directly from public internet
    this.serviceSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(8080),
      'Allow SRS HTTP/HLS streaming traffic (public access for friends)'
    );

    // Allow HTTP traffic from ALB to service (coordinator API)
    this.serviceSecurityGroup.addIngressRule(
      albSecurityGroup,
      ec2.Port.tcp(8000),
      'Allow HTTP traffic from ALB to coordinator'
    );

    // Allow SRS HTTP/HLS traffic from ALB to service  
    this.serviceSecurityGroup.addIngressRule(
      albSecurityGroup,
      ec2.Port.tcp(8080),
      'Allow SRS HTTP/HLS traffic from ALB to service'  
    );

    // Add egress rules to service security group to connect to database and cache
    this.serviceSecurityGroup.addEgressRule(
      ec2.Peer.ipv4(vpc.vpcCidrBlock),
      ec2.Port.tcp(streamrConfig.database.port),
      'Allow database access from application'
    );

    this.serviceSecurityGroup.addEgressRule(
      ec2.Peer.ipv4(vpc.vpcCidrBlock),
      ec2.Port.tcp(streamrConfig.cache.port),
      'Allow cache access from application'
    );

    // IAM Task Execution Role
    const taskExecutionRole = new iam.Role(this, 'TaskExecutionRole', {
      roleName: context.resourceName('task-execution-role'),
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
      ],
    });

    // Allow task execution role to pull images from ECR
    ecrRepository.grantPull(taskExecutionRole);

    // IAM Task Role
    const taskRole = new iam.Role(this, 'TaskRole', {
      roleName: context.resourceName('task-role'),
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'),
      ],
    });

    // Allow task to read secrets
    taskRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
        'secretsmanager:DescribeSecret',
      ],
      resources: [`arn:aws:secretsmanager:${context.region}:*:secret:${context.resourceName('db-credentials')}*`],
    }));

    // Allow task to describe CloudFormation stacks (for cache endpoint)
    taskRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'cloudformation:DescribeStacks',
      ],
      resources: [
        `arn:aws:cloudformation:${context.region}:*:stack/${context.stackName('foundation')}/*`,
      ],
    }));

    // CloudWatch Log Group
    const logGroup = new logs.LogGroup(this, 'LogGroup', {
      logGroupName: context.resourceName('logs'),
      retention: stageConfig.isProd ? logs.RetentionDays.ONE_MONTH : logs.RetentionDays.ONE_WEEK,
      removalPolicy: stageConfig.isProd ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    // Fargate Task Definition
    this.taskDefinition = new ecs.FargateTaskDefinition(this, 'TaskDefinition', {
      family: context.resourceName('coordinator'),
      cpu: this.getCpu(stageConfig.instanceSize),
      memoryLimitMiB: this.getMemory(stageConfig.instanceSize),
      executionRole: taskExecutionRole,
      taskRole: taskRole,
    });

    // Coordinator Container
    const coordinatorContainer = this.taskDefinition.addContainer('coordinator', {
      image: ecs.ContainerImage.fromEcrRepository(ecrRepository, imageTag),
      containerName: 'coordinator',
      logging: ecs.LogDriver.awsLogs({
        streamPrefix: 'coordinator',
        logGroup: logGroup,
      }),
      environment: {
        'ENVIRONMENT': 'production',
        'LOG_LEVEL': 'INFO',
        'WORKERS': '2',
        'AWS_DEFAULT_REGION': context.region,
        'DB_SECRET_NAME': context.resourceName('db-credentials'),
        'FOUNDATION_STACK_NAME': context.stackName('foundation'),
      },
      healthCheck: {
        command: ['CMD-SHELL', 'curl -f http://localhost:8000/health || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
        startPeriod: cdk.Duration.seconds(60),
      },
    });

    // Add port mappings for coordinator
    coordinatorContainer.addPortMappings({
      containerPort: 8000,
      protocol: ecs.Protocol.TCP,
      name: 'coordinator-http',
    });

    // SRS Container
    const srsContainer = this.taskDefinition.addContainer('srs', {
      image: ecs.ContainerImage.fromRegistry('ossrs/srs:5'),
      containerName: 'srs',
      logging: ecs.LogDriver.awsLogs({
        streamPrefix: 'srs',
        logGroup: logGroup,
      }),
      essential: true,
    });

    // Add port mappings for SRS
    srsContainer.addPortMappings(
      {
        containerPort: 1935,
        protocol: ecs.Protocol.TCP,
        name: 'srs-rtmp',
      },
      {
        containerPort: 8080,
        protocol: ecs.Protocol.TCP,
        name: 'srs-http',
      },
      {
        containerPort: 1985,
        protocol: ecs.Protocol.TCP,
        name: 'srs-api',
      }
    );

    // FIXED: Define target AZ for consistent NLB and ECS placement (prevents AZ mismatch)
    // Use the first available AZ that CDK knows about for deterministic single-EIP setup
    const targetAz = vpc.availabilityZones[0]; // Dynamic AZ selection - matches CDK synthesis

    // Application Load Balancer
    this.loadBalancer = new elbv2.ApplicationLoadBalancer(this, 'LoadBalancer', {
      loadBalancerName: context.resourceName('alb'),
      vpc,
      internetFacing: true,
      securityGroup: albSecurityGroup,
    });

    // Fargate Service
    this.service = new ecs.FargateService(this, 'Service', {
      serviceName: context.resourceName('coordinator'),
      cluster: ecsCluster,
      taskDefinition: this.taskDefinition,
      desiredCount: 1,
      securityGroups: [this.serviceSecurityGroup],
      // FIXED: Pin ECS service to same AZ as NLB to prevent AZ mismatch during deployment
      vpcSubnets: vpc.selectSubnets({
        availabilityZones: [targetAz], // Use same AZ as NLB for target group health
        subnetType: ec2.SubnetType.PUBLIC,
      }),
      assignPublicIp: true, // Required for public subnets to pull images from ECR
      healthCheckGracePeriod: cdk.Duration.minutes(5),
    });

    // Target Group for the coordinator API
    const coordinatorTargetGroup = new elbv2.ApplicationTargetGroup(this, 'CoordinatorTargetGroup', {
      targetGroupName: context.resourceName('coordinator-tg'),
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      vpc,
      targetType: elbv2.TargetType.IP,
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

    // Target Group for SRS streaming
    const srsTargetGroup = new elbv2.ApplicationTargetGroup(this, 'SRSTargetGroup', {
      targetGroupName: context.resourceName('srs-tg'),
      port: 8080,
      protocol: elbv2.ApplicationProtocol.HTTP,
      vpc,
      targetType: elbv2.TargetType.IP,
      healthCheck: {
        enabled: true,
        path: '/api/v1/versions',
        protocol: elbv2.Protocol.HTTP,
        port: '8080',
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 3,
        timeout: cdk.Duration.seconds(5),
        interval: cdk.Duration.seconds(30),
      },
    });

    // Register service with target groups
    coordinatorTargetGroup.addTarget(this.service);
    srsTargetGroup.addTarget(this.service);

    // HTTP Listener for coordinator API (default)
    this.loadBalancer.addListener('HTTPListener', {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
      defaultTargetGroups: [coordinatorTargetGroup],
    });

    // HTTP Listener for SRS streaming
    this.loadBalancer.addListener('SRSListener', {
      port: 8080,
      protocol: elbv2.ApplicationProtocol.HTTP,
      defaultTargetGroups: [srsTargetGroup],
    });

    // Import existing Elastic IP for static RTMP endpoint
    const elasticIpAllocationId = 'eipalloc-054297e161bb78275'; // Your existing Elastic IP

    // Network Load Balancer for RTMP with static Elastic IP
    // NOTE: Single-AZ deployment for validation phase (only one Elastic IP available)
    // For production, allocate one EIP per AZ for high availability
    
    // FIXED: Use consistent target AZ for both NLB and ECS to prevent AZ mismatch
    const primaryPublicSubnet = vpc.publicSubnets.find(subnet => subnet.availabilityZone === targetAz);
    
    if (!primaryPublicSubnet) {
      throw new Error(`No public subnet found in target AZ: ${targetAz}`);
    }
    
    // V2: Force replacement to add Elastic IP (AWS doesn't allow adding EIP to existing NLB)
    // NOTE: When using Elastic IP, we must use SubnetMappings instead of vpcSubnets
    const rtmpLoadBalancer = new elbv2.NetworkLoadBalancer(this, 'RTMPLoadBalancerV2', {
      loadBalancerName: context.resourceName('rtmp-nlb-v2'),
      vpc,
      internetFacing: true,
      // Do NOT specify vpcSubnets when using SubnetMappings - AWS doesn't allow both
    });

    // Associate Elastic IP with the NLB using subnet mapping (replaces vpcSubnets)
    const cfnNlb = rtmpLoadBalancer.node.defaultChild as elbv2.CfnLoadBalancer;
    cfnNlb.addPropertyOverride('SubnetMappings', [
      {
        SubnetId: primaryPublicSubnet.subnetId,
        AllocationId: elasticIpAllocationId,
      },
    ]);
    
    // Remove the Subnets property since we're using SubnetMappings
    cfnNlb.addPropertyDeletionOverride('Subnets');

    // Target Group for RTMP V2 (new target group for new NLB - AWS best practice)
    const rtmpTargetGroup = new elbv2.NetworkTargetGroup(this, 'RTMPTargetGroupV2', {
      targetGroupName: context.resourceName('rtmp-tg-v2'),
      port: 1935,
      protocol: elbv2.Protocol.TCP,
      vpc,
      targetType: elbv2.TargetType.IP,
      healthCheck: {
        enabled: true,
        protocol: elbv2.Protocol.TCP,
        port: '1935',
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 2,
        timeout: cdk.Duration.seconds(6),
        interval: cdk.Duration.seconds(30),
      },
    });

    // Register service with RTMP target group
    rtmpTargetGroup.addTarget(this.service.loadBalancerTarget({
      containerName: 'srs',
      containerPort: 1935,
    }));

    // RTMP Listener
    rtmpLoadBalancer.addListener('RTMPListener', {
      port: 1935,
      protocol: elbv2.Protocol.TCP,
      defaultTargetGroups: [rtmpTargetGroup],
    });

    // Outputs
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
      value: `http://${this.loadBalancer.loadBalancerDnsName}:8080/live/{stream}.m3u8`,
      description: 'SRS Streaming Endpoint (via ALB)',
      exportName: context.stackName('srs-endpoint'),
    });

    new cdk.CfnOutput(this, 'RTMPEndpoint', {
      value: `rtmp://52.213.32.59:1935/live`,
      description: 'RTMP Publishing Endpoint (Static IP via Elastic IP)',
      exportName: context.stackName('rtmp-endpoint'),
    });

    new cdk.CfnOutput(this, 'RTMPStaticIP', {
      value: '52.213.32.59',
      description: 'Static IP for RTMP streaming (Elastic IP)',
      exportName: context.stackName('rtmp-static-ip'),
    });

    new cdk.CfnOutput(this, 'ServiceName', {
      value: this.service.serviceName,
      description: 'ECS Service Name',
      exportName: context.stackName('service-name'),
    });

    new cdk.CfnOutput(this, 'ClusterName', {
      value: ecsCluster.clusterName,
      description: 'ECS Cluster Name',
      exportName: context.stackName('cluster-name'),
    });

    new cdk.CfnOutput(this, 'TaskDefinitionArn', {
      value: this.taskDefinition.taskDefinitionArn,
      description: 'ECS Task Definition ARN',
      exportName: context.stackName('task-definition-arn'),
    });

    new cdk.CfnOutput(this, 'ECRRepositoryUri', {
      value: ecrRepository.repositoryUri,
      description: 'ECR Repository URI',
      // Note: ECR Repository URI is already exported by foundation stack
    });

    new cdk.CfnOutput(this, 'EndpointSummary', {
      value: `Dashboard: http://${this.loadBalancer.loadBalancerDnsName}/ | Streaming: http://${this.loadBalancer.loadBalancerDnsName}:8080/live/{stream}.m3u8 | RTMP: rtmp://52.213.32.59:1935/live`,
      description: '🎯 ECS ENDPOINTS - All services via Load Balancers (RTMP via Static IP)',
      exportName: context.stackName('ecs-endpoints'),
    });
  }

  private getCpu(size: string): number {
    switch (size) {
      case 'micro': return 256;  // 0.25 vCPU
      case 'small': return 512;  // 0.5 vCPU
      case 'medium': return 1024; // 1 vCPU
      case 'large': return 2048;  // 2 vCPU
      default: return 256;
    }
  }

  private getMemory(size: string): number {
    switch (size) {
      case 'micro': return 512;   // 512 MB
      case 'small': return 1024;  // 1 GB
      case 'medium': return 2048; // 2 GB
      case 'large': return 4096;  // 4 GB
      default: return 512;
    }
  }
} 