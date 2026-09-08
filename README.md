 # EduTrack

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

 ## Deploy publicly

 This repository includes `render.yaml` for Render deployment.

 1. Open the [EduTrack GitHub repository](https://github.com/Maffi-Devi/EduTrack).
 2. In Render, choose **New +** and **Blueprint**.
 3. Select this repository and deploy.
 4. Add `GROQ_API_KEY` and `ADMIN_PASSWORD` as private environment variables in Render.
 5. Render will provide the public application URL after deployment.

 Never commit `.env` or a real API key. The repository only contains `.env.example`.

 ## License

 This project is provided for educational and demonstration purposes.
