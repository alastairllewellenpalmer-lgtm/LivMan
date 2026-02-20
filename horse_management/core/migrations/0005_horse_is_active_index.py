from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_placement_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='horse',
            name='is_active',
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text='False if horse has left permanently',
            ),
        ),
    ]
