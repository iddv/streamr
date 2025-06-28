# Debugging Narrative: The EC2 Instance That Never Updated

## The Goal: Deploy the Stream Lifecycle System

Our objective was to deploy the **Stream Lifecycle System**, a major application upgrade. The new code, in commit `194af44`, was pushed, and the GitHub Actions workflow completed successfully. We expected to see the new features live in our `beta` environment.

## The Twist: A "Successful" Deployment to an Old Server

Although the deployment pipeline reported success, the application running on our production URL (`http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com`) was unchanged. Our integration tests and `curl` commands confirmed it was still running the **old code**.

-   `/streams` endpoint returned the old `"status": "active"`.
-   The new `/streams/live` endpoint didn't exist.

## Our Investigation: The EC2 Revelation

Our debugging journey took a sharp turn.

1.  **Initial Hypothesis (Wrong):** We first assumed a modern containerized setup (ECS) and suspected a failed container image pull. We spent time investigating ECS services and task definitions.
2.  **The Correction (Crucial):** We were reminded to check the CDK code itself. The evidence was clear:
    -   `new ec2.Instance(...)`
    -   `new elbv2_targets.InstanceTarget(this.instance)`
3.  **Correct Diagnosis:** We are not using a container orchestrator like ECS. The architecture is a classic, robust setup: an **Application Load Balancer (ALB) pointing directly to a single EC2 Instance**.

This realization completely changes the problem. The issue is not with container images. The problem is: **how does the code on the EC2 instance get updated after it's been created?**

**The likely culprit is the EC2 UserData script.** This script runs when an instance is first provisioned. It's perfect for setting up the server, but it **does not re-run on subsequent deployments**. Our deployment pipeline updates the infrastructure (like the ALB), but it doesn't have a mechanism to SSH into the running EC2 instance to pull the new code and restart the application.

## How Q Can Solve This Mystery

We need Q to be our hands on the virtual server. Q can investigate the state of the EC2 instance to confirm our theory and find a path forward.

### **Key Questions for Q:**

1.  **Examine the UserData:** Can you retrieve the full `UserData` script for the EC2 instance (`i-0c5a5c767bec5c27e` if it's still the same one) in `eu-west-1`? This will show us exactly what commands ran when the instance was created.
2.  **Check the Deployment Logs on the Instance:** What's in the cloud-init log file at `/var/log/cloud-init-output.log` on the EC2 instance? This log will show the output of the UserData script and tell us if the application setup completed successfully.
3.  **Verify the Running Code:** Can Q connect to the instance and check what code version is actually present in the application directory (e.g., `/home/ec2-user/app`)? Is it the old code, as we suspect?
4.  **Application Service Status:** How is the FastAPI application being run on the server? Is it a `systemd` service? Can Q check its status (`sudo systemctl status streamr-app`) to see when it was last started? This will likely correspond to the initial instance boot time, not our recent deployment time.

By answering these questions, Q can confirm that the application is stale and help us devise a proper deployment strategy that includes updating the code on the running instance. 