import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';
import { DeploymentContext } from '../config/types';
import { streamrConfig } from '../config/streamr-config';

export interface ApplicationStackProps extends cdk.StackProps {
  readonly context: DeploymentContext;
  readonly vpc: ec2.IVpc;
  readonly database: rds.IDatabaseInstance;
  readonly dbSecurityGroup: ec2.SecurityGroup;
  readonly cacheSecurityGroup: ec2.SecurityGroup;
  readonly deploymentBucket: s3.IBucket;
  readonly ecrRepository: ecr.IRepository;
  readonly ecsCluster: ecs.ICluster;
}

export class ApplicationStack extends cdk.Stack {
  public readonly service: ecs.FargateService;
  public readonly loadBalancer: elbv2.ApplicationLoadBalancer;
  public readonly rtmpLoadBalancer: elbv2.NetworkLoadBalancer;
  public readonly serviceSecurityGroup: ec2.SecurityGroup;
  public readonly taskDefinition: ecs.FargateTaskDefinition;
  public readonly headscaleInstance: ec2.Instance;

  constructor(scope: Construct, id: string, props: ApplicationStackProps) {
    super(scope, id, props);

    const { context, vpc, database, dbSecurityGroup, cacheSecurityGroup, deploymentBucket, ecrRepository, ecsCluster } = props;
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

    // SRS Container — custom config written at startup (Fargate has no volume mounts)
    // Config: 2s HLS fragments, on_publish auth callback to coordinator (localhost in same task)
    const srsConfig = [
      'listen              1935;',
      'max_connections     1000;',
      'daemon              off;',
      'srs_log_tank        console;',
      'srs_log_level       info;',
      'http_api { enabled on; listen 1985; }',
      'http_server { enabled on; listen 8080; dir ./objs/nginx/html; }',
      'stats { network 0; }',
      'vhost __defaultVhost__ {',
      '  hls {',
      '    enabled         on;',
      '    hls_fragment    2;',
      '    hls_window      10;',
      '    hls_path        ./objs/nginx/html;',
      '    hls_m3u8_file   [app]/[stream].m3u8;',
      '    hls_ts_file     [app]/[stream]-[seq].ts;',
      '    hls_cleanup     on;',
      '    hls_dispose     30;',
      '  }',
      '  http_remux { enabled on; mount [vhost]/[app]/[stream].flv; }',
      '  http_hooks {',
      '    enabled         on;',
      '    on_publish      http://localhost:8000/api/v1/srs/on-publish;',
      '    on_unpublish    http://localhost:8000/api/v1/srs/on-unpublish;',
      '  }',
      '  tcp_nodelay     on;',
      '  min_latency     on;',
      '  play { gop_cache off; queue_length 10; mw_latency 100; }',
      '  publish { mr off; }',
      '}',
    ].join('\n');

    const srsContainer = this.taskDefinition.addContainer('srs', {
      image: ecs.ContainerImage.fromRegistry('ossrs/srs:5'),
      containerName: 'srs',
      command: [
        'bash', '-c',
        `echo '${srsConfig}' > /usr/local/srs/conf/custom.conf && ./objs/srs -c conf/custom.conf`,
      ],
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

    // -----------------------------------------------------------------------
    // Headscale VPN Coordination Server on EC2 (Phase 9)
    // Dedicated EC2 instance — Headscale is stateful, ECS rolling deploys
    // would kill active VPN connections. EC2 is persistent and always-on.
    // -----------------------------------------------------------------------

    // Security Group for Headscale EC2
    const headscaleSecurityGroup = new ec2.SecurityGroup(this, 'HeadscaleSecurityGroup', {
      vpc,
      securityGroupName: context.resourceName('headscale-sg'),
      description: 'Headscale VPN coordination server',
      allowAllOutbound: true,
    });

    // HTTPS coordination + DERP relay — Tailscale clients require HTTPS for DERP
    headscaleSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      'Allow Headscale HTTPS coordination + DERP relay'
    );

    // STUN — UDP for NAT traversal
    headscaleSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.udp(3478),
      'Allow DERP STUN relay for NAT traversal'
    );

    // Headscale EC2 can reach RDS because the DB security group already allows
    // ingress from the entire VPC CIDR (configured in foundation stack).
    // No additional cross-stack security group rule needed.

    // IAM Role for Headscale EC2 — SSM access + read DB secret
    const headscaleRole = new iam.Role(this, 'HeadscaleRole', {
      roleName: context.resourceName('headscale-role'),
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
      ],
    });

    // Allow Headscale EC2 to read DB credentials from Secrets Manager
    headscaleRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['secretsmanager:GetSecretValue'],
      resources: [`arn:aws:secretsmanager:${context.region}:*:secret:${context.resourceName('db-credentials')}*`],
    }));

    // Allow Headscale EC2 to read/write its own API key, TLS cert, and sidecar key secrets
    headscaleRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
        'secretsmanager:PutSecretValue',
        'secretsmanager:CreateSecret',
        'secretsmanager:DescribeSecret',
      ],
      resources: [
        `arn:aws:secretsmanager:${context.region}:*:secret:${context.resourceName('headscale-api-key')}*`,
        `arn:aws:secretsmanager:${context.region}:*:secret:${context.resourceName('headscale-tls-cert')}*`,
        `arn:aws:secretsmanager:${context.region}:*:secret:${context.resourceName('tailscale-sidecar-key')}*`,
      ],
    }));

    // User data script — installs Headscale, configures it, starts the service
    const headscaleUserData = ec2.UserData.forLinux();
    headscaleUserData.addCommands(
      '#!/bin/bash',
      'set -euo pipefail',
      'exec > >(tee /var/log/headscale-setup.log) 2>&1',
      '',
      '# Install dependencies',
      'yum update -y',
      'yum install -y jq postgresql15',
      '',
      '# Install Headscale',
      'HEADSCALE_VERSION="0.23.0"',
      'curl -Lo /usr/local/bin/headscale https://github.com/juanfont/headscale/releases/download/v${HEADSCALE_VERSION}/headscale_${HEADSCALE_VERSION}_linux_amd64',
      'chmod +x /usr/local/bin/headscale',
      '',
      '# Create headscale user and directories',
      'useradd --system --no-create-home --shell /usr/sbin/nologin headscale || true',
      'mkdir -p /etc/headscale /var/lib/headscale /var/run/headscale',
      'chown headscale:headscale /var/lib/headscale /var/run/headscale',
      '',
      '# Fetch DB credentials from Secrets Manager',
      `DB_SECRET=$(aws secretsmanager get-secret-value --secret-id ${context.resourceName('db-credentials')} --region ${context.region} --query SecretString --output text)`,
      'DB_HOST=$(echo "$DB_SECRET" | jq -r .host)',
      'DB_PORT=$(echo "$DB_SECRET" | jq -r .port)',
      'DB_USER=$(echo "$DB_SECRET" | jq -r .username)',
      'DB_PASS=$(echo "$DB_SECRET" | jq -r .password)',
      'DB_NAME=$(echo "$DB_SECRET" | jq -r .dbname)',
      '',
      '# Create a separate database for Headscale to avoid table name collisions',
      '# (Headscale has its own "nodes" table that conflicts with StreamrP2P "nodes")',
      'PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "CREATE DATABASE headscale;" 2>/dev/null || echo "headscale database already exists"',
      '',
      '# Get EC2 instance public IP for server_url',
      'TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")',
      'PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4)',
      '',
      '# Generate self-signed TLS certificate for Headscale + embedded DERP',
      '# Tailscale DERP clients require HTTPS — plain HTTP causes "tls: first record does not look like a TLS handshake"',
      'openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \\',
      '  -keyout /etc/headscale/tls.key -out /etc/headscale/tls.crt \\',
      '  -days 3650 -nodes -subj "/CN=streamr-headscale" \\',
      '  -addext "subjectAltName=IP:${PUBLIC_IP}"',
      'chown headscale:headscale /etc/headscale/tls.key /etc/headscale/tls.crt',
      'chmod 600 /etc/headscale/tls.key',
      '',
      '# Write Headscale config',
      'cat > /etc/headscale/config.yaml << HSEOF',
      'server_url: https://${PUBLIC_IP}:443',
      'listen_addr: 0.0.0.0:443',
      'grpc_listen_addr: 0.0.0.0:50443',
      '',
      'tls_cert_path: /etc/headscale/tls.crt',
      'tls_key_path: /etc/headscale/tls.key',
      '',
      'noise:',
      '  private_key_path: /var/lib/headscale/noise_private.key',
      '',
      'prefixes:',
      '  v4: 100.64.0.0/10',
      '  v6: fd7a:115c:a1e0::/48',
      '',
      'database:',
      '  type: postgres',
      '  postgres:',
      '    host: ${DB_HOST}',
      '    port: ${DB_PORT}',
      '    name: headscale',
      '    user: ${DB_USER}',
      '    pass: ${DB_PASS}',
      '    ssl: true',
      '',
      'derp:',
      '  server:',
      '    enabled: true',
      '    region_id: 999',
      '    region_code: streamr',
      '    region_name: StreamrP2P',
      '    stun_listen_addr: 0.0.0.0:3478',
      '    private_key_path: /var/lib/headscale/derp_server_private.key',
      '    automatically_add_embedded_derp_region: true',
      '    ipv4: ${PUBLIC_IP}',
      '  urls: []',
      '  paths: []',
      '',
      'disable_check_updates: true',
      '',
      'dns:',
      '  magic_dns: false',
      '  base_domain: streamr.mesh',
      '',
      'unix_socket: /var/run/headscale/headscale.sock',
      'unix_socket_permission: "0770"',
      '',
      'log:',
      '  format: text',
      '  level: info',
      '',
      'logtail:',
      '  enabled: false',
      'HSEOF',
      '',
      '# Write systemd service',
      'cat > /etc/systemd/system/headscale.service << SVCEOF',
      '[Unit]',
      'Description=Headscale VPN coordination server',
      'After=network.target',
      '',
      '[Service]',
      'Type=simple',
      'User=headscale',
      'RuntimeDirectory=headscale',
      'AmbientCapabilities=CAP_NET_BIND_SERVICE',
      'ExecStart=/usr/local/bin/headscale serve --config /etc/headscale/config.yaml',
      'Restart=always',
      'RestartSec=5',
      '',
      '[Install]',
      'WantedBy=multi-user.target',
      'SVCEOF',
      '',
      '# Start Headscale',
      'systemctl daemon-reload',
      'systemctl enable headscale',
      'systemctl start headscale',
      '',
      '# Wait for Headscale to be ready (DB migration + startup takes time)',
      'for i in $(seq 1 30); do',
      '  if /usr/local/bin/headscale users list >/dev/null 2>&1; then',
      '    echo "Headscale is ready after ${i}s"',
      '    break',
      '  fi',
      '  echo "Waiting for Headscale to start... (${i}/30)"',
      '  sleep 2',
      'done',
      '',
      '# Create default user',
      '/usr/local/bin/headscale users create default || true',
      '',
      '# Generate API key and store in Secrets Manager',
      'API_KEY=$(/usr/local/bin/headscale apikeys create --expiration 365d 2>&1 | tail -1)',
      `aws secretsmanager create-secret --name ${context.resourceName('headscale-api-key')} --secret-string "$API_KEY" --region ${context.region} 2>/dev/null || \\`,
      `aws secretsmanager put-secret-value --secret-id ${context.resourceName('headscale-api-key')} --secret-string "$API_KEY" --region ${context.region}`,
      '',
      '# Store self-signed TLS cert in Secrets Manager so Tailscale sidecar can trust it',
      'TLS_CERT=$(cat /etc/headscale/tls.crt)',
      `aws secretsmanager create-secret --name ${context.resourceName('headscale-tls-cert')} --secret-string "$TLS_CERT" --region ${context.region} 2>/dev/null || \\`,
      `aws secretsmanager put-secret-value --secret-id ${context.resourceName('headscale-tls-cert')} --secret-string "$TLS_CERT" --region ${context.region}`,
      '',
      '# Create a reusable pre-auth key for the ECS Tailscale sidecar and store it',
      'SIDECAR_KEY=$(/usr/local/bin/headscale preauthkeys create --user default --reusable --expiration 8760h 2>&1 | tail -1)',
      `aws secretsmanager create-secret --name ${context.resourceName('tailscale-sidecar-key')} --secret-string "$SIDECAR_KEY" --region ${context.region} 2>/dev/null || \\`,
      `aws secretsmanager put-secret-value --secret-id ${context.resourceName('tailscale-sidecar-key')} --secret-string "$SIDECAR_KEY" --region ${context.region}`,
      '',
      'echo "Headscale setup complete. API key, TLS cert, and sidecar key stored in Secrets Manager."',
      'echo "Public IP: ${PUBLIC_IP}"',
    );

    // Headscale EC2 Instance
    this.headscaleInstance = new ec2.Instance(this, 'HeadscaleInstanceV4', {
      instanceName: context.resourceName('headscale'),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
      machineImage: ec2.MachineImage.latestAmazonLinux2023(),
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
      securityGroup: headscaleSecurityGroup,
      role: headscaleRole,
      userData: headscaleUserData,
      associatePublicIpAddress: true,
      blockDevices: [{
        deviceName: '/dev/xvda',
        volume: ec2.BlockDeviceVolume.ebs(8, { encrypted: true }),
      }],
    });

    // Tag for easy identification
    cdk.Tags.of(this.headscaleInstance).add('Service', 'headscale');
    cdk.Tags.of(this.headscaleInstance).add('DeployVersion', '4');

    // Tailscale sidecar — coordinator joins the VPN mesh via EC2 Headscale
    // Needs TS_AUTHKEY to authenticate with Headscale so the proxy can reach VPN IPs (100.64.x.x)
    const tailscaleSidecarKeySecret = secretsmanager.Secret.fromSecretNameV2(
      this, 'TailscaleSidecarKeySecret', context.resourceName('tailscale-sidecar-key')
    );
    // Self-signed TLS cert from Headscale EC2 — sidecar needs to trust it
    const headscaleTlsCertSecret = secretsmanager.Secret.fromSecretNameV2(
      this, 'HeadscaleTlsCertSecret', context.resourceName('headscale-tls-cert')
    );
    const tailscaleContainer = this.taskDefinition.addContainer('tailscaled', {
      image: ecs.ContainerImage.fromRegistry('tailscale/tailscale:latest'),
      containerName: 'tailscaled',
      // Override entrypoint to install the self-signed Headscale TLS cert
      // before starting containerboot. The Tailscale image is Alpine-based.
      entryPoint: ['sh', '-c'],
      command: [
        'if [ -n "$HEADSCALE_TLS_CERT" ]; then ' +
        'echo "$HEADSCALE_TLS_CERT" > /usr/local/share/ca-certificates/headscale.crt && ' +
        'update-ca-certificates 2>/dev/null; ' +
        'fi; ' +
        'exec /usr/local/bin/containerboot'
      ],
      logging: ecs.LogDriver.awsLogs({
        streamPrefix: 'tailscaled',
        logGroup: logGroup,
      }),
      essential: false,
      environment: {
        'TS_STATE_DIR': '/var/lib/tailscale',
        // Points at EC2 Headscale instance (private IP within VPC) — HTTPS on 443 with self-signed cert
        'TS_EXTRA_ARGS': `--login-server=https://${this.headscaleInstance.instancePrivateIp}:443`,
        // Expose HTTP proxy so coordinator container can route to VPN IPs
        // (Fargate userspace mode has no TUN device — must proxy through sidecar)
        'TS_OUTBOUND_HTTP_PROXY_LISTEN': '0.0.0.0:1055',
      },
      secrets: {
        'TS_AUTHKEY': ecs.Secret.fromSecretsManager(tailscaleSidecarKeySecret),
        'HEADSCALE_TLS_CERT': ecs.Secret.fromSecretsManager(headscaleTlsCertSecret),
      },
    });

    // Add Headscale env vars to coordinator container
    coordinatorContainer.addEnvironment('HEADSCALE_URL', `https://${this.headscaleInstance.instancePrivateIp}:443`);
    // Public URL for external nodes (Go clients outside VPC) to connect to Headscale
    coordinatorContainer.addEnvironment('HEADSCALE_PUBLIC_URL', `https://${this.headscaleInstance.instancePublicIp}:443`);
    // Tailscale sidecar HTTP proxy — coordinator routes VPN traffic through this
    coordinatorContainer.addEnvironment('TS_OUTBOUND_HTTP_PROXY_URL', 'http://localhost:1055');
    // Inject API key directly from Secrets Manager via ECS native secrets (no boto3 needed)
    const headscaleApiKeySecret = secretsmanager.Secret.fromSecretNameV2(
      this, 'HeadscaleApiKeySecret', context.resourceName('headscale-api-key')
    );
    coordinatorContainer.addSecret('HEADSCALE_API_KEY', ecs.Secret.fromSecretsManager(headscaleApiKeySecret));

    // Also pass the TLS cert to coordinator so it can serve it to Go nodes via /api/v1/auth/headscale-cert
    coordinatorContainer.addSecret('HEADSCALE_TLS_CERT', ecs.Secret.fromSecretsManager(headscaleTlsCertSecret));

    // Allow coordinator task role to read the Headscale API key, sidecar auth key, and TLS cert secrets
    taskRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['secretsmanager:GetSecretValue'],
      resources: [
        `arn:aws:secretsmanager:${context.region}:*:secret:${context.resourceName('headscale-api-key')}*`,
        `arn:aws:secretsmanager:${context.region}:*:secret:${context.resourceName('tailscale-sidecar-key')}*`,
        `arn:aws:secretsmanager:${context.region}:*:secret:${context.resourceName('headscale-tls-cert')}*`,
      ],
    }));

    // Headscale coordination traffic from ECS to EC2 (within VPC)
    headscaleSecurityGroup.addIngressRule(
      this.serviceSecurityGroup,
      ec2.Port.tcp(443),
      'Allow ECS coordinator to reach Headscale'
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
    coordinatorTargetGroup.addTarget(this.service.loadBalancerTarget({
      containerName: 'coordinator',
      containerPort: 8000,
    }));
    srsTargetGroup.addTarget(this.service.loadBalancerTarget({
      containerName: 'srs', 
      containerPort: 8080,
    }));

    // ---------------------------------------------------------------------------
    // HTTPS/TLS — ACM certificate + HTTPS listener + HTTP→HTTPS redirect
    // ---------------------------------------------------------------------------
    const domainName = this.node.tryGetContext('domainName') || process.env.DOMAIN_NAME;

    if (domainName) {
      // DNS-validated ACM certificate for the domain
      const certificate = new acm.Certificate(this, 'Certificate', {
        domainName: domainName,
        subjectAlternativeNames: [`*.${domainName}`],
        validation: acm.CertificateValidation.fromDns(),
      });

      // HTTPS Listener (port 443) — primary listener with TLS termination
      this.loadBalancer.addListener('HTTPSListener', {
        port: 443,
        protocol: elbv2.ApplicationProtocol.HTTPS,
        certificates: [certificate],
        defaultTargetGroups: [coordinatorTargetGroup],
      });

      // HTTP Listener (port 80) — redirect to HTTPS
      this.loadBalancer.addListener('HTTPListener', {
        port: 80,
        protocol: elbv2.ApplicationProtocol.HTTP,
        defaultAction: elbv2.ListenerAction.redirect({
          protocol: 'HTTPS',
          port: '443',
          permanent: true,
        }),
      });

      new cdk.CfnOutput(this, 'CertificateArn', {
        value: certificate.certificateArn,
        description: 'ACM Certificate ARN for HTTPS',
      });
    } else {
      // Fallback: plain HTTP listener when no domain is configured
      this.loadBalancer.addListener('HTTPListener', {
        port: 80,
        protocol: elbv2.ApplicationProtocol.HTTP,
        defaultTargetGroups: [coordinatorTargetGroup],
      });
    }

    // HTTP Listener for SRS streaming
    this.loadBalancer.addListener('SRSListener', {
      port: 8080,
      protocol: elbv2.ApplicationProtocol.HTTP,
      defaultTargetGroups: [srsTargetGroup],
    });

    // Import existing Elastic IP for static RTMP endpoint
    // Parameterized: override via CDK context -c elasticIpAllocationId=eipalloc-xxx
    const elasticIpAllocationId = this.node.tryGetContext('elasticIpAllocationId') || 'eipalloc-054297e161bb78275';
    const elasticIpAddress = this.node.tryGetContext('elasticIpAddress') || '52.213.32.59';

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
    this.rtmpLoadBalancer = new elbv2.NetworkLoadBalancer(this, 'RTMPLoadBalancerV2', {
      loadBalancerName: context.resourceName('rtmp-nlb-v2'),
      vpc,
      internetFacing: true,
      // Do NOT specify vpcSubnets when using SubnetMappings - AWS doesn't allow both
    });

    // Associate Elastic IP with the NLB using subnet mapping (replaces vpcSubnets)
    const cfnNlb = this.rtmpLoadBalancer.node.defaultChild as elbv2.CfnLoadBalancer;
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
    this.rtmpLoadBalancer.addListener('RTMPListener', {
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
      value: `rtmp://${elasticIpAddress}:1935/live`,
      description: 'RTMP Publishing Endpoint (Static IP via Elastic IP)',
      exportName: context.stackName('rtmp-endpoint'),
    });

    // -----------------------------------------------------------------------
    // CloudWatch Alarms (Task 7.3 — Req 20.2, Design §23)
    // -----------------------------------------------------------------------

    new cloudwatch.Alarm(this, 'CpuAlarm', {
      metric: this.service.metricCpuUtilization({ period: cdk.Duration.minutes(5) }),
      threshold: 80,
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      alarmDescription: 'ECS CPU utilization > 80% for 10 min',
      alarmName: context.stackName('cpu-high'),
    });

    new cloudwatch.Alarm(this, 'MemoryAlarm', {
      metric: this.service.metricMemoryUtilization({ period: cdk.Duration.minutes(5) }),
      threshold: 80,
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      alarmDescription: 'ECS memory utilization > 80% for 10 min',
      alarmName: context.stackName('memory-high'),
    });

    new cloudwatch.Alarm(this, 'Http5xxAlarm', {
      metric: this.loadBalancer.metrics.httpCodeElb(elbv2.HttpCodeElb.ELB_5XX_COUNT, {
        period: cdk.Duration.minutes(5),
        statistic: 'Sum',
      }),
      threshold: 10,
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      alarmDescription: 'ALB 5xx errors > 10 in 5 min',
      alarmName: context.stackName('http-5xx-high'),
    });

    new cloudwatch.Alarm(this, 'LatencyAlarm', {
      metric: this.loadBalancer.metrics.targetResponseTime({
        period: cdk.Duration.minutes(5),
        statistic: 'p99',
      }),
      threshold: 2,
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      alarmDescription: 'ALB p99 latency > 2s for 10 min',
      alarmName: context.stackName('latency-p99-high'),
    });

    // -----------------------------------------------------------------------
    // Outputs
    // -----------------------------------------------------------------------

    new cdk.CfnOutput(this, 'RTMPStaticIP', {
      value: elasticIpAddress,
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
      value: `Dashboard: http://${this.loadBalancer.loadBalancerDnsName}/ | Streaming: http://${this.loadBalancer.loadBalancerDnsName}:8080/live/{stream}.m3u8 | RTMP: rtmp://${elasticIpAddress}:1935/live`,
      description: '🎯 ECS ENDPOINTS - All services via Load Balancers (RTMP via Static IP)',
      exportName: context.stackName('ecs-endpoints'),
    });

    // Headscale EC2 outputs
    new cdk.CfnOutput(this, 'HeadscaleInstanceIdV2', {
      value: this.headscaleInstance.instanceId,
      description: 'Headscale EC2 Instance ID (use SSM to connect)',
      exportName: context.stackName('headscale-instance-id'),
    });

    new cdk.CfnOutput(this, 'HeadscalePrivateIPV2', {
      value: this.headscaleInstance.instancePrivateIp,
      description: 'Headscale EC2 Private IP (VPC-internal coordination)',
      exportName: context.stackName('headscale-private-ip'),
    });

    new cdk.CfnOutput(this, 'HeadscalePublicURLV2', {
      value: `http://<HEADSCALE_PUBLIC_IP>:8080`,
      description: 'Headscale public URL for friend nodes (check EC2 console for public IP)',
      exportName: context.stackName('headscale-public-url'),
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