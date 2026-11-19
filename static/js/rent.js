// total price = days * price
(function () {
  var form = document.getElementById('rentForm');
  if (!form) return;

  var price = parseInt(form.dataset.price, 10) || 0;
  var start = document.getElementById('start_date');
  var end = document.getElementById('end_date');
  var daysCount = document.getElementById('daysCount');
  var total = document.getElementById('totalPrice');

  function update() {
    var days = 0;
    if (start.value && end.value) {
      // difference in days, first and last day are both counted
      days = Math.round((new Date(end.value) - new Date(start.value)) / 86400000) + 1;
      if (days < 0) days = 0;
    }
    daysCount.textContent = days;
    total.textContent = days * price;
  }

  // "To" date can not be before "From" date
  start.addEventListener('change', function () {
    end.min = start.value;
    if (end.value && end.value < start.value) end.value = start.value;
    update();
  });
  end.addEventListener('change', update);
  update();

  // disable button after click
  form.addEventListener('submit', function () {
    form.querySelector('button[type="submit"]').disabled = true;
  });
})();
