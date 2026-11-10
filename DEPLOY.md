# Deploying Dropa

This guide puts Dropa on Render with a PostgreSQL database. The code reads
everything from environment variables, so the same steps work on other hosts.

## Before you start
- Your code is pushed to GitHub.
- `requirements.txt`, `build.sh` and `.gitattributes` are in the repo root.
- Run `python manage.py check` locally and fix anything it reports.

## 1. Create the database
Render dashboard > New > PostgreSQL. Pick the region closest to your users
(check the current list), and a paid plan. Free databases expire. Copy the
**Internal Database URL**.

## 2. Create the web service
New > Web Service > connect your GitHub repo.

| Setting | Value |
|---|---|
| Runtime | Python |
| Build command | `./build.sh` |
| Start command | `gunicorn config.wsgi:application` |
| Instance type | a paid one (a persistent disk needs it) |
| Health check path | `/healthz` |

Add a **disk**: name `dropa-data`, mount path `/var/data`, 1 GB to start.

## 3. Environment variables
| Name | Value |
|---|---|
| `SECRET_KEY` | a long random string (generate one, never reuse your laptop's) |
| `DATABASE_URL` | the Internal Database URL from step 1 |
| `DATA_DIR` | `/var/data` |
| `PYTHON_VERSION` | the same version as `python --version` on your laptop |
| `DJANGO_SUPERUSER_PHONE` | `254...` (your admin phone, 254 format) |
| `DJANGO_SUPERUSER_NAME` | your name |
| `DJANGO_SUPERUSER_PASSWORD` | a strong password (delete this variable after the first deploy) |
| `DROPA_SIMULATE_PAYMENTS` | `True` until real M-Pesa is connected |

Render sets the site address itself, so `ALLOWED_HOSTS` is not needed until you
add your own domain (then set `ALLOWED_HOSTS=yourdomain.com` and
`CSRF_TRUSTED_ORIGINS=https://yourdomain.com`).

## 4. First checks after the deploy
1. Open `https://<your-service>.onrender.com/healthz`. It should say `ok`.
2. Log in at `/admin/` with your admin account, then set up your Zone and Blocks.
3. Create a test vendor, upload a document, and check you can open it as admin
   but a different logged-in user gets a 404 for the same link.
4. Redeploy once and check the uploaded document is still there (this confirms
   the disk is mounted).

## 5. The daily payout run
New > Cron Job, same repo and environment variables (not the disk).
Build command `./build.sh`, command `python manage.py run_payouts`,
schedule `0 15 * * *` (15:00 UTC is 18:00 in Nairobi).

## 6. Later
- Turn on HSTS once HTTPS works everywhere: `SECURE_HSTS_SECONDS=31536000`.
- Move uploads to an S3-compatible bucket by setting `S3_PRIVATE_BUCKET`,
  `S3_PUBLIC_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`,
  `S3_ENDPOINT_URL` (and `S3_REGION` if the service needs it). No code change.
- Take regular database backups and test restoring one.
