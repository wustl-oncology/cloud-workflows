#i/bin/bash

SRC_DIR=$(dirname "$0")

function show_help {
    echo "usage: sh $0 --gs-path <GS_PATH> --out-dir <OUT_DIR>"
    echo "arguments:"
    echo "    --wf-id      worflow id"
    echo "    --gs-path    path to dir that contains target folder. example: 'gs://\$BUCKET_NAME/...'"
    echo "    --out-dir    output dir. DEFAULT: './AllMonitoringFiles/'" 
    echo "    --py-path    path to gather_monitoring.py. DEFAULT: '/shared/gather_monitoring.py'"
    echo ""
}


function die {
    printf '%s\n' "$1" >&2 && exit 1
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
        --out-dir*)
            if [ ! "$2" ]; then
                OUT_DIR="./AllMonitoringFiles/"
            else
                OUT_DIR=$2
                shift
            fi
            ;;
        --py-path*)
            if [ ! "$2" ]; then
                PY_PATH="/shared/gather_monitoring.py"
            else
                PY_PATH=$2
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
    die 'ERROR: "--wf-if" must be set'
fi
if [ -z $GS_PATH ]; then
    die 'ERROR: "--gs-path" must be set.'
fi
if [ -z $OUT_DIR ]; then
    OUT_DIR="./AllMonitoringFiles/" 
fi

TARGET="monitor.log"

# where all monitoring files will be stored
mkdir $OUT_DIR

# download workflow locally
gsutil -m cp -r "$GS_PATH/$WF_ID" .

# iterate through workflow and output files
python3 $PY_PATH $WF_ID $TARGET $OUT_DIR

# delete local workflow folder
rm -r $WF_ID
