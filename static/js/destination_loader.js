document.addEventListener("DOMContentLoaded", function() {
  const forms = document.querySelectorAll("[data-destination-url]");

  forms.forEach(function(form) {
      const typeSelect = form.querySelector(".destination-type");
      const destSelect = form.querySelector(".destination-id");
      const url = form.dataset.destinationUrl;

      if (!typeSelect || !destSelect) return;

      function loadDestinations() {
          const destType = typeSelect.value;

          destSelect.innerHTML = "";
          destSelect.appendChild(new Option("---------", ""));

          if (!destType) return;

          fetch(url + "?destination_type=" + destType)
              .then(res => res.json())
              .then(data => {
                  const results = data.results || [];

                  results.forEach(item => {
                      destSelect.appendChild(new Option(item.name, item.id));
                  });

                  // Auto-select HO (because there is only one head office)
                  if (destType === "HO" && results.length === 1) {
                      destSelect.value = results[0].id;
                  }
              });
      }

      typeSelect.addEventListener("change", loadDestinations);
  });
});
