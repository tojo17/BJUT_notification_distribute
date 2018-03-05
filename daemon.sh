#!/bin/bash
cd $(dirname ${0})
nohup python3 ./noti.py > ./log.txt 2>&1 &