//javascript.js
//set map options


var myLatLng = { lat: 50.95788, lng: 6.96728 };
var mapOptions = {
    center: myLatLng,
    zoom: 10,
    mapTypeId: google.maps.MapTypeId.ROADMAP

};

//create map
var map = new google.maps.Map(document.getElementById('googleMap'), mapOptions);



//create a DirectionsService object to use the route method and get a result for our request
var directionsService = new google.maps.DirectionsService();

//create a DirectionsRenderer object which we will use to display the route
var directionsDisplay = new google.maps.DirectionsRenderer();

//bind the DirectionsRenderer to the map
directionsDisplay.setMap(map);


//define calcRoute function

function calcRoute() {
    //create request

    var request = {
        origin: document.getElementById("Pick-up").value,
        destination: document.getElementById("Drop").value,
        travelMode: google.maps.TravelMode.DRIVING, //WALKING, BYCYCLING, TRANSIT
        unitSystem: google.maps.UnitSystem.METRIC
    }

    var home = {
        origin: "Keupstraße 26, 51063 Köln, Germany",
        destination: document.getElementById("Pick-up").value,
        travelMode: google.maps.TravelMode.DRIVING, //WALKING, BYCYCLING, TRANSIT
        unitSystem: google.maps.UnitSystem.METRIC
    }

    var home_dist; // Declare a global variable to store the distance value

    function calculateDistance() {
        return new Promise(function (resolve, reject) {
            directionsService.route(home, function (out, stat) {
                if (stat == google.maps.DirectionsStatus.OK) {
                    home_dist = parseFloat((out.routes[0].legs[0].distance.value) / 1000);
                    resolve(home_dist);
                } else {
                    reject(new Error("Failed to calculate distance"));
                }
            })
        });
    }




    //pass the request to the route method
    directionsService.route(request, function (result, status) {
        if (status == google.maps.DirectionsStatus.OK) {

            //Get distance and time
            const output = document.getElementById('kms');
            output.innerHTML = result.routes[0].legs[0].distance.text;


            var dist = parseFloat((result.routes[0].legs[0].distance.value) / 1000);
            calculateDistance()
                .then(function (distance) {
                    console.log(home_dist); // You can access home_dist here
                    var dur = result.routes[0].legs[0].duration.text;
                    document.getElementById('dur').innerHTML = dur;
                    document.getElementById('book-datetime').innerHTML = document.getElementById('Date').value.toString() + ", " + document.getElementById('Time').value.toString();
                    document.getElementById("name").innerHTML = document.getElementById("Name").value;
                    document.getElementById("phone").innerHTML = document.getElementById("Phone").value;
                    document.getElementById("mail").innerHTML = document.getElementById("Mail").value;
                    document.getElementById("start").innerHTML = document.getElementById("Pick-up").value;
                    document.getElementById("end").innerHTML = document.getElementById("Drop").value;

                    let wait = parseInt(document.getElementById('Time').value.toString())

                    if (wait == 00 || wait < 06) {
                        document.getElementById('wait').style.display = 'block'
                    }
                    else {
                        document.getElementById('wait').style.display = 'none'
                    }

                    document.getElementById("Price").style.display = "block"


                    if (document.getElementById("Vehicle").value == "mini") {
                        document.getElementById("passengers").innerHTML = "bis zu 4 Personen sind erlaubt";
                        document.getElementById("luggage").innerHTML = "bis zu 2 Koffer sind erlaubt";
                        document.getElementById("additional").innerHTML = "0.00";

                        if (dist < 1 && home_dist < 7) {
                            document.getElementById("Hadditional").innerHTML = "0.00"
                            document.getElementById("total").innerHTML = Math.round(4.3 + 0 + 2.20 + 0);
                            document.getElementById('pay').innerHTML = "Bezahlen " + (Math.round(4.3 + 0 + (2.20) + 0)).toString() + " " + "€"


                        }
                        else if (dist < 1 && home_dist > 7) {
                            document.getElementById("Hadditional").innerHTML = "4.30"
                            document.getElementById("total").innerHTML = Math.round(4.3 + 0 + 2.20 + 4.30);
                            document.getElementById('pay').innerHTML = "Bezahlen " + (Math.round(4.3 + 0 + (2.20) + 4.30)).toString() + " " + "€"


                        }
                        else if (dist > 1 && home_dist > 7) {
                            document.getElementById("Hadditional").innerHTML = "4.30"
                            document.getElementById("total").innerHTML = Math.round(4.3 + 0 + (2.20 * dist) + 4.3);
                            document.getElementById('pay').innerHTML = "Bezahlen " + (Math.round(4.3 + 0 + (2.20 * dist) + 4.3)).toString() + " " + "€"


                        }
                        else {
                            document.getElementById("Hadditional").innerHTML = "0.00"
                            document.getElementById("total").innerHTML = Math.round(4.3 + 0 + (2.20 * dist) + 0);
                            document.getElementById('pay').innerHTML = "Bezahlen " + (Math.round(4.3 + 0 + (2.20 * dist) + 0)).toString() + " " + "€"

                        }
                    }
                    else if (document.getElementById("Vehicle").value == "combi") {
                        document.getElementById("passengers").innerHTML = "bis zu 4 Personen sind erlaubt";
                        document.getElementById("luggage").innerHTML = "bis zu 4 Koffer sind erlaubt";
                        document.getElementById("additional").innerHTML = "5.00";
                        if (dist < 1 && home_dist < 7) {
                            document.getElementById("Hadditional").innerHTML = "0.00"
                            document.getElementById("total").innerHTML = Math.round(4.3 + 5 + 2.20 + 0);
                            document.getElementById('pay').innerHTML = "Bezahlen " + (Math.round(4.3 + 5 + 2.20 + 0)).toString() + " " + "€"

                        }
                        else if (dist < 1 && home_dist > 7) {
                            document.getElementById("Hadditional").innerHTML = "4.30"
                            document.getElementById("total").innerHTML = Math.round(4.3 + 5 + 2.20 + 4.3);
                            document.getElementById('pay').innerHTML = "Bezahlen " + (Math.round(4.3 + 5 + 2.20 + 4.3)).toString() + " " + "€"

                        }
                        else if (dist > 1 && home_dist > 7) {
                            document.getElementById("Hadditional").innerHTML = "4.30"
                            document.getElementById("total").innerHTML = Math.round(4.3 + 5 + (2.20 * dist) + 4.3);
                            document.getElementById('pay').innerHTML = "Bezahlen " + (Math.round(4.3 + 5 + (2.20 * dist) + 4.3)).toString() + " " + "€"

                        }
                        else {
                            document.getElementById("Hadditional").innerHTML = "0.00"
                            document.getElementById("total").innerHTML = Math.round(4.3 + 5 + (2.20 * dist) + 0);
                            document.getElementById('pay').innerHTML = "Bezahlen " + (Math.round(4.3 + 5 + (2.20 * dist) + 0)).toString() + " " + "€"

                        }

                    } else if (document.getElementById("Vehicle").value == "wagen") {
                        document.getElementById("passengers").innerHTML = "bis zu 8 Personen sind erlaubt";
                        document.getElementById("luggage").innerHTML = "mehr als 4 Koffer sind erlaubt";
                        document.getElementById("additional").innerHTML = "10.00";
                        if (dist < 1 && home_dist < 7) {
                            document.getElementById("Hadditional").innerHTML = "0.00"
                            document.getElementById("total").innerHTML = Math.round(4.3 + 10 + 2.20 + 0);
                            document.getElementById('pay').innerHTML = "Bezahlen " + (Math.round(4.3 + 10 + 2.20 + 0)).toString() + " " + "€"

                        }
                        else if (dist < 1 && home_dist > 7) {
                            document.getElementById("Hadditional").innerHTML = "4.30"
                            document.getElementById("total").innerHTML = Math.round(4.3 + 10 + 2.20 + 4.30);
                            document.getElementById('pay').innerHTML = "Bezahlen " + (Math.round(4.3 + 10 + 2.20 + 4.30)).toString() + " " + "€"

                        }
                        else if (dist > 1 && home_dist > 7) {
                            document.getElementById("Hadditional").innerHTML = "4.30"
                            document.getElementById("total").innerHTML = Math.round(4.3 + 10 + (2.20 * dist) + 4.30);
                            document.getElementById('pay').innerHTML = "Bezahlen " + (Math.round(4.3 + 10 + (2.20 * dist) + 4.30)).toString() + " " + "€"

                        }
                        else {
                            document.getElementById("Hadditional").innerHTML = "0.00"
                            document.getElementById("total").innerHTML = Math.round(4.3 + 10 + (2.20 * dist));
                            document.getElementById('pay').innerHTML = "Bezahlen " + (Math.round(4.3 + 10 + (2.20 * dist))).toString() + " " + "€"

                        }

                    }
                })
                .catch(function (error) {
                    console.error(error);
                });
            //display route
            directionsDisplay.setDirections(result);
        } else {
            //delete route from map
            directionsDisplay.setDirections({ routes: [] });
            //center map in London
            map.setCenter(myLatLng);

            //show error message
            output.innerHTML = "<div class='alert-danger'><i class='fas fa-exclamation-triangle'></i> Could not retrieve driving distance.</div>";
        }

    });

}

const center = { lat: 50.93803, lng: 6.96039 };
// Create a bounding box with sides ~10km away from the center point
const defaultBounds = {
    north: center.lat + 0.066787,
    south: center.lat - 0.071687,
    east: center.lng + 0.086398,
    west: center.lng - 0.081491,
};

//create autocomplete objects for all inputs
var options = {
    types: ['address'],
    radius: '8120',
    bounds: defaultBounds,
    componentRestrictions: { country: "deu" },

}

var input1 = document.getElementById("Pick-up");
var autocomplete1 = new google.maps.places.Autocomplete(input1, options);

var input2 = document.getElementById("Drop");
var autocomplete2 = new google.maps.places.Autocomplete(input2, options);

var input3 = document.getElementById("PPick-up");
var autocomplete4 = new google.maps.places.Autocomplete(input3, options);

var input4 = document.getElementById("PDrop");
var autocomplete4 = new google.maps.places.Autocomplete(input4, options);