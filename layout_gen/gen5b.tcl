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
mk C3048 sky130_fd_pr__cap_mim_m3_1 w 30 l 48
quit -noprompt
