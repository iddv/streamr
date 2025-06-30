# Migration Plan: EC2 to ECS Fargate

This tracker outlines the tasks required to migrate the StreamrP2P coordinator application from a single EC2 instance to a scalable ECS Fargate service.

---

### Phase 1: Infrastructure Setup (CDK) ✅
*   [x] **Create ECR Repository:** In `foundation-stack.ts`, define a new ECR (Elastic Container Registry) repository to store the application's Docker images.
*   [x] **Create ECS Cluster:** Define a new, empty ECS Cluster in `foundation-stack.ts`. This provides the logical grouping for our application services.

---

### Phase 2: Refactor Application Stack (CDK) ✅
This is the core of the work, done in `application-stack.ts`.
*   [x] **Remove EC2 Instance:** Delete the `ec2.Instance` resource and its associated role, security group, and Elastic IP logic.
*   [x] **Add ECS Task Definition:** Define a Fargate task with both coordinator and SRS containers.
*   [x] **Add ECS Service:** Create a Fargate service to run the task.
*   [x] **Update Load Balancer:** Modify target groups to point to ECS service instead of EC2 instance.
*   [x] **Update Security Groups:** Adapt security groups for ECS networking.
*   [x] **Update IAM Roles:** Replace EC2 instance role with ECS task execution and task roles.
*   [x] **Update Outputs:** Change stack outputs to reflect ECS resources instead of EC2.
*   [x] **Wire Stacks Together:** Update main deployment file to pass ECR and ECS resources between stacks.

---

### Phase 3: Update CI/CD Pipeline (GitHub Actions) ✅
Modify the `.github/workflows/deploy.yml` file.
*   [x] **Add Docker Build & Push Step:**
    *   [x] Add a step to log in to Amazon ECR.
    *   [x] Add a step to build the `coordinator` Docker image.
    *   [x] Tag the image with the unique Git commit SHA for versioning.
    *   [x] Push the tagged image to the ECR repository.
*   [x] **Update Dockerfile:**
    *   [x] Add AWS CLI for fetching secrets and configuration.
    *   [x] Create entrypoint script to handle ECS environment setup.
    *   [x] Configure proper health checks and container startup.

---

### Phase 4: Validation and Cleanup
*   [ ] **Deploy:** Run the new GitHub Actions workflow to deploy the Fargate service for the first time.
*   [ ] **Verify:**
    *   [ ] Check the ECS console to confirm the new service and task are running.
    *   [ ] View the application logs in CloudWatch to ensure a clean startup.
    *   [ ] **Run the integration test suite.** This is the ultimate validation. The tests should now pass and detect the new Stream Lifecycle System.
*   [ ] **Cleanup (Optional):** Once confirmed, remove any old, now-unused resources from the CDK stack (like the EC2 key pair).

---

## 🎉 **MIGRATION STATUS: READY FOR DEPLOYMENT!**

### **✅ Completed:**
- **Phase 1**: Infrastructure Setup (ECR + ECS Cluster)
- **Phase 2**: Complete Application Stack Refactoring (EC2 → ECS Fargate)  
- **Phase 3**: CI/CD Pipeline & Docker Updates

### **🚀 Ready to Deploy:**
The migration is complete and ready for deployment! The next push to `main` branch will:

1. **Build & Push**: Docker image to ECR with commit SHA tag
2. **Deploy**: ECS Fargate service with coordinator + SRS containers
3. **Test**: Integration tests will validate the Stream Lifecycle System
4. **Success**: Your deployment issue will be resolved!

### **Key Improvements:**
- ✅ **Automatic Deployments**: No more manual SSH or UserData scripts
- ✅ **Container Orchestration**: ECS handles container lifecycle automatically  
- ✅ **Horizontal Scaling**: Ready to scale beyond 1 instance
- ✅ **Proper CI/CD**: Docker images versioned by Git commit
- ✅ **AWS Integration**: Secrets Manager + CloudFormation integration
- ✅ **Load Balancing**: ALB for HTTP + NLB for RTMP streaming 