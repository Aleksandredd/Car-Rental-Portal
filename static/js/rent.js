// Car page: show "days x daily price" while the user picks the number of days.
(function () {
  var form = document.getElementById('rentForm');
  if (!form) return;

  var price = parseFloat(form.dataset.price) || 0;
  var days = document.getElementById('days');
  var total = document.getElementById('totalPrice');

  function update() {
    var value = (parseInt(days.value, 10) || 1) * price;
    // Up to 2 decimals, without trailing zeros (120, 82.5, 99.99)
    total.textContent = String(Math.round(value * 100) / 100);
  }

  days.addEventListener('change', update);
  update();

  // Avoid renting twice with a double click.
  form.addEventListener('submit', function () {
    form.querySelector('button[type="submit"]').disabled = true;
  });
})();
