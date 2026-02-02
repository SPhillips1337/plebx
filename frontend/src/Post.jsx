import React, {useEffect, useState} from 'react'

const API_BASE = 'http://localhost:8001'

function ReplyNode({node, depth=0}){
  const pending = node && (node.optimistic === true || String(node.id||'').startsWith('tmp-'))
  return (
    <div style={{marginLeft: depth*18, marginTop:8, opacity: pending ? 0.75 : 1}}>
      <div style={{display:'flex',gap:8,alignItems:'flex-start'}}>
        <div style={{width:40,height:40,background:'#f3f4f6',borderRadius:999,display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>
          {node.author && node.author.display_name ? (node.author.display_name.slice(0,2).toUpperCase()) : (node.author_id||' ').slice(0,2).toUpperCase()}
        </div>
        <div style={{flex:1}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'baseline'}}>
            <div style={{fontSize:13,fontWeight:600}}>{(node.author && (node.author.display_name||node.author.username)) || node.author_id}</div>
            {pending && <div style={{fontSize:12,color:'#6b7280'}}>⏳ Sending</div>}
          </div>
          <div style={{color:'#374151',marginTop:4, fontStyle: pending ? 'italic' : 'normal'}}>{node.content}</div>
        </div>
      </div>
      {node.replies && node.replies.length>0 && node.replies.map(r=> <ReplyNode key={r.id} node={r} depth={depth+1} />)}
    </div>
  )
}

export default function PostView({postId}){
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(()=>{
    if(!postId) return
    setLoading(true); setError(null)
    fetch(`${API_BASE}/post/${encodeURIComponent(postId)}?mode=db&depth=4&page=1&per_page=20`)
      .then(r=>{ if(!r.ok) throw new Error(''+r.status); return r.json() })
      .then(j=>{ setData(j); setLoading(false) })
      .catch(e=>{ setError(e.message); setLoading(false) })
  }, [postId])

  if(loading) return <div>Loading post...</div>
  if(error) return <div style={{color:'red'}}>Error: {error}</div>
  if(!data || !data.post) return <div>No post found</div>

  const p = data.post
  return (
    <div className="plebx-post">
      <button onClick={()=>{ window.history.pushState({},'', '/'); window.dispatchEvent(new PopStateEvent('popstate')) }} style={{marginBottom:12}}>← Back to feed</button>
      <div className="plebx-card">
        <div style={{display:'flex',gap:12}}>
          <div style={{width:56,height:56,borderRadius:999,background:'#f3f4f6',display:'flex',alignItems:'center',justifyContent:'center'}}>
            {(p.author && (p.author.display_name||p.author.username)||p.author_id||' ').slice(0,2).toUpperCase()
            }
          </div>
          <div style={{flex:1}}>
            <div style={{fontWeight:700,fontSize:16}}>{(p.author && (p.author.display_name||p.author.username)) || p.author_id}</div>
            <div style={{marginTop:8,color:'#111827'}}>{p.content}</div>
          </div>
        </div>
      </div>
      <div style={{marginTop:16}}>
        <h4>Replies</h4>
        {(!data.thread || data.thread.length===0) && <div>No replies</div>}
        {data.thread && data.thread.map(r=> <ReplyNode key={r.id} node={r} depth={0} />)}
      </div>

      <div style={{marginTop:20}}>
        <h4>Write a reply</h4>
        <Composer
          postId={postId}
          onOptimistic={(node)=>{
            // prepend optimistic node to thread
            setData(prev=>{
              if(!prev) return prev
              const thread = prev.thread || []
              return {...prev, thread: [node, ...thread]}
            })
          }}
           onPosted={()=>{
            // refresh thread after posting (server authoritative)
            fetch(`${API_BASE}/post/${encodeURIComponent(postId)}?mode=db&depth=4&page=1&per_page=20`).then(r=>r.json()).then(j=>setData(j)).catch(()=>{})
          }}
          onRemoveOptimistic={(tmpId)=>{
            setData(prev=>{
              if(!prev) return prev
              const thread = (prev.thread||[]).filter(n=>n.id !== tmpId)
              return {...prev, thread}
            })
          }}
          onReplaceOptimistic={(tmpId, created) => {
            setData(prev => {
              if(!prev) return prev
              const thread = (prev.thread || []).map(n => n.id === tmpId ? created : n)
              return {...prev, thread}
            })
          }}
        />
      </div>
    </div>
  )
}

function Composer({postId, onPosted, onOptimistic, onRemoveOptimistic, onReplaceOptimistic}){
  const [userId, setUserId] = React.useState('')
  const [content, setContent] = React.useState('')
  const [dryRun, setDryRun] = React.useState(true)
  const [loading, setLoading] = React.useState(false)
  const [result, setResult] = React.useState(null)

  async function submit(e){
    e && e.preventDefault()
    setLoading(true)
    setResult(null)
    try{
      // create optimistic node
      const tmpId = 'tmp-' + Date.now()
      const tmpNode = { id: tmpId, author_id: userId, content: content, created_at: new Date().toISOString(), replies: [], author: { username: userId, display_name: userId }, reply_to: postId, optimistic: true }
      try{ if(onOptimistic) onOptimistic(tmpNode) }catch(e){}

      const body = { user: userId, content: content, reply_to: postId, dry_run: dryRun }
      const res = await fetch(`${API_BASE}/post`, { method: 'POST', headers: { 'Content-Type':'application/json', 'X-User': userId }, body: JSON.stringify(body) })
      let json = null
      try{ json = await res.json() }catch(e){ json = null }
      if(!res.ok){
        setResult({ error: json || `status ${res.status}` })
        // remove optimistic node on failure
        try{ if(onRemoveOptimistic) onRemoveOptimistic(tmpId) }catch(e){}
      } else {
        setResult({ ok: true, body: json })
        setContent('')
        // If server returned a created post, replace the optimistic node with server data
        if(json && json.created){
          try{ if(onOptimistic){ /* replace handler not provided here */ } }catch(e){}
          try{ if(typeof onRemoveOptimistic === 'function' && typeof onOptimistic === 'function'){} }catch(e){}
          // call a dedicated replace callback if provided
          if(typeof onReplaceOptimistic === 'function'){
            onReplaceOptimistic(tmpId, json.created)
          } else if(onPosted){
            // fallback: refresh thread
            onPosted()
          }
        } else {
          if(onPosted) onPosted()
        }
      }
      // (removed duplicate optimistic cleanup handled above)
    }catch(err){ setResult({ error: err.message }) }
    finally{ setLoading(false) }
  }

  return (
    <div style={{background:'#fff',padding:12,borderRadius:8,border:'1px solid #e6edf3'}}>
      <form onSubmit={submit}>
        <div style={{marginBottom:8}}>
          <label>From (X-User header)<br/><input value={userId} onChange={e=>setUserId(e.target.value)} placeholder="user id" required style={{width:'100%'}}/></label>
        </div>
        <div style={{marginBottom:8}}>
          <label>Reply content<br/><textarea value={content} onChange={e=>setContent(e.target.value)} rows={4} style={{width:'100%'}} required/></label>
        </div>
        <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:8}}>
          <label><input type="checkbox" checked={dryRun} onChange={e=>setDryRun(e.target.checked)} /> Dry run (preview)</label>
          <div style={{flex:1}} />
          <button type="submit" disabled={loading}>{loading? 'Posting...':'Post Reply'}</button>
        </div>
      </form>
      {result && result.error && <div style={{color:'red',marginTop:8}}>Error: {String(result.error)}</div>}
      {result && result.ok && <div style={{color:'green',marginTop:8}}>Success: {JSON.stringify(result.body)}</div>}
    </div>
  )
}
