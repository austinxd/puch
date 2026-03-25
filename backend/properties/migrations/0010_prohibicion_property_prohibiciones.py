from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0009_agent_google_calendar_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='Prohibicion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200, unique=True)),
            ],
            options={
                'verbose_name_plural': 'prohibiciones',
                'ordering': ['nombre'],
            },
        ),
        migrations.AddField(
            model_name='property',
            name='prohibiciones',
            field=models.ManyToManyField(blank=True, to='properties.prohibicion'),
        ),
    ]
