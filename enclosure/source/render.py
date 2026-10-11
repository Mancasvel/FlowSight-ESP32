"""Blender 4.3 renders of the exact printable meshes; demo display is synthetic."""
import bpy, math, json, os
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/'source/parameters.json').read_text())
OUT=ROOT/'preview';OUT.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.render.resolution_x=1800;scene.render.resolution_y=1500;scene.render.resolution_percentage=100
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

def load_stl(name,material,position_map):
    bpy.ops.wm.stl_import(filepath=str(ROOT/'print'/f'{name}.stl'))
    obj=bpy.context.object;obj.name=name
    for v in obj.data.vertices:v.co=Vector(position_map(v.co))
    obj.data.materials.append(material)
    for p in obj.data.polygons:p.use_smooth=False
    # Surface polish only; silhouette and holes remain from the printable mesh.
    mod=obj.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    return obj

def device(obj,explode=0):
    obj.rotation_euler[0]=math.radians(65)
    obj.location=(0,-math.sin(math.radians(65))*explode,39*math.sin(math.radians(65))+8+math.cos(math.radians(65))*explode)
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
    aw,ah=P['profiles'][profile]['active_area'];sy=6
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
    o=load_stl('Brand_inlay_optional',accent,lambda v:(v.x-26.6552129906,v.y-33.3061889251,v.z-.025))
    device(o,explode)

def hardware_lid():
    for x,y in P['case_screw_centers']:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=2.7,depth=1.5,location=(x,y,21.9))
        o=bpy.context.object;o.data.materials.append(metal)
        for v in o.data.vertices:v.co+=o.location
        o.location=(0,0,0);device(o)

def assemble(profile='CS32_024_reference',exploded=False):
    # Remove previous product objects; keep studio.
    for o in list(scene.objects):
        if o.get('product'):bpy.data.objects.remove(o,do_unlink=True)
    before=set(scene.objects)
    device(load_stl('Front_'+profile,body,lambda v:(v.x-52,v.y-39,v.z)))
    e=28 if exploded else 0
    device(load_stl('Rear_cover',body,lambda v:(v.x-52,39-v.y,23.2-v.z)),e)
    device(load_stl('Service_hatch',body,lambda v:(v.x-40,23-v.y,25.2-v.z)),e+20 if exploded else 0)
    load_stl('Desk_stand_65deg',body,lambda v:(v.x-45,v.y-45,v.z))
    brand();display(profile,9 if exploded else 0)
    if exploded:
        pr=P['profiles'][profile];o=cube('Reference board, illustrative',(*pr['pcb'][:2],1.6),(0,6,6.6),pcbmat)
        for v in o.data.vertices:v.co+=o.location
        o.location=(0,0,0);device(o,14)
    else:hardware_lid()
    for x in [-33,33]:
        for y in [-36,9]:cube('Rubber foot',(9,9,1.0),(x,y,.25),rubber,1)
    for o in set(scene.objects)-before:o['product']=True

floor=cube('Studio floor',(2000,2000,2),(0,0,-2),mat('Warm neutral',(.71,.72,.69),.65))
def area(name,loc,power,size,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,40))-ob.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-100,130,230),420000,170,(1,.93,.84))
area('Fill',(160,40,130),190000,150,(.78,.9,1))
area('Edge',(-110,-150,130),300000,90,(.75,1,.96))
camdata=bpy.data.cameras.new('Product camera');cam=bpy.data.objects.new('Product camera',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=170
def capture(name,loc,target,scale=170):
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=scale
    scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True)

assemble();capture('FlowSight-Desk-front.png',(-145,200,145),(0,-12,42),153)
capture('FlowSight-Desk-rear.png',(155,-205,145),(0,-12,42),158)
assemble(exploded=True);capture('FlowSight-Desk-exploded.png',(-170,225,180),(0,-22,46),200)
assemble('CYD_028');capture('FlowSight-Desk-CYD028.png',(-145,200,145),(0,-12,42),153)
print('CAD-derived previews complete.')
