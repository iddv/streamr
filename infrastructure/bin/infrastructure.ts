#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { FoundationStack } from '../lib/stacks/foundation-stack';
import { ApplicationStack } from '../lib/stacks/application-stack';
import { GitHubOidcStack } from '../lib/stacks/github-oidc-stack';
import { createDeploymentContext, getValidStages, getValidRegions, getPrimaryRegion } from '../lib/config/deployment-context';

const app = new cdk.App();

// Get deployment parameters from context or environment
const stage = app.node.tryGetContext('stage') || process.env.STAGE || 'beta';
const region = app.node.tryGetContext('region') || process.env.CDK_DEFAULT_REGION || getPrimaryRegion();

// Validate stage and region
if (!getValidStages().includes(stage)) {
  throw new Error(`Invalid stage: ${stage}. Valid stages: ${getValidStages().join(', ')}`);
}

if (!getValidRegions().includes(region)) {
  throw new Error(`Invalid region: ${region}. Valid regions: ${getValidRegions().join(', ')}`);
}

console.log(`🚀 Deploying StreamrP2P to stage: ${stage}, region: ${region}`);

// Create deployment context
const context = createDeploymentContext(stage, region);

// GitHub OIDC Stack - Deploy first for CI/CD authentication
const githubOidcStack = new GitHubOidcStack(app, context.stackName('github-oidc'), {
  githubOrg: 'iddv',
  githubRepo: 'streamr',
  env: {
    region: context.region,
  },
  description: 'StreamrP2P GitHub OIDC Authentication Stack',
  tags: {
    Project: 'streamr-p2p',
    Stage: context.stage,
    Region: context.region,
    StackType: 'oidc-auth',
  },
});

// Foundation Stack - VPC, RDS, ElastiCache
const foundationStack = new FoundationStack(app, context.stackName('foundation'), {
  context,
  env: {
    region: context.region,
  },
  description: `StreamrP2P Foundation Stack - ${context.stageConfig.description}`,
  tags: {
    Project: 'streamr-p2p',
    Stage: context.stage,
    Region: context.region,
    StackType: 'foundation',
  },
});

// Application Stack - EC2, ALB
const applicationStack = new ApplicationStack(app, context.stackName('application'), {
  context,
  vpc: foundationStack.vpc,
  dbSecurityGroup: foundationStack.dbSecurityGroup,
  cacheSecurityGroup: foundationStack.cacheSecurityGroup,
  deploymentBucket: foundationStack.deploymentBucket,
  env: {
    region: context.region,
  },
  description: `StreamrP2P Application Stack - ${context.stageConfig.description}`,
  tags: {
    Project: 'streamr-p2p',
    Stage: context.stage,
    Region: context.region,
    StackType: 'application',
  },
});

// Application stack depends on foundation stack
applicationStack.addDependency(foundationStack);

// Add global tags
cdk.Tags.of(app).add('Project', 'streamr-p2p');
cdk.Tags.of(app).add('ManagedBy', 'CDK');
cdk.Tags.of(app).add('Repository', 'streamr-p2p-monorepo');

// Output deployment summary
console.log(`📊 Deployment Summary:`);
console.log(`   Stage: ${context.stage} (${context.stageConfig.description})`);
console.log(`   Region: ${context.region} (${context.regionConfig.name})`);
console.log(`   Instance Size: ${context.stageConfig.instanceSize}`);
console.log(`   Multi-AZ: ${context.stageConfig.multiAz ? 'Yes' : 'No'}`);
console.log(`   Deletion Protection: ${context.stageConfig.enableDeletionProtection ? 'Yes' : 'No'}`);
console.log(`   Backups: ${context.stageConfig.enableBackups ? 'Yes' : 'No'}`);
console.log(`   Detailed Monitoring: ${context.stageConfig.monitoring.detailed ? 'Yes' : 'No'}`);
console.log(`   GitHub OIDC Stack: ${githubOidcStack.stackName}`);
console.log(`   Foundation Stack: ${foundationStack.stackName}`);
console.log(`   Application Stack: ${applicationStack.stackName}`);