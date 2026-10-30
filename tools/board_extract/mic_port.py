import sys, cadquery as cq
s=cq.importers.importStep(sys.argv[1]).val()
cx,cy=150.0,-100.0
mics={"MK1":(148.53,151.53,-65.92,-61.92),"MK2":(184.08,188.08,-101.53,-98.53),"MK3":(148.47,151.47,-138.08,-134.08),"MK4":(111.92,115.92,-101.47,-98.47)}
for n,(x0,x1,y0,y1) in mics.items():
    found=set()
    for e in s.Edges():
        if e.geomType()!="CIRCLE": continue
        c=e.arcCenter()
        if x0-0.1<=c.x<=x1+0.1 and y0-0.1<=c.y<=y1+0.1 and c.z>1.0:
            found.add((round(c.x-cx,2),round(c.y-cy,2),round(c.z,2),round(2*e.radius(),2)))
    print(n,"body centre (%.2f,%.2f)"%((x0+x1)/2-cx,(y0+y1)/2-cy),sorted(found))
