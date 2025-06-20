# 🔐 GitHub OIDC Security Review & Action Items

**Date**: 2025-06-19  
**Reviewer**: Amazon Q  
**Scope**: StreamrP2P GitHub OIDC Authentication Implementation  
**Environment**: Beta (Production will use separate AWS account)  

---

## 📊 Executive Summary

The GitHub OIDC implementation is **production-ready** with excellent security foundations. However, several permissions follow overly broad patterns that violate the principle of least privilege. This review identifies specific actions to tighten security while maintaining functionality.

**Current Security Grade**: B+ → **Target Grade**: A

---

## 🎯 Critical Action Items

### **PRIORITY 1: Restrict Overly Broad Permissions**

#### **1.1 ELB Permissions - IMMEDIATE ACTION REQUIRED**
**File**: `infrastructure/lib/stacks/github-oidc-stack.ts` (Lines 140-165)

**Current Issue**:
```typescript
resources: ['*'], // Allows creating ALBs anywhere in account
```

**Required Fix**:
```typescript
resources: [
  `arn:aws:elasticloadbalancing:${this.region}:${this.account}:loadbalancer/app/streamr-*/*`,
  `arn:aws:elasticloadbalancing:${this.region}:${this.account}:loadbalancer/net/streamr-*/*`,
  `arn:aws:elasticloadbalancing:${this.region}:${this.account}:targetgroup/streamr-*/*`,
  `arn:aws:elasticloadbalancing:${this.region}:${this.account}:listener/app/streamr-*/*`,
  `arn:aws:elasticloadbalancing:${this.region}:${this.account}:listener/net/streamr-*/*`,
  `arn:aws:elasticloadbalancing:${this.region}:${this.account}:listener-rule/app/streamr-*/*`,
],
```

#### **1.2 EC2 Permissions - ADD CONDITIONS**
**File**: `infrastructure/lib/stacks/github-oidc-stack.ts` (Lines 65-115)

**Current Issue**: EC2 permissions on `resources: ['*']` without conditions

**Required Fix**: Add regional and tagging conditions:
```typescript
this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
  sid: 'EC2Permissions',
  effect: iam.Effect.ALLOW,
  actions: [
    // ... existing actions
  ],
  resources: ['*'], // Some EC2 actions require *
  conditions: {
    StringEquals: {
      'ec2:Region': this.region,
    },
    ForAllValues: {
      'aws:RequestedRegion': [this.region]
    },
    StringLike: {
      'ec2:ResourceTag/Project': 'streamr-*'
    }
  }
}));
```

#### **1.3 IAM PassRole - RESTRICT SERVICE SCOPE**
**File**: `infrastructure/lib/stacks/github-oidc-stack.ts` (Lines 180-205)

**Current Issue**: `iam:PassRole` without service restrictions

**Required Fix**:
```typescript
this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
  sid: 'IAMPassRoleRestricted',
  effect: iam.Effect.ALLOW,
  actions: ['iam:PassRole'],
  resources: [`arn:aws:iam::${this.account}:role/streamr-*`],
  conditions: {
    StringEquals: {
      'iam:PassedToService': [
        'ec2.amazonaws.com',
        'rds.amazonaws.com',
        'elasticache.amazonaws.com',
        'elasticloadbalancing.amazonaws.com'
      ]
    }
  }
}));

// Separate statement for other IAM actions
this.githubActionsRole.addToPolicy(new iam.PolicyStatement({
  sid: 'IAMManagementPermissions',
  effect: iam.Effect.ALLOW,
  actions: [
    'iam:CreateRole',
    'iam:DeleteRole',
    'iam:GetRole',
    'iam:UpdateRole',
    // ... other actions EXCEPT PassRole
  ],
  resources: [`arn:aws:iam::${this.account}:role/streamr-*`],
}));
```

### **PRIORITY 2: Enhance Trust Policy Security**

#### **2.1 Branch-Specific Access**
**File**: `infrastructure/lib/stacks/github-oidc-stack.ts` (Lines 25-40)

**Current**: Allows all branches (`repo:iddv/streamr:*`)

**Recommended for Beta**: Restrict to main branch and PR environments:
```typescript
assumedBy: new iam.WebIdentityPrincipal(
  githubOidcProvider.openIdConnectProviderArn,
  {
    StringEquals: {
      'token.actions.githubusercontent.com:aud': 'sts.amazonaws.com',
    },
    StringLike: {
      'token.actions.githubusercontent.com:sub': [
        'repo:iddv/streamr:ref:refs/heads/main',
        'repo:iddv/streamr:pull_request',
        'repo:iddv/streamr:environment:beta'
      ]
    }
  }
),
```

### **PRIORITY 3: Add Resource Tagging Enforcement**

#### **3.1 Mandatory Project Tagging**
Add to all resource creation policies:

```typescript
conditions: {
  StringEquals: {
    'aws:RequestedRegion': this.region,
  },
  ForAllValues: {
    'aws:TagKeys': ['Project', 'Stage', 'ManagedBy']
  },
  StringLike: {
    'aws:RequestTag/Project': 'streamr-*'
  }
}
```

---

## 🔧 Implementation Plan

### **Phase 1: Immediate Security Fixes (This Week)**
1. ✅ **Fix ELB permissions** - restrict to `streamr-*` resources
2. ✅ **Add EC2 conditions** - regional and tagging restrictions  
3. ✅ **Separate IAM PassRole** - service-specific conditions
4. ✅ **Test deployment** - ensure no functionality breaks

### **Phase 2: Enhanced Security (Next Week)**
1. ✅ **Implement branch restrictions** in trust policy
2. ✅ **Add resource tagging enforcement**
3. ✅ **Add CloudWatch monitoring** for OIDC events
4. ✅ **Update documentation** with new security model

### **Phase 3: Production Preparation (Future)**
1. ✅ **Create separate prod account OIDC stack**
2. ✅ **Environment-specific role naming**
3. ✅ **Cross-account deployment strategy**
4. ✅ **Security scanning integration**

---

## 📋 Specific Code Changes Required

### **File 1: `infrastructure/lib/stacks/github-oidc-stack.ts`**

**Lines to Modify**:
- **Line 140**: ELB resources array
- **Line 90**: EC2 conditions object  
- **Line 185**: IAM PassRole separation
- **Line 30**: Trust policy conditions

### **File 2: `infrastructure/scripts/deploy-oidc.sh`**
**Enhancement**: Add validation checks for new restrictions

### **File 3: `.github/workflows/deploy.yml`**
**Enhancement**: Add permission validation step

---

## 🧪 Testing Strategy

### **Pre-Deployment Testing**
```bash
# 1. Validate IAM policy syntax
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT:role/streamr-github-actions-role \
  --action-names ec2:RunInstances \
  --resource-arns "arn:aws:ec2:eu-west-1:ACCOUNT:instance/*"

# 2. Test resource creation with new restrictions
aws ec2 run-instances --dry-run \
  --image-id ami-12345 \
  --instance-type t3.micro \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Project,Value=streamr-beta}]'
```

### **Post-Deployment Validation**
```bash
# 1. Verify OIDC authentication still works
aws sts get-caller-identity

# 2. Test restricted permissions
aws elasticloadbalancing create-load-balancer \
  --name test-streamr-alb \
  --subnets subnet-12345 \
  --dry-run

# 3. Verify denied actions fail appropriately
aws elasticloadbalancing create-load-balancer \
  --name unauthorized-alb \
  --subnets subnet-12345 \
  --dry-run
```

---

## 🚨 Risk Assessment

### **Current Risks (Before Fixes)**
- **HIGH**: ELB permissions allow creating load balancers anywhere in account
- **MEDIUM**: EC2 permissions lack regional restrictions
- **MEDIUM**: IAM PassRole without service restrictions
- **LOW**: Branch access too permissive

### **Residual Risks (After Fixes)**
- **LOW**: Some EC2 actions still require `*` resources (AWS limitation)
- **LOW**: CloudFormation permissions are broad by necessity
- **MINIMAL**: All other permissions properly scoped

---

## 💡 Future Enhancements

### **For Production Account Setup**
1. **Separate OIDC providers** per environment
2. **Cross-account role assumptions** for multi-account strategy
3. **AWS Config rules** for compliance monitoring
4. **AWS Security Hub** integration

### **Advanced Security Features**
1. **IP address restrictions** in trust policy
2. **Time-based access controls** for deployments
3. **MFA requirements** for sensitive operations
4. **Automated security scanning** in CI/CD

---

## 📊 Compliance & Audit

### **Security Standards Met**
- ✅ **Principle of Least Privilege** (after fixes)
- ✅ **Defense in Depth** with multiple restriction layers
- ✅ **Audit Trail** via CloudTrail integration
- ✅ **Short-lived Credentials** (1-hour max)

### **Audit Trail Verification**
```bash
# Check OIDC role assumptions
aws logs filter-log-events \
  --log-group-name CloudTrail/OIDCEvents \
  --filter-pattern "{ $.eventName = AssumeRoleWithWebIdentity }"

# Monitor resource creation
aws logs filter-log-events \
  --log-group-name CloudTrail/ResourceEvents \
  --filter-pattern "{ $.userIdentity.type = AssumedRole && $.userIdentity.arn = *streamr-github-actions-role* }"
```

---

## ✅ Action Checklist for Agent

### **Immediate Actions (Priority 1)**
- [ ] **Modify ELB permissions** in `github-oidc-stack.ts`
- [ ] **Add EC2 conditions** for regional/tagging restrictions
- [ ] **Separate IAM PassRole** with service conditions
- [ ] **Test deployment** with new restrictions
- [ ] **Verify GitHub Actions** still work correctly

### **This Week (Priority 2)**
- [ ] **Implement branch restrictions** in trust policy
- [ ] **Add resource tagging enforcement**
- [ ] **Create CloudWatch monitoring** for OIDC events
- [ ] **Update deployment documentation**

### **Next Sprint (Priority 3)**
- [ ] **Plan production account** OIDC strategy
- [ ] **Design cross-account** deployment approach
- [ ] **Implement security scanning** in pipeline
- [ ] **Create compliance dashboard**

---

## 📞 Support & Questions

For implementation questions or security concerns:
1. **Review AWS IAM Best Practices**: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
2. **Test changes in development** before applying to beta
3. **Monitor CloudTrail logs** for access patterns
4. **Validate with AWS Config** rules for compliance

---

**End of Report**  
**Next Review Date**: After Priority 1 implementation  
**Security Contact**: Continue with Amazon Q for implementation guidance
