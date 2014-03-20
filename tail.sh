#!/bin/bash

SSB_IP=10.120.29.122
USERNAME=admin
PASSWORD=a
LOGSPACE=center
SLEEP=2
LINES_PER_FETCH=1000

SEARCH_EXPRESSION=$1

SESSID=`wget -q --no-check-certificate -O - "https://$SSB_IP/api/1/login" --post-data='username=$USERNAME&password=$PASSWORD' | jq '.result' -r`

LAST_MINUTE=0

function api_request {
    REQUEST=$@

    wget -q --no-check-certificate -O - --header "Cookie: AUTHENTICATION_TOKEN=$SESSID" "https://$SSB_IP/api/1/search/logspace/$REQUEST" | jq '.result' -r
}

function fetch_logs {
    fl_SEARCH_EXPRESSION=$1
    fl_FROM=$2
    fl_TO=$3
    fl_OFFSET=$4
    fl_LIMIT=$5

    api_request "filter/$LOGSPACE?search_expression=$fl_SEARCH_EXPRESSION&from=$fl_FROM&to=$fl_TO&offset=$fl_OFFSET&limit=$fl_LIMIT"
}

function print_logs {
    RAW_LOGS=$@
    echo $RAW_LOGS | jq -c -M '.[].message'
    #echo $RAW_LOGS | jq -c -M '.[] | {timestamp: .received_timestamp, message: .message}'
}

# let's find the last message and their start timestamp
TO=9999999999
NUM_OF_MESSAGES=$(api_request "number_of_messages/$LOGSPACE?search_expression=$SEARCH_EXPRESSION&from=0&to=$TO")
OFFSET=$[$NUM_OF_MESSAGES - 1]
if [ $OFFSET -lt 0 ]
then
    OFFSET=0
fi
FROM=$(api_request "filter/$LOGSPACE?search_expression=$SEARCH_EXPRESSION&from=0&to=$TO&offset=$OFFSET&limit=1" | jq '.[0].received_timestamp')
NUM_OF_MESSAGES=$(api_request "number_of_messages/$LOGSPACE?search_expression=$SEARCH_EXPRESSION&from=$FROM&to=$TO")
# let's display the last 10 messages again...
OFFSET=$[$NUM_OF_MESSAGES - 10]
if [ $OFFSET -lt 0 ]
then
    OFFSET=0
fi

while true
do
    LOGS=$(fetch_logs "$SEARCH_EXPRESSION" $FROM $TO $OFFSET $LINES_PER_FETCH)
    NUM_OF_LINES=`echo $LOGS | jq '. | length'`
    OFFSET=$[$OFFSET + $NUM_OF_LINES]

    print_logs $LOGS

    sleep $SLEEP
done
