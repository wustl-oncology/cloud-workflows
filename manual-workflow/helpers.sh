export CROMWELL_JAR=/opt/cromwell/jar/cromwell.jar
export CROMWELL_CONF=/opt/cromwell/config/cromwell.conf
export ANALYSIS_WDLS=/shared/analysis-wdls

function cat-startup-logs () {
    cat /var/log/syslog |  grep 'startup-script' | sed 's/ GCEMetadataScripts.*startup-script//'
}
