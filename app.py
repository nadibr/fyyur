#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import logging
from logging import Formatter, FileHandler
import sys

import babel
import dateutil.parser
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from forms import *

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#


class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    website = db.Column(db.String)
    genres = db.Column(db.ARRAY(db.String))
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String)
    shows = db.relationship('Show', backref='venue', lazy=True)

    def __repr__(self):
        return f'<Venue {self.id} {self.name} {self.city}>'


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    website = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String(120)))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String)
    shows = db.relationship('Show', backref='artist', lazy=True)


class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)


migrate = Migrate(app, db)
#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():

    venue_query = Venue.query.\
        group_by(Venue.id, Venue.state, Venue.city).order_by(Venue.state, Venue.city).all()
    city_and_state = ''
    citystate = []
    data2 = []
    for venue in venue_query:
        upcoming_shows = Show.query.filter_by(venue_id=venue.id).\
            filter(Show.start_time >= datetime.now()).\
            all()

        if city_and_state == venue.city + venue.state:
            data2[len(data2) - 1]["venues"].append({
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": len(upcoming_shows)
            })
        else:
            city_and_state = venue.city + venue.state
            citystate.append((venue.city, venue.state))
            data2.append({
                "city": venue.city,
                "state": venue.state,
                "venues": [{
                    "id": venue.id,
                    "name": venue.name,
                    "num_upcoming_shows": len(upcoming_shows)
                }]
            })

    for i in data2:
        if "venues" in i:
            i["venues"] = sorted(i["venues"], key=lambda venue: venue['num_upcoming_shows'], reverse=True)

    return render_template('pages/venues.html', areas=data2);


@app.route('/venues/search', methods=['POST'])
def search_venues():
    # get search string from the form
    search_string = ''.join(request.form.get('search_term', ''))

    # query all the venues from DB that contain search string in lowercase
    venues = Venue.query.filter(Venue.name.ilike('%'+f'%{search_string}%'+'%')).all()
    # count matches quantity
    venues_number = len(venues)
    data = []

    for venue in venues:
        # filter upcoming shows for the venue
        shows_number = Show.query.filter_by(venue_id=venue.id). \
        filter(Show.start_time >= datetime.now()). \
        count()

        data.append({
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": shows_number
        })

    response = {
        "count": venues_number,
        "data": data
    }
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>', methods=['GET'])
def show_venue(venue_id):
    # shows the venue page with the given venue_id

    venue = Venue.query.get(venue_id)
    # replace separators in the genres string so it would come as a list (comes as a list of chracters otherwise)
    venue.genres = ''.join(list(filter(lambda x: x != '{' and x != '}' and x != '"', venue.genres))).split(',')
    venue.upcoming_shows = []
    venue.past_shows = []
    # retrieveing only upcoming shows from database
    upcoming_shows = Show.query.filter_by(venue_id=venue_id). \
        filter(Show.start_time >= datetime.now()). \
        all()

    # retrieveing upcoming shows' artists information for the venue
    for show in upcoming_shows:
        venue.upcoming_shows.append({
            "artist_id": show.artist_id,
            "artist_name": Artist.query.filter_by(id=show.artist_id).first().name,
            "artist_image_link": Artist.query.filter_by(id=show.artist_id).first().image_link,
            "start_time": format_datetime(str(show.start_time))
        })

    venue.upcoming_shows_count = len(upcoming_shows)
    # retrieveing only past shows from database
    past_shows = Show.query.filter_by(venue_id=venue_id). \
        filter(Show.start_time < datetime.now()). \
        all()
    # retrieveing past shows' artists information for the venue
    for show in past_shows:
        venue.past_shows.append({
            "artist_id": show.artist_id,
            "artist_name": Artist.query.filter_by(id=show.artist_id).first().name,
            "artist_image_link": Artist.query.filter_by(id=show.artist_id).first().image_link,
            "start_time": format_datetime(str(show.start_time))
        })

    venue.past_shows_count = len(past_shows)
    return render_template('pages/show_venue.html', venue=venue)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():

    form = VenueForm(request.form)

    try:
        #initialize Venue object and pass form's data
        venue = Venue(name=form.name.data, city=form.city.data, state=form.state.data, phone=form.phone.data,
                      address=form.address.data, genres=form.genres.data, website=form.website.data,
                      facebook_link=form.facebook_link.data, image_link=form.image_link.data,
                      seeking_talent=form.seeking_talent.data, seeking_description=form.seeking_description.data)
        # pass form's data to DB
        db.session.add(venue)
        db.session.commit()
        flash('Venue ' + form.name.data + ' was successfully updated!')

    except ValueError as e:
        print(e)
        db.session.rollback()
        print(sys.exc_info())
        flash('An error occurred. Venue ' + form.name.data + ' could not be updated.')
    finally:
        db.session.close()

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    venue = Venue.query.filter_by(id=venue_id).first_or_404()
    db.session.delete(venue)
    db.session.commit()
    #try:
    #    venue = Venue.query.filter_by(id=venue_id).first_or_404()
    #    db.session.delete(venue)
    #    db.session.commit()
    #    flash("Venue " + request.form['name'] + " is deleted successfully!")
    #    return render_template('pages/home.html')
    #except:
    #    db.session.rollback()
    #    flash("Venue " + request.form['name'] + " could not be deleted.")
    #finally:
    #    db.session.close()

    return render_template('pages/home.html'), jsonify({"success": True}), 200

#  Artists
#  ----------------------------------------------------------------

@app.route('/artists')
def artists():

    artists_query = Artist.query.order_by(Artist.name).all()
    data = []
    for artist in artists_query:
        data.append(artist)

    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    # get search string from the form
    search_string = ''.join(request.form.get('search_term', ''))

    # query all the artists from DB that contain search string in lowercase
    artists = Artist.query.filter(Artist.name.ilike('%' + f'%{search_string}%' + '%')).all()
    # count matches quantity
    artists_number = len(artists)
    data = []

    for artist in artists:
        # filter upcoming shows for the artist
        shows_number = Show.query.filter_by(artist_id=artist.id). \
            filter(Show.start_time >= datetime.now()). \
            count()

        data.append({
            "id": artist.id,
            "name": artist.name,
            "num_upcoming_shows": shows_number
        })

    response = {
        "count": artists_number,
        "data": data
    }
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the venue page with the given venue_id

    artist = Artist.query.filter_by(id=artist_id).first()
    artist.genres = ''.join(list(filter(lambda x: x != '{' and x != '}' and x != '"', artist.genres))).split(',')
    artist.upcoming_shows = []
    artist.past_shows = []
    upcoming_shows = Show.query.filter_by(artist_id=artist_id).\
            filter(Show.start_time >= datetime.now()).\
            all()

    for show in upcoming_shows:
        artist.upcoming_shows.append({
            "venue_id": show.venue_id,
            "venue_name": Venue.query.filter_by(id=show.venue_id).first().name,
            "venue_image_link": Venue.query.filter_by(id=show.venue_id).first().image_link,
            "start_time": format_datetime(str(show.start_time))
        })

    artist.upcoming_shows_count = len(upcoming_shows)

    past_shows = Show.query.filter_by(artist_id=artist_id). \
        filter(Show.start_time < datetime.now()). \
        all()

    for show in past_shows:
        artist.past_shows.append({
            "venue_id": show.venue_id,
            "venue_name": Venue.query.filter_by(id=show.venue_id).first().name,
            "venue_image_link": Venue.query.filter_by(id=show.venue_id).first().image_link,
            "start_time": format_datetime(str(show.start_time))
        })

    artist.past_shows_count = len(past_shows)

    return render_template('pages/show_artist.html', artist=artist)

#  Update
#  ----------------------------------------------------------------

@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.filter_by(id=artist_id).first_or_404()
    form = ArtistForm(obj=artist)

    # replace separators in the genres string so it would come as a list (comes as a list of chracters otherwise)
    form.genres.data = ''.join(list(filter(lambda x: x != '{' and x != '}' and x != '"', artist.genres))).split(',')
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # load the venue data from DB
    artist = Artist.query.filter_by(id=artist_id).first_or_404()
    form = ArtistForm(request.form)

    try:
        # pass form's data to DB
        artist.name = form.name.data
        artist.city = form.city.data
        artist.state = form.state.data
        artist.phone = form.phone.data
        artist.genres = form.genres.data
        artist.website = form.website.data
        artist.facebook_link = form.facebook_link.data
        artist.image_link = form.image_link.data

        if form.seeking_venue.data == 'y':
            artist.seeking_venue = True
        else:
            artist.seeking_venue = False

        artist.seeking_description = form.seeking_description.data
        db.session.commit()
        flash('Artist ' + form.name.data + ' was successfully updated!')

    except ValueError as e:
        print(e)
        db.session.rollback()
        print(sys.exc_info())
        flash('An error occurred. Artist ' + form.name.data + ' could not be updated.')
    finally:
        db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.filter_by(id=venue_id).first_or_404()
    form = VenueForm(obj=venue)

    # replace separators in the genres string so it would come as a list (comes as a list of characters otherwise)
    form.genres.data = ''.join(list(filter(lambda x: x != '{' and x != '}' and x != '"', venue.genres))).split(',')

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    # load the venue data from DB
    venue = Venue.query.filter_by(id=venue_id).first_or_404()
    form = VenueForm(request.form)

    try:
        # pass form's data to DB
        venue.name = form.name.data
        venue.city = form.city.data
        venue.state = form.state.data
        venue.phone = form.phone.data
        venue.address = form.address.data
        venue.genres = form.genres.data
        venue.website = form.website.data
        venue.facebook_link = form.facebook_link.data
        venue.image_link = form.image_link.data
        venue.seeking_talent = form.seeking_talent.data
        venue.seeking_description = form.seeking_description.data
        db.session.commit()
        flash('Venue ' + form.name.data + ' was successfully updated!')

    except ValueError as e:
        print(e)
        db.session.rollback()
        print(sys.exc_info())
        flash('An error occurred. Venue ' + form.name.data + ' could not be updated.')
    finally:
        db.session.close()

    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():

    form = ArtistForm(request.form)
    try:
        # initialize Artist object and pass form's data
        artist = Artist(name=form.name.data, city=form.city.data, state=form.state.data, phone=form.phone.data,
                      genres=form.genres.data, website=form.website.data,
                      facebook_link=form.facebook_link.data, image_link=form.image_link.data,
                      seeking_venue=form.seeking_venue.data, seeking_description=form.seeking_description.data)
        # pass form's data to DB
        db.session.add(artist)
        db.session.commit()
        flash('Artist ' + form.name.data + ' was successfully created!')

    except ValueError as e:
        print(e)
        db.session.rollback()
        print(sys.exc_info())
        flash('An error occurred. Artist ' + form.name.data + ' could not be created.')
    finally:
        db.session.close()

    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    all_shows = Show.query.all()
    data2 = []
    for show in all_shows:
        data2.append({
            "venue_id": show.venue_id,
            "venue_name": Venue.query.filter_by(id=show.venue_id).first().name,
            "artist_id": show.artist_id,
            "artist_name": Artist.query.filter_by(id=show.artist_id).first().name,
            "artist_image_link": Artist.query.filter_by(id=show.artist_id).first().image_link,
            "start_time": format_datetime(str(show.start_time))
        })

    return render_template('pages/shows.html', shows=data2)


@app.route('/shows/create')
def create_shows():
    # renders form
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    error = False
    body = {}
    try:
        artist_id = request.form['artist_id']
        venue_id = request.form['venue_id']
        start_time = request.form['start_time']

        show = Show(artist_id=artist_id, venue_id=venue_id, start_time=start_time)
        db.session.add(show)
        db.session.commit()
        body['artist_id'] = show.artist_id
        body['venue_id'] = show.venue_id
        body['start_time'] = show.start_time

    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Show could not be listed.')
    else:
        flash('Show was successfully listed!')

    return render_template('pages/home.html'), body


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')


#----------------------------------------------------------------------------#
# Seed data.
#----------------------------------------------------------------------------#

with app.app_context():

    # add venue seed data
    if db.session.query(Venue).count() == 0:
        venue_seed = [{
            "name": "The Musical Hop",
            "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
            "address": "1015 Folsom Street",
            "city": "San Francisco",
            "state": "CA",
            "phone": "123-123-1234",
            "website": "https://www.themusicalhop.com",
            "facebook_link": "https://www.facebook.com/TheMusicalHop",
            "seeking_talent": True,
            "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
            "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60"
        }, {
            "name": "The Dueling Pianos Bar",
            "genres": ["Classical", "R&B", "Hip-Hop"],
            "address": "335 Delancey Street",
            "city": "New York",
            "state": "NY",
            "phone": "914-003-1132",
            "website": "https://www.theduelingpianos.com",
            "facebook_link": "https://www.facebook.com/theduelingpianos",
            "seeking_talent": False,
            "image_link": "https://images.unsplash.com/photo-1497032205916-ac775f0649ae?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=750&q=80"
        }, {
            "name": "Park Square Live Music & Coffee",
            "genres": ["Rock n Roll", "Jazz", "Classical", "Folk"],
            "address": "34 Whiskey Moore Ave",
            "city": "San Francisco",
            "state": "CA",
            "phone": "415-000-1234",
            "website": "https://www.parksquarelivemusicandcoffee.com",
            "facebook_link": "https://www.facebook.com/ParkSquareLiveMusicAndCoffee",
            "seeking_talent": False,
            "image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80"
        }]


        for venue in venue_seed:
            g = Venue(**venue)
            db.session.add(g)
            db.session.commit()

# add atrist seed data
    if db.session.query(Artist).count() == 0:
        artist_seed = [{
            "id": 4,
            "name": "Guns N Petals",
            "genres": ["Rock n Roll"],
            "city": "San Francisco",
            "state": "CA",
            "phone": "326-123-5000",
            "website": "https://www.gunsnpetalsband.com",
            "facebook_link": "https://www.facebook.com/GunsNPetals",
            "seeking_venue": True,
            "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
            "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80"
        }, {
            "id": 5,
            "name": "Matt Quevedo",
            "genres": ["Jazz"],
            "city": "New York",
            "state": "NY",
            "phone": "300-400-5000",
            "facebook_link": "https://www.facebook.com/mattquevedo923251523",
            "seeking_venue": False,
            "image_link": "https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80"
        }, {
            "id": 6,
            "name": "The Wild Sax Band",
            "genres": ["Jazz", "Classical"],
            "city": "San Francisco",
            "state": "CA",
            "phone": "432-325-5432",
            "seeking_venue": False,
            "image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80"
        }]


        for artist in artist_seed:
            g = Artist(**artist)
            db.session.add(g)
            db.session.commit()


# add show seed data
    if db.session.query(Show).count() == 0:

        show_seed = []

        # show 1, get ids of venues and atrists by their names
        venue_id = Venue.query.filter_by(name="The Musical Hop").first().id
        artist_id = Artist.query.filter_by(name="Guns N Petals").first().id
        start_time = "2019-05-21T21:30:00.000Z"
        show = {
            "venue_id": venue_id,
            "artist_id": artist_id,
            "start_time": start_time
        }
        show_seed.append(show)

        # show 2
        venue_id = Venue.query.filter_by(name="Park Square Live Music & Coffee").first().id
        artist_id = Artist.query.filter_by(name="Matt Quevedo").first().id
        start_time = "2019-06-15T23:00:00.000Z"
        show = {
            "venue_id": venue_id,
            "artist_id": artist_id,
            "start_time": start_time
        }
        show_seed.append(show)

        # show 3
        venue_id = Venue.query.filter_by(name="Park Square Live Music & Coffee").first().id
        artist_id = Artist.query.filter_by(name="The Wild Sax Band").first().id
        start_time = "2035-04-01T20:00:00.000Z"
        show = {
            "venue_id": venue_id,
            "artist_id": artist_id,
            "start_time": start_time
        }
        show_seed.append(show)

        # show 4
        venue_id = Venue.query.filter_by(name="Park Square Live Music & Coffee").first().id
        artist_id = Artist.query.filter_by(name="The Wild Sax Band").first().id
        start_time = "2035-04-08T20:00:00.000Z"
        show = {
            "venue_id": venue_id,
            "artist_id": artist_id,
            "start_time": start_time
        }
        show_seed.append(show)

        # show 5
        venue_id = Venue.query.filter_by(name="Park Square Live Music & Coffee").first().id
        artist_id = Artist.query.filter_by(name="The Wild Sax Band").first().id
        start_time = "2035-04-15T20:00:00.000Z"
        show = {
            "venue_id": venue_id,
            "artist_id": artist_id,
            "start_time": start_time
        }
        show_seed.append(show)

        for show in show_seed:
            g = Show(**show)
            db.session.add(g)
            db.session.commit()


#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
