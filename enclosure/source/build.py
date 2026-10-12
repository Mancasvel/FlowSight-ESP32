"""Generate original FlowSight enclosure, millimetres, CadQuery 2.8.

Front face is Z=0, back is +Z. Print fronts with Z=0 on bed.
STLs have their required bed orientation baked in. No supports are intended.
Run: python source/build.py
"""
from pathlib import Path
import json, math, zipfile, xml.etree.ElementTree as ET
import cadquery as cq
import numpy as np
import trimesh
from PIL import Image
from scipy import ndimage
from matplotlib.figure import Figure
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT/'source', ROOT/'print'
P = json.loads((SRC/'parameters.json').read_text('utf-8'))
OUT.mkdir(exist_ok=True)

def rr(w,h,r,z,t,x=0,y=0):
    return (cq.Workplane('XY').workplane(offset=z).center(x,y)
            .rect(w,h).extrude(t).edges('|Z').fillet(r))

def box(w,h,t,x=0,y=0,z=0):
    return cq.Workplane('XY').box(w,h,t,centered=(True,True,False)).translate((x,y,z))

def cyl(r,h,x,y,z):
    return cq.Workplane('XY').workplane(offset=z).center(x,y).circle(r).extrude(h)

def logo_polygons():
    a=np.array(Image.open(SRC/'flowsight-logo.png').convert('RGBA'))[:,:,3]
    mask=ndimage.binary_closing(a>100,iterations=1)
    labs,n=ndimage.label(mask)
    mask=np.isin(labs,[i for i in range(1,n+1) if (labs==i).sum()>80])
    fig=Figure();ax=fig.subplots();cs=ax.contour(mask.astype(float),levels=[.5])
    segments=[seg for seg in cs.allsegs[0] if len(seg)>10]
    # The raster is the user's official logo; no substitute glyph is introduced.
    polys=[]
    for seg in segments:
        from shapely.geometry import Polygon
        poly=Polygon(seg).simplify(.8,preserve_topology=True)
        xy=np.array(poly.exterior.coords)[:-1]
        brand=P['brand']
        xy[:,0]=(xy[:,0]-256)/307*brand['logo_width']+brand['logo_center_x']
        xy[:,1]=-(xy[:,1]-270)/307*brand['logo_width']+brand['center_y']
        polys.append(xy.tolist())
    (SRC/'logo-polygons.json').write_text(json.dumps(polys,indent=2),'utf-8')
    return polys

fontpath=SRC/'Manrope-Bold.ttf'
if not fontpath.exists():
    font=TTFont(SRC/'Manrope.ttf')
    if 'fvar' in font: font=instantiateVariableFont(font,{'wght':700},inplace=True)
    font.save(fontpath)

def branding(depth=.6):
    parts=[]
    for poly in logo_polygons():
        parts.extend(cq.Workplane('XY').polyline(poly).close().extrude(depth).solids().vals())
    b=P['brand']
    words=(cq.Workplane('XY').text(b['wordmark'],b['type_size'],depth,fontPath=str(fontpath),
             halign='center',valign='center',combine=False).translate((b['type_center_x'],b['center_y'],0)))
    parts.extend(words.solids().vals())
    fused=cq.Workplane('XY').newObject([parts[0]])
    for part in parts[1:]: fused=fused.union(part)
    # Text must read from outside (-Z), so reverse its X axis in CAD.
    return fused.clean().mirror('YZ')

BRAND=branding()

def case_for(profile=None):
    return {**P['case'],**((profile or {}).get('case',{}))}

def screw_centers(c):
    ox,oy=P['case_screw_edge_offsets']
    return [(x,y) for x in [ox-c['width']/2,c['width']/2-ox]
            for y in [oy-c['height']/2,c['height']/2-oy]]

def front(profile):
    c=case_for(profile);w,h,d,t=c['width'],c['height'],c['front_depth'],c['wall']
    s=rr(w,h,c['radius'],0,d)
    s=s.edges('not |Z').fillet(.9)
    cavity=rr(w-2*t,h-2*t,c['radius']-t,t,d+1)
    s=s.cut(cavity)
    aw,ah=profile['window'];sx,sy=P['screen_center']
    window=rr(aw,ah,.55,-.1,t+.5,sx,sy)
    # 0.8 mm light-catching lead-in; no lip covers the active touch area.
    bevel=(cq.Workplane('XY').workplane(offset=-.1).center(sx,sy).rect(aw+1.6,ah+1.6)
            .workplane(offset=1.0).rect(aw,ah).loft())
    s=s.cut(window).cut(bevel)
    # Four independent PCB supports, no loads applied to display glass.
    hx,hy=profile['hole_spacing'];top=profile['pcb_front_z']
    for x in [-hx/2,hx/2]:
        for y in [sy-hy/2,sy+hy/2]:
            s=s.union(cyl(2.85,top-t,x,y,t))
            s=s.cut(cyl(P['board_insert']['pilot']/2,3.05,x,y,top-3.0))
    for x,y in screw_centers(c):
        s=s.union(cyl(3.6,d-t,x,y,t))
        # Root touches side wall; small bridge makes support continuous.
        s=s.union(box(3.0,5.0,d-t,x=math.copysign(w/2-3.6,x),y=y,z=t))
        s=s.cut(cyl(1.6,d-t,x,y,t+.1))
        s=s.cut(cyl(P['case_insert']['pilot']/2,5.1,x,y,d-5))
    # USB opening ends at split line: printed upright without a bridge.
    # Side names are from the user's view of the front: left is CAD +X.
    px=w/2 if profile['usb_side']=='left' else -w/2
    s=s.cut(box(8,P['port']['width'],P['port']['height']+1,px,profile['usb_y'],P['port']['bottom_z']))
    s=s.cut(branding(.65).translate((0,0,-.05)))
    return s.clean()

def lid(profile):
    c=case_for(profile);w,h,d,t=c['width'],c['height'],c['front_depth'],c['lid_thickness']
    # Exterior face is at +Z; print flipped so it rests on the bed.
    s=rr(w,h,c['radius'],d,t).edges('not |Z').fillet(.6)
    for x,y in screw_centers(c):
        s=s.cut(cyl(1.65,t+.5,x,y,d-.1))
        s=s.cut(cyl(3.0,2.05,x,y,d+t-2.0))
    # Segmented registration ridge avoids the board posts and USB area.
    reg=rr(w-5.3,h-5.3,c['radius']-2.65,d-1.4,1.5)
    reg=reg.cut(rr(w-8.1,h-8.1,c['radius']-4.05,d-1.5,1.7))
    for x,y in screw_centers(c):
        reg=reg.cut(cyl(5.3,2,x,y,d-1.5))
    px=w/2 if profile['usb_side']=='left' else -w/2
    reg=reg.cut(box(12,P['port']['width']+3,2,px,profile['usb_y'],d-1.5))
    s=s.union(reg)
    # Rear service hatch is location-independent for BOOT/RESET and SD.
    opening=rr(65,29,2,d-.2,t+.4,0,5)
    s=s.cut(opening)
    # Hatch screw bosses in rear cover, M2.5 inserts, fitted from inside.
    for x in [-36.5,36.5]:
        s=s.union(cyl(3.1,3.2,x,5,d-3.0))
        s=s.cut(cyl(1.6,6.3,x,5,d-3.05))
    # Small ventilation ports below hatch.
    for x in [-19,-9.5,0,9.5,19]:
        s=s.cut(rr(5.8,2.0,.9,d-.1,t+.2,x,-21))
    return s.clean()

def hatch():
    c=P['case'];z=c['depth']
    # Plate on exterior, pilot lip enters service window with 0.25 mm/side clearance.
    s=rr(80,36,3,z,2.0,0,5)
    s=s.union(rr(64.5,28.5,1.7,z-1.3,1.4,0,5))
    # Core cleared to leave space for components and a 2 mm continuous plate.
    s=s.cut(rr(60,24,1.5,z-1.4,1.5,0,5))
    for x in [-36.5,36.5]:
        s=s.cut(cyl(1.4,2.3,x,5,z-.1))
        s=s.cut(cyl(2.65,1.0,x,5,z+1.05))
    for y in [-3,5,13]:
        for x in [-19,-9.5,0,9.5,19]:
            s=s.cut(rr(6,1.8,.85,z-1.4,3.6,x,y))
    return s.clean()

def transform_device(s,profile=None):
    # Front exterior normal is -Z. Rx(180-angle), not Rx(angle), points it
    # toward the user (+Y) AND upward (+Z). Local +Y remains screen-up.
    return s.rotate((0,0,0),(1,0,0),180-P['stand']['angle_degrees']).translate((0,device_offset_y(profile),device_height(profile)))

def device_height(profile=None):
    a=math.radians(P['stand']['angle_degrees'])
    c=case_for(profile)
    return c['height']/2*math.sin(a)+c['depth']*math.cos(a)+P['stand']['rear_bottom_height']

def device_offset_y(profile=None):
    # Keep both case sizes seated at precisely the same lower front edge.
    return (P['case']['height']-case_for(profile)['height'])/2*math.cos(math.radians(P['stand']['angle_degrees']))

def stand():
    st=P['stand'];c=P['case'];gap=st['clearance']
    s=rr(st['width'],st['depth'],7,0,st['base_thickness'],0,st['base_center_y']).edges('not |Z').fillet(.8)
    # Two independent narrow cradles leave an open rear and centre.
    # The backrest rises behind the case; the front stops end below the brand.
    for x in st['rib_centers_x']:
        rib=(cq.Workplane('YZ').workplane(offset=x-st['rib_width']/2)
             .polyline([(-38,3.4),(-26,st['height']),(16,19),(21,3.4)])
             .close().extrude(st['rib_width']))
        s=s.union(rib)
    cut=box(c['width']+4,c['height']+8,c['depth']+2*gap,0,4,-gap)
    s=s.cut(transform_device(cut))
    # Recesses for four 10 mm x 1.5 mm adhesive rubber feet.
    for x in [-32,32]:
        for y in [-33,13]: s=s.cut(cyl(5.1,1.1,x,y,-.1))
    # Rear cable valley, behind device, no sharp cable bend.
    s=s.cut(box(10,13,8,0,-42,0))
    return s.clean()

def spacer(h):
    return cq.Workplane('XY').circle(2.8).circle(1.4).extrude(h)

def fit_check(profile):
    pw,ph,pt=profile['pcb'];sy=P['screen_center'][1]
    s=rr(pw+7,ph+7,3,0,1.6,0,sy)
    # Large open frame verifies LCD position and board hole spacing cheaply.
    aw,ah=profile['window']
    s=s.cut(rr(aw,ah,.55,-.1,2,0,sy))
    hx,hy=profile['hole_spacing']
    for x in [-hx/2,hx/2]:
        for y in [sy-hy/2,sy+hy/2]:
            s=s.union(cyl(2.8,5,x,y,1.6))
            s=s.cut(cyl(1.4,6.8,x,y,-.1))
    return s.clean()

def bed(s):
    b=s.val().BoundingBox()
    return s.translate((-b.xmin,-b.ymin,-b.zmin))

def flipped(s): return s.rotate((0,0,0),(1,0,0),180)

stats={}
meshes={}
def export(name,s,flip_for_print=False,assembly=True):
    oriented=flipped(s) if flip_for_print else s
    bb=oriented.val().BoundingBox()
    print_origin=[bb.xmin,bb.ymin,bb.zmin]
    print_s=bed(oriented)
    cq.exporters.export(print_s, str(OUT/(name+'.stl')), tolerance=.035,angularTolerance=.12)
    m=trimesh.load(OUT/(name+'.stl'),force='mesh')
    m.remove_unreferenced_vertices()
    assert s.val().isValid(), f'{name}: invalid CAD'
    assert m.is_watertight, f'{name}: open STL'
    assert m.is_winding_consistent, f'{name}: inconsistent normals'
    assert m.volume>0, f'{name}: negative volume'
    stats[name]={'bbox_mm':m.extents.round(3).tolist(),'volume_cm3':round(m.volume/1000,3),
                 'watertight':bool(m.is_watertight),'shells':len(m.split()),'triangles':len(m.faces),
                 'print_origin_mm':print_origin,'print_flip_x':flip_for_print}
    if name!='Brand_inlay_optional': assert stats[name]['shells']==1, f'{name}: disconnected solid'
    if assembly: cq.exporters.export(s,str(SRC/(name+'.step')))
    meshes[name]=m
    print(name,stats[name],flush=True)
    return s

fronts={key:export('Front_'+key,front(profile)) for key,profile in P['profiles'].items()}
for key,profile in P['profiles'].items():export('Fit_check_'+key,fit_check(profile),assembly=False)
lids={key:export('Rear_cover_'+key,lid(profile),flip_for_print=True) for key,profile in P['profiles'].items()}
H=export('Service_hatch',hatch(),flip_for_print=True)
S=export('Desk_stand_65deg',stand())
for h in [.4,.8,1.2]:export('PCB_spacer_'+str(h).replace('.','p')+'mm',spacer(h),assembly=False)
# Optional true multi-material inserts (engraved front can also be paint-filled).
export('Brand_inlay_optional',BRAND,assembly=False)

for key,fr in fronts.items():
    profile=P['profiles'][key]
    ass=cq.Assembly(name='FlowSight_Desk_'+key)
    ass.add(transform_device(fr,profile),name='front',color=cq.Color(.09,.15,.18))
    ass.add(transform_device(lids[key],profile),name='rear_cover',color=cq.Color(.09,.15,.18))
    ass.add(transform_device(H,profile),name='service_hatch',color=cq.Color(.09,.15,.18))
    ass.add(transform_device(BRAND,profile),name='brand',color=cq.Color(.33,.81,.76))
    ass.add(S,name='desk_stand',color=cq.Color(.09,.15,.18))
    ass.export(str(ROOT/('FlowSight_Desk_'+key+'.step')))

# A standards-based 3MF print layout. No printer-specific speeds or temperature.
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
ET.register_namespace('',NS)
def make_3mf(profile):
    model=ET.Element('{'+NS+'}model',{'unit':'millimeter','xml:lang':'es-ES'})
    ET.SubElement(model,'{'+NS+'}metadata',{'name':'Title'}).text='FlowSight Desk - '+profile
    ET.SubElement(model,'{'+NS+'}metadata',{'name':'Description'}).text='Print at 100%. PETG, 0.20 mm, 4 walls. No supports. Separate 024 reference and 028 assemblies.'
    res=ET.SubElement(model,'{'+NS+'}resources');build=ET.SubElement(model,'{'+NS+'}build')
    c=case_for(P['profiles'][profile]);dx=c['width']+6;dy=c['height']+10
    placements=[('Front_'+profile,0,0),('Rear_cover_'+profile,dx,0),('Desk_stand_65deg',0,dy),('Service_hatch',dx,dy)]
    for oid,(name,tx,ty) in enumerate(placements,1):
        obj=ET.SubElement(res,'{'+NS+'}object',{'id':str(oid),'type':'model','name':name})
        mesh=ET.SubElement(obj,'{'+NS+'}mesh');verts=ET.SubElement(mesh,'{'+NS+'}vertices');tris=ET.SubElement(mesh,'{'+NS+'}triangles')
        m=meshes[name]
        for v in m.vertices: ET.SubElement(verts,'{'+NS+'}vertex',dict(zip(['x','y','z'],[f'{n:.6f}' for n in v])))
        for f in m.faces: ET.SubElement(tris,'{'+NS+'}triangle',dict(zip(['v1','v2','v3'],map(str,f))))
        ET.SubElement(build,'{'+NS+'}item',{'objectid':str(oid),'transform':f'1 0 0 0 1 0 0 0 1 {tx} {ty} 0'})
    with zipfile.ZipFile(OUT/('FlowSight_Desk_'+profile+'.3mf'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True))
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
for key in fronts:make_3mf(key)

# Geometry checks are recorded separately from sales copy.
checks={}
for key,fr in fronts.items():
    prof=P['profiles'][key];sx,sy=P['screen_center'];pw,ph,pt=prof['pcb']
    L=lids[key]
    pcb=box(pw,ph,pt,sx,sy,prof['pcb_front_z'])
    checks[key]={'pcb_body_overlap_mm3':round(fr.intersect(pcb).val().Volume(),6),
                 'case_lid_overlap_mm3':round(fr.intersect(L).val().Volume(),6),
                 'hatch_lid_overlap_mm3':round(H.intersect(L).val().Volume(),6),
                 'stand_case_overlap_mm3':round(transform_device(fr,prof).intersect(S).val().Volume(),6),
                 'stand_lid_overlap_mm3':round(transform_device(L,prof).intersect(S).val().Volume(),6),
                 'stand_hatch_overlap_mm3':round(transform_device(H,prof).intersect(S).val().Volume(),6)}
    assert all(v<.01 for v in checks[key].values()),checks[key]
a=math.radians(180-P['stand']['angle_degrees'])
front_normal=[0,math.sin(a),-math.cos(a)]
screen_up=[0,math.cos(a),math.sin(a)]
assert front_normal[1]>0 and front_normal[2]>0, 'Display must face the user and upward'
assert screen_up[2]>0 and screen_up[1]<0, 'Top of display must lean away from the user'
assembly_transforms={key:[[1,0,0,0],[0,math.cos(a),-math.sin(a),device_offset_y(prof)],
    [0,math.sin(a),math.cos(a),device_height(prof)],[0,0,0,1]] for key,prof in P['profiles'].items()}
brand_origin=stats['Brand_inlay_optional']['print_origin_mm']
inlay_positions={key:[round(b-f,6) for b,f in zip(brand_origin,stats['Front_'+key]['print_origin_mm'])] for key in fronts}
(ROOT/'geometry-verification.json').write_text(json.dumps({'revision':P['revision'],'parts':stats,'clearance_checks':checks,
    'orientation':{'front_normal':front_normal,'screen_up':screen_up,'screen_tilt_above_horizontal_degrees':P['stand']['angle_degrees'],
        'front_elevation_degrees':90-P['stand']['angle_degrees'],'design_to_assembly':assembly_transforms},
    'brand_inlay_position_in_front_print_mm':inlay_positions,
    'physical_validation':'Not performed; CS32 measurements unresolved'},indent=2),'utf-8')
print('All solids exported and verified.',flush=True)
