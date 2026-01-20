# exam_site (Django Online Exam Starter)

## Features
- Login/logout (Django auth)
- Admin can create Exams, Questions, Choices
- Teacher dashboard (no admin) to create/manage exams and questions
- Teacher can view student attempts and per-question results for their exams
- Students can start an exam, answer MCQs, timer, submit
- Auto grading (MCQ) and result page

## Run (Windows 10)
```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Use
1. Go to /admin and create an Exam (set is_published=True)
2. Add Questions and Choices (mark the correct choice)
3. Go to / and take the exam

## Teacher dashboard
1. Run migrations (the **Teachers** group is auto-created)
2. Go to /admin and add your user to the **Teachers** group
3. Optional: create a **TeacherProfile** record in Admin
4. Visit /teacher/ to create/manage exams and questions

## Teacher dashboard (no admin)
1. In /admin create a Group named **Teachers** and add your user to it
2. Visit /teacher/
3. Create exams, add questions + choices, and publish/unpublish exams
