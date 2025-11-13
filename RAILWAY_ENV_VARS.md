# Railway Environment Variables for Dashboard Integration

## Required New Variables

Add these environment variables to your Railway project:

### Auth0 Configuration

```bash
AUTH0_DOMAIN=brikk-dashboard.us.auth0.com
AUTH0_AUDIENCE=https://api.getbrikk.com
```

### CORS Configuration

Update the existing `CORS_ALLOWED_ORIGINS` to include the dashboard:

```bash
CORS_ALLOWED_ORIGINS=https://beta.getbrikk.com,https://api.getbrikk.com,https://brikk-website.netlify.app,https://www.getbrikk.com,https://getbrikk.com,http://localhost:3000,https://dashboard.getbrikk.com
```

## Existing Variables (Verify These Exist)

These should already be set from previous configuration:

```bash
# Database
DATABASE_URL=postgresql://...

# Stripe
STRIPE_SECRET_KEY=sk_live_...
PRICE_FREE=price_...
PRICE_HACKER=price_...
PRICE_STARTER=price_...
PRICE_PRO=price_...

# API Key Encryption
BRIKK_ENCRYPTION_KEY=...

# JWT
BRIKK_JWT_SECRET=...
JWT_SECRET=...

# App Config
SECRET_KEY=...
BRIKK_BASE_URL=https://api.getbrikk.com
```

## How to Add Variables in Railway

1. Go to https://railway.app
2. Select your `brikk-infrastructure` project
3. Click on the service
4. Go to "Variables" tab
5. Click "New Variable"
6. Add each variable one by one
7. Railway will automatically redeploy after you save

## Testing After Deployment

Once deployed, test the endpoints:

### 1. Health Check
```bash
curl https://brikk-production-9913.up.railway.app/health
```

### 2. Test Auth0 Login (from dashboard)
- Go to https://dashboard.getbrikk.com
- Log in with Auth0
- Check browser console for any errors

### 3. Test User Sync
```bash
# This will be called automatically by the dashboard after login
# You can test it manually with a valid Auth0 token:
curl -X POST https://brikk-production-9913.up.railway.app/api/users/sync \
  -H "Authorization: Bearer YOUR_AUTH0_TOKEN"
```

### 4. Test Checkout Complete (Public Endpoint)
```bash
# This will be called by the dashboard after Stripe checkout
# Test with a real Stripe session ID:
curl -X POST https://brikk-production-9913.up.railway.app/api/billing/checkout-complete \
  -H "Content-Type: application/json" \
  -d '{"session_id": "cs_test_..."}'
```

## Database Migration

After deployment, Railway should automatically run the migration. If not, you can run it manually:

```bash
# SSH into Railway container or run via Railway CLI
alembic upgrade head
```

## Troubleshooting

### If Auth0 verification fails:
- Check that `AUTH0_DOMAIN` and `AUTH0_AUDIENCE` are set correctly
- Check Railway logs for error messages
- Verify Auth0 API audience matches the one in the dashboard

### If CORS errors occur:
- Check that `CORS_ALLOWED_ORIGINS` includes `https://dashboard.getbrikk.com`
- Check that the dashboard is using the correct API URL

### If database errors occur:
- Check that the migration ran successfully
- Check Railway logs for migration errors
- Manually run `alembic upgrade head` if needed

## Next Steps

1. ✅ Push code to GitHub (DONE)
2. ⏳ Add environment variables to Railway
3. ⏳ Wait for Railway deployment
4. ⏳ Run database migration
5. ⏳ Test dashboard login
6. ⏳ Test end-to-end flow (signup → checkout → dashboard)
