set -e
RSEED=${RSEED:-0} python3 route6.py 60 > route6.log 2>&1
timeout 1500 /opt/magic/bin/magic -dnull -noconsole drc_route2.tcl 2>&1 | grep -E "LOC|Total" | cut -c1-600 >> route6.log
cd ext && rm -f *.ext *.mag && cp ../*.mag . && cp ../tt_um_ecg_v5_ref.spice .
timeout 900 /opt/magic/bin/magic -dnull -noconsole ../ext5.tcl > ext.log 2>&1
timeout 900 /usr/lib/netgen/bin/netgen -batch source ../lvs5.tcl > netgen.log 2>&1
grep -E "Netlists match|Property|property|Number of devices" lvs5.out | sort | uniq -c >> ../route6.log
timeout 1500 /opt/magic/bin/magic -dnull -noconsole ../pex5.tcl > pex.log 2>&1
python3 ../pexmap.py > pexmap.log; head -6 pexmap.log >> ../route6.log
echo FLOWDONE >> ../route6.log
