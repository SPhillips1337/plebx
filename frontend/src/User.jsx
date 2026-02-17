import React, { useEffect, useState } from 'react'

const API_BASE = 'http://localhost:8010'  // Main API

export default function UserView({ userId }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(false)
  const [counts, setCounts] = useState({ followers: 0, following: 0 })
  useEffect(() => {
    if (!userId) return
    setLoading(true)
    Promise.all([
      fetch(`${API_BASE}/user/${encodeURIComponent(userId)}`).then(r => r.json()),
      fetch(`${API_BASE}/user/${encodeURIComponent(userId)}/counts`).then(r => r.json()),
    ]).then(([uj, cj]) => {
      setUser(uj.user)
      if (cj && cj.counts) setCounts(cj.counts)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [userId])

  if (loading) return <div>Loading user...</div>
  if (!user) return <div>User not found</div>
  return (
    <div className="plebx-card">
      <div className="post-row">
        <div className="plebx-avatar" style={{ width: 72, height: 72 }}>{user.avatar_url ? <img src={user.avatar_url} className="plebx-avatar-img" alt="avatar" /> : (user.display_name || user.username || 'U').slice(0, 2).toUpperCase()}</div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 18 }}>{user.display_name || user.username}</div>
          <div className="plebx-muted">@{user.username}</div>
          {user.bio && <div className="mt-8">{user.bio}</div>}
          <div className="mt-12">
            <strong>{counts.followers}</strong> Followers · <strong>{counts.following}</strong> Following
          </div>
        </div>
      </div>
    </div>
  )
}
