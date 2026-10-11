// Owner-private transport only. The capability is read from masked stdin,
// never arguments, environment files, Git, or stdout. One bounded request.
import { createInterface } from 'node:readline/promises';
import readline from 'node:readline';
readline.emitKeypressEvents(process.stdin);
if (process.stdin.isTTY) process.stdin.setRawMode(true);
const input = createInterface({input:process.stdin,output:process.stdout,terminal:false});
const origin='https://fabrya-product-live-validation.sempehugo03.chatgpt.site';
console.log('Ready for owner-private SEO transport JSON on stdin (input hidden).');
for await (const line of input) {
 try {
  const {token,path,method='GET',body}=JSON.parse(line);
  const read=method==='GET' && /^\/api\/seo\/(?:attribution|pages\/[a-z0-9-]{3,80}|preview\/[A-Za-z0-9_-]{8,100})$/.test(path);
  const stage=method==='POST' && path==='/api/seo/changes' && body?.action==='stage';
  if (!token || token.length>6000 || !(read||stage)) throw Error();
  const r=await fetch(origin+path,{method,redirect:'error',signal:AbortSignal.timeout(30000),headers:{'OAI-Sites-Authorization':'Bearer '+token,'origin':origin,'content-type':'application/json'},body:stage?JSON.stringify(body):undefined});
  const value=await r.text();if(value.length>100000)throw Error();
  const data=r.headers.get('content-type')?.includes('json')?JSON.parse(value):value;
  const result=stage && r.ok ? {id:data.id,slug:data.slug,state:data.state,before_version:data.before_version,after_version:data.after_version,source_commit:data.source_commit,source_data_json:data.source_data_json,expected_effect:data.expected_effect,created_at:data.created_at,updated_at:data.updated_at,production_published:false} : data;
  console.log(JSON.stringify({status:r.status,data:result}));
 }catch{console.log(JSON.stringify({error:'PRIVATE_SEO_TRANSPORT_UNAVAILABLE'}));process.exitCode=1;}
 break;
}
input.close();
