# 🕷️ Spider Host - Railway Hosting Guide

## 📋 Prerequisites

1. **GitHub Account** - github.com
2. **Railway Account** - railway.app (Free $5/month credit)
3. **Telegram Bot Token** - From @BotFather
4. **Your Telegram User ID** - From @userinfobot

---

## 🚀 Step-by-Step Deployment

### Step 1: Create GitHub Repository

1. Go to github.com → New Repository
2. Name: `spider-host-bot`
3. Make it **Public**
4. Click "Create repository"

### Step 2: Upload Files to GitHub

Upload these files:
```
├── bot.py
├── requirements.txt
├── Procfile
├── railway.json
└── README.md
```

**How to upload:**
- Click "uploading an existing file"
- Drag all files
- Click "Commit changes"

### Step 3: Connect Railway

1. Go to **railway.app**
2. Sign in with GitHub
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Select your `spider-host-bot` repository
6. Railway will auto-detect Python

### Step 4: Add Environment Variables

Go to **Variables** tab and add:

```
BOT_TOKEN=your_bot_token_here
OWNER_ID=your_user_id
OWNER_ID_2=second_owner_id
ADMIN_ID=your_user_id
YOUR_USERNAME=@your_username
YOUR_USERNAME_2=@second_username
CHANNEL_ID=-100xxxxxxxxxx
CHANNEL_NAME=🕷️ Spider Host Official
CHANNEL_LINK=https://t.me/your_channel
WELCOME_IMAGE_URL=https://cdn.phototourl.com/free/2026-07-15-b653e649-55d7-42e9-8afc-2206ba69ac61.gif
MAIN_LINK_URL=https://t.me/your_channel
MAIN_LINK_TEXT=🔗 Join Channel
```

### Step 5: Deploy

1. Railway will auto-deploy
2. Check **Deployments** tab for status
3. Bot should start automatically

---

## 🔧 How to Get Values

### Bot Token
1. Open Telegram → @BotFather
2. Send `/newbot`
3. Choose name → Copy token

### Your User ID
1. Open Telegram → @userinfobot
2. Send any message
3. Copy your User ID

### Channel ID
1. Forward a message from your channel to @userinfobot
2. Copy the ID (starts with -100)

### Channel must be public or private?
- **Public**: Use `@channelname` in CHANNEL_LINK
- **Private**: Use `https://t.me/+invite_link`

---

## ⚠️ Important Notes

1. **Bot must be ADMIN in your channel**
   - Go to channel settings
   - Add bot as admin
   - Give "Read members" permission

2. **Free Railway Credit**
   - $5 free per month
   - Bot uses ~$1-2/month
   - Add payment if needed

3. **Check Logs**
   - Railway dashboard → Deployments
   - Click on deployment → Logs

---

## 🔄 Update Bot

1. Edit `bot.py` locally
2. Push to GitHub
3. Railway auto-redeploys

---

## ❓ Troubleshooting

**Bot not starting?**
- Check Environment Variables are correct
- Check Deploy Logs for errors

**Channel verification not working?**
- Bot must be admin in channel
- Channel ID must be correct

**Bot stops after some time?**
- Check if free credit is used up
- Add payment method

---

## 📁 Files Included

| File | Purpose |
|------|---------|
| bot.py | Main bot code |
| requirements.txt | Python dependencies |
| Procfile | Railway process type |
| railway.json | Railway config |
| README.md | Documentation |

---

## 🎯 Quick Commands After Deploy

- `/start` - Start bot
- `/status` - Check statistics
- `/adminpanel` - Admin panel
- `/ping` - Test response time

---

**🕷️ Spider Host - Ready to Deploy!**
# SPIDER-HOST-
