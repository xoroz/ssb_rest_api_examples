
#!/bin/bash
#
# Script to QUERY syslog-ng store box using bash and api FOR NAGIOS MONITORING SYSTEM
# Felipe Ferreira 07-2016
#
# Refs:
# https://www.balabit.com/documents/ssb-4.4-guides/en/ssb-tutorial-rpcapi-quickstart/html-single/index.html
# https://github.com/gyp/ssb_rest_api_examples
#
# OUTPUT EXAMPLE
# ./check_syslog-storebox.sh 300 10 20
# OK -  "feapa01",9 Found 9 failed attemps to login via SSHD|totalfail=9


USER=admin
PASS=admin
SERVER=127.0.0.1

TIME=$1
WARN=$2
CRIT=$3
PROGRAM=$4
MESSAGE=$5

if [ -z $3 ]; then
 echo "UNKOWN - Missing aruments $0 <TIME_MIN> <WARN> <CRIT>"
 exit 3
fi
TMPFILE=".loginsshattempt"
PROGRAM=sshd
MESSAGE="Failed%20password%20for"
TIME=$(expr $1 \* 60)
#GET SEARCH TIME period
TE=$(date +%s)
TS=$(expr $TE - $TIME)

#echo "TE $TE TS $TS"
URL="https://$SERVER/api/1/search/logspace/filter/center?from=${TS}&to=${TE}&search_expression=Program%3A${PROGRAM}%20Message%3A%20${MESSAGE}&limit=300"


SESSIONID=`wget -q --no-check-certificate -O - "https://$SERVER/api/1/login" --post-data='username=admin&password=admin' | jq '.result' -r`

if [ -z $SESSIONID ]; then
 echo "UNKOWN - Could not login to $SERVER with $USER"
 exit 3
fi

wget -q --no-check-certificate -O - --header "Cookie: PHPSESSID=$SESSIONID" "$URL" | jq '.result' |egrep 'host|message' |grep -B1 "Failed password for" > $TMPFILE

C="cat $TMPFILE | grep host |uniq -c --skip-fields=1 |awk '{print \$NF  \$1 }'"
E=$(eval $C)
TOTALFAIL=$(cat $TMPFILE | grep -o host|wc -l)

MSG=" $E Found $TOTALFAIL failed attemps to login via SSHD|totalfail=$TOTALFAIL"

if [ $TOTALFAIL -gt $CRIT ]; then
 echo "CRITICAL - $MSG"
 exit 2
elif [ $TOTALFAIL -gt $WARN ]; then
 echo "WARNING - $MSG"
 exit 1
fi

echo "OK - $MSG"
exit 0
