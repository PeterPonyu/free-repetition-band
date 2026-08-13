/* Load warehouse FIGURE-INDEX (copied to data/figures.json by portal/build.sh). */
(function () {
  var root = document.getElementById("plates");
  if (!root) {
    return;
  }
  var src = root.getAttribute("data-index") || "data/figures.json";
  fetch(src)
    .then(function (res) {
      if (!res.ok) {
        throw new Error("FIGURE-INDEX.json missing at " + src);
      }
      return res.json();
    })
    .then(function (index) {
      var list = document.createElement("ol");
      (index.figures || []).forEach(function (fig) {
        var item = document.createElement("li");
        item.textContent = fig.id + " (" + fig.label + ")";
        list.appendChild(item);
      });
      root.appendChild(list);
    })
    .catch(function (err) {
      root.textContent = String(err);
    });
})();
