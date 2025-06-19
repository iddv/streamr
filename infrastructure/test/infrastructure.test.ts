import * as cdk from 'aws-cdk-lib';
import { GitHubOidcStack } from '../lib/stacks/github-oidc-stack';

describe('StreamrP2P Infrastructure Tests', () => {
  test('GitHub OIDC Stack can be created', () => {
    const app = new cdk.App();
    
    // This should not throw
    expect(() => {
      new GitHubOidcStack(app, 'TestGitHubOidcStack', {
        githubOrg: 'test-org',
        githubRepo: 'test-repo',
        env: {
          region: 'us-east-1',
          account: '123456789012',
        },
      });
    }).not.toThrow();
  });

  test('CDK app synthesis works', () => {
    const app = new cdk.App();
    
    new GitHubOidcStack(app, 'TestStack', {
      githubOrg: 'test',
      githubRepo: 'test',
      env: { region: 'us-east-1', account: '123456789012' },
    });

    // This should not throw
    expect(() => {
      app.synth();
    }).not.toThrow();
  });
}); 