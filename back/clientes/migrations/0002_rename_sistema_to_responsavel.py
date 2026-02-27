# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cliente',
            old_name='sistema_adquirido',
            new_name='nome_responsavel',
        ),
    ]
