from django.db import models


class Agent(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    # Google Calendar OAuth
    google_access_token = models.TextField(blank=True, default='')
    google_refresh_token = models.TextField(blank=True, default='')
    google_token_expiry = models.DateTimeField(null=True, blank=True)
    google_calendar_connected = models.BooleanField(default=False)

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
    recorrido_360 = models.CharField(max_length=500, blank=True, default='')
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'properties'

    def __str__(self):
        return f'{self.identificador} - {self.nombre}'


class PropertyImage(models.Model):
    COMMON_TAGS = [
        ('fachada', 'Fachada'),
        ('sala', 'Sala'),
        ('comedor', 'Comedor'),
        ('cocina', 'Cocina'),
        ('habitacion', 'Habitación'),
        ('bano', 'Baño'),
        ('terraza', 'Terraza'),
        ('vista', 'Vista'),
        ('cochera', 'Cochera'),
        ('lobby', 'Lobby'),
        ('piscina', 'Piscina'),
        ('areas_comunes', 'Áreas comunes'),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='properties/images/')
    order = models.PositiveIntegerField(default=0)
    tag = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'Image {self.id} for {self.property.identificador}'


class PropertyVideo(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='videos')
    video = models.FileField(upload_to='properties/videos/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Video {self.id} for {self.property.identificador}'


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Programada'
        CANCELLED = 'cancelled', 'Cancelada'
        COMPLETED = 'completed', 'Completada'

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='appointments')
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='appointments')
    client_name = models.CharField(max_length=200)
    client_phone = models.CharField(max_length=50, blank=True, default='')
    datetime_start = models.DateTimeField()
    datetime_end = models.DateTimeField()
    google_event_id = models.CharField(max_length=200, blank=True, default='')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    conversation_session_id = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-datetime_start']

    def __str__(self):
        return f'{self.client_name} - {self.property.identificador} ({self.datetime_start})'
