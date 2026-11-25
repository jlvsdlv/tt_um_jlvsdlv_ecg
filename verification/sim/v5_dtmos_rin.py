import os, re, json, numpy as np, sys
import v5_dtmos_cmp as D, v5_sim as S, v5_bias as B
from lv import header, run
out = {}
for kt in (("tt", 27), ("tt", 60)):
    r0 = [r for r in json.load(open(f"results/dtmos_cmp_{D.VAR}.json")) if (r["corner"], r["temp"]) == kt][0]
    p = S.P(*kt); p["VCM"] = r0["vcm"]
    z = S.zin(p, cpf=0.0)              # no neutralization: the input stage's own admittance
    f, g, b = z["f"], z["g"], z["b"]
    rin = {fx: 1/np.interp(fx, f, g) for fx in (0.5, 1, 10, 50, 150)}   # differential input: resistive part
    out[f"{kt[0]}{kt[1]}"] = dict(rin=rin, cin_pF=float(np.interp(10, f, b)/(2*np.pi*10)*2e12))
print(D.VAR, json.dumps(out, default=float))
