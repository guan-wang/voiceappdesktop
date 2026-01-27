# 🔒 HTTPS Setup for Mobile Microphone Access

## Why HTTPS is Required

Modern mobile browsers (iOS Safari, Android Chrome) **block microphone access over HTTP** for security. You must use HTTPS, even for local development.

## Quick Setup (Recommended)

### Step 1: Generate SSL Certificate

Run this script:

```powershell
cd web\backend
.\setup_https_python.ps1
```

This creates two files:
- `cert.pem` - SSL certificate
- `key.pem` - Private key

### Step 2: Restart Server

```powershell
.\stop_server.ps1
.\start_server.ps1
```

The server will automatically detect the certificates and use HTTPS!

### Step 3: Access from Phone

Use **HTTPS** (note the 's'):

```
https://192.168.45.151:7860
```

## Handling the Security Warning

Because this is a self-signed certificate, you'll see a warning. This is **normal and safe** for local development.

### On iOS Safari:
1. You'll see "This Connection Is Not Private"
2. Tap **"Show Details"**
3. Tap **"visit this website"**
4. Tap **"Visit Website"** again to confirm
5. The app will load!

### On Android Chrome:
1. You'll see "Your connection is not private"
2. Tap **"Advanced"**
3. Tap **"Proceed to 192.168.45.151 (unsafe)"**
4. The app will load!

### On Desktop Chrome/Edge:
1. You'll see "Your connection is not private"
2. Click **"Advanced"**
3. Click **"Proceed to localhost (unsafe)"**
4. The app will load!

## Troubleshooting

### Problem: "setup_https_python.ps1 failed"

**Solution:** Install cryptography package:

```powershell
cd ..\..  # Go to project root
uv pip install cryptography
cd web\backend
.\setup_https_python.ps1
```

### Problem: Still getting HTTP, not HTTPS

**Check:**
1. Files exist: `dir cert.pem` and `dir key.pem`
2. Server restarted: Run `.\stop_server.ps1` then `.\start_server.ps1`
3. Look for "🔒 HTTPS enabled" message in server logs

### Problem: "NET::ERR_CERT_AUTHORITY_INVALID"

This is **expected and normal** for self-signed certificates. Click "Advanced" → "Proceed" as described above.

### Problem: Can't proceed past security warning on iOS

Try these steps:
1. Settings → Safari → Advanced → Experimental Features
2. Disable "NSURLSession WebSocket" (if present)
3. Try accessing the site again
4. Or use Chrome on iOS instead of Safari

## Alternative: OpenSSL Method

If you have OpenSSL installed:

```powershell
.\setup_https.ps1
```

This does the same thing but uses OpenSSL instead of Python.

## Certificate Details

- **Valid for:** 365 days
- **Includes IPs:** localhost, 127.0.0.1, 192.168.45.151, 10.5.0.2
- **Algorithm:** RSA 2048-bit
- **Self-signed:** Yes (not trusted by default, but safe for local dev)

## Security Notes

### For Local Development (Current Setup):
- ✅ Self-signed certificate is fine
- ✅ Security warning is normal
- ✅ Safe to proceed past warning
- ⚠️ Only use on trusted local network
- ⚠️ Don't use on public WiFi

### For Production Deployment:
- Use HuggingFace (provides real HTTPS automatically)
- Or use Let's Encrypt for free trusted certificates
- Never use self-signed certificates in production

## Verification Checklist

After setup, verify:

- [ ] `cert.pem` exists in `web/backend/`
- [ ] `key.pem` exists in `web/backend/`
- [ ] Server shows "🔒 HTTPS enabled" on startup
- [ ] Can access `https://localhost:7860` from computer
- [ ] Can access `https://192.168.45.151:7860` from phone
- [ ] Browser shows padlock icon (even if with warning)
- [ ] Microphone permission prompt appears on phone

## Testing Microphone Access

Once HTTPS is set up:

1. Access from phone: `https://192.168.45.151:7860`
2. Bypass security warning (tap Advanced → Proceed)
3. Tap the PTT button
4. **You should see the microphone permission prompt!**
5. Tap "Allow"
6. The PTT button should now work!

## Remove SSL (Go Back to HTTP)

If you want to disable HTTPS:

```powershell
cd web\backend
Remove-Item cert.pem
Remove-Item key.pem
.\stop_server.ps1
.\start_server.ps1
```

Server will revert to HTTP.

## Files Added

- `web/backend/cert.pem` - SSL certificate (don't commit to git)
- `web/backend/key.pem` - Private key (don't commit to git)
- `web/backend/setup_https_python.ps1` - Certificate generator (Python)
- `web/backend/setup_https.ps1` - Certificate generator (OpenSSL)

Add to `.gitignore`:
```
cert.pem
key.pem
```

## Summary

1. Run `.\setup_https_python.ps1` to generate certificates
2. Restart server with `.\stop_server.ps1` then `.\start_server.ps1`
3. Access from phone using `https://` (not `http://`)
4. Bypass security warning (safe for local dev)
5. Microphone should now work! 🎤

---

**You're all set! The microphone should work on your phone now.** 🚀
