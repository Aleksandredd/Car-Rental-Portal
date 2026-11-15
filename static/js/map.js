// mapbox map with car marker
(function () {
  var el = document.getElementById('map');
  if (!el || typeof mapboxgl === 'undefined') return;

  var lat = parseFloat(el.dataset.lat);
  var lng = parseFloat(el.dataset.lng);
  if (isNaN(lat) || isNaN(lng)) return;

  mapboxgl.accessToken = el.dataset.token;
  var map = new mapboxgl.Map({
    container: el,
    style: 'mapbox://styles/mapbox/streets-v12',
    center: [lng, lat],
    zoom: 12
  });
  map.addControl(new mapboxgl.NavigationControl(), 'top-right');
  new mapboxgl.Marker({ color: '#e8590c' }).setLngLat([lng, lat]).addTo(map);
})();
