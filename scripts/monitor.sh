#! /bin/bash

printf "Memory_Percent\tMemory_Percent_Peak\tMemory_GB\tMemory_GB_Peak\tDisk_Percent\tDisk_G\tCPU_Percent\n"
DELAY=5
MEMORY_P_PEAK=0
MEMORY_G_PEAK=0

while : 
do
  
  #Retrieve current memory usage as percent and GB
  MEMORY_P=$(free -m | awk 'NR==2{printf "%.2f", $3*100/$2 }')
  MEMORY_G=$(free -m | awk 'NR==2{printf "%.2f", $3/1024 }')
 
  #Check for and store peak memory usage observed thus far
  MEMORY_P_PEAK=$(echo $MEMORY_P $MEMORY_P_PEAK | awk '{if ($1 > $2) print $1; else print $2}')
  MEMORY_G_PEAK=$(echo $MEMORY_G $MEMORY_G_PEAK | awk '{if ($1 > $2) print $1; else print $2}')

  #Retrieve current disk usage as percent and GB (assumes disk used by cromwell is mounted as '/mnt/disks/local-disk')
  DISK_P=$(df -h | awk '$NF=="/"{printf "%s", $5}' | tr -d "%" | awk '{printf "%.2f", $1}')
  DISK_G=$(df -h | awk '$NF=="/"{printf "%s", $4}' | tr -d "BKMGTP")

  #Check for and store peak disk usage

  #Retrieve overall current CPU usage
  CPU_P=$(top -bn1 | grep load | awk '{printf "%.2f", $(NF-2)}')

  #Print out the data line
  echo -e "$MEMORY_P\t$MEMORY_P_PEAK\t$MEMORY_G\t$MEMORY_G_PEAK\t$DISK_P\t$DISK_G\t$CPU_P"

  sleep $DELAY

done




