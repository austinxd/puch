import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0005_chatconversation_admin_paused_until_and_more'),
        ('properties', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatconversation',
            name='agent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='conversations',
                to='properties.agent',
            ),
        ),
    ]
