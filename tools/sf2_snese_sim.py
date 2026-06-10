#!/usr/bin/env python3
"""SNES SoundFont 9乐器 C4 试听 WAV 生成"""
import warnings; warnings.filterwarnings('ignore')
from sf2utils.sf2parse import Sf2File
import struct, os, wave

TARGET = 17640
SF2 = 'D:/working/vscode-projects/Reference_Project/STC-MCU/31_Minutos_SNES_Soundfont__Fanmade_.sf2'
OUT = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sf2_extract/snes_sim'

def resample(pcm, sr, dst):
    if sr == dst: return list(pcm)
    r = sr/dst; n = int(len(pcm)/r); o = []
    for j in range(n):
        p = j*r; i = int(p); f = p-i
        o.append(int(pcm[i]*(1-f)+pcm[i+1]*f) if i+1<len(pcm) else int(pcm[min(i,len(pcm)-1)]))
    return o

def fix_loop(pcm, ls, le, rng=200):
    t = pcm[le]; bi=ls; bd=abs(pcm[ls]-t)
    for j in range(max(0,ls-rng),min(len(pcm),ls+rng)):
        d=abs(pcm[j]-t)
        if d<bd: bd=d; bi=j
    return bi

class Voice:
    def __init__(self, pcm, ls, le, op):
        self.pcm=pcm; self.ls=ls; self.le=le; self.op=op; self.pos=0.0; self.act=True
    def note(self, mid):
        s=mid-self.op; self.r=2.0**(s/12.0); self.pos=0.0
    def tick(self):
        if not self.act: return 0
        p=self.pos
        if self.le>self.ls and p>=self.le:
            ll=self.le-self.ls; p=self.ls+(p-self.ls)%ll
        i=int(p); f=p-i
        if i<0 or i>=len(self.pcm): self.act=False; return 0
        n=i+1
        if self.le>self.ls and n>=self.le: n=self.ls
        elif n>=len(self.pcm): n=i
        v=self.pcm[i]*(1-f)+self.pcm[n]*f; self.pos+=self.r; return v

os.makedirs(OUT, exist_ok=True)
mid=60; dur=3.0; nf=int(dur*TARGET)

with open(SF2, 'rb') as f:
    sf = Sf2File(f)
    samples = [s for s in sf.samples if s.name != 'EOS']
    for samp in samples:
        raw=samp.raw_sample_data; sn=len(raw)//2
        sr=samp.sample_rate if hasattr(samp,'sample_rate') else 44100
        dn=int(sn*TARGET/sr)
        ls,le=samp.start_loop,samp.end_loop
        hl=ls<le and ls<sn and le<sn
        p16=struct.unpack('<%dh'%sn,raw)
        df=abs(p16[ls]-p16[le]) if hl else 999
        if not hl or df>10 or dn<200: continue
        d=resample(p16,sr,TARGET)
        r=len(d)/sn if sn>0 else 1
        rls=max(0,min(int(ls*r),len(d)-1)); rle=max(0,min(int(le*r),len(d)))
        rls=fix_loop(d,rls,rle)
        v=Voice(d,rls,rle,samp.original_pitch); v.note(mid)
        out=[]
        for i in range(nf):
            t=i/TARGET
            if t<0.05: e=t/0.05
            elif t<0.35: e=1.0-0.5*((t-0.05)/0.30)
            elif t<dur*0.7: e=0.5
            else: e=max(0,0.5*(1.0-(t-dur*0.7)/0.3))
            val = v.tick()
            out.append(max(-32768, min(32767, int(val * e))))
        cn=samp.name.replace(' ','_')
        wp=os.path.join(OUT,'%05d_%s_C4.wav'%(((dn+1)//2,cn))
        with wave.open(wp,'w') as wf:
            wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(TARGET)
            wf.writeframes(struct.pack('<%dh'%len(out),*out))
        print('%s C4 -> %s'%(samp.name,wp))
print('Done! -> %s/'%OUT)
