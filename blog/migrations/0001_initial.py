# Generated for complete blog app
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BlogCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
                ('slug', models.SlugField(blank=True, max_length=170, unique=True)),
                ('description', models.TextField(blank=True)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['name'], 'verbose_name_plural': 'Blog categories'},
        ),
        migrations.CreateModel(
            name='BlogPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=220)),
                ('slug', models.SlugField(blank=True, max_length=240, unique=True)),
                ('summary', models.TextField(blank=True)),
                ('content', models.TextField()),
                ('featured_image', models.ImageField(blank=True, null=True, upload_to='blog/images/')),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('is_paid', models.BooleanField(default=False)),
                ('is_published', models.BooleanField(default=True)),
                ('featured_post', models.BooleanField(default=False)),
                ('seo_title', models.CharField(blank=True, max_length=220)),
                ('seo_description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('view_count', models.PositiveIntegerField(default=0)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='posts', to='blog.blogcategory')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='blog_posts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='PostPurchase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_reference', models.CharField(max_length=255)),
                ('payment_screenshot', models.ImageField(blank=True, null=True, upload_to='blog/payments/')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('request_date', models.DateTimeField(auto_now_add=True)),
                ('approved_date', models.DateTimeField(blank=True, null=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_post_purchases', to=settings.AUTH_USER_MODEL)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purchases', to='blog.blogpost')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='post_purchases', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-request_date']},
        ),
        migrations.AddConstraint(
            model_name='postpurchase',
            constraint=models.UniqueConstraint(fields=('user', 'post'), name='unique_user_post_purchase'),
        ),
    ]
