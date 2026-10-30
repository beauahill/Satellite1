import sys, cadquery as cq
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN, TopAbs_ON
D=sys.argv[1]
parts=[cq.importers.importStep(D+"/"+n).val() for n in ["Sat1.x large - Chamber front - FPH Woofer +Tweeter + LD2450 pocket.step","Sat1.x large - Chamber back - Wifi pocket + Bass port.step"]]
cls=[BRepClass3d_SolidClassifier(p.wrapped) for p in parts]
def solid(x,y,z):
    for c in cls:
        c.Perform(gp_Pnt(x,y,z),1e-3)
        if c.State() in (TopAbs_IN,TopAbs_ON): return True
    return False
for x in range(-40,41,8):
    row=[]
    for y in range(-40,41,8):
        if x*x+y*y>42*42: row.append("   ."); continue
        z=-8.6
        while z>-40 and not solid(x,y,z): z-=0.5
        row.append("%4.1f"%(-8.5-z))
    print("x=%4d "%x+" ".join(row), flush=True)
print("cols y=-40..40 step 8 (+y = rear/I-O edge); value = clear depth (mm) below HAT bottom plane z=-8.5")
