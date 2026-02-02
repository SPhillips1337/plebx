import React from 'react'
import Feed from './Feed'
import Admin from './Admin'
import {useState} from 'react'

export default function App(){
  const [showAdmin,setShowAdmin] = useState(false)
  return (
    <div style={{fontFamily:'Inter,system-ui,Arial,sans-serif',padding:24,background:'linear-gradient(180deg,#f7fafc,#fff)'}}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <h1>PlebX — Feed (MVP)</h1>
        <div><button onClick={()=>setShowAdmin(s=>!s)}>{showAdmin? 'Close Admin':'Open Admin'}</button></div>
      </div>
      <Feed />
      {showAdmin && <Admin />}
    </div>
  )
}
