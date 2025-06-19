# 🏢 Multi-Account GitHub OIDC Setup for StreamrP2P

**Secure deployment across Beta and Production AWS accounts**

This guide shows how to configure GitHub OIDC authentication to work with multiple AWS accounts, enabling secure deployments to both beta and production environments.

---

## 🎯 Multi-Account Strategy

### **Why Separate AWS Accounts?**
- ✅ **Complete isolation** between environments
- ✅ **Independent billing** and cost tracking
- ✅ **Separate security boundaries** 
- ✅ **Different compliance requirements**
- ✅ **Reduced blast radius** for incidents

### **Account Structure**
```
GitHub Repository (iddv/streamr)
├── Beta Environment → AWS Account A (123456789012)
└── Production Environment → AWS Account B (987654321098)
```

---

## 🔧 GitHub Repository Variables Setup

### **Step 1: Add Environment-Specific Variables**

Go to: https://github.com/iddv/streamr/settings/variables/actions

Add these **Repository Variables** (NOT secrets):

#### **Beta Environment**
- **Name**: `AWS_ACCOUNT_ID_BETA`
- **Value**: `123456789012` (your current beta account)

#### **Production Environment** 
- **Name**: `AWS_ACCOUNT_ID_PROD`
- **Value**: `987654321098` (your production account)

### **Why Repository Variables?**
- Account IDs are not sensitive information
- Can be logged and referenced in workflow outputs
- Easier to debug deployment issues
- Follows AWS security best practices

---

## 🚀 Deployment Process

### **Current Setup (Beta Only)**
```bash
# Deploy OIDC to your current beta account
./infrastructure/scripts/deploy-oidc.sh
```

### **Future Production Setup**
When you're ready for production:

1. **Create Production AWS Account**
2. **Configure AWS CLI for Production**:
   ```bash
   aws configure --profile production
   # Enter production account credentials
   ```

3. **Deploy OIDC to Production**:
   ```bash
   # Switch to production profile
   export AWS_PROFILE=production
   
   # Deploy OIDC stack
   ./infrastructure/scripts/deploy-oidc.sh
   ```

4. **Update GitHub Variable**:
   - Add the production account ID to `AWS_ACCOUNT_ID_PROD`

---

## 🔄 GitHub Actions Workflow Logic

### **Automatic Account Selection**
The workflow automatically selects the correct AWS account based on the deployment stage:

```yaml
# Beta deployment (default)
- name: Configure AWS credentials using OIDC
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID_BETA }}:role/streamr-github-actions-role
    role-session-name: streamr-github-actions-${{ github.run_id }}
    aws-region: eu-west-1
  if: github.event.inputs.stage == 'beta' || github.event.inputs.stage == ''

# Production deployment
- name: Configure AWS credentials for Production  
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID_PROD }}:role/streamr-github-actions-role
    role-session-name: streamr-github-actions-${{ github.run_id }}
    aws-region: eu-west-1
  if: github.event.inputs.stage == 'prod'
```

### **Deployment Triggers**
```bash
# Deploy to beta (default)
git push origin main

# Deploy to production (manual)
# Go to: https://github.com/iddv/streamr/actions/workflows/deploy.yml
# Click "Run workflow" → Select "prod"
```

---

## 🛡️ Security Model

### **Cross-Account Isolation**
Each AWS account has its own:
- ✅ **OIDC Identity Provider** 
- ✅ **GitHub Actions Role**
- ✅ **Security policies and restrictions**
- ✅ **Resource isolation**
- ✅ **Billing separation**

### **Same Security Standards**
Both accounts use identical security configuration:
- ✅ **Branch restrictions** (main, PRs, environments)
- ✅ **Regional limitations** (eu-west-1)
- ✅ **Resource naming** (streamr-* only)
- ✅ **Service restrictions** (PassRole limitations)
- ✅ **Tagging enforcement** (Project/Stage/ManagedBy)

### **Trust Policy Consistency**
```json
{
  "StringLike": {
    "token.actions.githubusercontent.com:sub": [
      "repo:iddv/streamr:ref:refs/heads/main",
      "repo:iddv/streamr:pull_request",
      "repo:iddv/streamr:environment:beta",    // Beta account
      "repo:iddv/streamr:environment:prod"     // Prod account
    ]
  }
}
```

---

## 📋 Implementation Checklist

### **Phase 1: Beta Setup (Current)**
- [x] Deploy OIDC stack to beta account
- [ ] Add `AWS_ACCOUNT_ID_BETA` to GitHub variables
- [ ] Test beta deployment with OIDC
- [ ] Verify security restrictions work

### **Phase 2: Production Preparation**
- [ ] Create production AWS account
- [ ] Configure production AWS CLI profile
- [ ] Deploy OIDC stack to production account
- [ ] Add `AWS_ACCOUNT_ID_PROD` to GitHub variables
- [ ] Test production deployment workflow

### **Phase 3: Production Deployment**
- [ ] Create production environment in GitHub
- [ ] Configure production-specific settings
- [ ] Test end-to-end production deployment
- [ ] Set up monitoring and alerting

---

## 🧪 Testing Strategy

### **Beta Testing**
```bash
# Test beta deployment
gh workflow run deploy.yml -f stage=beta

# Verify correct account usage
aws sts get-caller-identity
# Should show beta account ID
```

### **Production Testing**
```bash
# Test production deployment (when ready)
gh workflow run deploy.yml -f stage=prod

# Verify correct account usage  
aws sts get-caller-identity
# Should show production account ID
```

### **Cross-Account Validation**
```bash
# Ensure beta role can't access production
aws sts assume-role \
  --role-arn arn:aws:iam::PROD_ACCOUNT:role/streamr-github-actions-role \
  --role-session-name test
# Should fail with access denied
```

---

## 🔍 Troubleshooting

### **"Could not load credentials" Error**
**Cause**: Missing repository variable  
**Solution**: Verify both `AWS_ACCOUNT_ID_BETA` and `AWS_ACCOUNT_ID_PROD` are set

### **"Access Denied" for Production**
**Cause**: OIDC stack not deployed to production account  
**Solution**: Deploy OIDC stack to production account first

### **Wrong Account Deployment**
**Cause**: Incorrect stage parameter  
**Solution**: Verify workflow input stage matches intended environment

### **Debugging Account Selection**
```yaml
# Add this step to verify account selection
- name: Debug Account Selection
  run: |
    echo "Stage: ${{ github.event.inputs.stage || 'beta' }}"
    echo "Beta Account: ${{ vars.AWS_ACCOUNT_ID_BETA }}"
    echo "Prod Account: ${{ vars.AWS_ACCOUNT_ID_PROD }}"
    aws sts get-caller-identity
```

---

## 📊 Cost Considerations

### **Per-Account Costs**
| Resource | Beta Account | Prod Account | Total |
|----------|-------------|-------------|-------|
| OIDC Provider | $0.00 | $0.00 | $0.00 |
| IAM Role | $0.00 | $0.00 | $0.00 |
| CloudFormation | $0.00 | $0.00 | $0.00 |
| **Monthly Total** | **$0.00** | **$0.00** | **$0.00** |

### **Infrastructure Costs**
- **Beta**: $45/month (current)
- **Production**: $98-115/month (estimated)
- **Total**: ~$150/month for both environments

---

## 🎯 Best Practices

### **1. Environment Naming Consistency**
```bash
# Use consistent naming across accounts
Beta: streamr-beta-*
Prod: streamr-prod-*
```

### **2. Separate IAM Policies**
```bash
# Environment-specific policy variations
Beta: More permissive for development
Prod: Stricter security controls
```

### **3. Monitoring & Alerting**
```bash
# Account-specific CloudWatch dashboards
Beta: Development metrics
Prod: Business-critical monitoring
```

### **4. Backup Strategies**
```bash
# Different backup retention
Beta: 7 days (cost optimization)
Prod: 30 days (compliance)
```

---

## 🚀 Quick Start Commands

### **For Current Beta Setup**
```bash
# 1. Deploy OIDC to beta account
./infrastructure/scripts/deploy-oidc.sh

# 2. Add GitHub variable
# Go to GitHub → Settings → Variables → Actions
# Add: AWS_ACCOUNT_ID_BETA = [your account ID]

# 3. Test deployment
git push origin main
```

### **For Future Production Setup**
```bash
# 1. Configure production AWS profile
aws configure --profile production

# 2. Deploy OIDC to production
AWS_PROFILE=production ./infrastructure/scripts/deploy-oidc.sh

# 3. Add production GitHub variable
# Add: AWS_ACCOUNT_ID_PROD = [production account ID]

# 4. Test production deployment
# GitHub → Actions → Run workflow → Select "prod"
```

---

## 📞 Summary

With this multi-account setup:

✅ **Secure isolation** between beta and production  
✅ **Automatic account selection** based on deployment stage  
✅ **Consistent security model** across all environments  
✅ **Zero additional costs** for OIDC authentication  
✅ **Scalable architecture** for future environments  

Your StreamrP2P platform now supports **enterprise-grade multi-account deployment** with GitHub OIDC! 🎉 