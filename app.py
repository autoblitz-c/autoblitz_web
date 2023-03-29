# resources...
import json
import requests
from datetime import datetime, time, date
import time
import flask
from flask import request, render_template, redirect, jsonify, Response, flash
import urllib.parse
from phonenumbers import geocoder, parse
from geopy.geocoders import Nominatim
import geoip2.database
import stripe
import smtplib
import email
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText

from email.utils import formatdate, formataddr
from email.header import Header
from email import encoders
from werkzeug.utils import secure_filename
from dotenv import load_dotenv, find_dotenv
import os
from functools import wraps
import googlemaps

#load_dotenv(find_dotenv())
# templates path and app creation

app = flask.Flask(__name__, template_folder="templates/")
app.config["DEBUG"] = False
app.config["UPLOAD_FOLDER"] = "static/"
app.config["Book"] = "static/booking/"
app.secret_key = '123456789@autoblitz'


# lat_long finder
def lat_long(address: str):
    try:
        url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(address) + '?format=json'

        lat_long = requests.get(url).json()
        lat = lat_long[0]["lat"]
        lon = lat_long[0]["lon"]
        return lat, lon
    except:
        flash('Ihre Anfrage wird nicht bearbeitet. Bitte geben Sie die gültige Adresse ein oder wählen Sie aus den \
         Dropdowns in den Abholort und Zielort.')


# phone number validation
def ph_country(phone_number: str):
    try:
        ph = parse(phone_number, None)
        country = geocoder.description_for_number(ph, "en")
        return country
    except:
        flash('Ihre Anfrage wird nicht bearbeitet. Bitte geben Sie eine gültige Telefonnummer ein.')


# filtering service based on city
def city_filter(address: str):
    geolocator = Nominatim(user_agent="geoapiExercises")
    lat, lon = lat_long(address)
    location = geolocator.reverse(lat + "," + lon)
    loc = location.raw['address']
    return loc


# finding zipcode
def zip_code(address: str):
    geolocator = Nominatim(user_agent="geoapiExercises")
    location = geolocator.geocode(address)
    data = location.raw
    loc_data = data['display_name'].split(',')
    return loc_data[-2]


# finding street
def street(address: str):
    geolocator = Nominatim(user_agent="geoapiExercises")
    location = geolocator.geocode(address)
    data = location.raw
    loc_data = data['display_name'].split(',')
    return loc_data[0]


def unix(datum: str, zeit: str):
    date_str = datum  # Example date string in ISO format
    date_format = "%Y-%m-%d"  # Format string for ISO date
    time_str = zeit  # Example time in 24-hour format
    time_format = "%H:%M"  # Format string for 24-hour time
    # Parse date string and time string into date and time objects
    date_obj = datetime.strptime(date_str, date_format).date()
    time_obj = datetime.strptime(time_str, time_format).time()
    # Combine date and time objects into a datetime object
    datetime_obj = datetime.combine(date_obj, time_obj)
    return int(time.mktime(datetime_obj.timetuple()))


g_file = os.path.join(app.config['UPLOAD_FOLDER'], 'GeoLite2-Country.mmdb')
geoip_reader = geoip2.database.Reader(g_file)


# user location access
def check_location():
    try:
        ip_address = request.remote_addr
        country = geoip_reader.country(ip_address).country.iso_code

        if country != 'DEU':
            return 'Access denied'
    except:
        return


# calculating distance of address
def cal_dis(pick: str, drop: str):
    # Example time in 24-hour format

    gmaps = googlemaps.Client(key=os.environ.get('map'))
    my_dist = gmaps.distance_matrix([pick], [drop], mode="driving")

    return float(my_dist['rows'][0]['elements'][0]['distance']['value'] / 1000)


def cal_price(pick: str, drop: str, vehicle: str):
    dist = cal_dis(pick, drop)
    if vehicle == "PKW für bis zu 4 Personen und 2 Koffer":
        if dist < 1:
            price = float(4.3 + 0 + 2.20)
            return round(price, 2)
        else:
            price = float(4.3 + 0 + (2.20 * dist))
            return round(price, 2)
    elif vehicle == "Kombi für bis zu 4 Personen und 4 Koffer":
        if dist < 1:
            price = float(4.3 + 5 + 2.20)
            return round(price, 2)
        else:
            price = float(4.3 + 5 + (2.20 * dist))
            return round(price, 2)
    else:
        if dist < 1:
            price = float(4.3 + 10 + 2.20)
            return round(price, 2)
        else:
            price = float(4.3 + 10 + (2.20 * dist))
            return round(price, 2)


# stripe key
#stripe.api_key = os.getenv('t_s_s_k')


# stripe.api_key = os.environ.get('t_s_s_k')


# creating auth
def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'autoblitz' and password == '1234@autoblitz'


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    return decorated


# home page
@app.route('/', methods=['POST', 'GET'])
def home():
    if check_location() == 'Access denied':
        return "Access Denied"

    return render_template('home.html')


# about us page
@app.route('/about_us', methods=['POST', 'GET'])
def about_us():
    if check_location() == 'Access denied':
        return "Access Denied"
    return render_template('about_us.html')


# booking page
@app.route('/book', methods=['POST', 'GET'])
def book():
    if check_location() == 'Access denied':
        return "Access Denied"
    return render_template('book.html')


# vacancy page
@app.route('/vacancy', methods=['POST', 'GET'])
def vacancy():
    if check_location() == 'Access denied':
        return "Access Denied"
    return render_template('vacancy.html')


# vacancy with sending mail
@app.route('/vacancy_result', methods=['POST', 'GET'])
def vacancy_result():
    if check_location() == 'Access denied':
        return "Access Denied"
    msg0 = "############## Bewerberdaten : ###############" + '\n'
    name = request.form.get('VName')
    phone = request.form.get('VPhone')

    mail = request.form.get('VMail')

    data = "Bewerbername =  {name}" + '\n' + "Bewerber-Telefonnummer = {phone}" + '\n' + "Bewerber-Mail-ID = {mail}" + '\n' + '\n'

    body = msg0 + data.format(name=name, phone=phone, mail=mail)
    licence = request.files['licence']
    licence_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(licence.filename))

    PB = request.files['P-letter']
    ############ form validating ###################
    # whole form validation check point
    if name == "" or str(phone) == "" or str(phone).find("+49") == -1 or mail == "" or licence == "" or PB == "":
        error = "Ihre Bewerbung wurde noch nicht eingereicht. Bitte füllen Sie das Formular korrekt aus und geben \
        Sie eine gültige Telefonnummer (einschließlich +49), E-Mail und Dokumente an."
        flash(error)

    # phone number validation checkpoint
    elif ph_country(str(phone)) != "Germany":
        flash("Ihre Bewerbung wird nicht übermittelt, da nur deutsche Handynummern akzeptiert werden.")

    else:
        licence.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(licence.filename)))
        PB_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(PB.filename))

        PB.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(PB.filename)))

        msg = MIMEMultipart()
        msg['From'] = "cologne.autoblitz@gmail.com"
        msg['To'] = 'info@autoblitz-koeln.de'
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = "Neue Stellenbewerbung"
        msg.attach(MIMEText(body, 'plain'))


        for f in request.files:
            part = MIMEBase(
                'application', "octet-stream"
            )
            path = "static/{name}"
            part.set_payload(open(path.format(name=request.files[f].filename), "rb").read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=request.files[f].filename)
            msg.attach(part)

        error = None

        smtp = smtplib.SMTP('smtp.gmail.com', 587)
        # start TLS for security
        smtp.starttls()

    # Authentication
    smtp.login("cologne.autoblitz@gmail.com", os.environ.get('c'))


        # Authentication
        smtp.login("cologne.autoblitz@gmail.com", "xrqhdhqwzkrwkutc")

        smtp.sendmail("cologne.autoblitz@gmail.com", "info@autoblitz-koeln.de", msg.as_string())

        smtp.quit()
        os.remove(licence_path)

        os.remove(PB_path)

    return render_template('vacancy.html')


# taxi booking page
@app.route('/taxi', methods=['POST', 'GET'])
def taxi():
    if check_location() == 'Access denied':
        return "Access Denied"
    return render_template('taxi.html')


# booking data storage
file_N = []


@app.route('/booking', methods=['POST'])
def booking():
    if check_location() == 'Access denied':
        return "Access Denied"
    file_N.clear()
    name = request.form.get('Name')
    phone = request.form.get('Phone')
    mail = request.form.get('Mail')
    pick = request.form.get('Pick-up')
    drop = request.form.get('Drop')
    date = request.form.get('Date')
    time = request.form.get('Time')
    vehicle = request.form.get('Vehicle')
    book = {"name": name,
            "phone": phone,
            "mail": mail,
            "pick": pick,
            "drop": drop,
            "date": date,
            "time": time,
            "vehicle": vehicle}
    file_name = os.path.join(app.config["Book"], name.split()[0] + '.json')
    file_N.append(file_name)
    with open(file_name, "w") as f:
        json.dump(book, f)

    return jsonify({'message': 'Form data received!'})


# ambulance booking page
@app.route('/ambulance', methods=['POST', 'GET'])
def ambulance():
    if check_location() == 'Access denied':
        return "Access Denied"
    return render_template('ambulance.html')


@app.route('/ambulance_result', methods=['POST', 'GET'])
def ambulance_result():
    if check_location() == 'Access denied':
        return "Access Denied"
    msg0 = "############## Kundendaten : ###############" + '\n'
    name = request.form.get('PName')
    phone = request.form.get('PPhone')
    age = request.form.get('PAge')

    mail = request.form.get('PMail')

    data = f"Kundenname =  {name}" + '\n' + f"Kundenalter =  {age}" + '\n' + f"Kunden-Telefonnummer = {phone}" + '\n' + f"Kunden-Mail-ID = {mail}" + '\n' + '\n'
    msg1 = "############## Buchungsdetails : ###############" + '\n'
    date = request.form.get("PDate")
    time = request.form.get("PTime")
    ins = request.form.get("PInsurance")
    pick = request.form.get("PPick-up")
    drop = request.form.get("PDrop")
    data1 = f"Datum =  {date}" + '\n' + f"Zeit =  {time}" + '\n' + f"Krankenversicherungsart = {ins}" + '\n' + f"Abholort = {pick}" + '\n' + f"Zielort = {drop}" + '\n' + '\n' + '\n'

    body = msg0 + data + msg1 + data1
    licence = request.files['Doctor-letter']
    licence_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(licence.filename))

    PB = request.files['P-letter']

    ############ form validating ###################
    # whole form validation check point
    if name == "" or str(phone) == "" or str(phone).find("+49") == -1 or str(
            age) == "" or str(date) == "" or str(time) == "" or str(ins) == "" or \
            str(pick) == "" or str(drop) == "" or mail == "" or licence == "":
        error = "Ihre Anfrage wurde noch nicht eingereicht. Bitte füllen Sie das Formular korrekt aus und geben \
           Sie eine gültige Telefonnummer (einschließlich +49), E-Mail, Alter, Abholort, Zielort, Datum, Zeit und Dokumente an."
        flash(error)

    # phone number validation checkpoint
    elif ph_country(str(phone)) != "Germany":
        flash("Ihre Anfrage wird nicht übermittelt, da nur deutsche Handynummern akzeptiert werden.")

    elif city_filter(str(pick))["city"] != "Köln" or city_filter(str(drop))["city"] != "Köln":
        flash("Es tut uns sehr leid.  Wir bedienen den angegebenen Ort nicht.")

    else:

        licence.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(licence.filename)))
        PB_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(PB.filename))
        if request.files['P-letter'].filename != "":
            PB.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(PB.filename)))


        msg = MIMEMultipart()
        msg['From'] = "cologne.autoblitz@gmail.com"
        msg['To'] = 'bestellung@autoblitz-koeln.de'

    # Authentication
    smtp.login("cologne.autoblitz@gmail.com", os.environ.get('c'))


        msg['Subject'] = "Neuer Auftrag für Krankentransport"
        msg.attach(MIMEText(body, 'plain'))

        for f in request.files:

            if request.files[f].filename != "":
                part = MIMEBase(
                    'application', "octet-stream"
                )
                path = "static/{name}"
                part.set_payload(open(path.format(name=request.files[f].filename), "rb").read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment', filename=request.files[f].filename)
                msg.attach(part)

        smtp = smtplib.SMTP('smtp.gmail.com', 587)
        # start TLS for security
        smtp.starttls()

        # Authentication
        smtp.login("cologne.autoblitz@gmail.com", "xrqhdhqwzkrwkutc")

        smtp.sendmail("cologne.autoblitz@gmail.com", "bestellung@autoblitz-koeln.de", msg.as_string())

        smtp.quit()
        os.remove(licence_path)
        if request.files['P-letter'].filename != "":
            os.remove(PB_path)


    # Authentication
    s.login("bestellung@autoblitz-koeln.de", os.environ.get('b'))


        message0 = "Vielen Dank für deine Bestellung." + '\n' + '\n' + "Dein Auto wird in kürze auf dem Weg zu dir sein." + '\n' + "Wenn du Fragen hast, kannst du dich gerne unter 0221612277 melden." + '\n' + '\n'
        message1 = "mit freundlichen Grüßen" + '\n' + "Team Autoblitz"

        # creates SMTP session

        s = smtplib.SMTP("smtp.udag.de", port=587)
        s.ehlo()

        # start TLS for security
        s.starttls()
        s.ehlo()

        # Authentication
        s.login("bestellung@autoblitz-koeln.de", "tiam2002")

        mail_msg = EmailMessage()

        mail_msg['Subject'] = Header("Bestellbestätigung").encode()
        mail_msg['From'] = "bestellung@autoblitz-koeln.de"
        mail_msg['To'] = request.form.get('PMail')
        mail_msg['Message-id'] = email.utils.make_msgid()
        mail_msg['Date'] = email.utils.formatdate()

        message = message0 + message1

        # sending the mail
        mail_msg.set_content(message)

        s.send_message(mail_msg)

        # terminating the session
        s.quit()

    return render_template('ambulance.html')


# kappey page
@app.route('/kappey', methods=['POST', 'GET'])

def kappey():
    return render_template('kappey.html')


# contact_us page
@app.route('/contact_us', methods=['POST', 'GET'])
def contact_us():
    if check_location() == 'Access denied':
        return "Access Denied"
    return render_template('contact_us.html')


# kappey result page
@app.route('/kappey_result', methods=['POST', 'GET'])

def kappey_result():
    msg = "Hello," + '\n' + '\n'
    date = request.form.getlist('date')
    time = request.form.getlist('time')
    kms = request.form.getlist('kms')
    info = request.form.getlist('info')
    for i in range(0, len(date)):
        data = "Form " + str(i + 1) + '\n' + "Date = " + str(date[i]) + '\n' + "Zeit = " + str(
            time[i]) + '\n' + "KMS = " + str(kms[i]) + '\n' + "info = " + str(info[i]) + '\n' + '\n' + '\n'

        msg = msg + data
    # creates SMTP session

    s = smtplib.SMTP('smtp.gmail.com', 587)

    # start TLS for security
    s.starttls()

    # Authentication
    s.login("cologne.autoblitz@gmail.com", "xrqhdhqwzkrwkutc")

    # message to be sent
    end = '\n' + "Danke und Grüße, " + '\n' + 'Cologne-autoblitz'
    message = msg + end

    mail_msg = EmailMessage()
    mail_msg.set_content(message)
    mail_msg['Subject'] = "Kappey"
    mail_msg['From'] = "cologne.autoblitz@gmail.com"
    mail_msg['To'] = "bestellung@autoblitz-koeln.de"

    # sending the mail

    s.send_message(mail_msg)

    # terminating the session
    s.quit()
    return render_template('kappey.html')


# contact_us backend
@app.route('/contact_us_result', methods=['POST', 'GET'])
def contact_us_result():
    if check_location() == 'Access denied':
        return "Access Denied"
    msg = "############## Kundendaten : ###############" + '\n'
    name = request.form.get('Name')
    phone = request.form.get('Phone')
    mail = request.form.get('Mail')
    subject = request.form.get('Subject')
    body = request.form.get('Message')

    # whole form validation check point
    if name == "" or str(phone) == "" or str(phone).find("+") == -1 or mail == "" or subject == "" or body == "":
        error = "Ihre Bewerbung wurde noch nicht eingereicht. Bitte füllen Sie das Formular korrekt aus und geben \
           Sie eine gültige Telefonnummer (einschließlich Landesvorwahl), E-Mail und Dokumente an."
        flash(error)

    elif ph_country(str(phone)) != "Germany":
        flash("Ihre Anfrage wird nicht übermittelt, da nur deutsche Handynummern akzeptiert werden.")


    else:
        data = "Kundenname =  {name}" + '\n' + "Kunden-Telefonnummer = {phone}" + '\n' + "Kunden-Mail-ID = {mail}" + '\n' + '\n'
        msg1 = "################ Kundenanforderung : ###############" + '\n'
        message = msg + data.format(name=name, phone=phone, mail=mail) + msg1 + body
        # creates SMTP session

        s = smtplib.SMTP('smtp.gmail.com', 587)

        # start TLS for security
        s.starttls()

        # Authentication
        s.login("cologne.autoblitz@gmail.com", "xrqhdhqwzkrwkutc")

        mail_msg = EmailMessage()
        mail_msg.set_content(message)
        mail_msg['Subject'] = subject
        mail_msg['From'] = "cologne.autoblitz@gmail.com"
        mail_msg['To'] = "info@autoblitz-koeln.de"

        # sending the mail

        s.send_message(mail_msg)

        # terminating the session
        s.quit()

    return render_template('contact_us.html')


# map key
valid = []


@app.route('/src', methods=['GET'])
def src():
    if check_location() == 'Access denied':
        return "Access Denied"
    kmap = os.environ.get('map')

    src = "https://maps.googleapis.com/maps/api/js?key=" + kmap + "&libraries=places"

    return redirect(src, code=302)


# publish key #
@app.route('/publish', methods=['POST', 'GET'])
def publish():
    if check_location() == 'Access denied':
        return "Access Denied"
    msg = {"key": os.getenv('t_s_p_k')}
    return jsonify(msg)





@app.route('/create-payment-intent', methods=['POST'])
def create_payment():
    if check_location() == 'Access denied':
        return "Access Denied"
    try:
        customer = stripe.Customer.create()
        json_data = open(file_N[0])
        book = json.load(json_data)
        price = cal_price(str(book["pick"]), str(book["drop"]), str(book["vehicle"]))

        amount = int(price * 100)
        data = json.loads(request.data)
        allowed_payment_methods = ["card", "paypal", "sofort", "giropay", "link"]
        allowed_card_networks = ["visa", "mastercard"]

        intent = stripe.PaymentIntent.create(
            customer=customer['id'],

            amount=amount,
            currency='eur',

            receipt_email=str(book['mail']),
            payment_method_types= allowed_payment_methods,
            payment_method_options={
                "card": {
                    "request_three_d_secure": "automatic"


                }
            },

            description=str(book['name']) + "'s" +" order"

        )


        test = jsonify({
            'clientSecret': intent['client_secret']
        })
        book['pay'] = intent['client_secret']
        with open(file_N[0], 'w') as new_json:
            json.dump(book, new_json)

        return test

    except Exception as e:
        return jsonify(error=str(e)), 403, print(str(e))

@app.route('/online_booking', methods=['POST', 'GET'])
def online_booking():
    data = open(file_N[0])
    book = json.load(data)
    id = book['pay'].split('_secret')[0]
    intent = stripe.PaymentIntent.retrieve(id)



    return render_template('online_booking.html' )

# check out  page
@app.route('/checkout', methods=['POST', 'GET'])
def checkout():
    if check_location() == 'Access denied':
        return "Access Denied"
    try:
        json_data = open(file_N[0])
        book = json.load(json_data)
        if book['name'] == "" or book['phone'] == "" or str(book["phone"]).find('+') == -1 or book["mail"] == "" or \
                book["pick"] == "" or book["drop"] == "" or book["vehicle"] == "" or book["date"] == "" or book[
            "time"] == "":
            error = "Ihre Anfrage wurde noch nicht eingereicht. Bitte füllen Sie das Formular korrekt aus und geben \
                       Sie eine gültige Telefonnummer (einschließlich +49), E-Mail, Alter, Abholort, Zielort, Datum und Zeit."
            flash(error)
            return render_template("taxi.html")
        elif ph_country(str(book["phone"])) != "Germany":
            flash("Ihre Anfrage wird nicht übermittelt, da nur deutsche Handynummern akzeptiert werden.")
            return render_template("taxi.html")

        elif city_filter(str(book["pick"]))["city"] != "Köln" or city_filter(str(book["drop"]))["city"] != "Köln":
            flash("Es tut uns sehr leid.  Wir bedienen den angegebenen Ort nicht.")
            return render_template("taxi.html")
        else:

            price = cal_price(str(book["pick"]), str(book["drop"]), str(book["vehicle"]))
            return render_template('checkout.html', price=price)
    except:
        flash(
            "Es tut uns leid, die Formulardaten wurden nicht an den Server übertragen. Bitte geben Sie daher die Daten noch einmal ein.")
        return render_template("taxi.html")


# runing the application
if __name__ == '__main__':
    app.run()
