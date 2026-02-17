from django.db import models


class Agent(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Property(models.Model):
    class Clase(models.TextChoices):
        INDUSTRIAL = 'Industrial', 'Industrial'
        COMERCIAL = 'Comercial', 'Comercial'
        RESIDENCIAL = 'Residencial', 'Residencial'

    class Operacion(models.TextChoices):
        VENTA = 'Venta', 'Venta'
        ALQUILER = 'Alquiler', 'Alquiler'

    identificador = models.CharField(max_length=50, unique=True)
    clase = models.CharField(max_length=20, choices=Clase.choices, default=Clase.RESIDENCIAL)
    agent = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True, related_name='properties')
    nombre = models.CharField(max_length=300)
    tipologia = models.CharField(max_length=200, blank=True, default='')
    operacion = models.CharField(max_length=20, choices=Operacion.choices, default=Operacion.VENTA)
    link_maps = models.URLField(max_length=500, blank=True, default='')
    distrito = models.CharField(max_length=200, blank=True, default='')
    pitch = models.TextField(blank=True, default='')
    calle = models.CharField(max_length=300, blank=True, default='')
    direccion = models.CharField(max_length=500, blank=True, default='')
    referencia = models.TextField(blank=True, default='')
    antiguedad = models.CharField(max_length=100, blank=True, default='')
    precio = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    costo_mantenimiento = models.CharField(max_length=200, blank=True, default='')
    metraje = models.CharField(max_length=500, blank=True, default='')
    vista = models.CharField(max_length=200, blank=True, default='')
    distribucion = models.TextField(blank=True, default='')
    ascensor = models.CharField(max_length=100, blank=True, default='')
    habitaciones = models.CharField(max_length=100, blank=True, default='')
    cocheras = models.CharField(max_length=100, blank=True, default='')
    cantidad_pisos = models.CharField(max_length=100, blank=True, default='')
    tipo_cocina = models.CharField(max_length=200, blank=True, default='')
    terraza_balcon = models.CharField(max_length=200, blank=True, default='')
    piso = models.CharField(max_length=100, blank=True, default='')
    banos = models.CharField(max_length=100, blank=True, default='')
    cuarto_servicio = models.CharField(max_length=100, blank=True, default='')
    bano_servicio = models.CharField(max_length=100, blank=True, default='')
    documentacion = models.TextField(blank=True, default='')
    parametros_usos = models.TextField(blank=True, default='')
    financiamiento = models.TextField(blank=True, default='')
    imagen_1 = models.URLField(max_length=500, blank=True, default='')
    imagen_2 = models.URLField(max_length=500, blank=True, default='')
    imagen_3 = models.URLField(max_length=500, blank=True, default='')
    imagen_4 = models.URLField(max_length=500, blank=True, default='')
    imagen_5 = models.URLField(max_length=500, blank=True, default='')
    video = models.URLField(max_length=500, blank=True, default='')
    recorrido_360 = models.CharField(max_length=500, blank=True, default='')
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'properties'

    def __str__(self):
        return f'{self.identificador} - {self.nombre}'
