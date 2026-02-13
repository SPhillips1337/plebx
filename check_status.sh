#!/bin/bash
echo "🔍 PlebX System Status Check"
echo "=================================="

echo "📡 Bridge Service:"
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "  ✅ Bridge: Running (http://localhost:8001)"
else
    echo "  ❌ Bridge: Not responding"
fi

echo ""
echo "🌉 Plebbit Daemon:"
if curl -s http://localhost:9138/ > /dev/null 2>&1; then
    echo "  ✅ Daemon: Running (http://localhost:9138)"
else
    echo "  ❌ Daemon: Not running"
    echo "  📋 To start: npm install -g bitsocialhq/bitsocial-cli && bitsocial daemon"
fi

echo ""
echo "🎨 Frontend:"
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "  ✅ Frontend: Running (http://localhost:3000)"
else
    echo "  ❌ Frontend: Not running"
    echo "  📋 To start: cd frontend && npm start"
fi

echo ""
echo "📋 Current Setup:"
echo "  Bridge connects to Plebbit daemon (port 9138)"
echo "  Bridge provides REST API (port 8001)"
echo "  Frontend consumes bridge API (port 3000)"
echo ""
echo "🚀 Quick Test:"
echo "  curl http://localhost:8001/health"
echo "  curl http://localhost:8001/subs"
echo "  curl http://localhost:3000 (if running)"