import React, {useEffect, useState} from 'react'

const API_BASE = 'http://localhost:8001'

export default function UserView({userId}){
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(false)
  useEffect(()=>{
    if(!userId) return
    setLoading(true)
    fetch(`${API_BASE}/user/${encodeURIComponent(userId)}`).then(r=>r.json()).then(j=>{ setUser(j.user); setLoading(false)}).catch(()=>setLoading(false))
  }, [userId])

  if(loading) return <div>Loading user...</div>
  if(!user) return <div>User not found</div>
  return (
    <div className="plebx-card">
      <div style={{display:'flex',gap:12,alignItems:'center'}}>
        <div className="plebx-avatar" style={{width:72,height:72}}>{user.avatar_url? <img src={user.avatar_url} className="plebx-avatar-img" alt="avatar" /> : (user.display_name||user.username||'U').slice(0,2).toUpperCase()}</div>
        <div>
          <div style={{fontWeight:700,fontSize:18}}>{user.display_name || user.username}</div>
          <div className="plebx-muted">@{user.username}</div>
          {user.bio && <div style={{marginTop:8}}>{user.bio}</div>}
        </div>
      </div>
    </div>
  )
}
