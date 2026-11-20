"""Pythagorean theorem: two exact tilings + pure-translation animation.

Pillow cached RGBA layers -> in-memory raw RGB frames -> FFmpeg H.264.
Fail-closed preflight: symbolic, 25 randomized shapes, topology, labels, motion.
Run: python render_video.py --fps 24 --output pythagoras_verified.mp4
"""
from __future__ import annotations
import argparse
import json
import math
import subprocess
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from geometry_model import PythagoreanLayout
from verifier import run_preflight, sample_label_positions

W,H=1280,720
FPS_DEFAULT=24
DURATION=37.0
MODEL=PythagoreanLayout(3,4)
BASE=Path(__file__).resolve().parent
BG='#091625'; FG='#EAF3FF'; MUTED='#AFC0D7'; GREEN='#64DFC6'; ORANGE='#FFC676'

# Background and hold frames are cached. No outline/symbol is positioned by eye:
# each triangle label's anchor is the mathematical centroid of that same polygon.

def find_font():
    for f in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
              '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
              '/System/Library/Fonts/PingFang.ttc',
              'C:/Windows/Fonts/msyh.ttc']:
        if Path(f).exists(): return f
    import subprocess
    r=subprocess.run(['fc-match','-f','%{file}','Noto Sans CJK SC'],capture_output=True,text=True)
    if Path(r.stdout.strip()).exists(): return r.stdout.strip()
    raise FileNotFoundError('No CJK font found; install Noto Sans CJK SC')

FONT_PATH=find_font()
FONTS={n:ImageFont.truetype(FONT_PATH,n) for n in [17,19,20,22,24,26,28,30,32,34,38,42,46,53]}

def font(n):
    if n not in FONTS: FONTS[n]=ImageFont.truetype(FONT_PATH,n)
    return FONTS[n]

def ease(t):
    t=max(0.,min(1.,t))
    return t*t*(3-2*t)

class PythagorasRenderer:
    def __init__(self,model=MODEL):
        self.m=model
        self.ox=123
        self.oy=577
        self.scale=62.0*7.0/model.s # always fit same square size
        self.static=self.make_static()
        self.cache={}
        self.stats={'frames_reused':0,'frames_rendered':0,'base_cache':1}
        self.labels=sample_label_positions(model)

    def xy(self,p):
        return (round(self.ox+self.scale*p[0]),round(self.oy-self.scale*p[1]))
    def polygon(self,points):return [self.xy(q) for q in points]
    def text(self,d,at,txt,n=24,color=FG,anchor='la',stroke_width=0):
        d.text(at,txt,font=font(n),fill=color,anchor=anchor,
               stroke_width=stroke_width,stroke_fill='#081220')
    def make_static(self):
        im=Image.new('RGBA',(W,H),BG)
        d=ImageDraw.Draw(im)
        for x in range(40,W,40):d.line([(x,0),(x,H)],fill='#0E2030',width=1)
        for y in range(40,H,40):d.line([(0,y),(W,y)],fill='#0E2030',width=1)
        d.rounded_rectangle((53,20,1226,102),radius=21,fill='#152E45',outline='#2A536D',width=2)
        self.text(d,(82,43),'勾股定理',42,'#F5FCFF','la')
        self.text(d,(326,55),'用四块全等三角形证明',28,'#9FD6FF','la')
        d.rounded_rectangle((60,121,624,659),radius=18,fill='#12283D',outline='#315674',width=2)
        d.rounded_rectangle((647,121,1226,659),radius=18,fill='#14283D',outline='#315674',width=2)
        d.rounded_rectangle((75,677,1205,709),radius=13,fill='#11283A')
        self.text(d,(640,692),'逻辑验证：恒等式 / 全等 / 面积 / 无重叠 / 标签 / 连续性 / 视频逐帧',19,'#A5BCD3','mm')
        # outer square frame (board itself contains the geometry; no overlap with cards)
        d.rectangle((self.ox, self.oy-round(self.m.s*self.scale), self.ox+round(self.m.s*self.scale), self.oy),fill='#132943')
        return im

    def outer_and_dimensions(self,d,stage,progress=0):
        m=self.m
        o=self.polygon(m.outer)
        d.line(o+[o[0]],fill='#E5F3FF',width=4,joint='curve')
        # Outer side length, computed from endpoints, not manually placed.
        mx=(o[0][0]+o[1][0])/2
        self.text(d,(mx,620),'a + b',26,'#D5E7FA','mm')
        # a and b remain attached to the *physical* moving T1 legs.
        # A stale fixed-coordinate annotation would falsely label layout B.
        p = (m.a_pieces[0] if stage in ('intro','A') else
             m.b_pieces[0] if stage in ('B','finish') else
             m.pieces_at(ease(progress))[0])
        side_a=((p.right[0]+p.leg_a[0])/2, (p.right[1]+p.leg_a[1])/2-0.30)
        side_b=((p.right[0]+p.leg_b[0])/2-0.34, (p.right[1]+p.leg_b[1])/2)
        self.text(d,self.xy(side_a),'a',22,'#FFDA9A','mm')
        self.text(d,self.xy(side_b),'b',22,'#FFDA9A','mm')
        # Draw dimension bracket beside left board edge outside the big square.
        d.line([(self.ox-34,self.oy),(self.ox-34,self.oy-round(m.s*self.scale))],fill='#819DB6',width=2)
        for y in [self.oy,self.oy-round(m.s*self.scale)]:
            d.line([(self.ox-39,y),(self.ox-29,y)],fill='#819DB6',width=2)

    def draw_geometry(self,im,stage,progress=0):
        d=ImageDraw.Draw(im)
        m=self.m
        if stage in ['intro','A']:
            d.polygon(self.polygon(m.central_square),fill='#175963',outline='#58C3BE',width=3)
            pieces=m.a_pieces
        elif stage in ['B','finish']:
            d.polygon(self.polygon(m.square_a),fill='#224A70',outline='#7BAFD7',width=3)
            d.polygon(self.polygon(m.square_b),fill='#62502C',outline='#E7C26C',width=3)
            pieces=m.b_pieces
        else:
            pieces=m.pieces_at(ease(progress))
            # During motion the layout is NOT a partition. Draw the target as
            # thin guides only, so gaps/overlap are never passed off as a tiling.
            for sq in (m.square_a,m.square_b):
                d.line(self.polygon(sq)+[self.xy(sq[0])],fill='#36536A',width=2)
        for i,p in enumerate(pieces):
            color=p.color
            if stage=='intro' and i!=0: color='#3A5064'
            d.polygon(self.polygon(p.points()),fill=color,outline='#081A2D',width=3)
            # Visual identity marker, anchor computed from true piece centroid.
            pts=p.points();centroid=(sum(x for x,y in pts)/3,sum(y for x,y in pts)/3)
            self.text(d,self.xy(centroid),p.name,22,'#102137','mm')
        self.outer_and_dimensions(d,stage,progress)
        if stage in ('intro','A'):
            self.text(d,self.xy(self.labels['c²']),'c²',53,'#E8FFF6','mm')
            # Edge label c placed toward the interior of the actual c-length side.
            a,b,s=m.a,m.b,m.s
            pt=(a+b/2-0.45*a/m.c,a/2+0.45*b/m.c)
            self.text(d,self.xy(pt),'c',24,'#F8FCFF','mm')
            # right angle marker in middle square, based on actual edge vectors
            q=m.central_square
            p=q[1];v1=(q[0][0]-p[0],q[0][1]-p[1]);v2=(q[2][0]-p[0],q[2][1]-p[1]);size=.32
            v1=(v1[0]/m.c*size,v1[1]/m.c*size)
            v2=(v2[0]/m.c*size,v2[1]/m.c*size)
            marker=[(p[0]+v1[0],p[1]+v1[1]),(p[0]+v1[0]+v2[0],p[1]+v1[1]+v2[1]),(p[0]+v2[0],p[1]+v2[1])]
            d.line(self.polygon(marker),fill='#E4FFF5',width=2)
        elif stage in ('B','finish'):
            self.text(d,self.xy(self.labels['a²']),'a²',46,'#E9F9FF','mm')
            self.text(d,self.xy(self.labels['b²']),'b²',53,'#FFF2CD','mm')

    def info(self,im,stage):
        d=ImageDraw.Draw(im)
        left=680
        def heading(index,label):
            d.rounded_rectangle((left,146,1196,203),radius=12,fill='#21435E')
            self.text(d,(700,173),index+'  '+label,28,'#F4FBFF','lm')
        def line(y,s,col=FG,n=26):self.text(d,(702,y),s,n,col,'lm')
        def formula(y,s,n=34,col=ORANGE):
            d.rounded_rectangle((685,y-31,1193,y+40),radius=11,fill='#1C3B50',outline='#3E6D7B',width=1)
            self.text(d,(938,y+4),s,n,col,'mm')
        if stage=='intro':
            heading('01','认识直角三角形')
            line(242,'直角边分别是 a、b')
            line(286,'斜边长度记作 c')
            line(352,'复制成 4 块全等三角形',GREEN)
            line(394,'每块面积均为  ab / 2')
            formula(507,'目标：证明 c² = a² + b²',28)
            line(605,'图示比例：a=3，b=4（证明一般成立）',MUTED,20)
        elif stage=='A':
            heading('02','拼法 A：中间留下 c²')
            line(247,'外正方形边长：a+b')
            line(299,'中心四边均为 c，邻边垂直')
            line(350,'中心确实是正方形',GREEN)
            formula(447,'c² = (a+b)² − 4×ab/2',28)
            formula(541,'c² = (a+b)² − 2ab',34)
            line(611,'四个彩色三角形完全相同',MUTED,20)
        elif stage=='move':
            heading('03','只移动三角形，不改变它们')
            line(247,'T1、T2、T3、T4 全部保持形状')
            line(302,'仅做平移：无旋转、拉伸和剪切',GREEN,24)
            line(368,'每条边长度保持不变')
            line(411,'每个直角保持不变')
            formula(515,'每块面积一直是 ab/2',30)
            line(609,'注意：移动中途不是完整拼图',ORANGE,21)
        elif stage=='B':
            heading('04','拼法 B：留下两个正方形')
            line(250,'左下角：边长 a，面积 a²')
            line(302,'右上角：边长 b，面积 b²')
            line(363,'外正方形没有改变',GREEN)
            line(409,'四个三角形也没有改变')
            formula(529,'剩余面积 = a² + b²',34)
            line(610,'此时无重叠、无空洞：已重新拼满',MUTED,20)
        else:
            heading('05','比较面积：完成证明')
            line(238,'外正方形的面积总是 (a+b)²',FG,24)
            line(288,'四块三角形面积总是 2ab',FG,24)
            line(342,'同样的总面积减去同样的部分：',GREEN,23)
            line(391,'两种拼法剩下的面积必然相等')
            formula(492,'c² = a² + b²',46,GREEN)
            line(578,'证明对任意 a>0、b>0 成立',ORANGE,22)
            line(614,'证毕  ∎',FG,24)

    def stage_at(self,t):
        if t<3.5:return 'intro',0
        if t<11:return 'A',0
        if t<19:return 'move',(t-11)/8
        if t<27:return 'B',0
        return 'finish',0

    def frame(self,t):
        stage,p=self.stage_at(t)
        if stage!='move' and stage in self.cache:
            self.stats['frames_reused']+=1
            return self.cache[stage]
        im=self.static.copy()
        self.draw_geometry(im,stage,p)
        self.info(im,stage)
        rgb=im.convert('RGB')
        self.stats['frames_rendered']+=1
        if stage!='move':self.cache[stage]=rgb
        return rgb


def render(out, fps=FPS_DEFAULT, duration=DURATION, preflight=True):
    if preflight:
        checks=run_preflight(MODEL,ease)
        (BASE/'preflight.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False),encoding='utf8')
    out=Path(out)
    out.parent.mkdir(parents=True,exist_ok=True)
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo',
         '-pixel_format','rgb24','-video_size',f'{W}x{H}',
         '-framerate',str(fps),'-i','pipe:0','-an',
         '-c:v','libx264','-preset','veryfast','-crf','19',
         '-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
    r=PythagorasRenderer();start=time.perf_counter()
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for i in range(round(fps*duration)):
            im=r.frame(i/fps)
            proc.stdin.write(im.tobytes())
        proc.stdin.close()
        error=proc.stderr.read().decode('utf8','replace')
        code=proc.wait()
        if code!=0:raise RuntimeError(f'ffmpeg exited {code}: {error}')
    except Exception:
        proc.kill();proc.wait();raise
    elapsed=time.perf_counter()-start
    stats=dict(r.stats,elapsed_seconds=round(elapsed,3),output=str(out),fps=fps,frames=round(fps*duration),duration=duration)
    (BASE/'render_stats.json').write_text(json.dumps(stats,indent=2,ensure_ascii=False),encoding='utf8')
    return stats

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--fps',type=int,default=FPS_DEFAULT)
    p.add_argument('--output',default=str(BASE/'pythagoras_verified.mp4'))
    p.add_argument('--duration',type=float,default=DURATION)
    args=p.parse_args()
    print(json.dumps(render(args.output,args.fps,args.duration),indent=2,ensure_ascii=False))