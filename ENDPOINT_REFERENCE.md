# 🎯 StreamrP2P Stable Endpoint Reference

## ⚡ **STABLE ENDPOINTS (Never Change!)**

### 🌐 **Web Dashboard & API**
```
http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com/
```
- **Status**: ✅ STABLE (ALB DNS - never changes)
- **Purpose**: Web dashboard, coordinator API, stream management
- **Health Check**: `http://[ALB-DNS]/health`

### 📺 **HLS Video Streaming** 
```
http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com:8080/live/{stream}.m3u8
```
- **Status**: ✅ STABLE (ALB DNS - never changes)  
- **Purpose**: Watch streams in web browsers, mobile apps
- **Example**: `http://[ALB-DNS]:8080/live/mystream.m3u8`
- **Health Check**: `http://[ALB-DNS]:8080/api/v1/version`

### 🎥 **RTMP Publishing**
```
rtmp://ELASTIC-IP:1935/live/{stream-key}
```
- **Status**: ✅ STABLE (Elastic IP - never changes)
- **Purpose**: Publish streams from OBS, streaming software
- **Note**: Only endpoint that needs direct IP (ALB can't handle RTMP/TCP)

---

## 🏗️ **Architecture Explanation**

### **Why This Setup?**
1. **ALB (Load Balancer)** handles all **HTTP traffic** with stable DNS
2. **Elastic IP** handles **RTMP streaming** with stable IP  
3. **No more changing endpoints** on deployments!

### **Before vs After**
```
❌ BEFORE: Instance IP changes every deployment
   Dashboard: http://54.154.29.216/     (BREAKS!)
   Streaming: http://54.154.29.216:8080/ (BREAKS!)
   RTMP: rtmp://54.154.29.216:1935/      (BREAKS!)

✅ AFTER: Stable endpoints that never change
   Dashboard: http://streamr-p2p-beta-alb-*.elb.amazonaws.com/     (STABLE!)
   Streaming: http://streamr-p2p-beta-alb-*.elb.amazonaws.com:8080/ (STABLE!)
   RTMP: rtmp://ELASTIC-IP:1935/                                   (STABLE!)
```

---

## 📝 **For Documentation & Friends**

### **Copy-Paste URLs**
```bash
# Web Dashboard
http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com/

# HLS Streaming (replace {stream} with your stream name)
http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com:8080/live/{stream}.m3u8

# RTMP Publishing (replace {stream-key} with your stream key)  
rtmp://ELASTIC-IP:1935/live/{stream-key}
```

### **Quick Tests**
```bash
# Test coordinator health
curl http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com/health

# Test SRS streaming server
curl http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com:8080/api/v1/version
```

---

## 🚀 **Next Steps**

1. **Deploy** this improved architecture: `./scripts/deploy-beta.sh`
2. **Update** all documentation with stable URLs
3. **Share** stable endpoints with friends for testing
4. **No more** worrying about changing IPs!

---

*✨ This architecture eliminates the #1 pain point of constantly changing endpoints!* 