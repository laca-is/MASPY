from maspy import *
from random import choice, choices
from time import sleep

movie_database = [
    {"title": "Inception", "genres": ["Action", "Sci-Fi", "Thriller"], "director": "Christopher Nolan", "actors": ["Leonardo DiCaprio", "Joseph Gordon-Levitt"], "popularity": 8.8},
    {"title": "The Matrix", "genres": ["Action", "Sci-Fi"], "director": "Lana Wachowski", "actors": ["Keanu Reeves", "Laurence Fishburne"], "popularity": 8.7},
    {"title": "The Dark Knight", "genres": ["Action", "Crime", "Drama"], "director": "Christopher Nolan", "actors": ["Christian Bale", "Heath Ledger"], "popularity": 9.0},
    {"title": "Interstellar", "genres": ["Adventure", "Drama", "Sci-Fi"], "director": "Christopher Nolan", "actors": ["Matthew McConaughey", "Anne Hathaway"], "popularity": 8.6},
    {"title": "Parasite", "genres": ["Drama", "Thriller"], "director": "Bong Joon-ho", "actors": ["Kang-ho Song", "Sun-kyun Lee"], "popularity": 8.6},
    {"title": "Mad Max: Fury Road", "genres": ["Action", "Adventure", "Sci-Fi"], "director": "George Miller", "actors": ["Tom Hardy", "Charlize Theron"], "popularity": 8.1},
    {"title": "Blade Runner 2049", "genres": ["Action", "Drama", "Sci-Fi"], "director": "Denis Villeneuve", "actors": ["Ryan Gosling", "Harrison Ford"], "popularity": 8.0},
    {"title": "Joker", "genres": ["Crime", "Drama", "Thriller"], "director": "Todd Phillips", "actors": ["Joaquin Phoenix", "Robert De Niro"], "popularity": 8.4},
    {"title": "The Godfather", "genres": ["Crime", "Drama"], "director": "Francis Ford Coppola", "actors": ["Marlon Brando", "Al Pacino"], "popularity": 9.2},
    {"title": "Pulp Fiction", "genres": ["Crime", "Drama"], "director": "Quentin Tarantino", "actors": ["John Travolta", "Uma Thurman"], "popularity": 8.9},
    {"title": "The Shawshank Redemption", "genres": ["Drama"], "director": "Frank Darabont", "actors": ["Tim Robbins", "Morgan Freeman"], "popularity": 9.3},
    {"title": "Fight Club", "genres": ["Drama"], "director": "David Fincher", "actors": ["Brad Pitt", "Edward Norton"], "popularity": 8.8},
    {"title": "The Social Network", "genres": ["Biography", "Drama"], "director": "David Fincher", "actors": ["Jesse Eisenberg", "Andrew Garfield"], "popularity": 7.7},
    {"title": "Gladiator", "genres": ["Action", "Adventure", "Drama"], "director": "Ridley Scott", "actors": ["Russell Crowe", "Joaquin Phoenix"], "popularity": 8.5},
    {"title": "The Lion King", "genres": ["Animation", "Adventure", "Drama"], "director": "Roger Allers", "actors": ["Matthew Broderick", "Jeremy Irons"], "popularity": 8.5},
    {"title": "The Grand Budapest Hotel", "genres": ["Adventure", "Comedy", "Crime"], "director": "Wes Anderson", "actors": ["Ralph Fiennes", "F. Murray Abraham"], "popularity": 8.1},
    {"title": "Memento", "genres": ["Mystery", "Thriller"], "director": "Christopher Nolan", "actors": ["Guy Pearce", "Carrie-Anne Moss"], "popularity": 8.4},
    {"title": "Django Unchained", "genres": ["Drama", "Western"], "director": "Quentin Tarantino", "actors": ["Jamie Foxx", "Christoph Waltz"], "popularity": 8.4},
    {"title": "Schindler's List", "genres": ["Biography", "Drama", "History"], "director": "Steven Spielberg", "actors": ["Liam Neeson", "Ralph Fiennes"], "popularity": 9.0},
    {"title": "Whiplash", "genres": ["Drama", "Music"], "director": "Damien Chazelle", "actors": ["Miles Teller", "J.K. Simmons"], "popularity": 8.5},
    {"title": "La La Land", "genres": ["Comedy", "Drama", "Music"], "director": "Damien Chazelle", "actors": ["Ryan Gosling", "Emma Stone"], "popularity": 8.0},
    {"title": "Inglourious Basterds", "genres": ["Adventure", "Drama", "War"], "director": "Quentin Tarantino", "actors": ["Brad Pitt", "Diane Kruger"], "popularity": 8.3},
    {"title": "The Prestige", "genres": ["Drama", "Mystery", "Sci-Fi"], "director": "Christopher Nolan", "actors": ["Christian Bale", "Hugh Jackman"], "popularity": 8.5},
    {"title": "Guardians of the Galaxy", "genres": ["Action", "Adventure", "Comedy"], "director": "James Gunn", "actors": ["Chris Pratt", "Zoe Saldana"], "popularity": 8.0},
    {"title": "The Avengers", "genres": ["Action", "Adventure", "Sci-Fi"], "director": "Joss Whedon", "actors": ["Robert Downey Jr.", "Chris Evans"], "popularity": 8.0},
    {"title": "A Beautiful Mind", "genres": ["Biography", "Drama"], "director": "Ron Howard", "actors": ["Russell Crowe", "Ed Harris"], "popularity": 8.2},
    {"title": "The Silence of the Lambs", "genres": ["Crime", "Drama", "Thriller"], "director": "Jonathan Demme", "actors": ["Jodie Foster", "Anthony Hopkins"], "popularity": 8.6},
    {"title": "Shutter Island", "genres": ["Mystery", "Thriller"], "director": "Martin Scorsese", "actors": ["Leonardo DiCaprio", "Mark Ruffalo"], "popularity": 8.2},
    {"title": "No Country for Old Men", "genres": ["Crime", "Drama", "Thriller"], "director": "Ethan Coen, Joel Coen", "actors": ["Tommy Lee Jones", "Javier Bardem"], "popularity": 8.2},
    {"title": "The Wolf of Wall Street", "genres": ["Biography", "Crime", "Drama"], "director": "Martin Scorsese", "actors": ["Leonardo DiCaprio", "Jonah Hill"], "popularity": 8.2},
    {"title": "The Big Lebowski", "genres": ["Comedy", "Crime"], "director": "Ethan Coen, Joel Coen", "actors": ["Jeff Bridges", "John Goodman"], "popularity": 8.1},
    {"title": "The Lord of the Rings: The Fellowship of the Ring", "genres": ["Action", "Adventure", "Drama"], "director": "Peter Jackson", "actors": ["Elijah Wood", "Ian McKellen"], "popularity": 8.8},
    {"title": "The Lord of the Rings: The Two Towers", "genres": ["Action", "Adventure", "Drama"], "director": "Peter Jackson", "actors": ["Elijah Wood", "Ian McKellen"], "popularity": 8.8},
    {"title": "The Lord of the Rings: The Return of the King", "genres": ["Action", "Adventure", "Drama"], "director": "Peter Jackson", "actors": ["Elijah Wood", "Viggo Mortensen"], "popularity": 9.0},
    {"title": "The Shining", "genres": ["Drama", "Horror"], "director": "Stanley Kubrick", "actors": ["Jack Nicholson", "Shelley Duvall"], "popularity": 8.4},
    {"title": "The Truman Show", "genres": ["Comedy", "Drama"], "director": "Peter Weir", "actors": ["Jim Carrey", "Ed Harris"], "popularity": 8.2},
    {"title": "Forrest Gump", "genres": ["Drama", "Romance"], "director": "Robert Zemeckis", "actors": ["Tom Hanks", "Robin Wright"], "popularity": 8.8},
    {"title": "Goodfellas", "genres": ["Biography", "Crime", "Drama"], "director": "Martin Scorsese", "actors": ["Robert De Niro", "Ray Liotta"], "popularity": 8.7},
    {"title": "The Sixth Sense", "genres": ["Drama", "Mystery", "Thriller"], "director": "M. Night Shyamalan", "actors": ["Bruce Willis", "Haley Joel Osment"], "popularity": 8.1},
    {"title": "The Usual Suspects", "genres": ["Crime", "Drama", "Mystery"], "director": "Bryan Singer", "actors": ["Kevin Spacey", "Gabriel Byrne"], "popularity": 8.5},
    {"title": "The Irishman", "genres": ["Biography", "Crime", "Drama"], "director": "Martin Scorsese", "actors": ["Robert De Niro", "Al Pacino", "Joe Pesci"], "popularity": 7.8},
    {"title": "Once Upon a Time in Hollywood", "genres": ["Comedy", "Drama"], "director": "Quentin Tarantino", "actors": ["Leonardo DiCaprio", "Brad Pitt", "Margot Robbie"], "popularity": 7.6},
    {"title": "1917", "genres": ["Drama", "War"], "director": "Sam Mendes", "actors": ["George MacKay", "Dean-Charles Chapman", "Mark Strong"], "popularity": 8.3},
    {"title": "Knives Out", "genres": ["Comedy", "Crime", "Drama"], "director": "Rian Johnson", "actors": ["Daniel Craig", "Chris Evans", "Ana de Armas"], "popularity": 7.9},
    {"title": "Jojo Rabbit", "genres": ["Comedy", "Drama", "War"], "director": "Taika Waititi", "actors": ["Roman Griffin Davis", "Thomasin McKenzie", "Scarlett Johansson"], "popularity": 7.9},
    {"title": "The Lighthouse", "genres": ["Drama", "Fantasy", "Horror"], "director": "Robert Eggers", "actors": ["Robert Pattinson", "Willem Dafoe"], "popularity": 7.5},
    {"title": "Marriage Story", "genres": ["Drama", "Romance"], "director": "Noah Baumbach", "actors": ["Adam Driver", "Scarlett Johansson", "Laura Dern"], "popularity": 7.9},
    {"title": "Ford v Ferrari", "genres": ["Action", "Biography", "Drama"], "director": "James Mangold", "actors": ["Matt Damon", "Christian Bale", "Jon Bernthal"], "popularity": 8.1},
    {"title": "The Farewell", "genres": ["Comedy", "Drama"], "director": "Lulu Wang", "actors": ["Shuzhen Zhao", "Awkwafina", "X Mayo"], "popularity": 7.5},
    {"title": "A Quiet Place", "genres": ["Drama", "Horror", "Sci-Fi"], "director": "John Krasinski", "actors": ["Emily Blunt", "John Krasinski", "Millicent Simmonds"], "popularity": 7.5},
    {"title": "Spider-Man: Into the Spider-Verse", "genres": ["Animation", "Action", "Adventure"], "director": "Bob Persichetti", "actors": ["Shameik Moore", "Jake Johnson", "Hailee Steinfeld"], "popularity": 8.4},
    {"title": "Hereditary", "genres": ["Drama", "Horror", "Mystery"], "director": "Ari Aster", "actors": ["Toni Collette", "Milly Shapiro", "Gabriel Byrne"], "popularity": 7.3},
    {"title": "The Shape of Water", "genres": ["Adventure", "Drama", "Fantasy"], "director": "Guillermo del Toro", "actors": ["Sally Hawkins", "Octavia Spencer", "Michael Shannon"], "popularity": 7.3},
    {"title": "Lady Bird", "genres": ["Comedy", "Drama"], "director": "Greta Gerwig", "actors": ["Saoirse Ronan", "Laurie Metcalf", "Tracy Letts"], "popularity": 7.4},
    {"title": "Moonlight", "genres": ["Drama"], "director": "Barry Jenkins", "actors": ["Mahershala Ali", "Naomie Harris", "Trevante Rhodes"], "popularity": 7.4},
    {"title": "Get Out", "genres": ["Horror", "Mystery", "Thriller"], "director": "Jordan Peele", "actors": ["Daniel Kaluuya", "Allison Williams", "Bradley Whitford"], "popularity": 7.7},
    {"title": "Mad Max: Fury Road", "genres": ["Action", "Adventure", "Sci-Fi"], "director": "George Miller", "actors": ["Tom Hardy", "Charlize Theron", "Nicholas Hoult"], "popularity": 8.1},
    {"title": "Birdman", "genres": ["Comedy", "Drama"], "director": "Alejandro G. Iñárritu", "actors": ["Michael Keaton", "Zach Galifianakis", "Edward Norton"], "popularity": 7.7},
    {"title": "The Revenant", "genres": ["Action", "Adventure", "Drama"], "director": "Alejandro G. Iñárritu", "actors": ["Leonardo DiCaprio", "Tom Hardy", "Will Poulter"], "popularity": 8.0},
    {"title": "Room", "genres": ["Drama", "Thriller"], "director": "Lenny Abrahamson", "actors": ["Brie Larson", "Jacob Tremblay", "Sean Bridgers"], "popularity": 8.1},
    {"title": "Arrival", "genres": ["Drama", "Mystery", "Sci-Fi"], "director": "Denis Villeneuve", "actors": ["Amy Adams", "Jeremy Renner", "Forest Whitaker"], "popularity": 7.9},
    {"title": "Spotlight", "genres": ["Biography", "Crime", "Drama"], "director": "Tom McCarthy", "actors": ["Mark Ruffalo", "Michael Keaton", "Rachel McAdams"], "popularity": 8.1},
    {"title": "The Hateful Eight", "genres": ["Crime", "Drama", "Mystery"], "director": "Quentin Tarantino", "actors": ["Samuel L. Jackson", "Kurt Russell", "Jennifer Jason Leigh"], "popularity": 7.8},
    {"title": "The Big Short", "genres": ["Biography", "Comedy", "Drama"], "director": "Adam McKay", "actors": ["Christian Bale", "Steve Carell", "Ryan Gosling"], "popularity": 7.8},
    {"title": "12 Years a Slave", "genres": ["Biography", "Drama", "History"], "director": "Steve McQueen", "actors": ["Chiwetel Ejiofor", "Michael Kenneth Williams", "Michael Fassbender"], "popularity": 8.1},
    {"title": "Dallas Buyers Club", "genres": ["Biography", "Drama"], "director": "Jean-Marc Vallée", "actors": ["Matthew McConaughey", "Jennifer Garner", "Jared Leto"], "popularity": 8.0},
    {"title": "Argo", "genres": ["Biography", "Drama", "Thriller"], "director": "Ben Affleck", "actors": ["Ben Affleck", "Bryan Cranston", "John Goodman"], "popularity": 7.7},
    {"title": "Life of Pi", "genres": ["Adventure", "Drama", "Fantasy"], "director": "Ang Lee", "actors": ["Suraj Sharma", "Irrfan Khan", "Adil Hussain"], "popularity": 7.9},
    {"title": "The Imitation Game", "genres": ["Biography", "Drama", "Thriller"], "director": "Morten Tyldum", "actors": ["Benedict Cumberbatch", "Keira Knightley", "Matthew Goode"], "popularity": 8.0},
    {"title": "The Theory of Everything", "genres": ["Biography", "Drama", "Romance"], "director": "James Marsh", "actors": ["Eddie Redmayne", "Felicity Jones", "Tom Prior"], "popularity": 7.7},
    {"title": "The King's Speech", "genres": ["Biography", "Drama", "History"], "director": "Tom Hooper", "actors": ["Colin Firth", "Geoffrey Rush", "Helena Bonham Carter"], "popularity": 8.0},
    {"title": "Black Swan", "genres": ["Drama", "Thriller"], "director": "Darren Aronofsky", "actors": ["Natalie Portman", "Mila Kunis", "Vincent Cassel"], "popularity": 8.0},
    {"title": "Inglourious Basterds", "genres": ["Adventure", "Drama", "War"], "director": "Quentin Tarantino", "actors": ["Brad Pitt", "Diane Kruger", "Eli Roth"], "popularity": 8.3},
    {"title": "Slumdog Millionaire", "genres": ["Drama", "Romance"], "director": "Danny Boyle", "actors": ["Dev Patel", "Freida Pinto", "Saurabh Shukla"], "popularity": 8.0},
    {"title": "The Hurt Locker", "genres": ["Drama", "Thriller", "War"], "director": "Kathryn Bigelow", "actors": ["Jeremy Renner", "Anthony Mackie", "Brian Geraghty"], "popularity": 7.5},
    {"title": "The Departed", "genres": ["Crime", "Drama", "Thriller"], "director": "Martin Scorsese", "actors": ["Leonardo DiCaprio", "Matt Damon", "Jack Nicholson"], "popularity": 8.5},
    {"title": "The Curious Case of Benjamin Button", "genres": ["Drama", "Fantasy", "Romance"], "director": "David Fincher", "actors": ["Brad Pitt", "Cate Blanchett", "Tilda Swinton"], "popularity": 7.8},
    {"title": "There Will Be Blood", "genres": ["Drama"], "director": "Paul Thomas Anderson", "actors": ["Daniel Day-Lewis", "Paul Dano", "Ciarán Hinds"], "popularity": 8.2},
    {"title": "No Country for Old Men", "genres": ["Crime", "Drama", "Thriller"], "director": "Ethan Coen, Joel Coen", "actors": ["Tommy Lee Jones", "Javier Bardem", "Josh Brolin"], "popularity": 8.1},
    {"title": "Pan's Labyrinth", "genres": ["Drama", "Fantasy", "War"], "director": "Guillermo del Toro", "actors": ["Ivana Baquero", "Ariadna Gil", "Sergi López"], "popularity": 8.2},
    {"title": "Brokeback Mountain", "genres": ["Drama", "Romance"], "director": "Ang Lee", "actors": ["Jake Gyllenhaal", "Heath Ledger", "Michelle Williams"], "popularity": 7.7},
    {"title": "Crash", "genres": ["Crime", "Drama", "Thriller"], "director": "Paul Haggis", "actors": ["Don Cheadle", "Sandra Bullock", "Thandiwe Newton"], "popularity": 7.7},
]

genres = [
    "Action", 
    "Adventure", 
    "Animation", 
    "Biography", 
    "Comedy", 
    "Crime", 
    "Drama",
    "Fantasy", 
    "Horror", 
    "Music", 
    "Mystery", 
    "Romance", 
    "Sci-Fi", 
    "Thriller", 
    "War", 
    "Western"
]

directors = [
    "Christopher Nolan", 
    "Lana Wachowski", 
    "Francis Ford Coppola", 
    "Quentin Tarantino", 
    "Frank Darabont", 
    "David Fincher", 
    "Ridley Scott", 
    "Bong Joon-ho", 
    "George Miller", 
    "Denis Villeneuve", 
    "Todd Phillips", 
    "Martin Scorsese", 
    "Wes Anderson", 
    "James Gunn", 
    "Joss Whedon", 
    "Ron Howard", 
    "Jonathan Demme", 
    "Alejandro G. Iñárritu", 
    "Steven Spielberg", 
    "Damien Chazelle", 
    "Ethan Coen", 
    "Joel Coen", 
    "Peter Jackson", 
    "Stanley Kubrick", 
    "Robert Zemeckis", 
    "Bryan Singer", 
    "Peter Weir", 
    "M. Night Shyamalan",
    "Sam Mendes", 
    "Rian Johnson", 
    "Taika Waititi", 
    "Robert Eggers", 
    "Noah Baumbach", 
    "James Mangold", 
    "Lulu Wang", 
    "John Krasinski", 
    "Bob Persichetti", 
    "Ari Aster", 
    "Guillermo del Toro", 
    "Greta Gerwig", 
    "Barry Jenkins", 
    "Jordan Peele", 
    "Lenny Abrahamson", 
    "Tom McCarthy", 
    "Adam McKay", 
    "Steve McQueen", 
    "Jean-Marc Vallée", 
    "Ben Affleck", 
    "Ang Lee", 
    "Morten Tyldum", 
    "James Marsh", 
    "Tom Hooper", 
    "Darren Aronofsky", 
    "Danny Boyle", 
    "Kathryn Bigelow", 
    "Paul Thomas Anderson", 
    "Paul Haggis"
]

actors = [
    "Leonardo DiCaprio", 
    "Joseph Gordon-Levitt", 
    "Keanu Reeves", 
    "Laurence Fishburne", 
    "Christian Bale", 
    "Heath Ledger", 
    "Matthew McConaughey", 
    "Anne Hathaway", 
    "Kang-ho Song", 
    "Sun-kyun Lee", 
    "Tom Hardy", 
    "Charlize Theron", 
    "Ryan Gosling", 
    "Harrison Ford", 
    "Joaquin Phoenix", 
    "Robert De Niro", 
    "Marlon Brando", 
    "Al Pacino", 
    "John Travolta", 
    "Uma Thurman", 
    "Tim Robbins", 
    "Morgan Freeman", 
    "Brad Pitt", 
    "Edward Norton", 
    "Jesse Eisenberg", 
    "Andrew Garfield", 
    "Russell Crowe", 
    "Jeff Bridges", 
    "John Goodman", 
    "Amy Adams", 
    "Jeremy Renner", 
    "Ralph Fiennes", 
    "F. Murray Abraham", 
    "Guy Pearce", 
    "Carrie-Anne Moss", 
    "Miles Teller", 
    "J.K. Simmons", 
    "Jamie Foxx", 
    "Christoph Waltz", 
    "Liam Neeson", 
    "Viggo Mortensen", 
    "Elijah Wood", 
    "Ian McKellen", 
    "Hugh Jackman", 
    "Benicio del Toro", 
    "Chris Pratt", 
    "Zoe Saldana", 
    "Robert Downey Jr.", 
    "Chris Evans", 
    "Ed Harris", 
    "Tommy Lee Jones", 
    "Javier Bardem", 
    "Jonah Hill", 
    "Bruce Willis", 
    "Haley Joel Osment", 
    "Kevin Spacey", 
    "Gabriel Byrne", 
    "Jim Carrey", 
    "Shelley Duvall",
    "Joe Pesci", 
    "Margot Robbie", 
    "George MacKay", 
    "Dean-Charles Chapman", 
    "Mark Strong", 
    "Daniel Craig", 
    "Ana de Armas", 
    "Roman Griffin Davis", 
    "Thomasin McKenzie", 
    "Scarlett Johansson", 
    "Robert Pattinson", 
    "Willem Dafoe", 
    "Adam Driver", 
    "Laura Dern", 
    "Matt Damon", 
    "Jon Bernthal", 
    "Yeo-jeong Jo", 
    "Shuzhen Zhao", 
    "Awkwafina", 
    "X Mayo", 
    "Zazie Beetz", 
    "Millicent Simmonds", 
    "Shameik Moore", 
    "Jake Johnson", 
    "Hailee Steinfeld", 
    "Toni Collette", 
    "Milly Shapiro", 
    "Gabriel Byrne", 
    "Sally Hawkins", 
    "Octavia Spencer", 
    "Michael Shannon", 
    "Saoirse Ronan", 
    "Laurie Metcalf", 
    "Tracy Letts", 
    "Mahershala Ali", 
    "Naomie Harris", 
    "Trevante Rhodes", 
    "Daniel Kaluuya", 
    "Allison Williams", 
    "Bradley Whitford", 
    "Rosemarie DeWitt", 
    "Nicholas Hoult", 
    "Michael Keaton", 
    "Zach Galifianakis", 
    "Edward Norton", 
    "Jacob Tremblay", 
    "Sean Bridgers", 
    "Forest Whitaker", 
    "Mark Ruffalo", 
    "Rachel McAdams", 
    "Samuel L. Jackson", 
    "Kurt Russell", 
    "Jennifer Jason Leigh", 
    "Steve Carell", 
    "Ryan Gosling", 
    "Chiwetel Ejiofor", 
    "Michael Kenneth Williams", 
    "Jared Leto", 
    "Bryan Cranston", 
    "John Goodman", 
    "Suraj Sharma", 
    "Irrfan Khan", 
    "Adil Hussain", 
    "Benedict Cumberbatch", 
    "Keira Knightley", 
    "Matthew Goode", 
    "Eddie Redmayne", 
    "Felicity Jones", 
    "Tom Prior", 
    "Colin Firth", 
    "Geoffrey Rush", 
    "Helena Bonham Carter", 
    "Natalie Portman", 
    "Mila Kunis", 
    "Vincent Cassel", 
    "Dev Patel", 
    "Freida Pinto", 
    "Saurabh Shukla", 
    "Jeremy Renner", 
    "Anthony Mackie", 
    "Brian Geraghty", 
    "Cate Blanchett", 
    "Tilda Swinton", 
    "Daniel Day-Lewis", 
    "Paul Dano", 
    "Ciarán Hinds", 
    "Josh Brolin", 
    "Ivana Baquero", 
    "Ariadna Gil", 
    "Sergi López", 
    "Jake Gyllenhaal", 
    "Michelle Williams", 
    "Don Cheadle", 
    "Sandra Bullock", 
    "Thandiwe Newton"
]

class Recomender(Agent):
    def __init__(self, agt_name:str):

        super().__init__(agt_name)
        self.already_recomended: dict[tuple,set] = dict()
        self.add(Goal("Test"))
        
    @pl(gain, Goal("Recomend"))
    def recomend(self, src):
        recomend_list = self.generate_list_for_agent(src)
        if recomend_list is None:
            return None
        self.send(src,achieve,Goal("checkRecomendations",recomend_list))
    
    def generate_list_for_agent(self, agt_name):
        saved_preferences = self.get(Belief("Preferences",Any,agt_name))
        if saved_preferences is not None:
            if saved_preferences.args['genres'] == {}:
                random_popular = self.get_popular_movies(agt_name)
                return random_popular
            else:
                random_personalized = self.get_personalized_list(agt_name, saved_preferences.args)
                return random_personalized
                
        else:
            random_popular = self.get_popular_movies(agt_name)
            return random_popular
    
    @pl(gain, Goal("checkFeedback",Any))
    def update_preferences(self, src, feedback_list):
        agent_prefs = self.get(Belief("Preferences",Any,src))
        self.print(agent_prefs)
        if agent_prefs is None:
            prefs_dict = {"directors": {},'genres': {},'actors': {}}
        else:
            prefs_dict = agent_prefs.args
            self.rm(agent_prefs)

        for movie in feedback_list:
            assert isinstance(movie, dict)
            if movie['feedback'] == 'liked':
                flag = 2
            else:
                flag = -1
                
            if movie['director'] not in prefs_dict['directors']:
                prefs_dict['directors'][movie['director']] = 10*flag
            else:
                prefs_dict['directors'][movie['director']] += 10*flag
            if prefs_dict['directors'][movie['director']] < 0:
                prefs_dict['directors'][movie['director']] = 0
            for genre in movie['genres']:
                if genre not in prefs_dict['genres']:
                    prefs_dict['genres'][genre] = 10*flag
                else:
                    prefs_dict['genres'][genre] += 10*flag
                if prefs_dict['genres'][genre] < 0:
                    prefs_dict['genres'][genre] = 0
            for actor in movie['actors']:
                if actor not in prefs_dict['actors']:
                    prefs_dict['actors'][actor] = 10*flag
                else:
                    prefs_dict['actors'][actor] += 10*flag
                if prefs_dict['actors'][actor] < 0:
                    prefs_dict['actors'][actor] = 0
            
        self.add(Belief("Preferences", prefs_dict, src))

    def calculate_weight(self, agt_name, preferences: dict, movie: dict, flag=False):
        if movie['title'] in self.already_recomended[agt_name]:
            return 0
        
        assert isinstance(preferences, dict)
        assert isinstance(preferences["directors"], dict)
        director_weight = preferences['directors'].get(movie['director'], 0)
        
        assert isinstance(preferences["genres"], dict)
        genre_weight = sum(preferences['genres'].get(genre, 0) for genre in movie['genres'])
        
        assert isinstance(preferences["actors"], dict)
        actor_weight = sum(preferences['actors'].get(actor, 0) for actor in movie['actors'])
        
        if flag:
            return max(genre_weight,1)*max(director_weight,1)*max(actor_weight,1), [director_weight, genre_weight, actor_weight]
        return max(genre_weight,1)*max(director_weight,1)*max(actor_weight,1)
    
    def get_personalized_list(self, agt_name, preferences):
        weights = [self.calculate_weight(agt_name,preferences, movie) for movie in movie_database]
        selected_dicts = []
        while len(selected_dicts) < 5:
            element = choices(movie_database, weights=weights)[0]
            if element not in selected_dicts:
                element['weigth'] = self.calculate_weight(agt_name,preferences, element, True)
                selected_dicts.append(element)
        for movie in selected_dicts:
            assert isinstance(movie, dict)
            self.already_recomended[agt_name].add(movie['title'])
        return selected_dicts
    
    def weighted_sample_no_replacement(population, weights, k):
        unique_elements = set()
        while len(unique_elements) < k:
            element = choices(population, weights)[0]
            unique_elements.add(element)
        return list(unique_elements)
    
    def get_popular_movies(self, agt_name):
        self.already_recomended[agt_name] = set()
        weights = [d['popularity'] for d in movie_database]
        selected_dicts = choices(movie_database, weights=weights, k=5)
        for movie in selected_dicts:
            self.already_recomended[agt_name].add(movie['title'])
        return selected_dicts

class Client(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)
        self.add(Belief("Preferences",{
                    "director":choice(directors),
                    "genres":choices(genres,k=2),
                    "actors":choices(actors,k=3)})
                )
        self.print_beliefs
        self.add(Goal("Ask_for_recomendations"))
    
    @pl(gain, Goal("Ask_for_recomendations"))
    def asking_recomendations(self, src):
        self.send("Recomender",achieve,Goal("Recomend"))
    
    @pl(gain, Goal("checkRecomendations",Any), Belief("Preferences",Any))
    def check_recomendations(self, src, recomendations, preferences):
        buffer = "I've been recommended the following movies:\n\t"
        feedback_list = []
        liked_counter = 0
        for recomendation in recomendations:
            assert isinstance(recomendation, dict)
            assert isinstance(recomendation['actors'], list)
            assert isinstance(preferences, dict)
            
            try:
               buffer += f"{recomendation['title']} {recomendation['genres']} made by {recomendation['director']}, with {recomendation['actors'][0]} and {recomendation['actors'][1]} ({recomendation['weigth']}) \n\t" 
            except KeyError:
                buffer += f"{recomendation['title']} {recomendation['genres']} made by {recomendation['director']}, with {recomendation['actors'][0]} and {recomendation['actors'][1]}\n\t"
            
            if recomendation['director'] == preferences['director'] or self.has_intersection(preferences['genres'],recomendation['genres']) or self.has_intersection(preferences['actors'],recomendation['actors']):
                recomendation['feedback'] = 'liked'
                liked_counter += 1
            else:
                recomendation['feedback'] = 'disliked'  
            feedback_list.append(recomendation)
        self.print(f'{buffer}')
        
        buffer = f"{liked_counter} liked recommendation(s)\n"
        for movie in feedback_list:
            assert isinstance(movie, dict)
            if movie['feedback'] == 'liked':
                buffer += f"\t{movie['title']}\n"
        self.print(f'{buffer}')
            
        self.send(src,achieve,Goal("checkFeedback",feedback_list))
        sleep(2)
        self.add(Goal("Ask_for_recomendations"))
        
    def has_intersection(self, list1, list2):
        set1 = set(list1)
        set2 = set(list2)
        return not set1.isdisjoint(set2)

if __name__=="__main__":
    rec = Recomender("Recomender")
    cli = Client("Client")
    Admin().start_system()