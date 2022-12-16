from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.shortcuts import render, get_object_or_404, redirect
from .forms import *
from django.http import Http404
from .models import Movie, Myrating, MyList
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.db.models import Case, When
import pandas as pd

# Create your views here.

def index(request):
    movies = Movie.objects.all()
    query = request.GET.get('q')

    if query:
        movies = Movie.objects.filter(Q(title__icontains=query)).distinct()
        return render(request, 'recommend/list.html', {'movies': movies})

    movie_list = recommendation_lgorithm(request)
    context = {
        'recommended_movie': len(movie_list),
        'movies': movies
    }

    return render(request, 'recommend/list.html', context)


# Show details of the movie
def detail(request, movie_id):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_active:
        raise Http404
    movies = get_object_or_404(Movie, id=movie_id)
    movie = Movie.objects.get(id=movie_id)
    
    temp = list(MyList.objects.all().values().filter(movie_id=movie_id,user=request.user))
    if temp:
        update = temp[0]['watch']
    else:
        update = False
    if request.method == "POST":

        # For my list
        if 'watch' in request.POST:
            watch_flag = request.POST['watch']
            if watch_flag == 'on':
                update = True
            else:
                update = False
            if MyList.objects.all().values().filter(movie_id=movie_id,user=request.user):
                MyList.objects.all().values().filter(movie_id=movie_id,user=request.user).update(watch=update)
            else:
                q=MyList(user=request.user,movie=movie,watch=update)
                q.save()
            if update:
                messages.success(request, "Movie added to your list!")
            else:
                messages.success(request, "Movie removed from your list!")

            
        # For rating
        else:
            rate = request.POST['rating']
            if Myrating.objects.all().values().filter(movie_id=movie_id,user=request.user):
                Myrating.objects.all().values().filter(movie_id=movie_id,user=request.user).update(rating=rate)
            else:
                q=Myrating(user=request.user,movie=movie,rating=rate)
                q.save()

            messages.success(request, "Rating has been submitted!")

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    out = list(Myrating.objects.filter(user=request.user.id).values())

    # To display ratings in the movie detail page
    movie_rating = 0
    rate_flag = False
    for each in out:
        if each['movie_id'] == movie_id:
            movie_rating = each['rating']
            rate_flag = True
            break

    context = {'movies': movies,'movie_rating':movie_rating,'rate_flag':rate_flag,'update':update}
    return render(request, 'recommend/detail.html', context)


# MyList functionality
def watch(request):

    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_active:
        raise Http404

    movies = Movie.objects.filter(mylist__watch=True,mylist__user=request.user)
    query = request.GET.get('q')

    if query:
        movies = Movie.objects.filter(Q(title__icontains=query)).distinct()
        return render(request, 'recommend/watch.html', {'movies': movies})

    return render(request, 'recommend/watch.html', {'movies': movies})


# To get similar movies based on user rating
def get_similar(movie,rating,corrMatrix):
    print(f'############### func get_similar() movie:{movie} ###################')
    # (movie, rating) value: (Frozen, 5)

    print(f'corrMatrix of movie: {movie}')
    print(corrMatrix[movie])
    #output:
        # corrMatrix[movie]: Frozen
        # movie__title
        # Avatar                   -1.0
        # Avengers: Infinity War   -1.0
        # Frozen                    1.0
        # Name: Frozen, dtype: float64

    # if a user has rated a movie as bad, we want al others similar movie to go down in the list
    # if rating below 3(dislike) will push all those towards even more negative side only that why -2.5
    # if rating positive 3,4 or 5 (like) will keep them on the top of list
    similar_ratings = corrMatrix[movie]*(rating-2.5) 
    print(f'--------- similar_ratings movie:{movie} --------------', similar_ratings, sep="\n")
    #output: 
        # movie__title
        # Avatar                   -2.5
        # Avengers: Infinity War   -2.5
        # Frozen                    2.5
        # Name: Frozen, dtype: float64

    similar_ratings = similar_ratings.sort_values(ascending=False) # sort as DESC
    print(f'--------- similar_ratings sort_values movie:{movie} --------------', similar_ratings, sep="\n")
    # output:
        # movie__title
        # Frozen                    2.5
        # Avatar                   -2.5
        # Avengers: Infinity War   -2.5
        # Name: Frozen, dtype: float64

    return similar_ratings

# Recommendation Algorithm
    # 1. User-Based filtering(user to user)
    # 2. Collaborative filtering
        # 1. User-to-User collaborative filtering
        # 1. Item-to-Item collaborative filtering (item to item similar)

    #. Noted:
        #  this algorithm using Item-to-Item Collaborative filtering
        #  filter similar movies base on movie itself that rating given by other users
        # Item-to-Item generally work much better than User-to-User method,
            # the reason is generally you would see that there are lots more users in a system then the number
            # of the products or categories in that system, also user prference are dynamic and something that you might
            # like in your early teens you might not like it growing older whereas in an Item-to-Item method
            # the item stay the same respective of the time right (horror movie still the horror movie after 10 Ys)

        #. ref: 
            # https://www.youtube.com/watch?v=3ecNC-So0r4 
            # https://github.com/codeheroku/Introduction-to-Machine-Learning/blob/master/Collaborative%20Filtering/Movie%20Lens%20Collaborative%20Filtering.ipynb
        

# current flow:
    # 1. new user who not yet rate any movies, when they access the recommendation feature, it will auto rate(score: 0) on a movie name "12 Years a Slave"
    # 2. most movies rated & watched, will be recommended to users who not yet rate at top
    # 3. For users who rated(min score: 1) or watched the movies(ex:a,b,c), then those movies(ex:a,b,c) will not show at recommendation feature for them anymore
    # 4. others users will see all the movies(a,b,c) rated at recommendation feature, except own movies's rated and watched.

# update to Flow:
    # users movies's rated & watched will not recommend
    # User-Based filtering that have similar taste, or rated similar movies, 
        # ex: user (A) & (B) have similar rated to movie (Frozen), they both are considered users having similar likes & dislike
        # then user (A) has rated 5 for movie (Advenger), next time when user (B) request for a recommendation the system will recommend 'Advenger' to user (B)
def recommendation_lgorithm(request):

    movies=pd.DataFrame(list(Movie.objects.all().values()))
    movie_rating=pd.DataFrame(list(Myrating.objects.all().values(
        'user_id',
        'movie__title', # Equal to Myrating.movie.title
        'rating',
    )))
    print('---- movie_rating ---- ', movie_rating, sep='\n')
    # output:
        # ---- movie_rating ---- 
        #    user_id            movie__title  rating
        # 0        8                  Avatar       5
        # 1        8  Avengers: Infinity War       3
        # 2       15                  Frozen       5

    movie_list = []
    if len(movie_rating) > 0:

        # save data as csv file
        movies.to_csv('movies.csv', index=False)
        movie_rating.to_csv('movie_rating.csv', index=False)

        # new_user=movie_rating.user_id.unique().shape[0]
        # print('---- new_user ---- ', new_user, sep='\n')

        current_user_id= request.user.id
        # if new user not rated any movie
        # if current_user_id>new_user:
        #     movie=Movie.objects.get(id=19)
        #     q=Myrating(user=request.user,movie=movie,rating=0)
        #     q.save()

        userRatings = movie_rating.pivot_table(index=['user_id'],columns=['movie__title'],values='rating')
        print('--------- userRatings pivot_table --------------', userRatings, sep="\n")
        # output1:
            #  movie__title  Avatar  Avengers: Infinity War  Frozen
            # user_id
            # 8                5.0                     3.0     NaN
            # 15               NaN                     NaN     5.0

        userRatings = userRatings.fillna(0,axis=1) # replace value NaN to 0
        print('--------- userRatings fillna 0 --------------', userRatings, sep="\n")
        #output2:
            # movie__title  Avatar  Avengers: Infinity War  Frozen
            # user_id
            # 8                5.0                     3.0     0.0
            # 15               0.0                     0.0     5.0

        corrMatrix = userRatings.corr(method='pearson') # Compute pairwise correlation of columns, excluding NA/null values (pearson : standard correlation coefficient).
        print('--------- corrMatrix --------------', corrMatrix, sep="\n")
        # output: 
            # movie__title            Avatar  Avengers: Infinity War  Frozen
            # movie__title
            # Avatar                     1.0                     1.0    -1.0
            # Avengers: Infinity War     1.0                     1.0    -1.0
            # Frozen                    -1.0                    -1.0     1.0

        # user = pd.DataFrame(list(Myrating.objects.filter(user=request.user).values())).drop(['user_id','id'],axis=1)
        user_loggedin_rated = Myrating.objects.filter(
            user=request.user,
        ).values(
            'movie__title', # Equal to Myrating.movie.title
            'rating',
        )

        my_rating = pd.DataFrame(list(user_loggedin_rated))
        if len(my_rating) > 0:

            my_rating.to_csv('Myrating.csv', index=False)
            # my_rating = my_rating.drop(['user_id','id'],axis=1)
            print('--------- user DataFrame --------------', my_rating, sep="\n")
            # save Myrating as csv file
            # output: 
                #   movie__title  rating
                # 0       Frozen       5
        
            user_filtered = [tuple(x) for x in my_rating.values]
            print('--------- user_filtered --------------', user_filtered, sep="\n")
            # output:
                # [('Frozen', 5)]

            movie_id_watched = [each[0] for each in user_filtered]
            print('--------- movie_id_watched --------------', movie_id_watched, sep="\n")
            # output:
                # ['Frozen']

            similar_movies = pd.DataFrame()
            for movie,rating in user_filtered:
                similar_movies = similar_movies.append(get_similar(movie,rating,corrMatrix),ignore_index = True)
                # once similar_movies output:
                    # movie__title
                    # Avatar                   -1.0
                    # Avengers: Infinity War   -1.0
                    # Frozen                    1.0
                    # Name: Frozen, dtype: float64

            print('--------- similar_movies DataFrame -------------', similar_movies, sep='\n')
            # output:
                # movie__title  Frozen  Avatar  Avengers: Infinity War
                # 0                2.5    -2.5                    -2.5

            movies_id = list(similar_movies.sum().sort_values(ascending=False).index)
            print('--------- similar_movies.sum().sort_values index -------------', movies_id, sep='\n')
            # sort movies_id: ['Frozen', 'Avatar', 'Avengers: Infinity War']
            # movie_id_watched: ['Frozen']
            
            movies_id_recommend = [each for each in movies_id if each not in movie_id_watched] # get only movie_id that not in movie_id_watched
            print('--------- movies_id_recommend -------------', movies_id_recommend, sep='\n')
            # output: ['Avatar', 'Avengers: Infinity War']

            preserved = Case(*[When(title=pk, then=pos) for pos, pk in enumerate(movies_id_recommend)])
            print('--------- preserved -------------', preserved, sep='\n')
            # output: CASE , ELSE Value(None)

            movie_list=list(Movie.objects.filter(title__in = movies_id_recommend).order_by(preserved)[:10])
            print('--------- movie_list -------------', movie_list, sep='\n')
    
    return movie_list

# view all recommended movies
def recommend(request):

    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_active:
        raise Http404

    movie_list = recommendation_lgorithm(request)
    context = {'movie_list': movie_list}
    return render(request, 'recommend/recommend.html', context)


# Register user
def signUp(request):
    form = UserForm(request.POST or None)

    if form.is_valid():
        user = form.save(commit=False)
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user.set_password(password)
        user.save()
        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect("index")

    context = {'form': form}

    return render(request, 'recommend/signUp.html', context)


# Login User
def Login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect("index")
            else:
                return render(request, 'recommend/login.html', {'error_message': 'Your account disable'})
        else:
            return render(request, 'recommend/login.html', {'error_message': 'Invalid Login'})

    return render(request, 'recommend/login.html')


# Logout user
def Logout(request):
    logout(request)
    return redirect("login")
