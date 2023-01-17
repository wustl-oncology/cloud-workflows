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

function analysis_summary {
    cp ./AllMonitoringLogs/$1 ./AllMonitoringLogs/summary/
    head -1 ./AllMonitoringLogs/$1 | awk -F "\t" '{print $1, $3, $5, $7, $9, $11, $13}' > ./AllMonitoringLogs/summary/$1
    tail -1 ./AllMonitoringLogs/$1 | awk -F "\t" '{print $1, $3, $5, $7, $9, $11, $13}' >>./AllMonitoringLogs/summary/$1
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

mkdir ./AllMonitoringLogs
mkdir ./AllMonitoringLogs/full_path
mkdir ./AllMonitoringLogs/summary

echo "Copying over files ... "

while read line; do
    name=$(echo $line | perl -F/ -wane 'print join("-", $F[-5],$F[-4],$F[-3],$F[-2],$F[-1])')
    gsutil cp $line ./AllMonitoringLogs/$name
    echo $line >./AllMonitoringLogs/full_path/$name.full_path
    analysis_summary $name
done < paths

rm paths
