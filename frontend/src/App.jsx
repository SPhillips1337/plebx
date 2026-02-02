import React from 'react'
import Feed from './Feed'

export default function App(){
  return (
    <div style={{fontFamily:'Inter,system-ui,Arial,sans-serif',padding:24,background:'linear-gradient(180deg,#f7fafc,#fff)'}}>
      <h1>PlebX — Feed (MVP)</h1>
      <Feed />
    </div>
  )
}
