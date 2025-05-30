from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('hello', views.hello, name='hello'),
    path('list_files', views.list_files, name='list_files'),
    path('upload_file', views.upload_file, name='upload_file'),
    path('list_db_data', views.list_db_data, name='list_db_data'),
    path('update_db_data', views.update_db_data, name='update_db_data'),
    path('delete_record/<int:pk>/', views.delete_record, name='delete_record'),
]