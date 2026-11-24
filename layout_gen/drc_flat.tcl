load tt_um_ecg_v5
select top cell
expand
flatten -nolabels tt_flat
load tt_flat
select top cell
drc style drc(full)
drc check; drc catchup
select top cell; puts "BBOX [box values]"; drc count total
set why [drc listall why]
foreach {msg boxes} $why {
  set s ""
  foreach b [lrange $boxes 0 7] { append s [format " (%.2f,%.2f)" [expr {[lindex $b 0]*0.005}] [expr {[lindex $b 1]*0.005}]] }
  puts "LOC [llength $boxes] | $msg |$s"
}
save tt_flat
quit -noprompt
