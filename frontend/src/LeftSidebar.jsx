import React, {useEffect, useState} from 'react'

function NavItem({icon, label, onClick, active}){
  return (
    <div className={"plebx-nav-item" + (active? ' active':'')} onClick={onClick} role="button">
      <span className="material-symbols-outlined">{icon}</span>
      <span className="plebx-nav-label">{label}</span>
    </div>
  )
}

export default function LeftSidebar({onHome, currentRoute, currentUser}){
  const [profile, setProfile] = useState(null)
  const [counts, setCounts] = useState({followers:0, following:0})

  useEffect(()=>{
    let mounted = true
    async function load(){
      if(!currentUser) { setProfile(null); setCounts({followers:0, following:0}); return }
      try{
        const res = await fetch(`/user/${encodeURIComponent(currentUser)}`)
        const cr = await fetch(`/user/${encodeURIComponent(currentUser)}/counts`)
        if(!res.ok) return
        const j = await res.json()
        const cj = await cr.json()
        if(mounted) {
          setProfile(j.user)
          if(cj && cj.counts) setCounts(cj.counts)
        }
      }catch(e){}
    }
    load()
    return ()=>{ mounted = false }
  }, [currentUser])

  const isActive = (name)=>{
    if(name === 'home') return currentRoute && currentRoute.name === 'feed'
    if(name === 'profile') return currentRoute && currentRoute.name === 'user' && currentRoute.params && currentRoute.params.id === (profile && profile.username)
    return false
  }

  return (
    <aside className="plebx-sidebar">
      <div className="plebx-logo" onClick={onHome} role="button">PlebX</div>

      <nav className="plebx-nav">
        <NavItem icon="home" label="Home" onClick={onHome} active={isActive('home')} />
        <NavItem icon="search" label="Explore" />
        <NavItem icon="notifications" label="Notifications" />
        <NavItem icon="message" label="Messages" />
        <NavItem icon="lists" label="Lists" />
        <NavItem icon="bookmarks" label="Bookmarks" />
        <NavItem icon="person" label="Profile" onClick={()=>{ if(profile) { window.history.pushState({},'', '/user/'+encodeURIComponent(profile.username)); window.dispatchEvent(new PopStateEvent('popstate')) } }} active={isActive('profile')} />
        <NavItem icon="more_horiz" label="More" />
      </nav>

      <div className="plebx-post-btn">
        <button className="plebx-btn-primary">Post</button>
      </div>

      <div className="plebx-profile-tile">
        <div className="plebx-user-avatar">
          {profile && profile.avatar_url ? <img src={profile.avatar_url} className="plebx-avatar-img" alt="avatar" /> : <div className="plebx-muted">{(profile && (profile.display_name||profile.username)||'G').slice(0,2).toUpperCase()}</div>}
        </div>
        <div className="plebx-user-meta">
          <div className="plebx-user-name">{profile? (profile.display_name || profile.username) : 'Guest'}</div>
          <div className="plebx-user-handle">{profile? '@'+(profile.username||profile.id) : '@guest'}</div>
          <div className="plebx-small-muted mt-8">{counts.followers} Followers · {counts.following} Following</div>
        </div>
      </div>
    </aside>
  )
}
