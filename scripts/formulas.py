"""Optional Matplotlib mathtext-to-Pillow sprites; semantic token transforms.

Mathtext is a SUBSET of LaTeX. Token matching by id is an explicit authoring
contract, not automatic symbolic proof or full glyph-to-glyph TeX morphing.
"""
from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
from functools import lru_cache
from PIL import Image
from .pillow_draw import point_lerp, smoothstep


@lru_cache(maxsize=256)
def math_sprite(math_expr:str,fontsize:int=48,dpi:int=180,color:str="#FFFFFF")->Image.Image:
    if not math_expr or len(math_expr)>2000 or fontsize<1:
        raise ValueError("invalid math expression")
    from matplotlib.mathtext import math_to_image
    from matplotlib.font_manager import FontProperties
    out=BytesIO()
    expr=math_expr if math_expr.startswith('$') and math_expr.endswith('$') else '$'+math_expr+'$'
    math_to_image(expr,out,prop=FontProperties(size=fontsize),dpi=dpi,format='png',color=color)
    out.seek(0)
    return Image.open(out).convert("RGBA").copy()


@dataclass(frozen=True)
class FormulaToken:
    id:str
    latex:str
    position:tuple[float,float]


def matching_token_states(source:list[FormulaToken],target:list[FormulaToken],progress:float):
    """Yield (id,latex,position,alpha) tuples. IDs must be unique per stage.
    For duplication/deletion use unique IDs and fades, not ambiguous match.
    """
    ids_s=[x.id for x in source];ids_t=[x.id for x in target]
    if len(ids_s)!=len(set(ids_s)) or len(ids_t)!=len(set(ids_t)):
        raise ValueError("duplicate token id in same formula state")
    u=smoothstep(progress)
    src={t.id:t for t in source};dst={t.id:t for t in target}
    result=[]
    for id_ in dict.fromkeys(ids_s+ids_t):
        a=src.get(id_); b=dst.get(id_)
        if a and b:
            if a.latex!=b.latex:raise ValueError(f"matched id changed meaning: {id_}")
            result.append((id_,a.latex,point_lerp(a.position,b.position,u),255))
        elif a:result.append((id_,a.latex,a.position,round(255*(1-u))))
        else:result.append((id_,b.latex,b.position,round(255*u)))
    return result


def paste_math(canvas:Image.Image,sprite:Image.Image,at:tuple[int,int],opacity:int=255):
    if canvas.mode!="RGBA" or sprite.mode!="RGBA":raise ValueError("expected RGBA")
    if not 0<=opacity<=255:raise ValueError("opacity out of range")
    layer=sprite.copy()
    if opacity!=255:layer.putalpha(layer.getchannel('A').point(lambda x:x*opacity//255))
    canvas.alpha_composite(layer,dest=(round(at[0]),round(at[1])))