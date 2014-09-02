#!/bin/bash

. ssb_credentials

LIMIT=1000

function translate_query_url_to_api_request {
    QUERY_URL=$1

    PREFIX_STRIPPED=`echo $QUERY_URL | sed 's/^https:\/\/.*index.php?_backend=SearchLogspace#logspace_name=//'`

    LOGSPACE=`echo $PREFIX_STRIPPED | sed 's/&.*$//'`
    QUERY_PARAMS=`echo $PREFIX_STRIPPED | sed 's/^[^&]*&//'`

    echo "filter/$LOGSPACE?$QUERY_PARAMS&limit=$LIMIT"
}

function api_request {
    REQUEST=$@

    wget -q --no-check-certificate -O - --header "Cookie: AUTHENTICATION_TOKEN=$SESSID" "https://$SSB_IP/api/1/search/logspace/$REQUEST" | jq '.result' -r
}

function format_results_as_syslog {
    RAW_RESULTS=$@

    NUM_RESULTS=`echo $RAW_RESULTS | jq -r -c '. | length'`
    ITER_MAX=$[$NUM_RESULTS - 1]
    for i in `seq 0 $ITER_MAX`
    do
        # FIXME: this is horribly inefficient this way

        LOG_MSG=`echo $RAW_RESULTS | jq -c ".[$i]"`

        TIMESTAMP=`echo $LOG_MSG | jq -r -c ".timestamp"`
        DATESTRING=`date -d @$TIMESTAMP` # FIXME: this is local time
        HOST=`echo $LOG_MSG | jq -r -c ".host"`
        PROGRAM=`echo $LOG_MSG | jq -r -c ".program"`
        PID=`echo $LOG_MSG | jq -r -c ".pid"`
        MESSAGE=`echo $LOG_MSG | jq -r -c ".message"`

        echo "$DATESTRING $HOST $PROGRAM[$PID]: $MESSAGE"
    done
}

API_REQUEST=$(translate_query_url_to_api_request $1)

# login
SESSID=`wget -q --no-check-certificate -O - "https://$SSB_IP/api/1/login" --post-data="username=$USERNAME&password=$PASSWORD" | jq '.result' -r`

RESULTS=$(api_request $API_REQUEST)

format_results_as_syslog $RESULTS
