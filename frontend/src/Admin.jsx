import React, {useState} from 'react'

const API_BASE = 'http://localhost:8001'

export default function Admin(){
  const [userId,setUserId] = useState('')
  const [displayName,setDisplayName] = useState('')
  const [avatarUrl,setAvatarUrl] = useState('')
  const [status,setStatus] = useState(null)

  async function submit(e){
    e.preventDefault()
    setStatus('Saving...')
    try{
      const res = await fetch(`${API_BASE}/admin/user/${encodeURIComponent(userId)}`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({display_name: displayName, avatar_url: avatarUrl})
      })
      const data = await res.json()
      if(!res.ok){ setStatus('Error: '+(data.detail||res.status)); return }
      setStatus('Saved')
    }catch(err){
      setStatus('Error: '+err.message)
    }
  }

  return (
    <div style={{marginTop:20,padding:12,background:'#fff',borderRadius:8,boxShadow:'0 1px 3px rgba(0,0,0,0.06)'}}>
      <h3>Admin: Edit User Profile</h3>
      <form onSubmit={submit}>
        <div style={{marginBottom:8}}>
          <label>User ID<br/><input value={userId} onChange={e=>setUserId(e.target.value)} required /></label>
        </div>
        <div style={{marginBottom:8}}>
          <label>Display name<br/><input value={displayName} onChange={e=>setDisplayName(e.target.value)} /></label>
        </div>
        <div style={{marginBottom:8}}>
          <label>Avatar URL<br/><input value={avatarUrl} onChange={e=>setAvatarUrl(e.target.value)} /></label>
        </div>
        <div><button type="submit">Save</button> <span style={{marginLeft:12}}>{status}</span></div>
      </form>
    </div>
  )
}
