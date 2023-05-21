# resources...
import json
import requests
from datetime import datetime, time, date, timedelta
import time
import flask
from flask import request, render_template, redirect, jsonify, Response, flash, abort, session
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
import uuid
from email.utils import formatdate, formataddr
from email.header import Header
from email import encoders
from werkzeug.utils import secure_filename
from dotenv import load_dotenv, find_dotenv
import os
from functools import wraps
import googlemaps
from gsheet import add_data, delete_data, query_data
from threading import Lock
import pytz
from dateutil import tz

# create a lock for synchronizing access to the Google Sheet
lock = Lock()

#load_dotenv(find_dotenv())
# templates path and app creation

app = flask.Flask(__name__, template_folder="templates/")
app.config["DEBUG"] = False
app.config["UPLOAD_FOLDER"] = "static/"
app.config["Book"] = "static/booking/"
app.secret_key = '123456789@autoblitz'
# Set permanent session lifetime to 10 minutes
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)

#backend api
identifier = os.environ.get('apiIdentifier_prod')
secert = os.environ.get('apiSecretKey_prod')
# stripe key
# stripe.api_key = os.getenv('t_s_s_k')
stripe.api_key = os.environ.get('p_s_s_k')


# order creating
def create_order(pay_type: str):
    url = "https://agentapi.seibtundstraub.de/v1/order"
    user_id = session.get('user_id', None)
    if user_id is None or session.get(f'data_{user_id}') is None:
        flash('Sitzung abgelaufen! Versuchen Sie es erneut.')
        return render_template('taxi.html')

    book = session.get(f'data_{user_id}')
    # book = json.load(data)
    price = cal_price(str(book["pick"]), str(book["drop"]), str(book["vehicle"]))

    amount = int(price * 100)
    book['amount'] = amount
    book['kms'] = cal_dis(str(book["pick"]), str(book["drop"]))
    print(lat_long(book['pick']))

    Plat, Plng = lat_long(book['pick'])
    Dlat, Dlng = lat_long(book['drop'])
    p_street, p_city, p_zip, pstreet_no = geo_cal(book['pick'])
    d_street, d_city, d_zip, dstreet_no = geo_cal(book['drop'])
    t, valid = validate_time(book['date'], book['time'])
    if pay_type == "cash":
        pay = "PAY_CASH"
    else:
        pay = "PAY_INV_BY_AGENT"
    if t == 0:
        p_time = 0
    else:
        p_time = unix(book['date'], book['time'])

    if book['vehicle'] == "mini":
        vehicle_type = "MINI"
        book['vehicle'] = vehicle_type
    elif book['vehicle'] == "combi":
        vehicle_type = "COMBI"
        book['vehicle'] = vehicle_type
    elif book['vehicle'] == "wagen":
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
        "streetNo": str(pstreet_no),
        "zip": p_zip,
        "city": "cologne",
        "pickupTime": p_time,
    }
    Destination = {
        "name": "",
        "pos": DlatLng,
        "street": d_street,
        "streetNo": str(dstreet_no),
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
        "dispFleetId": 388,
        "productId": "1",

        "pickup": Pickup,
        "dest": Destination,
        "title": "Bestellung von " + book['mail'] + " am Datum " + book['date'] + ", " + book['time'],
        "customer": Customer,

        "payment": pay,
        "billingInfo": Billing,
        'dispOptions': [book['vehicle']]
    }

    send = {"cmd": "create_order",
            "data": OrderRequest}
    headers = {'Content-Type': 'application/json',
               'Authentication': f'optipos-apiIdentifier \
               apiIdentifier={identifier}\
                apiSecretKey={secert}',

               }
    order_json = json.dumps(send, indent=4)
    # req = requests.post(url, headers=headers, data=order_json)
    while True:
        try:
            req = requests.post(url, headers=headers, data=order_json)
            req_test = req.json()
            if req_test['status'] == 'OK':
                break
        except requests.exceptions.RequestException:
            time.sleep(10)
    session[f'data_{user_id}'] = book
    print('create_order', session[f'data_{user_id}'])

    return req.json()


# query order
def query_order(orderguid):
    url = "https://agentapi.seibtundstraub.de/v1/order"
    send = {"cmd": "query_order",
            "data": {"orderGUID": orderguid}}
    headers = {'Content-Type': 'application/json',
               'Authentication': f'optipos-apiIdentifier \
                      apiIdentifier={identifier}\
                       apiSecretKey={secert}',

               }
    order_json = json.dumps(send, indent=4)
    req = requests.post(url, headers=headers, data=order_json)

    return req.json()


# lat_long finder
def lat_long(address: str):
    try:
        gmaps = googlemaps.Client(key=os.environ.get('pmap'))
        geocode_result = gmaps.geocode(address)
        location = geocode_result[0]['geometry']['location']
        return location['lat'], location['lng']
    except:
        return 'Ihre Anfrage wird nicht bearbeitet. Bitte geben Sie die gültige Adresse ein oder wählen Sie aus den \
         Dropdowns in den Abholort und Zielort.'


# phone number validation
def ph_country(phone_number: str):
    try:
        ph = parse(phone_number, None)
        country = geocoder.description_for_number(ph, "en")
        return country
    except:
        flash('Ihre Anfrage wird nicht bearbeitet. Bitte geben Sie eine gültige Telefonnummer ein.')


# street, city, zipcode
def geo_cal(address: str):
    geolocator = Nominatim(user_agent="autoblitz_cologne_taxi_web_app")
    lat, lon = lat_long(address)
    location = geolocator.reverse(str(lat) + "," + str(lon))
    loc = location.raw['address']
    street = loc['road']
    city = loc['city']
    zip_code = loc['postcode']
    try:
        street_no = loc['house_number']
    except:
        street_no = "none"
    return street, city, zip_code, street_no


def unix(datum: str, zeit: str):
    date_str = datum  # Example date string in ISO format
    date_format = "%Y-%m-%d"  # Format string for ISO date
    time_str = zeit  # Example time in 24-hour format
    time_format = "%H:%M"  # Format string for 24-hour time
    # Combine the date and time strings into a single string
    date_time_str = date_str + " " + time_str

    # Get the server's local time zone
    server_timezone = tz.gettz()

    # Define the Berlin time zone
    berlin_timezone = pytz.timezone("Europe/Berlin")

    # Convert the string to a datetime object in the server's local time zone
    date_time = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
    date_time_server = date_time.replace(tzinfo=server_timezone)

    # Convert the server's local datetime to the Berlin time zone
    date_time_berlin = date_time_server.astimezone(berlin_timezone)

    # Convert the datetime object to Unix time format
    unix_time = int(date_time_berlin.timestamp())
    return unix_time


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
    home = "Keupstraße 26, 51063 Köln, Germany"
    home_dist = cal_dis(home, pick)

    if vehicle == "mini":
        if dist < 1 and home_dist < 7:
            price = float(4.4 + 0 + 2.20 + 0)
            print("test_price", price)
            return round(price)
        elif dist < 1 and home_dist > 7:
            price = float(4.3 + 0 + 2.20 + 4.30)
            return round(price)
        elif dist > 1 and home_dist > 7:
            price = float(4.3 + 0 + (2.20 * dist) + 4.30)
            return round(price)
        else:
            price = float(4.3 + 0 + (2.20 * dist) + 0)
            return round(price)
    elif vehicle == "combi":
        if dist < 1 and home_dist < 7:
            price = float(4.3 + 5 + 2.20 + 0)
            return round(price)
        elif dist < 1 and home_dist > 7:
            price = float(4.3 + 5 + 2.20 + 4.30)
            return round(price)
        elif dist > 1 and home_dist > 7:
            price = float(4.3 + 5 + (2.20 * dist) + 4.30)
            return round(price)
        else:
            price = float(4.3 + 5 + (2.20 * dist) + 0)
            return round(price)
    elif vehicle == "wagen":
        if dist < 1 and home_dist < 7:
            price = float(4.3 + 10 + 2.20 + 0)
            return round(price)
        elif dist < 1 and home_dist > 7:
            price = float(4.3 + 10 + 2.20 + 4.30)
            return round(price)
        elif dist > 1 and home_dist > 7:
            price = float(4.3 + 10 + (2.20 * dist) + 4.30)
            return round(price)
        else:
            price = float(4.3 + 10 + (2.20 * dist) + 0)
            return round(price)





# creating auth
def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'autoblitz' and password == 'autoblitz@tm2023'


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
    return render_template('home.html')


# about us page
@app.route('/about_us', methods=['POST', 'GET'])
def about_us():
    return render_template('about_us.html')


# booking page
@app.route('/book', methods=['POST', 'GET'])
def book():
    return render_template('book.html')


# vacancy page
@app.route('/vacancy', methods=['POST', 'GET'])
def vacancy():
    # session.permanent = True  # Make the session permanent
    # Generate a unique user ID and store it in the session
    session.clear()
    user_id = str(uuid.uuid4())
    session['user_id'] = user_id
    return render_template('vacancy.html')


# vacancy with sending mail
@app.route('/vacancy_result', methods=['POST', 'GET'])
def vacancy_result():
    user_id = session.get('user_id', None)
    if user_id is None:
        flash('Sitzung abgelaufen! Versuchen Sie es erneut.')
        lock.release()
        return render_template('vacancy.html')
    msg0 = "############## Bewerberdaten : ###############" + '\n'
    name = request.form.get('VName')
    phone = request.form.get('VPhone')

    mail = request.form.get('VMail')

    data = "Bewerbername =  {name}" + '\n' + "Bewerber-Telefonnummer = {phone}" + '\n' + "Bewerber-Mail-ID = {mail}" + '\n' + '\n'

    body = msg0 + data.format(name=name, phone=phone, mail=mail)
    licence = request.files['licence']
    L = licence.filename + str(user_id)
    licence_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(L))

    PB = request.files['P-letter']
    P = PB.filename + str(user_id)
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
        licence.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(L)))
        PB_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(P))

        PB.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(P)))

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
            part.set_payload(open(path.format(name=request.files[f].filename + str(user_id)), "rb").read())
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

    session.pop(f'data_{user_id}', None)

    return render_template('vacancy.html')


# taxi booking page
@app.route('/taxi', methods=['POST', 'GET'])
@requires_auth
def taxi():
    if check_location() == 'Access denied':
        return "Access Denied"

    return render_template('taxi.html')


@app.route('/booking', methods=['POST'])
def booking():
    if check_location() == 'Access denied':
        return "Access Denied"

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
    # file_name = os.path.join(app.config["Book"], name.split()[0] + phone.split()[0][-5:] + '.json')
    # file_N.append(file_name)
    # with open(file_name, "w") as f:
    # json.dump(book, f)
    # Store data in the session
    # session.permanent = True  # Make the session permanent
    # Generate a unique user ID and store it in the session
    session.clear()
    user_id = str(uuid.uuid4())
    session['user_id'] = user_id
    # Store data in the session using the user ID as the key
    session[f'data_{user_id}'] = book
    print('booking', book)
    # file_N.append(book)

    return jsonify({'message': 'Form data received!'})


# ambulance booking page
@app.route('/ambulance', methods=['POST', 'GET'])
def ambulance():
    if check_location() == 'Access denied':
        return "Access Denied"
    # session.permanent = True  # Make the session permanent
    # Generate a unique user ID and store it in the session
    session.clear()
    user_id = str(uuid.uuid4())
    session['user_id'] = user_id
    return render_template('ambulance.html')


@app.route('/ambulance_result', methods=['POST', 'GET'])
def ambulance_result():

    if check_location() == 'Access denied':
        return "Access Denied"
    user_id = session.get('user_id', None)
    if user_id is None or session.get(f'data_{user_id}') is None:
        flash('Sitzung abgelaufen! Versuchen Sie es erneut.')
        return render_template('ambulance.html')
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
    L = licence.filename + str(user_id)
    licence_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(L))

    PB = request.files['P-letter']
    P = PB.filename + str(user_id)

    ############ form validating ###################
    # whole form validation check point
    pstreet, pcity, pzip_code, pstreet_no = geo_cal(str(pick))
    dstreet, dcity, dzip_code, dstreet_no = geo_cal(str(drop))
    if name == "" or str(phone) == "" or str(phone).find("+49") == -1 or str(
            age) == "" or str(date) == "" or str(time) == "" or str(ins) == "" or \
            str(pick) == "" or str(drop) == "" or mail == "" or licence == "":
        error = "Ihre Anfrage wurde noch nicht eingereicht. Bitte füllen Sie das Formular korrekt aus und geben \
           Sie eine gültige Telefonnummer (einschließlich +49), E-Mail, Alter, Abholort, Zielort, Datum, Zeit und Dokumente an."
        flash(error)


    # phone number validation checkpoint
    elif ph_country(str(phone)) != "Germany":
        flash("Ihre Anfrage wird nicht übermittelt, da nur deutsche Handynummern akzeptiert werden.")

    elif pcity != "Köln" or dcity != "Köln":
        flash("Es tut uns sehr leid.  Wir bedienen den angegebenen Ort nicht.")
    elif pstreet_no == "none" or dstreet_no == "none":
        flash("Bitte geben Sie die Hausnummern für die Abholung und Zielort an.")


    else:

        licence.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(L)))
        PB_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(P))
        if request.files['P-letter'].filename != "":
            PB.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(P)))

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
                part.set_payload(open(path.format(name=request.files[f].filename + str(user_id)), "rb").read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment', filename=request.files[f].filename + str(user_id))
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
        message1 = "Mit freundlichen Grüßen" + '\n' + "Team Autoblitz"

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
    session.pop(f'data_{user_id}', None)

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
    # session.permanent = True  # Make the session permanent
    # Generate a unique user ID and store it in the session
    session.clear()
    user_id = str(uuid.uuid4())
    session['user_id'] = user_id
    return render_template('contact_us.html')


# kappey result page
@app.route('/kappey_result', methods=['POST', 'GET'])
def kappey_result():
    msg = "Hallo," + '\n' + '\n'
    date = request.form.getlist('date')
    time = request.form.getlist('time')
    kms = request.form.getlist('kms')
    info = request.form.getlist('info')
    for i in range(0, len(date)):
        data = "Form " + str(i + 1) + '\n' + "Date = " + str(date[i]) + '\n' + "Zeit = " + str(
            time[i]) + '\n' + "KMS = " + str(kms[i]) + '\n' + "info = " + str(info[i]) + '\n' + '\n' + '\n'

        msg = msg + data
    # creates SMTP session

    s = smtplib.SMTP("smtp.udag.de", port=587)

    # start TLS for security
    s.starttls()

    # Authentication
    s.login(os.environ.get('ka'), os.environ.get('kap'))

    # message to be sent
    end = '\n' + "Danke und Grüße, " + '\n' + 'Team Autoblitz'
    message = msg + end

    mail_msg = MIMEMultipart()
    mail_msg.attach(MIMEText(message, 'plain'))
    mail_msg['Subject'] = "Kappey"
    mail_msg['From'] = os.environ.get('ka')
    mail_msg['To'] = ', '.join([os.environ.get('bk'), os.environ.get('iak')])

    # sending the mail

    s.sendmail(os.environ.get('ka'), mail_msg['To'], mail_msg.as_string())

    # terminating the session
    s.quit()

    return render_template('kappey.html')


# contact_us backend
@app.route('/contact_us_result', methods=['POST', 'GET'])
def contact_us_result():

    if check_location() == 'Access denied':
        return "Access Denied"
    user_id = session.get('user_id', None)
    if user_id is None:
        flash('Sitzung abgelaufen! Versuchen Sie es erneut.')

        return render_template('contact_us.html')
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


    session.pop(f'data_{user_id}', None)

    return render_template('contact_us.html')


@app.route('/src', methods=['GET'])
def src():
    kmap = os.environ.get('map')

    src = "https://maps.googleapis.com/maps/api/js?key=" + kmap + "&libraries=places"

    return redirect(src, code=302)


# publish key #
@app.route('/publish', methods=['GET'])
def publish():
    msg = {"key": os.environ.get('p_s_p_k')}
    return jsonify(msg)


@app.route('/create-payment-intent', methods=['POST'])
def create_payment():

    try:

        user_id = session.get('user_id', None)
        if user_id is None or session.get(f'data_{user_id}') is None:
            flash('Sitzung abgelaufen! Versuchen Sie es erneut.')
            return render_template('taxi.html')

        book = session.get(f'data_{user_id}')
        # Create a customer object
        customer = stripe.Customer.create(
            email=book['mail'],
            description=book['name']
        )
        # book = json.load(json_data)
        price = cal_price(str(book["pick"]), str(book["drop"]), str(book["vehicle"]))

        amount = int(price * 100)
        data = json.loads(request.data)
        allowed_payment_methods = ["card", "sofort", "giropay", "link"]
        allowed_card_networks = ["visa", "mastercard"]

        intent = stripe.PaymentIntent.create(
            customer=customer.id,

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
        session[f'data_{user_id}'] = book
        return test

    except Exception as e:
        return jsonify(error=str(e)), 403, print(str(e))


@app.route('/online_booking', methods=['POST', 'GET'])
def online_booking():
    return render_template('online_booking.html')


@app.route('/online_booking_res', methods=['POST', 'GET'])
def online_booking_res():

    user_id = session.get('user_id', None)
    if user_id is None or session.get(f'data_{user_id}') is None:
        return "session is None"

    book = session.get(f'data_{user_id}')

    return render_template('online_booking_res.html', orderid=book['orderNo']), session.pop(f'data_{user_id}', None)


@app.route('/cash_booking_res', methods=['POST', 'GET'])
def cash_booking_res():

    user_id = session.get('user_id', None)
    if user_id is None or session.get(f'data_{user_id}') is None:
        return "session is None"
    book = session.get(f'data_{user_id}')

    return render_template('cash_booking_res.html', orderid=book['orderNo']), session.pop(f'data_{user_id}', None)


@app.route('/cash_booking', methods=['POST', 'GET'])
def cash_booking():
    return render_template('cash_booking.html')


@app.route('/booking_status', methods=['POST', 'GET'])
def booking_status():

    user_id = session.get('user_id', None)
    if user_id is None or session.get(f'data_{user_id}') is None:
        return "session is None"

    book = session.get(f'data_{user_id}')
    print('stripe', book)
    # book = json.load(data)

    id = book['pay']
    counter = 0
    while True:

        try:
            time.sleep(3)
            intent = stripe.PaymentIntent.retrieve(id)
            book["amount"] = intent.amount
            book['payment_type'] = stripe.PaymentMethod.retrieve(intent.payment_method).type
            pay_status = intent.status

            print('payment_status', pay_status)
            if counter == 10 and pay_status != "succeeded":
                try:
                    stripe.Refund.create(payment_intent=id, amount=book['amount'])
                    flash(
                        'Ihre Zahlung war erfolglos. Wenn der Betrag von Ihrem Bankkonto erkannt wird, wird er innerhalb von 7-15 Werktagen auf Ihr Bankkonto zurückerstattet.')
                    return render_template('checkout.html')
                except:
                    flash(
                        'Ihre Zahlung ist fehlgeschlagen. Bitte setzen Sie sich mit unserem Team unter 0221 612277 in Verbindung, um weitere Hilfe zu erhalten.')
                    return render_template('checkout.html')

            counter += 1

            if pay_status == "succeeded":
                print('success')
                order = create_order(book['payment_type'])

                book["orderGUID"] = order['data']['orderGUID']
                book["orderNo"] = order['data']['orderNo']
                print(order['status'])
                print(order['data']['orderGUID'])

                ############ mail for customer #############
                me = os.environ.get("bk")
                you = book['mail']

                # Create message container - the correct MIME type is multipart/alternative.
                msg = MIMEMultipart('alternative')
                msg['Subject'] = "Buchungsbestätigung"
                msg['From'] = me
                msg['To'] = you
                msg['Message-id'] = email.utils.make_msgid()
                msg['Date'] = email.utils.formatdate()

                # Create the body of the message (a plain-text and an HTML version).

                html = '<!DOCTYPE html><html lang="de"><head>\
                                                          </head>\
                                                      <body><p>Hallo {name},</p>\
                                                      <p>Vielen Dank für Ihre Buchung. Hier ist Ihre Bestellnummer: <h8 style="font-weight:bold; font-size:20%; color:rgb(69, 69, 209)"> {orderNO} </h8>. Benutzen Sie diese Nummer, um den Status Ihrer Bestellung zu überprüfen oder um Ihre Bestellung zu stornieren.</p> \
                                                      <p>Unser Fahrer wird Sie anrufen, wenn er am Abholpunkt ist.</p>\
                                                      <a  type="button" href="https://autoblitz-koeln.de/order_status" style="color:white;background-color:green;border-radius:25px">Buchungsstatus überprüfen</a><br><br>\
                                                      <a  type="button" href="https://autoblitz-koeln.de/cancel_booking" style="color:white;background-color:red;border-radius:25px">Buchung stornieren</a><br>\
                                                      <p>Bei weiteren Fragen melden Sie sich gerne unter: 0221 612277</p>\
                                                      <p>Mit freundlichen Grüßen</p>\
                                                      <p>Team Autoblitz</p>\
                                                       </body>\
                                                      </html>'
                html = html.format(name=book['name'], orderNO=book['orderNo'])

                # Record the MIME types of both parts - text/plain and text/html.

                part2 = MIMEText(html, 'html')

                # Attach parts into message container.
                # According to RFC 2046, the last part of a multipart message, in this case
                # the HTML message, is best and preferred.

                msg.attach(part2)

                # Send the message via local SMTP server.
                s = smtplib.SMTP("smtp.udag.de", port=587)
                s.ehlo()

                # start TLS for security
                s.starttls()
                s.ehlo()

                # Authentication
                s.login(os.environ.get("bk"), os.environ.get("bkp"))
                # sendmail function takes 3 arguments: sender's address, recipient's address
                # and message to send - here it is sent as one string.
                s.sendmail(me, you, msg.as_string())
                s.quit()
                if book['payment_type'] == 'link':
                    book['net_amount'] = (int(book['amount']) / 100) - (
                                ((int(book['amount']) / 100) * (1.2 / 100)) + 0.25)
                elif book['payment_type'] == 'card' or book['payment_type'] == 'apple_pay' or book[
                    'payment_type'] == 'google_pay':
                    book['net_amount'] = (int(book['amount']) / 100) - (
                            ((int(book['amount']) / 100) * (2.28 / 100)) + 0.25)
                elif book['payment_type'] == 'giropay' or book['payment_type'] == 'sofort':
                    book['net_amount'] = (int(book['amount']) / 100) - (
                            ((int(book['amount']) / 100) * (1.4 / 100)) + 0.25)

                add_data('Customer_data', 1, book)

                time.sleep(1)
                response_data_s = {
                    'status': 'succeeded',
                    'template': 'online_booking_res',

                }


                return jsonify(response_data_s)



            else:
                response_data = {
                    'status': 'pending',
                    'template': 'online_booking'
                }
                return jsonify(response_data)

        except:
            time.sleep(5)


@app.route('/booking_cash_status', methods=['POST', 'GET'])
def booking_cash_status():

    user_id = session.get('user_id', None)
    if user_id is None or session.get(f'data_{user_id}') is None:

        return 'session is None'

    book = session.get(f'data_{user_id}')
    pickup_time_v, valid = validate_time(book["date"], book["time"])
    pstreet, pcity, pzip_code, pstreet_no = geo_cal(book['pick'])
    dstreet, dcity, dzip_code, dstreet_no= geo_cal(book['drop'])
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
    elif pstreet_no == "none" or dstreet_no == "none":
        flash("Bitte geben Sie die Hausnummern für die Abholung und Zielort an.")
        return render_template("taxi.html")
    elif validate_date(book["date"]) == False:
        flash("Bitte wählen Sie ein Datum aus dem angegebenen Bereich")

        return render_template("taxi.html")

    elif valid == False:
        flash("Bitte wählen Sie den gegenwärtigen oder zukünftigen Zeitpunkt")

        return render_template("taxi.html")

    elif pcity != "Köln" or dcity != "Köln":
        flash("Es tut uns sehr leid.  Wir bedienen den angegebenen Ort nicht.")

        return render_template("taxi.html")

    else:
        book['pay'] = "NA"
        book['payment_type'] = "cash"
        print("cash", book)
        order = create_order(book['payment_type'])
        print('order details', order)

        book["orderGUID"] = order['data']['orderGUID']
        book["orderNo"] = order['data']['orderNo']
        print(order['status'])
        print(order['data']['orderGUID'])


        if order['status'] == "OK":
            response_data = {
                'status': 'succeeded',
                'template': 'cash_booking_res',

            }
            ############ mail for customer #############
            me = os.environ.get("bk")
            you = book['mail']

            # Create message container - the correct MIME type is multipart/alternative.
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "Buchungsbestätigung"
            msg['From'] = me
            msg['To'] = you
            msg['Message-id'] = email.utils.make_msgid()
            msg['Date'] = email.utils.formatdate()

            # Create the body of the message (a plain-text and an HTML version).

            html = '<!DOCTYPE html><html lang="de"><head>\
                                            </head>\
                                        <body><p>Hello {name},</p>\
                                        <p>Vielen Dank für Ihre Buchung. Hier ist Ihre Bestellnummer: <h8 style="font-weight:bold; font-size:20%; color:rgb(69, 69, 209)"> {orderNO} </h8>. Benutzen Sie diese Nummer, um den Status Ihrer Bestellung zu überprüfen oder um Ihre Bestellung zu stornieren.</p> \
                                        <p>Unser Fahrer wird Sie anrufen, wenn er am Abholpunkt ist.</p>\
                                        <a  type="button" href="https://autoblitz-koeln.de/order_status" style="color:white;background-color:green;border-radius:25px">Buchungsstatus überprüfen</a><br><br>\
                                        <a  type="button" href="https://autoblitz-koeln.de/cancel_booking" style="color:white;background-color:red;border-radius:25px">Buchung stornieren</a><br>\
                                        <p>Bei weiteren Fragen melden Sie sich gerne unter: 0221 612277</p>\
                                        <p>Mit freundlichen Grüßen</p>\
                                        <p>Team Autoblitz</p>\
                                         </body>\
                                        </html>'
            html = html.format(name=book['name'], orderNO=book['orderNo'])

            # Record the MIME types of both parts - text/plain and text/html.

            part2 = MIMEText(html, 'html')

            # Attach parts into message container.
            # According to RFC 2046, the last part of a multipart message, in this case
            # the HTML message, is best and preferred.

            msg.attach(part2)

            # Send the message via local SMTP server.
            s = smtplib.SMTP("smtp.udag.de", port=587)
            s.ehlo()

            # start TLS for security
            s.starttls()
            s.ehlo()

            # Authentication
            s.login(os.environ.get("bk"), os.environ.get("bkp"))
            # sendmail function takes 3 arguments: sender's address, recipient's address
            # and message to send - here it is sent as one string.
            s.sendmail(me, you, msg.as_string())
            s.quit()

            time.sleep(1)
            book['net_amount'] = int(book['amount']) / 100
            add_data('Customer_data', 1, book)
            print('added data', book)


            return jsonify(response_data)

        else:
            response_data = {
                'status': 'pending',
                'template': 'cash_booking'
            }
            return jsonify(response_data)


@app.route('/order_status', methods=['POST', 'GET'])
def order_status():
    # session.permanent = True  # Make the session permanent
    # Generate a unique user ID and store it in the session
    session.clear()
    user_id = str(uuid.uuid4())
    session['user_id'] = user_id
    return render_template('order_status.html')


@app.route('/order', methods=['POST'])
def order():

    orderNo = request.json.get('order')
    user_id = session.get('user_id', None)
    if user_id is None:
        flash('Sitzung abgelaufen! Versuchen Sie es erneut.')
        lock.release()
        return render_template('order_status.html')

    try:
        query = query_data('Customer_data', 'orderNo', orderNo, 1)
    except:
        response_data = {
            'status': 'error',
            'message': 'Es liegt ein technischer Fehler vor, bitte versuchen Sie es nach einer Minute erneut.'
        }
        session.pop(f'data_{user_id}', None)
        return jsonify(response_data)
    if query == 0:
        response_data = {
            'status': 'error',
            'message': 'Die angegebene Bestellnummer ist falsch, bitte geben Sie die richtige Bestellnummer an.'
        }
        session.pop(f'data_{user_id}', None)
        return jsonify(response_data)

    while True:
        try:
            q_order = query_order(query['orderGUID'])
            if q_order['status'] == "OK":
                break
        except:
            time.sleep(10)

    if q_order['data']['orderState'] == 'O_CANCELED':
        response_data = {
            'status': 'pending',
            'message': 'Diese Bestellung wurde storniert.'
        }
        session.pop(f'data_{user_id}', None)
        return jsonify(response_data)
    elif q_order['data']['orderState'] == 'O_CONFIRMED' or q_order['data']['orderState'] == 'O_IN_DISPATCH':
        response_data = {
            'status': 'pending',
            'message': 'Bestellung bestätigt, Suche nach einem Fahrzeug.'
        }
        session.pop(f'data_{user_id}', None)
        return jsonify(response_data)
    elif q_order['data']['orderState'] == 'O_IN_APPROACH' or q_order['data']['orderState'] == 'O_RENDEZVOUS':
        response_data = {
            'status': 'succeeded',
            'message': 'Das Fahrzeug ist auf dem Weg zu einem Abholer.',
            "drvName": q_order['data']['transport']['driver']['drvName'],
            "drvPhone": q_order['data']['transport']['driver']['drvPhone'],
            "vehModel": q_order['data']['transport']['vehicle']['vehModel']
        }
        session.pop(f'data_{user_id}', None)
        return jsonify(response_data)
    elif q_order['data']['orderState'] == 'O_IN_TRANSPORT' or q_order['data']['orderState'] == 'O_DEST_REACHED' or \
            q_order['data']['orderState'] == 'O_TRANSPORT_COMPLETE' or q_order['data']['orderState'] == 'O_SETTLED' or \
            q_order['data']['orderState'] == 'O_COMPLETE':
        response_data = {
            'status': 'pending',
            'message': 'Dieser Auftrag ist entweder abgeschlossen oder auf dem Transportweg.'
        }
        session.pop(f'data_{user_id}', None)
        return jsonify(response_data)


@app.route('/cancel_booking', methods=['POST', 'GET'])
def cancel_booking():
    # session.permanent = True  # Make the session permanent
    # Generate a unique user ID and store it in the session
    session.clear()
    user_id = str(uuid.uuid4())
    session['user_id'] = user_id

    return render_template('cancel_booking.html')


@app.route('/cancel', methods=['POST'])
def cancel():
    orderNo = request.json.get('order')
    reason = str(request.json.get('reason'))
    user_id = session.get('user_id', None)
    if user_id is None:
        flash('Sitzung abgelaufen! Versuchen Sie es erneut.')
        response_data = {
            'status': 'error',
            'message': 'Sitzung abgelaufen! Versuchen Sie es erneut.'
        }
        session.pop(f'data_{user_id}', None)

        return jsonify(response_data)

    print(orderNo)
    print(reason)
    while True:
        try:
            query = query_data('Customer_data', 'orderNo', orderNo, 1)
            print(query)

            if query != 0 or query == 0:
                break
        except:
            time.sleep(40)
    if query == 0:
        response_data = {
            'status': 'error',
            'message': 'Die angegebene Bestellnummer ist falsch, bitte geben Sie die richtige Bestellnummer an.'
        }
        session.pop(f'data_{user_id}', None)

        return jsonify(response_data)

    while True:
        try:
            status = query_order(query['orderGUID'])
            if status['status'] == "OK":
                break
        except:
            time.sleep(10)

    if status['data']['orderState'] == 'O_CANCELED':

        response_data = {
            'status': 'error',
            'message': "Diese Bestellung wurde bereits zurückerstattet."
        }
        session.pop(f'data_{user_id}', None)

        return jsonify(response_data)
    elif status['data']['orderState'] == 'O_IN_TRANSPORT' or status['data']['orderState'] == 'O_DEST_REACHED' or \
            status['data']['orderState'] == 'O_TRANSPORT_COMPLETE' or status['data']['orderState'] == 'O_SETTLED' or \
            status['data']['orderState'] == 'O_COMPLETE':
        response_data = {
            'status': 'error',
            'message': 'Dieser Auftrag ist entweder abgeschlossen oder auf dem Transportweg. Daher ist eine Stornierung nicht möglich.'
        }
        session.pop(f'data_{user_id}', None)

        return jsonify(response_data)
    if status['data']['orderState'] == 'O_CONFIRMED' or status['data']['orderState'] == 'O_IN_DISPATCH':

        refund_amount = {"refund": int(query['amount'])}

        # Store data in the session using the user ID as the key
        session[f'data_{user_id}'] = refund_amount




    elif status['data']['orderState'] == 'O_IN_APPROACH' or status['data']['orderState'] == 'O_RENDEZVOUS':

        refund_amount = {"refund": int(query['amount']) - 500}

        # Store data in the session using the user ID as the key
        session[f'data_{user_id}'] = refund_amount

    url = "https://agentapi.seibtundstraub.de/v1/order"

    send = {"cmd": "cancel_order",
            "data": {"orderGUID": query['orderGUID']}}
    headers = {'Content-Type': 'application/json',
               'Authentication': f'optipos-apiIdentifier \
                                  apiIdentifier={identifier}\
                                   apiSecretKey={secert}',

               }
    order_json = json.dumps(send, indent=4)
    while True:
        try:
            req = requests.post(url, headers=headers, data=order_json)
            res = req.json()
            if res['status'] == "OK":
                break
        except:
            time.sleep(30)

    if res['data']['orderState'] == 'O_CANCELED':

        if query['payment_type'] == 'cash':
            print('cash')

            ############ mail for customer #############
            me = os.environ.get("bk")
            you = query['mail']

            # Create message container - the correct MIME type is multipart/alternative.
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "Stornierungsbestätigung"
            msg['From'] = me
            msg['To'] = you
            msg['Message-id'] = email.utils.make_msgid()
            msg['Date'] = email.utils.formatdate()

            # Create the body of the message (a plain-text and an HTML version).

            html = '<!DOCTYPE html>\
                                                        <html lang="de">\
                                                        <head></head>\
                                                        <body><p>Hallo {name},</p>\
                                                        <p>Ihre Buchung mit der Bestellnummer:  <h8 style="font-weight:bold; color:rgb(69, 69, 209)">{orderNO}</h8> wurde erfolgreich storniert.</p>\
                                                        <p>Bei weiteren Fragen melden Sie sich gerne unter: 0221 612277</p>\
                                                        <p>Mit freundlichen Grüßen</p>\
                                                        <p>Team Autoblitz</p>\
                                                        </body>\
                                                       </html>'

            html = html.format(name=query['name'], orderNO=query['orderNo'],
                               )

            # Record the MIME types of both parts - text/plain and text/html.

            part2 = MIMEText(html, 'html')

            # Attach parts into message container.

            msg.attach(part2)

            # Send the message via local SMTP server.
            s = smtplib.SMTP("smtp.udag.de", port=587)
            s.ehlo()

            # start TLS for security
            s.starttls()
            s.ehlo()

            # Authentication
            s.login(os.environ.get("bk"), os.environ.get("bkp"))
            # sendmail function takes 3 arguments: sender's address, recipient's address
            # and message to send - here it is sent as one string.
            s.sendmail(me, you, msg.as_string())
            s.quit()
            cancel_msg = "Ihre Bestellung Nummer {orderNoGet} wurde erfolgreich storniert. Bitte überprüfen Sie Ihre E-Mail {Email} für weitere Informationen.\nWir freuen uns darauf, Sie wieder zu bedienen, Danke."
            cancel_msg = cancel_msg.format(orderNoGet=query['orderNo'], Email=query['mail'])
            now = datetime.now()

            datum = str(now.date())
            zeit = str(now.time())
            response_cash = {"orderNo": query['orderNo'], "mail": query['mail'], "payment_type": "cash",
                             "amount": float(int(query['amount']) / 100),
                             "refund_amount": "0", "reason": reason, "date": datum, "time": zeit}
            add_data("Customer_data", 2, response_cash)

            response_data = {
                'status': 'succeeded',
                'message': cancel_msg
            }
            session.pop(f'data_{user_id}', None)

            return jsonify(response_data)


        else:
            try:
                print('stripe')
                print(query['pay'])
                refund = session.get(f'data_{user_id}')
                r_res = stripe.Refund.create(payment_intent=query['pay'], amount=refund['refund'])
                print('stripe_success')

                ############ mail for customer #############
                me = "bestellung@autoblitz-koeln.de"
                you = query['mail']

                # Create message container - the correct MIME type is multipart/alternative.
                msg = MIMEMultipart('alternative')
                msg['Subject'] = "Stornierungsbestätigung"
                msg['From'] = me
                msg['To'] = you
                msg['Message-id'] = email.utils.make_msgid()
                msg['Date'] = email.utils.formatdate()

                # Create the body of the message (a plain-text and an HTML version).

                html = '<!DOCTYPE html>\
                                                <html lang="de">\
                                                <head></head>\
                                                <body><p>Hallo {name},</p>\
                                                <p>Ihre Buchung mit der Bestellnummer:  <h8 style="font-weight:bold; color:rgb(69, 69, 209)">{orderNO}</h8> wurde erfolgreich storniert. {refund_amount} € wurde für eine Rückerstattung auf die von Ihnen bei der Buchung gewählte Zahlungsart eingeleitet. Es dauert je nach Bank zwischen 7-15 Werktage, bis der Betrag auf Ihrem Konto eingeht.</p>\
                                                <p>Bei weiteren Fragen melden Sie sich gerne unter: 0221 612277</p>\
                                                <p>Mit freundlichen Grüßen</p>\
                                                <p>Team Autoblitz</p>\
                                                </body>\
                                               </html>'

                html = html.format(name=query['name'], orderNO=query['orderNo'],
                                   refund_amount=int(r_res['amount']) / 100)

                # Record the MIME types of both parts - text/plain and text/html.

                part2 = MIMEText(html, 'html')

                # Attach parts into message container.
                # According to RFC 2046, the last part of a multipart message, in this case
                # the HTML message, is best and preferred.

                msg.attach(part2)

                # Send the message via local SMTP server.
                s = smtplib.SMTP("smtp.udag.de", port=587)
                s.ehlo()

                # start TLS for security
                s.starttls()
                s.ehlo()

                # Authentication
                s.login(me, 'tiam2002')
                # sendmail function takes 3 arguments: sender's address, recipient's address
                # and message to send - here it is sent as one string.
                s.sendmail(me, you, msg.as_string())
                s.quit()
                cancel_msg = "Ihre Bestellung Nummer {orderNoGet} wurde erfolgreich storniert. Bitte überprüfen Sie Ihre E-Mail {Email} für weitere Informationen. Je nach Ihrer Bank wird der Betrag innerhalb von 7-15 Tagen auf Ihr Konto zurückerstattet.\nWir freuen uns darauf, Sie wieder zu bedienen, Danke."
                cancel_msg = cancel_msg.format(orderNoGet=query['orderNo'], Email=query['mail'])
                response_data = {
                    'status': 'succeeded',
                    'message': cancel_msg
                }
                now = datetime.now()

                datum = str(now.date())
                zeit = str(now.time())

                response = {"orderNo": query['orderNo'], "mail": query['mail'], "payment_type": query['payment_type'],
                            "amount": float(int(query['amount']) / 100),
                            "refund_amount": float(int(r_res['amount']) / 100), "reason": reason, "date": datum,
                            "time": zeit}
                add_data("Customer_data", 2, response)

                session.pop(f'data_{user_id}', None)


                return jsonify(response_data)



            except:
                print('error')

                response_data = {
                    'status': 'error',
                    'message': "Diese Bestellung wurde bereits zurückerstattet."
                }

                return jsonify(response_data)


# check out  page
@app.route('/checkout', methods=['POST', 'GET'])
def checkout():


    try:
        user_id = session.get('user_id', None)
        if user_id is None or session.get(f'data_{user_id}') is None:
            flash('Sitzung abgelaufen! Versuchen Sie es erneut.')
            return render_template('taxi.html')
        book = session.get(f'data_{user_id}')
        print(book)
        # book = json.load(json_data)
        pickup_time_v, valid = validate_time(book["date"], book["time"])
        pstreet, pcity, pzip_code, pstreet_no = geo_cal(book['pick'])
        dstreet, dcity, dzip_code, dstreet_no = geo_cal(book['drop'])
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
        elif pstreet_no == "none" or dstreet_no == "none":
            flash("Bitte geben Sie die Hausnummern für die Abholung und Zielort an.")
            return render_template("taxi.html")
        elif validate_date(book["date"]) == False:
            flash("Bitte wählen Sie ein Datum aus dem angegebenen Bereich")
            return render_template("taxi.html")

        elif valid == False:
            flash("Bitte wählen Sie den gegenwärtigen oder zukünftigen Zeitpunkt")
            return render_template("taxi.html")

        elif pcity != "Köln" or dcity != "Köln":
            flash("Es tut uns sehr leid.  Wir bedienen den angegebenen Ort nicht.")
            return render_template("taxi.html")


        else:

            price = cal_price(str(book["pick"]), str(book["drop"]), str(book["vehicle"]))
            session[f'data_{user_id}'] = book
            print('price', price)

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


@app.route('/dashboard', methods=['POST', 'GET'])
@requires_auth
def dashboard():
    return render_template('dashboard.html')


@app.route('/gdash', methods=['POST', 'GET'])
@requires_auth
def gdash():
    return render_template('Gdash.html')


@app.context_processor
def inject_template_scope():
    injections = dict()

    def cookies_check():
        value = request.cookies.get('cookie_consent')
        return value == 'true'

    injections.update(cookies_check=cookies_check)

    return injections


# runing the application
if __name__ == '__main__':
    app.run()
