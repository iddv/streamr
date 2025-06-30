Subject: Deployment Issue on 'beta' stage

Pushed commit `194af44` to deploy the Stream Lifecycle System. GitHub Actions succeeded, but the EC2 instance is still running the old code.

We've confirmed the architecture is an EC2 instance, not ECS. The problem is likely that the UserData script doesn't re-run on new deployments, so the code on the instance is never updated.

To confirm, can you please check the EC2 instance in `eu-west-1`:

1.  What code is in `/home/ec2-user/app`? (`ls -la`)
2.  When was the app service last started? (`sudo systemctl status streamr-app`)
3.  Can you get the initial `UserData` script and the logs from `/var/log/cloud-init-output.log`?

This will tell us what's actually running and help us fix the deployment process. Thanks! 