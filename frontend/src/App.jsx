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

  useEffect(()=>{
    function onPop(){ setRoute(parseRoute()) }
    window.addEventListener('popstate', onPop)
    return ()=> window.removeEventListener('popstate', onPop)
  }, [])

  return (
    <div style={{fontFamily:'Inter,system-ui,Arial,sans-serif',padding:24,background:'linear-gradient(180deg,#f7fafc,#fff)'}}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <h1>PlebX — Feed (MVP)</h1>
        <div><button onClick={()=>setShowAdmin(s=>!s)}>{showAdmin? 'Close Admin':'Open Admin'}</button></div>
      </div>

      {route.name === 'feed' && <Feed />}
      {route.name === 'post' && <PostView postId={route.params.id} />}

      {showAdmin && <Admin />}
    </div>
  )
}
