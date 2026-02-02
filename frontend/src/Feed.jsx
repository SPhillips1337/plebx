import React, {useState, useEffect} from 'react'

const API_BASE = 'http://localhost:8001'

function Post({p}){
  return (
    <div className="post" onClick={()=>window.open(`${API_BASE}/post/${encodeURIComponent(p.id)}?mode=db`,'_blank')}>
      <div className="meta"><strong>{p.author_id}</strong> <span className="score">★ {Number(p.score||0).toFixed(2)}</span></div>
      <div>{p.content}</div>
    </div>
  )
}

export default function Feed(){
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
        {posts.map(p=> <Post key={p.id} p={p} />)}
        {posts.length===0 && !loading && <div>No posts</div>}
      </div>
      {nextCursor && <div style={{textAlign:'center',marginTop:12}}><button onClick={()=>load(nextCursor,true)} disabled={loading}>{loading? 'Loading...':'Load more'}</button></div>}
    </div>
  )
}
