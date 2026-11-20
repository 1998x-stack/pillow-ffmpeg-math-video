"""Postflight verification of encoded MP4, with reproducible random screenshots.

The sampled PNGs come from ffmpeg-decoded MP4, NOT from Pillow's in-memory
frames. Thus this checks the actual delivered video, including encoding.
"""
import argparse
import io
import math
import json
import random
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, Point
from geometry_model import PythagoreanLayout
from render_video import PythagorasRenderer, FONT_PATH, font, W, H, DURATION
from verifier import require

BASE=Path(__file__).resolve().parent
PER_STAGE={'intro':(.45,3.0),'A':(4.0,10.4),'move':(12.1,17.8),'B':(19.7,26.3),'finish':(28.0,35.9)}
EXPECTED_HOLES={'A':[('c²','#175963')],
                'B':[('a²','#224A70'),('b²','#62502C')],
                'finish':[('a²','#224A70'),('b²','#62502C')]}

def sample_times(seed=20261120,per_stage=2):
    rng=random.Random(seed)
    frames=[]
    for stage,(lo,hi) in PER_STAGE.items():
        if stage=='move' and per_stage>=2:
            # Stratified randomness is mandatory for this stage: the two
            # snapshots must show *different* positions, not just two early frames.
            frames.append((stage,rng.uniform(12.0,14.2)))
            frames.append((stage,rng.uniform(15.6,18.3)))
            frames.extend((stage,rng.uniform(lo,hi)) for _ in range(per_stage-2))
        else:
            frames.extend((stage,rng.uniform(lo,hi)) for _ in range(per_stage))
    return frames

def extract_png(video,t,output):
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-ss',f'{t:.5f}',
         '-i',str(video),'-frames:v','1','-f','image2pipe','-vcodec','png','pipe:1']
    res=subprocess.run(cmd,check=True,capture_output=True,timeout=35)
    im=Image.open(io.BytesIO(res.stdout)).convert('RGB')
    im.save(output)
    return im

def rgb(s):
    s=s.lstrip('#')
    return tuple(int(s[i:i+2],16) for i in (0,2,4))

def difference(a,b):return max(abs(x-y) for x,y in zip(a,b))

def safe_triangle_sample(piece):
    r,pa,pb=piece.points()
    return (r[0]*.72+pa[0]*.14+pb[0]*.14,r[1]*.72+pa[1]*.14+pb[1]*.14)

def safe_hole_sample(m,label):
    if label=='c²':
        # away from center c² label and corner marker
        q=m.central_square
        w=(.65,.15,.10,.10)
        return sum(p[0]*z for p,z in zip(q,w)),sum(p[1]*z for p,z in zip(q,w))
    if label=='a²':return (.68*m.a,.73*m.a)
    if label=='b²':return (m.a+.30*m.b,m.a+.76*m.b)
    raise ValueError(label)

def validate_encoded_frame(im,stage,renderer,threshold=52):
    checks=[]
    m=renderer.m
    if stage in ('A','B','finish'):
        pieces=m.a_pieces if stage=='A' else m.b_pieces
        for p in pieces:
            x,y=renderer.xy(safe_triangle_sample(p))
            actual=im.getpixel((x,y))
            expect=rgb(p.color)
            diff=difference(actual,expect)
            require(diff<=threshold,f'{stage}: piece {p.name} color mismatch at {(x,y)}: {actual} expected {expect} diff={diff}')
            checks.append({'object':p.name,'pixel':[x,y],'max_rgb_delta':diff,'passed':True})
        for label,color in EXPECTED_HOLES[stage]:
            x,y=renderer.xy(safe_hole_sample(m,label))
            actual=im.getpixel((x,y));expected=rgb(color)
            diff=difference(actual,expected)
            require(diff<=threshold,f'{stage}: square {label} incorrect at {(x,y)}: {actual} expected {expected} diff={diff}')
            checks.append({'object':label,'pixel':[x,y],'max_rgb_delta':diff,'passed':True})
    return checks

def region_sweep_check(im,stage,renderer,seed=20261120,per_region=24):
    """Independent geometry-mask-vs-decoded-pixels test on random safe interior samples.

    Exclude labels and anti-aliased edges so a legitimate glyph/outline is
    not falsely mistaken for a geometry placement error.
    """
    if stage not in ('A','B','finish'):return {'sampled_pixels':0,'status':'not_applicable'}
    rng=random.Random(seed+{'A':1,'B':2,'finish':3}[stage])
    m=renderer.m
    parts=m.a_pieces if stage=='A' else m.b_pieces
    regions=[(p.name,Polygon(p.points()),p.color) for p in parts]
    if stage=='A':
        regions.append(('c²',Polygon(m.central_square),'#175963'))
    else:
        regions.append(('a²',Polygon(m.square_a),'#224A70'))
        regions.append(('b²',Polygon(m.square_b),'#62502C'))
    label_locs=renderer.labels
    exclusions=[label_locs[p.name+('A' if stage=='A' else 'B')] for p in parts]
    exclusions+= [label_locs['c²'] if stage=='A' else label_locs['a²'],label_locs['b²']] if stage!='A' else [label_locs['c²']]
    if stage=='A':
        a,b=m.a,m.b
        exclusions.append((a+b/2-0.45*a/m.c,a/2+0.45*b/m.c))
    # Numerical a/b labels may sit within an adjacent square; their anchors
    # follow T1's physical edges, so exclude nearby text zones too.
    t1=parts[0]
    exclusions.append(((t1.right[0]+t1.leg_a[0])/2,(t1.right[1]+t1.leg_a[1])/2-.3))
    exclusions.append(((t1.right[0]+t1.leg_b[0])/2-.34,(t1.right[1]+t1.leg_b[1])/2))
    n=0
    stats=[]
    for name,region,color in regions:
        interior=region.buffer(-.33)
        require(not interior.is_empty,f'{name} has no safe interior')
        lo_x,lo_y,hi_x,hi_y=interior.bounds
        found=0;attempts=0;max_diff=0
        while found<per_region and attempts<10000:
            attempts+=1
            px=rng.uniform(lo_x,hi_x);py=rng.uniform(lo_y,hi_y)
            if not interior.covers(Point(px,py)):continue
            if any(math.hypot(px-ex,py-ey)<.83 for ex,ey in exclusions):continue
            x,y=renderer.xy((px,py))
            delta=difference(im.getpixel((x,y)),rgb(color))
            require(delta<=52,f'full-area pixel-mismatch for {name} at {(x,y)} diff {delta}')
            max_diff=max(max_diff,delta)
            found+=1;n+=1
        require(found==per_region,f'{name}: insufficient safe samples for image validator')
        stats.append({'region':name,'pixels':found,'max_channel_diff':max_diff})
    return {'sampled_pixels':n,'region_samples':stats,'status':'pass'}

def verify_video_metadata(video):
    cp=subprocess.run(['ffprobe','-v','error','-show_entries',
         'stream=codec_name,width,height,avg_frame_rate,nb_frames:format=duration,size',
         '-of','json',str(video)],capture_output=True,text=True,check=True)
    data=json.loads(cp.stdout)
    s=data['streams'][0]
    require((s['width'],s['height'])==(W,H),'video size mismatch')
    require(s['codec_name']=='h264','video codec mismatch')
    require(abs(float(data['format']['duration'])-DURATION)<0.08,'video duration mismatch')
    fps=float(s['avg_frame_rate'].split('/')[0])/float(s['avg_frame_rate'].split('/')[1])
    require(int(s['nb_frames'])==round(fps*DURATION),'frame count mismatch')
    return {'codec':s['codec_name'],'width':W,'height':H,'fps':fps,'frames':int(s['nb_frames']),
            'duration':float(data['format']['duration']),'bytes':int(data['format']['size']),'status':'pass'}

def make_contact_sheet(entries,out):
    cols=2
    thumb_w=590
    thumb_h=332
    title_h=48
    cell_h=thumb_h+title_h+16
    rows=(len(entries)+cols-1)//cols
    sheet=Image.new('RGB',(cols*thumb_w+24,rows*cell_h+20),'#071523')
    d=ImageDraw.Draw(sheet)
    for i,entry in enumerate(entries):
        im=Image.open(entry['file']).convert('RGB')
        im.thumbnail((thumb_w-18,thumb_h))
        x=12+(i%cols)*thumb_w
        y=12+(i//cols)*cell_h
        sheet.paste(im,(x,y))
        txt=f"{entry['stage']}   t={entry['t']:.2f}s   像素验证 {'通过' if entry['pixel_status']=='pass' else '未适用'}"
        d.text((x+8,y+thumb_h+9),txt,font=font(20),fill='#E2F0FF')
    sheet.save(out)

def main(video,seed=20261120):
    video=Path(video)
    require(video.exists(),'MP4 missing')
    meta=verify_video_metadata(video)
    renderer=PythagorasRenderer()
    screenshots=BASE/'screenshots';screenshots.mkdir(exist_ok=True)
    reports=[]
    for idx,(stage,t) in enumerate(sample_times(seed)):
        output=screenshots/f'random_{idx+1:02d}_{stage}_{t:.2f}s.png'
        image=extract_png(video,t,output)
        require(image.size==(W,H),'decoded frame size mismatch')
        checks=validate_encoded_frame(image,stage,renderer)
        sweep=region_sweep_check(image,stage,renderer)
        reports.append({'index':idx+1,'stage':stage,'t':round(t,4),'file':str(output),
                        'pixel_status':'pass' if checks else 'not_applicable',
                        'pixel_checks':checks,'region_sweep':sweep})
    # Motion image difference: two random mid-flight frames must differ.
    moving=[p for p in reports if p['stage']=='move']
    a=Image.open(moving[0]['file']);b=Image.open(moving[1]['file'])
    import PIL.ImageChops
    bb=PIL.ImageChops.difference(a,b).getbbox()
    require(bb is not None,'moving frames appear identical')
    out=BASE/'random_screenshot_contact_sheet.png'
    make_contact_sheet(reports,out)
    result={'seed':seed,'video':meta,'screenshots':reports,
            'pixel_checks_passed':sum(len(e['pixel_checks']) for e in reports),
            'region_samples_passed':sum(e['region_sweep']['sampled_pixels'] for e in reports),
            'motion_frames_differ':True,'contact_sheet':str(out),'status':'pass'}
    (BASE/'visual_verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8')
    print(json.dumps({'status':'pass','screenshots':len(reports),
            'pixel_checks':result['pixel_checks_passed'],
            'region_samples':result['region_samples_passed'],'contact_sheet':str(out),'meta':meta},ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('video',nargs='?',default=str(BASE/'pythagoras_verified.mp4'))
    p.add_argument('--seed',type=int,default=20261120)
    args=p.parse_args()
    main(args.video,args.seed)