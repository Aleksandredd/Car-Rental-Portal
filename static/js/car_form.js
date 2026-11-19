// show only models of the chosen brand
(function () {
  var brands = JSON.parse(document.getElementById('car-brands').textContent);
  var brandSelect = document.getElementById('id_brand');
  var modelSelect = document.getElementById('id_model');
  var selected = modelSelect.value;

  function fillModels() {
    var models = brands[brandSelect.value] || [];
    modelSelect.innerHTML = '';

    var first = document.createElement('option');
    first.value = '';
    first.textContent = models.length ? 'Choose...' : 'Choose brand first';
    modelSelect.appendChild(first);

    models.forEach(function (model) {
      var option = document.createElement('option');
      option.value = model;
      option.textContent = model;
      if (model === selected) option.selected = true;
      modelSelect.appendChild(option);
    });
    modelSelect.disabled = models.length === 0;
  }

  brandSelect.addEventListener('change', function () {
    selected = '';
    fillModels();
  });
  fillModels();
})();
