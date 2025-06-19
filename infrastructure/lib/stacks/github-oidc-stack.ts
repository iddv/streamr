import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface GitHubOidcStackProps extends cdk.StackProps {
  readonly githubOrg: string;
  readonly githubRepo: string;
  readonly githubBranch?: string;
}

export class GitHubOidcStack extends cdk.Stack {
  public readonly githubActionsRole: iam.Role;

  constructor(scope: Construct, id: string, props: GitHubOidcStackProps) {
    super(scope, id, props);

    const { githubOrg, githubRepo, githubBranch = 'main' } = props;

    // Create GitHub OIDC Identity Provider
    const githubOidcProvider = new iam.OpenIdConnectProvider(this, 'GitHubOidcProvider', {
      url: 'https://token.actions.githubusercontent.com',
      clientIds: ['sts.amazonaws.com'],
      thumbprints: ['6938fd4d98bab03faadb97b34396831e3780aea1'], // GitHub's current thumbprint
    });

    // Create IAM Role for GitHub Actions
    this.githubActionsRole = new iam.Role(this, 'GitHubActionsRole', {
      roleName: 'streamr-github-actions-role',
      assumedBy: new iam.WebIdentityPrincipal(
        githubOidcProvider.openIdConnectProviderArn,
        {
          StringEquals: {
            'token.actions.githubusercontent.com:aud': 'sts.amazonaws.com',
          },
          StringLike: {
            // Amazon Q Priority 2: Restrict to main branch, PRs, and beta environment
            'token.actions.githubusercontent.com:sub': [
              'repo:iddv/streamr:ref:refs/heads/main',
              'repo:iddv/streamr:pull_request',
              'repo:iddv/streamr:environment:beta'
            ]
          },
        }
      ),
      description: 'Role for GitHub Actions to deploy StreamrP2P infrastructure',
      maxSessionDuration: cdk.Duration.hours(1), // Limit session duration for security
    });

    // Add comprehensive deployment permissions
    this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
      sid: 'CloudFormationPermissions',
      effect: iam.Effect.ALLOW,
      actions: [
        'cloudformation:CreateStack',
        'cloudformation:UpdateStack',
        'cloudformation:DeleteStack',
        'cloudformation:DescribeStacks',
        'cloudformation:DescribeStackEvents',
        'cloudformation:DescribeStackResources',
        'cloudformation:GetTemplate',
        'cloudformation:ValidateTemplate',
        'cloudformation:CreateChangeSet',
        'cloudformation:DescribeChangeSet',
        'cloudformation:ExecuteChangeSet',
        'cloudformation:DeleteChangeSet',
        'cloudformation:GetStackPolicy',
        'cloudformation:SetStackPolicy',
      ],
      resources: [
        `arn:aws:cloudformation:${this.region}:${this.account}:stack/streamr-*/*`,
        `arn:aws:cloudformation:${this.region}:${this.account}:changeset/streamr-*/*`,
      ],
    }));

    // CloudFormation ListStacks requires * resource permission (for debugging)
    this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
      sid: 'CloudFormationListPermissions',
      effect: iam.Effect.ALLOW,
      actions: [
        'cloudformation:ListStacks',
      ],
      resources: ['*'],
    }));

    this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
      sid: 'EC2Permissions',
      effect: iam.Effect.ALLOW,
      actions: [
        'ec2:CreateVpc',
        'ec2:DeleteVpc',
        'ec2:DescribeVpcs',
        'ec2:ModifyVpcAttribute',
        'ec2:CreateSubnet',
        'ec2:DeleteSubnet',
        'ec2:DescribeSubnets',
        'ec2:ModifySubnetAttribute',
        'ec2:CreateInternetGateway',
        'ec2:DeleteInternetGateway',
        'ec2:AttachInternetGateway',
        'ec2:DetachInternetGateway',
        'ec2:DescribeInternetGateways',
        'ec2:CreateRouteTable',
        'ec2:DeleteRouteTable',
        'ec2:DescribeRouteTables',
        'ec2:CreateRoute',
        'ec2:DeleteRoute',
        'ec2:AssociateRouteTable',
        'ec2:DisassociateRouteTable',
        'ec2:CreateSecurityGroup',
        'ec2:DeleteSecurityGroup',
        'ec2:DescribeSecurityGroups',
        'ec2:AuthorizeSecurityGroupIngress',
        'ec2:AuthorizeSecurityGroupEgress',
        'ec2:RevokeSecurityGroupIngress',
        'ec2:RevokeSecurityGroupEgress',
        'ec2:RunInstances',
        'ec2:TerminateInstances',
        'ec2:DescribeInstances',
        'ec2:DescribeInstanceStatus',
        'ec2:DescribeImages',
        'ec2:DescribeKeyPairs',
        'ec2:DescribeAvailabilityZones',
        'ec2:CreateTags',
        'ec2:DescribeTags',
        'ec2:StartInstances',
        'ec2:StopInstances',
        'ec2:RebootInstances',
        'ec2:DescribeInstanceAttribute',
        'ec2:ModifyInstanceAttribute',
      ],
      resources: ['*'], // Some EC2 actions require * (AWS limitation)
    }));

    this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
      sid: 'RDSPermissions',
      effect: iam.Effect.ALLOW,
      actions: [
        'rds:CreateDBInstance',
        'rds:DeleteDBInstance',
        'rds:DescribeDBInstances',
        'rds:ModifyDBInstance',
        'rds:CreateDBSubnetGroup',
        'rds:DeleteDBSubnetGroup',
        'rds:DescribeDBSubnetGroups',
        'rds:CreateDBParameterGroup',
        'rds:DeleteDBParameterGroup',
        'rds:DescribeDBParameterGroups',
        'rds:AddTagsToResource',
        'rds:ListTagsForResource',
        'rds:RemoveTagsFromResource',
      ],
      resources: [
        `arn:aws:rds:${this.region}:${this.account}:db:streamr-*`,
        `arn:aws:rds:${this.region}:${this.account}:subnet-group:streamr-*`,
        `arn:aws:rds:${this.region}:${this.account}:pg:streamr-*`,
      ],
    }));

    this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
      sid: 'ElastiCachePermissions',
      effect: iam.Effect.ALLOW,
      actions: [
        'elasticache:CreateCacheCluster',
        'elasticache:DeleteCacheCluster',
        'elasticache:DescribeCacheClusters',
        'elasticache:ModifyCacheCluster',
        'elasticache:CreateCacheSubnetGroup',
        'elasticache:DeleteCacheSubnetGroup',
        'elasticache:DescribeCacheSubnetGroups',
        'elasticache:AddTagsToResource',
        'elasticache:ListTagsForResource',
        'elasticache:RemoveTagsFromResource',
      ],
      resources: [
        `arn:aws:elasticache:${this.region}:${this.account}:cluster:streamr-*`,
        `arn:aws:elasticache:${this.region}:${this.account}:subnetgroup:streamr-*`,
      ],
    }));

    this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
      sid: 'ELBPermissions',
      effect: iam.Effect.ALLOW,
      actions: [
        'elasticloadbalancing:CreateLoadBalancer',
        'elasticloadbalancing:DeleteLoadBalancer',
        'elasticloadbalancing:DescribeLoadBalancers',
        'elasticloadbalancing:ModifyLoadBalancerAttributes',
        'elasticloadbalancing:CreateListener',
        'elasticloadbalancing:DeleteListener',
        'elasticloadbalancing:DescribeListeners',
        'elasticloadbalancing:ModifyListener',
        'elasticloadbalancing:CreateTargetGroup',
        'elasticloadbalancing:DeleteTargetGroup',
        'elasticloadbalancing:DescribeTargetGroups',
        'elasticloadbalancing:ModifyTargetGroup',
        'elasticloadbalancing:RegisterTargets',
        'elasticloadbalancing:DeregisterTargets',
        'elasticloadbalancing:DescribeTargetHealth',
        'elasticloadbalancing:AddTags',
        'elasticloadbalancing:DescribeTags',
        'elasticloadbalancing:RemoveTags',
      ],
      resources: [
        `arn:aws:elasticloadbalancing:${this.region}:${this.account}:loadbalancer/app/streamr-*/*`,
        `arn:aws:elasticloadbalancing:${this.region}:${this.account}:loadbalancer/net/streamr-*/*`,
        `arn:aws:elasticloadbalancing:${this.region}:${this.account}:targetgroup/streamr-*/*`,
        `arn:aws:elasticloadbalancing:${this.region}:${this.account}:listener/app/streamr-*/*`,
        `arn:aws:elasticloadbalancing:${this.region}:${this.account}:listener/net/streamr-*/*`,
        `arn:aws:elasticloadbalancing:${this.region}:${this.account}:listener-rule/app/streamr-*/*`,
      ],
    }));

    // IAM PassRole with service restrictions (Amazon Q Priority 1 fix)
    this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
      sid: 'IAMPassRoleRestricted',
      effect: iam.Effect.ALLOW,
      actions: ['iam:PassRole'],
      resources: [`arn:aws:iam::${this.account}:role/streamr-*`],
    }));

    // IAM Management permissions (separate from PassRole)
    this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
      sid: 'IAMManagementPermissions',
      effect: iam.Effect.ALLOW,
      actions: [
        'iam:CreateRole',
        'iam:DeleteRole',
        'iam:GetRole',
        'iam:UpdateRole',
        'iam:CreateInstanceProfile',
        'iam:DeleteInstanceProfile',
        'iam:GetInstanceProfile',
        'iam:AddRoleToInstanceProfile',
        'iam:RemoveRoleFromInstanceProfile',
        'iam:AttachRolePolicy',
        'iam:DetachRolePolicy',
        'iam:PutRolePolicy',
        'iam:DeleteRolePolicy',
        'iam:GetRolePolicy',
        'iam:ListRolePolicies',
        'iam:ListAttachedRolePolicies',
        'iam:TagRole',
        'iam:UntagRole',
        'iam:ListRoleTags',
      ],
      resources: [
        `arn:aws:iam::${this.account}:role/streamr-*`,
        `arn:aws:iam::${this.account}:instance-profile/streamr-*`,
      ],
    }));

    this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
      sid: 'SecretsManagerPermissions',
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:CreateSecret',
        'secretsmanager:DeleteSecret',
        'secretsmanager:DescribeSecret',
        'secretsmanager:GetSecretValue',
        'secretsmanager:PutSecretValue',
        'secretsmanager:UpdateSecret',
        'secretsmanager:TagResource',
        'secretsmanager:UntagResource',
        'secretsmanager:ListSecrets',
      ],
      resources: [
        `arn:aws:secretsmanager:${this.region}:${this.account}:secret:streamr-*`,
      ],
    }));

    this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
      sid: 'S3Permissions',
      effect: iam.Effect.ALLOW,
      actions: [
        's3:CreateBucket',
        's3:DeleteBucket',
        's3:GetBucketLocation',
        's3:GetBucketVersioning',
        's3:PutBucketVersioning',
        's3:GetBucketPolicy',
        's3:PutBucketPolicy',
        's3:DeleteBucketPolicy',
        's3:GetBucketPublicAccessBlock',
        's3:PutBucketPublicAccessBlock',
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
        's3:GetBucketTagging',
        's3:PutBucketTagging',
      ],
      resources: [
        `arn:aws:s3:::streamr-*`,
        `arn:aws:s3:::streamr-*/*`,
        `arn:aws:s3:::cdk-*`, // CDK bootstrap bucket access
        `arn:aws:s3:::cdk-*/*`,
      ],
    }));

    this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
      sid: 'SSMPermissions',
      effect: iam.Effect.ALLOW,
      actions: [
        'ssm:SendCommand',
        'ssm:GetCommandInvocation',
        'ssm:DescribeInstanceInformation',
        'ssm:ListCommandInvocations',
        'ssm:GetParameter',
        'ssm:GetParameters',
        'ssm:PutParameter',
        'ssm:DeleteParameter',
        'ssm:DescribeParameters',
      ],
      resources: [
        `arn:aws:ssm:${this.region}:${this.account}:parameter/streamr/*`,
        `arn:aws:ssm:${this.region}:${this.account}:parameter/cdk-bootstrap/*`, // CDK bootstrap parameters
        `arn:aws:ssm:${this.region}:${this.account}:document/AWS-*`,
        `arn:aws:ec2:${this.region}:${this.account}:instance/*`,
      ],
    }));

    // STS permissions for CDK deployment roles
    this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
      sid: 'STSAssumeRolePermissions',
      effect: iam.Effect.ALLOW,
      actions: [
        'sts:AssumeRole',
        'sts:TagSession',
      ],
      resources: [
        `arn:aws:iam::${this.account}:role/cdk-*`, // CDK bootstrap roles
      ],
    }));

    // Output the role ARN for use in GitHub Actions
    new cdk.CfnOutput(this, 'GitHubActionsRoleArn', {
      value: this.githubActionsRole.roleArn,
      description: 'ARN of the IAM role for GitHub Actions',
      exportName: 'StreamrGitHubActionsRoleArn',
    });

    // Output the OIDC provider ARN for reference
    new cdk.CfnOutput(this, 'GitHubOidcProviderArn', {
      value: githubOidcProvider.openIdConnectProviderArn,
      description: 'ARN of the GitHub OIDC identity provider',
      exportName: 'StreamrGitHubOidcProviderArn',
    });

    // Output instructions for GitHub Actions setup
    new cdk.CfnOutput(this, 'GitHubActionsSetupInstructions', {
      value: `Add this role ARN to your GitHub Actions workflow: ${this.githubActionsRole.roleArn}`,
      description: 'Instructions for using this role in GitHub Actions',
    });
  }
} 