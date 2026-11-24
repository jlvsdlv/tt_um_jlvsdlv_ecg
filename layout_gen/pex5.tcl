load tt_um_ecg_v5
select top cell
extract do local
extract do capacitance
extract do coupling
extract all
ext2spice hierarchy off
ext2spice cthresh 0
ext2spice format ngspice
ext2spice -o tt_um_ecg_v5_pex.spice
quit -noprompt
