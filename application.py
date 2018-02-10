import os
import re
from flask import Flask, jsonify, render_template, request, url_for
from flask_jsglue import JSGlue

from cs50 import SQL
from helpers import lookup

# configure application
app = Flask(__name__)
JSGlue(app)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///mashup.db")

@app.route("/")
def index():
    """Render map."""
    if not os.environ.get("API_KEY"):
        raise RuntimeError("API_KEY not set")
    return render_template("index.html", key=os.environ.get("API_KEY"))

@app.route("/articles")
def articles():
    """Look up articles for geo."""
    geo = request.args.get("geo")
    # make sure geo is not None or empty.
    if not geo or geo=="":
        raise RuntimeError("missing geo");
    articles_array = [];
    google_array = lookup(geo);
    # keep number of stories to max of 5
    for i in range(0, 5):
        articles_array.append(google_array[i]);
    return jsonify(articles_array)

@app.route("/search")#For now expects only postal code.
def search():
    """Search for places that match query."""
    query = request.args.get("q")
    if not query or query=="":
        raise RuntimeError("missing query parameter")
    if "," in query:
        # remove whitespace
        query.replace(" ", "")
        # split up extra params...
        query_array = query.split(",")
    else:
        query_array = query.split()# split at the space. 
        
    # Should split at both and check to make sure index is not punctuation.
    for i in range(0, len(query_array)):
        query_array[i]+="%"#append SQL's wildcard to match any num of characters
        
    ret = db.execute("""SELECT * FROM places WHERE postal_code LIKE :q
    """, q=query_array[0] )
    
    return jsonify(ret)

@app.route("/update")
def update():
    """Find up to 15 places within view."""

    # ensure parameters are present
    if not request.args.get("sw"):
        raise RuntimeError("missing sw")
    if not request.args.get("ne"):
        raise RuntimeError("missing ne")

    # ensure parameters are in lat,lng format
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("sw")):
        raise RuntimeError("invalid sw")
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("ne")):
        raise RuntimeError("invalid ne")

    # explode southwest corner into two variables
    (sw_lat, sw_lng) = [float(s) for s in request.args.get("sw").split(",")]

    # explode northeast corner into two variables
    (ne_lat, ne_lng) = [float(s) for s in request.args.get("ne").split(",")]

    # find 15 cities within view, pseudorandomly chosen if more within view
    if (sw_lng <= ne_lng):

        # doesn't cross the antimeridian
        rows = db.execute("""SELECT * FROM places
            WHERE :sw_lat <= latitude AND latitude <= :ne_lat AND (:sw_lng <= longitude AND longitude <= :ne_lng)
            GROUP BY country_code, place_name, admin_code1
            ORDER BY RANDOM()
            LIMIT 15""",
            sw_lat=sw_lat, ne_lat=ne_lat, sw_lng=sw_lng, ne_lng=ne_lng)

    else:

        # crosses the antimeridian
        rows = db.execute("""SELECT * FROM places
            WHERE :sw_lat <= latitude AND latitude <= :ne_lat AND (:sw_lng <= longitude OR longitude <= :ne_lng)
            GROUP BY country_code, place_name, admin_code1
            ORDER BY RANDOM()
            LIMIT 15""",
            sw_lat=sw_lat, ne_lat=ne_lat, sw_lng=sw_lng, ne_lng=ne_lng)

    # output places as JSON
    return jsonify(rows)
