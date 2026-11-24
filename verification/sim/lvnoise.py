from lv import *
from amp import nef
def rps(p):
    net=header(p)+core(p)+sup(p)+".control\nop\nprint @m.xmr3.msky130_fd_pr__pfet_01v8[gds] @m.xmr3.msky130_fd_pr__pfet_01v8[gbd]\n.endc\n.end\n"
    out,_=run(net); g=sum(float(l.split("=")[1]) for l in out.splitlines() if "[gds]" in l or "[gbd]" in l)
    return 1/g
def opnodes(p):
    net=header(p)+core(p)+sup(p)+".control\nop\nprint all\n.endc\n.end\n"
    out,_=run(net); ns={}
    for l in out.splitlines():
        m_=re.match(r"^(\w+)\s*=\s*([-\d.e+]+)$",l.strip())
        if m_ and m_.group(1) not in ("idd",) and "#" not in m_.group(1): ns[m_.group(1)]=float(m_.group(2))
    return ns
def noise(p):
    r=rps(p); c=core(p)
    ns=opnodes(p)
    c=re.sub(r"\.nodeset.*\n","",c)
    c+= ".nodeset "+" ".join(f"v({k})={v:.6g}" for k,v in ns.items() if k not in ("vdd","vss","vi1","vi2","vbn","vb"))+"\n"
    c=re.sub(r"XMR3 .*\n",f"RR3 g3 vo2 {r:.6g}\n",c); c=re.sub(r"XMR4 .*\n",f"RR4 g4 vo1 {r:.6g}\n",c)
    net=header(p).replace("gmin=1e-15","gmin=1e-13")+c+sup(p,vi1_ac="0.5",vi2_ac="0.5 180")+(".control\nnoise v(vo1,vo2) Vi1 dec 30 0.05 1e4\nsetplot noise1\nlet on2=onoise_spectrum^2\nwrdata no.txt on2\n"
        "setplot const\nac dec 30 0.05 1e4\nlet hm=mag(v(vo1)-v(vo2))\nwrdata ac.txt hm\n.endc\n.end\n")
    out,f=run(net); a=load_wrdata(f["no.txt"]); b=load_wrdata(f["ac.txt"])
    fr=a[:,0]; in2=a[:,1]/np.interp(fr,b[:,0],b[:,1])**2; return fr,in2
if __name__=="__main__":
    for name,p,fL in [("0.3 V shrunk",LP(VDD=0.3,VBN=0.15,VCM=0.07,M34=(40,8,8),M12=(50,8,4),Cg=5e-12,CL=2.5e-12,Cf=0.657e-12),551),
                      ("0.3 V full",LP(VDD=0.3,VBN=0.15,VCM=0.11,M34=(40,8,8),M12=(50,8,16),Cf=2.22e-12),155),
                      ("0.2 V shrunk",LP(VDD=0.2,IB=0.3e-9,M34=(40,4,8),M12=(50,8,4),VBN=0.2,Cg=5e-12,CL=2.5e-12,Cf=0.864e-12,VCM=0.03),305)]:
        fr,in2=noise(p); d=op(p); itot=d["idd"]
        for f1,f2 in ((0.5,150),(0.1,fL)):
            m=(fr>=f1)&(fr<=f2); v=np.sqrt(np.trapezoid(in2[m],fr[m])); n=nef(v,itot,f2)
            print(f"{name}: IRN {f1}-{f2:.0f} Hz = {v*1e6:.2f} uVrms, NEF={n:.2f}, PEF={n*n*p['VDD']:.2f}  (vn@1Hz={np.sqrt(np.interp(1,fr,in2))*1e9:.0f} nV/rtHz, @100Hz={np.sqrt(np.interp(100,fr,in2))*1e9:.0f})")
