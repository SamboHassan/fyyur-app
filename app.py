from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    sites = ["twitter", "facebook", "instagram", "whatsapp"]
    return render_template("about.html", sites=sites)


@app.route("/<name>")
def welcome(name):
    return render_template("welcome.html", name=name)


@app.route("/contact/<role>")
def contact(role):
    return render_template("contact.html", person=role)


# If you have the debugger disabled or trust the users on your network, you can
# make the server publicly available simply by adding --host=0.0.0.0 to the command line:

# $ flask run --host=0.0.0.0
# This tells your operating system to listen on all public IPs.

# To enable debug mode, use the --debug option.
# $ flask --app hello --debug run

# Default port:
if __name__ == "__main__":
    app.run()

# Or specify port manually:
"""
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
"""
