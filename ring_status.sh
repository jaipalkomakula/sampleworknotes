#!/bin/bash

state=$(sed -n '/Nodes:/p' /tmp/Metricly_dsoStatus | sed -e 's/:/=/g' -e 's/,//g' -e 's/Nodes=//g' -e 's/(/_/g' -e 's/)//g')
string=$(echo -n "$state"| sed -e 's/=/ /g' -e 's/[0-9]\+//g')
disk=$(sed -n '/Disks:/p' /tmp/Metricly_dsoStatus | sed -e 's/:/=/g' -e 's/,//g')
disk_string=$(echo -n "$disk"| sed -e 's/=/ /g' -e 's/[0-9]\+//g')
ring_status=$(curl -s -X GET --header 'Accept: application/json' 'http://root:admin@localhost:80/api/v0.1/rings/?limit=200' | jq '._items[].status')

  if [ "$ring_status" == "\"OK\"" ] ; then
   RING=$(echo -n "RING=1") # Ring status is okay
  elif [ "$ring_status" == "\"WARNING\"" ] ; then
   RING=$(echo -n "RING=2") # Ring status is Warning state
  else
   RING=$(echo -n "RING=0") # Ring status is Critical state
  fi

  if [ "$(echo -n "$string"|grep -o -P 'RUN')" == "RUN" ] ;then
   Run=$(echo -n "$state" | grep -o -P 'RUN=\d+')
  fi

  if [ "$(echo -n "$string"|grep -o -P 'BAL_DST')" == "BAL_DST" ] ; then
   BAL_DST=$(echo -n "$state" | grep -o -P 'BAL_DST=\d+')
  else
   BAL_DST=$(echo "BAL_DST=0")
  fi

  if [ "$(echo -n "$string"|grep -o -P 'BAL_SRC')" == "BAL_SRC" ] ; then
   BAL_SRC=$(echo -n "$state" | grep -o -P 'BAL_SRC=\d+')
  else
   BAL_SRC=$(echo "BAL_SRC=0")
  fi

  if [ "$(echo -n "$string"|grep -o -P 'SPLIT')" == "SPLIT" ]; then
   SPLIT=$(echo -n "$state" | grep -o -P 'SPLIT=\d+')
  else
   SPLIT=$(echo "SPLIT=0")
  fi

  if [ "$(echo -n "$string"|grep -o -P 'LOOP')" == "LOOP" ];then
   LOOP=$(echo -n "$state" | grep -o -P 'LOOP=\d+')
  else
   LOOP=$(echo "LOOP=0")
  fi

  if [ "$(echo -n "$string"|grep -w -o -P 'OFFLINE')" == "OFFLINE" ];then
   OFFLINE=$(echo -n "$state" | grep -w -o -P 'OFFLINE=\d+')
  else
   OFFLINE=$(echo "OFFLINE=0")
  fi

 if [ "$(echo -n "$string"|grep -o -P 'OOS')" == "OOS" ];then
   OOS=$(echo -n "$state" | grep -o -P 'OOS=\d+')
  else
   OOS=$(echo "OOS=0")
  fi

 if [ "$(echo -n "$string"|grep -o -P 'LOADING')" == "LOADING" ];then
   LOADING=$(echo -n "$state" | grep -o -P 'LOADING=\d+')
  else
   LOADING=$(echo "LOADING=0")
  fi

 if [ "$(echo -n "$disk_string"|grep -o -P 'OOS_PERM')" == "OOS_PERM" ];then
   OOS_PERM=$(echo -n "$disk" | grep -o -P 'OOS_PERM=\d+')
  else
   OOS_PERM=$(echo "OOS_PERM=0")
  fi

 if [ "$(echo -n "$disk_string"|grep -o -P 'OOS_TEMP')" == "OOS_TEMP" ];then
   OOS_TEMP=$(echo -n "$disk" | grep -o -P 'OOS_TEMP=\d+')
  else
   OOS_TEMP=$(echo "OOS_TEMP=0")
  fi

 if [ "$(echo -n "$disk_string"|grep -o -P 'OOS_SYS')" == "OOS_SYS" ];then
   OOS_SYS=$(echo -n "$disk" | grep -o -P 'OOS_SYS=\d+')
  else
   OOS_SYS=$(echo "OOS_SYS=0")
  fi

 if [ "$(echo -n "$string"|grep -o -P 'TASKS_BLOCKED')" == "TASKS_BLOCKED" ];then
   TASKS_BLOCKED=$(echo -n "$state" | grep -o -P 'TASKS_BLOCKED=\d+')
  else
   TASKS_BLOCKED=$(echo "TASKS_BLOCKED=0")
  fi
echo "Scality_ring,status=node $RING,$Run,$BAL_DST,$BAL_SRC,$LOOP,$SPLIT,$OFFLINE,$OOS,$LOADING,$OOS_PERM,$OOS_TEMP,$OOS_SYS,$TASKS_BLOCKED"
