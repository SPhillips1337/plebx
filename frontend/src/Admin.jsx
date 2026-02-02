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
  const [queueInfo, setQueueInfo] = useState(null)
  const [workerInfo, setWorkerInfo] = useState(null)
  const [queueLoading, setQueueLoading] = useState(false)

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

  async function loadQueue(){
    setQueueLoading(true)
    try{
      const hdrs = {}
      if(adminToken) hdrs['X-Admin-Token'] = adminToken
      const res = await fetch(`${API_BASE}/admin/queue`, {headers: hdrs})
      const data = await res.json()
      if(res.ok) setQueueInfo(data)
      else setQueueInfo({error: data.detail || 'failed'})
    }catch(e){ setQueueInfo({error: String(e)}) }
    finally{ setQueueLoading(false) }
  }

  async function loadWorker(){
    try{
      const hdrs = {}
      if(adminToken) hdrs['X-Admin-Token'] = adminToken
      const res = await fetch(`${API_BASE}/admin/worker`, {headers: hdrs})
      const data = await res.json()
      if(res.ok) setWorkerInfo(data)
      else setWorkerInfo({error: data.detail || 'failed'})
    }catch(e){ setWorkerInfo({error: String(e)}) }
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
    <div className="plebx-card mb-12">
      <h3>Admin: Edit User Profile</h3>
      {showTokenModal && (
        <div className="plebx-modal-overlay">
          <div className="plebx-modal-box">
            <h4>Enter Admin Token</h4>
            <div className="mb-8">
              <input className="plebx-input" placeholder="X-Admin-Token (kept in memory unless 'Remember' checked)" value={adminToken} onChange={e=>setAdminToken(e.target.value)} />
            </div>
            <div className="mb-12">
              <label><input type="checkbox" checked={rememberToken} onChange={e=>setRememberToken(e.target.checked)} /> Remember token</label>
            </div>
            <div className="flex gap-8 justify-end">
              <button onClick={()=>{ setShowTokenModal(false); setAdminToken(''); }}>Cancel</button>
              <button onClick={closeAndApplyToken}>Apply</button>
            </div>
          </div>
        </div>
      )}
      <form onSubmit={submit}>
        <div className="mb-8 flex gap-8 align-start">
          <div className="flex-1">
            <label>User ID<br/><input value={userId} onChange={e=>onChangeUserId(e.target.value)} required /></label>
            {suggestions.length>0 && (
              <div className="plebx-suggestions">
                {suggestions.map(u=> (
                  <div key={u.id} className="plebx-suggestion-item" onClick={()=>{setUserId(u.id); setSuggestions([]); setDisplayName(u.display_name||u.username||''); setAvatarUrl(u.avatar_url||'')}}>
                    <strong className="mr-8">{u.display_name||u.username}</strong><small className="plebx-muted">@{u.username}</small>
                  </div>
                ))}
              </div>
            )}
          </div>
           <div className="flex gap-8">
             <button type="button" onClick={loadUser} disabled={loadingUser}>{loadingUser? 'Loading...':'Load'}</button>
           </div>
        </div>
        <div className="mb-8">
          <label>Display name<br/><input value={displayName} onChange={e=>setDisplayName(e.target.value)} /></label>
        </div>
        <div className="mb-8">
          <label>Avatar URL<br/><input value={avatarUrl} onChange={e=>setAvatarUrl(e.target.value)} /></label>
        </div>
        <div><button type="submit">Save</button> <span className="ml-12">{status}</span></div>
      </form>
      <div className="mt-16">
        <button className="plebx-btn-primary" onClick={()=>loadUsers(1)} disabled={listLoading}>{listLoading? 'Loading...':'Show Users'}</button>
      {showList && (
          <div className="mt-12">
            <div className="mb-8"><strong>Users (page {listPage})</strong></div>
              <div className="box-border">
              {usersList.map(u=> (
                <div key={u.id} className="plebx-user-row" onClick={()=>{ setUserId(u.id); setDisplayName(u.display_name||u.username||''); setAvatarUrl(u.avatar_url||''); setShowList(false)} }>
                  <div className="plebx-user-avatar">
                    {u.avatar_url ? <img src={u.avatar_url} alt={u.username} className="plebx-avatar-img" /> : <span className="plebx-muted">{(u.display_name||u.username||'').slice(0,2).toUpperCase()}</span>}
                  </div>
                  <div className="flex-1">
                    <div className="plebx-user-name">{u.display_name||u.username}</div>
                    <div className="plebx-user-handle">@{u.username}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-between mt-8">
              <button onClick={()=>loadUsers(Math.max(1,listPage-1))} disabled={listPage<=1}>Prev</button>
               <div className="align-self-center">Total: {listTotal}</div>
              <button onClick={()=>loadUsers(listPage+1)} disabled={listPage*listPerPage >= listTotal}>Next</button>
            </div>
          </div>
        )}
      </div>
      <div className="mt-12">
        <h3>Admin: Queue & Worker</h3>
        <div style={{display:'flex',gap:8,alignItems:'center',marginBottom:8}}>
          <button className="plebx-btn-primary" onClick={loadQueue} disabled={queueLoading}>{queueLoading? 'Loading...':'Refresh Queue'}</button>
          <button className="plebx-btn-primary" onClick={loadWorker}>Worker Status</button>
        </div>
        {queueInfo && (
          <pre style={{whiteSpace:'pre-wrap',fontSize:12,maxHeight:200,overflow:'auto',background:'#071426',padding:8,borderRadius:6}}>{JSON.stringify(queueInfo,null,2)}</pre>
        )}
        {workerInfo && (
          <pre style={{whiteSpace:'pre-wrap',fontSize:12,maxHeight:200,overflow:'auto',background:'#071426',padding:8,borderRadius:6}}>{JSON.stringify(workerInfo,null,2)}</pre>
        )}
      </div>
    </div>
  )
}
