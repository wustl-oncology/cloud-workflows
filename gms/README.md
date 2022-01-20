# Running Workflows via GMS

This codebase is primarily concerned with first-time setup and
providing required resources to operate the GMS integration. Details
on how to use these resources through the GMS interface are provided
[on the GMS
wiki](https://github.com/genome/genome/wiki/Running-on-Google-Cloud)


# Initial Setup


In order to create and use resources for the various Google Cloud
APIs, you must manually enter the web console and enable them for the
project. [See instructions here](../docs/enable_api.md).


Create requisite resources. Any that already exist will spit out an
"already exists" stderr but these can be safely ignored. This creates
the required service accounts, bucket, and permissions.
```
sh resources.sh --project PROJECT \
    --inputs-bucket INPUTS_BUCKET \
    --executions-bucket EXECUTIONS_BUCKET
```

Add the values given from this script to your environment
configuration.

You should now be able to run a workflow on the cloud via your new
environment configuration.


# Who can use these resources?

Permissions required to run a GMS workflow are:
- create a compute instance
- read/write files to bucket
- use Cromwell server service account
  which enables using the Cromwell compute service account, and run
  lifesciences workflows

GMS should be enforcing these requirements on the running user,
meaning you have to be `gcloud auth`d to operate. This works for
manual workflow kickoffs but not for automated ingestion, which will
be tackled later.
