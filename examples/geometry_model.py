"""Exact two-dissection model of the Pythagorean theorem.

Coordinates use mathematical x-right/y-up. All four physical triangle pieces
are translated only; they are not stretched, sheared or reflected.
"""
from dataclasses import dataclass
from math import hypot

@dataclass(frozen=True)
class Piece:
    name: str
    right: tuple[float,float]
    leg_a: tuple[float,float]
    leg_b: tuple[float,float]
    color: str

    def points(self):
        return (self.right, self.leg_a, self.leg_b)

    def move(self, dx, dy):
        def mv(p): return (p[0]+dx,p[1]+dy)
        return Piece(self.name,mv(self.right),mv(self.leg_a),mv(self.leg_b),self.color)

COLORS = ('#58C3F2','#EF9A67','#B6A0F6','#61D6B0')

@dataclass(frozen=True)
class PythagoreanLayout:
    a: float = 3.0
    b: float = 4.0

    @property
    def s(self): return self.a + self.b
    @property
    def c(self): return hypot(self.a,self.b)
    @property
    def outer(self):
        s=self.s
        return ((0,0),(s,0),(s,s),(0,s))
    @property
    def a_pieces(self):
        a,b,s=self.a,self.b,self.s
        return (
            Piece('T1',(0,0),(a,0),(0,b),COLORS[0]),
            Piece('T2',(s,0),(s,a),(a,0),COLORS[1]),
            Piece('T3',(s,s),(s-a,s),(s,s-b),COLORS[2]),
            Piece('T4',(0,s),(0,s-a),(b,s),COLORS[3]),
        )
    @property
    def translations(self):
        a,b=self.a,self.b
        return ((0,a),(0,0),(-b,0),(a,-b))
    @property
    def b_pieces(self):
        return tuple(p.move(*delta) for p,delta in zip(self.a_pieces,self.translations))
    def pieces_at(self, fraction):
        return tuple(p.move(dx*fraction,dy*fraction) for p,(dx,dy) in zip(self.a_pieces,self.translations))
    @property
    def central_square(self):
        a,b,s=self.a,self.b,self.s
        return ((a,0),(s,a),(b,s),(0,b))
    @property
    def square_a(self):
        a=self.a
        return ((0,0),(a,0),(a,a),(0,a))
    @property
    def square_b(self):
        a,s=self.a,self.s
        return ((a,a),(s,a),(s,s),(a,s))