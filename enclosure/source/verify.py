"""Reopen deliverables independently; verify orientation, print layout and layers."""
from pathlib import Path
import json
import zipfile
import xml.etree.ElementTree as ET
import cadquery as cq
import numpy as np
import trimesh
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/'source/parameters.json').read_text('utf-8'))
G=json.loads((ROOT/'geometry-verification.json').read_text('utf-8'))
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
report={'assemblies':{},'print_layouts':{},'layer_checks':{}}

for key in P['profiles']:
    profile=P['profiles'][key]
    case={**P['case'],**profile.get('case',{})}
    front=cq.importers.importStep(str(ROOT/'source'/f'Front_{key}.step')).solids().val()
    side=1 if profile['usb_side']=='left' else -1
    x=side*(case['width']/2-case['wall']/2)
    z=(P['port']['bottom_z']+case['front_depth'])/2
    aperture_open=not front.isInside(cq.Vector(x,profile['usb_y'],z))
    opposite_closed=front.isInside(cq.Vector(-x,profile['usb_y'],z))
    assert aperture_open and opposite_closed, f'{key}: USB aperture is on wrong side'
    path=ROOT/f'FlowSight_Desk_{key}.step'
    shape=cq.importers.importStep(str(path)).val()
    assert shape.isValid(), f'{key}: invalid reimported STEP'
    transform=np.array(G['orientation']['design_to_assembly'][key])
    normal=transform[:3,:3]@np.array([0,0,-1])
    up=transform[:3,:3]@np.array([0,1,0])
    assert normal[1]>0 and normal[2]>0 and up[1]<0 and up[2]>0
    # Locate the actual outside front plane in the reimported assembly.
    candidates=[]
    for face in shape.Faces():
        if face.geomType()!='PLANE' or face.Area()<1000:
            continue
        n=np.array(face.normalAt().toTuple())
        centre=np.array(face.Center().toTuple())
        if np.dot(n,normal)>.9999 and abs(np.dot(centre-transform[:3,3],normal))<.002:
            candidates.append(face)
    assert candidates, f'{key}: outside front face missing or facing wrong direction'
    report['assemblies'][key]={
        'valid_step':True,'front_face_area_mm2':round(max(f.Area() for f in candidates),3),
        'front_normal':normal.round(6).tolist(),'screen_up':up.round(6).tolist(),
        'usb_side_from_front':profile['usb_side'],'usb_aperture_open':aperture_open,
        'opposite_wall_closed':opposite_closed}

    with zipfile.ZipFile(ROOT/'print'/f'FlowSight_Desk_{key}.3mf') as z:
        model=ET.fromstring(z.read('3D/3dmodel.model'))
    assert model.attrib['unit']=='millimeter'
    objects={}
    for obj in model.findall('m:resources/m:object',NS):
        vertices=np.array([[float(v.attrib[a]) for a in ['x','y','z']]
            for v in obj.findall('m:mesh/m:vertices/m:vertex',NS)])
        faces=np.array([[int(f.attrib[a]) for a in ['v1','v2','v3']]
            for f in obj.findall('m:mesh/m:triangles/m:triangle',NS)])
        m=trimesh.Trimesh(vertices=vertices,faces=faces,process=True)
        assert m.is_watertight and m.is_winding_consistent and m.volume>0
        assert len(m.split())==1
        stl=trimesh.load(ROOT/'print'/(obj.attrib['name']+'.stl'),force='mesh')
        assert np.allclose(m.bounds,stl.bounds,atol=.002)
        assert abs(m.volume-stl.volume)<.02
        assert abs(m.bounds[0,2])<.002
        objects[obj.attrib['id']]=(obj.attrib['name'],m)
    items=model.findall('m:build/m:item',NS)
    assert len(items)==4
    bounds=[];names=[]
    for item in items:
        name,m=objects[item.attrib['objectid']]
        t=np.array([float(v) for v in item.attrib['transform'].split()])
        assert np.allclose(t[:9],np.eye(3).flatten())
        bounds.append(m.bounds+t[9:]);names.append(name)
    assert set(names)=={'Front_'+key,'Rear_cover_'+key,'Service_hatch','Desk_stand_65deg'}
    for i,b in enumerate(bounds):
        for a in bounds[:i]:
            assert not np.all(np.minimum(a[1,:2],b[1,:2])-np.maximum(a[0,:2],b[0,:2])>0)
    limits=np.array([np.min([b[0] for b in bounds],axis=0),np.max([b[1] for b in bounds],axis=0)])
    assert np.all(limits[1,:2]<220)
    report['print_layouts'][key]={'objects':names,'bounds_mm':np.round(limits,3).tolist(),
        'size_mm':np.round(limits[1]-limits[0],3).tolist(),'closed_meshes':True,'nonoverlapping':True}

parts=[name for name in G['parts'] if name.startswith(('Front_','Rear_cover_'))]
parts+=['Service_hatch','Desk_stand_65deg']
for name in parts:
    mesh=trimesh.load(ROOT/'print'/(name+'.stl'),force='mesh')
    heights=np.arange(.1,mesh.bounds[1,2],.2)
    sections=mesh.section_multiplane([0,0,0],[0,0,1],heights)
    previous=None;islands=[]
    for z,path in zip(heights,sections):
        if path is None:continue
        polys=list(path.polygons_full)
        if previous is not None:
            support=previous.buffer(.22)
            islands.extend({'z_mm':round(float(z),3),'area_mm2':round(poly.area,4)}
                for poly in polys if poly.area>.04 and not poly.intersects(support))
        previous=unary_union(polys)
    assert not islands, f'{name}: floating layer islands {islands}'
    report['layer_checks'][name]={'layer_height_mm':.2,'lateral_allowance_mm':.22,
        'sections':len(heights),'floating_start_islands':0}

report['limits']='Digital checks only. Layer sampling is not printer simulation; physical CS32 dimensions, fit and touch stability remain unverified.'
G['independent_verification']=report
(ROOT/'geometry-verification.json').write_text(json.dumps(G,indent=2),'utf-8')
print(json.dumps(report,indent=2))
