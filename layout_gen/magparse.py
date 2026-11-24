import re
U=200.0   # magscale 1 2 -> 1 unit = 0.005 um
def parse(name):
    layer=None; rects={}; labels=[]; bbox=None
    for l in open(f"{name}.mag"):
        l=l.strip()
        m=re.match(r"<< (\S+) >>",l)
        if m: layer=m.group(1); continue
        if l.startswith("rect ") and layer not in ("checkpaint",):
            x1,y1,x2,y2=[int(v)/U for v in l.split()[1:5]]; rects.setdefault(layer,[]).append((x1,y1,x2,y2))
        if l.startswith("rlabel") or l.startswith("flabel"):
            p=l.split(); labels.append((p[-1],p[1],int(p[2])/U,int(p[3])/U))
        if "FIXED_BBOX" in l:
            bbox=[int(v)/U for v in l.split()[2:6]]
    if bbox is None:
        al=[r for k,v in rects.items() if k not in ("error_p","error_s","error_ps") for r in v]
        bbox=[min(r[0] for r in al),min(r[1] for r in al),max(r[2] for r in al),max(r[3] for r in al)]
    return dict(rects=rects,labels=labels,bbox=bbox)
def m1_stripe_at(c,x,y,layer="metal1"):
    """union bbox of metal1 fragments containing (x,y) column"""
    rs=[r for r in c["rects"].get(layer,[]) if r[0]-1e-6<=x<=r[2]+1e-6]
    rs=[r for r in rs if r[1]-0.6<=y<=r[3]+0.6] or rs
    if not rs: return None
    # grow to connected column
    xs=min(r[0] for r in rs); xe=max(r[2] for r in rs); ys=min(r[1] for r in rs); ye=max(r[3] for r in rs)
    return (xs,ys,xe,ye)
if __name__=="__main__":
    for n in ["M12","M34","MB1","MB2","MR","MVG","MSW","MBF","RBF","CG","CF","CL"]:
        c=parse(n); print(n,"bbox",c["bbox"],"layers",sorted(c["rects"].keys()))
        for lab in c["labels"]:
            st=m1_stripe_at(c,lab[2],lab[3]) if lab[1] not in ("mimcapcontact","via3") else m1_stripe_at(c,lab[2],lab[3],"metal4")
            print("   ",lab, "stripe", None if st is None else tuple(round(v,3) for v in st))
