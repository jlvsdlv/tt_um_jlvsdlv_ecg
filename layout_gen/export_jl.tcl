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
# antenna diodes (b4, it0, b5, b9)
box 288.500um 74.500um 289.100um 75.100um
paint ndiode
box 288.715um 74.715um 288.885um 74.885um
paint ndiodec
box 288.600um 74.600um 289.000um 75.000um
paint locali
box 288.715um 74.715um 288.885um 74.885um
paint viali
box 288.600um 74.600um 289.000um 75.000um
paint metal1
box 286.650um 74.650um 288.950um 74.950um
paint metal1
box 267.100um 74.500um 267.700um 75.100um
paint ndiode
box 267.315um 74.715um 267.485um 74.885um
paint ndiodec
box 267.200um 74.600um 267.600um 75.000um
paint locali
box 267.315um 74.715um 267.485um 74.885um
paint viali
box 267.200um 74.600um 267.600um 75.000um
paint metal1
box 265.050um 74.650um 267.550um 74.950um
paint metal1
box 288.500um 27.300um 289.100um 27.900um
paint ndiode
box 288.715um 27.515um 288.885um 27.685um
paint ndiodec
box 288.600um 27.400um 289.000um 27.800um
paint locali
box 288.715um 27.515um 288.885um 27.685um
paint viali
box 288.600um 27.400um 289.000um 27.800um
paint metal1
box 286.650um 27.450um 288.950um 27.750um
paint metal1
box 303.500um 109.700um 304.100um 110.300um
paint ndiode
box 303.715um 109.915um 303.885um 110.085um
paint ndiodec
box 303.600um 109.800um 304.000um 110.200um
paint locali
box 303.715um 109.915um 303.885um 110.085um
paint viali
box 303.600um 109.800um 304.000um 110.200um
paint metal1
box 301.050um 109.850um 303.950um 110.150um
paint metal1
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
