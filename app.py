# resources...
import json
import flask
from flask import request, render_template, redirect, jsonify, Response
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
# from dotenv import load_dotenv, find_dotenv
import os
from functools import wraps

# load_dotenv(find_dotenv())
# templates path and app creation

app = flask.Flask(__name__, template_folder="templates/")
app.config["DEBUG"] = False
app.config["UPLOAD_FOLDER"] = "static/"

# stripe key
#stripe.api_key = os.environ.get('t_s_s_k')


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
    return render_template('vacancy.html')


# vacancy with sending mail
@app.route('/vacancy_result', methods=['POST', 'GET'])
def vacancy_result():
    msg0 = "############## Bewerberdaten : ###############" + '\n'
    name = request.form.get('VName')
    phone = request.form.get('VPhone')

    mail = request.form.get('VMail')

    data = "Bewerbername =  {name}" + '\n' + "Bewerber-Telefonnummer = {phone}" + '\n' + "Bewerber-Mail-ID = {mail}" + '\n' + '\n'

    body = msg0 + data.format(name=name, phone=phone, mail=mail)
    licence = request.files['licence']
    licence_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(licence.filename))
    licence.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(licence.filename)))

    PB = request.files['P-letter']
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

    smtp = smtplib.SMTP('smtp.gmail.com', 587)
    # start TLS for security
    smtp.starttls()

    # Authentication
    smtp.login("cologne.autoblitz@gmail.com", os.environ.get('c'))

    smtp.sendmail("cologne.autoblitz@gmail.com", "info@autoblitz-koeln.de", msg.as_string())

    smtp.quit()
    os.remove(licence_path)

    os.remove(PB_path)

    return render_template('vacancy.html')


# taxi booking page
@app.route('/taxi', methods=['POST', 'GET'])
def taxi():
    return render_template('taxi.html')


# ambulance booking page
@app.route('/ambulance', methods=['POST', 'GET'])
def ambulance():
    return render_template('ambulance.html')


@app.route('/ambulance_result', methods=['POST', 'GET'])
def ambulance_result():
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
    licence.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(licence.filename)))

    PB = request.files['P-letter']

    PB_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(PB.filename))
    if request.files['P-letter'].filename != "":
        PB.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(PB.filename)))

    msg = MIMEMultipart()
    msg['From'] = "cologne.autoblitz@gmail.com"
    msg['To'] = 'bestellung@autoblitz-koeln.de'

    msg['Subject'] = "Neuer Auftrag für Krankentransport"
    msg.attach(MIMEText(body, 'plain'))

    for f in request.files:
        print("print", f)
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
    smtp.login("cologne.autoblitz@gmail.com", os.environ.get('c'))

    smtp.sendmail("cologne.autoblitz@gmail.com", "bestellung@autoblitz-koeln.de", msg.as_string())

    smtp.quit()
    os.remove(licence_path)
    if request.files['P-letter'].filename != "":
        os.remove(PB_path)

    ########## customer mail  ######

    message0 = "Vielen Dank für deine Bestellung." + '\n' + '\n' + "Dein Auto wird in kürze auf dem Weg zu dir sein." + '\n' + "Wenn du Fragen hast, kannst du dich gerne unter 0221612277 melden." + '\n' + '\n'
    message1 = "mit freundlichen Grüßen" + '\n' + "Team Autoblitz"

    # creates SMTP session

    s = smtplib.SMTP("smtp.udag.de", port=587)
    s.ehlo()

    # start TLS for security
    s.starttls()
    s.ehlo()

    # Authentication
    s.login("bestellung@autoblitz-koeln.de", os.environ.get('b'))

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
@requires_auth
def kappey():
    return render_template('kappey.html')


# contact_us page
@app.route('/contact_us', methods=['POST', 'GET'])
def contact_us():
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
    msg = "############## Kundendaten : ###############" + '\n'
    name = request.form.get('Name')
    phone = request.form.get('Phone')
    mail = request.form.get('Mail')
    subject = request.form.get('Subject')
    body = request.form.get('Message')

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
@app.route('/src', methods=['POST', 'GET'])
def src():
    kmap = os.environ.get('map')

    src = "https://maps.googleapis.com/maps/api/js?key=" + kmap + "&libraries=places"

    return redirect(src, code=302)


# publish key # Todo: change publish key in checkout.js
@app.route('/publish', methods=['POST', 'GET'])
def publish():
    return


#customer = stripe.Customer.create()


@app.route('/create-payment-intent', methods=['POST'])
def create_payment():
    try:
        data = json.loads(request.data)
        intent = stripe.PaymentIntent.create(
            #customer=customer['id'],

            amount=600,
            currency='eur',
            receipt_email="tausallu.md007@gmail.com",
            payment_method_types=[

                "card",

                "giropay",

                "sofort",
                "link"

            ],

        )

        return jsonify({
            'clientSecret': intent['client_secret']
        })

    except Exception as e:
        return jsonify(error=str(e)), 403


# about us page
@app.route('/checkout', methods=['POST', 'GET'])
def checkout():
    return render_template('checkout.html')


# runing the application
if __name__ == '__main__':
    app.run()
