# 🔐 GitHub OIDC Authentication Setup for StreamrP2P

**Secure CI/CD without long-lived credentials**

This guide shows you how to set up OpenID Connect (OIDC) authentication between GitHub Actions and AWS, eliminating the need for storing long-lived AWS credentials in GitHub secrets.

---

## 🎯 Why OIDC?

### **Security Benefits**
- ✅ **No long-lived credentials** stored in GitHub secrets
- ✅ **Short-lived tokens** (1 hour max session duration)
- ✅ **Scoped permissions** - only specific repositories can assume the role
- ✅ **Audit trail** - all AWS actions are logged with GitHub context
- ✅ **Automatic rotation** - tokens are generated fresh for each workflow run

### **vs. Traditional Approach**
| Traditional (Secrets) | OIDC Authentication |
|----------------------|-------------------|
| Long-lived credentials | Short-lived tokens |
| Manual rotation needed | Automatic rotation |
| Stored in GitHub secrets | No secrets needed |
| Risk if compromised | Self-expiring tokens |
| Hard to audit | Full audit trail |

---

## 🚀 Quick Setup

### **Step 1: Deploy OIDC Stack**
```bash
# Run the deployment script
./infrastructure/scripts/deploy-oidc.sh
```

This will:
- Create GitHub OIDC Identity Provider in AWS
- Create IAM role with necessary permissions
- Output the AWS Account ID and Role ARN

### **Step 2: Add GitHub Repository Variable**
1. Go to: https://github.com/iddv/streamr/settings/variables/actions
2. Click "New repository variable"
3. Add:
   - **Name**: `AWS_ACCOUNT_ID`
   - **Value**: Your AWS account ID (from script output)

### **Step 3: Test the Setup**
Push a change to trigger GitHub Actions - it will now use OIDC authentication!

---

## 🔧 Manual Setup (Alternative)

If you prefer to understand each step:

### **1. Create OIDC Identity Provider**
```bash
# Using AWS CLI
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  --client-id-list sts.amazonaws.com
```

### **2. Create IAM Role**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:iddv/streamr:*"
        }
      }
    }
  ]
}
```

### **3. Attach Policies**
The CDK stack creates comprehensive policies for:
- CloudFormation operations
- EC2 management
- RDS management
- ElastiCache management
- Load Balancer management
- IAM role management
- Secrets Manager access
- S3 operations
- SSM operations

---

## 🛡️ Security Configuration

### **Repository Restrictions**
The OIDC role is configured to only trust:
- **Organization**: `iddv`
- **Repository**: `streamr`
- **Access**: Restricted to main branch, pull requests, and beta environment (Amazon Q enhanced security)

### **Enhanced Security Features (Amazon Q Recommendations)**
✅ **Branch-Specific Access**: Only `main` branch, PRs, and `beta` environment  
✅ **Regional Restrictions**: All resources limited to `eu-west-1`  
✅ **Service-Specific PassRole**: IAM PassRole restricted to specific AWS services  
✅ **Resource Tagging Enforcement**: Mandatory Project, Stage, ManagedBy tags  
✅ **ELB Resource Scoping**: Load balancers restricted to `streamr-*` naming pattern  

### **Scope Restrictions**
You can further restrict access by modifying the trust policy:

```json
// Current: Restricted to main branch, PRs, and beta environment
"token.actions.githubusercontent.com:sub": [
  "repo:iddv/streamr:ref:refs/heads/main",
  "repo:iddv/streamr:pull_request", 
  "repo:iddv/streamr:environment:beta"
]

// Allow only specific environment
"token.actions.githubusercontent.com:sub": "repo:iddv/streamr:environment:production"

// Allow only tags
"token.actions.githubusercontent.com:sub": "repo:iddv/streamr:ref:refs/tags/*"
```

### **Session Duration**
- **Maximum**: 1 hour (configured in CDK)
- **Typical workflow**: 10-15 minutes
- **Automatic expiration**: No manual cleanup needed

---

## 🔄 GitHub Actions Configuration

### **Required Permissions**
```yaml
permissions:
  id-token: write   # Required for requesting JWT
  contents: read    # Required for actions/checkout
```

### **Authentication Step**
```yaml
- name: Configure AWS credentials using OIDC
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/streamr-github-actions-role
    role-session-name: streamr-github-actions-${{ github.run_id }}
    aws-region: eu-west-1
```

### **Complete Workflow Example**
```yaml
name: Deploy with OIDC
on:
  push:
    branches: [ main ]

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/streamr-github-actions-role
          role-session-name: deploy-${{ github.run_id }}
          aws-region: eu-west-1
      
      - name: Deploy infrastructure
        run: |
          cd infrastructure
          npm ci
          npm run build
          npx cdk deploy --all --require-approval never
```

---

## 🧪 Testing & Validation

### **Test OIDC Authentication**
```bash
# In GitHub Actions, this should work without any secrets
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AROAXXXXXXXXXXXXX:streamr-github-actions-1234567890",
    "Account": "123456789012",
    "Arn": "arn:aws:sts::123456789012:assumed-role/streamr-github-actions-role/streamr-github-actions-1234567890"
}
```

### **Verify Permissions**
```bash
# Test CloudFormation access
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE

# Test EC2 access
aws ec2 describe-instances --filters "Name=tag:Project,Values=streamr-p2p"
```

### **Check Token Expiration**
```bash
# This will show when the token expires
aws sts get-session-token --query 'Credentials.Expiration'
```

---

## 🔍 Troubleshooting

### **"Error: Could not load credentials"**
**Cause**: GitHub repository variable `AWS_ACCOUNT_ID` not set
**Solution**: Add the variable in GitHub repository settings

### **"Error: Access Denied"**
**Cause**: Role trust policy doesn't match repository
**Solution**: Verify the trust policy includes your repository path

### **"Error: Invalid identity token"**
**Cause**: Missing `id-token: write` permission
**Solution**: Add required permissions to workflow

### **"Error: Role ARN not found"**
**Cause**: OIDC stack not deployed
**Solution**: Run `./infrastructure/scripts/deploy-oidc.sh`

### **Check OIDC Configuration**
```bash
# Verify OIDC provider exists
aws iam list-open-id-connect-providers

# Check role trust policy
aws iam get-role --role-name streamr-github-actions-role

# List role policies
aws iam list-attached-role-policies --role-name streamr-github-actions-role
```

---

## 📊 Cost Impact

### **OIDC vs. Secrets Comparison**
| Aspect | OIDC | Secrets |
|--------|------|---------|
| AWS Costs | **Free** | **Free** |
| Security Risk | **Low** | **Medium** |
| Maintenance | **None** | **Manual rotation** |
| Audit Trail | **Complete** | **Limited** |
| Setup Complexity | **One-time** | **Ongoing** |

### **AWS Resources Created**
- **OIDC Identity Provider**: Free
- **IAM Role**: Free
- **IAM Policies**: Free
- **CloudFormation Stack**: Free

**Total Additional Cost**: $0.00/month

---

## 🎯 Best Practices

### **1. Principle of Least Privilege**
```bash
# Only grant permissions your workflows actually need
# Review and remove unused permissions regularly
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT:role/streamr-github-actions-role \
  --action-names ec2:DescribeInstances \
  --resource-arns "*"
```

### **2. Environment-Specific Roles**
```yaml
# Different roles for different environments
role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/streamr-${{ github.event.inputs.environment }}-role
```

### **3. Monitoring & Alerting**
```bash
# Set up CloudWatch alerts for role assumptions
aws logs create-log-group --log-group-name /aws/iam/github-actions

# Monitor for unusual activity
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=streamr-github-actions-role
```

### **4. Regular Security Reviews**
- **Monthly**: Review role permissions
- **Quarterly**: Audit CloudTrail logs
- **Annually**: Rotate OIDC thumbprints if needed

---

## 📚 Additional Resources

### **AWS Documentation**
- [IAM OIDC Identity Providers](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)
- [AssumeRoleWithWebIdentity](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRoleWithWebIdentity.html)

### **GitHub Documentation**
- [Configuring OpenID Connect in AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [Security hardening with OpenID Connect](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)

### **StreamrP2P Resources**
- [AWS Deployment Guide](AWS_DEPLOYMENT_GUIDE.md)
- [CDK Infrastructure Plan](STREAMR_CDK_INFRASTRUCTURE_PLAN.md)
- [Security & Cost Review](../AWS_ARCHITECTURE_SECURITY_COST_REVIEW.md)

---

## 🎉 Summary

With GitHub OIDC authentication configured:

✅ **No more AWS secrets** in GitHub repository  
✅ **Enhanced security** with short-lived tokens  
✅ **Zero additional cost** for OIDC setup  
✅ **Automatic credential rotation** built-in  
✅ **Complete audit trail** for all AWS operations  
✅ **Production-ready** CI/CD pipeline  

Your StreamrP2P deployment pipeline is now **secure, automated, and maintainable**! 