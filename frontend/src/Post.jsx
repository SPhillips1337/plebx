import React, {useEffect, useState} from 'react'

const API_BASE = 'http://localhost:8001'

function ReplyNode({node, depth=0}){
  const pending = node && (node.optimistic === true || String(node.id||'').startsWith('tmp-'))
  // clamp depth to available indent classes
  const d = Math.max(0, Math.min(8, depth))
  return (
    <div className={"plebx-reply indent-"+d}>
      <div className="plebx-reply-row">
        <div className="plebx-reply-avatar">
          {node.author && node.author.display_name ? (node.author.display_name.slice(0,2).toUpperCase()) : (node.author_id||' ').slice(0,2).toUpperCase()}
        </div>
          <div className="plebx-reply-content">
          <div className="plebx-reply-meta">
            <div className="reply-author-name">{(node.author && (node.author.display_name||node.author.username)) || node.author_id}</div>
            {pending && <div className="plebx-sending">⏳ Sending</div>}
          </div>
          <div className={"plebx-reply-text" + (pending? ' plebx-pending':'' )}>{node.content}</div>
        </div>
      </div>
      {node.replies && node.replies.length>0 && node.replies.map(r=> <ReplyNode key={r.id} node={r} depth={depth+1} />)}
    </div>
  )
}

export default function PostView({postId, currentUser}){
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
  if(error) return <div className="plebx-error">Error: {error}</div>
  if(!data || !data.post) return <div>No post found</div>

  const p = data.post
  return (
    <div className="plebx-post">
      <div className="mb-12"><button className="plebx-back" onClick={()=>{ window.history.pushState({},'', '/'); window.dispatchEvent(new PopStateEvent('popstate')) }}>← Back to feed</button></div>
      <div className="plebx-card">
        <div className="post-row">
          <div className={"plebx-avatar " + (p.author && p.author.avatar_url ? 'plebx-avatar--image' : '')}>
            {p.author && p.author.avatar_url ? <img src={p.author.avatar_url} alt="avatar" className="plebx-avatar-img" /> : ((p.author && (p.author.display_name||p.author.username)||p.author_id||' ').slice(0,2).toUpperCase())}
          </div>
          <div className="post-content">
            <div className="plebx-meta">
              <strong>{(p.author && (p.author.display_name||p.author.username)) || p.author_id}</strong>
            <div className="flex gap-8 align-center">
                <span className="plebx-score">★ {Number(p.score||0).toFixed(2)}</span>
                <FollowButton authorId={p.author_id} currentUser={currentUser} />
              </div>
            </div>
            <div className="content-text">{p.content}</div>
          </div>
        </div>
      </div>
      <div className="mt-16">
        <h4>Replies</h4>
        {(!data.thread || data.thread.length===0) && <div>No replies</div>}
        {data.thread && data.thread.map(r=> <ReplyNode key={r.id} node={r} depth={0} />)}
      </div>

      <div className="mt-20">
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
    <div className="plebx-compose">
      <form onSubmit={submit}>
        <div className="mb-8">
          <label>From (X-User header)<br/><input className="plebx-input" value={userId} onChange={e=>setUserId(e.target.value)} placeholder="user id" required /></label>
        </div>
        <div className="mb-8">
          <label>Reply content<br/><textarea className="plebx-textarea" value={content} onChange={e=>setContent(e.target.value)} rows={4} required/></label>
        </div>
        <div className="flex align-center gap-12 mb-8">
          <label><input type="checkbox" checked={dryRun} onChange={e=>setDryRun(e.target.checked)} /> Dry run (preview)</label>
          <div className="flex-1" />
          <button type="submit" className="plebx-btn-primary" disabled={loading}>{loading? 'Posting...':'Post Reply'}</button>
        </div>
      </form>
      {result && result.error && <div className="plebx-error">Error: {String(result.error)}</div>}
      {result && result.ok && <div className="plebx-success">Success: {JSON.stringify(result.body)}</div>}
    </div>
  )
}

// Follow button component for posts
export function FollowButton({authorId, currentUser, onChanged}){
  const [following, setFollowing] = React.useState(false)
  const [loading, setLoading] = React.useState(false)

  async function refresh(){
    if(!currentUser) return setFollowing(false)
    try{
      const res = await fetch(`${API_BASE}/user/${encodeURIComponent(currentUser)}/following`)
      if(!res.ok) return
      const j = await res.json()
      setFollowing((j.following||[]).includes(authorId))
    }catch(e){}
  }

  React.useEffect(()=>{ refresh() }, [authorId, currentUser])

  async function toggle(){
    if(!currentUser) return alert('Set current user in header to follow')
    setLoading(true)
    try{
      const hdrs = {'X-User': currentUser}
      if(!following){
        await fetch(`${API_BASE}/user/${encodeURIComponent(authorId)}/follow`, {method:'POST', headers: hdrs})
      }else{
        await fetch(`${API_BASE}/user/${encodeURIComponent(authorId)}/follow`, {method:'DELETE', headers: hdrs})
      }
      await refresh()
      if(onChanged) onChanged(!following)
    }catch(e){}
    finally{ setLoading(false) }
  }

  return <button className="plebx-btn-primary" onClick={toggle} disabled={loading}>{following? 'Following':'Follow'}</button>
}
