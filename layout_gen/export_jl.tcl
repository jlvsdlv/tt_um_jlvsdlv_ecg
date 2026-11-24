set T0 tt_um_ecg_v5
set T tt_um_jlvsdlv_ecg
load $T0
set subs {}
foreach c [cellname list allcells] { if {$c ne $T0 && $c ne "(UNNAMED)" && ![string match "_scratch_*" $c] && ![string match "tmp_*" $c]} { lappend subs $c } }
foreach c $subs { load $c }
load $T0
select top cell
expand
file mkdir outj/mag outj/gds outj/lef
foreach c $subs { catch {cellname rename $c ${T}_$c} }
cellname rename $T0 $T
load $T
box 4.5um 0.5um 36.79um 2.5um
paint metal4
box 4.5um 0.5um 6.5um 5.2um
paint metal4
cd outj/mag
foreach c $subs { catch {load ${T}_$c; save ${T}_$c} }
load $T
save $T
cd ../..
load $T
select top cell
drc style drc(full); drc check; drc catchup
puts "FINAL_DRC [drc list count total]"
puts "CELLS [llength [cellname list allcells]]"
gds write outj/gds/$T.gds
lef write outj/lef/$T.lef -hide -pinonly
quit -noprompt
