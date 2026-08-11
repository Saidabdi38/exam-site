UPDATED VIDEOS APP

Changes:
- Removed the "Standalone videos — not courses." text.
- Added website Create Video page for staff.
- Added website Edit Video page for staff.
- Added Manage Videos page for staff.
- Added Video Categories list/create/edit pages for staff.
- Added Create/Edit buttons to Videos pages when the logged-in user is staff.
- Uses existing project CSS only; no CSS file added.

Replace your current videos app with this updated folder.

Then run:
    python manage.py makemigrations videos
    python manage.py migrate
    python manage.py check
    python manage.py runserver

Pages:
    /videos/
    /videos/create/
    /videos/manage/
    /videos/categories/

If you already have data in the videos app, DO NOT delete your database.
Running migrations will add any new model fields needed.
