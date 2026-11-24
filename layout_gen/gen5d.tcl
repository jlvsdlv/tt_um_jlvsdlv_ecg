proc mk {name dev args} {
    load tmp_$name -silent
    box 0 0 0 0
    eval magic::gencell sky130::$dev ${name}_i $args
    set c [lindex [cellname list children tmp_$name] 0]
    load $c
    cellname rename $c $name
    select top cell
    set b [box values]
    drc style drc(full); drc check; drc catchup
    puts "BBOX $name [expr {([lindex $b 2]-[lindex $b 0])/200.0}] [expr {([lindex $b 3]-[lindex $b 1])/200.0}] DRC [drc list count total]"
    save $name
}
set F {conn_gates 1 viagl 100 viagr 100 viagb 0 viagt 0}
eval mk XP1 sky130_fd_pr__pfet_01v8_lvt w 25 l 8 nf 4 topc 1 botc 0 $F
eval mk XP1B sky130_fd_pr__pfet_01v8_lvt w 25 l 8 nf 4 topc 0 botc 1 $F
eval mk M34S sky130_fd_pr__nfet_01v8_lvt w 2.5 l 64 nf 1 topc 1 botc 0 $F
mk VAR9G sky130_fd_pr__cap_var_lvt w 10 l 8 nf 9 guard 0
mk VB0G sky130_fd_pr__cap_var_lvt w 2 l 0.8 nf 1 guard 0
mk VB1G sky130_fd_pr__cap_var_lvt w 2 l 0.8 nf 2 guard 0
mk VB2G sky130_fd_pr__cap_var_lvt w 2 l 0.8 nf 4 guard 0
mk VB3G sky130_fd_pr__cap_var_lvt w 2 l 0.8 nf 8 guard 0
mk VB4G sky130_fd_pr__cap_var_lvt w 8 l 3.2 nf 1 guard 0
mk VB5G sky130_fd_pr__cap_var_lvt w 8 l 3.2 nf 2 guard 0
mk RXA sky130_fd_pr__res_xhigh_po_0p35 l 70 nx 16 snake 0 guard 1
mk RXB sky130_fd_pr__res_xhigh_po_0p35 l 65.5 nx 2 snake 0 guard 1
mk RXC sky130_fd_pr__res_xhigh_po_0p35 l 65.5 nx 4 snake 0 guard 1
quit -noprompt
