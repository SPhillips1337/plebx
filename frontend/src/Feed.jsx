import React, {useState, useEffect} from 'react'

const API_BASE = 'http://localhost:8000'  // Main API
const BRIDGE_API_BASE = 'http://localhost:8001'  // P2P Bridge

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
  // map address hash into a fixed hue bucket to avoid inline styles
  const bucket = Math.abs((name||'').split('').reduce((h,c)=> ((h<<5)-h)+c.charCodeAt(0),0)) % 12
  return <div className={"avatar avatar-hue-"+bucket}>{label}</div>
}

function Post({p, currentUser}){
  // Handle Plebbit bridge post structure
  const authorAddress = p.author?.address || p.author_id
  const authorShort = p.author?.shortAddress || authorAddress?.substring(0, 8) + '...'
  const authorName = p.author?.display_name || authorShort
  const engagement = p.engagement || {}
  
  return (
    <div className="post" onClick={()=>{ window.history.pushState({},'', `/post/${encodeURIComponent(p.cid || p.id)}`); window.dispatchEvent(new PopStateEvent('popstate')) }}>
      <div className="post-row">
        <Avatar name={authorName} avatar={p.author?.avatar_url} />
        <div className="post-content">
          <div className="meta" style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
            <div>
              <strong>{authorName}</strong>
              <div className="plebx-small-muted" style={{marginLeft:8,display:'inline-block'}}>
                {engagement.reply_count && `${engagement.reply_count} replies`}
                {engagement.reply_count && engagement.upvote_count && ' • '}
                {engagement.upvote_count && `+${engagement.upvote_count}`}
              </div>
            </div>
            <div>
              {/* Follow button placed here; stopPropagation handled in the button */}
              <FollowButton authorId={authorAddress} currentUser={currentUser} onChanged={(nowFollowing)=>{
                // optimistic update of local posts author follower counts
                // update posts in parent via a custom event
                const ev = new CustomEvent('plebx:follow', { detail: { authorId: authorAddress, nowFollowing } })
                window.dispatchEvent(ev)
              }} />
            </div>
          </div>
          <div className="content-text">{p.content}</div>
          <div className="post-meta-info">
            <div className="plebx-small-muted">
              {p.timestamp && new Date(p.timestamp * 1000).toLocaleDateString()}
            </div>
            {p.subplebbit_address && (
              <div className="plebx-small-muted">
                in /{p.subplebbit_address}/
              </div>
            )}
          </div>
          {(p.attachments && p.attachments.length>0) && (
            <div className="attachments">
              {p.attachments.map((a,idx)=> (
                <img key={idx} src={a.url || a.thumbnail_url} alt="attachment" />
              ))}
            </div>
          )}
          {(p.link || p.thumbnail_url) && (
            <div className="attachments">
              <img src={p.link || p.thumbnail_url} alt="preview" />
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
  const [bridgeStatus, setBridgeStatus] = useState('unknown')

  async function load(cursor=null, append=false){
    setLoading(true)
    try{
      const params = new URLSearchParams({limit:20, mode:'bridge'})
      if(cursor) params.set('cursor', cursor)
      const res = await fetch(`${API_BASE}/feed?${params.toString()}`)
      if(!res.ok) throw new Error(''+res.status)
      const data = await res.json()
      
      // Log bridge activity
      console.log('🌉 Loaded posts from P2P bridge:', data.posts?.length || 0)
      
      if(append) setPosts(prev=>[...prev,...(data.posts||[])])
      else setPosts(data.posts||[])
      setNextCursor(data.next_cursor || null)
    }catch(e){
      console.error('❌ Load failed, trying bridge directly:', e)
      // Fallback to direct bridge call
      try{
        const bridgeRes = await fetch(`${BRIDGE_API_BASE}/subs/memes.eth/posts?limit=20&sort=hot`)
        if(bridgeRes.ok){
          const bridgeData = await bridgeRes.json()
          console.log('🌉 Bridge fallback successful:', bridgeData.length)
          setPosts(bridgeData || [])
        } else {
          setPosts([])
        }
      }catch(bridgeError){
        console.error('❌ Bridge fallback failed:', bridgeError)
        setPosts([])
      }
    }finally{
      setLoading(false)
    }
  }

  // Check bridge status on mount
  useEffect(()=>{
    async function checkBridgeStatus(){
      try{
        const res = await fetch(`${BRIDGE_API_BASE}/health`)
        if(res.ok){
          const data = await res.json()
          setBridgeStatus(data.status === 'healthy' ? 'online' : 'offline')
        } else {
          setBridgeStatus('offline')
        }
      }catch(e){
        setBridgeStatus('offline')
      }
    }
    
    checkBridgeStatus()
    // Check bridge status every 30 seconds
    const interval = setInterval(checkBridgeStatus, 30000)
    return ()=> clearInterval(interval)
  }, [])
  
  useEffect(()=>{ load(null,false) }, [])

  // Listen for follow events to update counts optimistically
  useEffect(()=>{
    function onFollow(e){
      const { authorId, nowFollowing } = e.detail || {}
      if(!authorId) return
      setPosts(prev => prev.map(p => {
        if(p.author_id === authorId){
          const a = p.author || { counts: { followers: 0, following: 0 } }
          const counts = Object.assign({}, a.counts || { followers:0, following:0 })
          counts.followers = Math.max(0, counts.followers + (nowFollowing ? 1 : -1))
          return { ...p, author: { ...(p.author||{}), counts } }
        }
        return p
      }))
    }
    window.addEventListener('plebx:follow', onFollow)
    return ()=> window.removeEventListener('plebx:follow', onFollow)
  }, [])

  // Listen for new posts from SSE
  useEffect(()=>{
    function onPost(e){
      const post = (e.detail && e.detail.post) || null
      if(!post) return
      setPosts(prev => [post, ...(prev || [])])
    }
    window.addEventListener('plebx:post', onPost)
    return ()=> window.removeEventListener('plebx:post', onPost)
  }, [])

  return (
    <div>
      <div className="plebx-status-bar">
        <div className="plebx-bridge-status">
          P2P Bridge: <span className={`plebx-status-${bridgeStatus}`}>
            {bridgeStatus === 'online' ? '🟢 Online' : bridgeStatus === 'offline' ? '🔴 Offline' : '🟡 Unknown'}
          </span>
        </div>
      </div>
      <div id="feed">
        {posts.map(p=> <Post key={p.cid || p.id} p={p} className="plebx-post" currentUser={currentUser} />)}
        {posts.length===0 && !loading && (
          <div className="plebx-empty">
            {bridgeStatus === 'online' ? '🌉 No posts yet from Plebbit network' : '🔌 Connecting to Plebbit network...'}
          </div>
        )}
        {loading && <div className="plebx-loading">🔄 Loading posts from Plebbit...</div>}
      </div>
      {nextCursor && <div className="plebx-loadmore"><button className="plebx-btn-primary" onClick={()=>load(nextCursor,true)} disabled={loading}>{loading? 'Loading...':'Load more'}</button></div>}
    </div>
  )
}
