from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0008_agent_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='google_calendar_id',
            field=models.EmailField(
                blank=True,
                default='',
                help_text='Gmail del agente (se usa como Calendar ID)',
                max_length=254,
            ),
        ),
    ]
