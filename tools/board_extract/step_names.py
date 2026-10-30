import sys
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopLoc import TopLoc_Location
doc = TDocStd_Document(TCollection_ExtendedString("doc"))
r = STEPCAFControl_Reader(); r.SetNameMode(True)
r.ReadFile(sys.argv[1]); r.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
def name(l):
    a = TDataStd_Name()
    return a.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(), a) else "?"
from OCP.XCAFDoc import XCAFDoc_ShapeTool
out=[]
def walk(lab, loc, depth):
    comps = TDF_LabelSequence()
    if XCAFDoc_ShapeTool.IsAssembly_s(lab) or XCAFDoc_ShapeTool.IsReference_s(lab):
        pass
    if XCAFDoc_ShapeTool.IsReference_s(lab):
        ref = TDF_LabelSequence()
        from OCP.TDF import TDF_Label
        r2 = TDF_Label(); XCAFDoc_ShapeTool.GetReferredShape_s(lab, r2)
        walk(r2, loc * XCAFDoc_ShapeTool.GetLocation_s(lab), depth); return
    XCAFDoc_ShapeTool.GetComponents_s(lab, comps, False)
    if comps.Length()==0:
        s = XCAFDoc_ShapeTool.GetShape_s(lab).Moved(loc)
        b=Bnd_Box(); BRepBndLib.Add_s(s,b,True)
        if b.IsVoid(): return
        x0,y0,z0,x1,y1,z1=b.Get()
        out.append((name(lab),x0,y0,z0,x1,y1,z1)); return
    for i in range(1,comps.Length()+1):
        c=comps.Value(i)
        nm=name(c)
        r2 = __import__('OCP.TDF',fromlist=['TDF_Label']).TDF_Label()
        XCAFDoc_ShapeTool.GetReferredShape_s(c, r2)
        sub=r2
        s = XCAFDoc_ShapeTool.GetShape_s(c)
        cc=TDF_LabelSequence(); XCAFDoc_ShapeTool.GetComponents_s(sub,cc,False)
        if cc.Length()==0:
            s=XCAFDoc_ShapeTool.GetShape_s(sub).Moved(loc*XCAFDoc_ShapeTool.GetLocation_s(c))
            b=Bnd_Box(); BRepBndLib.Add_s(s,b,True)
            if b.IsVoid(): continue
            x0,y0,z0,x1,y1,z1=b.Get()
            out.append((nm+"|"+name(sub),x0,y0,z0,x1,y1,z1))
        else:
            walk(sub, loc*XCAFDoc_ShapeTool.GetLocation_s(c), depth+1)
roots=TDF_LabelSequence(); st.GetFreeShapes(roots)
for i in range(1,roots.Length()+1): walk(roots.Value(i), TopLoc_Location(), 0)
for o in out: print("%-60s x[%8.2f %8.2f] y[%8.2f %8.2f] z[%7.2f %7.2f]"%(o[0][:60],o[1],o[4],o[2],o[5],o[3],o[6]))
print(len(out),"leaf parts")
