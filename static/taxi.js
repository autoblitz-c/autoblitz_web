//javascript.js
//set map options
var myLatLng = { lat: 50.9375, lng: 6.9603 };
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

    //pass the request to the route method
    directionsService.route(request, function (result, status) {
        if (status == google.maps.DirectionsStatus.OK) {

            //Get distance and time
            const output = document.getElementById('kms');
            output.innerHTML = result.routes[0].legs[0].distance.text;
             if(result.routes[0].legs[0].distance.text.includes(',')){
                var dist = parseFloat(result.routes[0].legs[0].distance.text.split(",")[0] + result.routes[0].legs[0].distance.text.split(",")[1].split()[0])
            }
            else{
                var dist = parseFloat(result.routes[0].legs[0].distance.text.split("")[0]);

            }

            var dist = parseFloat(result.routes[0].legs[0].distance.text.split()[0]);
            var dur = result.routes[0].legs[0].duration.text;
            document.getElementById('dur').innerHTML = dur;
            document.getElementById('book-datetime').innerHTML = document.getElementById('Date').value.toString() + ", " + document.getElementById('Time').value.toString() ;

            if (document.getElementById("Vehicle").value == "PKW für bis zu 4 Personen und 2 Koffer") {

                if (dist < 1) {
                    document.getElementById("total").innerHTML = 4.3 + 0 + 2.20;
                    document.getElementById('pay').innerHTML = "Bezahlen " + (4.3 + 0 + (2.20 )).toString() + " " + "<i style='color:white'class='fa fa-eur ' aria-hidden='true'></i>"

                }
                else {
                    document.getElementById("total").innerHTML = 4.3 + 0 + (2.20 * dist);
                    document.getElementById('pay').innerHTML = "Bezahlen " + (4.3 + 0 + (2.20 * dist)).toString() + " " + "<i style='color:white'class='fa fa-eur ' aria-hidden='true'></i>"

                }
            }
            else if (document.getElementById("Vehicle").value == "Kombi für bis zu 4 Personen und 4 Koffer") {
                if (dist < 1) {
                    document.getElementById("total").innerHTML = 4.3 + 5 + 2.20;
                    document.getElementById('pay').innerHTML = "Bezahlen " + (4.3 + 5 + 2.20 ).toString() + " " + "<i style='color:white'class='fa fa-eur ' aria-hidden='true'></i>"

                }
                else {
                    document.getElementById("total").innerHTML = parseFloat(4.3 + 5 + (2.20 * dist));
                    document.getElementById('pay').innerHTML = "Bezahlen " + (4.3 + 5 + (2.20 * dist)).toString() + " " + "<i style='color:white'class='fa fa-eur ' aria-hidden='true'></i>" 

                }

            } else {
                if (dist < 1) {
                    document.getElementById("total").innerHTML = 4.3 + 10 + 2.20;
                    document.getElementById('pay').innerHTML = "Bezahlen " + (4.3 + 10 + (2.20 )).toString() + " " + "<i style='color:white'class='fa fa-eur ' aria-hidden='true'></i>"

                }
                else {
                    document.getElementById("total").innerHTML = 4.3 + 10 + (2.20 * dist);
                    document.getElementById('pay').innerHTML = "Bezahlen " + (4.3 + 10 + (2.20 * dist)).toString() + " " + "<i style='color:white'class='fa fa-eur ' aria-hidden='true'></i>"

                }

            }





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

//create autocomplete objects for all inputs
var options = {
    types: ['address']
}

var input1 = document.getElementById("Pick-up");
var autocomplete1 = new google.maps.places.Autocomplete(input1, options);

var input2 = document.getElementById("Drop");
var autocomplete2 = new google.maps.places.Autocomplete(input2, options);

