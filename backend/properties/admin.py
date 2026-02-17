from django.contrib import admin
from .models import Agent, Property


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email']
    search_fields = ['name', 'email']


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['identificador', 'nombre', 'clase', 'operacion', 'distrito', 'precio', 'activo']
    list_filter = ['clase', 'operacion', 'distrito', 'activo']
    search_fields = ['identificador', 'nombre', 'distrito', 'pitch']
