# 🌐 Elastic IP Setup for RTMP Streaming

## Overview
Your existing Elastic IP (`52.213.32.59` / `eipalloc-054297e161bb78275`) has been integrated into the CDK infrastructure to provide a static IP for RTMP streaming.

## ⚠️ Important: Single-AZ Deployment
For the **validation phase**, the NLB is configured for single-AZ deployment since we only have one Elastic IP. This is acceptable for testing but creates a single point of failure.

**For production**, you should:
1. Allocate additional Elastic IPs (one per AZ)
2. Update the CDK configuration to use multiple EIPs for high availability

## Changes Made

### 1. Application Stack Updates (`application-stack.ts`)
- ✅ **Elastic IP Association**: Network Load Balancer uses your existing Elastic IP
- ✅ **Single-AZ Configuration**: Explicitly configured for validation phase safety
- ✅ **Static RTMP Endpoint**: RTMP endpoint updated to `rtmp://52.213.32.59:1935/live`
- ✅ **Subnet Mapping**: Configured NLB with proper subnet mapping for Elastic IP
- ✅ **Updated Outputs**: All outputs now show static IP instead of dynamic DNS

### 2. GitHub Actions Permissions (`github-oidc-stack.ts`)
- ✅ **Secure Permissions**: Added only necessary Elastic IP permissions (describe, associate, disassociate)
- ✅ **No Delete Risk**: Removed dangerous AllocateAddress/ReleaseAddress permissions
- ✅ **Deploy-Ready**: GitHub Actions can safely manage Elastic IP associations

## 🚀 Deployment

### Deploy to Beta Environment
```bash
cd infrastructure
npm install

# Deploy updated stacks
npx cdk deploy streamr-p2p-beta-ireland-application \
    --context stage=beta \
    --context region=eu-west-1 \
    --require-approval never
```

### Verify Deployment
```bash
# Check outputs
npx cdk list --context stage=beta --context region=eu-west-1

# Test RTMP endpoint
ffmpeg -f lavfi -i testsrc2=size=1280x720:rate=30 \
    -f lavfi -i sine=frequency=1000:sample_rate=48000 \
    -c:v libx264 -preset ultrafast -tune zerolatency \
    -c:a aac -ar 48000 -b:a 128k \
    -f flv rtmp://52.213.32.59:1935/live/test
```

## 📡 New Endpoints

| Service | Endpoint | Description |
|---------|----------|-------------|
| **RTMP** | `rtmp://52.213.32.59:1935/live` | Static IP for streaming |
| **Dashboard** | `http://[ALB-DNS]/` | Web interface |
| **HLS** | `http://[ALB-DNS]:8080/live/{stream}.m3u8` | Stream playback |

## 🎯 Benefits

✅ **Static IP**: No more dynamic DNS changes for RTMP  
✅ **OBS Friendly**: Easy to configure in streaming software  
✅ **Validation Ready**: Stable endpoint for economic validation testing  
✅ **CDK Managed**: Infrastructure as code with proper associations  
✅ **Secure**: No risk of accidentally deleting the static IP

## 🔧 Technical Details

The Elastic IP is associated with the Network Load Balancer using CloudFormation's `SubnetMappings` property:

```typescript
// Single-AZ deployment for validation phase
const primaryPublicSubnet = vpc.publicSubnets[0];

cfnNlb.addPropertyOverride('SubnetMappings', [
  {
    SubnetId: primaryPublicSubnet.subnetId,
    AllocationId: 'eipalloc-054297e161bb78275',
  },
]);
```

This ensures the static IP is properly attached to the NLB and will persist across deployments.

## 🚀 Production Readiness
For production deployment, upgrade to multi-AZ by:
1. Allocating EIPs for each AZ: `aws ec2 allocate-address --domain vpc`
2. Updating the subnet mappings to include all AZs with their respective EIPs 