import React, {useState, useRef, useEffect} from 'react'

const API_BASE = 'http://localhost:8001'

export default function Admin(){
  const [userId,setUserId] = useState('')
  const [displayName,setDisplayName] = useState('')
  const [avatarUrl,setAvatarUrl] = useState('')
  const [status,setStatus] = useState(null)
  const [loadingUser,setLoadingUser] = useState(false)
  const [suggestions,setSuggestions] = useState([])
  const [suggestLoading,setSuggestLoading] = useState(false)
  const suggestTimer = useRef(null)

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

  async function loadUser(){
    if(!userId) { setStatus('Enter User ID to load'); return }
    setLoadingUser(true)
    setStatus('Loading user...')
    try{
      const res = await fetch(`${API_BASE}/user/${encodeURIComponent(userId)}`)
      if(res.status === 404){
        setStatus('User not found — you can create it')
        setDisplayName('')
        setAvatarUrl('')
        setLoadingUser(false)
        return
      }
      const data = await res.json()
      if(!res.ok){ setStatus('Error: '+(data.detail||res.status)); setLoadingUser(false); return }
      const u = data.user || {}
      setDisplayName(u.display_name || u.username || '')
      setAvatarUrl(u.avatar_url || '')
      setStatus('Loaded')
    }catch(err){
      setStatus('Error: '+err.message)
    }finally{
      setLoadingUser(false)
    }
  }

  function onChangeUserId(v){
    setUserId(v)
    // debounce search
    if(suggestTimer.current) clearTimeout(suggestTimer.current)
    if(!v) { setSuggestions([]); return }
    suggestTimer.current = setTimeout(async ()=>{
      setSuggestLoading(true)
      try{
        const res = await fetch(`${API_BASE}/users?query=${encodeURIComponent(v)}&limit=6`)
        const data = await res.json()
        if(res.ok) setSuggestions(data.users || [])
        else setSuggestions([])
      }catch(e){ setSuggestions([]) }
      setSuggestLoading(false)
    }, 250)
  }

  useEffect(()=>()=>{ if(suggestTimer.current) clearTimeout(suggestTimer.current) }, [])

  return (
    <div style={{marginTop:20,padding:12,background:'#fff',borderRadius:8,boxShadow:'0 1px 3px rgba(0,0,0,0.06)'}}>
      <h3>Admin: Edit User Profile</h3>
      <form onSubmit={submit}>
        <div style={{marginBottom:8,display:'flex',gap:8,alignItems:'flex-start'}}>
          <div style={{flex:1}}>
            <label>User ID<br/><input value={userId} onChange={e=>onChangeUserId(e.target.value)} required /></label>
            {suggestions.length>0 && (
              <div style={{border:'1px solid #e5e7eb',background:'#fff',marginTop:6,borderRadius:6,maxHeight:180,overflow:'auto'}}>
                {suggestions.map(u=> (
                  <div key={u.id} style={{padding:8,cursor:'pointer'}} onClick={()=>{setUserId(u.id); setSuggestions([]); setDisplayName(u.display_name||u.username||''); setAvatarUrl(u.avatar_url||'')}}>
                    <strong style={{marginRight:8}}>{u.display_name||u.username}</strong><small style={{color:'#6b7280'}}>@{u.username}</small>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div style={{display:'flex',gap:8}}>
            <button type="button" onClick={loadUser} disabled={loadingUser}>{loadingUser? 'Loading...':'Load'}</button>
          </div>
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
