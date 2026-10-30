import sys, cadquery as cq, math
from OCP.STEPCAFControl import STEPCAFControl_Reader
# load whole STEP, pick the solid whose bbox is the PCB (thin, large)
shape = cq.importers.importStep(sys.argv[1])
cx, cy = float(sys.argv[2]), float(sys.argv[3])
best=None
for s in shape.val().Solids():
    bb=s.BoundingBox()
    if bb.xlen>80 and bb.ylen>80 and bb.zlen<2: best=s
bb=best.BoundingBox(); print("PCB bbox", bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax)
print("PCB area top face approx:", best.Volume()/bb.zlen, " (square 88^2=7744, circle d88=%.0f)"%(math.pi*44*44))
# outer edges on top face
top=[f for f in best.Faces() if f.geomType()=="PLANE" and abs(f.Center().z-bb.zmax)<1e-3]
print("top faces", len(top))
for e in top[0].outerWire().Edges():
    t=e.geomType()
    if t=="CIRCLE":
        c=e.arcCenter() if hasattr(e,'arcCenter') else e.Center(); print("outer CIRCLE r=%.2f c=(%.2f,%.2f)"%(e.radius(),c.x-cx,c.y-cy))
    else:
        a,b=e.startPoint(),e.endPoint(); print("outer",t,"(%.2f,%.2f)->(%.2f,%.2f)"%(a.x-cx,a.y-cy,b.x-cx,b.y-cy))
holes={}
for w in top[0].innerWires():
    es=w.Edges()
    if all(e.geomType()=="CIRCLE" for e in es):
        r=es[0].radius(); c=es[0].arcCenter()
        k=(round(c.x-cx,2),round(c.y-cy,2),round(2*r,2))
        holes[k]=1
    else:
        b=w.BoundingBox(); holes[("slot",round(b.center.x-cx,2),round(b.center.y-cy,2),round(b.xlen,2),round(b.ylen,2))]=1
for k in sorted(holes, key=lambda k: str(k)): print("hole", k)
