# Historical Progression of the Repo

I'm going to very quickly walk through the high level decisions that
guided the repo and hopefully that may explain any idiosyncracies or
cruft leftover.

## Version 1: Central Server, Terraform+Jinja

The first iteration of the repo was aiming for the following setup:
- a single central server
- that could host many labs
- and bill against their various projects
Basically a custom Terra setup. We could have, instead of trying to
force a custom setup to work, forced our workflows to function with
Terra. The main reason we chose not to do this was that it made
integration with GMS much much more difficult, mostly because [the API
for Terra, Firecloud](https://api.firecloud.org/), assumes behavior
won't deviate from Terra in really any way. It's not designed to be
used by others but they made it available I guess because why not?

The very first pass of this iteration was cribbing off of [the Hall Lab
Cromwell deployment
setup](https://github.com/hall-lab/cromwell-deployment). The remains
of this can be seen at `./central-server/jinja` which still owns the
compute VM itself.

As work progressed, for personal familiarity reasons, I used Terraform
to manage extra resources instead of dealing with Jinja
deployments. These resources can be seen in
`./central-server/terraform` along with documentation on how to
interact with it.

**IMPORTANT NOTE**: The entire central-server directory is, at this
point, completely unused. It's kept around mostly for reference and
because we had tentatively planned on bringing back up the
central-server approach when things were ironed out.

### Problems Encountered

#### Inefficient Database

Cromwell's database is hugely inefficient and having a single central
server, with a single database instance, was not enough for even a
single lab to do a single very large run. Irenaeus with the Bolton Lab
tried running through a relatively-large (though by no means the
largest) archerdx workflow and consistently ran into timeout issues
with the database.

There are two options for resolving this issue. The easy one is,
simply do not use a database. This removes the ability to cache calls
which is crippling for _troubleshooting_ workflows but I believe it
isn't present in our current GMS setup anyway? I think the local
cromwell database generated for each run gets wiped at the end? Either
way, with Google's increased reliability and properly configured
retries within the workflow, this is not really a requirement but a
nice to have.

The harder option is to do a distributed setup of Cromwell
servers. This setup is "detailed"
[here](https://cromwell.readthedocs.io/en/stable/Scaling/), though I'm
using the word detailed very lightly. The jist of it is that,
depending on the .conf file, separate Cromwell instances can be given
separate jobs, and this can be used to spread the load amongst them. I
don't know how to set this up around the database in a way that avoids
getting stuck behind locks, but it's apparently doable.

#### Security Issues

There was no built-in way to assure that requests made to this central
server were associated with the correct labs. Cromwell assumes anyone
that can hit the endpoints is allowed to use any backend, which is not
the case we were aiming for.

The easiest solutions to this would be to not do a central server for
the entire organization, but let each lab optionally run their own
central server. This avoids the whole "Cromwell can't differentiate"
part, but doesn't solve the fact that anyone with access to those
endpoints can submit workflows and thus create resources and spend
money on the account. The solution for that is a Google Cloud product
called [Identity-Aware
Proxy](https://cloud.google.com/iap/docs/concepts-overview).  What
this does, in short, is enforces that requests sent to the Cromwell
server are only allowed for people logged in to gcloud with proper
permissions. I haven't attempted implementing this but conceptually
it's exactly what's needed here. Each lab would have their own server
(if they want it), which enforces that only people allowed to submit
workflows are allowed.

#### Cost Issues

This is essentially just a combination "Inefficient Database" and
"Security Issues". The database grows in size at a much faster rate
than you'd expect, especially in my case where I was consistently
submitting small slightly-different workflows which couldn't be
consolidated. Running a central server and a central database means
the costs for those resources are assigned to the maintainers, not the
requesting parties.

The database size problem is _lessened_ in real use but not
avoided. The cost assignment problem is resolved with the resolution
to the above security issues.

### Pivoting Away

The problems detailed above aren't completely damning and we could
have continued down the central server path. In my opinion,
fragmenting the central server to be per lab brings us close enough
that other approaches work better. Because we would be enabling labs
to spin up their own instances to begin with, there are cases where
they would not want to have an always-on central server and instead
bring them up and down as needed, and submit workflows as
needed. This approach also fits in neatly with GMS integrations, where
each submitted workflow creates its own managing instance. This is
what happens on the cluster, with docker containers.

I believe that labs wanting to adopt this approach would open with the
one-off attempts first before committing to an always-on server
anyway, so it makes sense to punt on this approach and focus on the
more direct solution.


## Version 2: Manual Workflows

Our second pass is a stripped down version -- this time just a single
Cromwell instance. Most of the complication in this setup is in
helpers and resource creation to ease things on the
user. `resources.sh` creates all the required resources, meaning both
GCP resources and required files like workflow options and cromwell
configuration. `user_permissions.sh` can be used to grant permissions
to other users to create their own workflows. `start.sh` makes the
instance and `helpers.sh` is provided within the instance for easier
use. Everything is meant to be very straightforward to do from the
command-line, so long as the user actually knows it's there.

Most of the focus has been on this approach because it's the easiest
to test and troubleshoot with, so we've used it the most.

The instance created to run Cromwell clones the analysis-wdls repo,
but otherwise users are expected to shuffle required files around as
needed. If they used the cloudize-workflow.py path, this mostly just
means copying their inputs yaml to the instance and submitting against
the already-cloned WDL repo.

For gotchas on how this works, you're mostly going to be digging
through gotchas on Cromwell and GCP in general since this is a thin
glue between them. Everything else is pretty explicit in the code
which has been kept intentionally minimal.


### Problems Encountered

Really nothing special. The main issues are ones of maintenance. If
you use the same instance for too many runs then you may run into an
out of space error for the boot disk. This is easily resolved by
either restarting the instance (after making sure to persist any files
you want to keep) or by proactively assigning sufficient disk space on
start with ``--boot-disk-size XXGB` for whatever XX size you
want. Another issue is if you forget to shut down the instance you'll
be billed for that time.

If you want to stop being billed without losing files, you can `stop`
the instance without deleting it. If you want to delete the instance
and keep the files you'll need to look into disk persistence options.

## Version 3: GMS

Similar to manual workflows, the intention is to create a compute
instance to run Cromwell. The GMS version runs without human
interaction, as its meant to be an integration point for GMS to
leverage cloud resources. It'll create the instance, expecting all
required files to be provided to it, then run the workflow and persist
its artifacts. The most important piece here is that the code in GMS
which uses this approach is located in [this Genome
file](https://github.com/genome/genome/blob/master/lib/perl/Genome/Model/CwlPipeline/Command/Run.pm). Instructions
on how to interact with this are [on the genome
wiki](https://github.com/genome/genome/wiki/Running-on-Google-Cloud).


This approach has a very similar `start.sh` and `server_startup.py` to
the `./manual-workflows` approach. The files aren't deduplicated
because it would complicate things, especially the `server_startup.py`
which is just sent to the GCP instance as text via a metadata tag.

An alternative approach to GMS that was considered -- make the GMS
process run the Cromwell server with `cromwell run` and just run the
instances on GCP. We chose not to do this because it leaves the
instance vulnerable to compute1 failures. The Cromwell server
shuffled off to GCP means that compute1 failures don't break the run,
they just break the GMS build. We haven't implemented stronger
recovery, but the requisite files are available and theoretically
there could be a recovery process implemented.

## Scripts

Any program or script used by multiple approaches, or by the user
regardless of te approach, are in the scripts
directory. workflow_options.jsons were, I think, only used for central server

## Big Things We Haven't Addressed

The main "big thing" we haven't addressed that we'd like to address is
reference disks. Google will let you mount a pre-populated disk image
to compute instances. Cromwell leverages this feature to enable what
they call reference disks, disk images pre-populated with non-changing
files to be used as reference. The actual reference fasta could go
here, but the bigger win is large directories like VEP cache or star
fusion which are very large directories and, without reference disks,
require downloading the full contents of the files into the VM
regardless of use.

We also haven't addressed issues of optimization, or finding out what
the upper limit on stress testing is. I'm not sure if the workflow
Irenaeus was pushing through would go through without the backing
database, or how close to that size we could get.

We also have not bothered trying to drive adoption yet. As of this
writing, we were just getting Malachi Griffith able to run a real
Immuno workflow through, and Sridar able to run large somatic_wgs
workflows.

# Billing

Initially we wanted to get "real billing numbers". What this meant for
us initially was trying to pull billing data from BigQuery and
filtering down based on tags for each workflow. Because of limitations
within Google Cloud -- billing happens on a separate project entirely,
only one for the organization, which users would need to be granted
access to -- we weren't able to provide this in a simple way. Instead
we chose to estimate the numbers, through the `estimate_billing.py`
script. This leverages the Cromwell metadata, and values pulled from
the GCP price pages. Something to improve would be automatically
pulling values programmatically, instead of hard-coding.

This estimate varies above or below the real value based on:
- difference in cost at run-time (GCP costs vary per day)
- error in event timestamps vs real runtime of the instance
- CPU platform _may_ change though I think N1 is what happens?
- floating point errors are unavoidable in python
