#!/bin/sh
PID=`ps -ef | grep 'python3 app/app.py 0.0.0.0:10573' | grep -v grep | awk '{print $2}'`
for i in $PID
do
  kill -9 $i
done