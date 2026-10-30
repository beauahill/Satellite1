import sys, cadquery as cq
from collections import Counter
s=cq.importers.importStep(sys.argv[1]).val(); rmin=float(sys.argv[2]) if len(sys.argv)>2 else 1.0
seen=Counter()
for e in s.Edges():
    if e.geomType()!="CIRCLE": continue
    r=e.radius()
    if r<rmin: continue
    c=e.arcCenter()
    # axis direction
    try:
        n=e._geomAdaptor().Circle().Axis().Direction(); ax="X" if abs(n.X())>.9 else "Y" if abs(n.Y())>.9 else "Z" if abs(n.Z())>.9 else "?"
    except Exception: ax="?"
    seen[(ax,round(c.x,1),round(c.y,1),round(c.z,1),round(2*r,2))]+=1
for k,v in sorted(seen.items(), key=lambda kv:(kv[0][0],kv[0][3],kv[0][1],kv[0][2])): print(k, "x%d"%v)
