from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chamados', '0010_emailingestionconfig_destino'),
    ]

    operations = [
        migrations.AddField(
            model_name='chamado',
            name='prioridade_ahp',
            field=models.CharField(blank=True, help_text='Banda calculada pelo AHP: p1, p2, p3, p4 ou revisao_humana.', max_length=20, verbose_name='Prioridade AHP'),
        ),
        migrations.AddField(
            model_name='chamado',
            name='indice_ahp',
            field=models.FloatField(blank=True, null=True, verbose_name='Indice AHP (0-100)'),
        ),
    ]
