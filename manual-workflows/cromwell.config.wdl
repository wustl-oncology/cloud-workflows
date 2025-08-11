include required(classpath("application"))
include "akka-http-version"
 
backend {
  default = "LSF"
  providers {
    LSF {
      actor-factory = "cromwell.backend.impl.sfs.config.ConfigBackendLifecycleActorFactory"
      config {
	exit-code-timeout-seconds = 600
        runtime-attributes = """
        Int cpu = 1
        Int memory_kb = 4096000
        Int memory_mb = 4096
        String? docker
        """
 
        submit = """
        bsub \
        -J ${job_name} \
        -cwd ${cwd} \
        -G compute-oncology \
  -g /path/to/your/job_group \
        -o /dev/null \
        -e ${err} \
	-q general \
        -M ${memory_kb} \
        -n ${cpu} \
        -R "select[mem>${memory_mb} && tmp>10G] span[hosts=1] rusage[mem=${memory_mb}:tmp=10G]" \
        /bin/bash ${script}
        """
 
        submit-docker = """
        LSF_DOCKER_VOLUMES="${cwd}:${docker_cwd} $LSF_DOCKER_VOLUMES" \
	LSF_DOCKER_PRESERVE_ENVIRONMENT=false \
        bsub \
        -J ${job_name} \
        -cwd ${cwd} \
        -G compute-oncology \
  -g /path/to/your/job_group \
        -o /dev/null \
        -e ${err} \
        -a "docker(${docker})" \
        -q general \
        -M ${memory_kb} \
        -n ${cpu} \
        -R "select[mem>${memory_mb} && tmp>10G] span[hosts=1] rusage[mem=${memory_mb}:tmp=10G]" \
        /bin/bash ${docker_script}
        """
 
        kill = "bkill ${job_id}"
        docker-kill = "bkill ${job_id}"
        check-alive = "bjobs -noheader -o stat ${job_id} | /bin/grep 'PEND\\|RUN'"
        job-id-regex = "Job <(\\d+)>.*"
      }
    }
  }
}

akka.http
{
  parsing
  {
    max-chunk-size = 2m
  }
}

