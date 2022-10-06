#! /bin/bash

printf "Seconds\tMemory_Percent\tMemory_Percent_Peak\tMemory_GB\tMemory_GB_Peak\tDisk_Percent\tDisk_Percent_Peak\tDisk_GB\tDisk_GB_Peak\tCPU_Percent\tCPU_Percent_Peak\n"
DELAY=60
MEMORY_P_PEAK=0
MEMORY_G_PEAK=0
DISK_P_PEAK=0
DISK_G_PEAK=0
CPU_P_PEAK=0
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
  DISK_P=$(df -h | awk '$NF=="/"{printf "%s", $5}' | tr -d "%" | awk '{printf "%.2f", $1}')
  DISK_G=$(df -B 1M | awk '$NF=="/"{printf "%.2f", $4/1024}')

  #Check for and store peak disk usage
  DISK_P_PEAK=$(echo $DISK_P $DISK_P_PEAK | awk '{if ($1 > $2) print $1; else print $2}')
  DISK_G_PEAK=$(echo $DISK_G $DISK_G_PEAK | awk '{if ($1 > $2) print $1; else print $2}')

  #Retrieve overall current CPU usage
  CPU_P=$(top -bn1 | grep load | awk '{printf "%.2f", $(NF-2)}')

  #Check for and store peak CPU usage
  CPU_P_PEAK=$(echo $CPU_P $CPU_P_PEAK | awk '{if ($1 > $2) print $1; else print $2}')

  #Print out the data line
  echo -e "$i\t$MEMORY_P\t$MEMORY_P_PEAK\t$MEMORY_G\t$MEMORY_G_PEAK\t$DISK_P\t$DISK_P_PEAK\t$DISK_G\t$DISK_G_PEAK\t$CPU_P\t$CPU_P_PEAK"

  sleep $DELAY
  let "i+=$DELAY"

done

