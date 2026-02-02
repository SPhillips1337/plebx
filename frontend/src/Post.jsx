import React, {useEffect, useState} from 'react'

const API_BASE = 'http://localhost:8001'

function ReplyNode({node, depth=0}){
  return (
    <div style={{marginLeft: depth*18, marginTop:8}}>
      <div style={{display:'flex',gap:8}}>
        <div style={{width:40,height:40,background:'#f3f4f6',borderRadius:999,display:'flex',alignItems:'center',justifyContent:'center'}}>
          {node.author && node.author.display_name ? (node.author.display_name.slice(0,2).toUpperCase()) : (node.author_id||' ').slice(0,2).toUpperCase()}
        </div>
        <div style={{flex:1}}>
          <div style={{fontSize:13,fontWeight:600}}>{(node.author && (node.author.display_name||node.author.username)) || node.author_id}</div>
          <div style={{color:'#374151',marginTop:4}}>{node.content}</div>
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
    <div>
      <button onClick={()=>{ window.history.pushState({},'', '/'); window.dispatchEvent(new PopStateEvent('popstate')) }} style={{marginBottom:12}}>← Back to feed</button>
      <div style={{background:'#fff',padding:16,borderRadius:12,boxShadow:'0 4px 12px rgba(12,20,30,0.06)'}}>
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
    </div>
  )
}
