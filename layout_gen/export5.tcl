set T tt_um_ecg_v5
load $T
set subs {}
foreach c [cellname list allcells] { if {$c ne $T && $c ne "(UNNAMED)" && ![string match "_scratch_*" $c] && ![string match "tmp_*" $c]} { lappend subs $c } }
foreach c $subs { load $c }
load $T
select top cell
expand
file mkdir out/mag out/gds out/lef
foreach c $subs { catch {cellname rename $c ${T}_$c} }
cd out/mag
foreach c $subs { catch {load ${T}_$c; save ${T}_$c} }
load $T
save $T
cd ../..
load $T
select top cell
drc style drc(full); drc check; drc catchup
puts "FINAL_DRC [drc list count total]"
puts "CELLS [llength [cellname list allcells]]"
gds write out/gds/$T.gds
lef write out/lef/$T.lef -hide -pinonly
quit -noprompt
