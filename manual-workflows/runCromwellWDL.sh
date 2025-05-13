#!/bin/bash

# EXAMPLE COMMAND:
#bsub -q general -G compute-obigriffith -M 22000000 -R 'select[mem>22000] rusage[mem=22000]' -oo /storage1/fs1/obigriffith/Active/canine/canine_embryonal_rhabdomyosarcoma/exome_somatic/Annie/CER_Annie_exome.stdout -eo /storage1/fs1/obigriffith/Active/canine/canine_embryonal_rhabdomyosarcoma/exome_somatic/Annie/CER_Annie_exome.stderr -a 'docker(ghcr.io/genome/genome_perl_environment:compute1-58)' /bin/bash /storage1/fs1/obigriffith/Active/Common/git/archive/misc/runCromwellWDL.sh --cromwell_config /storage1/fs1/obigriffith/Active/canine/canine_embryonal_rhabdomyosarcoma/exome_somatic/cromwell.config.wdl --sample Annie --wdl /storage1/fs1/obigriffith/Active/canine/canine_embryonal_rhabdomyosarcoma/exome_somatic/analysis-wdls/definitions/somatic_exome_nonhuman.wdl --imports /storage1/fs1/obigriffith/Active/canine/canine_embryonal_rhabdomyosarcoma/exome_somatic/analysis-wdls/workflows.zip --yaml /storage1/fs1/obigriffith/Active/canine/canine_embryonal_rhabdomyosarcoma/exome_somatic/Annie/somatic_exome.yml --results /storage1/fs1/obigriffith/Active/canine/canine_embryonal_rhabdomyosarcoma/exome_somatic/Annie/final_somatic_results --temp /scratch1/fs1/obigriffith/obi-tmp/somatic_exome_nonhuman/Annie --cromwell_jar /storage1/fs1/mgriffit/Active/griffithlab/common/cromwell-jars/cromwell-71.jar --cromwell_server_mem 10g --cromwell_submit_mem 10g

#NOTE. When specifying memory for the two Java commands below (which run in parallel) make sure they add up to LESS than what is requested for the parent LSF job.  
function usage
{
    echo ""
    echo "usage: runCromwellCWL.sh -q <queue> -m <memory> -a <docker image> -h"
    echo ""
    echo "  -g | --cromwell_config       Path to cromwell config file"
    echo "  -s | --sample                Sample name"
    echo "  -w | --wdl                   Path to WDL pipeline file"
    echo "  -i | --imports               Path to ZIP archive of all WDL files"
    echo "  -y | --yaml                  Path to input YAML file"
    echo "  -r | --results               Path to final results dir where named outputs of the pipeline will be placed"
    echo "  -t | --temp                  Path to temp dir where intermediate pipeline files will be stored (e.g., scratch dir)"
    echo "  -j | --cromwell_jar          Path to cromwell jar file (default: /storage1/fs1/mgriffit/Active/common/cromwell-jars/cromwell-51.jar)"
    echo "  -a | --cromwell_server_mem   Memory (GB) used for the Java process for Cromwell Server command"
    echo "  -b | --cromwell_submit_mem   Memory (GB) used for the Java process for Cromwell Submit command"
    echo "  -n | --clean                 Whether to clean up or not (default: YES - things will be cleaned up unless you say --clean NO)"
    echo "  -h | --help                  Show this message"
    echo ""
    exit 1
}

if [[ $1 == "" ]];then
    usage
    exit;
fi

while [[ "$1" != "" ]]; do
    case $1 in
         -g | --cromwell_config )        shift
                                         cromwell_config=$1
				         ;;
         -s | --sample )                 shift
                                         sample=$1
                                         ;;
        -w | --wdl )                     shift
                                         wdl=$1
                                         ;; 
        -i | --imports )                 shift
                                         imports=$1
                                         ;; 
        -y | --yaml )                    shift
                                         yaml=$1
                                         ;;
        -t | --temp )                    shift
                                         temp=$1
                                         ;;
        -r | --results )                 shift
                                         results=$1
                                         ;;
        -j | --cromwell_jar )            shift
                                         cromwell_jar=$1
				         ;;
        -a | --cromwell_server_mem )     shift
                                         cromwell_server_mem=$1
				         ;;
        -b | --cromwell_submit_mem )     shift
                                         cromwell_submit_mem=$1
				         ;;
        -n | --clean )                   shift
                                         clean=$1
				         ;;
        -h | --help )                    usage
                                         exit
                                         ;;
        * )                              usage
                                         exit 1
    esac
    shift
done

if [[ $cromwell_config == "" ]];then
    echo "--cromwell_config must be specified"
    exit;
fi
if [[ $sample == "" ]];then
    echo "--sample must be specified"
    exit;
fi
if [[ $wdl == "" ]];then
    echo "--wdl must be specified"
    exit;
fi
if [[ $imports == "" ]];then
    echo "--imports must be specified"
    exit;
fi
if [[ $yaml == "" ]];then
    echo "--yaml must be specified"
    exit;
fi
if [[ $results == "" ]];then
    echo "--results must be specified"
    exit;
fi
if [[ $temp == "" ]];then
    echo "--temp must be specified"
    exit;
fi
if [[ $cromwell_jar = "" ]];then
    echo "using cromwell jar: /storage1/fs1/mgriffit/Active/griffithlab/common/cromwell-jars/cromwell-71.jar"
    cromwell_jar=/storage1/fs1/mgriffit/Active/griffithlab/common/cromwell-jars/cromwell-71.jar;
fi
if [[ $cromwell_server_mem == "" ]];then
    echo "--cromwell_server_mem (in GB) must be specified (e.g. --cromwell_server_mem=10g)"
    exit;
fi
if [[ $cromwell_submit_mem == "" ]];then
    echo "--cromwell_submit_mem (in GB) must be specified (e.g. --cromwell_submit_mem=10g)"
    exit;
fi
if [[ $clean == "" ]];then
    echo "Temp files will be cleaned up"
    clean="YES";
fi

###########################################################################################
############################# pre-setup ###################################################
###########################################################################################

# get base name of the CWL pipeline being run
CWL_BASE=$(basename $wdl)
JAVA_MEM_BASE="-Xmx"
CROMWELL_SERVER_MEM_STRING="$JAVA_MEM_BASE$cromwell_server_mem"
CROMWELL_SUBMIT_MEM_STRING="$JAVA_MEM_BASE$cromwell_submit_mem"

echo "Java memory request for Server command: " $CROMWELL_SERVER_MEM_STRING
echo "Java memory request for Submit command: " $CROMWELL_SUBMIT_MEM_STRING

###########################################################################################
###################start up the cromwell server/start job #################################
###########################################################################################

#create temp dir where cromwell will be run
if mkdir -p "$temp"; then
    echo "Successfully created: $temp"
else
    echo "Failed to create: $temp"
    exit 1
fi

# Attempt to change to the target directory
if cd "$temp"; then
    echo "Successfully changed to directory: $temp"
else
    echo "Failed to change directory to: $temp"
    exit 1
fi

# start cromwell server and give it time to setup
echo /usr/bin/java $CROMWELL_SERVER_MEM_STRING -Dconfig.file=$cromwell_config -jar $cromwell_jar server &
/usr/bin/java $CROMWELL_SERVER_MEM_STRING -Dconfig.file=$cromwell_config -jar $cromwell_jar server &
echo sleep 60
sleep 60

# create a yaml to label the cromwell job
echo -e "{\n\"model\":\"$sample\"\n}" >| $sample.label

# submit the cromwell job
echo /usr/bin/java $CROMWELL_SUBMIT_MEM_STRING -Dconfig.file=$cromwell_config -jar $cromwell_jar submit -h http://localhost:8000 -l $sample.label -t wdl -i $yaml -p $imports $wdl
/usr/bin/java $CROMWELL_SUBMIT_MEM_STRING -Dconfig.file=$cromwell_config -jar $cromwell_jar submit -h http://localhost:8000 -l $sample.label -t wdl -i $yaml -p $imports $wdl

############################################################################################
################# query the cromwell server for status #####################################
############################################################################################

# infinity loop to check job status
x=0
while [ $x -le 1 ]
do
    curl -SL http://localhost:8000/api/workflows/v1/query?label=model:$sample >| $sample.status
    sleep 600
    if cat $sample.status | python3 -m json.tool | grep -q "Succeeded"; then
        break
    elif cat $sample.status | python3 -m json.tool | grep -q "Failed"; then
        exit 1
    else
        continue
    fi
done

############################################################################################
################ grab the final outputs and put them in the correct place ##################
############################################################################################

# with the cromwell job complete get the name and id so we can query and clean up the outputs
CROMWELL_ID="$(cat $sample.status | python3 -m json.tool | grep "\"id\":" | sed 's@.*\"id\": \"\(.*\)\".*@\1@')"
CROMWELL_NAME="$(cat $sample.status | python3 -m json.tool | grep "\"name\":" | sed 's@.*\"name\": \"\(.*\)\".*@\1@')"

# when done continue and grab the outputs
echo curl -SL http://localhost:8000/api/workflows/v1/$CROMWELL_ID/outputs >| $sample.output
curl -SL http://localhost:8000/api/workflows/v1/$CROMWELL_ID/outputs >| $sample.output

# loop through the output and put everything in the right place
#cat $sample.output | python3 -m json.tool | grep $temp | sed 's@.*\"location\": \"\(.*\)\".*@\1@' >| $sample.final_results
cat $sample.output | python3 -m json.tool | grep $temp | sed -n 's/^[^"]*"\([^"]*\)".*"\([^"]*\)".*/\2/p' >| $sample.final_results

echo "Copying results files defined in the WDL to user specified location: " $results

for line in $(cat $sample.final_results)
do
    echo cp -r $line $results
    cp -r $line $results
done

#############################################################################################
################ with everything now done clean up after yourself ###########################
#############################################################################################

if [ $clean == "NO" ]; then
    echo "Leaving full cromwell-executions dir and temp files in place"
else
    echo "Removing cromwell-executions dir"
    echo rm -rf $temp/cromwell-executions/$CROMWELL_NAME/$CROMWELL_ID
    rm -rf $temp/cromwell-executions/$CROMWELL_NAME/$CROMWELL_ID

    echo rm -f $temp/$sample.final_results
    rm -f $temp/$sample.final_results

    echo rm -f $temp/$sample.output
    rm -f $temp/$sample.output

    echo rm -f $temp/$sample.status
    rm -f $temp/$sample.status

    echo rm -f $temp/$sample.label
    rm -f $temp/$sample.label
fi

