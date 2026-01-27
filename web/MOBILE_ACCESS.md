# 📱 Accessing Web App from Phone

## Quick Start

### Step 1: Find Your Computer's IP Address

Run this script:

```powershell
cd web\backend
.\get_local_ip.ps1
```

This will show something like:
```
🌐 Your Computer's IP Address(es):

   Interface: Wi-Fi
   IP Address: 192.168.1.100

   📱 Access from phone:
   http://192.168.1.100:7860
```

### Step 2: Configure Windows Firewall

**Option A: Run the automatic script (Recommended)**

Open PowerShell **as Administrator**:
1. Right-click PowerShell → "Run as Administrator"
2. Navigate to the backend folder:
   ```powershell
   cd C:\Users\Guan\Projects\agents\korean_voice_tutor\web\backend
   ```
3. Run the firewall script:
   ```powershell
   .\allow_firewall.ps1
   ```

**Option B: Manual Configuration**

1. Open Windows Defender Firewall with Advanced Security
2. Click "Inbound Rules" → "New Rule"
3. Select "Port" → Next
4. TCP, Specific local ports: `7860` → Next
5. Allow the connection → Next
6. Check all profiles (Domain, Private, Public) → Next
7. Name: "Korean Voice Tutor Web App" → Finish

### Step 3: Access from Phone

1. **Connect phone to SAME WiFi network** as your computer
2. Open a browser on your phone (Chrome, Safari, etc.)
3. Enter the URL shown by the script (e.g., `http://192.168.1.100:7860`)
4. The web app should load!

## Verification Checklist

✅ **Server is running**
```powershell
cd web\backend
.\start_server.ps1
```

✅ **Server is listening on 0.0.0.0** (not just localhost)
- Check server.py line 172: `uvicorn.run(app, host="0.0.0.0", port=7860)`
- ✅ Already configured correctly!

✅ **Phone on same WiFi network**
- Check WiFi name matches on both devices

✅ **Firewall allows port 7860**
- Run `.\allow_firewall.ps1` as Administrator

✅ **Computer IP address is correct**
- Run `.\get_local_ip.ps1` to double-check

## Troubleshooting

### Problem: "Can't reach this page" or connection timeout

**Check 1: Same Network?**
```
Computer WiFi: [Check network name]
Phone WiFi:    [Check network name]
→ Must be IDENTICAL
```

**Check 2: Server Running?**
```powershell
# Should see server logs
cd web\backend
.\start_server.ps1
```

**Check 3: Firewall Blocking?**
```powershell
# Run as Administrator
.\allow_firewall.ps1
```

**Check 4: Correct IP?**
```powershell
.\get_local_ip.ps1
# Use the IP from Wi-Fi adapter (usually 192.168.x.x)
```

### Problem: Loads but microphone doesn't work

This is normal! Mobile browsers have strict HTTPS requirements for microphone access.

**Solution: Use HTTPS with self-signed certificate**

Quick setup:
```powershell
# Generate self-signed certificate (one-time)
cd web\backend
```

Then update `server.py` to use SSL:
```python
uvicorn.run(
    app, 
    host="0.0.0.0", 
    port=7860,
    ssl_keyfile="key.pem",
    ssl_certfile="cert.pem"
)
```

Access via: `https://192.168.1.100:7860`

**Note:** You'll see a security warning (because it's self-signed). Click "Advanced" → "Proceed anyway"

### Problem: Works on WiFi but not mobile data

This is expected! The local IP (192.168.x.x) only works on the same local network.

**For external access, you need one of:**
1. **Port forwarding** on your router (security risk)
2. **Deploy to cloud** (HuggingFace, Render, etc.)
3. **Use a tunnel service** (ngrok, localtunnel, cloudflare tunnel)

## Network Architecture

```
Your Local Network (192.168.1.x)
│
├── Computer (192.168.1.100)
│   └── Server running on 0.0.0.0:7860
│       ├── Accessible via localhost:7860 (from computer)
│       └── Accessible via 192.168.1.100:7860 (from network)
│
└── Phone (192.168.1.101)
    └── Browser connects to 192.168.1.100:7860
```

## Security Notes

### Current Setup: Development Only

- No authentication
- HTTP only (not HTTPS)
- Exposes API key on network
- **DO NOT use on public WiFi**
- **DO NOT expose to internet**

### For Production:

1. Use HTTPS (SSL/TLS)
2. Add user authentication
3. Move API key to server-side only
4. Deploy to secure cloud platform (HuggingFace)
5. Use environment-based configuration

## Quick Commands Reference

### Get IP Address
```powershell
.\get_local_ip.ps1
```

### Allow Firewall (as Admin)
```powershell
.\allow_firewall.ps1
```

### Start Server
```powershell
.\start_server.ps1
```

### Stop Server
```powershell
.\stop_server.ps1
```

### Check Firewall Rules
```powershell
Get-NetFirewallRule -DisplayName "*Korean Voice Tutor*"
```

### Remove Firewall Rule
```powershell
Remove-NetFirewallRule -DisplayName "Korean Voice Tutor Web App (Port 7860)"
```

## Advanced: Using ngrok (for external access)

If you need to access from outside your local network:

1. **Install ngrok**: https://ngrok.com/download
2. **Start your server** (port 7860)
3. **Run ngrok**:
   ```powershell
   ngrok http 7860
   ```
4. **Use the forwarding URL** (e.g., `https://abc123.ngrok.io`)

**Benefits:**
- Works from anywhere (not just local network)
- Automatic HTTPS
- No firewall configuration needed

**Drawbacks:**
- Requires internet connection
- Free tier has limitations
- Temporary URLs (change each time)

## Testing Checklist

Before using on phone:

- [ ] Server starts without errors
- [ ] Ran `get_local_ip.ps1` and noted IP address
- [ ] Ran `allow_firewall.ps1` as Administrator
- [ ] Phone connected to same WiFi network
- [ ] Can access `http://[IP]:7860` from computer browser
- [ ] Can access `http://[IP]:7860` from phone browser
- [ ] PTT button works on phone
- [ ] Audio plays on phone

## Common IP Address Ranges

Your local IP should look like one of these:

- `192.168.x.x` (most common for home routers)
- `10.0.x.x` (some home routers)
- `172.16.x.x` to `172.31.x.x` (less common)

**NOT these:**
- `127.0.0.1` (localhost - only works on same computer)
- `169.254.x.x` (no network - not connected)

## Need Help?

If still having issues:

1. Share output of `.\get_local_ip.ps1`
2. Share output of `.\allow_firewall.ps1`
3. Share server logs when accessing from phone
4. Confirm both devices on same WiFi network

---

**Good luck! 🚀 You should be able to access from your phone now!**
