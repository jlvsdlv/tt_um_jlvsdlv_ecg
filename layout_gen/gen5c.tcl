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
mk VB0 sky130_fd_pr__cap_var_lvt w 2 l 0.8 nf 1
mk VB1 sky130_fd_pr__cap_var_lvt w 2 l 0.8 nf 2
mk VB2 sky130_fd_pr__cap_var_lvt w 2 l 0.8 nf 4
mk VB3 sky130_fd_pr__cap_var_lvt w 2 l 0.8 nf 8
mk VB4 sky130_fd_pr__cap_var_lvt w 8 l 3.2 nf 1
mk VB5 sky130_fd_pr__cap_var_lvt w 8 l 3.2 nf 2
quit -noprompt
