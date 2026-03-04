import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0006_chatconversation_agent'),
        ('properties', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatconversation',
            name='first_property',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='first_intent_conversations',
                to='properties.property',
            ),
        ),
    ]
