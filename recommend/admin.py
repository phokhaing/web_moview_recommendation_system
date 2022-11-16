from django.contrib import admin
from .models import Movie, Myrating, MyList


# Register your models here.
# admin.site.register(Movie)
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'genre', 'movie_logo']
    list_display_links = ['title', 'genre']

# admin.site.register(Myrating)
@admin.register(Myrating)
class MyratingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'movie', 'rating']
    list_display_links = ['user', 'movie']


# admin.site.register(MyList)
@admin.register(MyList)
class MyListAdmin(admin.ModelAdmin):
    list_display = ['user', 'movie', 'watch']
    list_display_links = ['user', 'movie']