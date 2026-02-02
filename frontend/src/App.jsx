import React from 'react'
import Feed from './Feed'
import Admin from './Admin'
import PostView from './Post'
import {useState, useEffect} from 'react'

function parseRoute(){
  const path = window.location.pathname || '/'
  if(path.startsWith('/post/')){
    const id = decodeURIComponent(path.replace('/post/',''))
    return {name: 'post', params: {id}}
  }
  return {name: 'feed'}
}

export default function App(){
  const [showAdmin,setShowAdmin] = useState(false)
  const [route, setRoute] = useState(parseRoute())
  const [currentUser, setCurrentUser] = useState('')

  useEffect(()=>{
    try{ const u = localStorage.getItem('plebx_current_user') || ''; setCurrentUser(u) }catch(e){}
  }, [])

  function saveCurrentUser(){
    try{ localStorage.setItem('plebx_current_user', currentUser||'') }catch(e){}
  }

  useEffect(()=>{
    function onPop(){ setRoute(parseRoute()) }
    window.addEventListener('popstate', onPop)
    return ()=> window.removeEventListener('popstate', onPop)
  }, [])

  return (
    <div className="plebx-app">
      <div className="plebx-header">
        <h1>PlebX — Feed (MVP)</h1>
        <div className="flex gap-8 align-center">
          <input className="plebx-input" placeholder="Act as user id" value={currentUser} onChange={e=>setCurrentUser(e.target.value)} />
          <button onClick={saveCurrentUser} className="plebx-btn-primary">Set</button>
          <button className="plebx-btn-primary" onClick={()=>setShowAdmin(s=>!s)}>{showAdmin? 'Close Admin':'Open Admin'}</button>
        </div>
      </div>

      {route.name === 'feed' && <Feed currentUser={currentUser} />}
      {route.name === 'post' && <PostView postId={route.params.id} currentUser={currentUser} />}

      {showAdmin && <Admin />}
    </div>
  )
}
