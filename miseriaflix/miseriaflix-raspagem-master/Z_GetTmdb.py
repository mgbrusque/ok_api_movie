import tmdbsimple as tmdb
tmdb.API_KEY = 'd2f104538c0b6336cb298faaf5645137'

search = tmdb.Search()
response = search.movie(query='samaritano')
for s in search.results:
    print(s['title'], s['id'], s['release_date'], s['vote_average'])

