// get location from browser and put it in hidden inputs
(function () {
  var latInput = document.getElementById('id_latitude');
  var lngInput = document.getElementById('id_longitude');
  var status = document.getElementById('locationStatus');
  var form = document.getElementById('addCarForm');
  if (!latInput || !lngInput) return;

  function say(text) {
    if (status) status.lastChild.textContent = text;
  }

  if (!('geolocation' in navigator)) {
    say('Location is not available in this browser. The car will be saved without a map position.');
    return;
  }

  navigator.geolocation.getCurrentPosition(
    function (position) {
      latInput.value = position.coords.latitude;
      lngInput.value = position.coords.longitude;
      say('Your current location will be saved as the car\'s position.');
    },
    function () {
      latInput.value = '';
      lngInput.value = '';
      say('Location not shared. The car will be saved without a map position.');
    },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 }
  );

  if (form) {
    form.addEventListener('submit', function () {
      var button = form.querySelector('button[type="submit"]');
      button.disabled = true;
      button.textContent = 'Uploading...';
    });
  }
})();
