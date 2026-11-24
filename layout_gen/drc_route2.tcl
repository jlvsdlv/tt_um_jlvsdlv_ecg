source build5_route.tcl
load tt_um_ecg_v5
select top cell
save tt_um_ecg_v5
drc style drc(full)
drc check; drc catchup
puts "DRCCOUNT [drc count total]"
set why [drc listall why]
foreach {msg boxes} $why {
  set s ""
  foreach b [lrange $boxes 0 60] { append s [format " (%.2f,%.2f)" [expr {[lindex $b 0]*0.005}] [expr {[lindex $b 1]*0.005}]] }
  puts "LOC [llength $boxes] | $msg |$s"
}
quit -noprompt
