import React, {useState, useEffect} from 'react'

const API_BASE = 'http://localhost:8001'

function initials(name){
  if(!name) return '??'
  const parts = String(name).split(/[^a-zA-Z0-9]+/).filter(Boolean)
  if(parts.length===0) return name.slice(0,2).toUpperCase()
  if(parts.length===1) return parts[0].slice(0,2).toUpperCase()
  return (parts[0][0]+parts[1][0]).toUpperCase()
}

function colorFor(name){
  let h = 0
  for(let i=0;i<name.length;i++) h = name.charCodeAt(i) + ((h<<5)-h)
  const hue = Math.abs(h) % 360
  return `hsl(${hue}deg 65% 45%)`
}

function Avatar({name, avatar}){
  if(avatar){
    return <div className="avatar plebx-avatar--image"><img className="plebx-avatar-img" src={avatar} alt={name} /></div>
  }
  const label = initials(name)
  const bg = colorFor(name||'')
  // map name hash into a fixed hue bucket to avoid inline styles
  const bucket = Math.abs(name.split('').reduce((h,c)=> ((h<<5)-h)+c.charCodeAt(0),0)) % 12
  return <div className={"avatar avatar-hue-"+bucket}>{label}</div>
}

function Post({p, currentUser}){
  return (
    <div className="post" onClick={()=>{ window.history.pushState({},'', `/post/${encodeURIComponent(p.id)}`); window.dispatchEvent(new PopStateEvent('popstate')) }}>
      <div className="post-row">
        <Avatar name={(p.author && (p.author.display_name||p.author.username)) || p.author_id} avatar={p.author && p.author.avatar_url} />
        <div className="post-content">
          <div className="meta"><strong>{(p.author && (p.author.display_name||p.author.username)) || p.author_id}</strong> <span className="score">★ {Number(p.score||0).toFixed(2)}</span></div>
          <div className="content-text">{p.content}</div>
          {p.attachments && p.attachments.length>0 && (
            <div className="attachments">
              {p.attachments.map((a,idx)=> (
                <img key={idx} src={a.url || a} alt="attachment" />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Feed({currentUser}){
  const [posts,setPosts] = useState([])
  const [nextCursor,setNextCursor] = useState(null)
  const [loading,setLoading] = useState(false)

  async function load(cursor=null, append=false){
    setLoading(true)
    try{
      const params = new URLSearchParams({limit:10, mode:'db'})
      if(cursor) params.set('cursor', cursor)
      const res = await fetch(`${API_BASE}/feed?${params.toString()}`)
      if(!res.ok) throw new Error(''+res.status)
      const data = await res.json()
      if(append) setPosts(prev=>[...prev,...(data.posts||[])])
      else setPosts(data.posts||[])
      setNextCursor(data.next_cursor || null)
    }catch(e){
      console.error('load failed', e)
      setPosts([])
    }finally{
      setLoading(false)
    }
  }

  useEffect(()=>{ load(null,false) }, [])

  return (
    <div>
      <div id="feed">
        {posts.map(p=> <Post key={p.id} p={p} className="plebx-post" currentUser={currentUser} />)}
        {posts.length===0 && !loading && <div>No posts</div>}
      </div>
      {nextCursor && <div className="plebx-loadmore"><button className="plebx-btn-primary" onClick={()=>load(nextCursor,true)} disabled={loading}>{loading? 'Loading...':'Load more'}</button></div>}
    </div>
  )
}
