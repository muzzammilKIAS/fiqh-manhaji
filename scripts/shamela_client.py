"""Klien MCP stdio minimum untuk Shamela 4 setempat (macOS). Tetapkan SHAMELA_INSTALL_ROOT jika lokasi lain."""
import subprocess, json, sys, os
R=os.environ.get("SHAMELA_INSTALL_ROOT", os.path.expanduser("~/Library/Application Support/Shamela"))
class Shm:
    def __init__(s):
        s.p=subprocess.Popen(['node',R+'/mcp/shamela-mcp/dist/index.js'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',
            env={**os.environ,'SHAMELA_INSTALL_ROOT':R,'SHAMELA_JRE':R+'/app/mac/arm64/jre/2/bin/java'})
        s.i=0
        s.rpc('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'x','version':'1'}})
        s.p.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/initialized'})+'\n');s.p.stdin.flush()
    def rpc(s,m,params):
        s.i+=1;s.p.stdin.write(json.dumps({'jsonrpc':'2.0','id':s.i,'method':m,'params':params})+'\n');s.p.stdin.flush()
        while True:
            l=s.p.stdout.readline()
            if not l: raise EOFError
            try: d=json.loads(l)
            except: continue
            if d.get('id')==s.i: return d
    def call(s,name,**a):
        d=s.rpc('tools/call',{'name':name,'arguments':a})
        r=d.get('result',d)
        return '\n'.join(c.get('text','') for c in r.get('content',[])) if 'content' in r else json.dumps(r,ensure_ascii=False)
if __name__=='__main__':
    s=Shm(); print(s.call(sys.argv[1],**json.loads(sys.argv[2] if len(sys.argv)>2 else '{}')))
