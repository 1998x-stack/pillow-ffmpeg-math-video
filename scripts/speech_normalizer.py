"""Conservative Mandarin math-formula speech preprocessor.

This is a *reading aid*, never a mathematical equivalence proof. Unknown or
ambiguous syntax is rejected, rather than silently guessed. Use manually
reviewed spoken_text for proofs and high-risk mathematics.
"""
from __future__ import annotations
import re

WORDS = {"0":"零","1":"一","2":"二","3":"三","4":"四","5":"五","6":"六","7":"七","8":"八","9":"九"}
OPERATORS = {"+":"加","-":"减","=":"等于","*":"乘以","/":"除以", "<":"小于", ">":"大于"}
GREEK = {r"\pi":"派",r"\alpha":"阿尔法",r"\beta":"贝塔",r"\theta":"西塔",r"\Delta":"德尔塔"}
FUNC = {r"\sin":"正弦",r"\cos":"余弦",r"\tan":"正切",r"\ln":"自然对数"}

class MathSpeechError(ValueError):
    """An expression needs human narration instead of unsupported auto-TTS."""


def _number(token: str) -> str:
    """Read integer tokens; avoid treating numerals as independent digits."""
    n = int(token)
    if n < 0: return "负" + _number(str(-n))
    if n < 10: return WORDS[str(n)]
    if n < 20: return "十" + (WORDS[str(n % 10)] if n % 10 else "")
    if n < 100:
        return WORDS[str(n // 10)] + "十" + (WORDS[str(n % 10)] if n % 10 else "")
    if n < 1000:
        r = n % 100
        return WORDS[str(n // 100)] + "百" + ("零" + _number(str(r)) if 0 < r < 10 else _number(str(r)) if r else "")
    # Large integers must be authored as a custom educational script.
    raise MathSpeechError("numbers >= 1000 need a reviewed spoken phrase")


class _Parser:
    def __init__(self, raw: str):
        self.s = raw.strip().replace("−", "-").replace("×", "*").replace("÷", "/")
        self.i = 0
    def peek(self): return self.s[self.i:self.i+1]
    def item(self) -> str:
        ch=self.peek()
        if not ch: raise MathSpeechError("unexpected end")
        if ch=='{':
            self.i+=1
            inner=self.expr('}')
            if self.peek()!='}': raise MathSpeechError("missing closing brace")
            self.i+=1
            return inner
        if ch=='\\':
            m=re.match(r'\\[A-Za-z]+',self.s[self.i:])
            if not m: raise MathSpeechError(f"bad LaTeX command at {self.i}")
            command=m.group();self.i+=len(command)
            if command==r'\frac':
                num=self._group();den=self._group()
                return f'（{num}）除以（{den}）'
            if command==r'\sqrt':
                rad=self._group();return f'根号下（{rad}）'
            if command in GREEK:return GREEK[command]
            if command in FUNC:return FUNC[command]
            if command in (r'\left',r'\right'):
                return self.item()
            raise MathSpeechError(f'unsupported LaTeX command: {command}')
        if ch.isdigit():
            m=re.match(r'\d+(?:\.\d+)?',self.s[self.i:]);tok=m.group();self.i+=len(tok)
            if '.' in tok:
                before,after=tok.split('.')
                return _number(before)+'点'+''.join(WORDS[d] for d in after)
            return _number(tok)
        if ch.isalpha():
            m=re.match(r'[A-Za-z]+',self.s[self.i:]);self.i+=len(m.group());return m.group()
        if ch in '(（':self.i+=1;return '括号内'
        if ch in ')）':self.i+=1;return '括号结束'
        if ch in OPERATORS:
            self.i+=1
            if ch=='-' and (self.i==1 or self.s[self.i-2] in '({=,+-*/'):
                return '负'
            return OPERATORS[ch]
        if ch in '^_':
            self.i+=1
            power=self.item()
            if ch=='_':return '下标'+power
            if power=='二':return '的平方'
            if power=='三':return '的立方'
            return '的'+power+'次方'
        if ch in ' ,，；;':self.i+=1;return ' '
        raise MathSpeechError(f'unsupported character: {ch!r}')
    def _group(self):
        if self.peek()!='{':raise MathSpeechError('expected braced LaTeX argument')
        return self.item()
    def expr(self, stop=''):
        parts=[]
        while self.i < len(self.s) and self.peek()!=stop:
            parts.append(self.item())
        return ''.join(parts).strip()


def normalize_math(expr: str) -> str:
    if not isinstance(expr,str) or not expr.strip():raise MathSpeechError('empty math expression')
    p=_Parser(expr)
    result=p.expr()
    if p.i != len(p.s):raise MathSpeechError('unconsumed braces')
    return result


def require_reviewed_narration(scene: dict) -> str:
    """Claims require an explicitly authored and reviewed spoken_text.

    An auto-normalized formula is an aid only, never a substitute for checking
    that a spoken claim is equivalent to the validated math claim.
    """
    spoken=scene.get('spoken_text')
    if not isinstance(spoken,str) or not spoken.strip():
        raise MathSpeechError('spoken_text required: never feed raw LaTeX to a TTS provider')
    if re.search(r'\\[A-Za-z]+|\$[^$]+\$',spoken):
        raise MathSpeechError('raw LaTeX found in spoken_text')
    if not scene.get('claim_id'):
        raise MathSpeechError('claim_id is required for proof-to-speech traceability')
    return spoken.strip()