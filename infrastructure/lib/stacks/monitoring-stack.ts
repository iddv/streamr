import * as cdk from 'aws-cdk-lib';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';
import { Construct } from 'constructs';
import { DeploymentContext } from '../config/types';
import { streamrConfig } from '../config/streamr-config';

/** Threshold values for red-line annotations (investigate when exceeded) */
const THRESHOLDS = {
  cpuPercent: 80,
  memoryPercent: 80,
  albLatencySeconds: 2,
  alb5xxCount: 10,
  rdsCpuPercent: 80,
  rdsConnections: 80,
  elasticacheCpuPercent: 75,
  elasticacheConnections: 100,
} as const;

export interface MonitoringStackProps extends cdk.StackProps {
  readonly context: DeploymentContext;
  readonly vpc: ec2.IVpc;
  readonly ecsCluster: ecs.ICluster;
  readonly ecsService: ecs.FargateService;
  readonly alb: elbv2.ApplicationLoadBalancer;
  readonly nlb: elbv2.NetworkLoadBalancer;
  readonly headscaleInstance: ec2.Instance;
  readonly database: rds.IDatabaseInstance;
  readonly cache: elasticache.CfnCacheCluster;
}

/**
 * CloudWatch Monitoring Stack - Dashboard with default AWS metrics.
 * Uses only free default metrics (no custom metrics, no Container Insights required).
 * Red lines on graphs indicate thresholds to investigate.
 */
export class MonitoringStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: MonitoringStackProps) {
    super(scope, id, props);

    const { context, ecsService, alb, nlb, headscaleInstance, database, cache } = props;

    cdk.Tags.of(this).add('Project', streamrConfig.app.name);
    cdk.Tags.of(this).add('Stage', context.stage);
    cdk.Tags.of(this).add('Region', context.region);
    cdk.Tags.of(this).add('Owner', streamrConfig.app.owner);

    const period = cdk.Duration.minutes(1);

    const dashboard = new cloudwatch.Dashboard(this, 'ServiceDashboard', {
      dashboardName: context.resourceName('monitoring'),
      defaultInterval: cdk.Duration.hours(3),
      widgets: [],
    });

    // ─── ECS Fargate ─────────────────────────────────────────────────────────
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'ECS CPU %',
        left: [ecsService.metricCpuUtilization({ period })],
        leftAnnotations: [{ value: THRESHOLDS.cpuPercent, color: cloudwatch.Color.RED, label: `${THRESHOLDS.cpuPercent}%` }],
        width: 8,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'ECS Memory %',
        left: [ecsService.metricMemoryUtilization({ period })],
        leftAnnotations: [{ value: THRESHOLDS.memoryPercent, color: cloudwatch.Color.RED, label: `${THRESHOLDS.memoryPercent}%` }],
        width: 8,
        height: 6,
      })
    );

    // ─── EC2 Headscale ───────────────────────────────────────────────────────
    const ec2CpuMetric = new cloudwatch.Metric({
      namespace: 'AWS/EC2',
      metricName: 'CPUUtilization',
      dimensionsMap: { InstanceId: headscaleInstance.instanceId },
      period,
      statistic: 'Average',
    });
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Headscale EC2 CPU %',
        left: [ec2CpuMetric],
        leftAnnotations: [{ value: THRESHOLDS.cpuPercent, color: cloudwatch.Color.RED, label: `${THRESHOLDS.cpuPercent}%` }],
        width: 8,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Headscale EC2 Network In',
        left: [
          new cloudwatch.Metric({
            namespace: 'AWS/EC2',
            metricName: 'NetworkIn',
            dimensionsMap: { InstanceId: headscaleInstance.instanceId },
            period,
            statistic: 'Sum',
          }),
        ],
        width: 8,
        height: 6,
      })
    );

    // ─── ALB ─────────────────────────────────────────────────────────────────
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'ALB Request Count',
        left: [alb.metrics.requestCount({ period, statistic: 'Sum' })],
        width: 8,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'ALB Target Response Time (p99)',
        left: [alb.metrics.targetResponseTime({ period, statistic: 'p99' })],
        leftAnnotations: [{ value: THRESHOLDS.albLatencySeconds, color: cloudwatch.Color.RED, label: `${THRESHOLDS.albLatencySeconds}s` }],
        width: 8,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'ALB HTTP 5xx',
        left: [alb.metrics.httpCodeElb(elbv2.HttpCodeElb.ELB_5XX_COUNT, { period, statistic: 'Sum' })],
        leftAnnotations: [{ value: THRESHOLDS.alb5xxCount, color: cloudwatch.Color.RED, label: `${THRESHOLDS.alb5xxCount}` }],
        width: 8,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'ALB Active Connection Count',
        left: [alb.metrics.activeConnectionCount({ period })],
        width: 8,
        height: 6,
      })
    );

    // ─── NLB (RTMP) ──────────────────────────────────────────────────────────
    // LoadBalancer dimension format: net/name/id (extract from ARN)
    const nlbDimension = cdk.Fn.select(1, cdk.Fn.split('loadbalancer/', nlb.loadBalancerArn));
    const nlbMetrics = {
      activeFlowCount: new cloudwatch.Metric({
        namespace: 'AWS/NetworkELB',
        metricName: 'ActiveFlowCount',
        dimensionsMap: { LoadBalancer: nlbDimension },
        period,
        statistic: 'Average',
      }),
      processedBytes: new cloudwatch.Metric({
        namespace: 'AWS/NetworkELB',
        metricName: 'ProcessedBytes',
        dimensionsMap: { LoadBalancer: nlbDimension },
        period,
        statistic: 'Sum',
      }),
      newFlowCount: new cloudwatch.Metric({
        namespace: 'AWS/NetworkELB',
        metricName: 'NewFlowCount',
        dimensionsMap: { LoadBalancer: nlbDimension },
        period,
        statistic: 'Sum',
      }),
    };
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'NLB RTMP Active Flows',
        left: [nlbMetrics.activeFlowCount],
        width: 8,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'NLB RTMP Processed Bytes',
        left: [nlbMetrics.processedBytes],
        width: 8,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'NLB RTMP New Flows',
        left: [nlbMetrics.newFlowCount],
        width: 8,
        height: 6,
      })
    );

    // ─── RDS ─────────────────────────────────────────────────────────────────
    const dbInstanceId = database.instanceIdentifier;
    const rdsMetrics = {
      cpu: new cloudwatch.Metric({
        namespace: 'AWS/RDS',
        metricName: 'CPUUtilization',
        dimensionsMap: { DBInstanceIdentifier: dbInstanceId },
        period,
        statistic: 'Average',
      }),
      connections: new cloudwatch.Metric({
        namespace: 'AWS/RDS',
        metricName: 'DatabaseConnections',
        dimensionsMap: { DBInstanceIdentifier: dbInstanceId },
        period,
        statistic: 'Average',
      }),
      freeableMemory: new cloudwatch.Metric({
        namespace: 'AWS/RDS',
        metricName: 'FreeableMemory',
        dimensionsMap: { DBInstanceIdentifier: dbInstanceId },
        period,
        statistic: 'Average',
      }),
    };
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'RDS CPU %',
        left: [rdsMetrics.cpu],
        leftAnnotations: [{ value: THRESHOLDS.rdsCpuPercent, color: cloudwatch.Color.RED, label: `${THRESHOLDS.rdsCpuPercent}%` }],
        width: 8,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'RDS Database Connections',
        left: [rdsMetrics.connections],
        leftAnnotations: [{ value: THRESHOLDS.rdsConnections, color: cloudwatch.Color.RED, label: `${THRESHOLDS.rdsConnections}` }],
        width: 8,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'RDS Freeable Memory (bytes)',
        left: [rdsMetrics.freeableMemory],
        width: 8,
        height: 6,
      })
    );

    // ─── ElastiCache Redis ────────────────────────────────────────────────────
    const cacheClusterId = cache.ref; // CfnCacheCluster ref returns the cluster ID
    const elasticacheMetrics = {
      cpu: new cloudwatch.Metric({
        namespace: 'AWS/ElastiCache',
        metricName: 'CPUUtilization',
        dimensionsMap: { CacheClusterId: cacheClusterId },
        period,
        statistic: 'Average',
      }),
      connections: new cloudwatch.Metric({
        namespace: 'AWS/ElastiCache',
        metricName: 'CurrConnections',
        dimensionsMap: { CacheClusterId: cacheClusterId },
        period,
        statistic: 'Average',
      }),
      hitRate: new cloudwatch.Metric({
        namespace: 'AWS/ElastiCache',
        metricName: 'CacheHitRate',
        dimensionsMap: { CacheClusterId: cacheClusterId },
        period,
        statistic: 'Average',
      }),
    };
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'ElastiCache CPU %',
        left: [elasticacheMetrics.cpu],
        leftAnnotations: [{ value: THRESHOLDS.elasticacheCpuPercent, color: cloudwatch.Color.RED, label: `${THRESHOLDS.elasticacheCpuPercent}%` }],
        width: 8,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'ElastiCache Current Connections',
        left: [elasticacheMetrics.connections],
        leftAnnotations: [{ value: THRESHOLDS.elasticacheConnections, color: cloudwatch.Color.RED, label: `${THRESHOLDS.elasticacheConnections}` }],
        width: 8,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'ElastiCache Cache Hit Rate %',
        left: [elasticacheMetrics.hitRate],
        width: 8,
        height: 6,
      })
    );

    new cdk.CfnOutput(this, 'DashboardUrl', {
      value: `https://${context.region}.console.aws.amazon.com/cloudwatch/home?region=${context.region}#dashboards:name=${context.resourceName('monitoring')}`,
      description: 'CloudWatch Dashboard URL',
      exportName: context.stackName('dashboard-url'),
    });
  }
}
