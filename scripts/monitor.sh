#! /bin/bash

printf "Memory_Percent\tMemory_G\tDisk_Percent\tDisk_G\tCPU_Percent\n"
DELAY=5

while : 
do

  MEMORY_P=$(free -m | awk 'NR==2{printf "%.2f%%\t", $3*100/$2 }')
  MEMORY_G=$(free -g | awk 'NR==2{printf "%.2fG\t", $3 }')

  DISK_P=$(df -h | awk '$NF=="/"{printf "%s\t", $5}')
  DISK_G=$(df -h | awk '$NF=="/"{printf "%s\t", $4}')

  CPU_P=$(top -bn1 | grep load | awk '{printf "%.2f%%\t\n", $(NF-2)}')

  echo "$MEMORY_P$MEMORY_G$DISK_P$DISK_G$CPU_P"

  sleep $DELAY

done
