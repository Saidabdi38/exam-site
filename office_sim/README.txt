office_sim Django app starter

Install steps:
1. Copy the office_sim folder into your Django project.
2. Add 'office_sim' to INSTALLED_APPS in settings.py.
3. Add path('office/', include('office_sim.urls')) to your main urls.py.
4. Run:
   python manage.py makemigrations office_sim
   python manage.py migrate
5. Register data in Django admin.
6. Optional base.html nav link:
   <a class="navlink" href="{% url 'office_dashboard' %}">Virtual Office</a>
