from django.conf.urls import url

from api.tokens import views
from website import settings

urlpatterns = []

if settings.DEV_MODE:
    urlpatterns.extend([
        url(r'^$', views.TokenList.as_view(), name=views.TokenList.view_name),
        url(r'^(?P<_id>\w+)/$', views.TokenDetail.as_view(), name=views.TokenDetail.view_name)
    ])
