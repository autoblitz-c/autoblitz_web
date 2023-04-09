# resources...
import json
import requests
from datetime import datetime, time, date, timedelta
import time
import flask
from flask import request, render_template, redirect, jsonify, Response, flash, abort
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
from gsheet import add_data, delete_data, query_data

load_dotenv(find_dotenv())
# templates path and app creation

app = flask.Flask(__name__, template_folder="templates/")
app.config["DEBUG"] = False
app.config["UPLOAD_FOLDER"] = "static/"
app.config["Book"] = "static/booking/"
app.secret_key = '123456789@autoblitz'

# booking data storage
file_N = []
counter = 0
order_ids = []


# order creating
def create_order():
    url = "https://agentapitest.seibtundstraub.de/v1/order"
    book = file_N[0]
    #book = json.load(data)
    price = cal_price(str(book["pick"]), str(book["drop"]), str(book["vehicle"]))

    amount = int(price * 100)

    Plat, Plng = lat_long(book['pick'])
    Dlat, Dlng = lat_long(book['drop'])
    p_zip = zip_code(book['pick'])
    d_zip = zip_code(book['drop'])
    p_street = street(book['pick'])
    d_street = street(book['drop'])
    t, valid = validate_time(book['date'], book['time'])
    if t == 0:
        p_time = 0
    else:
        p_time = unix(book['date'], book['time'])
    print(book['vehicle'])
    if book['vehicle'] == "PKW für bis zu 4 Personen und 2 Koffer":
        vehicle_type = "MINI"
        book['vehicle'] = vehicle_type
    elif book['vehicle'] == "Kombi für bis zu 4 Personen und 4 Koffer":
        vehicle_type = "COMBI"
        book['vehicle'] = vehicle_type
    elif book['vehicle'] == "Großraumwagen für bis zu 8 Personen und mehr als 4 Koffer":
        vehicle_type = "VAN"
        book['vehicle'] = vehicle_type


    c_phone = book['phone'][0:3] + " " + book['phone'][3:6] + " " + book['phone'][6:]
    PlatLng = {
        "lat": float(Plat),
        "lng": float(Plng)
    }
    DlatLng = {
        "lat": float(Dlat),
        "lng": float(Dlng)
    }

    Pickup = {
        "name": "",
        "pos": PlatLng,
        "street": p_street,
        "streetNo": "9999",
        "zip": p_zip,
        "city": "cologne",
        "pickupTime": p_time,
    }
    Destination = {
        "name": "",
        "pos": DlatLng,
        "street": d_street,
        "streetNo": "9999",
        "zip": d_zip,
        "city": "cologne"
    }

    Customer = {
        "customerName": book['name'],
        "customerAgentId": book['name'],
        "customerPhone": c_phone,
        "customerEmail": book['mail']
    }
    Billing = {
        "accCustNo": 1,
        'fixedPriceGross': amount,

    }

    OrderRequest = {
        "dispFleetId": 63,
        "productId": "1",

        "pickup": Pickup,
        "dest": Destination,
        "title": "test",
        "customer": Customer,

        "payment": "PAY_INV_BY_AGENT",
        "billingInfo": Billing,
        'dispOptions': [book['vehicle']]
    }

    send = {"cmd": "create_order",
            "data": OrderRequest}
    headers = {'Content-Type': 'application/json',
               'Authentication': 'optipos-apiIdentifier \
               apiIdentifier=79E91C9358EB4A078653EA30A4C73D1F\
                apiSecretKey=4C18CDEE890D43BF8A9AD06FB5C257B8',

               }
    order_json = json.dumps(send, indent=4)
    req = requests.post(url, headers=headers, data=order_json)

    return req.json()

#query order
def query_order(orderguid):
    url = "https://agentapitest.seibtundstraub.de/v1/order"
    send = {"cmd": "query_order",
            "data": {"orderGUID": orderguid}}
    headers = {'Content-Type': 'application/json',
               'Authentication': 'optipos-apiIdentifier \
                      apiIdentifier=79E91C9358EB4A078653EA30A4C73D1F\
                       apiSecretKey=4C18CDEE890D43BF8A9AD06FB5C257B8',

               }
    order_json = json.dumps(send, indent=4)
    req = requests.post(url, headers=headers, data=order_json)

    return req.json()


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


def validate_date(datum: str):
    date_str = datum  # Example date string in ISO format
    date_format = "%Y-%m-%d"  # Format string for ISO date
    today = date.today()
    end_date = today + timedelta(days=6)

    date_obj = datetime.strptime(date_str, date_format).date()
    if today <= date_obj <= end_date:
        return True
    else:
        return False


def validate_time(datum: str, zeit: str):
    date_str = datum  # Example date string in ISO format
    date_format = "%Y-%m-%d"  # Format string for ISO date
    time_str = zeit  # Example time in 24-hour format
    time_format = "%H:%M"  # Format string for 24-hour time
    # Parse date string and time string into date and time objects
    date_obj = datetime.strptime(date_str, date_format).date()
    time_obj = datetime.strptime(time_str, time_format).time()
    # Combine date and time objects into a datetime object
    datetime_obj = datetime.combine(date_obj, time_obj)
    now = datetime.now()
    time_diff = datetime_obj - now
    hours = int(time_diff.total_seconds() / 3600)
    minutes = int(time_diff.total_seconds() / 60)
    if datetime_obj < now:
        pickup_time, valid = -1, False
        return pickup_time, valid
    else:
        if time_diff.days == 0 and hours == 0 and minutes <= 10:
            pickup_time, valid = 0, True
            return pickup_time, valid
        else:
            pickup_time, valid = 1, True
            return pickup_time, valid


g_file = os.path.join(app.config['UPLOAD_FOLDER'], 'GeoLite2-Country.mmdb')
geoip_reader = geoip2.database.Reader(g_file)


# user location access
def check_location():
    try:
        ip_address = request.remote_addr
        country = geoip_reader.country(ip_address).country.iso_code
        print(country)

        if country != 'DEU':
            return 'Access denied'
    except:
        return


# calculating distance of address

def cal_dis(pick: str, drop: str):
    gmaps = googlemaps.Client(key=os.environ.get('pmap'))
    my_dist = gmaps.distance_matrix([pick], [drop], mode="driving")

    return float(my_dist['rows'][0]['elements'][0]['distance']['value'] / 1000)


def cal_price(pick: str, drop: str, vehicle: str):
    dist = cal_dis(pick, drop)
    print(dist)
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
stripe.api_key = os.getenv('t_s_s_k')
stripe.api_key = os.environ.get('t_s_s_k')


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
        msg['From'] = os.environ.get("cg")
        msg['To'] = os.environ.get("ik")
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

        smtp = smtplib.SMTP('smtp.gmail.com', 587)
        # start TLS for security
        smtp.starttls()
        # Authentication
        smtp.login(os.environ.get("cg"), os.environ.get('cgp'))

        smtp.sendmail(os.environ.get("cg"), os.environ.get("ik"), msg.as_string())

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
    #file_name = os.path.join(app.config["Book"], name.split()[0] + phone.split()[0][-5:] + '.json')
    #file_N.append(file_name)
    #with open(file_name, "w") as f:
        #json.dump(book, f)
    file_N.append(book)

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
        msg['From'] = os.environ.get("cg")
        msg['To'] = os.environ.get("bk")

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
        smtp.login(os.environ.get("cg"), os.environ.get("cgp"))

        smtp.sendmail(os.environ.get("cg"), os.environ.get("bk"), msg.as_string())

        smtp.quit()
        os.remove(licence_path)
        if request.files['P-letter'].filename != "":
            os.remove(PB_path)

        message0 = "Vielen Dank für deine Bestellung." + '\n' + '\n' + "Dein Auto wird in kürze auf dem Weg zu dir sein." + '\n' + "Wenn du Fragen hast, kannst du dich gerne unter 0221612277 melden." + '\n' + '\n'
        message1 = "mit freundlichen Grüßen" + '\n' + "Team Autoblitz"

        # creates SMTP session

        s = smtplib.SMTP("smtp.udag.de", port=587)
        s.ehlo()

        # start TLS for security
        s.starttls()
        s.ehlo()

        # Authentication
        s.login(os.environ.get("bk"), os.environ.get("bkp"))

        mail_msg = EmailMessage()

        mail_msg['Subject'] = Header("Bestellbestätigung").encode()
        mail_msg['From'] = os.environ.get("bk")
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
    s.login(os.environ.get("cg"), os.environ.get("cgp"))

    # message to be sent
    end = '\n' + "Danke und Grüße, " + '\n' + 'Cologne-autoblitz'
    message = msg + end

    mail_msg = EmailMessage()
    mail_msg.set_content(message)
    mail_msg['Subject'] = "Kappey"
    mail_msg['From'] = os.environ.get("cg")
    mail_msg['To'] = os.environ.get("bk")

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
        s.login(os.environ.get("cg"), os.environ.get("cgp"))

        mail_msg = EmailMessage()
        mail_msg.set_content(message)
        mail_msg['Subject'] = subject
        mail_msg['From'] = os.environ.get("cg")
        mail_msg['To'] = os.environ.get("ik")

        # sending the mail

        s.send_message(mail_msg)

        # terminating the session
        s.quit()

    return render_template('contact_us.html')


@app.route('/src', methods=['GET'])
def src():
    if check_location() == 'Access denied':
        return "Access Denied"
    kmap = os.environ.get('map')

    src = "https://maps.googleapis.com/maps/api/js?key=" + kmap + "&libraries=places"

    return redirect(src, code=302)


# publish key #
@app.route('/publish', methods=['GET'])
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
        book = file_N[0]
        #book = json.load(json_data)
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
            payment_method_types=allowed_payment_methods,
            payment_method_options={
                "card": {
                    "request_three_d_secure": "automatic"

                }
            },

            description=str(book['name']) + "'s" + " order"

        )

        test = jsonify({
            'clientSecret': intent['client_secret']
        })
        book['pay'] = intent['client_secret'].split('_secret')[0]
        """with open(file_N[0], 'w') as new_json:
            json.dump(book, new_json)"""

        return test

    except Exception as e:
        return jsonify(error=str(e)), 403, print(str(e))


@app.route('/online_booking', methods=['POST', 'GET'])
def online_booking():
    return render_template('online_booking.html')


@app.route('/online_booking_res', methods=['POST', 'GET'])
def online_booking_res():
    return render_template('online_booking_res.html', orderid=order_ids[0]), order_ids.clear()


@app.route('/booking_status', methods=['POST', 'GET'])
def booking_status():
    book = file_N[0]
    #book = json.load(data)

    id = book['pay']
    while True:
        intent = stripe.PaymentIntent.retrieve(id)
        book["amount"] = intent.amount
        book['payment_type'] = stripe.PaymentMethod.retrieve(intent.payment_method).type
        status = intent.status
        order_ids.clear()
        print(status)

        if status == "succeeded":
            while True:
                order = create_order()
                if order['status'] == "OK":
                    break
                time.sleep(5)

            order_ids.append(order['data']['orderNo'])
            book["orderGUID"] = order['data']['orderGUID']
            book["orderNo"] = order['data']['orderNo']
            print(order['status'])
            print(order['data']['orderGUID'])
            add_data('Customer_data', 1, book)
            time.sleep(3)

            response_data = {
                'status': 'succeeded',
                'template': 'online_booking_res',

            }
            #os.remove(file_N[0])
            return jsonify(response_data), file_N.clear()


        else:
            response_data = {
                'status': 'pending',
                'template': 'online_booking'
            }
            return jsonify(response_data)


@app.route('/order_status', methods=['POST', 'GET'])
def order_status():
    return


@app.route('/cancel_booking', methods=['POST', 'GET'])
def cancel_booking():
    return render_template('cancel_booking.html')

@app.route('/cancel', methods=['POST'])
def cancel():
    orderNo = str(request.form['orderNo'])
    query = query_data('Customer_data', 'orderNo', orderNo, 1)
    status = query_order(query['data']['orderGUID'])
    if status['data']['orderState'] == 'O_CONFIRMED' or status['data']['orderState'] == 'O_IN_DISPATCH':
        refund_amount = int(query['amount'])
        amt_cut = "No"
    else:
        refund_amount = int(query['amount']) - 500
        amt_cut = "Yes"
    url = "https://agentapitest.seibtundstraub.de/v1/order"
    send = {"cmd": "cancel_order",
            "data": {"orderGUID": query['orderGUID']}}
    headers = {'Content-Type': 'application/json',
               'Authentication': 'optipos-apiIdentifier \
                      apiIdentifier=79E91C9358EB4A078653EA30A4C73D1F\
                       apiSecretKey=4C18CDEE890D43BF8A9AD06FB5C257B8',

               }
    order_json = json.dumps(send, indent=4)
    req = requests.post(url, headers=headers, data=order_json)
    print(req)
    res = req.json()
    if res['data']['orderState'] == 'O_CANCELED':
        r_res = stripe.Refund.create(payment_intent=query['pay'], amount=refund_amount)
        if r_res['status'] == 'succeeded':
            response = {"orderNo": query['orderNo'], "mail": query['mail'], "amount": r_res['amount'], "amt_cut": amt_cut}
            return jsonify(response)
# check out  page
@app.route('/checkout', methods=['POST', 'GET'])
def checkout():
    if check_location() == 'Access denied':
        return "Access Denied"

    try:
        book = file_N[0]
        #book = json.load(json_data)
        pickup_time_v, valid = validate_time(book["date"], book["time"])
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
        elif validate_date(book["date"]) == False:
            flash("Bitte wählen Sie ein Datum aus dem angegebenen Bereich")
            return render_template("taxi.html")

        elif valid == False:
            flash("Bitte wählen Sie den gegenwärtigen oder zukünftigen Zeitpunkt")
            return render_template("taxi.html")

        elif city_filter(str(book["pick"]))["city"] != "Köln" or city_filter(str(book["drop"]))["city"] != "Köln":
            flash("Es tut uns sehr leid.  Wir bedienen den angegebenen Ort nicht.")
            return render_template("taxi.html")


        else:
            print('hi')

            price = cal_price(str(book["pick"]), str(book["drop"]), str(book["vehicle"]))
            print(price)
            return render_template('checkout.html', price=price)
    except:
        flash(
            "Wir bitten um Entschuldigung, aber die Formulardaten wurden nicht an den Server übertragen. Bitte geben Sie daher die Daten erneut ein.")
        return render_template("taxi.html")

@app.route('/datenschutz', methods=['POST', 'GET'])
def datenschutz():
    return render_template('data_privacy.html')
@app.route('/impressum', methods=['POST', 'GET'])
def impressum():
    return render_template('impressum.html')
# runing the application
if __name__ == '__main__':
    app.run()
