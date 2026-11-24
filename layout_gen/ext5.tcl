load tt_um_ecg_v5
select top cell
extract do local
extract all
ext2spice lvs
ext2spice -o tt_um_ecg_v5_lvs.spice
quit -noprompt
