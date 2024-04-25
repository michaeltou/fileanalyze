#!/bin/bash
check_start=`ps axu | grep 'python3 app/app.py 0.0.0.0:10573' | grep -v grep | awk '{printf $2}'`
if [ -z "$check_start" ]
then
  echo 0
else
	echo "No stopping!" 1>&2
fi