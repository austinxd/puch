from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0004_systemprompt'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatconversation',
            name='admin_paused_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='chatmessage',
            name='role',
            field=models.CharField(
                choices=[('user', 'User'), ('assistant', 'Assistant'), ('admin', 'Admin')],
                max_length=10,
            ),
        ),
    ]
