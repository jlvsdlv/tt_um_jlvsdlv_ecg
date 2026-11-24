gds read ../outj/gds/tt_um_jlvsdlv_ecg.gds
load tt_um_jlvsdlv_ecg
select top cell
expand
flatten -nolabels aflat
load aflat
select top cell
extract do local
extract no all
extract do aliases
extract do unique
extract all
antennacheck debug
antennacheck
puts "ANTDONE"
quit -noprompt
