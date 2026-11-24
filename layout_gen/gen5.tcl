proc mk {name dev args} {
    load tmp_$name -silent
    box 0 0 0 0
    eval magic::gencell sky130::$dev ${name}_i $args
    set c [lindex [cellname list children tmp_$name] 0]
    load $c
    cellname rename $c $name
    select top cell
    set b [box values]
    puts "BBOX $name [expr {([lindex $b 2]-[lindex $b 0])/200.0}] [expr {([lindex $b 3]-[lindex $b 1])/200.0}]"
    save $name
}
set F {topc 1 botc 0 conn_gates 1 viagl 100 viagr 100 viagb 0 viagt 0}
eval mk M12Q sky130_fd_pr__pfet_01v8_lvt w 50 l 8 nf 4 $F
eval mk M34H sky130_fd_pr__nfet_01v8_lvt w 2.5 l 64 nf 2 $F
eval mk MB1 sky130_fd_pr__pfet_01v8_lvt w 2 l 2 nf 10 $F
eval mk MB2Q sky130_fd_pr__pfet_01v8_lvt w 2 l 2 nf 50 $F
eval mk MREP sky130_fd_pr__pfet_01v8 w 10 l 1 nf 48 $F
eval mk MRB sky130_fd_pr__pfet_01v8 w 2 l 20 nf 1 $F
eval mk MRF sky130_fd_pr__pfet_01v8 w 0.42 l 4 nf 1 $F
eval mk MIRB sky130_fd_pr__nfet_01v8_lvt w 0.42 l 16 nf 1 $F
eval mk MSWP sky130_fd_pr__pfet_01v8_lvt w 0.42 l 0.5 nf 1 $F
eval mk MLAD sky130_fd_pr__pfet_01v8_lvt w 2 l 2 nf 1 $F
eval mk PL4L2 sky130_fd_pr__pfet_01v8_lvt w 4 l 2 nf 1 $F
eval mk PL2L2 sky130_fd_pr__pfet_01v8_lvt w 2 l 2 nf 1 $F
eval mk NL2L8 sky130_fd_pr__nfet_01v8_lvt w 2 l 8 nf 1 $F
eval mk NL2L8x4 sky130_fd_pr__nfet_01v8_lvt w 2 l 8 nf 4 $F
eval mk NL2L8x5 sky130_fd_pr__nfet_01v8_lvt w 2 l 8 nf 5 $F
eval mk NL2L8x8 sky130_fd_pr__nfet_01v8_lvt w 2 l 8 nf 8 $F
eval mk NL2L4 sky130_fd_pr__nfet_01v8_lvt w 2 l 4 nf 1 $F
eval mk PL4L8 sky130_fd_pr__pfet_01v8_lvt w 4 l 8 nf 1 $F
eval mk NL042L1 sky130_fd_pr__nfet_01v8_lvt w 0.42 l 1 nf 1 $F
eval mk N042L1 sky130_fd_pr__nfet_01v8 w 0.42 l 1 nf 1 $F
eval mk P042L4 sky130_fd_pr__pfet_01v8 w 0.42 l 4 nf 1 $F
eval mk N1L05 sky130_fd_pr__nfet_01v8 w 1 l 0.5 nf 1 $F
eval mk N2L05 sky130_fd_pr__nfet_01v8 w 2 l 0.5 nf 1 $F
eval mk N05L05 sky130_fd_pr__nfet_01v8 w 0.5 l 0.5 nf 1 $F
eval mk P1L05 sky130_fd_pr__pfet_01v8 w 1 l 0.5 nf 1 $F
eval mk P2L05 sky130_fd_pr__pfet_01v8 w 2 l 0.5 nf 1 $F
eval mk P4L05 sky130_fd_pr__pfet_01v8 w 4 l 0.5 nf 1 $F
mk VARCBC sky130_fd_pr__cap_var_lvt w 10 l 8 nf 15
mk VARU sky130_fd_pr__cap_var_lvt w 2 l 0.8 nf 1
mk VAR16 sky130_fd_pr__cap_var_lvt w 8 l 3.2 nf 1
mk C30 sky130_fd_pr__cap_mim_m3_1 w 30 l 30
mk C236 sky130_fd_pr__cap_mim_m3_1 w 23.6 l 23.6
mk C184 sky130_fd_pr__cap_mim_m3_1 w 18.4 l 18.4
mk C7 sky130_fd_pr__cap_mim_m3_1 w 7 l 7
mk RX0 sky130_fd_pr__res_xhigh_po_0p35 l 70 nx 16 snake 1 viagl 100 viagr 100
mk RX1 sky130_fd_pr__res_xhigh_po_0p35 l 65.5 nx 2 snake 1 viagl 100 viagr 100
mk RX2 sky130_fd_pr__res_xhigh_po_0p35 l 65.5 nx 4 snake 1 viagl 100 viagr 100
quit -noprompt
