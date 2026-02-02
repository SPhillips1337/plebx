import React from 'react'

function NavItem({icon, label, onClick}){
  return (
    <div className="plebx-nav-item" onClick={onClick} role="button">
      <span className="material-symbols-outlined">{icon}</span>
      <span className="plebx-nav-label">{label}</span>
    </div>
  )
}

export default function LeftSidebar({onHome}){
  return (
    <aside className="plebx-sidebar">
      <div className="plebx-logo" onClick={onHome} role="button">PlebX</div>

      <nav className="plebx-nav">
        <NavItem icon="home" label="Home" onClick={onHome} />
        <NavItem icon="search" label="Explore" />
        <NavItem icon="notifications" label="Notifications" />
        <NavItem icon="message" label="Messages" />
        <NavItem icon="lists" label="Lists" />
        <NavItem icon="bookmarks" label="Bookmarks" />
        <NavItem icon="person" label="Profile" />
        <NavItem icon="more_horiz" label="More" />
      </nav>

      <div className="plebx-post-btn">
        <button className="plebx-btn-primary">Post</button>
      </div>

      <div className="plebx-profile-tile">
        <div className="plebx-user-avatar"><div className="plebx-avatar-img"/></div>
        <div className="plebx-user-meta">
          <div className="plebx-user-name">Guest</div>
          <div className="plebx-user-handle">@guest</div>
        </div>
      </div>
    </aside>
  )
}
