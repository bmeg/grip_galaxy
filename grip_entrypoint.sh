#!/bin/bash

SIFTER_FILE=$1
GRAPH_NAME=$2

grip server &
sleep 2
sifter run $SIFTER_FILE -g grip://localhost:8202/$GRAPH_NAME --proxy http://localhost:8080 --port 8888 &

export GRIP_URL="http://localhost:8201"

jupyter-lab --allow-root --no-browser --NotebookApp.token='' --NotebookApp.password='' --ip=0.0.0.0 --port 8080
