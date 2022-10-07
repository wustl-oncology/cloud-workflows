#! /bin/bash

printf "Seconds\tMemory_Percent\tMemory_Percent_Peak\tMemory_GB\tMemory_GB_Peak\tDisk_Percent\tDisk_Percent_Peak\tDisk_GB\tDisk_GB_Peak\tCPU_Load_Percent\tCPU_Load_Percent_Peak\tCPU_Usage_Percent\tCPU_Usage_Percent_Peak\n"
DELAY=60
MEMORY_P_PEAK=0
MEMORY_G_PEAK=0
DISK_P_PEAK=0
DISK_G_PEAK=0
CPU_LOAD_P_PEAK=0
CPU_USAGE_P_PEAK=0
i=0

while : 
do
  
  #Retrieve current memory usage as percent and GB
  MEMORY_P=$(free -m | awk 'NR==2{printf "%.2f", $3*100/$2 }')
  MEMORY_G=$(free -m | awk 'NR==2{printf "%.2f", $3/1024 }')
 
  #Check for and store peak memory usage observed thus far
  MEMORY_P_PEAK=$(echo $MEMORY_P $MEMORY_P_PEAK | awk '{if ($1 > $2) print $1; else print $2}')
  MEMORY_G_PEAK=$(echo $MEMORY_G $MEMORY_G_PEAK | awk '{if ($1 > $2) print $1; else print $2}')

  #Retrieve current disk usage as percent and GB (assumes disk used by cromwell is mounted as '/mnt/disks/local-disk')
  DISK_P=$(df -h | awk '$NF=="/mnt/disks/local-disk"{printf "%s", $5}' | tr -d "%" | awk '{printf "%.2f", $1}')
  DISK_G=$(df -B 1K | awk '$NF=="/mnt/disks/local-disk"{printf "%.2f", $4/1024/1024}')

  #Check for and store peak disk usage
  DISK_P_PEAK=$(echo $DISK_P $DISK_P_PEAK | awk '{if ($1 > $2) print $1; else print $2}')
  DISK_G_PEAK=$(echo $DISK_G $DISK_G_PEAK | awk '{if ($1 > $2) print $1; else print $2}')

  #Retrieve current CPU load (based on last 5 minutes value from top)
  CPU_LOAD_P=$(top -bn2 | head -n 5 | grep load | awk '{printf "%.2f", $(NF-2)}')

  #Check for and store peak CPU load
  CPU_LOAD_P_PEAK=$(echo $CPU_LOAD_P $CPU_LOAD_P_PEAK | awk '{if ($1 > $2) print $1; else print $2}')

  #Retrieve current CPU usage (based on top)
  CPU_USAGE_P=$(top -b -d1 -n2 | head -n 5 | grep -i "Cpu(s)" | cut -d ',' -f 1 | cut -d ':' -f 2 | tr -d " us")

  #Check for and store peak CPU load
  CPU_USAGE_P_PEAK=$(echo $CPU_USAGE_P $CPU_USAGE_P_PEAK | awk '{if ($1 > $2) print $1; else print $2}')

  #Set any empty variables to 'NA' for readability (the "peak" variable should never be empty - so not needed there)
  if test -z "$MEMORY_P"; then MEMORY_P="NA"; fi
  if test -z "$MEMORY_G"; then MEMORY_G="NA"; fi
  if test -z "$DISK_P"; then DISK_P="NA"; fi
  if test -z "$DISK_G"; then DISK_G="NA"; fi
  if test -z "$CPU_LOAD_P"; then CPU_LOAD_P="NA"; fi
  if test -z "$CPU_USAGE_P"; then CPU_USAGE_P="NA"; fi

  #Print out the data line
  echo -e "$i\t$MEMORY_P\t$MEMORY_P_PEAK\t$MEMORY_G\t$MEMORY_G_PEAK\t$DISK_P\t$DISK_P_PEAK\t$DISK_G\t$DISK_G_PEAK\t$CPU_LOAD_P\t$CPU_LOAD_P_PEAK\t$CPU_USAGE_P\t$CPU_USAGE_P_PEAK"

  sleep $DELAY
  let "i+=$DELAY"

done

