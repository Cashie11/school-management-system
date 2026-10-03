from django.urls import path

from . import views

app_name = "support"

urlpatterns = [
    path("", views.help_index, name="help"),
    path("contact/", views.contact, name="contact"),
    path("contact/done/", views.contact_done, name="contact_done"),
    path("messages/", views.message_list, name="message_list"),
    path("messages/<int:pk>/resolve/", views.message_resolve, name="message_resolve"),
    path("<slug:slug>/", views.help_article, name="article"),
]
