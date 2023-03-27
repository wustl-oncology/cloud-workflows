#!/bin/bash

SRC_DIR=$(dirname "$0")

function show_help {
    echo "usage: sh $0 --gs-path <GS_PATH> --wf-id <WORKFLOW_ID>"
    echo "arguments:"
    echo "    -h, --help     prints this block"
    echo "    -a, --analyze  performs analysis of monitoring logs"
    echo "    --gs-path      path to dir that contains target folder. example: 'BUCKET_NAME/<folder_name>/...'"
    echo "    --wf-id        worflow id. example 'b62f29-124d...'"
    echo ""
}


function die {
    printf '%s\n' "$1" >&2 && exit 1
}

# we only want peaks and they are recorded at every other column
function analysis_summary {

    line_count=$(wc -l < ./MonitoringLogs/summary.log)
    
    if [[ $line_count -eq 0 ]]; then
        head -1 ./MonitoringLogs/logs/$1 | awk -F "\t" '{print "Task", $1, $3, $5, $7, $9, $11, $13}' > ./MonitoringLogs/summary.log
    fi

    line_count=$(wc -l < ./MonitoringLogs/logs/$1)

    # monitoring logs could have only the headers or nothing at all
    if [[ $line_count -le 1 ]]; then
        echo -e "$1 0 0 0 0 0 0 0" >>./MonitoringLogs/summary.log
    else
        tail -1 ./MonitoringLogs/logs/$1 | awk -v name=$1 -F "\t" '{print name, $1, $3, $5, $7, $9, $11, $13}' >>./MonitoringLogs/summary.log
    fi
}

while test $# -gt 0; do
   case $1 in
        -h|--help)
            show_help
            exit
            ;;
        --wf-id*)
            if [ ! "$2" ]; then
                die 'ERROR: "--wf-id" requires a non-empty argument'
            else
                 WF_ID=$2
                 shift
            fi
            ;;
        --gs-path*)
            if [ ! "$2" ]; then
                die 'ERROR: "--gs-path" requires a non-empty argument'
            else
                GS_PATH=$2
                shift
            fi
            ;;
        *)
            break
            ;;
    esac
    shift
done

if [ -z $WF_ID ]; then
    die 'ERROR: "--wf-id" must be set'
fi
if [ -z $GS_PATH ]; then
    die 'ERROR: "--gs-path" must be set.'
fi

echo "Searching for all 'monitoring.log' files ... "

gsutil ls gs://$GS_PATH/$WF_ID/**/monitoring.log >paths

mkdir ./MonitoringLogs
mkdir ./MonitoringLogs/logs
mkdir ./MonitoringLogs/full_path
touch ./MonitoringLogs/summary.log


echo "Copying over all monitoring logs and creating 'summary.log' ... "
echo " ---  This will take about 20 min --- "

while read line; do
    # to achieve unique names for all logs, each log is given the names of the last 5 folders
    name=$(echo $line | perl -F/ -wane 'print join("-", $F[-5],$F[-4],$F[-3],$F[-2],$F[-1])')
    gsutil cp $line ./MonitoringLogs/logs/$name
    echo $line >./MonitoringLogs/full_path/$name.full_path
    analysis_summary $name
done < paths

rm paths
