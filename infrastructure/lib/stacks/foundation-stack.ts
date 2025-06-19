import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { DeploymentContext } from '../config/types';
import { streamrConfig } from '../config/streamr-config';

export interface FoundationStackProps extends cdk.StackProps {
  readonly context: DeploymentContext;
}

export class FoundationStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly database: rds.DatabaseInstance;
  public readonly cache: elasticache.CfnCacheCluster;
  public readonly dbSecurityGroup: ec2.SecurityGroup;
  public readonly cacheSecurityGroup: ec2.SecurityGroup;
  public readonly deploymentBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: FoundationStackProps) {
    super(scope, id, props);

    const { context } = props;
    const { stageConfig, regionConfig } = context;

    // Tags for all resources in this stack
    cdk.Tags.of(this).add('Project', streamrConfig.app.name);
    cdk.Tags.of(this).add('Stage', context.stage);
    cdk.Tags.of(this).add('Region', context.region);
    cdk.Tags.of(this).add('Owner', streamrConfig.app.owner);

    // VPC with public and private subnets
    this.vpc = new ec2.Vpc(this, 'VPC', {
      vpcName: context.resourceName('vpc'),
      ipAddresses: ec2.IpAddresses.cidr(streamrConfig.networking.vpcCidr),
      maxAzs: regionConfig.availabilityZones,
      natGateways: streamrConfig.networking.enableNatGateway ? 1 : 0,
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'Private',
          subnetType: streamrConfig.networking.enableNatGateway 
            ? ec2.SubnetType.PRIVATE_WITH_EGRESS 
            : ec2.SubnetType.PRIVATE_ISOLATED,
        },
      ],
      enableDnsHostnames: true,
      enableDnsSupport: true,
    });

    // Security Group for Database
    this.dbSecurityGroup = new ec2.SecurityGroup(this, 'DatabaseSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: context.resourceName('db-sg'),
      description: `Database security group for ${context.stage} stage`,
      allowAllOutbound: false,
    });

    // Allow database access from VPC (application instances)
    this.dbSecurityGroup.addIngressRule(
      ec2.Peer.ipv4(this.vpc.vpcCidrBlock),
      ec2.Port.tcp(streamrConfig.database.port),
      'Allow database access from VPC'
    );

    // Security Group for Cache
    this.cacheSecurityGroup = new ec2.SecurityGroup(this, 'CacheSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: context.resourceName('cache-sg'),
      description: `Cache security group for ${context.stage} stage`,
      allowAllOutbound: false,
    });

    // Allow cache access from VPC (application instances)
    this.cacheSecurityGroup.addIngressRule(
      ec2.Peer.ipv4(this.vpc.vpcCidrBlock),
      ec2.Port.tcp(streamrConfig.cache.port),
      'Allow cache access from VPC'
    );

    // RDS Subnet Group
    // Use public subnets when NAT Gateway is disabled (for cost optimization)
    // Use private subnets when NAT Gateway is enabled (for security)
    const dbSubnetGroup = new rds.SubnetGroup(this, 'DatabaseSubnetGroup', {
      subnetGroupName: context.resourceName('db-subnet-group'),
      description: `Database subnet group for ${context.stage} stage`,
      vpc: this.vpc,
      vpcSubnets: {
        subnetType: streamrConfig.networking.enableNatGateway 
          ? ec2.SubnetType.PRIVATE_WITH_EGRESS
          : ec2.SubnetType.PUBLIC,
      },
    });

    // RDS PostgreSQL Database
    this.database = new rds.DatabaseInstance(this, 'Database', {
      instanceIdentifier: context.resourceName('db'),
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_15_13,
      }),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T3,
        this.getInstanceSize(stageConfig.instanceSize)
      ),
      vpc: this.vpc,
      subnetGroup: dbSubnetGroup,
      securityGroups: [this.dbSecurityGroup],
      databaseName: 'streamr',
      credentials: rds.Credentials.fromGeneratedSecret('streamr', {
        secretName: context.resourceName('db-credentials'),
      }),
      allocatedStorage: stageConfig.isProd ? 100 : 20,
      storageEncrypted: true,
      multiAz: stageConfig.multiAz,
      backupRetention: stageConfig.enableBackups 
        ? cdk.Duration.days(stageConfig.isProd ? 30 : 7)
        : cdk.Duration.days(0),
      deletionProtection: stageConfig.enableDeletionProtection,
      removalPolicy: stageConfig.isProd 
        ? cdk.RemovalPolicy.RETAIN 
        : cdk.RemovalPolicy.DESTROY,
      monitoringInterval: stageConfig.monitoring.detailed 
        ? cdk.Duration.seconds(60) 
        : undefined,
    });

    // ElastiCache Subnet Group
    // Use public subnets when NAT Gateway is disabled (for cost optimization)
    // Use private subnets when NAT Gateway is enabled (for security)
    const cacheSubnets = streamrConfig.networking.enableNatGateway 
      ? this.vpc.privateSubnets 
      : this.vpc.publicSubnets;
    
    const cacheSubnetGroup = new elasticache.CfnSubnetGroup(this, 'CacheSubnetGroup', {
      cacheSubnetGroupName: context.resourceName('cache-subnet-group'),
      description: `Cache subnet group for ${context.stage} stage`,
      subnetIds: cacheSubnets.map(subnet => subnet.subnetId),
    });

    // ElastiCache Redis Cluster
    this.cache = new elasticache.CfnCacheCluster(this, 'Cache', {
      clusterName: context.resourceName('cache'),
      cacheNodeType: this.getCacheNodeType(stageConfig.instanceSize),
      engine: streamrConfig.cache.engine,
      numCacheNodes: 1,
      cacheSubnetGroupName: cacheSubnetGroup.cacheSubnetGroupName,
      vpcSecurityGroupIds: [this.cacheSecurityGroup.securityGroupId],
      port: streamrConfig.cache.port,
    });

    this.cache.addDependency(cacheSubnetGroup);

    // S3 Bucket for deployment artifacts
    this.deploymentBucket = new s3.Bucket(this, 'DeploymentBucket', {
      bucketName: context.resourceName('deployments'),
      versioned: true,
      lifecycleRules: [{
        id: 'CleanupOldDeployments',
        enabled: true,
        expiration: cdk.Duration.days(30), // Clean up old deployments after 30 days
      }],
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: stageConfig.isProd 
        ? cdk.RemovalPolicy.RETAIN 
        : cdk.RemovalPolicy.DESTROY,
    });

    // Outputs for use by other stacks
    new cdk.CfnOutput(this, 'VpcId', {
      value: this.vpc.vpcId,
      description: 'VPC ID',
      exportName: context.stackName('vpc-id'),
    });

    new cdk.CfnOutput(this, 'DatabaseEndpoint', {
      value: this.database.instanceEndpoint.hostname,
      description: 'RDS Database Endpoint',
      exportName: context.stackName('db-endpoint'),
    });

    new cdk.CfnOutput(this, 'DatabasePort', {
      value: this.database.instanceEndpoint.port.toString(),
      description: 'RDS Database Port',
      exportName: context.stackName('db-port'),
    });

    new cdk.CfnOutput(this, 'DatabaseSecretArn', {
      value: this.database.secret!.secretArn,
      description: 'RDS Database Secret ARN',
      exportName: context.stackName('db-secret-arn'),
    });

    new cdk.CfnOutput(this, 'CacheEndpoint', {
      value: this.cache.attrRedisEndpointAddress,
      description: 'ElastiCache Redis Endpoint',
      exportName: context.stackName('cache-endpoint'),
    });

    new cdk.CfnOutput(this, 'CachePort', {
      value: this.cache.attrRedisEndpointPort,
      description: 'ElastiCache Redis Port',
      exportName: context.stackName('cache-port'),
    });

    new cdk.CfnOutput(this, 'DeploymentBucketName', {
      value: this.deploymentBucket.bucketName,
      description: 'S3 Deployment Bucket Name',
      exportName: context.stackName('deployment-bucket'),
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

  private getCacheNodeType(size: string): string {
    switch (size) {
      case 'micro': return 'cache.t4g.micro';
      case 'small': return 'cache.t4g.small';
      case 'medium': return 'cache.t4g.medium';
      case 'large': return 'cache.t4g.large';
      default: return 'cache.t4g.micro';
    }
  }
} 