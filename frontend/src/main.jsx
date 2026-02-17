import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'
import './theme.css'
import './LeftSidebar'

// SSE: subscribe to server events and re-dispatch as window events
if (typeof window !== 'undefined' && window.EventSource) {
  try {
    const es = new EventSource('http://localhost:8010/events')
    es.onmessage = (evt) => {
      try {
        const payload = JSON.parse(evt.data)
        if (payload.event === 'follow') {
          const d = payload.data || {}
          // re-dispatch as custom DOM event for React components
          window.dispatchEvent(new CustomEvent('plebx:follow', { detail: { authorId: d.followee, nowFollowing: d.action === 'follow', action: d.action, follower: d.follower } }))
        } else if (payload.event === 'post') {
          const d = payload.data || {}
          window.dispatchEvent(new CustomEvent('plebx:post', { detail: { post: d.post } }))
        }
      } catch (e) {/* ignore parse errors */ }
    }
    es.onerror = (e) => {
      // keep silent; SSE auto-reconnects
    }
  } catch (e) {/* ignore */ }
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
