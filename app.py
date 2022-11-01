# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#
import dateutil.parser
import babel
from flask import (
    Flask,
    render_template,
    request,
    Response,
    flash,
    redirect,
    url_for,
    abort,
)
from flask_moment import Moment
from datetime import datetime
from sqlalchemy import func
import sys
from sqlalchemy.orm.exc import NoResultFound
import logging
from logging import Formatter, FileHandler
from flask_migrate import Migrate
from models import db, Venue, Artist, Show, Genre
from forms import *


app = Flask(__name__)
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = "postgresql://postgres:postgres@localhost:5432/mydb"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

moment = Moment(app)
db.init_app(app)

# connect to a local postgresql database
migrate = Migrate(app, db)


def format_datetime(value, format="medium"):
    date = dateutil.parser.parse(value)
    if format == "full":
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == "medium":
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale="en")


app.jinja_env.filters["datetime"] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


app.route("/")


def index():
    return render_template("pages/home.html")


#  ---------------------------------------------------------------------------#
#  Venues
#  ---------------------------------------------------------------------------#


@app.route("/venues")
def venues():

    # venues = (
    #     Venue.query.with_entities(func.count(Venue.id), Venue.city, Venue.state)
    #     .group_by(Venue.city, Venue.state)
    #     .all()
    # )

    venues = (
        db.session.query(Venue)
        .with_entities(func.count(Venue.id), Venue.city, Venue.state)
        .group_by(Venue.city, Venue.state)
        .all()
    )

    data = []

    for new_venue in venues:
        area_venues = (
            Venue.query.filter_by(state=new_venue.state)
            .filter_by(city=new_venue.city)
            .all()
        )
        venue_data = []
        for new_venue in area_venues:
            venue_data.append(
                {
                    "id": new_venue.id,
                    "name": new_venue.name,
                    "num_upcoming_shows": len(
                        db.session.query(Show)
                        .filter(Show.venue_id == 1)
                        .filter(Show.start_time > datetime.now())
                        .all()
                    ),
                }
            )

        data.append(
            {"city": new_venue.city, "state": new_venue.state, "venues": venue_data}
        )

    return render_template("pages/venues.html", areas=data)


@app.route("/venues/search", methods=["POST"])
def search_venues():
    search_term = request.form.get("search_term", "")
    search_result = (
        db.session.query(Venue).filter(Venue.name.ilike(f"%{search_term}%")).all()
    )
    data = []

    for result in search_result:
        data.append(
            {
                "id": result.id,
                "name": result.name,
                "num_upcoming_shows": len(
                    db.session.query(Show)
                    .filter(Show.venue_id == result.id)
                    .filter(Show.start_time > datetime.now())
                    .all()
                ),
            }
        )
    response = {"count": len(search_result), "data": data}
    return render_template(
        "pages/search_venues.html",
        results=response,
        search_term=request.form.get("search_term", ""),
    )


@app.route("/venues/<int:venue_id>")
def show_venue(venue_id):

    # venue = Venue.query.get(venue_id)
    venue = db.session.query(Venue).get(venue_id)

    if not venue:
        abort(404)
    else:
        # use python list-comprehension to iterate through
        # artist.genres object to get all genres names as python-list
        genres = [genre.name for genre in venue.genres]

        upcoming_shows_query = (
            db.session.query(Show)
            .join(Venue)
            .filter(Show.venue_id == venue_id)
            .filter(Show.start_time > datetime.now())
            .all()
        )

        upcoming_shows = []

        for show in upcoming_shows_query:
            upcoming_shows.append(
                {
                    "artist_id": show.artist_id,
                    "artist_name": show.artist.name,
                    "artist_image_link": show.artist.image_link,
                    "start_time": format_datetime(str(show.start_time)),
                }
            )

        past_shows_query = (
            db.session.query(Show)
            .join(Venue)
            .filter(Show.venue_id == venue_id)
            .filter(Show.start_time > datetime.now())
            .all()
        )
        past_shows = []

        for show in past_shows_query:
            past_shows.append(
                {
                    "artist_id": show.artist_id,
                    "artist_name": show.artist.name,
                    "artist_image_link": show.artist.image_link,
                    "start_time": format_datetime(str(show.start_time)),
                }
            )

        data = {
            "id": venue_id,
            "name": venue.name,
            "genres": genres,
            "address": venue.address,
            "city": venue.city,
            "state": venue.state,
            "phone": (venue.phone[:3] + "-" + venue.phone[3:6] + "-" + venue.phone[6:]),
            "website_link": venue.website_link,
            "facebook_link": venue.facebook_link,
            "seeking_talent": venue.seeking_talent,
            "seeking_description": venue.seeking_description,
            "image_link": venue.image_link,
            "past_shows": past_shows,
            "past_shows_count": len(past_shows),
            "upcoming_shows": upcoming_shows,
            "upcoming_shows_count": len(upcoming_shows),
        }

    return render_template("pages/show_venue.html", venue=data)


#  -----------------------------------------------------------------------#
#  Create Venue
#  -----------------------------------------------------------------------#


@app.route("/venues/create", methods=["GET"])
def create_venue_form():
    form = VenueForm()
    return render_template("forms/new_venue.html", form=form)


@app.route("/venues/create", methods=["POST"])
def create_venue_submission():

    form = VenueForm()

    name = form.name.data.strip()
    city = form.city.data
    state = form.state.data.strip()
    address = form.address.data.strip()
    phone = form.phone.data
    image_link = form.image_link.data.strip()
    facebook_link = form.facebook_link.data.strip()
    genres = form.genres.data
    website_link = form.website_link.data.strip()
    seeking_talent = True if form.seeking_talent.data == "Yes" else False
    seeking_description = form.seeking_description.data.strip()

    if not form.phone.validate(form):
        for fieldName, errorMessages in form.errors.items():
            for err in errorMessages:
                if fieldName == "phone":
                    flash(err)
        return redirect(url_for("create_venue_submission"))
    else:
        insert_error = False
        try:
            new_venue = Venue(
                name=name,
                city=city,
                state=state,
                address=address,
                phone=phone,
                image_link=image_link,
                facebook_link=facebook_link,
                website_link=website_link,
                seeking_talent=seeking_talent,
                seeking_description=seeking_description,
            )
            for genre in genres:
                fetch_genre = Genre.query.filter_by(name=genre).one_or_none()
                if fetch_genre:
                    new_venue.genres.append(fetch_genre)
                else:
                    new_genre = Genre(name=genre)
                    db.session.add(new_genre)
                    new_venue.genres.append(new_genre)

            db.session.add(new_venue)
            db.session.commit()
        except Exception as e:
            insert_error = True
            print(f'Exception "{e}"')
            db.session.rollback()
        finally:
            db.session.close()
        if not insert_error:
            flash("Venue " + request.form["name"] + " was successfully listed!")
            return redirect(url_for("index"))
        else:
            flash(
                "An error occurred. Venue "
                + request.form["name"]
                + " could not be listed."
            )
            abort(500)
            # return render_template("pages/home.html")


@app.route("/venues/<venue_id>", methods=["DELETE"])
def delete_venue(venue_id):

    error_on_delete = False
    try:
        new_venue = Venue.query.get(venue_id)
        db.session.delete(new_venue)
        db.session.commit()
    except NoResultFound:
        error_on_delete = True
        db.session.rollback()
        print(sys.exc_info())
        abort(404)
    finally:
        db.session.close()
    if error_on_delete:
        flash(f"An error occurred. Venue {new_venue.name} could not be deleted.")
        abort(500)
    else:
        flash(f"Venue {new_venue.name} was successfully deleted.")

    return render_template("pages/home.html")


#  ----------------------------------------------------------------#
#  Artists
#  ----------------------------------------------------------------#


@app.route("/artists")
def artists():
    artists = db.session.query(Artist).all()

    data = []

    for artist in artists:
        data.append({"id": artist.id, "name": artist.name})
    return render_template("pages/artists.html", artists=data)


@app.route("/artists/search", methods=["POST"])
def search_artists():
    search_term = request.form.get("search_term", "")
    search_result = (
        db.session.query(Artist).filter(Artist.name.ilike(f"%{search_term}%")).all()
    )

    data = []
    for result in search_result:
        data.append(
            {
                "id": result.id,
                "name": result.name,
                "num_upcomming_shows": len(
                    db.session.query(Show)
                    .filter(Show.artist_id == result.id)
                    .filter(Show.start_time > datetime.now())
                    .all()
                ),
            }
        )

    response = {"count": len(search_result), "data": data}

    return render_template(
        "pages/search_artists.html",
        results=response,
        search_term=request.form.get("search_term", ""),
    )


@app.route("/artists/<int:artist_id>")
def show_artist(artist_id):

    # artist = Artist.query.get(artist_id)
    artist = db.session.query(Artist).get(artist_id)

    if not artist:
        abort(404)
    else:
        # use python list-comprehension to iterate through
        # artist.genres object to get all genres names as python-list
        genres = [genre.name for genre in artist.genres]

        upcoming_shows_query = (
            db.session.query(Show)
            .join(Venue)
            .filter(Show.artist_id == artist_id)
            .filter(Show.start_time > datetime.now())
            .all()
        )

        upcoming_shows = []

        for show in upcoming_shows_query:
            upcoming_shows.append(
                {
                    "venue_id": show.venue_id,
                    "venue_name": show.venue.name,
                    "artist_image_link": show.venue.image_link,
                    "start_time": format_datetime(str(show.start_time)),
                }
            )

        past_shows_query = (
            db.session.query(Show)
            .join(Venue)
            .filter(Show.artist_id == artist_id)
            .filter(Show.start_time < datetime.now())
            .all()
        )

        past_shows = []

        for show in past_shows_query:
            past_shows.append(
                {
                    "venue_id": show.venue_id,
                    "venue_name": show.venue.name,
                    "artist_image_link": show.artist.image_link,
                    "start_time": format_datetime(str(show.start_time)),
                }
            )

        data = {
            "id": artist_id,
            "name": artist.name,
            "genres": genres,
            "city": artist.city,
            "phone": (
                artist.phone[:3] + "-" + artist.phone[3:6] + "-" + artist.phone[6:]
            ),
            "website_link": artist.website_link,
            "facebook_link": artist.facebook_link,
            "seeking_venue": artist.seeking_venue,
            "seeking_description": artist.seeking_description,
            "image_link": artist.image_link,
            "past_shows": past_shows,
            "past_shows_count": len(past_shows),
            "upcoming_shows": upcoming_shows,
            "upcoming_shows_count": len(upcoming_shows),
        }
    return render_template("pages/show_artist.html", artist=data)


#  ----------------------------------------------------------------
#  Update
#  ----------------------------------------------------------------


@app.route("/artists/<int:artist_id>/edit", methods=["GET"])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.filter(Artist.id == artist_id).one_or_none()

    if artist is None:
        abort(404)
    else:
        form.name.data = artist.name
        form.city.data = artist.city
        form.state.data = artist.state
        form.phone.data = artist.phone
        form.genres.data = artist.genres
        form.facebook_link.data = artist.facebook_link
        form.image_link.data = artist.image_link
        form.website_link.data = artist.website_link
        form.seeking_venue.data = artist.seeking_venue
        form.seeking_description.data = artist.seeking_description

    return render_template("forms/edit_artist.html", form=form, artist=artist)


@app.route("/artists/<int:artist_id>/edit", methods=["POST"])
def edit_artist_submission(artist_id):
    # take values from the form submitted, and update existing
    # artist record with ID <artist_id> using the new attributes
    update_error = False

    form = ArtistForm()

    name = form.name.data.strip()
    city = form.city.data.strip()
    state = form.state.data.strip()
    phone = form.phone.data
    image_link = form.image_link.data.strip()
    facebook_link = form.facebook_link.data.strip()
    genres = form.genres.data
    website_link = form.website_link.data.strip()
    seeking_venue = True if form.seeking_venue.data == "Yes" else False
    seeking_description = form.seeking_description.data.strip()

    try:
        artist = Artist.query.get(artist_id)
        artist.name = name
        artist.city = city
        artist.state = state
        artist.phone = phone
        artist.image_link = image_link
        artist.facebook_link = facebook_link
        artist.website_link = website_link
        artist.seeking_venue = seeking_venue
        artist.seeking_description = seeking_description

        artist.genres = []

        for genre in genres:
            fetch_genre = Genre.query.filter_by(name=genre).one_or_none()
            if fetch_genre:
                artist.genres.append(fetch_genre)
            else:
                new_genre = Genre(name=genre)
                db.session.add(new_genre)
                artist.genres.append(new_genre)
        db.session.commit()
        # on successful submission flash success
        flash("Artist " + name + " was successfully updated!")
    except:
        db.session.rollback()
        flash("An error occurred. Artist " + name + " could not be updated.")
        print(sys.exc_info())
        abort(500)
    finally:
        db.session.close()

    return redirect(url_for("show_artist", artist_id=artist_id))


@app.route("/venues/<int:venue_id>/edit", methods=["GET"])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.filter_by(id=venue_id).one_or_none()
    if venue is None:
        abort(404)
    else:
        form.name.data = venue.name
        form.city.data = venue.city
        form.state.data = venue.state
        form.phone.data = venue.phone
        form.address.data = venue.address
        form.genres.data = venue.genres
        form.image_link.data = venue.image_link
        form.facebook_link.data = venue.facebook_link
        form.website_link.data = venue.website_link
        form.seeking_talent.data = venue.seeking_talent
        form.seeking_description.data = venue.seeking_description

    # else:
    #     # If specified url is not valid redirect to homepage
    #     return redirect(url_for("index"))
    # venue = {
    #     "id": 1,
    #     "name": "The Musical Hop",
    #     "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
    #     "address": "1015 Folsom Street",
    #     "city": "San Francisco",
    #     "state": "CA",
    #     "phone": "123-123-1234",
    #     "website": "https://www.themusicalhop.com",
    #     "facebook_link": "https://www.facebook.com/TheMusicalHop",
    #     "seeking_talent": True,
    #     "seeking_description": "We are on the lookout for a local new_venue to play every two weeks. Please call us.",
    #     "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60",
    # }
    # populate form with values from venue with ID <venue_id>
    return render_template("forms/edit_venue.html", form=form, venue=venue)


@app.route("/venues/<int:venue_id>/edit", methods=["POST"])
def edit_venue_submission(venue_id):
    # take values from the form submitted, and update existing
    # new_venue record with ID <venue_id> using the new attributes
    update_error = False

    form = VenueForm()

    name = form.name.data.strip()
    city = form.city.data.strip()
    state = form.state.data
    address = form.address.data.strip()
    phone = form.phone.data
    image_link = form.image_link.data.strip()
    facebook_link = form.facebook_link.data.strip()
    genres = form.genres.data
    website_link = form.website_link.data.strip()
    seeking_talent = True if form.seeking_talent.data == "Yes" else False
    seeking_description = form.seeking_description.data.strip()

    try:
        venue = Venue.query.filter_by(id=venue_id).one_or_none()

        venue.name = name
        venue.city = city
        venue.state = state
        venue.address = address
        venue.phone = phone
        venue.image_link = image_link
        venue.facebook_link = facebook_link
        venue.website_link = website_link
        venue.seeking_talent = seeking_talent
        venue.seeking_description = seeking_description

        venue.genres = []

        for genre in genres:
            fetch_genre = Genre.query.filter_by(name=genre).one_or_none()
            if fetch_genre:
                venue.genres.append(fetch_genre)
            else:
                new_genre = Genre(name=genre)
                db.session.add(new_genre)
                venue.genres.append(new_genre)
        db.session.commit()
    except:
        update_error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if update_error:
        flash("An error occurred. Venue " + name + " could not be updated.")
        abort(500)
    else:
        flash("Venue " + name + " was successfully updated!")

    return redirect(url_for("show_venue", venue_id=venue_id))


#  ----------------------------------------------------------------
#  Create Artist
#  ----------------------------------------------------------------


@app.route("/artists/create", methods=["GET"])
def create_artist_form():
    form = ArtistForm()
    return render_template("forms/new_artist.html", form=form)


@app.route("/artists/create", methods=["POST"])
def create_artist_submission():
    form = ArtistForm()

    name = form.name.data.strip()
    city = form.city.data.strip()
    state = form.state.data
    phone = form.phone.data
    image_link = form.image_link.data.strip()
    facebook_link = form.facebook_link.data.strip()
    genres = form.genres.data
    website_link = form.website_link.data.strip()
    seeking_venue = True if form.seeking_venue.data == "Yes" else False
    seeking_description = form.seeking_description.data.strip()

    if not form.phone.validate(form):
        for fieldName, errorMessages in form.errors.items():
            for err in errorMessages:
                if fieldName == "phone":
                    flash(err)
        return redirect(url_for("create_venue_submission"))
    else:
        insert_error = False
        try:
            new_artist = Artist(
                name=name,
                city=city,
                state=state,
                phone=phone,
                image_link=image_link,
                facebook_link=facebook_link,
                website_link=website_link,
                seeking_venue=seeking_venue,
                seeking_description=seeking_description,
            )
            for genre in genres:
                fetch_genre = Genre.query.filter_by(name=genre).one_or_none()
                if fetch_genre:
                    new_artist.genres.append(fetch_genre)
                else:
                    new_genre = Genre(name=genre)
                    db.session.add(new_genre)
                    new_artist.genres.append(new_genre)

            db.session.add(new_artist)
            db.session.commit()
        except:
            insert_error = True
            db.session.rollback()
            print(sys.exc_info())
        finally:
            db.session.close()
        if not insert_error:
            flash("Artist " + request.form["name"] + " was successfully listed!")
            return redirect(url_for("index"))
        else:
            flash(
                "An error occurred. Artist "
                + request.form["name"]
                + " could not be listed."
            )
            abort(500)

            # return render_template("pages/home.html")


#  ----------------------------------------------------------------
#  Shows
#  ----------------------------------------------------------------


@app.route("/shows")
def shows():

    data = []
    shows = Show.query.all()
    for show in shows:
        data.append(
            {
                "venue_id": show.venue.id,
                "venue_name": show.venue.name,
                "artist_id": show.artist.id,
                "artist_name": show.artist.name,
                "artist_image_link": show.artist.image_link,
                "start_time": show.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    # data = [
    #     {
    #         "venue_id": 1,
    #         "venue_name": "The Musical Hop",
    #         "artist_id": 4,
    #         "artist_name": "Guns N Petals",
    #         "artist_image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
    #         "start_time": "2019-05-21T21:30:00.000Z",
    #     },
    #     {
    #         "venue_id": 3,
    #         "venue_name": "Park Square Live Music & Coffee",
    #         "artist_id": 5,
    #         "artist_name": "Matt Quevedo",
    #         "artist_image_link": "https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80",
    #         "start_time": "2019-06-15T23:00:00.000Z",
    #     },
    #     {
    #         "venue_id": 3,
    #         "venue_name": "Park Square Live Music & Coffee",
    #         "artist_id": 6,
    #         "artist_name": "The Wild Sax Band",
    #         "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
    #         "start_time": "2035-04-01T20:00:00.000Z",
    #     },
    #     {
    #         "venue_id": 3,
    #         "venue_name": "Park Square Live Music & Coffee",
    #         "artist_id": 6,
    #         "artist_name": "The Wild Sax Band",
    #         "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
    #         "start_time": "2035-04-08T20:00:00.000Z",
    #     },
    #     {
    #         "venue_id": 3,
    #         "venue_name": "Park Square Live Music & Coffee",
    #         "artist_id": 6,
    #         "artist_name": "The Wild Sax Band",
    #         "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
    #         "start_time": "2035-04-15T20:00:00.000Z",
    #     },
    # ]
    return render_template("pages/shows.html", shows=data)


@app.route("/shows/create")
def create_shows():

    form = ShowForm()
    return render_template("forms/new_show.html", form=form)


@app.route("/shows/create", methods=["POST"])
def create_show_submission():
    error = False
    form = ShowForm()

    artist_id = form.artist_id.data.strip()
    venue_id = form.venue_id.data.strip()
    start_time = form.start_time.data

    error = False

    try:
        show = Show(artist_id=artist_id, venue_id=venue_id, start_time=start_time)
        db.session.add(show)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash("An error occurred. Show could not be listed.")
        abort(500)
    if not error:
        flash("Show was successfully listed!")

    return render_template("pages/home.html")


@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


if not app.debug:
    file_handler = FileHandler("error.log")
    file_handler.setFormatter(
        Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info("errors")

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#


# Default port:
if __name__ == "__main__":
    app.run()

# Or specify port manually:
"""
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
"""
