# Why do workflows have to be in WDL?

We ran into issues with Cromwell not sizing up disk space on worker
instances. If you want to wrestle with that or if you think your data
won't exceed the default, go for it.


# How do I check the cost of a workflow run?

TODO(john): this requires some BigQuery fiddling. Talk to Eric Suiter.
TODO(john): look into DataBiosphere's `workflow_cost_estimator` : https://github.com/DataBiosphere/featured-notebooks/blob/master/notebooks/workflow_cost_estimator/main.py


# How do I resolve `write error: No space left on device`

In the WDL for the task that's failing, the runtime block needs a
higher value for the line
```
    disks: "local-disk ~{space_needed_gb} SSD"
```

Make sure that the value of `space_needed_gb` is enough for all the
input files _and_ all the generated output files.

A special case of this issue happens when /dev/stdin or /dev/stdout
pipes are overloaded.


# How do I bring the cost of a task down?

The easiest thing is to make sure it's running on a preemptible
compute instance. See below for details.

After that decision, the main thing you can do is make sure proper
resources are requested. Costs in GCP will be determined by number of
CPU cores, amount of memory, and amount of disk space.

The cheapest option will be to set these to minimum that won't cause a
crash. Depending on the tool you can scale any of the three for
whatever gives most performance. The "best" tuning is the one that
uses everything it's provided, minimizing idle time of any
resource.


# My workflow on the cloud ran slower than on the cluster?

There's a short and a long version answer for this.

The short version is that the cloud has overhead involved and things
will take extra time for that to be handled. If wall-clock time isn't
really a priority then this is fine. If it is, see the long answer below.


The long version is that your workflow should be changed to leverage
the benefits that the cloud does provide, and minimize its weak
points. That's likely been done for the cluster, which is likely why
it runs faster there.

Certain operations, like file localization, are much faster in the
cluster. Some operations are _only relevant_ to the cluster and just
introduce overhead in the cloud, things like moving or renaming
files. Changes that remove tasks that aren't beneficial, and reduce
the number of file transfers like merging tasks that share a docker
container can bring this overhead down.

That's minimizing the weak points. The main strength of the cloud, in
our case, is that you aren't limited in what resources you can
request, except by price. If a task scales with memory, or cores, or
disk space, bring those numbers up. The task will run faster, and if
there were resources that were just idling it'll probably be overall
cheaper. This can be an effort-intensive process, so it's best to
focus on doing this only for the tasks that give high returns. Ones
that run frequently, run long, and can benefit from the resources.


# What's a preemptible instance?

Preemptible instances are a special type of compute instance with two
important attributes:
1. Google can kill them without notice, at any time
2. They are priced at a 60-91% discount

Because we use a workflow runner that handles retrying preemptible
machines, they're _likely_ to be a large cost savings with small
performance costs.

Compute Engine *always* stops these instances after 24 hours. For
individual tasks that you expect to run this long, disable preemptiple
instance for that task.

For full details on how preemptible compute instances work, see [the
Google docs](https://cloud.google.com/compute/docs/instances/preemptible)


To enable preemptible instances for an individual task, set the
following runtime option in the task's WDL definition

```
runtime {
  preemptible: 1
}
```

[Source](https://cromwell.readthedocs.io/en/stable/RuntimeAttributes/#preemptible)


To enable preemptible instances for all tasks in a workflow, set the
following option in your workflow_options.json

```
{
    "default_runtime_attributes": { "preemptible": 1 }
}
```

[Source](https://cromwell.readthedocs.io/en/stable/wf_options/Overview/#setting-default-runtime-attributes)


To _disable_ preemptible instances in either case, apply that case
with a value of `0` instead of `1`.


# My workflow is failing and the Cromwell logs show `'IOCommand.success '()'' is over 5 minutes.`

This was seen in the following errors, details redacted in `<arrows>`

(IO-<uuid>) 'IOCommand.success '()'' is over 5 minutes. It was running for <n> seconds. IO command description: 'GcsBatchCopyCommand source <gcspath> destination <gcspath> setUserProject 'false' rewriteToken 'None''


The following description applies specifically to
`'GcsBatchCopyCommand` occurrence. Update this section with followup
if this happens with another category.

This error exhibited some strange behavior. The workflow failed, and
the server stopped responding to requests, but the _service_ that runs
it had not crashed. Logs were riddled with several errors, including
this one, almost all regarding a timeout of some sort.

The cause of this was a workflow options setting.
`final_workflow_outputs_dir`, when provided a GCS path, copies all
outputs of the workflow to that directory. When output files are large
enough, this process takes so long that it times out and causes the
above error. Simply leaving that out resolved the issue.

[Cromwell docs on Output Copying](https://cromwell.readthedocs.io/en/stable/wf_options/Overview/#output-copying)


# My workflow is failing and the Cromwell logs show `WorkflowStoreHeartbeatWriteActor Failed to properly process data`

TODO(john) I... don't have an answer for this one yet. Stay tuned.


# Can I improve my upload/download speed to the GCP bucket?

When uploading input files to GCS form a bsub job, add to your
`rusage` the value `internet2_upload_mbps=500`. This value maxes out
at 5000 across the entire organization. This removes an overhead cap
and should help you get faster uploads.

The same applies to downloads with `internet2_download_mbps`


# How do I get call caching in the cloud?

That involves extra infrastructure, which means extra setup complexity
and more importantly extra costs.

Setting up call caching requires a persistent database. That database
is going to have a cost for storage, and that cost is just going to
increase as the amount of storage required increases. For most use
cases we believe it won't be necessary, and haven't implemented it
yet. That said, if it's needed just ping us and modifications can be
made to allow easily setting up a database for caching.

TODO(john): implement optional database for caching, gms/resources.sh
and manual-workflows/resources.sh
