"""Blender 4.3 renders of the exact printable meshes; demo display is synthetic."""
import bpy, math, json, os
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/'source/parameters.json').read_text())
G=json.loads((ROOT/'geometry-verification.json').read_text())
DEVICE=Matrix(G['orientation']['design_to_assembly']['CS32_024_reference'])
EXPLODE_LIFT=0
OUT=ROOT/'preview';OUT.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=48
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    if any(d.type=='OPTIX' for d in prefs.devices):scene.cycles.device='GPU'
except Exception:
    pass  # CPU rendering remains available on machines without an NVIDIA GPU.
scene.cycles.use_denoising=True
scene.render.resolution_x=1800;scene.render.resolution_y=1500;scene.render.resolution_percentage=int(os.environ.get('FS_RENDER_PERCENT','100'))
scene.world.color=(.15,.15,.15)
scene.view_settings.view_transform='AgX'

def mat(name,color,rough=.4,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1)
    b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
    return m
body=mat('Graphite PETG',(.045,.073,.089),.33)
accent=mat('FlowSight turquoise',(.12,.67,.61),.29,.05)
black=mat('Screen bezel',(.005,.012,.015),.3)
rubber=mat('Rubber feet',(.02,.023,.025),.7)
metal=mat('Hardware',(.18,.22,.25),.23,.7)
pcbmat=mat('Reference PCB',(.52,.32,.015),.55)

def load_stl(name,material):
    bpy.ops.wm.stl_import(filepath=str(ROOT/'print'/f'{name}.stl'))
    obj=bpy.context.object;obj.name=name
    # Reconstruct the original CAD coordinates from recorded export metadata.
    # This also handles the flipped rear parts and the exact branding origin.
    meta=G['parts'][name];origin=Vector(meta['print_origin_mm'])
    for v in obj.data.vertices:
        v.co+=origin
        if meta['print_flip_x']:v.co.y=-v.co.y;v.co.z=-v.co.z
    obj.data.materials.append(material)
    for p in obj.data.polygons:p.use_smooth=False
    # Surface polish only; silhouette and holes remain from the printable mesh.
    mod=obj.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    return obj

def device(obj,explode=0):
    obj.matrix_world=Matrix.Translation((0,0,EXPLODE_LIFT)) @ DEVICE @ Matrix.Translation((0,0,explode))
    return obj

def cube(name,dims,loc,material, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material)
    if bevel:
        m=o.modifiers.new('Corner radius','BEVEL');m.width=bevel;m.segments=4
        o.modifiers.new('Normals','WEIGHTED_NORMAL')
    return o

screenmat=bpy.data.materials.new('Firmware-rendered demo snapshot');screenmat.use_nodes=True
n=screenmat.node_tree.nodes;n.clear();tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'source/screen-demo.png'))
em=n.new('ShaderNodeEmission');em.inputs['Strength'].default_value=.45
out=n.new('ShaderNodeOutputMaterial');screenmat.node_tree.links.new(tex.outputs['Color'],em.inputs['Color']);screenmat.node_tree.links.new(em.outputs[0],out.inputs[0])

def display(profile,explode=0):
    aw,ah=P['profiles'][profile]['active_area'];sx,sy=P['screen_center']
    bezel=cube('Illustrative LCD - not printed',(aw+4,ah+3,1.5),(0,sy,3.0),black,1)
    # Bake device-local box position into vertex coordinates before transform.
    for v in bezel.data.vertices:v.co+=bezel.location
    bezel.location=(0,0,0);device(bezel,explode)
    verts=[(-aw/2,sy-ah/2,2.15),(aw/2,sy-ah/2,2.15),(aw/2,sy+ah/2,2.15),(-aw/2,sy+ah/2,2.15)]
    mesh=bpy.data.meshes.new('LCD');mesh.from_pydata(verts,[],[(0,3,2,1)]);mesh.update()
    o=bpy.data.objects.new('Display demo (not a live photograph)',mesh);scene.collection.objects.link(o);o.data.materials.append(screenmat)
    uv=mesh.uv_layers.new();uvs=[(1,0),(1,1),(0,1),(0,0)]
    for loop,xy in zip(mesh.loops,uvs):uv.data[loop.index].uv=xy
    device(o,explode)

def brand(explode=0):
    # Logo and lettering exported from CAD, fills the 0.6 mm recess exactly.
    # Brand is mirrored in CAD so it reads from the exterior (-Z).
    o=load_stl('Brand_inlay_optional',accent)
    for v in o.data.vertices:v.co.z-=.025
    device(o,explode)

def hardware_lid(profile):
    c={**P['case'],**P['profiles'][profile].get('case',{})};ox,oy=P['case_screw_edge_offsets']
    for x,y in [(x,y) for x in [ox-c['width']/2,c['width']/2-ox] for y in [oy-c['height']/2,c['height']/2-oy]]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=2.7,depth=1.5,location=(x,y,P['case']['depth']-1.3))
        o=bpy.context.object;o.data.materials.append(metal)
        for v in o.data.vertices:v.co+=o.location
        o.location=(0,0,0);device(o)

def assemble(profile='CS32_024_reference',exploded=False):
    global DEVICE,EXPLODE_LIFT
    DEVICE=Matrix(G['orientation']['design_to_assembly'][profile])
    EXPLODE_LIFT=20 if exploded else 0
    # Remove previous product objects; keep studio.
    for o in list(scene.objects):
        if o.get('product'):bpy.data.objects.remove(o,do_unlink=True)
    before=set(scene.objects)
    device(load_stl('Front_'+profile,body))
    e=48 if exploded else 0
    device(load_stl('Rear_cover_'+profile,body),e)
    device(load_stl('Service_hatch',body),e+24 if exploded else 0)
    load_stl('Desk_stand_65deg',body)
    brand();display(profile,18 if exploded else 0)
    if exploded:
        pr=P['profiles'][profile];o=cube('Reference board, illustrative',(*pr['pcb'][:2],1.6),(*P['screen_center'],6.6),pcbmat)
        for v in o.data.vertices:v.co+=o.location
        o.location=(0,0,0);device(o,26)
    else:hardware_lid(profile)
    for x in [-32,32]:
        for y in [-33,13]:cube('Rubber foot',(9,9,1.5),(x,y,.05),rubber,1)
    for o in set(scene.objects)-before:o['product']=True

floor=cube('Studio floor',(20000,20000,2),(0,0,-2),mat('Warm neutral',(.71,.72,.69),.65))
def area(name,loc,power,size,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,40))-ob.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-100,130,230),420000,170,(1,.93,.84))
area('Fill',(160,40,130),190000,150,(.78,.9,1))
area('Edge',(-110,-150,130),300000,90,(.75,1,.96))
camdata=bpy.data.cameras.new('Product camera');cam=bpy.data.objects.new('Product camera',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=170
camdata.clip_end=50000
def capture(name,loc,target,scale=170,projection='PERSP'):
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=scale
    camdata.type=projection;camdata.sensor_fit='HORIZONTAL';camdata.sensor_width=36
    # Long-lens product perspective; keep framing constant without wide-angle distortion.
    camdata.lens=(Vector(loc)-Vector(target)).length*camdata.sensor_width/scale
    scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True)

views=set(os.environ.get('FS_RENDER_VIEWS','front,left,rear,side,exploded,cyd').split(','))
assemble()
if 'front' in views:capture('FlowSight-Desk-front.png',(0,360,216),(0,-9,43),143)
if 'left' in views:capture('FlowSight-Desk-left.png',(95,350,205),(0,-9,43),146)
if 'rear' in views:capture('FlowSight-Desk-rear.png',(150,-210,140),(0,-12,44),151)
if 'side' in views:capture('FlowSight-Desk-side.png',(260,0,56),(0,-10,44),133,projection='ORTHO')
if 'exploded' in views:
    assemble(exploded=True);capture('FlowSight-Desk-exploded.png',(-240,110,180),(0,-38,50),215)
if 'cyd' in views:
    assemble('CYD_028');capture('FlowSight-Desk-CYD028.png',(0,360,216),(0,-9,45),146)
print('CAD-derived previews complete.')
