# 🌐 StreamrP2P Live Production Endpoints

> **🎯 STABLE ARCHITECTURE DEPLOYED!** These endpoints now use **permanent Elastic IP** and **stable ALB DNS** - they will **NEVER CHANGE** on redeployments!

## ⚡ **STABLE ENDPOINTS (Updated Jan 2025)**

### 🎮 **For Streamers**
```bash
# RTMP Publishing (OBS Studio, etc.)
rtmp://52.213.32.59:1935/live/{your-stream-key}
```

### 📺 **For Viewers** 
```bash
# HTTP-FLV (RECOMMENDED for VLC - Low latency)
http://52.213.32.59:8080/live/{stream-name}.flv

# HLS (For web browsers - Higher latency)
http://52.213.32.59:8080/live/{stream-name}.m3u8

# Examples with existing stream:
http://52.213.32.59:8080/live/obs-test.flv    (VLC)
http://52.213.32.59:8080/live/obs-test.m3u8   (Browser)
```

### 🌐 **Web Dashboard & API**
```bash
# Main Dashboard (Stable ALB DNS)
http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com/

# API Health Check
http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com/health

# API Endpoints
http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com/streams
http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com/payouts
```

### 🔧 **SRS Admin Console**
```bash
# SRS Server Console (Direct Elastic IP) - ✅ WORKING
http://52.213.32.59:8080/

# Note: API endpoint may vary, console works for monitoring
```

---

## 🎯 **MAJOR IMPROVEMENT: Stable Endpoints**

### **Before (Problematic)**
- **Instance IP**: Changed every deployment (54.154.29.216 → NEW IP)  
- **Documentation**: Broke on every redeploy
- **Friends**: Had to update configurations constantly

### **After (Stable)** ✅
- **Elastic IP**: `52.213.32.59` (PERMANENT - never changes)
- **ALB DNS**: `streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com` (STABLE)
- **Documentation**: Never breaks again
- **Friends**: Set URLs once, work forever

---

## 📊 **System Status**

| Component | Status | Endpoint |
|-----------|--------|----------|
| 🎮 **Coordinator API** | ✅ RUNNING | ALB DNS (stable) |
| 📺 **SRS Streaming** | ✅ WORKING | Elastic IP (stable) |
| 🔗 **Load Balancer** | ✅ HEALTHY | ALB DNS (stable) |
| 💾 **Database** | ✅ OPERATIONAL | Internal |
| ⚡ **Cache** | ✅ OPERATIONAL | Internal |

**Last Updated**: January 2025  
**Architecture**: Stable Endpoint v2.0 with Elastic IP + Fixed Security Groups  
**Deployment**: streamr-p2p-beta-ireland-application

---

## 🚀 **Ready for Friends Testing**

**Share these stable URLs with friends** - they will never change again:

```bash
# For Streamers (RTMP)
rtmp://52.213.32.59:1935/live/

# For Viewers - VLC (RECOMMENDED) 
http://52.213.32.59:8080/live/{stream}.flv

# For Viewers - Web Browsers
http://52.213.32.59:8080/live/{stream}.m3u8

# Web Dashboard
http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com/
```

**✨ Problem Solved**: 
- ✅ Stable endpoints that never change
- ✅ SRS streaming working with proper security groups  
- ✅ Both FLV (VLC) and HLS (browsers) available