# CWL Changes

Because LSF and GCP approaches to running Cromwell have divergent
properties, there are a number of differences required in the CWL
files. The hope is to cover as many of these in an automated fashion
as possible. Sometimes this won't be possible. This document aims to
detail those differences and whether or not they're handled
automatically.


### 1. File locations must refer to buckets

In LSF, files are specified locally. In GCP they must be uploaded to a
GCS bucket and referenced by URI.

Automated: Yes. cloudize-workflow.py script


### 2. Must explicitly state resource requirements

In LSF, there's an assumption of certain amounts of disk space
available, RAM, etc. Because GCP spins up separate isolated compute
workers for each task in the workflow, these tasks must have their
resource requirements specified explicitly.

As an side, WDL has a feature that allows dynamic allocation based on
input sizes. Conversion may be something to consider.

Automated: No. Cannot be with CWL v1.0


### 3. Modular workflow task definitions just available

In the analysis-workflows repo, all workflows are defined relative to
one another. To submit jobs using these repos, those dependencies must
be zipped together, and the topmost CWL must refer to them as if it
were located besides the .zip file.

The zip step only needs to be done once per update to
analysis-workflows though. That artifact generation could be automated
in the future.

Automated: No. May be later.


### 4. Cannot use union type on File inputs

Throughout analysis-workflows there are a number of inputs with

    type:
        - File
        - string

This union type of File and string together causes GCP-based runs to
fail, because Cromwell will believe that it doesn't need to pull the
file down from the GCS bucket. Remove all union types that should just
be File.

Similar issues happen for complex Record types including File inputs.

Automated: No.


### 5. Directory input likely requires tmpdirMin setting

Trying to use a Directory input which refers to a path on GCS, unless
that directory is fairly minimal, will result in the disk running out
of space when the inputs are localized. To ensure the disk has enough
space, any task which uses the Directory input needs to have its CWL
modified to include the following:

```yaml
requirements:
    - class: ResourceRequirement
      tmpdirMin: 12345
```

The value for tmpdirMin must exceed the size of the directory with
some headroom for any other usage the task needs.

Also, value must refer to a bucket unless reference image disk is
attached. See [point #1](1-file-locations-must-refer-to-buckets)

Automated: No. Probably can't reasonably be. Reference image disks may
be the best approach for handling this.
