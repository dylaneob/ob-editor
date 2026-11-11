#!/usr/bin/env python3
"""Token burn report from Claude Code transcripts (deduped by message id).
usage: python3 -I token_report.py [--days 10] [--today]
Per day: turns, tokens re-read (cache read), median context per turn, output.
--today: per session since the weekly reset day start (UTC 02:00)."""
import json,glob,os,sys,collections,datetime,time
P=os.path.expanduser("~/.claude/projects/-Users-YOU")
days=int(sys.argv[sys.argv.index("--days")+1]) if "--days" in sys.argv else 10
cut=time.time()-days*86400
byday=collections.defaultdict(lambda:[0,0,0,[]]); bys=collections.defaultdict(lambda:[0,0,0])
today=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
for f in glob.glob(P+"/**/*.jsonl",recursive=True):
    if not os.path.exists(f) or os.path.getmtime(f)<cut: continue
    rel=f[len(P)+1:]; sid=rel.split("/")[0].replace(".jsonl","")[:8]+(" agents" if "/" in rel else "")
    seen=set()
    with open(f,"rb") as fh:
        for line in fh:
            if b'"cache_read_input_tokens"' not in line: continue
            try: d=json.loads(line)
            except: continue
            m=d.get("message") or {}; u=m.get("usage") or {}
            if m.get("id") in seen: continue
            seen.add(m.get("id")); ts=d.get("timestamp","")
            if not ts: continue
            ctx=u.get("input_tokens",0)+u.get("cache_read_input_tokens",0)+u.get("cache_creation_input_tokens",0)
            b=byday[ts[:10]]; b[0]+=1; b[1]+=ctx; b[2]+=u.get("output_tokens",0); b[3].append(ctx)
            if ts[:10]==today: s=bys[sid]; s[0]+=1; s[1]+=ctx; s[2]=max(s[2],ctx)
print("day         turns  re-read(M)  median ctx(K)  output(K)")
for k in sorted(byday)[-days:]:
    b=byday[k]; v=sorted(b[3]); print(f"{k}  {b[0]:6} {b[1]/1e6:10.0f} {v[len(v)//2]/1e3:12.0f} {b[2]/1e3:10.0f}")
if "--today" in sys.argv:
    print("\nsession today      turns  re-read(M)  max ctx(K)")
    for k,s in sorted(bys.items(),key=lambda kv:-kv[1][1])[:12]: print(f"{k:18} {s[0]:6} {s[1]/1e6:10.0f} {s[2]/1e3:11.0f}")
