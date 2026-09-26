# EduTrack

## Live Demo

Open the deployed application: [https://maffi.pythonanywhere.com](https://maffi.pythonanywhere.com/)

 EduTrack is a Flask-based student performance dashboard with marks, targets, study notes, exam timetable, PDF reports, and an EduBot academic assistant.

 ## Features

 - Student registration and login
 - Marks, grades, GPA, targets, and recommendations
 - Exam timetable and study notes
 - PDF performance report
 - EduBot powered by Groq when `GROQ_API_KEY` is configured
 - Offline EduBot fallback when no API key is available

 ## Run locally

 ```powershell
 py -m pip install -r requirements.txt
 Copy-Item .env.example .env
 ```

 Edit `.env` and set these values:

 ```env
 GROQ_API_KEY=your_groq_api_key
 SECRET_KEY=your_long_random_secret
 ADMIN_PASSWORD=your_strong_admin_password
 ```

 Start the app:

 ```powershell
 py app.py
 ```

 Open http://127.0.0.1:5000.

 ## Admin panel

 Set `ADMIN_PASSWORD` before the first start; an `admin` account is created with it.
 Log in as `admin` to open `/admin`, which shows:

 - total students, students with and without marks, overall average, students with a failed subject
 - semester-wise summary and top performers
 - a searchable list of all students
 - a detail page per student (marks by semester, targets, exams, notes), their PDF report,
   and an option to delete the student with all their data

 ## Deploy on PythonAnywhere (recommended free option)

 PythonAnywhere keeps files on disk, so the SQLite database survives restarts.
 On Render's free plan the disk is wiped on every deploy/restart, which deletes all accounts and marks.

 1. Create a free account at [pythonanywhere.com](https://www.pythonanywhere.com/).
 2. Open a **Bash console** and run:

    ```bash
    git clone https://github.com/Maffi-Devi/EduTrack.git
    cd EduTrack
    python3.12 -m venv ~/edutrack-venv
    source ~/edutrack-venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    nano .env      # fill GROQ_API_KEY, SECRET_KEY, ADMIN_PASSWORD, SESSION_COOKIE_SECURE=true
    ```

 3. **Web** tab → **Add a new web app** → **Manual configuration** → Python 3.12.
 4. Set **Virtualenv** to `/home/<username>/edutrack-venv`.
 5. Open the **WSGI configuration file** and replace its contents with:

    ```python
    import sys, os
    project = '/home/<username>/EduTrack'
    sys.path.insert(0, project)
    os.chdir(project)
    from app import app as application
    ```

 6. Under **Static files** add URL `/static/` → directory `/home/<username>/EduTrack/static`.
 7. Turn on **Force HTTPS**, click **Reload**, and open `https://<username>.pythonanywhere.com`.

 To update later: `cd ~/EduTrack && git pull`, then **Reload** in the Web tab.
 Free web apps must be kept running by logging in at least once a month and clicking
 **Run until 1 month from today** in the Web tab (PythonAnywhere emails a reminder a week before).

 ## Deploy publicly on Render

 This repository includes `render.yaml` for Render deployment.

 1. Open the [EduTrack GitHub repository](https://github.com/Maffi-Devi/EduTrack).
 2. In Render, choose **New +** and **Blueprint**.
 3. Select this repository and deploy.
 4. Add `GROQ_API_KEY` and `ADMIN_PASSWORD` as private environment variables in Render.
 5. Render will provide the public application URL after deployment.

 > **Warning:** the free Render disk is temporary. The SQLite database is erased on every
 > deploy or restart. Keep data by adding a paid persistent disk and setting `DB_PATH`
 > to a file on it (for example `/var/data/edutrack.db`), or use PythonAnywhere.

 Never commit `.env` or a real API key. The repository only contains `.env.example`.

 ## Keep the Render service warm

 The app provides a public `GET /health` endpoint that returns HTTP 200 and
 `{"status":"ok"}` without querying the database or calling external APIs.
 `render.yaml` uses this route for deployment health checks. Render health checks
 alone are not an external keep-alive schedule.

 After deploying these changes, create a job at [cron-job.org](https://cron-job.org/):

 - Title: `EduTrack keep-alive`
 - URL: `https://edutrack-4rxz.onrender.com/health` (replace the hostname if needed)
 - Method: `GET`, with no authentication or request body
 - Schedule: every 5 minutes, all hours and days (`*/5 * * * *`)
 - Enable the job and failure notifications, then run a test and confirm HTTP 200.

 The schedule must run on an external service: an in-app timer stops when Render
 puts the app to sleep. Creating this endpoint does not activate the cron job;
 the job must be saved and enabled in your cron-job.org account.

 [Render Free services](https://render.com/docs/free) sleep after 15 minutes without
 inbound traffic. Regular pings can reduce idle cold starts, but cannot guarantee
 immediate responses during restarts, deploys, or scheduler outages. Free instance
 hours are limited to 750 per workspace per month and shared across services;
 keeping a service awake consumes those hours. For guaranteed avoidance of idle
 spin-down, use a paid instance.

 ## License

 This project is provided for educational and demonstration purposes.
