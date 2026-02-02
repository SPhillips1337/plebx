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
  const [adminToken, setAdminToken] = useState('')
  const [showTokenModal, setShowTokenModal] = useState(true)
  const [rememberToken, setRememberToken] = useState(false)

  async function submit(e){
    e.preventDefault()
    setStatus('Saving...')
    try{
      const hdrs = {'Content-Type':'application/json'}
      if(adminToken) hdrs['X-Admin-Token'] = adminToken
      const res = await fetch(`${API_BASE}/admin/user/${encodeURIComponent(userId)}`, {
        method: 'POST',
        headers: hdrs,
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
      const hdrs = {}
      if(adminToken) hdrs['X-Admin-Token'] = adminToken
      const res = await fetch(`${API_BASE}/user/${encodeURIComponent(userId)}`, {headers: hdrs})
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
        const hdrs = {}
        if(adminToken) hdrs['X-Admin-Token'] = adminToken
        const res = await fetch(`${API_BASE}/users?query=${encodeURIComponent(v)}&limit=6`, {headers: hdrs})
        const data = await res.json()
        if(res.ok) setSuggestions(data.users || [])
        else setSuggestions([])
      }catch(e){ setSuggestions([]) }
      setSuggestLoading(false)
    }, 250)
  }

  useEffect(()=>()=>{ if(suggestTimer.current) clearTimeout(suggestTimer.current) }, [])

  const [showList, setShowList] = useState(false)
  const [usersList, setUsersList] = useState([])
  const [listPage, setListPage] = useState(1)
  const [listPerPage] = useState(10)
  const [listTotal, setListTotal] = useState(0)
  const [listLoading, setListLoading] = useState(false)

  async function loadUsers(page = 1){
    setListLoading(true)
    try{
      const hdrs = {'Content-Type':'application/json'}
      if(adminToken) hdrs['X-Admin-Token'] = adminToken
      const res = await fetch(`${API_BASE}/admin/users?page=${page}&per_page=${listPerPage}`, {headers: hdrs})
      const data = await res.json()
      if(!res.ok){ setUsersList([]); setListTotal(0); return }
      setUsersList(data.users || [])
      setListTotal((data.meta && data.meta.total) || 0)
      setListPage(page)
      setShowList(true)
    }catch(e){ setUsersList([]); setListTotal(0) }
    finally{ setListLoading(false) }
  }
  
  // Show token modal when admin UI opens; token kept in memory unless user opts to remember
  useEffect(()=>{
    // showTokenModal is true by default; no localStorage access for security
    setShowTokenModal(true)
  }, [])

  function closeAndApplyToken(){
    try{
      if(rememberToken){ localStorage.setItem('plebx_admin_token', adminToken || '') }
      setShowTokenModal(false)
      setStatus('Token applied')
    }catch(e){ setStatus('Failed to save token') }
  }


  return (
    <div style={{marginTop:20,padding:12,background:'#fff',borderRadius:8,boxShadow:'0 1px 3px rgba(0,0,0,0.06)'}}>
      <h3>Admin: Edit User Profile</h3>
      {showTokenModal && (
        <div style={{position:'fixed',left:0,top:0,right:0,bottom:0,display:'flex',alignItems:'center',justifyContent:'center',background:'rgba(0,0,0,0.4)'}}>
          <div style={{background:'#fff',padding:20,borderRadius:8,minWidth:320}}>
            <h4>Enter Admin Token</h4>
            <div style={{marginBottom:8}}>
              <input placeholder="X-Admin-Token (kept in memory unless 'Remember' checked)" value={adminToken} onChange={e=>setAdminToken(e.target.value)} style={{width:'100%'}} />
            </div>
            <div style={{marginBottom:12}}
>
              <label><input type="checkbox" checked={rememberToken} onChange={e=>setRememberToken(e.target.checked)} /> Remember token</label>
            </div>
            <div style={{display:'flex',justifyContent:'flex-end',gap:8}}>
              <button onClick={()=>{ setShowTokenModal(false); setAdminToken(''); }}>Cancel</button>
              <button onClick={closeAndApplyToken}>Apply</button>
            </div>
          </div>
        </div>
      )}
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
      <div style={{marginTop:16}}>
        <button onClick={()=>loadUsers(1)} disabled={listLoading}>{listLoading? 'Loading...':'Show Users'}</button>
        {showList && (
          <div style={{marginTop:12}}>
            <div style={{marginBottom:8}}><strong>Users (page {listPage})</strong></div>
            <div style={{border:'1px solid #e5e7eb',borderRadius:6,overflow:'hidden'}}>
              {usersList.map(u=> (
                <div key={u.id} style={{display:'flex',alignItems:'center',padding:8,borderBottom:'1px solid #f3f4f6',cursor:'pointer'}} onClick={()=>{ setUserId(u.id); setDisplayName(u.display_name||u.username||''); setAvatarUrl(u.avatar_url||''); setShowList(false)} }>
                  <div style={{width:40,height:40,overflow:'hidden',borderRadius:999,background:'#f3f4f6',display:'inline-flex',alignItems:'center',justifyContent:'center',marginRight:12}}>
                    {u.avatar_url ? <img src={u.avatar_url} alt={u.username} style={{width:'100%',height:'100%',objectFit:'cover'}} /> : <span style={{color:'#6b7280'}}>{(u.display_name||u.username||'').slice(0,2).toUpperCase()}</span>}
                  </div>
                  <div style={{flex:1}}>
                    <div style={{fontWeight:600}}>{u.display_name||u.username}</div>
                    <div style={{fontSize:12,color:'#6b7280'}}>@{u.username}</div>
                  </div>
                </div>
              ))}
            </div>
            <div style={{display:'flex',justifyContent:'space-between',marginTop:8}}>
              <button onClick={()=>loadUsers(Math.max(1,listPage-1))} disabled={listPage<=1}>Prev</button>
              <div style={{alignSelf:'center'}}>Total: {listTotal}</div>
              <button onClick={()=>loadUsers(listPage+1)} disabled={listPage*listPerPage >= listTotal}>Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
