#!/bin/bash
i=5
while [[ $i -gt 0 ]];do
  sleep 3
	check_start=`netstat -an|grep -w LISTEN|awk '{if($4 ~/:10573$/) print $4}'|sed 's/:::/ /g'`
	if [ -n "$check_start" ]
	then
		break
	fi
	((i = i - 1))
done
if [[ $i -gt 0 ]]
then
    echo 0
else
	echo "start failed" 1>&2
fi