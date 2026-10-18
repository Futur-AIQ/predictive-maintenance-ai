# Deployment Guide — Render (backend) + Vercel (frontend)

Step-by-step guide to put the app online on the free plans of Render and Vercel.

| Part | Host | Source in this repo | Final address |
|------|------|---------------------|---------------|
| Backend (FastAPI + AI) | Render | `render.yaml` → `backend/` | `https://<service>.onrender.com` |
| Frontend (Next.js) | Vercel | `frontend/` | `https://<project>.vercel.app` |

**Order matters:** backend first (the frontend needs its URL), then frontend, then tell the backend the frontend's URL (CORS).

Time needed: about 20–30 minutes, most of it waiting for the first Render build.

---

## 0. Before you start

You need:

- [ ] A **GitHub** account with access to this repo, and the latest code pushed to `main`
- [ ] A **Render** account — sign up at https://render.com with GitHub
- [ ] A **Vercel** account — sign up at https://vercel.com with GitHub
- [ ] An **LLM API key**: an OpenRouter key and model name (e.g. from https://openrouter.ai/keys), or an Anthropic or OpenAI key
- [ ] Two **new passwords** for the app's built-in users (admin and engineer). Do not reuse `Admin@123` / `Engineer@123`: the repo is public, so those are public.
- [ ] A **NextAuth secret**. Generate it now in a terminal and keep it for step 2:

  ```bash
  openssl rand -base64 32
  ```

> **Repo in a GitHub organization?** Render and Vercel can only see it after their GitHub apps are allowed on that organization. Both sites show a "Configure GitHub App" / "Adjust GitHub App Permissions" link when the repo isn't listed. An organization owner may need to approve it.

---

## 1. Deploy the backend on Render

### 1.1 Create the service from the Blueprint

1. Open https://dashboard.render.com.
2. Click **New +** → **Blueprint**.
3. Connect GitHub if asked, then select this repository.
4. Branch: **main**. Blueprint file path: leave the default (`render.yaml`).
5. Give the Blueprint a name, e.g. `predictive-maintenance`.
6. Render lists one service, **predictive-maintenance-api** (Free), and asks for the values marked as secrets:

   | Variable | What to enter |
   |----------|---------------|
   | `ADMIN_PASSWORD` | Your new admin password |
   | `ENGINEER_PASSWORD` | Your new engineer password |
   | `OPENROUTER_API_KEY` | Your OpenRouter key (leave blank if you use Anthropic/OpenAI, see note) |
   | `OPENROUTER_MODEL` | The OpenRouter model ID you use locally (same value as in `backend/.env`) |
   | `CORS_ORIGINS` | `http://localhost:3000` for now. You'll replace it in step 3. |

   `SECRET_KEY` is generated automatically. All other settings come from `render.yaml`.

   > Using Anthropic or OpenAI instead of OpenRouter? Leave both OpenRouter fields blank. After the service is created, go to **Environment** and add `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`.

7. Click **Apply** (or **Deploy Blueprint**).

### 1.2 Wait for the first build

Open the service → **Logs**. The first build takes several minutes. It:

1. Installs CPU-only PyTorch and the Python packages
2. Runs `scripts/prebuild.py`, which downloads the embedding model and builds the search index

You are looking for these lines, in this order:

```
Ingestion complete: {'technical_docs_count': 128, 'maintenance_history_count': 50}
Prebuild complete.
...
Collections already populated: ... Skipping ingestion.
Application startup complete.
```

The service status turns **Live**.

### 1.3 Check the backend

Copy the service URL from the top of the service page (e.g. `https://predictive-maintenance-api.onrender.com`).

- Open `https://<service>.onrender.com/api/health` → should show `{"status":"ok", ...}`
- Open `https://<service>.onrender.com/docs` → the interactive API docs

Keep the URL for the next step.

---

## 2. Deploy the frontend on Vercel

### 2.1 Import the project

1. Open https://vercel.com/new.
2. Under **Import Git Repository**, find this repo and click **Import**.
3. **Project Name**: choose it now. It decides your address, `https://<project-name>.vercel.app` (Vercel adds a suffix if the name is taken).
4. **Root Directory**: click **Edit** and select `frontend`. This step is required.
5. **Framework Preset**: Next.js (detected automatically). Leave build settings at their defaults.

### 2.2 Environment variables

Open **Environment Variables** on the same screen and add:

| Name | Value |
|------|-------|
| `NEXT_API_URL` | Your Render URL, e.g. `https://predictive-maintenance-api.onrender.com`. Must start with `https://` and have **no trailing slash**. |
| `NEXTAUTH_SECRET` | The value you generated with `openssl rand -base64 32` |
| `NEXTAUTH_URL` | `https://<project-name>.vercel.app` (from step 2.1). If Vercel ends up giving a different address, fix this in step 2.3. |

Click **Deploy**. The build takes 1–2 minutes.

> **Why `NEXT_API_URL` and not `NEXT_PUBLIC_API_URL`?** Vercel's dashboard fails to save `NEXT_PUBLIC_` variables for this repo layout ("Failed to verify the project's public environment variable prefix"). `frontend/next.config.ts` exposes `NEXT_API_URL` to the browser instead. Don't rename it back.

### 2.3 Note the production address

When the deploy finishes, go to the project's **Overview** and copy the **Domains** entry (e.g. `https://pm-ai.vercel.app`). Use this production domain, not the long per-deployment URL.

If it differs from the `NEXTAUTH_URL` you entered, go to **Settings → Environment Variables**, correct `NEXTAUTH_URL`, then **Deployments** → **⋯** on the latest one → **Redeploy**.

---

## 3. Connect frontend and backend (CORS)

The backend only accepts browser requests from addresses listed in `CORS_ORIGINS`.

1. In Render, open **predictive-maintenance-api** → **Environment**.
2. Edit `CORS_ORIGINS` and set it to your Vercel production address, exactly, e.g.:

   ```
   https://pm-ai.vercel.app
   ```

   Use `https://`, no trailing slash, no spaces. To also allow local development, separate with a comma: `https://pm-ai.vercel.app,http://localhost:3000`
3. Click **Save, rebuild, and deploy** (or **Save changes** and then **Manual Deploy → Deploy latest commit**).
4. Wait until the service is **Live** again.

---

## 4. Check that everything works

1. Open your Vercel address. You should be redirected to the login page.
2. Log in as `engineer@pm-system.com` with your `ENGINEER_PASSWORD`.
   - If the backend was asleep, the first login can take up to a minute.
3. **Dashboard** loads with a red critical-equipment banner and health cards.
4. **Equipment → Engine-05 → Run Diagnostic**, ask "What is causing the high temperature readings?". You get a CRITICAL diagnosis and a work order ID.
5. **Work Orders**: change the new order's status to IN_PROGRESS. You should see "Status updated".
6. Log out, log in as `admin@pm-system.com` with your `ADMIN_PASSWORD`, and open **Admin**. Both users are listed.

---

## 5. After deployment

- **Automatic deploys:** every push to `main` redeploys both services.
- **Changing `NEXT_API_URL`** only takes effect after a Vercel **Redeploy**, because it is built into the frontend at build time.
- **Free plan behaviour (expected):**
  - The backend sleeps after 15 minutes without traffic. The next visit wakes it in about a minute, and everyone has to log in again.
  - Every deploy, restart or sleep **resets the database**: work orders, diagnostic history and users created in the Admin screen disappear. The admin and engineer users are recreated with the passwords set in Render.
  - Before a demo, open the site a minute early so the backend is awake.
- **RAG evaluation** (Admin → Evaluation → Run) makes many LLM calls. It hasn't been tested end to end on the 512 MB free instance, so run it once before relying on it in a demo.

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Render build fails mentioning the Python version | `3.11.16` not available on Render | In `render.yaml`, change `PYTHON_VERSION` to another 3.11 release (e.g. `3.11.11`), push |
| Render shows "Out of memory" / service restarts | Memory-saving settings missing | In Render → Environment, confirm `EMBEDDING_BACKEND=onnx` and `ENABLE_RERANKER=false` |
| Login says "Invalid email or password" with the right password | Backend asleep, wrong `NEXT_API_URL`, or different password set in Render | Open `/api/health` on Render to wake it and retry; check the Vercel variable and redeploy; check `ENGINEER_PASSWORD` in Render |
| Logged in, but dashboard is empty; browser console shows a **CORS** error | `CORS_ORIGINS` doesn't exactly match the Vercel address | Fix the value in step 3 (https, no trailing slash) and redeploy the backend |
| Vercel: "Failed to verify the project's public environment variable prefix" when adding a variable | A variable named `NEXT_PUBLIC_…` was added | Use the name `NEXT_API_URL` (see the note in step 2.2) |
| Site loads but every request goes to `localhost:8000` | `NEXT_API_URL` was missing or misspelled at build time | Set it in Vercel → Settings → Environment Variables, then Redeploy |
| Browser console shows **Mixed Content** | `NEXT_API_URL` starts with `http://` | Change to `https://`, redeploy on Vercel |
| Login works on the main domain but not on a preview URL | Preview deployments aren't in `CORS_ORIGINS` | Use the production domain, or add that preview URL to `CORS_ORIGINS` |
| Suddenly logged out | Backend restarted or slept, or the 30-minute access token expired | Log in again. Expected on the free plan. |
| Diagnostic returns "Unable to perform diagnosis" | LLM key/model missing or wrong | Check `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` (or Anthropic/OpenAI key) in Render → Environment; check Render logs |
