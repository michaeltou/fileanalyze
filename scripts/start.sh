#!/bin/sh
cd mce-service
nohup python3 app/app.py 0.0.0.0:10573 >app.log 2>&1 &