from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/atendimento/(?P<atendimento_id>\d+)/$", consumers.AtendimentoChatConsumer.as_asgi()),
]
