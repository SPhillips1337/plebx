import React, { useState, useEffect, useRef } from 'react'

const API_BASE = 'http://localhost:8010'

export default function Chat({ currentUser, onSelectUser }) {
  const [conversations, setConversations] = useState([])
  const [activeChat, setActiveChat] = useState(null)
  const [messages, setMessages] = useState([])
  const [newMessage, setNewMessage] = useState('')
  const [ws, setWs] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (!currentUser) return
    loadConversations()
    connectWebSocket()
    return () => {
      if (ws) ws.close()
    }
  }, [currentUser])

  useEffect(() => {
    if (ws) {
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'message') {
            const msg = data.data
            if (activeChat && (msg.sender_id === activeChat || msg.receiver_id === activeChat)) {
              setMessages(prev => [...prev, msg])
            }
            loadConversations()
          } else if (data.type === 'typing') {
            // Could show typing indicator
          }
        } catch (e) {}
      }
    }
  }, [ws, activeChat])

  useEffect(() => {
    if (activeChat) {
      loadMessages(activeChat)
    }
  }, [activeChat])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function connectWebSocket() {
    if (!currentUser) return
    try {
      const socket = new WebSocket(`ws://localhost:8010/ws/chat`)
      socket.onopen = () => {
        socket.send(JSON.stringify({ user_id: currentUser }))
      }
      setWs(socket)
    } catch (e) {
      console.error('WebSocket connection failed:', e)
    }
  }

  async function loadConversations() {
    if (!currentUser) return
    try {
      const res = await fetch(`${API_BASE}/chat/conversations`, {
        headers: { 'X-User': currentUser }
      })
      const data = await res.json()
      if (data.ok) setConversations(data.conversations || [])
    } catch (e) {
      console.error('Failed to load conversations:', e)
    }
  }

  async function loadMessages(otherUser) {
    if (!currentUser) return
    try {
      const res = await fetch(`${API_BASE}/chat/${encodeURIComponent(otherUser)}`, {
        headers: { 'X-User': currentUser }
      })
      const data = await res.json()
      if (data.ok) setMessages(data.messages || [])
    } catch (e) {
      console.error('Failed to load messages:', e)
    }
  }

  async function sendMessage(e) {
    e.preventDefault()
    if (!newMessage.trim() || !activeChat || !currentUser) return

    const content = newMessage
    setNewMessage('')

    // Try WebSocket first
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'message',
        receiver_id: activeChat,
        content
      }))
    } else {
      // Fallback to REST
      try {
        const res = await fetch(`${API_BASE}/chat/message`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-User': currentUser },
          body: JSON.stringify({ receiver_id: activeChat, content })
        })
        const data = await res.json()
        if (data.ok && data.message) {
          setMessages(prev => [...prev, data.message])
        }
      } catch (e) {
        console.error('Failed to send message:', e)
      }
    }
  }

  function formatTime(iso) {
    if (!iso) return ''
    const d = new Date(iso)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (!currentUser) {
    return (
      <div className="plebx-chat-empty">
        <p>Set a user ID to view messages</p>
      </div>
    )
  }

  return (
    <div className="plebx-chat-container">
      <div className="plebx-chat-conversations">
        <h3>Messages</h3>
        {conversations.length === 0 ? (
          <p className="plebx-muted">No conversations yet</p>
        ) : (
          conversations.map((conv, i) => (
            <div
              key={i}
              className={`plebx-chat-conv-item ${activeChat === conv.other_user ? 'active' : ''}`}
              onClick={() => setActiveChat(conv.other_user)}
            >
              <div className="plebx-conv-avatar">
                {(conv.other_user || '?').slice(0, 2).toUpperCase()}
              </div>
              <div className="plebx-conv-meta">
                <div className="plebx-conv-user">{conv.other_user}</div>
                <div className="plebx-conv-preview">{conv.last_message?.slice(0, 30)}...</div>
              </div>
              {conv.unread > 0 && <span className="plebx-conv-badge">{conv.unread}</span>}
            </div>
          ))
        )}
      </div>

      <div className="plebx-chat-main">
        {activeChat ? (
          <>
            <div className="plebx-chat-header">
              <span>{activeChat}</span>
            </div>
            <div className="plebx-chat-messages">
              {messages.map((msg, i) => (
                <div
                  key={msg.id || i}
                  className={`plebx-chat-msg ${msg.sender_id === currentUser ? 'sent' : 'received'}`}
                >
                  <div className="plebx-msg-content">{msg.content}</div>
                  <div className="plebx-msg-time">{formatTime(msg.created_at)}</div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
            <form className="plebx-chat-input" onSubmit={sendMessage}>
              <input
                type="text"
                value={newMessage}
                onChange={e => setNewMessage(e.target.value)}
                placeholder="Type a message..."
              />
              <button type="submit">Send</button>
            </form>
          </>
        ) : (
          <div className="plebx-chat-empty">
            <p>Select a conversation to start messaging</p>
          </div>
        )}
      </div>
    </div>
  )
}
