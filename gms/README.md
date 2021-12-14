# Running Workflows via GMS


## Initial Setup

Enter docker container for this repo, `jackmaruska/cloudize-workflow:latest`


Enable requisite APIs in Google Cloud Platform. Easiest way to do this
is probably just to navigate to them in the web console.

https://console.cloud.google.com/storage
https://console.cloud.google.com/compute
https://console.cloud.google.com/lifesciences/pipelines
https://console.cloud.google.com/iam-admin


Create requisite resources. Any that already exist will spit out an
"already exists" stderr but these can be safely ignored. This creates
the required service accounts, bucket, and permissions.
```
sh /opt/resources.sh --project PROJECT --bucket BUCKET
```

Add the values given from this script to your environment
configuration.

You should now be able to run a workflow on the cloud via your new
environment configuration.
