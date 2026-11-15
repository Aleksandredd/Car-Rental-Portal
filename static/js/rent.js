// total price = days * price
(function () {
  var form = document.getElementById('rentForm');
  if (!form) return;

  var price = parseFloat(form.dataset.price) || 0;
  var days = document.getElementById('days');
  var total = document.getElementById('totalPrice');

  function update() {
    var value = (parseInt(days.value, 10) || 1) * price;
    total.textContent = String(Math.round(value * 100) / 100);
  }

  days.addEventListener('change', update);
  update();

  // disable button after click
  form.addEventListener('submit', function () {
    form.querySelector('button[type="submit"]').disabled = true;
  });
})();
